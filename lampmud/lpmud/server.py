from lampost.server.handlers import SessionHandler
from lampost.di.resource import Injected, module_inject

db = Injected('datastore')
module_inject(__name__)


class NewCharacterData(SessionHandler):

    def post(self):
        self._return({'races': {race.dbo_id: _race_dto(race) for race in db.load_object_set('race')}})


def _race_dto(race):
    return {'name' : race.name, 'desc': race.desc}