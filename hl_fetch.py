#!/usr/bin/env python3
"""
Crypto Perp -> Postgres -- Fetch OHLCV via CCXT (Binance Futures USDT-M).
Backfill historique long (5+ ans) + boucle live.

Tables: candles_crypto_<symbol>_<tf>  (TFs = 1h, 4h)
Schema identique au fetch MT5 -> backtest_engine consomme directement.

Pourquoi Binance vs Hyperliquid native: HL API limite a 5000 candles/TF
(= 7 mois 1h, 2.3 ans 4h). Binance Futures: 5+ ans full history.
Basis HL/Binance ~10-30 bps sur top perps -> acceptable pour BT robuste.

Source: top 20 market cap CoinGecko (mai 2026) hors stables/wrapped.
4 absents (tokens CEX/niche): FIGR (#7), WBT (#9), LEO (#13), CC (#18).
17 actifs sur Binance Futures USDT-M.

Usage:
  python hl_fetch.py --once                   # backfill max histo, single pass
  python hl_fetch.py                          # boucle continue (live)
  python hl_fetch.py --pairs BTC,ETH --once   # backfill specifique
  python hl_fetch.py --tfs 1h --once          # subset TF
"""
import os, re, sys, time, argparse
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import ccxt
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, Column, BigInteger, String, Float, Numeric, select, desc
from sqlalchemy.dialects.postgresql import insert as pg_insert

UTC = timezone.utc
LOOP_SLEEP = 30
BATCH_LIMIT = 1500  # Binance Futures cap par requete
BACKFILL_START_MS = int(datetime(2020, 1, 1, tzinfo=UTC).timestamp() * 1000)
TFS_DEFAULT = ['1h', '4h']
TF_MS = {'15m': 900_000, '1h': 3_600_000, '4h': 14_400_000, '1d': 86_400_000}

# Top 20 CoinGecko hors stables/wrapped, filtre par disponibilite Binance Futures USDT-M.
# Format CCXT pour USDT-margined perp: 'BTC/USDT:USDT'
COIN_MAP = {
    'BTC':  {'db': 'BTCUSD',  'ccxt': 'BTC/USDT:USDT'},
    'ETH':  {'db': 'ETHUSD',  'ccxt': 'ETH/USDT:USDT'},
    'XRP':  {'db': 'XRPUSD',  'ccxt': 'XRP/USDT:USDT'},
    'BNB':  {'db': 'BNBUSD',  'ccxt': 'BNB/USDT:USDT'},
    'SOL':  {'db': 'SOLUSD',  'ccxt': 'SOL/USDT:USDT'},
    'TRX':  {'db': 'TRXUSD',  'ccxt': 'TRX/USDT:USDT'},
    'DOGE': {'db': 'DOGEUSD', 'ccxt': 'DOGE/USDT:USDT'},
    'HYPE': {'db': 'HYPEUSD', 'ccxt': 'HYPE/USDT:USDT'},
    'ZEC':  {'db': 'ZECUSD',  'ccxt': 'ZEC/USDT:USDT'},
    'ADA':  {'db': 'ADAUSD',  'ccxt': 'ADA/USDT:USDT'},
    'BCH':  {'db': 'BCHUSD',  'ccxt': 'BCH/USDT:USDT'},
    'LINK': {'db': 'LINKUSD', 'ccxt': 'LINK/USDT:USDT'},
    'XMR':  {'db': 'XMRUSD',  'ccxt': 'XMR/USDT:USDT'},
    'TON':  {'db': 'TONUSD',  'ccxt': 'TON/USDT:USDT'},
    'XLM':  {'db': 'XLMUSD',  'ccxt': 'XLM/USDT:USDT'},
    'LTC':  {'db': 'LTCUSD',  'ccxt': 'LTC/USDT:USDT'},
}
# Note: CC (#18 Canton) absent de Binance Futures -> exclu.

DEFAULT_PAIRS = list(COIN_MAP.keys())


def sanitize_name(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def get_pg_engine():
    load_dotenv()
    host = os.getenv("PG_HOST", "127.0.0.1")
    port = os.getenv("PG_PORT", "5432")
    db = os.getenv("PG_DB", "postgres")
    user = os.getenv("PG_USER", "postgres")
    pwd = os.getenv("PG_PASSWORD", "postgres")
    return create_engine(
        f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}?sslmode=disable",
        pool_pre_ping=True, future=True,
    )


def get_exchange():
    return ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'},
    })


def make_table(engine, table_name):
    meta = MetaData()
    table = Table(table_name, meta,
        Column("ts", BigInteger, primary_key=True),
        Column("ts_utc", String),
        Column("open", Numeric(20, 8)),
        Column("high", Numeric(20, 8)),
        Column("low", Numeric(20, 8)),
        Column("close", Numeric(20, 8)),
        Column("volume", Float),
        Column("exchange", String(16)),
        Column("symbol", String(32)),
        Column("base", String(8)),
        Column("quote", String(8)),
        Column("timeframe", String(8)),
    )
    meta.create_all(engine, checkfirst=True)
    return table


def fetch_and_store(engine, exchange, coin, tf):
    info = COIN_MAP[coin]
    db_sym = info['db']
    ccxt_sym = info['ccxt']
    table_name = f"candles_crypto_{sanitize_name(db_sym)}_{tf}"
    table = make_table(engine, table_name)
    tf_ms = TF_MS[tf]

    last_ts = None
    with engine.connect() as c:
        row = c.execute(select(table.c.ts).order_by(desc(table.c.ts)).limit(1)).fetchone()
        if row: last_ts = int(row.ts)

    since_ms = (last_ts + 1) if last_ts else BACKFILL_START_MS
    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    inserted = 0
    batch_num = 0

    while since_ms < now_ms:
        try:
            ohlcv = exchange.fetch_ohlcv(ccxt_sym, tf, since=since_ms, limit=BATCH_LIMIT)
        except ccxt.BadSymbol:
            print(f"[SKIP] {coin} {tf}: pas listed sur Binance Futures", flush=True)
            return
        except Exception as e:
            print(f"[WARN] {coin} {tf}: {e}", flush=True)
            time.sleep(2)
            break

        if not ohlcv:
            break

        # Drop la derniere bougie (potentiellement en cours)
        if len(ohlcv) > 1:
            ohlcv = ohlcv[:-1]
        else:
            break

        rows = []
        for candle in ohlcv:
            ts, o, h, l, c, v = candle
            if last_ts and ts <= last_ts: continue
            rows.append({
                "ts": ts,
                "ts_utc": datetime.fromtimestamp(ts / 1000, tz=UTC).isoformat(timespec="seconds"),
                "open": Decimal(str(o)), "high": Decimal(str(h)),
                "low": Decimal(str(l)), "close": Decimal(str(c)),
                "volume": float(v),
                "exchange": "binance",
                "symbol": db_sym,
                "base": coin, "quote": "USD",
                "timeframe": tf,
            })
            last_ts = ts

        if rows:
            with engine.begin() as conn:
                res = conn.execute(
                    pg_insert(table).values(rows).on_conflict_do_nothing(index_elements=["ts"]))
                inserted += (res.rowcount or 0)
            batch_num += 1
            f_dt = datetime.fromtimestamp(rows[0]['ts'] / 1000, tz=UTC).strftime('%Y-%m-%d')
            l_dt = datetime.fromtimestamp(rows[-1]['ts'] / 1000, tz=UTC).strftime('%Y-%m-%d')
            print(f"  {coin} [{tf}] batch {batch_num}: +{len(rows)} ({f_dt} -> {l_dt}) cum={inserted}",
                  flush=True)

        # Pagination: avancer au dernier ts + 1
        since_ms = ohlcv[-1][0] + 1

    print(f"[DONE] {coin} ({db_sym}) [{tf}]: {inserted} candles inserees.", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=str, default=None,
                    help="Coins comma-separated (BTC,ETH,SOL)")
    ap.add_argument("--tfs", type=str, default=None,
                    help="Timeframes comma-separated. Default = 1h,4h")
    ap.add_argument("--once", action="store_true",
                    help="Single pass (backfill mode, no loop)")
    args = ap.parse_args()

    pairs = ([x.strip().upper() for x in args.pairs.split(",") if x.strip()]
             if args.pairs else DEFAULT_PAIRS)
    tfs = ([x.strip() for x in args.tfs.split(",") if x.strip()]
           if args.tfs else TFS_DEFAULT)

    for c in pairs:
        if c not in COIN_MAP:
            print(f"[ERR] {c} pas dans COIN_MAP. Disponibles: {list(COIN_MAP.keys())}")
            sys.exit(1)
    for t in tfs:
        if t not in TF_MS:
            print(f"[ERR] TF {t} non supporte. Disponibles: {list(TF_MS.keys())}")
            sys.exit(1)

    engine = get_pg_engine()
    exchange = get_exchange()
    print(f"[INIT] Binance Futures USDT-M fetch: {len(pairs)} coins, TFs={tfs}", flush=True)

    try:
        if args.once:
            print(f"[BACKFILL] {datetime.now(UTC).isoformat(timespec='seconds')}", flush=True)
            for tf in tfs:
                for coin in pairs:
                    fetch_and_store(engine, exchange, coin, tf)
            print("[DONE] Backfill complete.", flush=True)
        else:
            while True:
                print(f"[LOOP] {datetime.now(UTC).isoformat(timespec='seconds')}", flush=True)
                for tf in tfs:
                    for coin in pairs:
                        fetch_and_store(engine, exchange, coin, tf)
                time.sleep(LOOP_SLEEP)
    except KeyboardInterrupt:
        print("[STOP]")


if __name__ == "__main__":
    main()
