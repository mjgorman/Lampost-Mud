from twisted.web.resource import Resource

from lampost.client.resources import request
from lampost.context.resource import m_requires
from lampost.datastore.exceptions import DataError
from lampost.editor.base import EditResource
from lampost.mud.socials import Social
from lampost.comm.broadcast import BroadcastMap, Broadcast, broadcast_types

m_requires('mud_actions', __name__)


class SocialsResource(EditResource):
    def __init__(self):
        EditResource.__init__(self, Social)
        self.putChild('preview', SocialPreview())

    def pre_create(self, social_dto, session):
        if mud_actions.verb_list((social_dto['dbo_id'],)):
            raise DataError("Verb already in use")

    def post_delete(self, social, session):
        mud_actions.rem_verb(social.dbo_id, social)


class SocialPreview(Resource):
    @request
    def render_POST(self, content):
        broadcast_map = BroadcastMap()
        broadcast_map.populate(content.b_map)
        broadcast = Broadcast(broadcast_map, content.source, content.source if content.self_source else content.target)
        return {broadcast_type['id']: broadcast.substitute(broadcast_type['id']) for broadcast_type in broadcast_types}





