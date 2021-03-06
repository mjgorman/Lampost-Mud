from lampost.db.dbofield import DBOField
from lampost.gameops.action import obj_action
from lampmud.model.item import Readable, ItemDBO


class Inscription(ItemDBO, Readable):
    class_id = 'inscription'

inscription = Inscription()
inscription.title = "Archaic Inscription"
inscription.text = "Herewith wilt thou be bound"
inscription.desc = "An inscription written in the flowery letters of a time long past."
inscription.on_loaded()


class Touchstone(ItemDBO):
    class_id = 'touchstone'

    title = DBOField('Touchstone')
    desc = DBOField("An unadorned marble obelisk about five feet high.  There is an inscription in an archaic script on one side.")
    aliases = DBOField(["obelisk"])
    inscription = DBOField(inscription, 'inscription')

    @obj_action()
    def touch(self, source, **_):
        source.display_line("You feel a shock coursing through you.  It lasts a few seconds")
        source.touchstone = self.dbo_owner.dbo_id

    def _on_loaded(self):
        self.target_providers = [self.inscription]
        self.instance_providers.append(self.inscription)
