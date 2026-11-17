#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test : acheter tout de suite et laisser le bot gérer la sortie, est-ce mieux qu'attendre son signal ?

Pour chaque crypto, on lance le bot à 16 dates de départ différentes (un mois d'écart), pendant 6 mois :
  - Bot actuel        : attend un signal d'achat avant d'entrer
  - Entrée immédiate  : achète le premier jour, puis le bot décide quand vendre et quand racheter
  - Acheter et garder : achète le premier jour et ne vend jamais
Les deux versions du bot sont testées avec et sans le filtre de fond 100 jours.
Écrit le résultat dans ENTREE.md. Lancé à la main depuis l'onglet Actions de GitHub.
"""
import os
from datetime import datetime, timezone

import bot

COINS = ["ETH", "SOL", "BTC", "XRP"]
FEE = 0.40
WARM = 100
WIN = 182


def backtest(candles, cfg, taker, trade_from, start_long=False, trend=None):
    """Même logique que le bot. start_long : achète à l'ouverture qui suit trade_from, sans attendre de signal."""
    n = len(candles)
    closes = [c[4] for c in candles]
    fast = bot.sma_series(closes, cfg["fast"])
    slow = bot.sma_series(closes, cfg["slow"])
    trend_s = bot.sma_series(closes, trend) if trend else None
    slip, stop, gap = cfg["slippage_pct"] / 100.0, cfg["stop_loss_pct"] / 100.0, cfg["min_gap_pct"]
    st = {"cash": float(cfg["budget"]), "eth": 0.0, "entry": None, "cost": 0.0, "cool": 10 ** 9}
    trips, equity, pending, armed = [], [], None, None

    def buy(price):
        qty = st["cash"] / (price * (1 + taker))
        st["cost"] = st["cash"]
        st["cash"], st["eth"], st["entry"] = 0.0, qty, price

    def sell(price):
        net = st["eth"] * price * (1 - taker)
        trips.append(net - st["cost"])
        st["cash"] += net
        st["eth"], st["entry"], st["cool"] = 0.0, None, 0

    for j in range(n):
        o, l, c = candles[j][1], candles[j][3], candles[j][4]
        if pending == "buy" and st["eth"] == 0:
            buy(o * (1 + slip))
        elif pending == "sell" and st["eth"] > 0:
            sell(o * (1 - slip))
        pending = None
        if st["eth"] > 0 and l <= st["entry"] * (1 - stop):
            sell(min(o, st["entry"] * (1 - stop)) * (1 - slip))
        equity.append(st["cash"] + st["eth"] * c)
        if j == trade_from and start_long:
            pending, armed = "buy", True
        elif j >= trade_from and fast[j] is not None and slow[j] is not None:
            cur = st["eth"] > 0
            want = bot.want_long(fast[j], slow[j], cur, gap)
            if not cur:
                if armed is None:
                    armed = not want
                if not want:
                    armed = True
                elif (not armed) or st["cool"] < cfg["cooldown_bars"]:
                    want = False
                if want and trend_s is not None:
                    want = trend_s[j] is not None and c > trend_s[j]
            if want and st["eth"] == 0:
                pending = "buy"
            elif (not want) and st["eth"] > 0:
                pending = "sell"
        st["cool"] += 1
    final = st["cash"] + st["eth"] * closes[-1] * (1 - taker)
    peak, dd = equity[trade_from], 0.0
    for v in equity[trade_from:]:
        peak = max(peak, v)
        dd = max(dd, (peak - v) / peak)
    return {"ret": (final / cfg["budget"] - 1) * 100, "dd": dd * 100, "trips": len(trips)}


def hold(candles, start, end):
    f, s = FEE / 100.0, 0.0005
    seg = candles[start + 1:end]
    eq = [b[4] for b in seg]
    peak, dd = eq[0], 0.0
    for v in eq:
        peak = max(peak, v)
        dd = max(dd, (peak - v) / peak)
    ret = (seg[-1][4] * (1 - s) * (1 - f) / (seg[0][1] * (1 + s) * (1 + f)) - 1) * 100
    return {"ret": ret, "dd": dd * 100, "trips": 0}


VARIANTS = [
    ("Acheter et garder", None),
    ("Bot actuel (attend le signal)", {"start_long": False}),
    ("Entrée immédiate", {"start_long": True}),
    ("Bot avec filtre 100 j (attend le signal)", {"start_long": False, "trend": 100}),
    ("Entrée immédiate + filtre 100 j", {"start_long": True, "trend": 100}),
]


def run_windows(candles, cfg):
    res = {name: [] for name, _ in VARIANTS}
    starts = list(range(WARM, len(candles) - WIN + 1, 30))
    for st in starts:
        for name, opts in VARIANTS:
            if opts is None:
                res[name].append(hold(candles, st, st + WIN))
            else:
                seg = candles[st - WARM:st + WIN]
                res[name].append(backtest(seg, cfg, FEE / 100.0, WARM - 1, **opts))
    return res, [candles[s][0] for s in starts]


def pct(x):
    return f"{x:+.0f} %".replace("-", "−")


def median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


def main():
    cfg = bot.load_config()
    ex = bot.make_exchange(False)
    ex.load_markets()
    md = ["# Acheter tout de suite ou attendre le signal du bot ?\n",
          f"Calculé le {datetime.now(timezone.utc).strftime('%Y-%m-%d')} avec les vrais prix de Kraken, "
          f"frais de {str(FEE).replace('.', ',')} % par transaction inclus. Pour chaque crypto, le bot est lancé "
          "à des dates différentes (un mois d'écart) et tourne 6 mois. On regarde ce qui se passe selon le jour où tu commences.\n",
          "- **Entrée immédiate** : achète le premier jour, peu importe la tendance. Ensuite, le bot vend et rachète selon ses règles habituelles.",
          "- **Bot actuel** : reste en dollars tant qu'il n'a pas de signal d'achat.\n"]
    verdict = []
    for base in COINS:
        sym = next((f"{base}/{q}" for q in ("CAD", "USD") if f"{base}/{q}" in ex.markets), None)
        if not sym:
            continue
        candles = ex.fetch_ohlcv(sym, "1d", limit=720)[:-1]
        if len(candles) < WARM + WIN + 60:
            continue
        res, starts = run_windows(candles, cfg)
        n = len(starts)
        md += [f"## {base} ({sym})\n",
               f"{n} départs, du {datetime.fromtimestamp(starts[0] / 1000, tz=timezone.utc):%Y-%m-%d} "
               f"au {datetime.fromtimestamp(starts[-1] / 1000, tz=timezone.utc):%Y-%m-%d}.\n",
               "| Stratégie | Médiane après 6 mois | Pire départ | Meilleur départ | Départs gagnants | Chute max médiane |",
               "|---|---|---|---|---|---|"]
        for name, _ in VARIANTS:
            r = res[name]
            rets = [x["ret"] for x in r]
            md.append(f"| {name} | **{pct(median(rets))}** | {pct(min(rets))} | {pct(max(rets))} | "
                      f"{sum(1 for x in rets if x > 0)}/{n} | {median([x['dd'] for x in r]):.0f} % |")
        a, b = res["Bot actuel (attend le signal)"], res["Entrée immédiate"]
        better = sum(1 for x, y in zip(a, b) if y["ret"] > x["ret"] + 0.5)
        worse = sum(1 for x, y in zip(a, b) if y["ret"] < x["ret"] - 0.5)
        md += ["", f"Entrée immédiate contre bot actuel : meilleure dans {better} départs, pire dans {worse}, "
               f"pareille dans {n - better - worse}.\n"]
        verdict.append(f"| {base} | {better}/{n} | {worse}/{n} | {pct(median([y['ret'] - x['ret'] for x, y in zip(a, b)]))} |")
    md[4:4] = ["## Résumé : entrée immédiate contre bot actuel\n",
               "| Crypto | Départs où c'est mieux | Départs où c'est pire | Écart médian |", "|---|---|---|---|"] + verdict + [""]
    md.append("Un bon résultat passé ne garantit rien pour la suite. Ce n'est pas un conseil financier.")
    text = "\n".join(md) + "\n"
    with open(os.path.join(bot.HERE, "ENTREE.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
