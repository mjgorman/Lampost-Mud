from lampost.db.dbofield import DBOTField
from lampost.di.app import on_app_start
from lampost.di.config import config_value, on_config_change
from lampost.di.resource import Injected, module_inject
from lampost.gameops import target
from lampost.gameops.action import ActionError
from lampost.meta.auto import TemplateField
from lampost.meta.core import CoreMeta
from lampost.util.lputil import args_print

from lampmud.lpmud import attributes
from lampmud.lpmud.skill import BaseSkill, roll_calc, SkillTemplate, avg_calc
from lampmud.mud.action import mud_action
from lampmud.mud.tools import combat_log

log = Injected('log')
ev = Injected('dispatcher')
module_inject(__name__)

damage_categories = {}


@on_app_start
@on_config_change
def _config():
    global damage_categories
    damage_categories = {group['dbo_id']: set() for group in config_value('damage_groups')}
    for damage_type in config_value('damage_types'):
        dbo_id, damage_group = damage_type['dbo_id'], damage_type['group']
        if damage_group:
            damage_categories['any'].add(dbo_id)
            damage_categories[damage_group].add(dbo_id)


CON_LEVELS = ['Insignificant', 'Trivial', 'Pesky', 'Annoying', 'Irritating', 'Bothersome', 'Troublesome',
              'Evenly Matched',
              'Threatening', 'Difficult', 'Intimidating', 'Imposing', 'Frightening', 'Terrifying', 'Unassailable']
CON_RANGE = int((len(CON_LEVELS) - 1) / 2)


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
    return True


def validate_delivery(ability, delivery):
    if delivery not in ability.delivery:
        raise ActionError("This doesn't work against that.")


def validate_dam_type(ability, damage_type):
    if damage_type not in ability.calc_damage_types:
        raise ActionError("That has no effect.")


def calc_consider(entity):
    try:
        best_attack = max(
            [skill.points_per_pulse(entity) for skill in entity.skills.values() if skill.template_id == 'attack'])
    except ValueError:
        best_attack = 0
    try:
        best_defense = max(
            [skill.points_per_pulse(entity) for skill in entity.skills.values() if skill.template_id == 'defense'])
    except ValueError:
        best_defense = 0
    pool_levels = sum(getattr(entity, base_pool_id, 0) for pool_id, base_pool_id in attributes.pool_keys)
    return int((best_attack + best_defense + pool_levels) / 2)


def consider_level(source_con, target_con):
    perc = max(target_con, 1) / max(source_con, 1) * 100
    perc = min(perc, 199)
    return int(perc / 13.27) - CON_RANGE


class Attack(metaclass=CoreMeta):
    success_map = TemplateField()
    fail_map = TemplateField()
    delivery = TemplateField()
    damage_pool = TemplateField()
    verb = TemplateField()

    def from_skill(self, skill, source):
        self.template = skill
        self.damage_type = skill.active_damage_type
        self.accuracy = roll_calc(source, skill.accuracy_calc, skill.skill_level)
        self.damage = roll_calc(source, skill.damage_calc, skill.skill_level)
        self.adj_damage = self.damage
        self.adj_accuracy = self.accuracy
        self.source = source
        return self

    def combat_log(self):
        return ''.join(['{n} ATTACK-- ',
                        args_print(damage_type=self.damage_type, accuracy=self.accuracy,
                                   damage=self.damage)])


class AttackTemplate(SkillTemplate):
    dbo_key_type = 'attack'
    dbo_set_key = 'attacks'


class AttackSkill(BaseSkill):
    template_id = 'attack'

    target_class = target.make_gen('env_living')

    display = 'combat'
    msg_class = 'attacked'
    match_args = 'source', 'target'
    damage_type = DBOTField('weapon')
    delivery = DBOTField('melee')
    damage_calc = DBOTField({})
    damage_pool = DBOTField('health')
    accuracy_calc = DBOTField({})
    weapon_type = DBOTField('any')
    prep_map = DBOTField(
        {'s': 'You prepare to {v} {N}.', 't': '{n} prepares to {v} you.', 'e': '{n} prepares to {v} {N}.'})
    success_map = DBOTField(
        {'s': 'You {v} {N}.', 't': '{n} {v}s you.', 'e': '{n} {v}s {N}.', 'display': 'combat'})
    fail_map = DBOTField(
        {'s': 'You miss {N}.', 't': '{n} misses you.', 'e': '{n} missed {N}.', 'display': 'combat'})

    def validate(self, source, target, **kwargs):
        if source == target:
            raise ActionError("You cannot harm yourself.  This is a happy place.")
        if validate_weapon(self, source.weapon_type):
            self.active_damage_type = source.weapon.damage_type
        else:
            self.active_damage_type = self.damage_type
        if 'dual_wield' in self.pre_reqs:
            validate_weapon(self, source.second_type)

    def prepare_action(self, source, target):
        self.validate(source, target)
        source.start_combat(target)
        target.start_combat(source)
        super().prepare_action(source, target)

    def invoke(self, source, target):
        attack = Attack().from_skill(self, source)
        combat_log(source, attack)
        target.attacked(source, attack)

    def points_per_pulse(self, owner):
        effect = avg_calc(owner, self.accuracy_calc, self.skill_level) + avg_calc(owner, self.damage_calc,
                                                                                  self.skill_level)
        cost = avg_calc(owner, self.costs, self.skill_level)
        return int((effect - cost) / max(self.prep_time, 1))


class DefenseTemplate(SkillTemplate):
    dbo_key_type = 'defense'
    dbo_set_key = 'defenses'

    def _on_loaded(self):
        self.calc_damage_types = set()
        for damage_type in self.damage_type:
            try:
                self.calc_damage_types |= damage_categories[damage_type]
            except KeyError:
                self.calc_damage_types.add(damage_type)


class DefenseSkill(BaseSkill):
    template_id = 'defense'

    target_class = target.make_gen('env_living')
    damage_type = DBOTField(['physical'])
    delivery = DBOTField(['melee', 'ranged'])
    weapon_type = DBOTField('unused')
    absorb_calc = DBOTField({})
    avoid_calc = DBOTField({})
    success_map = DBOTField(
        {'s': 'You avoid {N}\'s attack.', 't': '{n} avoids your attack.', 'e': '{n} avoids {N}\'s attack.'})
    calc_damage_types = TemplateField([])

    match_args = 'source',

    def invoke(self, source):
        source.defenses.add(self)

    def revoke(self, source):
        if self in source.defenses:
            source.defenses.remove(self)

    def apply(self, owner, attack):
        try:
            validate_weapon(self, owner)
            validate_delivery(self, attack.delivery)
            validate_dam_type(self, attack.damage_type)
        except ActionError:
            return
        adj_accuracy = roll_calc(owner, self.avoid_calc, self.skill_level)
        combat_log(attack.source, lambda: ''.join(['{N} defense: ', self.name, ' adj_accuracy: ', str(adj_accuracy)]),
                   self)
        attack.adj_accuracy -= adj_accuracy
        if attack.adj_accuracy < 0:
            return
        absorb = roll_calc(owner, self.absorb_calc, self.skill_level)
        combat_log(attack.source, lambda: ''.join(['{N} defense: ', self.name, ' absorb: ', str(absorb)]), self)
        attack.adj_damage -= absorb

    def points_per_pulse(self, owner):
        effect = avg_calc(owner, self.avoid_calc, self.skill_level) + avg_calc(owner, self.absorb_calc,
                                                                               self.skill_level)
        cost = avg_calc(owner, self.costs, self.skill_level)
        return int((effect - cost) / max(self.prep_time, 1))


@mud_action('consider', 'considered', target_class='env_living')
def consider(source, target, **_):
    target_con = target.considered()
    source_con = source.considered()
    con_string = CON_LEVELS[consider_level(source_con, target_con) + CON_RANGE]
    saved_last = source.last_opponent
    source.last_opponent = target
    source.status_change()
    source.last_opponent = saved_last
    return "At first glance, {} looks {}.".format(target.name, con_string)


@mud_action('peace')
def peace(source):
    if source.fight.opponents:
        source.fight.end_all()
        return "You use your great calming power to end the fight."
    else:
        return "You're not in combat"

