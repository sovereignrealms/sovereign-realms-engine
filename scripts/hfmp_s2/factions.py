FACTION_DEFS = [
    {
        "id": 0,
        "name": "Frontier Wilds",
        "color": (136, 146, 118, 255),
        "role": "neutral environment",
        "signature_units": ["Ridge Doe", "Brush Deer", "Scrap Chicken"],
    },
    {
        "id": 1,
        "name": "Sentinel Compact",
        "color": (108, 132, 220, 255),
        "role": "disciplined frontier command",
        "signature_units": [
            "Captain Rowan - rally radius bonus",
            "Shield Knight - brace stance",
            "Trail Ranger - faster fog reveal",
        ],
    },
    {
        "id": 2,
        "name": "Rime Covenant",
        "color": (178, 108, 96, 255),
        "role": "elite heavy assault host",
        "signature_units": [
            "Line Breaker - charge impact bonus",
            "War Banner Bearer - morale aura",
            "Iron Vanguard - armour spike under focus fire",
        ],
    },
    {
        "id": 3,
        "name": "Ashen Raiders",
        "color": (168, 132, 76, 255),
        "role": "fast pressure and flanking faction",
        "signature_units": [
            "Dust Scout - wider sight arc",
            "Hook Duelist - pursuit bonus",
            "Marauder Chief - kill-chain damage ramp",
        ],
    },
]


def apply():
    import pf

    for faction in FACTION_DEFS:
        pf.update_faction(faction["id"], faction["name"], faction["color"])


def visible_faction_names():
    return [faction["name"] for faction in FACTION_DEFS if faction["id"] != 0]
