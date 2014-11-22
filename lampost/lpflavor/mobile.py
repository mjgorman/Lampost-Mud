from lampost.context.resource import m_requires
from lampost.datastore.dbo import DBOField, DBOTField
from lampost.datastore.auto import TemplateField
from lampost.lpflavor.archetype import Archetype
from lampost.lpflavor.attributes import fill_pools
from lampost.lpflavor.entity import EntityLP
from lampost.lpflavor.skill import SkillTemplate
from lampost.model.mobile import Mobile, MobileTemplate
from lampost.model.race import base_attr_value

m_requires(__name__, 'log', 'context', 'datastore', 'dispatcher')

affinities = {'player': {'enemies': ['monster']},
              'neutral': {'enemies': []},
              'monster': {'enemies': ['player']}}


def _post_init():
    context.set('affinities', affinities)


class MobileTemplateLP(MobileTemplate):
    dbo_key_type = 'mobile'
    default_skills = DBOField({})

    def on_loaded(self):
        if self.archetype:
            arch = load_object(Archetype, self.archetype)
            for attr_name, start_value in arch.base_attrs.items():
                setattr(instance_cls, attr_name, start_value)
            self.desc = arch.desc
        else:
            for attr_name in Archetype.attr_list:
                setattr(self.instance_cls, attr_name, base_attr_value * self.level)
        self.enemies = affinities[self.affinity]['enemies']

    def config_instance(self, mobile, owner):
        mobile.skills = {}
        for skill_id, skill_status in self.default_skills.items():
            skill_template = load_object(SkillTemplate, skill_id)
            if not skill_template:
                warn("Skill {} not found.", skill_id)
                continue
            skill = skill_template.create_instance(mobile)
            skill.skill_level = skill_status['skill_level']
            mobile.add_skill(skill)
        fill_pools(mobile)
        super().config_instance(mobile, owner)


class MobileLP(EntityLP):
    template_id = "mobile"

    archetype = DBOTField()
    level = DBOTField(1)
    affinity = DBOTField('neutral')
    enemies = TemplateField('enemies')

    def entity_enter_env(self, entity):
        self._react_entity(entity)

    def entity_leave_env(self, entity, ex):
        super().entity_leave_env(entity, ex)
        self.fight.check_follow(entity, ex)

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

    def detach(self):
        super().detach()
        self.original_env.mobiles[self.template].remove(self)

