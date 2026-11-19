from swing import bot


def test_capital_show_set_and_guard(tmp_path, monkeypatch):
    p = tmp_path / "settings.yaml"
    p.write_text("# x\ncapital: 51000\nkill_switch: false\n")
    monkeypatch.setattr(bot, "ROOT", tmp_path)
    import swing.config as c
    monkeypatch.setattr(c, "load_settings", lambda: {"capital": float(p.read_text().split("capital: ")[1].split()[0])})
    assert "51,000" in bot.capital_command("/capital")
    assert "between" in bot.capital_command("/capital 500")
    assert "big change" in bot.capital_command("/capital 200000") and "51000" in p.read_text()
    r = bot.capital_command("/capital 60,000")
    assert "60,000" in r and "capital: 60000" in p.read_text() and "kill_switch: false" in p.read_text()
    assert "capital: 150000" in (bot.capital_command("/capital 150000 sure") and p.read_text())
