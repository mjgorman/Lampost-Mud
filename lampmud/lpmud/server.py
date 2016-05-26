from lampost.server.handlers import SessionHandler
from lampost.di.resource import m_requires

from lampmud.lpmud.archetype import PlayerRace

m_requires(__name__, 'log', 'datastore')


class NewCharacterData(SessionHandler):

    def post(self):
        self._return({'races': {race.dbo_id: _race_dto(race) for race in load_object_set(PlayerRace)}})


def _race_dto(race):
    return {'name' : race.name, 'desc': race.desc}
