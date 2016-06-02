from lampost.di.config import on_configured, config_value
from lampost.di.resource import Injected, module_inject
from lampost.meta.auto import TemplateField
from lampost.db.dbofield import DBOField, DBOTField

from lampmud.lpmud.archetype import Archetype
from lampmud.lpmud.attributes import fill_pools
from lampmud.lpmud.entity import EntityLP, Skilled
from lampmud.lpmud.skill import add_skill
from lampmud.model.mobile import MobileTemplate, Mobile


log = Injected('log')
db = Injected('datastore')
module_inject(__name__)


@on_configured
def _on_configured():
    global affinities
    global attributes
    global base_attr_value
    affinities = config_value('affinities')
    attributes = config_value('attributes')
    base_attr_value = config_value('base_attr_value')


class MobileTemplateLP(MobileTemplate):
    class_id = 'mobile'
    default_skills = DBOField([], 'default_skill')

    def on_loaded(self):
        if self.archetype:
            arch = db.load_object(self.archetype, Archetype)
            for attr_name, start_value in arch.base_attrs.items():
                setattr(self.instance_cls, attr_name, start_value)
            self.desc = arch.desc
        else:
            for attr in attributes:
                setattr(self.instance_cls, attr['dbo_id'], base_attr_value * self.level)
        self.enemies = affinities[self.affinity]['enemies']

    def config_instance(self, mobile, owner):
        mobile.skills = {}
        for default_skill in self.default_skills:
            add_skill(default_skill.skill_template, mobile, default_skill.skill_level, 'mobile')
        fill_pools(mobile)
        super().config_instance(mobile, owner)


class MobileLP(EntityLP, Mobile, Skilled):
    template_id = "mobile"

    archetype = DBOTField()
    level = DBOTField(1)
    affinity = DBOTField('neutral')
    enemies = TemplateField('enemies')
    guard_msg = DBOField("{source} stops you from moving {exit}.")

    def entity_enter_env(self, entity, *_):
        self._react_entity(entity)

    def entity_leave_env(self, entity, exit_action):
        super().entity_leave_env(entity, exit_action)
        self.fight.check_follow(entity, exit_action)

    def enter_env(self, new_env, ex=None):
        super().enter_env(new_env, ex)
        for entity in new_env.denizens:
            self._react_entity(entity)

    def _react_entity(self, entity):
        if entity in self.fight.opponents.keys():
            self.fight.add(entity)
            self.check_fight()
        elif hasattr(entity, 'affinity') and entity.affinity in self.enemies:
            self.start_combat(entity)

    def on_detach(self):
        self.original_env.mobiles[self.template].remove(self)

