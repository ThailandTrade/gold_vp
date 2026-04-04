#!/usr/bin/env python3
"""
Crypto -> Postgres — Fetch OHLCV 5m candles via CCXT (Binance Futures).
Backfill historique + boucle live.
Usage:
  python hl_fetch.py --once                     # backfill 2 ans, single pass
  python hl_fetch.py                            # boucle continue (live)
  python hl_fetch.py --pairs BTC,ETH --once     # backfill specifique
"""
import os, re, sys, time, argparse
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP

import ccxt
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, Column, BigInteger, String, Float, Numeric, select, desc
from sqlalchemy.dialects.postgresql import insert as pg_insert

UTC = timezone.utc
TF = "5m"
TF_MS = 300_000  # 5 minutes
BATCH_LIMIT = 1000  # Binance max per request
LOOP_SLEEP = 1
BACKFILL_DAYS = 730  # 2 ans

# Coin -> DB symbol name + CCXT symbol
COIN_MAP = {
    'BTC': {'db': 'BTCUSD', 'ccxt': 'BTC/USDT:USDT'},
    'ETH': {'db': 'ETHUSD', 'ccxt': 'ETH/USDT:USDT'},
    'SOL': {'db': 'SOLUSD', 'ccxt': 'SOL/USDT:USDT'},
    'BNB': {'db': 'BNBUSD', 'ccxt': 'BNB/USDT:USDT'},
    'XRP': {'db': 'XRPUSD', 'ccxt': 'XRP/USDT:USDT'},
    'ADA': {'db': 'ADAUSD', 'ccxt': 'ADA/USDT:USDT'},
    'DOGE': {'db': 'DOGEUSD', 'ccxt': 'DOGE/USDT:USDT'},
    'LTC': {'db': 'LTCUSD', 'ccxt': 'LTC/USDT:USDT'},
    'BCH': {'db': 'BCHUSD', 'ccxt': 'BCH/USDT:USDT'},
    'DOT': {'db': 'DOTUSD', 'ccxt': 'DOT/USDT:USDT'},
    'LINK': {'db': 'LNKUSD', 'ccxt': 'LINK/USDT:USDT'},
    'XMR': {'db': 'XMRUSD', 'ccxt': 'XMR/USDT:USDT'},
    'AVAX': {'db': 'AVAUSD', 'ccxt': 'AVAX/USDT:USDT'},
    'ETC': {'db': 'ETCUSD', 'ccxt': 'ETC/USDT:USDT'},
    'NEO': {'db': 'NEOUSD', 'ccxt': 'NEO/USDT:USDT'},
    'HYPE': {'db': 'HYPEUSD', 'ccxt': 'HYPE/USDT:USDT'},
    'TAO': {'db': 'TAOUSD', 'ccxt': 'TAO/USDT:USDT'},
    'ZEC': {'db': 'ZECUSD', 'ccxt': 'ZEC/USDT:USDT'},
    'NEAR': {'db': 'NEARUSD', 'ccxt': 'NEAR/USDT:USDT'},
    'ALGO': {'db': 'ALGOUSD', 'ccxt': 'ALGO/USDT:USDT'},
    'SUI': {'db': 'SUIUSD', 'ccxt': 'SUI/USDT:USDT'},
    'FET': {'db': 'FETUSD', 'ccxt': 'FET/USDT:USDT'},
    'AAVE': {'db': 'AAVEUSD', 'ccxt': 'AAVE/USDT:USDT'},
    'UNI': {'db': 'UNIUSD', 'ccxt': 'UNI/USDT:USDT'},
    'PEPE': {'db': 'PEPEUSD', 'ccxt': '1000PEPE/USDT:USDT'},
}

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
    return create_engine(f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}?sslmode=disable",
                         pool_pre_ping=True, future=True)

def get_exchange():
    return ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'},
    })

def fetch_and_store(engine, exchange, coin):
    info = COIN_MAP.get(coin)
    if not info:
        print(f"[WARN] {coin}: not in COIN_MAP"); return
    db_sym = info['db']
    ccxt_sym = info['ccxt']
    table_name = f"candles_mt5_{sanitize_name(db_sym)}_5m"

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

    # Dernier ts en DB
    last_ts = None
    with engine.connect() as c:
        row = c.execute(select(table.c.ts).order_by(desc(table.c.ts)).limit(1)).fetchone()
        if row: last_ts = int(row.ts)

    # Start
    if last_ts:
        since_ms = last_ts + 1
    else:
        since_ms = int((datetime.now(UTC) - timedelta(days=BACKFILL_DAYS)).timestamp() * 1000)

    now_ms = int(datetime.now(UTC).timestamp() * 1000)
    inserted = 0
    batch_num = 0

    while since_ms < now_ms:
        try:
            ohlcv = exchange.fetch_ohlcv(ccxt_sym, TF, since=since_ms, limit=BATCH_LIMIT)
        except Exception as e:
            print(f"[WARN] {coin}: fetch error: {e}")
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
            ts, o, h, l, c, v = candle[0], candle[1], candle[2], candle[3], candle[4], candle[5]
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
                "timeframe": TF,
            })
            last_ts = ts

        if rows:
            with engine.begin() as conn:
                res = conn.execute(pg_insert(table).values(rows).on_conflict_do_nothing(index_elements=["ts"]))
                inserted += (res.rowcount or 0)
            batch_num += 1
            first_dt = datetime.fromtimestamp(rows[0]['ts'] / 1000, tz=UTC).strftime('%Y-%m-%d')
            last_dt = datetime.fromtimestamp(rows[-1]['ts'] / 1000, tz=UTC).strftime('%Y-%m-%d')
            print(f"  {coin} batch {batch_num}: +{len(rows)} ({first_dt} -> {last_dt}) total={inserted}", flush=True)

        # Pagination: avancer au dernier timestamp + 1
        since_ms = ohlcv[-1][0] + 1

    print(f"[DONE] {coin} ({db_sym}): {inserted} candles total.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=str, default=None, help="Coins comma-separated (BTC,ETH,SOL)")
    ap.add_argument("--once", action="store_true", help="Single pass (backfill mode, no loop)")
    args = ap.parse_args()

    if args.pairs:
        pairs = [x.strip().upper() for x in args.pairs.split(",") if x.strip()]
    else:
        pairs = DEFAULT_PAIRS

    engine = get_pg_engine()
    exchange = get_exchange()

    print(f"[INIT] CCXT Binance Futures fetch: {', '.join(pairs)} ({TF})")

    try:
        if args.once:
            print(f"[BACKFILL] {datetime.now(UTC).isoformat(timespec='seconds')}")
            for coin in pairs:
                fetch_and_store(engine, exchange, coin)
            print("[DONE] Backfill complete.")
        else:
            while True:
                print(f"[LOOP] {datetime.now(UTC).isoformat(timespec='seconds')}")
                for coin in pairs:
                    fetch_and_store(engine, exchange, coin)
                time.sleep(LOOP_SLEEP)
    except KeyboardInterrupt:
        print("[STOP]")

if __name__ == "__main__":
    main()
