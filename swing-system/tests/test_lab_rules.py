import json

from swing import lab_rules, vantage


def _setup(tmp_path, monkeypatch, rules):
    f = tmp_path / "lab_rules.json"
    f.write_text(json.dumps({"rules": rules, "runs": []}))
    monkeypatch.setattr(lab_rules, "RULES_F", f)
    lab_rules._CACHE.clear()
    return f


RULE = {"id": "LAB-AB12", "name": "skip price_rs 980..", "kind": "skip", "col": "price_rs", "val": [980.0, float("inf")],
        "num": True, "status": "proposed", "plain": "Skip VANTAGE buys when the share price is above 980"}


def test_only_approved_rules_act_and_owner_controls_status(tmp_path, monkeypatch):
    f = _setup(tmp_path, monkeypatch, [dict(RULE)])
    monkeypatch.setattr(lab_rules, "_features", lambda sym, b, day: {"price_rs": 1500.0})
    assert lab_rules.decision("X", {"signal": "2026-11-20"}, "2026-11-20") == (None, "")      # proposed: no effect
    assert "approved" in lab_rules.set_status("lab-ab12", "approved")
    lab_rules._CACHE.clear()
    assert lab_rules.decision("X", {"signal": "2026-11-20"}, "2026-11-20") == ("skip", "LAB-AB12")
    assert vantage.lab_skip("X", {"signal": "2026-11-21"}, "2026-11-21") == "LAB-AB12"
    assert "switched off" in lab_rules.set_status("LAB-AB12", "declined")
    lab_rules._CACHE.clear()
    assert lab_rules.decision("X", {"signal": "2026-11-22"}, "2026-11-22") == (None, "")
    assert json.loads(f.read_text())["rules"][0]["status"] == "declined"
    assert "No research rule" in lab_rules.set_status("LAB-0000", "approved")


def test_half_rule_halves_quantity_and_bad_facts_never_block(tmp_path, monkeypatch):
    r = dict(RULE, kind="half", status="approved")
    _setup(tmp_path, monkeypatch, [r])
    monkeypatch.setattr(lab_rules, "_features", lambda sym, b, day: {"price_rs": 1500.0})
    monkeypatch.setattr(vantage, "results_line", lambda sym, day: ("", 1.0))
    seen = {}
    monkeypatch.setattr(vantage, "qty_line", lambda e, st, scale=1.0: seen.setdefault("scale", scale) and "")
    line = vantage._res_and_qty("X", 1500.0, 1400.0, "2026-11-20", {"signal": "2026-11-20"})
    assert seen["scale"] == 0.5 and "LAB-AB12" in line
    lab_rules._CACHE.clear()
    monkeypatch.setattr(lab_rules, "_features", lambda sym, b, day: (_ for _ in ()).throw(ValueError()))
    assert lab_rules.decision("X", {"signal": "2026-11-23"}, "2026-11-23") == (None, "")


def test_bot_routes_lab_ids(tmp_path, monkeypatch):
    import inspect
    from swing import bot
    src = inspect.getsource(bot)
    assert 'startswith("LAB-")' in src and '"/decline"' in src and '"/research"' in src
