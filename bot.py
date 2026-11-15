#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot de trading Ethereum pour Kraken (au comptant, sans levier, achat seulement).

Commandes :
  python bot.py backtest [--demo | --csv fichier.csv]   Test sur l'historique, frais inclus
  python bot.py paper                                    Simulation en direct, aucun argent réel
  python bot.py paper --once                             Un seul passage (utilisé par GitHub Actions)
  python bot.py check                                    Vérifie ta clé API (lit le solde, aucun ordre)
  python bot.py live                                     Mode réel (voir README)

Stratégie : croisement de moyennes mobiles (rapide / lente) sur les bougies fermées.
  - Achat quand la moyenne rapide dépasse la lente d'au moins `min_gap_pct` %.
  - Vente quand la rapide repasse sous la lente, ou si le stop-loss est touché.
Sécurité : budget maximal, stop-loss, perte maximale (coupe-circuit), fichier STOP.
Ce bot ne peut pas retirer d'argent : il n'appelle jamais les fonctions de retrait.
"""
import argparse
import csv
import json
import os
import random
import sys
import time
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULTS = {
    "symbol": "ETH/CAD",
    "timeframe": "1d",
    "fast": 10,
    "slow": 30,
    "min_gap_pct": 0.5,
    "cooldown_bars": 2,
    "stop_loss_pct": 8.0,
    "max_loss_pct": 20.0,
    "budget": 200.0,
    "slippage_pct": 0.05,
    "fee_maker_pct": None,
    "fee_taker_pct": None,
    "fallback_fee_maker_pct": 0.25,
    "fallback_fee_taker_pct": 0.40,
    "order_type": "limit",
    "limit_timeout_s": 90,
    "poll_seconds": 300,
    "history_bars": 200,
    "live_validate_only": True,
}


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


# --------------------------------------------------------------------------
# Configuration et clés
# --------------------------------------------------------------------------
def load_env():
    """Lit les clés dans cles.env (ou .env). Elles ne sont jamais écrites dans le code."""
    for name in ("cles.env", ".env"):
        path = os.path.join(HERE, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_config():
    cfg = dict(DEFAULTS)
    path = os.path.join(HERE, "config.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
        cfg.update({k: v for k, v in user.items() if not k.startswith("_")})
    if cfg["fast"] >= cfg["slow"]:
        sys.exit("Erreur de config : 'fast' doit être plus petit que 'slow'.")
    if cfg["order_type"] not in ("limit", "market"):
        sys.exit("Erreur de config : 'order_type' doit être 'limit' ou 'market'.")
    return cfg


def make_exchange(authenticated):
    try:
        import ccxt
    except ImportError:
        sys.exit("La bibliothèque ccxt manque. Lance : pip install -r requirements.txt")
    params = {"enableRateLimit": True}
    if authenticated:
        load_env()
        key = os.environ.get("KRAKEN_API_KEY", "").strip()
        secret = os.environ.get("KRAKEN_API_SECRET", "").strip()
        if not key or not secret or key.startswith("colle_") or secret.startswith("colle_"):
            sys.exit("Clé API absente. Remplis KRAKEN_API_KEY et KRAKEN_API_SECRET dans le fichier cles.env")
        params.update({"apiKey": key, "secret": secret})
    return ccxt.kraken(params)


def get_fees(ex, cfg, authenticated):
    """Retourne (maker, taker) en fractions (0.004 = 0,40 %). Lit les vrais frais quand c'est possible."""
    maker = taker = None
    try:
        ex.load_markets()
        m = ex.market(cfg["symbol"])
        maker, taker = m.get("maker"), m.get("taker")
        if authenticated:
            fees = ex.fetch_trading_fees()
            t = fees.get(cfg["symbol"])
            if t and t.get("maker") is not None:
                maker, taker = t["maker"], t["taker"]
    except Exception as e:
        log(f"Impossible de lire les frais sur Kraken ({e}). J'utilise les valeurs de secours.")
    if cfg["fee_maker_pct"] is not None:
        maker = cfg["fee_maker_pct"] / 100.0
    if cfg["fee_taker_pct"] is not None:
        taker = cfg["fee_taker_pct"] / 100.0
    if maker is None:
        maker = cfg["fallback_fee_maker_pct"] / 100.0
    if taker is None:
        taker = cfg["fallback_fee_taker_pct"] / 100.0
    return maker, taker


# --------------------------------------------------------------------------
# Stratégie
# --------------------------------------------------------------------------
def sma_series(values, n):
    out = [None] * len(values)
    s = 0.0
    for i, x in enumerate(values):
        s += x
        if i >= n:
            s -= values[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def want_long(f, s, currently_long, gap_pct):
    """Vrai si la stratégie veut être en position. Écart minimal pour entrer (anti-faux signaux)."""
    if f is None or s is None:
        return currently_long
    if currently_long:
        return f >= s
    return f > s * (1 + gap_pct / 100.0)


# --------------------------------------------------------------------------
# Données
# --------------------------------------------------------------------------
def demo_candles(n=720, seed=42):
    random.seed(seed)
    price = 3000.0
    t0 = int(time.time() * 1000) - n * 86400000
    drift = 0.0
    out = []
    for i in range(n):
        if i % 90 == 0:
            drift = random.choice([-0.004, -0.001, 0.001, 0.004])
        ret = random.gauss(drift, 0.03)
        o = price
        c = o * (1 + ret)
        h = max(o, c) * (1 + abs(random.gauss(0, 0.01)))
        l = min(o, c) * (1 - abs(random.gauss(0, 0.01)))
        out.append([t0 + i * 86400000, o, h, l, c, random.uniform(100, 1000)])
        price = c
    return out


def read_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append([int(float(r["timestamp"])), float(r["open"]), float(r["high"]),
                         float(r["low"]), float(r["close"]), float(r.get("volume", 0) or 0)])
    return rows


def write_csv(path, candles):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        w.writerows(candles)


# --------------------------------------------------------------------------
# Backtest
# --------------------------------------------------------------------------
def backtest(candles, cfg, taker):
    n = len(candles)
    closes = [c[4] for c in candles]
    fast = sma_series(closes, cfg["fast"])
    slow = sma_series(closes, cfg["slow"])
    slip = cfg["slippage_pct"] / 100.0
    stop = cfg["stop_loss_pct"] / 100.0
    gap = cfg["min_gap_pct"]
    cooldown = cfg["cooldown_bars"]

    cash = float(cfg["budget"])
    eth = 0.0
    entry = None
    entry_cost = 0.0
    pending = None
    cool = 10 ** 9
    armed = None
    fees_paid = 0.0
    trips = []          # profit net de chaque aller-retour
    equity = []
    first_open = None

    def do_buy(price):
        nonlocal cash, eth, entry, entry_cost, fees_paid
        qty = cash / (price * (1 + taker))
        fee = qty * price * taker
        entry_cost = qty * price + fee
        cash -= entry_cost
        eth = qty
        entry = price
        fees_paid += fee

    def do_sell(price):
        nonlocal cash, eth, entry, fees_paid, cool
        gross = eth * price
        fee = gross * taker
        net = gross - fee
        trips.append(net - entry_cost)
        cash += net
        eth = 0.0
        entry = None
        fees_paid += fee
        cool = 0

    for j in range(n):
        o, h, l, c = candles[j][1], candles[j][2], candles[j][3], candles[j][4]
        # 1) ordre décidé à la clôture précédente, exécuté à l'ouverture de cette bougie
        if pending == "buy" and eth == 0:
            if first_open is None:
                first_open = o
            do_buy(o * (1 + slip))
        elif pending == "sell" and eth > 0:
            do_sell(o * (1 - slip))
        pending = None
        # 2) stop-loss dans la bougie
        if eth > 0 and entry is not None:
            level = entry * (1 - stop)
            if l <= level:
                do_sell(min(o, level) * (1 - slip))
        equity.append(cash + eth * c)
        # 3) signal à la clôture, pour la bougie suivante
        if fast[j] is not None and slow[j] is not None:
            cur_long = eth > 0
            want = want_long(fast[j], slow[j], cur_long, gap)
            if not cur_long:
                if armed is None:
                    armed = not want
                if not want:
                    armed = True
                elif (not armed) or cool < cooldown:
                    want = False
            if want and eth == 0:
                pending = "buy"
            elif (not want) and eth > 0:
                pending = "sell"
        cool += 1

    last_close = closes[-1]
    final = cash + eth * last_close * (1 - taker)
    start_i = cfg["slow"]
    peak = equity[start_i] if len(equity) > start_i else equity[0]
    max_dd = 0.0
    for v in equity[start_i:]:
        peak = max(peak, v)
        if peak > 0:
            max_dd = max(max_dd, (peak - v) / peak)
    bh = None
    if first_open is None and n > start_i + 1:
        first_open = candles[start_i + 1][1]
    if first_open:
        bh = (cfg["budget"] / (first_open * (1 + slip) * (1 + taker))) * last_close * (1 - slip) * (1 - taker)
    wins = sum(1 for t in trips if t > 0)
    return {
        "final": final, "budget": float(cfg["budget"]), "fees": fees_paid, "trips": len(trips),
        "wins": wins, "max_dd": max_dd, "buy_hold": bh, "in_position": eth > 0,
        "bars": n,
    }


def print_report(res, cfg, taker):
    b = res["budget"]
    ret = (res["final"] / b - 1) * 100
    print()
    print("=" * 60)
    print(f" BACKTEST {cfg['symbol']} | bougies {cfg['timeframe']} | {res['bars']} bougies")
    print(f" Moyennes {cfg['fast']}/{cfg['slow']} | écart d'entrée {cfg['min_gap_pct']} % | stop-loss {cfg['stop_loss_pct']} %")
    print(f" Frais par transaction (taker) : {taker * 100:.2f} % | glissement : {cfg['slippage_pct']} %")
    print("=" * 60)
    print(f" Capital de départ        : {b:,.2f}")
    print(f" Valeur finale (nette)    : {res['final']:,.2f}  ({ret:+.1f} %)")
    if res["buy_hold"] is not None:
        bhr = (res["buy_hold"] / b - 1) * 100
        print(f" Simplement acheter/garder: {res['buy_hold']:,.2f}  ({bhr:+.1f} %)  <- point de comparaison")
    print(f" Frais payés au total     : {res['fees']:,.2f}  ({res['fees'] / b * 100:.1f} % du capital)")
    print(f" Allers-retours           : {res['trips']}  (gagnants : {res['wins']})")
    print(f" Perte maximale temporaire: {res['max_dd'] * 100:.1f} %")
    if res["in_position"]:
        print(" (Une position était encore ouverte à la fin du test.)")
    print("=" * 60)
    print(" Un backtest ne prédit pas l'avenir. Si le résultat ne bat même pas")
    print(" 'acheter/garder', ça veut dire que la stratégie n'apporte rien.")
    print()


def cmd_backtest(args, cfg):
    candles = None
    taker = cfg["fallback_fee_taker_pct"] / 100.0
    if args.demo:
        log("Données de démonstration (fausses, générées au hasard) : sert seulement à vérifier l'installation.")
        candles = demo_candles()
        if cfg["fee_taker_pct"] is not None:
            taker = cfg["fee_taker_pct"] / 100.0
    elif args.csv:
        candles = read_csv(args.csv)
        if cfg["fee_taker_pct"] is not None:
            taker = cfg["fee_taker_pct"] / 100.0
    else:
        ex = make_exchange(False)
        _, taker = get_fees(ex, cfg, False)
        log(f"Téléchargement des bougies {cfg['timeframe']} de {cfg['symbol']} sur Kraken...")
        candles = ex.fetch_ohlcv(cfg["symbol"], cfg["timeframe"], limit=720)
        candles = candles[:-1]  # on enlève la bougie encore ouverte
        out = os.path.join(HERE, "data.csv")
        write_csv(out, candles)
        log(f"{len(candles)} bougies reçues (Kraken en donne 720 au maximum). Copie enregistrée : data.csv")
    if len(candles) < cfg["slow"] + 5:
        sys.exit("Pas assez de bougies pour ce test.")
    res = backtest(candles, cfg, taker)
    print_report(res, cfg, taker)


# --------------------------------------------------------------------------
# Journal et état
# --------------------------------------------------------------------------
def journal(mode, side, price, qty, fee, note=""):
    path = os.path.join(HERE, "trades.csv")
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "mode", "cote", "prix", "quantite", "frais", "note"])
        w.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), mode, side,
                    f"{price:.4f}", f"{qty:.8f}", f"{fee:.4f}", note])


def load_state(mode):
    path = os.path.join(HERE, f"state_{mode}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(mode, state):
    path = os.path.join(HERE, f"state_{mode}.json")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)


# --------------------------------------------------------------------------
# Courtiers : simulation et réel
# --------------------------------------------------------------------------
class PaperBroker:
    name = "paper"

    def __init__(self, cfg, state, taker):
        self.cfg, self.s, self.taker = cfg, state, taker
        self.s.setdefault("cash", float(cfg["budget"]))
        self.s.setdefault("eth", 0.0)

    def in_position(self, price):
        return self.s["eth"] > 0

    def equity(self, price):
        return self.s["cash"] + self.s["eth"] * price

    def buy(self, price, bar_key):
        slip = self.cfg["slippage_pct"] / 100.0
        fill = price * (1 + slip)
        spend = min(float(self.cfg["budget"]), self.s["cash"])
        qty = spend / (fill * (1 + self.taker))
        fee = qty * fill * self.taker
        self.s["cash"] -= qty * fill + fee
        self.s["eth"] += qty
        return {"price": fill, "qty": qty, "fee": fee}

    def sell(self, price, bar_key):
        slip = self.cfg["slippage_pct"] / 100.0
        fill = price * (1 - slip)
        qty = self.s["eth"]
        gross = qty * fill
        fee = gross * self.taker
        self.s["cash"] += gross - fee
        self.s["eth"] = 0.0
        return {"price": fill, "qty": qty, "fee": fee}


class LiveBroker:
    name = "live"

    def __init__(self, ex, cfg, state, taker):
        self.ex, self.cfg, self.s, self.taker = ex, cfg, state, taker
        self.sym = cfg["symbol"]
        self.market = ex.market(self.sym)
        self.base, self.quote = self.market["base"], self.market["quote"]
        self.min_amount = ((self.market.get("limits") or {}).get("amount") or {}).get("min") or 0.001
        self.min_cost = ((self.market.get("limits") or {}).get("cost") or {}).get("min") or 0.0

    def balances(self):
        bal = self.ex.fetch_balance()
        quote_free = float((bal.get(self.quote) or {}).get("free") or 0.0)
        base_free = float((bal.get(self.base) or {}).get("free") or 0.0)
        return quote_free, base_free

    def in_position(self, price):
        _, base_free = self.balances()
        return base_free >= self.min_amount

    def equity(self, price):
        quote_free, base_free = self.balances()
        return quote_free + base_free * price

    def _place(self, side, amount, px):
        params = {}
        validate = bool(self.cfg["live_validate_only"])
        if validate:
            params["validate"] = True
        if self.cfg["order_type"] == "limit":
            params["postOnly"] = True
            return self.ex.create_order(self.sym, "limit", side, amount, px, params)
        return self.ex.create_order(self.sym, "market", side, amount, None, params)

    def _wait_fill(self, order):
        oid = order.get("id")
        if not oid:
            return None
        timeout = self.cfg["limit_timeout_s"] if self.cfg["order_type"] == "limit" else 20
        deadline = time.time() + timeout
        o = order
        while True:
            time.sleep(3)
            o = self.ex.fetch_order(oid, self.sym)
            if o.get("status") in ("closed", "canceled", "expired"):
                break
            if time.time() > deadline:
                break
        if o.get("status") == "open":
            try:
                self.ex.cancel_order(oid, self.sym)
                log("Ordre non exécuté à temps : annulé. Le bot réessaiera au prochain tour.")
            except Exception as e:
                log(f"Annulation impossible ({e}).")
            time.sleep(2)
            try:
                o = self.ex.fetch_order(oid, self.sym)
            except Exception:
                pass
        filled = float(o.get("filled") or 0.0)
        if filled <= 0:
            return None
        avg = o.get("average") or o.get("price") or 0.0
        fee = float(((o.get("fee") or {}).get("cost")) or 0.0)
        return {"price": float(avg), "qty": filled, "fee": fee}

    def _skip_validated(self, side, bar_key):
        key = f"{side}:{bar_key}"
        if self.cfg["live_validate_only"] and self.s.get("validated") == key:
            return True
        return False

    def buy(self, price, bar_key):
        if self._skip_validated("buy", bar_key):
            return None
        quote_free, _ = self.balances()
        spend = min(float(self.cfg["budget"]), quote_free)
        ticker = self.ex.fetch_ticker(self.sym)
        px = float(self.ex.price_to_precision(self.sym, ticker["bid"] if self.cfg["order_type"] == "limit" else ticker["last"]))
        amount = float(self.ex.amount_to_precision(self.sym, spend / (px * (1 + self.taker))))
        if amount < self.min_amount or amount * px < self.min_cost:
            log(f"Achat impossible : montant trop petit ({amount} {self.base}, minimum {self.min_amount}).")
            return None
        order = self._place("buy", amount, px)
        if self.cfg["live_validate_only"]:
            log(f"[VALIDATION] Kraken a accepté l'ordre d'achat de {amount} {self.base} vers {px}. Rien n'a été exécuté.")
            self.s["validated"] = f"buy:{bar_key}"
            journal("live-validation", "achat", px, amount, 0.0, "validé par Kraken, non exécuté")
            return None
        return self._wait_fill(order)

    def sell(self, price, bar_key):
        if self._skip_validated("sell", bar_key):
            return None
        _, base_free = self.balances()
        ticker = self.ex.fetch_ticker(self.sym)
        px = float(self.ex.price_to_precision(self.sym, ticker["ask"] if self.cfg["order_type"] == "limit" else ticker["last"]))
        amount = float(self.ex.amount_to_precision(self.sym, base_free))
        if amount < self.min_amount:
            log("Vente impossible : quantité sous le minimum de Kraken.")
            return None
        order = self._place("sell", amount, px)
        if self.cfg["live_validate_only"]:
            log(f"[VALIDATION] Kraken a accepté l'ordre de vente de {amount} {self.base} vers {px}. Rien n'a été exécuté.")
            self.s["validated"] = f"sell:{bar_key}"
            journal("live-validation", "vente", px, amount, 0.0, "validé par Kraken, non exécuté")
            return None
        return self._wait_fill(order)


# --------------------------------------------------------------------------
# Boucle principale (paper et live)
# --------------------------------------------------------------------------
def run(mode, cfg, ex=None, max_loops=None, sleeper=time.sleep):
    live = mode == "live"
    if ex is None:
        ex = make_exchange(live)
    ex.load_markets()
    maker, taker = get_fees(ex, cfg, live)
    sym = cfg["symbol"]
    state = load_state(mode)
    broker = LiveBroker(ex, cfg, state, taker) if live else PaperBroker(cfg, state, taker)

    log(f"Mode {mode.upper()} | {sym} | bougies {cfg['timeframe']} | frais maker {maker * 100:.2f} % / taker {taker * 100:.2f} %")
    if live and cfg["live_validate_only"]:
        log("VALIDATION SEULEMENT : Kraken vérifie chaque ordre mais n'exécute rien.")
    if live and not cfg["live_validate_only"]:
        print("\n*** MODE RÉEL : le bot va passer de vrais ordres avec ton argent. ***")
        print(f"Budget maximal : {cfg['budget']} | stop-loss : {cfg['stop_loss_pct']} % | perte max : {cfg['max_loss_pct']} %")
        if input("Tape OUI en majuscules pour continuer : ").strip() != "OUI":
            sys.exit("Annulé.")

    loops = 0
    while True:
        loops += 1
        if max_loops is not None and loops > max_loops:
            break
        if os.path.exists(os.path.join(HERE, "STOP")):
            log("Fichier STOP détecté : arrêt du bot (la position éventuelle est conservée).")
            break
        try:
            candles = ex.fetch_ohlcv(sym, cfg["timeframe"], limit=cfg["history_bars"])
            price = float(ex.fetch_ticker(sym)["last"])
            closed = candles[:-1]
            if len(closed) < cfg["slow"] + 2:
                log("Pas assez de bougies pour calculer les moyennes.")
                sleeper(cfg["poll_seconds"])
                continue
            closes = [c[4] for c in closed]
            f = sma_series(closes, cfg["fast"])[-1]
            s = sma_series(closes, cfg["slow"])[-1]
            bar_ts = closed[-1][0]

            # Initialisation au premier lancement
            if "last_bar_ts" not in state:
                bullish = want_long(f, s, False, cfg["min_gap_pct"])
                in_pos = broker.in_position(price)
                state.update({
                    "last_bar_ts": bar_ts, "target_long": in_pos, "armed": not bullish,
                    "bars_since_exit": 999, "entry": price if in_pos else None,
                    "start_equity": broker.equity(price), "halted": False,
                })
                log(f"Premier lancement. Valeur de départ : {state['start_equity']:.2f}. "
                    + ("Le marché est déjà haussier : j'attends un nouveau croisement avant d'acheter."
                       if bullish else "En attente d'un signal d'achat."))
                if in_pos:
                    log("Tu détiens déjà de l'ETH : le stop-loss sera calculé à partir du prix actuel.")
                save_state(mode, state)

            # Nouvelle bougie fermée : on réévalue le signal
            if bar_ts != state["last_bar_ts"]:
                state["last_bar_ts"] = bar_ts
                state["bars_since_exit"] = state.get("bars_since_exit", 999) + 1
                cur = state["target_long"]
                want = want_long(f, s, cur, cfg["min_gap_pct"])
                if not cur:
                    if not want:
                        state["armed"] = True
                    elif (not state["armed"]) or state["bars_since_exit"] < cfg["cooldown_bars"]:
                        want = False
                if want != cur:
                    log(f"Nouveau signal : {'ACHAT' if want else 'VENTE'} (moyenne rapide {f:.2f} / lente {s:.2f})")
                state["target_long"] = want
                state["validated"] = None
                save_state(mode, state)

            in_pos = broker.in_position(price)

            # Stop-loss
            if in_pos and state.get("entry") and price <= state["entry"] * (1 - cfg["stop_loss_pct"] / 100.0):
                if state["target_long"]:
                    log(f"STOP-LOSS touché (prix {price:.2f}, entrée {state['entry']:.2f}). Vente.")
                    state["target_long"] = False
                    state["bars_since_exit"] = 0
                    state["validated"] = None

            # Coupe-circuit : perte maximale
            equity = broker.equity(price)
            if not state.get("halted") and equity < state["start_equity"] * (1 - cfg["max_loss_pct"] / 100.0):
                log(f"COUPE-CIRCUIT : valeur {equity:.2f} sous la limite de perte ({cfg['max_loss_pct']} %). Je vends et j'arrête.")
                state["halted"] = True
                state["target_long"] = False

            bar_key = state["last_bar_ts"]
            # Rapprocher la position réelle de la cible
            if state["target_long"] and not in_pos:
                r = broker.buy(price, bar_key)
                if r:
                    state["entry"] = r["price"]
                    journal(mode, "achat", r["price"], r["qty"], r["fee"])
                    log(f"ACHAT : {r['qty']:.6f} à {r['price']:.2f} (frais {r['fee']:.2f})")
                save_state(mode, state)
            elif (not state["target_long"]) and in_pos:
                r = broker.sell(price, bar_key)
                if r:
                    journal(mode, "vente", r["price"], r["qty"], r["fee"])
                    log(f"VENTE : {r['qty']:.6f} à {r['price']:.2f} (frais {r['fee']:.2f})")
                    state["entry"] = None
                    state["bars_since_exit"] = 0
                save_state(mode, state)

            if state.get("halted") and not broker.in_position(price):
                log("Position fermée. Le bot s'arrête après le coupe-circuit.")
                save_state(mode, state)
                break

            log(f"Prix {price:.2f} | moyennes {f:.2f}/{s:.2f} | "
                f"{'EN POSITION' if broker.in_position(price) else 'hors position'} | valeur {broker.equity(price):.2f}")
        except KeyboardInterrupt:
            log("Arrêt demandé. La position éventuelle est conservée.")
            break
        except Exception as e:
            log(f"Erreur (je réessaie au prochain tour) : {e}")
        sleeper(cfg["poll_seconds"])
    return state


def cmd_check(cfg):
    ex = make_exchange(True)
    ex.load_markets()
    bal = ex.fetch_balance()
    log("Connexion à Kraken réussie avec ta clé. Soldes disponibles :")
    shown = False
    for cur, amt in (bal.get("free") or {}).items():
        if amt:
            print(f"   {cur}: {amt}")
            shown = True
    if not shown:
        print("   (aucun solde pour l'instant)")
    print("Aucun ordre n'a été passé.")


def main():
    ap = argparse.ArgumentParser(description="Bot ETH pour Kraken")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backtest")
    b.add_argument("--demo", action="store_true")
    b.add_argument("--csv")
    pp = sub.add_parser("paper")
    pp.add_argument("--once", action="store_true",
                    help="un seul passage puis arrêt (pour GitHub Actions)")
    sub.add_parser("check")
    sub.add_parser("live")
    args = ap.parse_args()
    cfg = load_config()
    try:
        import ccxt
        network_errors = (ccxt.NetworkError,)
        auth_errors = (ccxt.AuthenticationError, ccxt.PermissionDenied)
    except ImportError:
        sys.exit("La bibliothèque ccxt manque. Lance : pip install -r requirements.txt")
    try:
        if args.cmd == "backtest":
            cmd_backtest(args, cfg)
        elif args.cmd == "paper":
            if args.once:
                run("paper", cfg, max_loops=1, sleeper=lambda s: None)
            else:
                run("paper", cfg)
        elif args.cmd == "check":
            cmd_check(cfg)
        elif args.cmd == "live":
            run("live", cfg)
    except network_errors as e:
        sys.exit(f"\nImpossible de joindre Kraken. Vérifie ta connexion internet puis réessaie.\n(Détail technique : {e})")
    except auth_errors as e:
        sys.exit("\nKraken a refusé ta clé API. Vérifie qu'elle est bien copiée dans .env et qu'elle a "
                 f"les bonnes permissions (sans retrait).\n(Détail technique : {e})")
    except ccxt.BadSymbol:
        sys.exit(f"\nKraken ne connaît pas la paire {cfg['symbol']}. Vérifie 'symbol' dans config.json.")


if __name__ == "__main__":
    main()
