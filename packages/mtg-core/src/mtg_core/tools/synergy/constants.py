"""Constants and data for synergy detection."""

from __future__ import annotations

from typing import Any

from ...data.models.responses import SynergyType

SYNERGY_BASE_SCORES: dict[SynergyType, float] = {
    "keyword": 0.8,
    "tribal": 0.85,
    "ability": 0.75,
    "theme": 0.7,
    "archetype": 0.65,
}

KEYWORD_SYNERGIES: dict[str, list[tuple[str, str]]] = {
    "Flying": [
        ("reach", "Can block flying creatures"),
        ("can block.*flying", "Anti-flying defense"),
    ],
    "Deathtouch": [
        ("first strike", "Strike first with deathtouch"),
        ("double strike", "Strike first with deathtouch"),
        ("fight", "Removal via fighting"),
        ("lure", "Force blocks with deathtouch"),
    ],
    "Lifelink": [
        ("whenever you gain life", "Life gain triggers"),
        ("life.*matters", "Life total payoffs"),
        ("pay.*life", "Offset life payment costs"),
    ],
    "Trample": [
        ("power.*greater", "Power boost synergy"),
        ("double.*power", "Double power for trample damage"),
    ],
    "+1/+1 counter": [
        ("proliferate", "Increase counters"),
        ("Hardened Scales", "Double counters"),
        ("Doubling Season", "Double counters"),
        ("Winding Constrictor", "Extra counters"),
    ],
    "-1/-1 counter": [
        ("proliferate", "Increase counters"),
        ("Hapatra", "Snake tokens from counters"),
        ("Nest of Scarabs", "Insect tokens from counters"),
    ],
    "Unblockable": [
        ("whenever.*deals combat damage", "Combat damage triggers"),
        ("Curiosity", "Draw on damage"),
        ("Sword of", "Equipment synergy"),
    ],
    "Menace": [
        ("can't block alone", "Stack blocking restrictions"),
    ],
    "Flash": [
        ("instant", "Instant speed synergy"),
        ("end step", "End step tricks"),
    ],
    "Haste": [
        ("enters the battlefield", "Immediate ETB + attack"),
        ("attack trigger", "Attack triggers immediately"),
    ],
}

ABILITY_SYNERGIES: dict[str, list[tuple[str, str]]] = {
    "enters the battlefield": [
        ("Panharmonicon", "Double ETB triggers"),
        ("blink", "Repeat ETB effects"),
        ("flicker", "Repeat ETB effects"),
        ("return.*to.*hand", "Bounce for re-ETB"),
        ("Conjurer's Closet", "Free blink each turn"),
        ("Thassa, Deep-Dwelling", "Free blink each turn"),
    ],
    "whenever.*dies": [
        ("sacrifice", "Controlled death triggers"),
        ("Blood Artist", "Drain on death"),
        ("Zulaport Cutthroat", "Drain on death"),
        ("aristocrat", "Sacrifice synergy"),
        ("Grave Pact", "Force opponent sacrifice"),
    ],
    "when.*dies": [
        ("sacrifice", "Controlled death triggers"),
        ("reanimate", "Return after death"),
    ],
    "draw.*card": [
        ("whenever you draw", "Draw triggers"),
        ("Rhystic Study", "More draw triggers"),
        ("Consecrated Sphinx", "Mass card draw"),
        ("Notion Thief", "Steal opponent draws"),
    ],
    "whenever you cast": [
        ("storm", "Storm count builder"),
        ("magecraft", "Copy spells"),
        ("prowess", "Pump on cast"),
        ("cascade", "Free extra casts"),
    ],
    "discard": [
        ("madness", "Cast discarded cards"),
        ("Waste Not", "Value from discard"),
        ("whenever you discard", "Discard triggers"),
        ("Anje Falkenrath", "Madness commander"),
    ],
    # Split "graveyard" into specific mechanics that actually synergize
    "flashback": [
        ("mill", "Fill graveyard for flashback"),
        ("discard", "Put spells in graveyard"),
        ("surveil", "Filter cards to graveyard"),
        ("self-mill", "Stock graveyard"),
    ],
    "unearth|escape": [
        ("mill", "Fill graveyard for recursion"),
        ("surveil", "Filter to graveyard"),
        ("discard", "Put creatures in graveyard"),
    ],
    r"return.*creature.*graveyard.*battlefield|reanimate": [
        ("sacrifice", "Put creatures in graveyard"),
        ("mill", "Fill graveyard with creatures"),
        ("entomb", "Tutor to graveyard"),
        ("discard", "Put creatures in graveyard"),
    ],
    r"return.*aura.*graveyard|return.*equipment.*graveyard": [
        ("mill", "Fill graveyard with auras/equipment"),
        ("sacrifice.*enchantment", "Put auras in graveyard"),
        ("Voltron", "Aura/Equipment theme"),
    ],
    "dredge": [
        ("draw", "Trigger dredge replacement"),
        ("mill", "Fill graveyard"),
        ("graveyard.*matters", "Benefit from full graveyard"),
    ],
    "create.*token": [
        ("populate", "Copy tokens"),
        ("Doubling Season", "Double tokens"),
        ("Anointed Procession", "Double tokens"),
        ("whenever.*token.*enters", "Token ETB triggers"),
        ("Purphoros", "Damage on token creation"),
    ],
    "counter": [
        ("proliferate", "Add more counters"),
        ("The Ozolith", "Save counters"),
    ],
    "sacrifice": [
        ("whenever.*dies", "Death triggers"),
        ("creature dying", "Death triggers"),
        ("Grave Pact", "Force opponent sacrifice"),
        ("Blood Artist", "Drain on sacrifice"),
    ],
}

TYPE_SYNERGIES: dict[str, list[tuple[str, str]]] = {
    "Artifact": [
        ("artifact.*enters", "Artifact ETB triggers"),
        ("affinity", "Cost reduction"),
        ("metalcraft", "Artifact count matters"),
        ("improvise", "Tap for mana"),
        ("Urza", "Artifact synergy commander"),
    ],
    "Enchantment": [
        ("constellation", "Enchantment ETB triggers"),
        ("enchantress", "Draw on enchantment cast"),
        ("Sythis", "Enchantress value"),
        ("whenever.*enchantment", "Enchantment triggers"),
    ],
    "Instant": [
        ("magecraft", "Spell copy"),
        ("prowess", "Combat boost"),
        ("whenever you cast.*instant", "Instant triggers"),
    ],
    "Sorcery": [
        ("magecraft", "Spell copy"),
        ("prowess", "Combat boost"),
        ("flashback", "Cast again"),
    ],
    "Planeswalker": [
        ("proliferate", "Add loyalty counters"),
        ("Doubling Season", "Double loyalty"),
        ("The Chain Veil", "Extra activations"),
    ],
    "Land": [
        ("landfall", "Land ETB triggers"),
        ("whenever.*land.*enters", "Land triggers"),
        ("Azusa", "Extra land drops"),
    ],
}

THEME_INDICATORS: dict[str, list[str]] = {
    "tokens": ["create.*token", "populate", "whenever.*enters", "token creature"],
    "aristocrats": ["sacrifice", "whenever.*dies", "blood artist", "zulaport"],
    "reanimator": ["graveyard", "return.*battlefield", "reanimate", "unearth"],
    "spellslinger": ["instant", "sorcery", "magecraft", "prowess", "storm"],
    "voltron": ["equipment", "aura", "attach", "equipped creature"],
    "stax": ["sacrifice.*permanent", "each player", "can't", "opponent.*can't"],
    "landfall": ["land.*enters", "landfall", "play.*additional land"],
    "blink": ["exile.*return", "flicker", "enters the battlefield"],
    "counters": ["+1/+1 counter", "proliferate", "counter.*creature"],
    "tribal": [],
    "graveyard": ["mill", "graveyard", "from.*graveyard", "self-mill"],
    "artifacts": ["artifact.*enters", "metalcraft", "affinity", "improvise"],
    "enchantress": ["enchantment", "constellation", "whenever.*enchantment"],
    "control": ["counterspell", "counter target", "destroy.*permanent"],
    "aggro": ["haste", "attack", "combat damage", "first strike"],
}

KNOWN_COMBOS: list[dict[str, Any]] = [
    {
        "id": "twin",
        "cards": [
            ("Splinter Twin", "Enchant creature, tap to copy"),
            ("Deceiver Exarch", "Untap enchanted creature"),
        ],
        "type": "infinite",
        "desc": "Infinite hasty token copies",
        "colors": ["U", "R"],
    },
    {
        "id": "twin-pestermite",
        "cards": [
            ("Splinter Twin", "Enchant creature, tap to copy"),
            ("Pestermite", "Untap enchanted creature"),
        ],
        "type": "infinite",
        "desc": "Infinite hasty token copies",
        "colors": ["U", "R"],
    },
    {
        "id": "thoracle-consult",
        "cards": [
            ("Thassa's Oracle", "Win with empty library"),
            ("Demonic Consultation", "Exile library"),
        ],
        "type": "win",
        "desc": "Win the game with empty library",
        "colors": ["U", "B"],
    },
    {
        "id": "thoracle-pact",
        "cards": [
            ("Thassa's Oracle", "Win with empty library"),
            ("Tainted Pact", "Exile library"),
        ],
        "type": "win",
        "desc": "Win the game with empty library",
        "colors": ["U", "B"],
    },
    {
        "id": "niv-curiosity",
        "cards": [
            ("Niv-Mizzet, Parun", "Draw trigger deals damage"),
            ("Curiosity", "Damage trigger draws"),
        ],
        "type": "infinite",
        "desc": "Infinite draw and damage loop",
        "colors": ["U", "R"],
    },
    {
        "id": "niv-ophidian",
        "cards": [
            ("Niv-Mizzet, Parun", "Draw trigger deals damage"),
            ("Ophidian Eye", "Damage trigger draws"),
        ],
        "type": "infinite",
        "desc": "Infinite draw and damage loop",
        "colors": ["U", "R"],
    },
    {
        "id": "sanguine-exquisite",
        "cards": [
            ("Sanguine Bond", "Life gain causes life loss"),
            ("Exquisite Blood", "Life loss causes life gain"),
        ],
        "type": "infinite",
        "desc": "Infinite life drain loop",
        "colors": ["B"],
    },
    {
        "id": "kiki-conscripts",
        "cards": [
            ("Kiki-Jiki, Mirror Breaker", "Tap to copy creature"),
            ("Zealous Conscripts", "Untaps Kiki-Jiki"),
        ],
        "type": "infinite",
        "desc": "Infinite hasty tokens",
        "colors": ["R"],
    },
    {
        "id": "kiki-felidar",
        "cards": [
            ("Kiki-Jiki, Mirror Breaker", "Tap to copy creature"),
            ("Felidar Guardian", "Blinks Kiki-Jiki"),
        ],
        "type": "infinite",
        "desc": "Infinite hasty tokens",
        "colors": ["R", "W"],
    },
    {
        "id": "mike-trike",
        "cards": [
            ("Mikaeus, the Unhallowed", "Undying + buff"),
            ("Triskelion", "Damage ping + self-kill"),
        ],
        "type": "infinite",
        "desc": "Infinite damage",
        "colors": ["B"],
    },
    {
        "id": "mike-ballista",
        "cards": [
            ("Mikaeus, the Unhallowed", "Undying + buff"),
            ("Walking Ballista", "Damage ping + self-kill"),
        ],
        "type": "infinite",
        "desc": "Infinite damage",
        "colors": ["B"],
    },
    {
        "id": "dramatic-scepter",
        "cards": [
            ("Dramatic Reversal", "Untap all nonlands"),
            ("Isochron Scepter", "Imprint and repeat"),
        ],
        "type": "infinite",
        "desc": "Infinite mana (with 3+ mana from rocks)",
        "colors": ["U"],
    },
    {
        "id": "heliod-ballista",
        "cards": [
            ("Heliod, Sun-Crowned", "Gives lifelink"),
            ("Walking Ballista", "Damage + gain life"),
        ],
        "type": "infinite",
        "desc": "Infinite damage and life",
        "colors": ["W"],
    },
    {
        "id": "devoted-vizier",
        "cards": [
            ("Devoted Druid", "Untap with -1/-1"),
            ("Vizier of Remedies", "Prevents -1/-1 counters"),
        ],
        "type": "infinite",
        "desc": "Infinite green mana",
        "colors": ["G", "W"],
    },
    {
        "id": "peregrine-deadeye",
        "cards": [
            ("Peregrine Drake", "Untap 5 lands on ETB"),
            ("Deadeye Navigator", "Soulbond blink"),
        ],
        "type": "infinite",
        "desc": "Infinite mana",
        "colors": ["U"],
    },
    {
        "id": "palinchron-high-tide",
        "cards": [
            ("Palinchron", "Untap 7 lands on ETB"),
            ("High Tide", "Islands tap for extra mana"),
        ],
        "type": "infinite",
        "desc": "Infinite mana",
        "colors": ["U"],
    },
    {
        "id": "worldgorger-animate",
        "cards": [
            ("Worldgorger Dragon", "Exile all permanents"),
            ("Animate Dead", "Return and re-exile loop"),
        ],
        "type": "infinite",
        "desc": "Infinite mana and ETB triggers",
        "colors": ["B", "R"],
    },
    {
        "id": "basalt-rings",
        "cards": [
            ("Basalt Monolith", "Tap for 3, untap for 3"),
            ("Rings of Brighthearth", "Copy untap ability"),
        ],
        "type": "infinite",
        "desc": "Infinite colorless mana",
        "colors": [],
    },
    {
        "id": "food-chain-eternal",
        "cards": [
            ("Food Chain", "Exile creature for mana"),
            ("Eternal Scourge", "Cast from exile"),
        ],
        "type": "infinite",
        "desc": "Infinite creature mana",
        "colors": ["G"],
    },
    {
        "id": "food-chain-misthollow",
        "cards": [
            ("Food Chain", "Exile creature for mana"),
            ("Misthollow Griffin", "Cast from exile"),
        ],
        "type": "infinite",
        "desc": "Infinite creature mana",
        "colors": ["G", "U"],
    },
    {
        "id": "teferi-knowledge",
        "cards": [
            ("Teferi, Time Raveler", "Opponents cast at sorcery only"),
            ("Knowledge Pool", "Exile and swap spells"),
        ],
        "type": "lock",
        "desc": "Opponents can't cast spells",
        "colors": ["W", "U"],
    },
    {
        "id": "drannith-knowledge",
        "cards": [
            ("Drannith Magistrate", "Can't cast from non-hand"),
            ("Knowledge Pool", "Exile and swap spells"),
        ],
        "type": "lock",
        "desc": "Opponents can't cast spells",
        "colors": ["W"],
    },
    {
        "id": "narset-wheels",
        "cards": [
            ("Narset, Parter of Veils", "Opponents draw only 1"),
            ("Windfall", "Everyone discards and draws"),
        ],
        "type": "value",
        "desc": "One-sided hand refill",
        "colors": ["U"],
    },
    {
        "id": "notion-wheels",
        "cards": [
            ("Notion Thief", "Steal opponent draws"),
            ("Windfall", "Everyone draws = you draw all"),
        ],
        "type": "value",
        "desc": "Draw everyone's cards",
        "colors": ["U", "B"],
    },
    {
        "id": "dauthi-thoracle",
        "cards": [
            ("Dauthi Voidwalker", "Exile opponents' cards"),
            ("Opposition Agent", "Steal tutored cards"),
        ],
        "type": "value",
        "desc": "Deny all opponent resources",
        "colors": ["B"],
    },
]
