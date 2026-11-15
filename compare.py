#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare la stratégie du bot sur plusieurs cryptos, avec les vrais prix de Kraken (environ 2 ans).
Écrit le résultat dans COMPARAISON.md. Lancé à la main depuis l'onglet Actions de GitHub.
"""
import os
from datetime import datetime, timezone

import bot

COINS = ["ETH", "BTC", "SOL", "XRP"]
FEE = 0.40      # frais par transaction utilisés pour comparer (plus prudent que le taux affiché)
WARM = 60       # tous les réglages commencent à trader à la même bougie
GRID = [(f, s) for f in (5, 7, 10, 14, 20) for s in (20, 30, 40, 50, 60) if f < s]


def day(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def pct(x):
    return f"{x:+.1f} %".replace(".", ",").replace("-", "−")


def hold(seg, cfg, fee):
    f, s = fee / 100.0, cfg["slippage_pct"] / 100.0
    return (seg[-1][4] * (1 - s) * (1 - f) / (seg[0][1] * (1 + s) * (1 + f)) - 1) * 100


def run(candles, cfg, start=WARM, end=None, fee=FEE, **over):
    c = dict(cfg)
    c.update(over)
    end = end if end is not None else len(candles)
    r = bot.backtest(candles[start - c["slow"]:end], c, fee / 100.0)
    return {
        "ret": (r["final"] / r["budget"] - 1) * 100,
        "bh": hold(candles[start + 1:end], c, fee),
        "dd": r["max_dd"] * 100, "trips": r["trips"], "wins": r["wins"],
    }


def pick_symbol(ex, base):
    for quote in ("CAD", "USD"):
        sym = f"{base}/{quote}"
        if sym in ex.markets:
            return sym
    return None


def analyse(ex, base, cfg):
    sym = pick_symbol(ex, base)
    if not sym:
        return {"base": base, "error": "paire introuvable sur Kraken"}
    candles = ex.fetch_ohlcv(sym, "1d", limit=720)[:-1]
    if len(candles) < WARM + 200:
        return {"base": base, "sym": sym, "error": f"historique trop court ({len(candles)} jours)"}
    c = dict(cfg)
    c["symbol"] = sym
    main = run(candles, c)
    grid = [run(candles, c, fast=f, slow=s) for f, s in GRID]
    win = 182
    roll = [run(candles, c, start=st, end=st + win) for st in range(WARM, len(candles) - win + 1, 30)]
    return {
        "base": base, "sym": sym, "start": day(candles[WARM][0]), "end": day(candles[-1][0]),
        "days": len(candles) - WARM, "main": main,
        "grid_pos": sum(1 for g in grid if g["ret"] > 0), "grid_beat": sum(1 for g in grid if g["ret"] > g["bh"]),
        "grid_n": len(grid), "grid_med": sorted(g["ret"] for g in grid)[len(grid) // 2],
        "roll_pos": sum(1 for r in roll if r["ret"] > 0), "roll_n": len(roll),
        "roll_worst": min(r["ret"] for r in roll), "roll_med": sorted(r["ret"] for r in roll)[len(roll) // 2],
        "roll_dd20": sum(1 for r in roll if r["dd"] >= c["max_loss_pct"]),
    }


def build(ex, cfg):
    ex.load_markets()
    res = []
    for base in COINS:
        try:
            res.append(analyse(ex, base, cfg))
        except Exception as e:
            res.append({"base": base, "error": str(e)})
        print(res[-1])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    md = [f"# Comparaison de la stratégie sur {len(COINS)} cryptos\n",
          f"Calculé le {now} avec les vrais prix de Kraken (bougies d'un jour, environ 2 ans), "
          f"frais de {str(FEE).replace('.', ',')} % par transaction inclus. "
          f"Réglage du bot : moyennes {cfg['fast']}/{cfg['slow']}, stop-loss {str(cfg['stop_loss_pct']).replace('.', ',')} %.\n",
          "## Résultat sur toute la période\n",
          "| Crypto | Paire | Période | Bot | Acheter et garder | Chute max du bot | Trades (gagnants) |",
          "|---|---|---|---|---|---|---|"]
    for r in res:
        if "error" in r:
            md.append(f"| {r['base']} | {r.get('sym', '—')} | {r['error']} | | | | |")
            continue
        m = r["main"]
        md.append(f"| **{r['base']}** | {r['sym']} | {r['days']} jours | **{pct(m['ret'])}** | {pct(m['bh'])} | {m['dd']:.0f} % | "
                  f"{m['trips']} ({m['wins']}) |")
    md += ["", "## Solidité du résultat\n",
           "- **Autres réglages** : sur 24 combinaisons de moyennes, combien finissent gagnantes et combien battent « acheter et garder ».",
           "- **6 mois selon la date de départ** : le bot lancé à différentes dates, un mois d'écart chaque fois.\n",
           "| Crypto | Réglages gagnants | Réglages qui battent « garder » | Départs gagnants après 6 mois | Médiane 6 mois | Pire 6 mois | Départs avec chute ≥ 20 % |",
           "|---|---|---|---|---|---|---|"]
    for r in res:
        if "error" in r:
            continue
        md.append(f"| **{r['base']}** | {r['grid_pos']}/{r['grid_n']} | {r['grid_beat']}/{r['grid_n']} | "
                  f"{r['roll_pos']}/{r['roll_n']} | {pct(r['roll_med'])} | {pct(r['roll_worst'])} | "
                  f"{r['roll_dd20']}/{r['roll_n']} |")
    md += ["", "## Comment lire ce tableau\n",
           "- Une crypto se prête bien à la stratégie si le bot fait mieux que « acheter et garder » "
           "**et** si ça tient avec d'autres réglages et d'autres dates de départ.",
           "- La « chute max » est la plus grosse baisse temporaire de la valeur du bot. Au-delà de 20 %, "
           "le coupe-circuit du bot vendrait tout et s'arrêterait.",
           "- Toutes ces cryptos suivent en partie le Bitcoin : elles ont souvent chuté en même temps.",
           "- Un bon résultat passé ne garantit rien pour la suite. Ce n'est pas un conseil financier.\n"]
    with open(os.path.join(bot.HERE, "COMPARAISON.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    build(bot.make_exchange(False), bot.load_config())
