def test_menu_has_reasons_and_overrides():
    from swing.idea_factory import MENU
    assert len(MENU) >= 10 and all(isinstance(o, dict) and len(r) > 20 for o, r in MENU)
