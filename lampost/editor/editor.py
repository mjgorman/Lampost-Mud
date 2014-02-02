import copy
from twisted.web.resource import Resource
from lampost.client.resources import request
from lampost.datastore.classes import get_sub_classes
from lampost.context.resource import requires
from lampost.editor.areas import AreaResource, RoomResource
from lampost.editor.articles import ArticleResource
from lampost.editor.base import EditResource
from lampost.editor.config import ConfigResource
from lampost.editor.display import DisplayResource
from lampost.editor.mobiles import MobileResource
from lampost.editor.players import PlayerResource
from lampost.editor.socials import SocialsResource
from lampost.lpflavor.combat import AttackTemplate, DefenseTemplate
from lampost.model.area import Area
from lampost.model.player import Player
from lampost.model.race import PlayerRace


class EditorResource(Resource):
    def __init__(self):
        Resource.__init__(self)
        self.putChild('area', AreaResource(Area))
        self.putChild('room', RoomResource())
        self.putChild('mobile', MobileResource())
        self.putChild('article', ArticleResource())
        self.putChild('player', PlayerResource(Player))
        self.putChild('config', ConfigResource())
        self.putChild('constants', PropertiesResource())
        self.putChild('social', SocialsResource())
        self.putChild('display', DisplayResource())
        self.putChild('race', EditResource(PlayerRace))
        self.putChild('attack', EditResource(AttackTemplate))
        self.putChild('defense', EditResource(DefenseTemplate))


@requires('context')
class PropertiesResource(Resource):
    @request
    def render_POST(self):
        constants = copy.copy(self.context.properties)
        constants['features'] = get_sub_classes('feature')
        return constants
