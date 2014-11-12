from lampost.editor.areas import AreaEditor, RoomEditor
from lampost.editor.config import ConfigEditor, DisplayEditor, Properties
from lampost.editor.editor import ChildrenEditor, Editor, ChildList
from lampost.editor.imports import ImportsEditor
from lampost.editor.players import PlayerEditor
from lampost.editor.scripts import ScriptEditor
from lampost.editor.socials import SocialsEditor
from lampost.env.room import Room
from lampost.gameops.script import Script
from lampost.lpflavor.skill import SkillTemplate
from lampost.model.article import ArticleTemplate
from lampost.model.mobile import MobileTemplate
from lampost.model.race import PlayerRace


def add_endpoints(web_server):
    web_server.add(r'/editor/constants', Properties)
    web_server.add(r'/editor/area/(.*)', AreaEditor)
    web_server.add(r'/editor/room/list/(.*)', ChildList, obj_class=Room)
    web_server.add(r'/editor/room/(.*)', RoomEditor)
    web_server.add(r'/editor/mobile/list/(.*)', ChildList, obj_class=MobileTemplate)
    web_server.add(r'/editor/mobile/(.*)', ChildrenEditor, obj_class=MobileTemplate)
    web_server.add(r'/editor/article/list/(.*)', ChildList, obj_class=ArticleTemplate)
    web_server.add(r'/editor/article/(.*)', ChildrenEditor, obj_class=ArticleTemplate)
    web_server.add(r'/editor/player/(.*)', PlayerEditor)
    web_server.add(r'/editor/config/(.*)', ConfigEditor)
    web_server.add(r'/editor/social/(.*)', SocialsEditor)
    web_server.add(r'/editor/display/(.*)', DisplayEditor)
    web_server.add(r'/editor/race/(.*)', Editor, obj_class=PlayerRace)
    web_server.add(r'/editor/skill/(.*)', Editor, obj_class=SkillTemplate)
    web_server.add(r'/editor/script/list/(.*)', ChildList, obj_class=Script)
    web_server.add(r'/editor/script/(.*)', ScriptEditor)
    web_server.add(r'/editor/imports/(.*)', ImportsEditor)