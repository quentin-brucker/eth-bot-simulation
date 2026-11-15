#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de la stratégie du bot sur les actions américaines : S&P 500 et Nasdaq 100.

Trois façons de faire, comparées sur un long historique (depuis 2007, crises incluses) :
  - Acheter et garder le FNB de l'indice (SPY ou QQQ)
  - Bot « hausse seulement »   : achète le FNB quand la tendance monte, reste en dollars sinon
  - Bot « hausse et baisse »   : en plus, achète le FNB inversé (SH ou PSQ) quand la tendance baisse

Les prix viennent de Yahoo Finance (dividendes inclus). Les FNB inversés sont les vrais fonds,
donc leur usure dans le temps et leurs frais de gestion sont déjà dans les prix.
Écrit le résultat dans ACTIONS.md. Lancé à la main depuis l'onglet Actions de GitHub.
"""
import json
import os
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
START = "2007-01-01"
PAIRS = [("S&P 500", "SPY", "SH"), ("Nasdaq 100", "QQQ", "PSQ")]
GRID = [(10, 30), (10, 50), (10, 100), (10, 200), (20, 50), (20, 100), (20, 200), (50, 100), (50, 200)]
BASE = (10, 30)             # le réglage du bot crypto
CLASSIC = (50, 200)         # le réglage classique pour les actions
GAP = 0.5                   # écart minimal entre les moyennes pour entrer (%)
STOP = 8.0                  # stop-loss (%)
COOLDOWN = 2                # jours d'attente après un stop-loss
FEE = 0.10                  # frais par transaction (%) : environ 1 $ US par ordre sur 1 000 $
FEE_SMALL = 0.50            # la même commission de 1 $ sur un compte de 200 $
SLIP = 0.02                 # glissement (%)
CRISES = [("Crise de 2008", "2007-10-09", "2009-03-09"), ("Krach COVID 2020", "2020-02-19", "2020-03-23"),
          ("Baisse de 2022", "2022-01-03", "2022-10-12")]


# --------------------------------------------------------------------------
# Données
# --------------------------------------------------------------------------
def fetch(symbol):
    """Retourne {date: (open, high, low, close)} ajustés des dividendes et fractionnements."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=max&interval=1d"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.load(r)["chart"]["result"][0]
    return parse_yahoo(res)


def parse_yahoo(res):
    q = res["indicators"]["quote"][0]
    adj = res["indicators"]["adjclose"][0]["adjclose"]
    out = {}
    for i, t in enumerate(res["timestamp"]):
        o, h, l, c, a = q["open"][i], q["high"][i], q["low"][i], q["close"][i], adj[i]
        if None in (o, h, l, c, a) or c <= 0:
            continue
        k = a / c
        out[datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d")] = (o * k, h * k, l * k, a)
    return out


def align(a, b):
    dates = sorted(d for d in a if d in b and d >= START)
    return dates, [a[d] for d in dates], [b[d] for d in dates]


# --------------------------------------------------------------------------
# Stratégie
# --------------------------------------------------------------------------
def sma(values, n):
    out, s = [None] * len(values), 0.0
    for i, x in enumerate(values):
        s += x
        if i >= n:
            s -= values[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def backtest(long_bars, inv_bars, fast, slow, short, fee, start=0, end=None, trade_from=None):
    """Position : 'L' (FNB de l'indice), 'S' (FNB inversé) ou None (dollars).
    Signal calculé à la clôture, ordre exécuté à l'ouverture du lendemain. Stop-loss dans la journée."""
    end = end if end is not None else len(long_bars)
    trade_from = start if trade_from is None else trade_from
    closes = [b[3] for b in long_bars[:end]]
    f_s, s_s = sma(closes, fast), sma(closes, slow)
    g, fe, sl, st = GAP / 100.0, fee / 100.0, SLIP / 100.0, STOP / 100.0
    cash, qty, pos, entry = 1000.0, 0.0, None, None
    cool, pending = 10 ** 9, "keep"
    trades, wins, cost, days_in = 0, 0, 0.0, 0
    equity = []

    def bars(p):
        return long_bars if p == "L" else inv_bars

    def close_pos(price):
        nonlocal cash, qty, pos, entry, trades, wins
        net = qty * price * (1 - sl) * (1 - fe)
        trades += 1
        wins += net > cost
        cash, qty, pos, entry = cash + net, 0.0, None, None

    def open_pos(p, price):
        nonlocal cash, qty, pos, entry, cost
        px = price * (1 + sl)
        qty = cash / (px * (1 + fe))
        cost, cash, pos, entry = cash, 0.0, p, px

    for j in range(start, end):
        if pending != "keep" and j > start:
            if pos is not None and pending != pos:
                close_pos(bars(pos)[j][0])
            if pending is not None and pos is None:
                open_pos(pending, bars(pending)[j][0])
        pending = "keep"
        if pos is not None:
            o, _, low, _ = bars(pos)[j]
            level = entry * (1 - st)
            if low <= level:
                close_pos(min(o, level))
                cool = 0
        equity.append(cash + (qty * bars(pos)[j][3] if pos else 0.0))
        days_in += pos is not None and j >= trade_from
        f, s = f_s[j], s_s[j]
        if j >= trade_from and f is not None and s is not None:
            if pos == "L":
                target = "L" if f >= s else ("S" if short and f < s * (1 - g) else None)
            elif pos == "S":
                target = "S" if f <= s else ("L" if f > s * (1 + g) else None)
            else:
                target = "L" if f > s * (1 + g) else ("S" if short and f < s * (1 - g) else None)
                if cool < COOLDOWN:
                    target = None
            if target != pos:
                pending = target
        cool += 1

    final = cash + (qty * bars(pos)[end - 1][3] * (1 - fe) if pos else 0.0)
    peak, dd = equity[0], 0.0
    for v in equity:
        peak = max(peak, v)
        dd = max(dd, (peak - v) / peak)
    return {"ret": (final / 1000.0 - 1) * 100, "dd": dd * 100, "trades": trades, "wins": wins,
            "time_in": 100.0 * days_in / max(1, end - trade_from), "mult": final / 1000.0}


def hold(bars, fee, start, end):
    fe = fee / 100.0
    eq = [b[3] / bars[start][0] for b in bars[start:end]]
    peak, dd = eq[0], 0.0
    for v in eq:
        peak = max(peak, v)
        dd = max(dd, (peak - v) / peak)
    mult = eq[-1] * (1 - fe) / (1 + fe)
    return {"ret": (mult - 1) * 100, "dd": dd * 100, "trades": 0, "wins": 0, "time_in": 100.0, "mult": mult}


# --------------------------------------------------------------------------
# Rapport
# --------------------------------------------------------------------------
def pct(x, dec=0):
    return f"{x:+.{dec}f} %".replace(".", ",").replace("-", "−")


def cagr(mult, years):
    return (mult ** (1 / years) - 1) * 100 if mult > 0 else -100.0


def median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]


def analyse(name, dates, lb, ib):
    n = len(dates)
    warm = 200                      # toutes les variantes commencent le même jour
    years = (n - warm) / 252.0
    md = [f"## {name}\n", f"Période : du {dates[warm]} au {dates[-1]} ({years:.1f} ans).\n".replace(".", ",", 1)]

    def run(fs, short, fee=FEE, start=warm, end=None):
        return backtest(lb, ib, fs[0], fs[1], short, fee, start=start - fs[1], end=end, trade_from=start - 1)

    rows = [("Acheter et garder", hold(lb, FEE, warm, n)),
            (f"Bot hausse seulement ({BASE[0]}/{BASE[1]})", run(BASE, False)),
            (f"Bot hausse et baisse ({BASE[0]}/{BASE[1]})", run(BASE, True)),
            (f"Bot hausse seulement ({CLASSIC[0]}/{CLASSIC[1]})", run(CLASSIC, False)),
            (f"Bot hausse et baisse ({CLASSIC[0]}/{CLASSIC[1]})", run(CLASSIC, True))]
    md += ["| Stratégie | Rendement total | Par an | Chute max | Transactions (gagnantes) | Temps investi |",
           "|---|---|---|---|---|---|"]
    for label, r in rows:
        md.append(f"| {label} | {pct(r['ret'])} | {pct(cagr(r['mult'], years), 1)} | {r['dd']:.0f} % | "
                  f"{r['trades']} ({r['wins']}) | {r['time_in']:.0f} % |")

    md += ["", "**Sur 9 réglages de moyennes** (rendement par an, du pire au meilleur, et réglages qui battent « garder ») :\n",
           "| Stratégie | Pire | Médian | Meilleur | Battent « garder » | Chute max médiane |", "|---|---|---|---|---|---|"]
    h = hold(lb, FEE, warm, n)
    for label, short in (("Bot hausse seulement", False), ("Bot hausse et baisse", True)):
        rs = [run(fs, short) for fs in GRID]
        cg = sorted(cagr(r["mult"], years) for r in rs)
        md.append(f"| {label} | {pct(cg[0], 1)} | {pct(cg[len(cg) // 2], 1)} | {pct(cg[-1], 1)} | "
                  f"{sum(1 for r in rs if r['mult'] > h['mult'])}/{len(rs)} | {median([r['dd'] for r in rs]):.0f} % |")

    md += ["", "**Pendant les grandes baisses** (réglage classique 50/200) :\n",
           "| Période | Acheter et garder | Bot hausse seulement | Bot hausse et baisse |", "|---|---|---|---|"]
    for label, a, b in CRISES:
        i0 = next((i for i, d in enumerate(dates) if d >= a), None)
        i1 = next((i for i, d in enumerate(dates) if d > b), n)
        if i0 is None or i0 < warm or i1 - i0 < 5:
            continue
        # la stratégie tourne depuis le début ; on mesure sa valeur entre les deux dates
        def window(short):
            e0 = backtest(lb, ib, CLASSIC[0], CLASSIC[1], short, FEE, start=warm - CLASSIC[1], end=i0 + 1, trade_from=warm - 1)
            e1 = backtest(lb, ib, CLASSIC[0], CLASSIC[1], short, FEE, start=warm - CLASSIC[1], end=i1, trade_from=warm - 1)
            return (e1["mult"] / e0["mult"] - 1) * 100
        md.append(f"| {label} | {pct((lb[i1 - 1][3] / lb[i0][3] - 1) * 100)} | {pct(window(False))} | {pct(window(True))} |")

    md += ["", f"**Avec un petit compte** (commission de 1 $ US sur 200 $, soit {str(FEE_SMALL).replace('.', ',')} % par ordre, réglage {BASE[0]}/{BASE[1]}) :\n",
           "| Stratégie | Par an avec 1 000 $ | Par an avec 200 $ |", "|---|---|---|"]
    for label, short in (("Bot hausse seulement", False), ("Bot hausse et baisse", True)):
        a, b = run(BASE, short), run(BASE, short, fee=FEE_SMALL)
        md.append(f"| {label} | {pct(cagr(a['mult'], years), 1)} | {pct(cagr(b['mult'], years), 1)} |")
    md.append("")
    return md


def main():
    md = ["# La stratégie du bot sur les actions américaines\n",
          f"Calculé le {datetime.now(timezone.utc).strftime('%Y-%m-%d')} avec les prix de Yahoo Finance (dividendes inclus). "
          f"Frais de {str(FEE).replace('.', ',')} % par transaction, stop-loss de {STOP:.0f} %. "
          "Les montants sont en dollars américains ; le taux de change n'est pas compté. "
          "L'argent qui attend en dollars ne rapporte aucun intérêt dans ce test.\n",
          "- **Hausse seulement** : le bot achète le FNB de l'indice quand la moyenne courte passe au-dessus de la longue, et reste en dollars sinon.",
          "- **Hausse et baisse** : quand la moyenne courte passe sous la longue, il achète en plus le FNB inversé (SH pour le S&P 500, PSQ pour le Nasdaq).\n"]
    for name, long_sym, inv_sym in PAIRS:
        try:
            dates, lb, ib = align(fetch(long_sym), fetch(inv_sym))
            md += analyse(f"{name} ({long_sym}, inversé : {inv_sym})", dates, lb, ib)
        except Exception as e:
            md += [f"## {name}\n", f"Données indisponibles : {e}\n"]
    md.append("Un bon résultat passé ne garantit rien pour la suite. Ce n'est pas un conseil financier.")
    text = "\n".join(md) + "\n"
    with open(os.path.join(HERE, "ACTIONS.md"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
