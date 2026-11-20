"""Test the strategies the owner queued (/test NAME) on Kite candles of every NSE stock, then the Learner report;
the summary goes to Telegram. Every message starts with the data used (Kite only)."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if __name__ == "__main__":
    from swing.config import load_settings
    from swing.daemon import TEST_QUEUE
    from swing import backtest, learner, telegram, candles
    try:
        q = json.loads(TEST_QUEUE.read_text())
    except Exception:
        q = []
    if not q:
        sys.exit(0)
    from swing.strategy import load_all
    S = load_all()
    ready = [n for n in q if n not in S or candles.complete(S[n].interval)]
    name = ready[0] if ready else q[0]
    st = S.get(name)
    s = load_settings()
    if st is None:
        msg = f"⚠️ Test {name}: no such strategy."
    elif not candles.complete(st.interval):
        p = candles.progress()
        msg = (f"⏳ Test {name}: Kite {st.interval} history is not complete yet ({p.get(st.interval)} stocks) - the test "
               "waits so it never runs on part of the data. It starts by itself when the download is done.")
        q = q[1:] + [name]                      # back of the queue
        TEST_QUEUE.write_text(json.dumps(q))
        telegram.send(s, msg, label="test result")
        sys.exit(0)
    else:
        T, data = backtest.run(name)
        learner.report(name, T, data)
        a = backtest.stats(T) or {}
        acc = backtest.account(T) if len(T) else None
        msg = (f"🧪 Test {name}\n{backtest.data_line(data)}\n\n"
               f"Trades {a.get('trades', 0):,} · won {a.get('win_pct', '-')}% · average {a.get('avg_net_pct', 0):+.2f}% after costs"
               f" · stop hit {a.get('stop_hit_pct', '-')}% · target hit {a.get('target_hit_pct', '-')}%"
               + (f"\nAccount ₹{acc['start']:,.0f} → ₹{acc['end']:,.0f} in {acc['years']} years ({acc['per_year_pct']:+.1f}%/yr), "
                  f"worst fall {acc['worst_fall_pct']}%" if acc else "")
               + f"\n\nFull report: results/tests/{name}.md · Learner: /learn {name}\nGoes live only if you send /approve {name}.")
    TEST_QUEUE.write_text(json.dumps([x for x in q if x != name]))
    telegram.send(s, msg, label="test result")
    try:
        from swing.ci_save import save
        save(f"test {name}")
    except Exception as e:
        print("save failed:", e)
