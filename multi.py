#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fait tourner plusieurs simulations côte à côte (argent fictif), chacune dans son dossier,
puis écrit le résumé sur la page d'accueil du dépôt (README.md).

Lancé automatiquement par GitHub Actions à chaque réveil. Aucune clé API nécessaire.
"""
import csv
import os
import sys
from datetime import datetime, timezone

import bot
import dashboard

SIMS = [
    {"dir": "eth", "label": "ETH, bot actuel", "symbol": "ETH/CAD", "trend_days": 0,
     "description": "La stratégie de départ : croisement des moyennes 10 et 30 jours."},
    {"dir": "eth-filtre", "label": "ETH avec filtre de fond", "symbol": "ETH/CAD", "trend_days": 100,
     "description": "Même stratégie, mais le bot n'achète que si le prix est aussi au-dessus de sa moyenne 100 jours."},
    {"dir": "sol-filtre", "label": "SOL avec filtre de fond", "symbol": "SOL/CAD", "trend_days": 100,
     "description": "Solana, avec le filtre de fond 100 jours."},
]
COLORS = ["#1a7f37", "#0969da", "#bf8700", "#8250df", "#cf222e"]


class Recorder:
    """Enveloppe l'exchange et garde les dernières bougies reçues, pour que le filtre de fond
    utilise exactement les mêmes données que le bot."""

    def __init__(self, ex):
        self._ex = ex
        self.last = []

    def __getattr__(self, name):
        return getattr(self._ex, name)

    def fetch_ohlcv(self, *a, **k):
        self.last = self._ex.fetch_ohlcv(*a, **k)
        return self.last


def trend_filter(ex, days, original):
    """Version de bot.want_long qui refuse un achat si la dernière clôture est sous sa moyenne longue.
    Les ventes ne sont jamais bloquées."""
    def filtered(f, s, currently_long, gap_pct):
        want = original(f, s, currently_long, gap_pct)
        if want and not currently_long:
            closes = [c[4] for c in ex.last[:-1]]
            t = bot.sma_series(closes, days)[-1] if len(closes) >= days else None
            return t is not None and closes[-1] > t
        return want
    return filtered


def migrate(root):
    """Premier lancement : range l'ancienne simulation ETH (à la racine) dans le dossier eth/."""
    src, dst = os.path.join(root, "state_paper.json"), os.path.join(root, "eth")
    if os.path.exists(src) and not os.path.exists(os.path.join(dst, "state_paper.json")):
        os.makedirs(dst, exist_ok=True)
        for name in ("state_paper.json", "history.csv", "trades.csv", "graphiques"):
            a, b = os.path.join(root, name), os.path.join(dst, name)
            if os.path.exists(a) and not os.path.exists(b):
                os.replace(a, b)
        print("Ancienne simulation ETH déplacée dans le dossier eth/.")


def run_all(ex, base_cfg, root, now=None):
    results = []
    original = bot.want_long
    for sim in SIMS:
        folder = os.path.join(root, sim["dir"])
        os.makedirs(folder, exist_ok=True)
        cfg = dict(base_cfg)
        cfg.update({k: v for k, v in sim.items() if k != "dir"})
        cfg["home_link"] = "../README.md"
        print(f"=== {sim['label']} ===", flush=True)
        try:
            bot.HERE = folder
            if cfg["trend_days"]:
                bot.want_long = trend_filter(ex, cfg["trend_days"], original)
            bot.run("paper", cfg, ex=ex, max_loops=1, sleeper=lambda s: None)
            bot.want_long = original
            summary = dashboard.build(ex, cfg, now=now)
            results.append((sim, summary))
        except Exception as e:
            print(f"Erreur sur {sim['label']} : {e}", flush=True)
            results.append((sim, None))
        finally:
            bot.want_long = original
            bot.HERE = root
    return results


def write_home(results, root, now=None):
    now = now or datetime.now(timezone.utc)
    bot.HERE = root
    series = []
    for i, (sim, _) in enumerate(results):
        p = os.path.join(root, sim["dir"], "history.csv")
        if os.path.exists(p):
            with open(p, newline="", encoding="utf-8") as f:
                pts = [(dashboard.parse_iso(r["date"]).timestamp(), float(r["valeur"])) for r in csv.DictReader(f)]
            series.append({"name": sim["label"], "color": COLORS[i % len(COLORS)], "points": pts, "width": 2.5})
    svg = dashboard.chart_svg(series, title="Valeur de chaque simulation") if series else None
    if svg:
        dashboard.write_svg("comparaison.svg", svg)

    md = ["# Simulations du bot (argent fictif)\n",
          f"Mis à jour le **{dashboard.fmt_dt(now)}** (heure de Montréal). "
          "Les bots se réveillent environ toutes les 30 minutes ; GitHub a souvent du retard.\n",
          "| Simulation | Statut | Valeur | Si tu avais acheté et gardé | Transactions |",
          "|---|---|---|---|---|"]
    for sim, s in results:
        link = f"[**{sim['label']}**]({sim['dir']}/README.md)"
        if s is None:
            md.append(f"| {link} | ⚠️ Erreur à ce réveil | | | |")
            continue
        status = "⛔ Arrêté (coupe-circuit)" if s["halted"] else ("🟢 En position" if s["in_pos"] else "⚪ Hors position")
        md.append(f"| {link} | {status} | **{dashboard.money(s['equity'])}** ({dashboard.pct((s['equity'] / s['start'] - 1) * 100)}) | "
                  f"{dashboard.money(s['hold'])} ({dashboard.pct((s['hold'] / s['start'] - 1) * 100)}) | {s['trades']} |")
    md += ["", "Clique sur le nom d'une simulation pour voir son tableau de bord complet : prochain signal, graphiques et transactions.\n"]
    for sim, _ in results:
        md.append(f"- **{sim['label']}** : {sim['description']}")
    md.append("")
    md.append("## Valeur de chaque simulation\n")
    md.append("![Valeur de chaque simulation](graphiques/comparaison.svg)\n" if svg
              else "_Le graphique apparaîtra après le deuxième réveil._\n")
    md += ["## Les analyses\n",
           "- [Comparaison de la stratégie sur ETH, BTC, SOL et XRP](COMPARAISON.md)",
           "- [Test des améliorations : pourquoi le filtre de fond a été retenu](AMELIORATIONS.md)",
           "- [Instructions](LISEZ-MOI.md)\n",
           "---",
           "Chaque simulation démarre avec 200 $ fictifs. Ce n'est pas un conseil financier."]
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")


def main():
    root = bot.HERE
    cfg = bot.load_config()
    migrate(root)
    ex = Recorder(bot.make_exchange(False))
    ex.load_markets()
    results = run_all(ex, cfg, root)
    write_home(results, root)
    if all(s is None for _, s in results):
        sys.exit("Toutes les simulations ont échoué à ce réveil.")


if __name__ == "__main__":
    main()
