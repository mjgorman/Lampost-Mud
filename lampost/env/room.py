from collections import defaultdict
import itertools
import random

from lampost.comm.broadcast import Broadcast
from lampost.context.resource import m_requires
from lampost.datastore.dbo import RootDBO, DBOField, DBOTField
from lampost.env.movement import Direction
from lampost.gameops.script import Scriptable
from lampost.model.mobile import MobileTemplate
from lampost.model.article import ArticleTemplate
from lampost.gameops.display import *
from lampost.mud.inventory import InvenContainer


m_requires('log', 'dispatcher', 'datastore', __name__)

default_room_size = 10
room_garbage_time = 600


def tell(listeners, msg_type, *args):
    for listener in listeners:
        try:
            receiver = getattr(listener, msg_type)
        except AttributeError:
            continue
        receiver(*args)


class Exit(RootDBO):
    class_id = 'exit'

    target_class = None
    direction = DBOField(None, 'direction')
    destination = DBOField()
    desc = DBOField()
    aliases = DBOField([])

    can_follow = True
    msg_class = 'no_args'

    @property
    def verbs(self):
        return (self.direction.dbo_id,), (self.direction.desc,)

    @property
    def dir_desc(self):
        return self.direction.desc

    @property
    def from_desc(self):
        from_dir = Direction.ref_map.get(self.direction.rev_key, None)
        if from_dir:
            return from_dir.desc

    @property
    def dest_room(self):
        return load_by_key('room', self.destination)

    def examine(self, source, **ignored):
        source.display_line('Exit: {0}  {1}'.format(self.direction.desc, self.dest_room.title), EXIT_DISPLAY)

    def __call__(self, source, **ignored):
        if source.instance:
            destination = source.instance.get_room(self.destination)
        else:
            destination = self.dest_room
        source.change_env(destination, self)


class Room(Scriptable):
    dbo_key_type = "room"

    dbo_rev = DBOTField(0)
    desc = DBOTField()
    size = DBOTField(default_room_size)
    exits = DBOTField([], 'exit')
    extras = DBOTField([], 'base_item')
    mobile_resets = DBOTField([], 'mobile_reset')
    article_resets = DBOTField([], 'article_reset')
    features = DBOTField([], 'feature')
    title = DBOTField()

    instance = None

    def __init__(self, dbo_id=None):
        super(Room, self).__init__(dbo_id)
        self.inven = InvenContainer()
        self.denizens = []
        self.mobiles = defaultdict(set)

    @property
    def action_providers(self):
        return itertools.chain(self.features, self.exits, self.denizens, self.inven)

    @property
    def dbo_set_key(self):
        return "area_rooms:{}".format(self.area_id)

    @property
    def room_id(self):
        return self.dbo_id

    @property
    def name(self):
        return self.title

    @property
    def area_id(self):
        return self.dbo_id.split(":")[0]

    @property
    def contents(self):
        return itertools.chain(self.features, self.denizens, self.inven)

    def glance(self, source, **ignored):
        return source.display_line(self.title, ROOM_DISPLAY)

    def entity_enters(self, entity, ex):
        try:
            entity.entry_msg.source = entity
            self.receive_broadcast(entity.entry_msg)
        except AttributeError:
            pass
        self.denizens.append(entity)
        entity.pulse_stamp = current_pulse()
        tell(self.contents, "entity_enter_env", entity)

    def entity_leaves(self, entity, ex):
        try:
            entity.exit_msg.source = entity
            self.receive_broadcast(entity.exit_msg)
        except AttributeError:
            pass
        self.denizens.remove(entity)
        tell(self.contents, "entity_leave_env", entity, ex)

    def add_inven(self, article):
        self.inven.append(article)
        article.pulse_stamp = current_pulse()

    def remove_inven(self, article):
        self.inven.remove(article)

    def receive_broadcast(self, broadcast):
        if not broadcast:
            return
        if getattr(broadcast, 'target', None) == self:
            broadcast.target = None
        tell(self.contents, "receive_broadcast", broadcast)

    def broadcast(self, **kwargs):
        self.receive_broadcast(Broadcast(**kwargs))

    def social(self):
        pass

    def examine(self, source, **ignored):
        source.display_line(self.title, ROOM_TITLE_DISPLAY)
        source.display_line('HRT', ROOM_DISPLAY)
        source.display_line(self.desc, ROOM_DISPLAY)
        source.display_line('HRB', ROOM_DISPLAY)
        if self.exits:
            for my_exit in self.exits:
                my_exit.examine(source)
        else:
            source.display_line("No obvious exits", EXIT_DISPLAY)
        tell(filter(lambda x: x != source, self.contents), 'glance', source)

    def short_exits(self):
        return ", ".join([ex.dir_desc for ex in self.exits])

    def find_exit(self, exit_dir):
        for my_exit in self.exits:
            if my_exit.direction == exit_dir:
                return my_exit

    def on_loaded(self):
        self.reset()
        self.garbage_time()

    def garbage_time(self):
        register_once(self.check_garbage, seconds=room_garbage_time + 1)

    def check_garbage(self):
        if hasattr(self, 'dirty'):
            if not self.instance:
                save_object(self)
            del self.dirty
        stale_pulse = future_pulse(-room_garbage_time)
        for obj in self.contents:
            obj_pulse = getattr(obj, 'pulse_stamp', 0)
            if obj_pulse > stale_pulse or hasattr(obj, 'is_player'):
                self.garbage_time()
                return
        self.clean_up()

    def reset(self):
        for m_reset in self.mobile_resets:
            template = m_reset.mobile_id
            if not template:
                error("Missing template for mobile reset roomId: {0}  mobileId: {1}".format(self.dbo_id, m_reset.mobile_id))
                continue
            curr_count = len(self.mobiles[template])
            for unused in range(m_reset.reset_count - curr_count):
                self.add_mobile(template, m_reset)
            if m_reset.reset_count <= curr_count < m_reset.reset_max:
                self.add_mobile(template, m_reset)
        for a_reset in self.article_resets:
            template = a_reset.article_id
            if not template:
                error('Invalid article in reset roomId: {0}  articleId: {1}'.format(self.dbo_id, a_reset.article_id))
                continue
            curr_count = len([entity for entity in self.inven if getattr(entity, 'template', None) == template])
            if template.divisible:
                if not curr_count:
                    instance = template.create_instance(self)
                    instance.quantity = random.randrange(a_reset.reset_count, a_reset.reset_max + 1)
                    instance.enter_env(self)
            else:
                for unused in range(a_reset.reset_count - curr_count):
                    instance = template.create_instance(self)
                    instance.enter_env(self)
                if a_reset.reset_count <= curr_count < a_reset.reset_max:
                    instance = template.create_instance(self)
                    instance.enter_env(self)

    def add_mobile(self, template, reset):
        instance = template.create_instance(self)
        for article_load in reset.article_loads:
            article_template = article_load.article_id
            if not template:
                error(
                    "Invalid article load for roomId: {0}, mobileId: {1}, articleId: {2}".format(self.dbo_id, template.mobile_id, article_template.article_id))
                continue
            article = article_template.create_instance()
            instance.add_inven(article)
            if article_load.load_type == "equip":
                instance.equip_article(article)
        instance.enter_env(self)

    def clean_up(self):
        detach_events(self)
        for mobile_list in self.mobiles.viewvalues():
            for mobile in mobile_list:
                if mobile.env != self:
                    mobile.enter_env(self)
        for obj in self.contents:
            if hasattr(obj, 'detach'):
                obj.detach()
        if not getattr(self, 'template', None):
            evict_object(self)
