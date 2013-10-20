from random import randint
from lampost.context.resource import m_requires
from lampost.datastore.dbo import RootDBO
from lampost.gameops.action import ActionError
from lampost.gameops.display import COMBAT_DISPLAY
from lampost.lpflavor.skill import base_skill, BaseSkill
from lampost.util.lmutil import args_print

m_requires('log', 'tools', 'dispatcher', __name__)

DAMAGE_TYPES = {'blunt': {'desc': 'Blunt trauma (clubs, maces)'},
                'pierce': {'desc': 'Piercing damage (spears, arrows)'},
                'slash': {'desc': 'Slash damage (swords, knives)'},
                'cold': {'desc': 'Cold'},
                'fire': {'desc': 'Fire'},
                'shock': {'desc': 'Electric'},
                'acid': {'desc': 'Acid'},
                'poison': {'desc': 'Poison'},
                'psych': {'desc': 'Mental/psychic damage'},
                'spirit': {'desc': 'Spiritual damage'}}

DAMAGE_DELIVERY = {'melee', 'ranged', 'psychic'}


def roll_calc(source, calc, skill_level=0):
    base_calc = sum(getattr(source, attr, 0) * calc_value for attr, calc_value in calc.iteritems())
    roll = randint(0, 20)
    if roll == 0:
        roll = -5
    if roll == 19:
        roll = 40
    return base_calc + roll * calc.get('roll', 0) + skill_level * calc.get('skill', 0)


def validate_weapon(ability, weapon_type):
    if not ability.weapon_type or ability.weapon_type == 'unused':
        return
    if ability.weapon_type == 'unarmed':
        if weapon_type:
            raise ActionError("You can't do that with a weapon.")
        return
    if not weapon_type:
        raise ActionError("That requires a weapon.")
    if ability.weapon_type != 'any' and ability.weapon_type != weapon_type:
        raise ActionError("You need a different weapon for that.")


def validate_delivery(ability, attack):
    if attack.delivery not in ability.delivery:
        raise ActionError("This doesn't work against that.")


class Attack(object):
    def from_skill(self, skill, skill_level, source):
        self.success_map = skill.success_map
        self.fail_map = skill.fail_map
        self.damage_type = skill.damage_type
        self.accuracy = roll_calc(source, skill.accuracy_calc, skill_level)
        self.damage = roll_calc(source, skill.damage_calc, skill_level)
        self.damage_pool = skill.damage_pool
        self.adj_damage = self.damage
        self.adj_accuracy = self.accuracy
        self.delivery = skill.delivery
        self.source = source
        return self

    def combat_log(self):
        return ''.join(['{n} ATTACK-- ',
                        args_print(damage_type=self.damage_type, accuracy=self.accuracy,
                                   damage=self.damage)])


@base_skill
class AttackSkill(BaseSkill, RootDBO):
    dbo_fields = BaseSkill.dbo_fields + ('damage_type', 'damage_calc', 'accuracy_calc', 'weapon_type')
    dbo_key_type = 'skill'
    dbo_set_key = 'skill_attack'

    msg_class = 'rec_attack'
    damage_type = 'blunt'
    delivery = 'melee'
    damage_calc = {}
    damage_pool = 'health'
    accuracy_calc = {}
    weapon_type = None
    success_map = {'s': 'You hit {N}.', 't': '{n} hits you.', 'e': '{n} hits {N}.', 'display': COMBAT_DISPLAY}
    fail_map = {'s': 'You miss {N}.', 't': '{n} misses you.', 'e': '{n} missed {N}.', 'display': COMBAT_DISPLAY}

    def prepare_action(self, source, target, **kwargs):
        if source == target:
            raise ActionError("You cannot harm yourself.  This is a happy place.")
        validate_weapon(self, source.weapon_type)
        if 'dual_wield' in self.pre_reqs:
            validate_weapon(self, source.second_type)
        super(AttackSkill, self).prepare_action(source, target, **kwargs)

    def invoke(self, skill_status, source, target_method, **ignored):
        attack = Attack().from_skill(self, skill_status.skill_level, source)
        combat_log(source, attack)
        target_method(source, attack)


@base_skill
class DefenseSkill(BaseSkill, RootDBO):
    dbo_fields = BaseSkill.dbo_fields + ('damage_type', 'absorb_calc', 'accuracy_calc', 'weapon_type')
    dbo_key_type = 'skill'
    dbo_set_key = 'skill_defense'

    damage_type = 'any'
    delivery = {'melee'}
    weapon_type = 'unused'
    accuracy_calc = {}
    absorb_calc = {}
    success_map = {'s': 'You avoid {N}\'s attack.', 't': '{n} avoids your attack.', 'e': '{n} avoids {N}\'s attack.'}

    def invoke(self, source, **ignored):
        pass

    def apply(self, owner, attack):
        try:
            validate_weapon(self, owner)
            validate_delivery(self, attack)
        except ActionError:
            return
        adj_accuracy = roll_calc(owner, self.accuracy_calc)
        combat_log(attack.source, lambda: ''.join(['{N} defense: ', self.dbo_id, ' adj_accuracy: ', str(adj_accuracy)]), self)
        attack.adj_accuracy -= roll_calc(owner, self.accuracy_calc)
        if attack.adj_accuracy < 0:
            return
        attack.adj_damage -= roll_calc(owner, self.absorb_calc)
