from lampost.context.resource import m_requires
from lampost.lpflavor.combat import AttackSkill, DefenseSkill
from lampost.lpflavor.skill import DEFAULT_SKILLS
from lampost.model.race import PlayerRace

m_requires('datastore', __name__)


def first_time_setup():
    unknown_race = PlayerRace('unknown')
    unknown_race.name = "Unknown"
    save_object(unknown_race)
    default_skills()


def default_skills():
    punch_skill = AttackSkill('punch')
    punch_skill.verb = 'punch'
    punch_skill.desc = "The basic, time honored punch."
    punch_skill.costs = {'action': 10, 'stamina': 10}
    punch_skill.prep_time = 10
    punch_skill.damage_type = "blunt"
    punch_skill.weapon_type = "unarmed"
    punch_skill.damage_calc = {'str': 2}
    punch_skill.accuracy_calc = {'agi': 5}
    punch_skill.prep_map = {'s': 'You wind up to wallop {N}.', 't': '{n} winds up to wallop you!', 'e': "{n} winds up to wallop {N}"}
    save_object(punch_skill)

    zap_skill = AttackSkill('zap')
    zap_skill.verb = 'zap'
    zap_skill.desc = "The all powerful immortal zap skill."
    zap_skill.damage_type = "spirit"
    zap_skill.weapon_type = "unused"
    zap_skill.damage_calc = {'skill': 1000000}
    zap_skill.accuracy_calc = {'skill': 1000000}
    zap_skill.success_map = {'s': "{n} calls forth mysterious power from the heavens, zapping {N}!"}
    save_object(zap_skill)

    dodge_skill = DefenseSkill('dodge')
    dodge_skill.desc = "The instinctive attempt to get out of the way"
    dodge_skill.delivery = {"melee"}
    dodge_skill.accuracy_calc = {'agi': 50, 'bal': 1}
    dodge_skill.auto_start = True
    save_object(dodge_skill)

