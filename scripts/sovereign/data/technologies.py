TECHNOLOGIES = {
    "advance_to_rising": {
        "display_name": "Advance to Rising Age",
        "cost": {"food": 500},
        "research_time_sec": 130,
        "requires_age": "founding",
        "effects": [{"type": "set_age", "age": "rising"}],
    },
    "infantry_drills": {
        "display_name": "Infantry Drills",
        "cost": {"food": 120, "gold": 40},
        "research_time_sec": 45,
        "requires_age": "founding",
        "effects": [{"type": "strategy_tag", "tag": "infantry_pressure"}],
    },
    "settlement_logistics": {
        "display_name": "Settlement Logistics",
        "cost": {"food": 80, "wood": 160},
        "research_time_sec": 55,
        "requires_age": "founding",
        "effects": [{"type": "strategy_tag", "tag": "balanced_expansion"}],
    },
    "ranger_fletching": {
        "display_name": "Ranger Fletching",
        "cost": {"wood": 100, "gold": 80},
        "research_time_sec": 50,
        "requires_age": "founding",
        "effects": [{"type": "strategy_tag", "tag": "archer_pressure"}],
    },
}
