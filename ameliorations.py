#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Banc d'essai : est-ce que des améliorations de la stratégie tiennent vraiment ?

Trois idées, testées seules et combinées, sur 4 cryptos (vrais prix de Kraken) :
  - stop suiveur  : le stop monte avec le prix (vente si le prix redescend de X % sous son sommet)
  - filtre de fond: n'acheter que si le prix est au-dessus de sa moyenne longue
  - confirmation  : le signal d'achat doit tenir 2 jours de suite

Chaque variante est jugée sur 24 réglages de moyennes et sur des départs à dates différentes,
pour ne pas garder une amélioration qui ne marche que par chance.
Écrit le résultat dans AMELIORATIONS.md. Lancé à la main depuis l'onglet Actions de GitHub.
"""
import os
from datetime import datetime, timezone

import bot

COINS = ["ETH", "BTC", "SOL", "XRP"]
FEE = 0.40
WARM = 100      # jours d'échauffement : toutes les variantes commencent à trader le même jour
GRID = [(f, s) for f in (5, 7, 10, 14, 20) for s in (20, 30, 40, 50, 60) if f < s]
WIN = 182       # fenêtre de 6 mois pour le test des dates de départ

VARIANTS = [
    ("Bot actuel", {}),
    ("Stop suiveur 10 %", {"trail": 10}),
    ("Stop suiveur 15 %", {"trail": 15}),
    ("Stop suiveur 20 %", {"trail": 20}),
    ("Filtre de fond 50 j", {"trend": 50}),
    ("Filtre de fond 100 j", {"trend": 100}),
    ("Confirmation 2 jours", {"confirm": 2}),
    ("Suiveur 15 % + filtre 100 j", {"trail": 15, "trend": 100}),
    ("Suiveur 15 % + confirmation", {"trail": 15, "confirm": 2}),
    ("Filtre 100 j + confirmation", {"trend": 100, "confirm": 2}),
    ("Les trois ensemble", {"trail": 15, "trend": 100, "confirm": 2}),
]


def backtest2(candles, cfg, taker, trade_from, trail=None, trend=None, confirm=1):
    """Même logique que bot.backtest, avec les trois options. Aucun signal avant la bougie trade_from."""
    n = len(candles)
    closes = [c[4] for c in candles]
    fast = bot.sma_series(closes, cfg["fast"])
    slow = bot.sma_series(closes, cfg["slow"])
    trend_s = bot.sma_series(closes, trend) if trend else None
    slip = cfg["slippage_pct"] / 100.0
    stop = cfg["stop_loss_pct"] / 100.0
    gap = cfg["min_gap_pct"]
    cooldown = cfg["cooldown_bars"]

    st = {"cash": float(cfg["budget"]), "eth": 0.0, "entry": None, "cost": 0.0, "peak": 0.0,
          "fees": 0.0, "cool": 10 ** 9}
    trips, equity = [], []
    pending, armed = None, None

    def buy(price):
        qty = st["cash"] / (price * (1 + taker))
        fee = qty * price * taker
        st["cost"] = qty * price + fee
        st["cash"] -= st["cost"]
        st["eth"], st["entry"], st["peak"] = qty, price, price
        st["fees"] += fee

    def sell(price):
        gross = st["eth"] * price
        fee = gross * taker
        trips.append(gross - fee - st["cost"])
        st["cash"] += gross - fee
        st["eth"], st["entry"] = 0.0, None
        st["fees"] += fee
        st["cool"] = 0

    for j in range(n):
        o, h, l, c = candles[j][1], candles[j][2], candles[j][3], candles[j][4]
        if pending == "buy" and st["eth"] == 0:
            buy(o * (1 + slip))
        elif pending == "sell" and st["eth"] > 0:
            sell(o * (1 - slip))
        pending = None
        if st["eth"] > 0:
            level = st["entry"] * (1 - stop)
            if trail:
                level = max(level, st["peak"] * (1 - trail / 100.0))   # sommet connu AVANT cette bougie
            if l <= level:
                sell(min(o, level) * (1 - slip))
        if st["eth"] > 0:
            st["peak"] = max(st["peak"], h)
        equity.append(st["cash"] + st["eth"] * c)
        if j >= trade_from and fast[j] is not None and slow[j] is not None:
            cur = st["eth"] > 0
            want = bot.want_long(fast[j], slow[j], cur, gap)
            if not cur:
                if armed is None:
                    armed = not want
                if not want:
                    armed = True
                elif (not armed) or st["cool"] < cooldown:
                    want = False
                if want and confirm > 1:
                    want = all(fast[j - i] is not None and slow[j - i] is not None
                               and bot.want_long(fast[j - i], slow[j - i], False, gap) for i in range(1, confirm))
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
    return {"ret": (final / cfg["budget"] - 1) * 100, "dd": dd * 100, "trips": len(trips),
            "wins": sum(1 for t in trips if t > 0), "fees": st["fees"]}


def run(candles, cfg, opts, start=WARM, end=None, **over):
    c = dict(cfg)
    c.update(over)
    end = end if end is not None else len(candles)
    return backtest2(candles[start - WARM:end], c, FEE / 100.0, WARM - 1, **opts)


def hold(candles, cfg, start=WARM, end=None):
    end = end if end is not None else len(candles)
    f, s = FEE / 100.0, cfg["slippage_pct"] / 100.0
    return (candles[end - 1][4] * (1 - s) * (1 - f) / (candles[start][1] * (1 + s) * (1 + f)) - 1) * 100


def median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


def evaluate(candles, cfg):
    out = []
    for name, opts in VARIANTS:
        main = run(candles, cfg, opts)
        grid = [run(candles, cfg, opts, fast=f, slow=s)["ret"] for f, s in GRID]
        roll = [run(candles, cfg, opts, start=st, end=st + WIN)
                for st in range(WARM, len(candles) - WIN + 1, 30)]
        out.append({
            "name": name, "ret": main["ret"], "dd": main["dd"], "trips": main["trips"], "wins": main["wins"],
            "grid_med": median(grid), "grid_pos": sum(1 for g in grid if g > 0),
            "roll_med": median([r["ret"] for r in roll]), "roll_worst": min(r["ret"] for r in roll),
            "roll_pos": sum(1 for r in roll if r["ret"] > 0), "roll_n": len(roll),
        })
    return out


def pct(x, dec=0):
    return f"{x:+.{dec}f} %".replace(".", ",").replace("-", "−")


def report(results, holds, cfg):
    coins = list(results.keys())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    md = ["# Améliorations de la stratégie : est-ce que ça tient ?\n",
          f"Calculé le {now} avec les vrais prix de Kraken, frais de {str(FEE).replace('.', ',')} % inclus. "
          f"Toutes les variantes commencent à trader le même jour (après {WARM} jours d'échauffement), "
          "donc les chiffres du bot actuel diffèrent un peu de la comparaison précédente.\n"]

    def table(title, intro, cell):
        md.append(f"## {title}\n")
        md.append(intro + "\n")
        md.append("| Variante | " + " | ".join(coins) + " |")
        md.append("|---|" + "---|" * len(coins))
        for i, (name, _) in enumerate(VARIANTS):
            label = f"**{name}**" if i == 0 else name
            md.append(f"| {label} | " + " | ".join(cell(results[c][i]) for c in coins) + " |")
        md.append("")

    md.append("## Verdict\n")
    md.append("Pour chaque variante, sur combien de cryptos elle fait **mieux que le bot actuel**. "
              "Une amélioration solide devrait gagner sur 3 ou 4 cryptos dans plusieurs colonnes.\n")
    md.append("| Variante | Rendement médian (24 réglages) | Chute max plus faible | Médiane sur 6 mois | Pire départ sur 6 mois |")
    md.append("|---|---|---|---|---|")
    for i, (name, _) in enumerate(VARIANTS[1:], start=1):
        def better(key, lower=False):
            k = 0
            for c in coins:
                a, b = results[c][i][key], results[c][0][key]
                k += (a < b - 0.5) if lower else (a > b + 0.5)
            return f"{k}/{len(coins)}"
        md.append(f"| {name} | {better('grid_med')} | {better('dd', True)} | {better('roll_med')} | {better('roll_worst')} |")
    md.append("")

    table("Rendement avec le réglage du bot",
          f"Moyennes {cfg['fast']}/{cfg['slow']}, toute la période. Entre parenthèses : la plus grosse chute temporaire. "
          "Acheter et garder : " + ", ".join(f"{c} {pct(holds[c])}" for c in coins) + ".",
          lambda r: f"{pct(r['ret'])} ({r['dd']:.0f} %)")
    table("Rendement médian sur 24 réglages de moyennes",
          "Le chiffre le plus fiable : il ne dépend pas d'un réglage précis. Entre parenthèses : nombre de réglages gagnants sur 24.",
          lambda r: f"{pct(r['grid_med'])} ({r['grid_pos']}/24)")
    table("Six mois de bot selon la date de départ",
          "Résultat médian après 6 mois, puis le pire départ. Entre parenthèses : départs gagnants.",
          lambda r: f"{pct(r['roll_med'])} / {pct(r['roll_worst'])} ({r['roll_pos']}/{r['roll_n']})")
    table("Nombre de transactions",
          "Allers-retours avec le réglage du bot (gagnants entre parenthèses). Plus de transactions = plus de frais.",
          lambda r: f"{r['trips']} ({r['wins']})")
    md.append("Un bon résultat passé ne garantit rien pour la suite. Ce n'est pas un conseil financier.")
    return "\n".join(md) + "\n"


def main():
    cfg = bot.load_config()
    ex = bot.make_exchange(False)
    ex.load_markets()
    results, holds = {}, {}
    for base in COINS:
        sym = next((f"{base}/{q}" for q in ("CAD", "USD") if f"{base}/{q}" in ex.markets), None)
        if not sym:
            print(base, "introuvable")
            continue
        candles = ex.fetch_ohlcv(sym, "1d", limit=720)[:-1]
        if len(candles) < WARM + WIN + 60:
            print(base, "historique trop court")
            continue
        results[base] = evaluate(candles, cfg)
        holds[base] = hold(candles, cfg)
    text = report(results, holds, cfg)
    with open(os.path.join(bot.HERE, "AMELIORATIONS.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
