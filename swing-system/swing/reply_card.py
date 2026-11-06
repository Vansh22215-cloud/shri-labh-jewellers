"""One clear, same-every-time reply for anything forwarded to the bot (stock tip, index/forex/gold/crypto view or
setup, chart picture). Written for a quick read on a phone:

  1. the ANSWER first, in one line, in plain words (not jargon)
  2. what the tip says  ->  where the price is now
  3. WHY it could work / WHY it could fail (each point is a reason, not a number dump)
  4. the odds as a picture (out of 100 similar cases ...)
  5. the plan, only if you still take it (entry / exit-if-wrong / target / max quantity)
  6. BOTTOM LINE: what to do and why, with the calm reminder that skipping costs nothing
Telegram HTML; every outside text is escaped.
"""
import html
import re

from .config import DISCLAIMER

VERDICT = {   # verdict -> (icon, headline word, one-line meaning)
    "GOOD": ("🟢", "WORTH CONSIDERING", "the numbers lean in its favour"),
    "NEUTRAL": ("🔵", "COIN FLIP", "no real edge either way"),
    "RISKY": ("🟡", "RISKY", "the odds are not on your side"),
    "AVOID": ("🔴", "SKIP IT", "this one is more likely to lose than win"),
    "UNKNOWN": ("⚪", "CAN'T JUDGE YET", "something important is missing"),
}
HYPE = r"\b(SURE ?SHOT|JACKPOT|100 ?%|GUARANTEED?|MULTI ?BAGGER|OPERATOR|BIG NEWS|DON'?T MISS|LAST CHANCE|ROCKET|" \
       r"BLAST|FIXED (?:PROFIT|RETURN)|ZERO RISK|NO RISK|DOUBLE YOUR|INSIDE ?(?:R|INFO))\b"


def E(x):
    return html.escape(str(x), quote=False)


def hype_words(raw):
    """Sales-pitch words in the forwarded message (a warning sign, explained to the owner)."""
    found = sorted({m.group(0).title() for m in re.finditer(HYPE, str(raw).upper())})
    if not found:
        return None
    return (f"The message uses hype words ({', '.join(found[:3])}). Real analysts never promise results - "
            "this language is used to rush you into acting before thinking.")


def odds_bar(p, need):
    """'▓▓▓▓▓░░░░░  48 out of 100 (need 50)'"""
    if p is None:
        return None
    full = int(round(p / 10))
    bar = "▓" * full + "░" * (10 - full)
    verdict = "✅ enough" if need is not None and p >= need else "❌ not enough" if need is not None else ""
    return f"{bar}  {p:.0f} out of 100" + (f" · need {need:.0f} to make money {verdict}" if need is not None else "")


def fmt(x):
    if x is None:
        return "n/a"
    x = float(x)
    return f"{x:,.5f}".rstrip("0").rstrip(".") if abs(x) < 10 else f"{x:,.2f}" if abs(x) < 10000 else f"{x:,.0f}"


def bottom_line(verdict, pros, cons, p=None, need=None, missing=None):
    top_con = cons[0] if cons else None
    top_pro = pros[0] if pros else None
    if verdict == "UNKNOWN":
        return f"I can't give an honest answer yet: {missing or 'key information is missing'}. Don't act on it until it can be checked."
    if verdict == "AVOID":
        return ("Skip it. Main reason: " + (_lc(top_con) if top_con else "the numbers do not add up") +
                ". Missing a trade costs you nothing; a bad trade costs real money.")
    if verdict == "RISKY":
        why = _lc(top_con) if top_con else "the odds are not on your side"
        return (f"Not a good bet as it stands - {why}. If you still want it, use only a small quantity and the "
                "exit-if-wrong level below, no exceptions.")
    if verdict == "NEUTRAL":
        odds = f" (about {p:.0f} in 100 worked, {need:.0f} needed)" if p is not None and need is not None else ""
        return (f"It's close to a coin flip{odds}. No real edge, so waiting costs nothing - there is always "
                "another trade.")
    stop_fail = f"about {100 - p:.0f} in 100" if p is not None else "some"
    return ("The numbers lean in its favour" + (f" - {_lc(top_pro)}" if top_pro else "") + ". Still, "
            f"{stop_fail} similar setups failed, so respect the exit-if-wrong level and the quantity limit.")


def _lc(s):
    s = str(s).rstrip(".")
    return s[:1].lower() + s[1:] if s[:2] != s[:2].upper() else s


def pattern_points(own, side):
    """System's own pattern scan -> (pros, cons) in plain words, for the side of the call."""
    if not own:
        return [], []
    fired, candles = own
    pros, cons = [], []
    if fired:
        names = ", ".join(fired[:4])
        if side == "buy":
            pros.append(f"On the daily chart, my own pattern scan of real prices found {len(fired)} bullish setup(s) "
                        f"in the last 3 days ({names}) - the bigger picture supports a rise.")
        else:
            cons.append(f"On the daily chart, my own pattern scan found {len(fired)} bullish setup(s) in the last 3 days "
                        f"({names}) - that works against a sell call.")
    elif side == "buy":
        cons.append("On the daily chart, my own pattern scan found no bullish setup in the last 3 days - the "
                    "bigger picture does not confirm the call yet.")
    bull = [c for c in candles if c.startswith("bullish ")]
    bear = [c for c in candles if c.startswith("bearish ")]
    if bull:
        (pros if side == "buy" else cons).append("Today's daily candle looks positive (" + ", ".join(bull[:2]) + ").")
    if bear:
        (cons if side == "buy" else pros).append("Today's daily candle looks negative (" + ", ".join(bear[:2]) + ").")
    return pros, cons


def build(verdict, title, said=None, now=None, pros=(), cons=(), info=(), p=None, need=None,
          plan=None, record=None, tracking=False, source=None, raw=None, missing=None, picture=None):
    """plan: {'side','entry','stop','target','rr','qty','risk_rs','unit'}"""
    icon, word, meaning = VERDICT.get(verdict, VERDICT["UNKNOWN"])
    pros, cons = list(pros), list(cons)
    hw = hype_words(raw or "")
    if hw:
        cons.append(hw)
    L = [f"{icon} <b>{word}</b> - {meaning}", f"<i>{E(title)}" + (f" · from {E(source)}" if source else "") + "</i>"]
    if picture:
        L += ["", "🖼 <b>What I read on the picture</b>"] + [f"• {E(x)}" for x in picture]
    if said:
        L += ["", "🗣 <b>What the tip says</b>", E(said)]
    if now:
        L += ["", "📍 <b>Where the price is now</b>", E(now)]
    if pros:
        L += ["", "✅ <b>Why it could work</b>"] + [f"• {E(x)}" for x in pros[:5]]
    if cons:
        L += ["", "⚠️ <b>Why it could fail</b>"] + [f"• {E(x)}" for x in cons[:6]]
    ob = odds_bar(p, need)
    if ob:
        L += ["", "📊 <b>The odds</b> (similar past moves of this same instrument)", f"<code>{ob}</code>"]
    if info:
        L += ["", "ℹ️ <b>Good to know</b>"] + [f"• {E(x)}" for x in info[:4]]
    if plan and plan.get("stop") and verdict not in ("UNKNOWN", "AVOID"):
        side = plan.get("side", "buy")
        rows = [f"{'Buy' if side == 'buy' else 'Sell'} near  {fmt(plan.get('entry'))}",
                f"Exit if wrong {fmt(plan.get('stop'))}  ({'falls below' if side == 'buy' else 'rises above'})",
                f"Target       {fmt(plan.get('target'))}"]
        if plan.get("rr"):
            rows.append(f"Win/lose     you aim to make {plan['rr']:.1f}x what you risk")
        if plan.get("qty"):
            rows.append(f"Max quantity {plan['qty']} {plan.get('unit', 'shares')} "
                        f"(about ₹{plan.get('risk_rs', 0):,.0f} lost if wrong = 1% of capital)")
        L += ["", "🎯 <b>The plan - only if you still take it</b>", "<pre>" + E("\n".join(rows)) + "</pre>"]
    L += ["", "🧠 <b>Bottom line</b>", E(bottom_line(verdict, pros, cons, p, need, missing))]
    if record:
        L += ["", "📒 " + E(record)]
    if tracking:
        L.append("⏳ I'm tracking it and will message you when it's right ✅, wrong ❌ or runs out of time ⌛.")
    L += ["", f"<i>{E(DISCLAIMER)}</i>"]
    return "\n".join(L)
