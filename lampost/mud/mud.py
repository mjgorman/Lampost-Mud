from importlib import import_module
from lampost.env.movement import Direction
from lampost.comm.broadcast import broadcast_types, broadcast_tokens
from lampost.env.room import Room, safe_room
from lampost.mud.action import imm_actions
from lampost.context.resource import requires, m_requires, register_module
from lampost.comm.channel import Channel


room_module = import_module('lampost.env.room')
import_module('lampost.model.area')
import_module('lampost.mud.immortal')
import_module('lampost.comm.chat')
import_module('lampost.mud.inventory')
import_module('lampost.mud.socials')
import_module('lampost.mud.group')
import_module('lampost.env.instance')

m_requires(__name__, 'log', 'datastore', 'dispatcher', 'mud_actions', 'perm')


@requires('context', 'config_manager', 'instance_manager')
class MudNature():

    def __init__(self, flavor):
        flavor_module = __import__('lampost.' + flavor + '.flavor', globals(), locals())
        register_module(self)

    def _post_init(self):
        self.shout_channel = Channel("shout", general=True)
        self.imm_channel = Channel("imm")

        self.context.set('article_load_types', ['equip', 'default'])
        self.context.set('broadcast_types', broadcast_types)
        self.context.set('broadcast_tokens', broadcast_tokens)
        self.context.set('directions', Direction.ordered)

        register('game_settings', self._game_settings)
        register('player_baptise', self._baptise, priority=-100)
        register('imm_baptise', self._imm_baptise, priority=-100)
        register('missing_env', self._start_env)

    def _imm_baptise(self, player):
        player.can_die = False
        player.immortal = True
        self.imm_channel.add_sub(player)
        for cmd in imm_actions:
            if player.imm_level >= perm_level(cmd.imm_level):
                player.enhance_soul(cmd)
            else:
                player.diminish_soul(cmd)

    def _game_settings(self, game_settings):
        room_module.default_room_size = game_settings.get('room_size', room_module.default_room_size)
        room_module.room_reset_time = game_settings.get('room_reset_time', room_module.room_reset_time)

    def _baptise(self, player):
        player.baptise()
        self.shout_channel.add_sub(player)
        if player.imm_level:
            dispatch("imm_baptise", player)
        self._start_env(player)

    def _start_env(self, player):
        room = None
        if getattr(player, "room_id", None):
            instance = self.instance_manager.get(player.instance_id)
            if instance:
                room = instance.get_room(player.room_id)
            else:
                del player.instance_id
            if not room:
                room = load_object(player.room_id, Room)
        if not room:
            room = load_object(self.config_manager.start_room, Room)
            if room:
                player.room_id = room.dbo_id
                save_object(player)
        if not room:
            room = safe_room
            try:
                del player.room_id
                save_object(player)
            except AttributeError:
                pass
        player.change_env(room)