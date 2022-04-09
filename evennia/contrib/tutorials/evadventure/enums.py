"""
Enums are constants representing different things in EvAdventure. The advantage
of using an Enum over, say, a string is that if you make a typo using an unknown
enum, Python will give you an error while a typo in a string may go through silently.

It's used as a direct reference:

    from enums import Ability

    if abi is Ability.STR:
        # ...

To get the `value` of an enum (must always be hashable, useful for Attribute lookups), use
`Ability.STR.value` (which would return 'strength' in our case).

"""
from enum import Enum

class Ability(Enum):
    """
    The six base abilities (defense is always bonus + 10)

    """
    STR = "strength"
    DEX = "dexterity"
    CON = "constitution"
    INT = "intelligence"
    WIS = "wisdom"
    CHA = "charisma"

    STR_DEFENSE = "strength_defense"
    DEX_DEFENSE = "dexterity_defense"
    CON_DEFENSE = "constitution_defense"
    INT_DEFENSE = "intelligence_defense"
    WIS_DEFENSE = "wisdom_defense"
    CHA_DEFENSE = "charisma_defense"

    ARMOR = "armor"
    HP = "hp"
    EXPLORATION_SPEED = "exploration_speed"
    COMBAT_SPEED = "combat_speed"
    LEVEL = "level"
    XP = "xp"

class WieldLocation(Enum):
    """
    Wield (or wear) locations.

    """
    # wield/wear location
    BACKPACK = "backpack"
    WEAPON_HAND = "weapon_hand"
    SHIELD_HAND = "shield_hand"
    TWO_HANDS = "two_handed_weapons"
    BODY = "body"  # armor
    HEAD = "head"  # helmets

    # combat-related
    OPTIMAL_DISTANCE = "optimal_distance"
    SUBOPTIMAL_DISTANCE = "suboptimal_distance"
