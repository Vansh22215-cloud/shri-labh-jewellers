"""The evening dashboard picture (owner 20 Nov: "after market closes I see our dashboard the way I sent you"):
Zerodha-style 'Closed' positions - Closed / In Profit / In Loss counts, Name, Product, Qty, Buy Avg, Sell Avg,
LTP, P&L, Realised P&L - plus the charges, the net result and the practice account's balance underneath."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

BG, ROW, LINE, TXT, DIM = "#000000", "#141414", "#262626", "#e8e8e8", "#9a9a9a"
GREEN, RED, ORANGE = "#5cb85c", "#e05252", "#f0a03c"


def _money(v):
    return f"{v:,.2f}"


def render(rows, path, day, balance=None, start=None, charges=None, net=None, note=""):
    """rows: dicts with name, kind, product, qty, buy_avg, sell_avg, ltp, pnl."""
    n = max(1, len(rows))
    h = 2.2 + 0.75 * n + 1.6
    fig = plt.figure(figsize=(20, h), dpi=100)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 2000)
    ax.set_ylim(0, h * 100)
    ax.axis("off")
    top = h * 100
    prof = sum(1 for r in rows if r["pnl"] > 0)
    loss = sum(1 for r in rows if r["pnl"] < 0)
    y = top - 70
    ax.text(40, y, "Closed", color="white", fontsize=22, va="center", fontweight="bold")
    for x, lab, cnt, col in ((150, "Closed", len(rows), GREEN), (335, "In Profit", prof, TXT), (530, "In Loss", loss, TXT)):
        ax.add_patch(FancyBboxPatch((x, y - 24), 170, 48, boxstyle="round,pad=2,rounding_size=8", ec=LINE if col != GREEN else "#2e5e2e",
                                    fc=BG, lw=1.5))
        ax.text(x + 15, y, lab, color=col, fontsize=17, va="center")
        ax.add_patch(FancyBboxPatch((x + 118, y - 15), 40, 30, boxstyle="round,pad=1,rounding_size=5", ec="none", fc="#2a2a2a"))
        ax.text(x + 138, y, str(cnt), color=col, fontsize=15, va="center", ha="center")
    ax.text(1940, y, f"{day:%a %d %b %Y}  ·  PRACTICE ACCOUNT", color=DIM, fontsize=14, va="center", ha="right")
    hy = y - 85
    ax.add_patch(plt.Rectangle((40, hy - 37), 1902, 74, color="#1b1b1b"))
    cols = [(130, "Name", "left"), (800, "Product", "center"), (1040, "Qty", "right"), (1322, "Buy Avg Price", "right"),
            (1534, "Sell Avg Price", "right"), (1722, "LTP", "right"), (1922, "P&L", "right")]
    for x, lab, ha in cols:
        ax.text(x, hy, lab, color="#cfcfcf", fontsize=16, va="center", ha=ha)
    ry = hy + 1
    for r in rows:
        ry -= 75
        ax.add_patch(plt.Rectangle((40, ry - 37), 1902, 74, color=ROW))
        ax.plot([40, 1942], [ry - 37, ry - 37], color=LINE, lw=1)
        ax.add_patch(FancyBboxPatch((62, ry - 15), 30, 30, boxstyle="round,pad=1,rounding_size=4", ec="none", fc="#5a5a5a"))
        ax.text(77, ry, "C", color="white", fontsize=13, va="center", ha="center")
        t = ax.text(130, ry, r["name"], color="white", fontsize=18, va="center")
        bb = t.get_window_extent(renderer=fig.canvas.get_renderer()).transformed(ax.transData.inverted())
        ax.text(bb.x1 + 10, ry - 3, "NSE", color=DIM, fontsize=11, va="center")
        ax.add_patch(FancyBboxPatch((752, ry - 17), 96, 34, boxstyle="round,pad=1,rounding_size=5", ec="#6b4a16", fc="#2a1e0c"))
        ax.text(800, ry, r.get("product", "Intraday"), color=ORANGE, fontsize=15, va="center", ha="center")
        ax.text(1040, ry, f"{r['qty']}", color=TXT, fontsize=18, va="center", ha="right")
        ax.text(1322, ry, _money(r["buy_avg"]), color=TXT, fontsize=18, va="center", ha="right")
        ax.text(1534, ry, _money(r["sell_avg"]), color=TXT, fontsize=18, va="center", ha="right")
        ax.text(1722, ry, _money(r["ltp"]), color=TXT, fontsize=18, va="center", ha="right")
        ax.text(1922, ry, _money(r["pnl"]), color=GREEN if r["pnl"] >= 0 else RED, fontsize=18, va="center", ha="right")
    if not rows:
        ry -= 75
        ax.text(990, ry, "No trades today", color=DIM, fontsize=18, va="center", ha="center")
    total = sum(r["pnl"] for r in rows)
    fy = ry - 85
    ax.text(105, fy, "⤓  Download as CSV", color=DIM, fontsize=16, va="center")
    ax.text(1560, fy, "Realised P&L:", color=DIM, fontsize=18, va="center", ha="right")
    ax.text(1722, fy, f"₹ {_money(total)}", color=GREEN if total >= 0 else RED, fontsize=19, va="center", ha="right")
    ly = fy - 55
    extra = []
    if charges is not None:
        extra.append(f"Charges ₹{charges:,.2f}")
    if net is not None:
        extra.append(f"Net ₹{net:+,.2f}")
    if balance is not None and start:
        extra.append(f"Balance ₹{balance:,.2f} (started ₹{start:,.0f}, {balance / start * 100 - 100:+.1f}%)")
    if extra:
        ax.text(1922, ly, "   ·   ".join(extra), color=DIM, fontsize=14, va="center", ha="right")
    if note:
        ax.text(40, ly, note, color=DIM, fontsize=13, va="center")
    fig.savefig(path, facecolor=BG)
    plt.close(fig)
    return path
