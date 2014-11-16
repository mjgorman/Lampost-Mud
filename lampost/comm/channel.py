from lampost.client.services import ClientService
from lampost.gameops.action import make_action
from lampost.context.resource import m_requires, provides
from lampost.util.lmutil import timestamp

m_requires(__name__, 'dispatcher', 'datastore', 'channel_service')

ALL_CHANNELS = 'all_channels'
GENERAL_CHANNELS = 'general_channels'


class Channel():
    def __init__(self, channel_type, instance_id=None, general=False):
        make_action(self, channel_type)
        self.id = "{}_{}".format(channel_type, instance_id) if instance_id else channel_type
        self.display = "{}_display".format(channel_type)
        channel_service.register_channel(self.id, general)

    def __call__(self, source, command, **_):
        space_ix = command.find(" ")
        if space_ix == -1:
            return source.display_line("Say what?")
        self.send_msg(source.name + ":" + command[space_ix:])

    def send_msg(self, msg):
        channel_service.dispatch_message(self.id, msg)

    def disconnect(self, player):
        channel_service.unregister_channel(self.id)





@provides('channel_service')
class ChannelService(ClientService):

    def _post_init(self):
        super()._post_init()
        self.all_channels = fetch_set_keys(ALL_CHANNELS)
        self.general_channels = fetch_set_keys(GENERAL_CHANNELS)
        register('maintenance', self._prune_channels)
        register('session_connect', self._session_connect)
        register('player_connect', self._player_connect)
        register('player_logout', self._player_logout)
        register('server_settings', self._update_settings)

    def _update_settings(self, server_settings):
        self.max_channel_history = server_settings.get('max_channel_history', 1000)

    def register_channel(self, channel_id, general=False):
        add_set_key(ALL_CHANNELS, channel_id)
        self.all_channels.add(channel_id)
        if general:
            add_set_key(GENERAL_CHANNELS, channel_id)
            self.general_channels.add(channel_id)

    def unregister_channel(self, channel_id):
        remove_set_key(ALL_CHANNELS, channel_id)
        self.all_channels.pop(channel_id, None)
        self.general_channels.pop(channel_id, None)

    def dispatch_message(self, channel_id, text):
        message = {'id': channel_id, 'text': text}
        timestamp(message)
        for session in self.sessions:
            if channel_id in session.channel_ids:
                session.append({'channel': message})
        add_db_list(channel_key(channel_id), {'text': text, 'timestamp': message['timestamp']})

    def subscribe(self, session, channel_id):
        session.channel_ids.add(channel_id)
        session.append({'channel_subscribe': {'id': channel_id, 'messages': get_db_list(channel_key(channel_id))}})

    def unsubscribe(self, session, channel_id):
        session.channel_ids.remove(channel_id)
        session.append({'channel_unsubscribe': channel_id})

    def _session_connect(self, session, *_):
        self.register(session, None)
        if not hasattr(session, 'channel_ids'):
            session.channel_ids = set()
        for channel_id in session.channel_ids.copy():
            if channel_id not in self.general_channels:
                self.unsubscribe(session, channel_id)
        for channel_id in self.general_channels:
            self.subscribe(session, channel_id)

    def _player_connect(self, player, *_):
        new_channels = {channel.id for channel in player.active_channels}
        for channel_id in new_channels:
            if channel_id not in player.session.channel_ids:
                self.subscribe(player.session, channel_id)
        for channel_id in player.session.channel_ids.copy():
            if channel_id not in new_channels:
                self.unsubscribe(session, channel_id)

    def _player_logout(self, player, *_):
        self._session_connect(player.session)

    def _prune_channels(self):
        for channel_id in self.all_channels:
            trim_db_list(channel_key(channel_id), 0, self.max_channel_history)


def channel_key(channel_id):
    return 'channel:{}'.format(channel_id)
