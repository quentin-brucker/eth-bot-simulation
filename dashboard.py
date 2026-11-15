#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tableau de bord de la simulation.

Après chaque passage du bot, ce script met à jour :
  - README.md        : la page d'accueil du dépôt GitHub (statut, prochain signal, graphiques, transactions)
  - history.csv      : une ligne par réveil (prix, moyennes, position, valeur)
  - graphiques/*.svg : les graphiques affichés dans README.md

Lancé automatiquement par GitHub Actions. Aucune clé API nécessaire.
"""
import csv
import json
import os
from datetime import datetime, timezone, timedelta

import bot

HERE = bot.HERE
MOIS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/Toronto")
except Exception:  # pas de base de fuseaux : on se rabat sur UTC-5
    TZ = timezone(timedelta(hours=-5))


# --------------------------------------------------------------------------
# Mise en forme
# --------------------------------------------------------------------------
def money(x, dec=2):
    s = f"{abs(x):,.{dec}f}".replace(",", " ").replace(".", ",")
    return f"{'−' if x < 0 else ''}{s} $"


def pct(x):
    s = f"{abs(x):.1f}".replace(".", ",")
    return f"{'+' if x >= 0 else '−'}{s} %"


def to_local(dt):
    return dt.astimezone(TZ)


def fmt_dt(dt):
    d = to_local(dt)
    return f"{d.day} {MOIS[d.month - 1]} {d.year} à {d.hour} h {d.minute:02d}"


def fmt_short(dt):
    d = to_local(dt)
    return f"{d.day} {MOIS[d.month - 1]} {d.hour} h {d.minute:02d}"


def parse_iso(s):
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# --------------------------------------------------------------------------
# Fichiers
# --------------------------------------------------------------------------
def path(name):
    return os.path.join(HERE, name)


def load_state():
    p = path("state_paper.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_trades():
    p = path("trades.csv")
    if not os.path.exists(p):
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("mode") == "paper"]


HIST_FIELDS = ["date", "prix", "moy_rapide", "moy_lente", "en_position", "valeur"]


def read_history():
    p = path("history.csv")
    if not os.path.exists(p):
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_history(row):
    p = path("history.csv")
    new = not os.path.exists(p)
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HIST_FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


# --------------------------------------------------------------------------
# Signal : quel prix de clôture déclencherait un croisement ce soir ?
# --------------------------------------------------------------------------
def cross_price(closed_closes, nf, ns, k):
    """Prix de clôture P de la bougie en cours tel que moyenne_rapide = k × moyenne_lente."""
    if len(closed_closes) < ns:
        return None
    sf = sum(closed_closes[-(nf - 1):]) if nf > 1 else 0.0
    ss = sum(closed_closes[-(ns - 1):])
    a = 1.0 / nf - k / ns
    if a <= 0:
        return None
    return (k * ss / ns - sf / nf) / a


# --------------------------------------------------------------------------
# Graphiques SVG (sans bibliothèque externe)
# --------------------------------------------------------------------------
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def chart_svg(series, markers=(), title="", width=900, height=340, ydec=0):
    """series : liste de dicts {name, color, points:[(x_epoch, y)], dash}. markers : [(x, y, 'achat'|'vente')]."""
    pts = [p for s in series for p in s["points"]]
    if len(pts) < 2:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts] + [m[1] for m in markers]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if xmax == xmin:
        xmax = xmin + 1
    pad = (ymax - ymin) * 0.08 or max(abs(ymax) * 0.02, 1)
    ymin, ymax = ymin - pad, ymax + pad
    L, R, T, B = 78, 18, 58, 38
    W, H = width, height

    def sx(x):
        return L + (x - xmin) / (xmax - xmin) * (W - L - R)

    def sy(y):
        return T + (ymax - y) / (ymax - ymin) * (H - T - B)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif">',
           f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="8" fill="#ffffff" stroke="#d0d7de"/>']
    if title:
        out.append(f'<text x="{L}" y="24" font-size="15" font-weight="600" fill="#1f2328">{esc(title)}</text>')
    # légende
    lx = L
    for s in series:
        dash = ' stroke-dasharray="6 4"' if s.get("dash") else ""
        out.append(f'<line x1="{lx}" y1="42" x2="{lx + 22}" y2="42" stroke="{s["color"]}" stroke-width="2.5"{dash}/>')
        out.append(f'<text x="{lx + 28}" y="46" font-size="12" fill="#57606a">{esc(s["name"])}</text>')
        lx += 40 + 7 * len(s["name"])
    if markers:
        out.append(f'<path d="M{lx} 46 l6 -9 l6 9 z" fill="#1a7f37"/>'
                   f'<text x="{lx + 16}" y="46" font-size="12" fill="#57606a">achat</text>')
        lx += 62
        out.append(f'<path d="M{lx} 37 l6 9 l6 -9 z" fill="#cf222e"/>'
                   f'<text x="{lx + 16}" y="46" font-size="12" fill="#57606a">vente</text>')
    # grille horizontale
    for i in range(5):
        y = ymin + (ymax - ymin) * i / 4
        py = sy(y)
        out.append(f'<line x1="{L}" y1="{py:.1f}" x2="{W - R}" y2="{py:.1f}" stroke="#eaeef2"/>')
        out.append(f'<text x="{L - 8}" y="{py + 4:.1f}" font-size="11" fill="#57606a" text-anchor="end">'
                   f'{esc(money(y, ydec))}</text>')
    # dates en bas
    span = xmax - xmin
    for i in range(6):
        x = xmin + span * i / 5
        d = to_local(datetime.fromtimestamp(x, tz=timezone.utc))
        label = f"{d.day} {MOIS[d.month - 1]}" if span > 2 * 86400 else f"{d.hour} h {d.minute:02d}"
        anchor = "start" if i == 0 else ("end" if i == 5 else "middle")
        out.append(f'<text x="{sx(x):.1f}" y="{H - 14}" font-size="11" fill="#57606a" text-anchor="{anchor}">{esc(label)}</text>')
    # courbes
    for s in series:
        if len(s["points"]) < 2:
            continue
        coords = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in s["points"])
        dash = ' stroke-dasharray="6 4"' if s.get("dash") else ""
        out.append(f'<polyline points="{coords}" fill="none" stroke="{s["color"]}" stroke-width="{s.get("width", 2)}" '
                   f'stroke-linejoin="round"{dash}/>')
    # repères d'achat et de vente
    for x, y, side in markers:
        px, py = sx(x), sy(y)
        if side == "achat":
            out.append(f'<path d="M{px - 7:.1f} {py + 14:.1f} l7 -11 l7 11 z" fill="#1a7f37"/>')
        else:
            out.append(f'<path d="M{px - 7:.1f} {py - 14:.1f} l7 11 l7 -11 z" fill="#cf222e"/>')
    out.append("</svg>")
    return "\n".join(out)


def write_svg(name, svg):
    os.makedirs(path("graphiques"), exist_ok=True)
    with open(path(os.path.join("graphiques", name)), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n' + svg)


# --------------------------------------------------------------------------
# Construction du tableau de bord
# --------------------------------------------------------------------------
def build(ex, cfg, now=None):
    now = now or datetime.now(timezone.utc)
    sym, nf, ns = cfg["symbol"], cfg["fast"], cfg["slow"]
    ex.load_markets()
    _, taker = bot.get_fees(ex, cfg, False)
    candles = ex.fetch_ohlcv(sym, cfg["timeframe"], limit=cfg.get("history_bars", 200))
    price = float(ex.fetch_ticker(sym)["last"])
    closed = candles[:-1]
    closes = [c[4] for c in closed]
    fast_s = bot.sma_series(closes, nf)
    slow_s = bot.sma_series(closes, ns)
    f, s = fast_s[-1], slow_s[-1]

    state = load_state()
    cash = float(state.get("cash", cfg["budget"]))
    eth = float(state.get("eth", 0.0))
    equity = cash + eth * price
    start_equity = float(state.get("start_equity", cfg["budget"]))
    in_pos = eth > 0
    trades = load_trades()
    fees = sum(float(t.get("frais") or 0) for t in trades)

    append_history({
        "date": now.isoformat(timespec="seconds"), "prix": f"{price:.2f}",
        "moy_rapide": f"{f:.2f}", "moy_lente": f"{s:.2f}",
        "en_position": int(in_pos), "valeur": f"{equity:.2f}",
    })
    hist = read_history()
    start_price = float(hist[0]["prix"])
    hold = start_equity * (price / start_price) * (1 - taker) ** 2
    hist_start = parse_iso(hist[0]["date"])

    # ---- graphique 1 : prix et moyennes sur 90 jours
    n = min(90, len(closed))
    first = len(closed) - n
    def ts(c):
        return c[0] / 1000.0
    price_pts = [(ts(c), c[4]) for c in closed[first:]] + [(now.timestamp(), price)]
    fast_pts = [(ts(closed[i]), fast_s[i]) for i in range(first, len(closed)) if fast_s[i] is not None]
    slow_pts = [(ts(closed[i]), slow_s[i]) for i in range(first, len(closed)) if slow_s[i] is not None]
    marks = []
    t_first = ts(closed[first])
    for t in trades:
        tt = parse_iso(t["date"]).timestamp()
        if tt >= t_first:
            marks.append((tt, float(t["prix"]), "achat" if t["cote"] == "achat" else "vente"))
    svg1 = chart_svg([
        {"name": "Prix ETH/CAD", "color": "#1f2328", "points": price_pts, "width": 2},
        {"name": f"Moyenne {nf} jours", "color": "#0969da", "points": fast_pts},
        {"name": f"Moyenne {ns} jours", "color": "#bf8700", "points": slow_pts},
    ], marks, title=f"Prix et moyennes, {n} derniers jours")
    if svg1:
        write_svg("prix.svg", svg1)

    # ---- graphique 2 : valeur du bot contre acheter et garder
    eq_pts, hold_pts = [], []
    for h in hist:
        t = parse_iso(h["date"]).timestamp()
        eq_pts.append((t, float(h["valeur"])))
        hold_pts.append((t, start_equity * float(h["prix"]) / start_price * (1 - taker) ** 2))
    svg2 = chart_svg([
        {"name": "Valeur du bot", "color": "#1a7f37", "points": eq_pts, "width": 2.5},
        {"name": "Si tu avais acheté et gardé", "color": "#8c959f", "points": hold_pts, "dash": True},
    ], title=f"Valeur depuis le {hist_start.astimezone(TZ).day} {MOIS[hist_start.astimezone(TZ).month - 1]}", ydec=0)
    if svg2:
        write_svg("valeur.svg", svg2)

    # ---- prochain signal
    gap = (f / s - 1) * 100
    next_close = to_local(datetime.fromtimestamp(candles[-1][0] / 1000 + 86400, tz=timezone.utc))
    close_txt = f"{next_close.hour} h"
    sig = []
    sig.append(f"- Moyenne {nf} jours : **{money(f, 0)}** · Moyenne {ns} jours : **{money(s, 0)}** "
               f"(la moyenne courte est {pct(abs(gap))[1:]} {'au-dessus' if gap >= 0 else 'en dessous'} de la longue)")
    if state.get("halted"):
        sig.append("- ⛔ **Le coupe-circuit s'est déclenché** : la simulation est arrêtée.")
    elif not in_pos:
        k = 1 + cfg["min_gap_pct"] / 100.0
        p_star = cross_price(closes, nf, ns, k)
        if state.get("armed") is False:
            sig.append("- Le marché était déjà en hausse au démarrage : le bot attend que la moyenne courte "
                       "repasse sous la longue, puis remonte, avant d'acheter.")
        elif p_star is None or p_star > price * 1.5:
            sig.append(f"- Un signal d'achat dès ce soir est **impossible** : il faudra plusieurs jours de hausse "
                       f"pour que la moyenne {nf} jours remonte au-dessus de la moyenne {ns} jours.")
        elif p_star <= 0:
            sig.append(f"- Le signal d'achat sera donné à la clôture de ce soir ({close_txt}).")
        else:
            sig.append(f"- Pour un **signal d'achat** à la clôture de ce soir ({close_txt}), l'ETH devrait finir la journée "
                       f"au-dessus de **{money(p_star, 0)}** (prix actuel {money(price, 0)}, soit {pct((p_star / price - 1) * 100)}).")
        bars = state.get("bars_since_exit", 999)
        if bars < cfg["cooldown_bars"]:
            sig.append(f"- Période d'attente après une vente : encore {cfg['cooldown_bars'] - bars} jour(s).")
    else:
        entry = state.get("entry")
        if entry:
            stop = entry * (1 - cfg["stop_loss_pct"] / 100.0)
            sig.append(f"- Acheté à **{money(entry, 0)}**. Gain latent : {pct((price / entry - 1) * 100)}.")
            sig.append(f"- **Stop-loss** : vente immédiate si le prix descend sous **{money(stop, 0)}** "
                       f"({pct((stop / price - 1) * 100)} par rapport à maintenant).")
        p_sell = cross_price(closes, nf, ns, 1.0)
        if p_sell and p_sell > 0:
            sig.append(f"- **Signal de vente** à la clôture de ce soir ({close_txt}) si l'ETH finit la journée "
                       f"sous **{money(p_sell, 0)}**.")
        else:
            sig.append(f"- Aucun signal de vente possible ce soir : la tendance reste nettement à la hausse. "
                       f"Seul le stop-loss peut déclencher une vente.")

    # ---- README
    status = "🟢 **En position** (le bot détient de l'ETH)" if in_pos else "⚪ **Hors position** (en attente d'un signal d'achat)"
    if state.get("halted"):
        status = "⛔ **Arrêté par le coupe-circuit**"
    md = []
    md.append("# Bot ETH : simulation (argent fictif)\n")
    md.append(f"Mis à jour le **{fmt_dt(now)}** (heure de Montréal). "
              "Le bot se réveille environ toutes les 30 minutes ; GitHub a souvent du retard.\n")
    md.append("| | |\n|---|---|")
    md.append(f"| Statut | {status} |")
    md.append(f"| Valeur du bot | **{money(equity)}** ({pct((equity / start_equity - 1) * 100)} depuis le départ) |")
    md.append(f"| Si tu avais acheté et gardé | {money(hold)} ({pct((hold / start_equity - 1) * 100)}) |")
    md.append(f"| Prix ETH/CAD | {money(price)} |")
    md.append(f"| Transactions | {len(trades)} · frais payés : {money(fees)} |")
    md.append("")
    md.append("## Prochain signal\n")
    md.extend(sig)
    md.append("")
    md.append("Les moyennes ne changent qu'une fois par jour, à la clôture de la bougie quotidienne. "
              "Entre-temps, seul le prix bouge.\n")
    md.append("## Prix et moyennes\n")
    md.append("![Prix et moyennes](graphiques/prix.svg)\n" if svg1 else "_Pas encore assez de données._\n")
    md.append("## Valeur du bot\n")
    md.append("![Valeur du bot](graphiques/valeur.svg)\n" if svg2 else
              "_Le graphique apparaîtra après le deuxième réveil._\n")
    md.append("## Transactions\n")
    if trades:
        md.append("| Date | Côté | Prix | Quantité ETH | Frais |\n|---|---|---|---|---|")
        for t in reversed(trades):
            md.append(f"| {fmt_short(parse_iso(t['date']))} | {'🟢 Achat' if t['cote'] == 'achat' else '🔴 Vente'} | "
                      f"{money(float(t['prix']))} | {str(round(float(t['quantite']), 6)).replace('.', ',')} | {money(float(t['frais']))} |")
    else:
        md.append("Aucune transaction pour l'instant.")
    md.append("")
    md.append("## Derniers réveils\n")
    md.append("| Heure | Prix | Position | Valeur |\n|---|---|---|---|")
    for h in reversed(hist[-8:]):
        md.append(f"| {fmt_short(parse_iso(h['date']))} | {money(float(h['prix']))} | "
                  f"{'En position' if h['en_position'] == '1' else 'Hors position'} | {money(float(h['valeur']))} |")
    md.append("")
    md.append("---")
    md.append(f"Simulation avec 200 $ fictifs, frais de {str(round(taker * 100, 2)).replace('.', ',')} % par transaction inclus. "
              "Ce n'est pas un conseil financier. Instructions : [LISEZ-MOI.md](LISEZ-MOI.md)")
    with open(path("README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(md) + "\n")
    print(f"Tableau de bord mis à jour : valeur {equity:.2f}, prix {price:.2f}, {len(hist)} réveils enregistrés.")


def main():
    cfg = bot.load_config()
    build(bot.make_exchange(False), cfg)


if __name__ == "__main__":
    main()
