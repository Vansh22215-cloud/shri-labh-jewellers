"""Implementation audit of the owner's pattern library (required before strategy testing by the library's handoff).
Writes library/IMPLEMENTATION_AUDIT.md and .csv: every catalogue item with status, code reference and limitations."""
import pandas as pd

from .catalog import CANDLE_X, CHART_DETECTORS, DUPLICATE_OF, CHART_MAPPED, LIB, MS_DETECTORS, RULE_VERSION, RULE_VERSION_MS, load
from .features import BLOCKED, INDICATOR_V2, INDICATOR_V2_APPROX, NON_TALIB_IMPL, QUANT_BLOCKED_CATS, QUANT_ELSEWHERE, QUANT_IMPL


def build():
    import talib
    tl = set(talib.get_functions())
    rows = []
    for key, it in load().items():
        kind, iid = it["_type"], it["id"]
        status, ref, note = "not_yet_implemented", "", ""
        if key in DUPLICATE_OF:
            rows.append({"type": kind, "id": iid, "name": it["name"], "status": "implemented",
                         "code_reference": f"same rule as family {DUPLICATE_OF[key]}", "rule_version": "cat-v2",
                         "notes": "identical definition: merged so it is not counted as a separate test"})
            continue
        if kind == "candlestick":
            code = it.get("canonical_code")
            if code and code in tl:
                d = it.get("typical_direction")
                if d in ("bullish", "both", "neutral"):
                    status, ref = "implemented", f"swing/catalog.py:signals -> family cdl_{iid} (TA-Lib {code})"
                    note = "entry = bullish TA-Lib reading + close above 200-day average"
                else:
                    status, ref = "implemented_detector_only", f"TA-Lib {code} via swing/catalog.py:cdl_panel"
                    note = "bearish pattern: the system is long-only (delivery), so it is not an entry rule"
            elif iid in CANDLE_X:
                status, ref = "implemented", f"swing/catalog.py:candle_x('{iid}') -> family cdx_{iid}"
                note = "adaptive body/ATR heuristic (library v2 variant), rule cat-v2"
            elif iid in ("inside_bar",):
                status, ref = "implemented", "swing/families.py:inside_day"
            elif iid in ("outside_bar",):
                status, ref = "implemented", "swing/catalog.py:chart_signal('outside_bar')"
            elif iid == "tweezer_bottom":
                note = "non-TA-Lib variant; to be added as a versioned rule"
            else:
                note = "non-TA-Lib/community variant; to be added as a versioned rule" if it.get("typical_direction") != "bearish" \
                    else "bearish; long-only system"
                status = "not_yet_implemented" if it.get("typical_direction") != "bearish" else "not_applicable_to_strategy"
        elif kind == "chart_pattern":
            bias = str(it.get("typical_bias", ""))
            if iid in CHART_DETECTORS:
                status, ref = "implemented", f"swing/catalog.py:chart_signal('{iid}') -> family cp_{iid}"
                note = "pivot engine L=3/R=3 (confirmed), ATR tolerances from the catalogue defaults" \
                    if iid not in ("breakout_retest", "false_breakout", "outside_bar", "pin_bar_rejection", "gap_breakaway",
                                   "gap_runaway", "wyckoff_spring", "island_reversal") else "rolling-window/price-action definition"
            elif iid in CHART_MAPPED:
                status, ref = "implemented", f"family {CHART_MAPPED[iid]} (swing/patterns.py or families.py)"
                note = "earlier heuristic definition, kept as its own version"
            elif bias.startswith(("bearish", "often_bearish", "usually_bearish")) or iid in ("head_and_shoulders_top",
                                                                                            "double_top", "triple_top"):
                status, note = "not_applicable_to_strategy", "bearish structure; long-only delivery system (could be an exit filter later)"
            elif it.get("category") in ("harmonic", "wave_theory"):
                note = "highly subjective; needs a Fibonacci-ratio pivot engine (planned on top of the pivot engine)"
            elif it.get("category") in ("wyckoff",):
                note = "multi-phase schematic; only the 'spring' event is implemented so far"
            else:
                note = "planned on top of the pivot engine"
        elif kind == "market_structure":
            bias = it.get("typical_bias")
            needs = " ".join(map(str, it.get("required_inputs", []))).lower()
            if iid in MS_DETECTORS:
                status, ref = "implemented", f"swing/catalog.py:ms_signal('{iid}') -> family ms_{iid}"
                note = "daily completed bars, confirmed pivots (L=3/R=3); ICT/SMC-style definitions are one versioned convention"
            elif iid in ("higher_high",):
                status, ref, note = "implemented_detector_only", "swing/catalog.py:pivots", "structure label used inside BOS/CHoCH"
            elif any(k in needs for k in ("order_book", "trades", "profile", "tpo", "auction", "bid", "ask")) or \
                    it.get("category") in ("auction_profile", "order_flow", "microstructure", "volume_profile"):
                status, note = "blocked_by_data", "needs intraday profile / order-flow data (not available free)"
            elif bias == "bearish":
                status, note = "not_applicable_to_strategy", "bearish event; long-only delivery system"
            elif it.get("category") in ("session", "intraday_session"):
                status, note = "blocked_by_data", "intraday-session event; daily system (5-minute data only for today)"
            else:
                note = "planned on top of the pivot engine"
        elif kind == "quant_feature":
            if iid in QUANT_IMPL:
                status, ref, note = "implemented", f"swing/features.py:quant_feature('{iid}')", "feature (not an entry rule)"
            elif iid in QUANT_ELSEWHERE:
                status, ref = "implemented", QUANT_ELSEWHERE[iid]
            elif it.get("category") in QUANT_BLOCKED_CATS:
                status, note = "blocked_by_data", QUANT_BLOCKED_CATS[it["category"]]
            else:
                note = "planned"
        else:   # indicator
            code = it.get("canonical_code")
            if code and code in tl:
                status, ref = "implemented", f"TA-Lib {code} via swing/features.py:talib_feature"
                note = "available as a feature (not an entry rule by itself)"
            elif iid in NON_TALIB_IMPL:
                status, ref = "implemented", NON_TALIB_IMPL[iid]
            elif iid in INDICATOR_V2:
                status, ref = "implemented", f"swing/features.py:indicator_v2('{iid}')"
                note = INDICATOR_V2_APPROX.get(iid, "daily completed bars (feature, not an entry rule)")
            elif iid == "bos_choch":
                status, ref = "implemented", "swing/catalog.py:ms_signal (break_of_structure / change_of_character)"
            elif it.get("category") in ("options_analytics", "market_microstructure", "derivatives_market", "volume_profile"):
                status, note = "blocked_by_data", {"options_analytics": "needs option-chain history (IV/OI by strike)",
                                                   "market_microstructure": "needs tick / order-book data",
                                                   "derivatives_market": "needs futures / OI history",
                                                   "volume_profile": "needs intraday volume-at-price data"}[it["category"]]
            elif it.get("category") == "market_breadth":
                status, note = "blocked_by_data", "needs exchange-wide advance/decline volume history (top-500 breadth is in quant features)"
            elif iid in BLOCKED:
                status, note = "blocked_by_data", BLOCKED[iid]
            elif code:
                note = f"canonical code {code} not in installed TA-Lib {talib.__version__}"
            else:
                note = "planned (divergence/zigzag/BOS-CHOCH need the pivot engine)"
        rows.append({"type": kind, "id": iid, "name": it["name"], "status": status, "code_reference": ref,
                     "rule_version": (RULE_VERSION_MS if kind in ("market_structure", "quant_feature") else RULE_VERSION)
                     if status.startswith("implemented") else "", "notes": note})
    df = pd.DataFrame(rows).sort_values(["type", "status", "id"])
    df.to_csv(LIB.parent / "IMPLEMENTATION_AUDIT.csv", index=False)
    counts = df.groupby(["type", "status"]).size().unstack(fill_value=0)
    import json
    ver = json.loads((LIB / "manifest.json").read_text()).get("version", "?")
    md = [f"# Implementation audit - Market Pattern & Technical Research Library v{ver} ({len(df)} records)", "",
          "Generated by swing/audit.py. Detectors existing does NOT mean they are profitable: every entry rule is tested",
          "by the idea factory (walk-forward, costs, multiple-testing margin) before it could ever give tips.", "",
          "## Summary", "", counts.to_markdown(), "", "## Every item", "",
          df.to_markdown(index=False)]
    (LIB.parent / "IMPLEMENTATION_AUDIT.md").write_text("\n".join(md), encoding="utf-8")
    return counts
