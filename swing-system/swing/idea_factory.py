"""Idea factory: keeps the self-improvement loop going WITHOUT Claude.

When fewer than 3 untested ideas remain in IMPROVEMENTS.md, it writes 2 new ones (dated today, so the reason is on
record BEFORE the next run tests them). Ideas come from a fixed menu of economically sensible single changes, each
with its reason; ones already tried (same parameters) are skipped. Testing and promotion follow weekly.test_proposal:
beat the current strategy in most walk-forward years, higher CAGR, worst fall not deeper by > 2 points; one change
per run; every idea counts as a tried variant (the bar for 'validated' rises with it).
"""
import json
from datetime import date

from . import validate
from .config import load_settings, load_strategy
from .weekly import IMPROVEMENTS, parse_proposals, tips_strategy

MENU = [
    ({"stop_atr_mult": 2.5}, "a slightly tighter stop cuts the size of losing trades while staying outside daily noise"),
    ({"stop_atr_mult": 3.5}, "a slightly wider stop avoids being shaken out of trends by normal volatility"),
    ({"max_hold_days": 15}, "shorter holds free capital faster for fresh signals when trends fade quickly"),
    ({"max_hold_days": 35}, "longer holds give drifting trends more time to reach targets"),
    ({"target1_r": 1.5}, "a nearer first target banks partial profit more often"),
    ({"target2_r": 3.0}, "a nearer final target converts more winners before the time limit"),
    ({"exit_style": "trail", "trail_atr_mult": 3.0}, "a trailing stop lets the few big trends run instead of capping them"),
    ({"min_rs_filter": 50}, "buying only stocks stronger than the average stock favours leaders"),
    ({"min_mom12_rank": 0.5}, "requiring above-average 12-month momentum favours long-term winners"),
    ({"max_atr_pct": 5.0}, "skipping the most volatile stocks reduces gap losses through stops"),
    ({"min_volume_mult": 1.0}, "requiring at least average volume on the signal day filters thin moves"),
    ({"use_regime_filter": True}, "avoiding new trades when the market is below its 200-day average cuts bear-market losses"),
    ({"max_open_positions": 3}, "fewer, best-ranked positions concentrate on the strongest signals"),
    ({"max_open_positions": 5}, "one more position spreads risk across more independent trades"),
    ({"max_per_industry": 2}, "at most two trades per industry limits sector-wide drawdowns"),
    ({"skip_if_us_drop_pct": 2.0}, "skipping entries after a >2% overnight US fall avoids buying into global risk-off opens"),
    ({"min_fii_long_pct": 25}, "skipping entries when FIIs are extremely short in index futures avoids hostile markets"),
]


def family_ideas():
    """Every pattern/method family as a candidate entry rule with the current strategy's exits."""
    from .families import FAMILIES, LIBRARY_FAMILIES, SHORT_FAMILIES
    from .patterns import DESCRIPTIONS, PATTERN_FAMILIES
    lib_desc = {"minervini_vcp": "Minervini trend template + volatility contraction breakout",
                "weinstein_stage2": "Weinstein stage-2 breakout above a rising 30-week average",
                "darvas_box": "Darvas box breakout near the 52-week high", "momentum_12_1": "monthly 12-1 momentum leaders",
                "high52_rank": "stocks closest to their 52-week high", "pead": "post-earnings drift after strong results gaps",
                "sector_rotation": "leaders of the strongest sectors", "connors_pctb": "sharp dips below the lower Bollinger band in uptrends"}
    out = [({"family": f}, f"a well-known setup ({DESCRIPTIONS[f]}) may time entries better than the current rule")
           for f in PATTERN_FAMILIES]
    out += [({"family": f}, f"a published method ({lib_desc[f]}) may beat the current entry rule with the same exits")
            for f in LIBRARY_FAMILIES]
    out += [({"family": f}, "an alternative core entry rule may beat the current one with the same exits")
            for f in FAMILIES + SHORT_FAMILIES]
    try:   # the owner's pattern library: TA-Lib candles and pivot-confirmed chart patterns
        from .catalog import families as cat_families, get
        for f in cat_families():
            kind = {"cdl": "candlestick", "cdx": "candlestick", "cp": "chart_pattern", "ms": "market_structure"}[f.split("_", 1)[0]]
            it = get(kind, f.split("_", 1)[1])
            out.append(({"family": f}, f"the {it['name']} pattern from the owner's pattern library may time entries "
                                       f"better than the current rule"))
    except Exception:
        pass
    return out


def combo_ideas():
    """Second wave: each filter/exit change from MENU combined with every family (thousands of candidates)."""
    fams = [o["family"] for o, _ in family_ideas()]
    return [({"family": f, **ov}, f"{why} - applied to the {f} entry rule") for f in fams for ov, why in MENU]


def top_up(min_open=3, n_new=2):
    props = parse_proposals()
    open_ = [p for p in props if p.get("status") == "proposed"]
    if len(open_) >= min_open:
        return []
    s = load_settings()
    base_name, _ = tips_strategy(s)
    base = load_strategy(base_name)
    tried = set(json.loads(validate.REGISTRY.read_text()).keys()) if validate.REGISTRY.exists() else set()
    used = {p.get("overrides") for p in props}
    ids = [int(p["id"][1:]) for p in props if str(p.get("id", "")).startswith("A") and p["id"][1:].isdigit()]
    nxt = max(ids, default=0) + 1
    added = []
    for ov, why in family_ideas() + MENU + combo_ideas():
        if len(added) >= n_new:
            break
        if all(base.get(k) == v for k, v in ov.items()):
            continue                                    # already the current setting
        cand = dict(base, **ov, name="x")
        if validate.params_hash(cand) in tried or json.dumps(ov) in used:
            continue
        block = (f"\n```proposal\nid: A{nxt}\nstatus: proposed\nwritten: {date.today()}\n"
                 f"reason: (idea factory) For {base_name}: {why}.\noverrides: {json.dumps(ov)}\n```\n")
        with open(IMPROVEMENTS, "a", encoding="utf-8") as f:
            f.write(block)
        added.append(f"A{nxt} {json.dumps(ov)}")
        nxt += 1
    return added
