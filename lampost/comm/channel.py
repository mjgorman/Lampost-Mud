from lampost.client.services import ClientService
from lampost.gameops.action import make_action
from lampost.context.resource import m_requires, provides
from lampost.util.lmutil import timestamp

m_requires(__name__, 'dispatcher', 'datastore', 'channel_service')


class Channel():
    def __init__(self, verb):
        make_action(self, verb)
        self.id = verb
        self.display = "{}_display".format(verb)
        channel_service.known_channels.append(self.id)

    def __call__(self, source, command, **_):
        space_ix = command.find(" ")
        if space_ix == -1:
            return source.display_line("Say what?")
        text = source.name + ":" + command[space_ix:]
        channel_service.dispatch_message(self.id, text)


@provides('channel_service')
class ChannelService(ClientService):

    def __init__(self):
        super().__init__()
        self.known_channels = []

    def _post_init(self):
        super()._post_init()
        register('maintenance', self._prune_channels)
        register('session_connect', self._session_connect)
        register('player_connect', self._player_connect)
        register('server_settings', self._update_settings)

    def _update_settings(self, server_settings):
        self.max_channel_history = server_settings.get('max_channel_history', 1000)

    def dispatch_message(self, channel_id, text):
        message = {'id': channel_id, 'text': text}
        timestamp(message)
        for session in self.sessions:
            if channel_id in session.channel_ids:
                session.append({'channel': message})
        add_db_list(channel_key(channel_id), {'text': text, 'timestamp': message['timestamp']})

    def gen_channels(self):
        return [self._channel_messages('shout')]

    def _session_connect(self, session):
        self.register(session, None)
        session.channel_ids = (['shout'])
        session.append({'gen_channels': self.gen_channels()})

    def _channel_messages(self, channel_id):
        return {'id': channel_id, 'messages': get_db_list(channel_key(channel_id))}

    def _player_connect(self, player, client_data):
        player.session.channel_ids = {channel.id for channel in player.active_channels}
        client_data['channels'] = [self._channel_messages(channel.id) for channel in player.active_channels]

    def _prune_channels(self):
        for channel_id in self.known_channels:
            trim_db_list(channel_key(channel_id), 0, self.max_channel_history)


def channel_key(channel_id):
    return 'channel:{}'.format(channel_id)
