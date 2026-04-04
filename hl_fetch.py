#!/usr/bin/env python3
"""
Hyperliquid -> Postgres — Fetch OHLCV 5m candles.
Meme logique que mt5_fetch_clean.py: boucle continue, drop last candle (potentiellement ouverte).
Usage: python hl_fetch.py [--pairs BTC,ETH,SOL]
"""
import os, re, sys, time, argparse
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, Column, BigInteger, String, Float, Numeric, select, desc, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

UTC = timezone.utc
HL_API = "https://api.hyperliquid.xyz/info"
TF = "5m"
TF_MS = 300_000  # 5 minutes
MAX_CANDLES = 5000  # HL API limit
LOOP_SLEEP = 1

# Mapping coin -> DB symbol name (HL utilise "BTC", on stocke "BTCUSD")
COIN_MAP = {
    'BTC': 'BTCUSD', 'ETH': 'ETHUSD', 'SOL': 'SOLUSD', 'BNB': 'BNBUSD',
    'XRP': 'XRPUSD', 'ADA': 'ADAUSD', 'DOGE': 'DOGEUSD', 'LTC': 'LTCUSD',
    'BCH': 'BCHUSD', 'DOT': 'DOTUSD', 'LINK': 'LNKUSD', 'XMR': 'XMRUSD',
    'AVAX': 'AVAUSD', 'ETC': 'ETCUSD', 'NEO': 'NEOUSD',
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

def fetch_candles(coin, start_ms, end_ms):
    """Fetch candles from HL API. Returns list of dicts."""
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": coin,
            "interval": TF,
            "startTime": int(start_ms),
            "endTime": int(end_ms),
        }
    }
    try:
        resp = requests.post(HL_API, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[WARN] {coin}: fetch error: {e}")
        return []

def fetch_and_store(engine, coin):
    db_sym = COIN_MAP.get(coin, f"{coin}USD")
    table_name = f"candles_mt5_{sanitize_name(db_sym)}_5m"

    meta = MetaData()
    table = Table(table_name, meta,
        Column("ts", BigInteger, primary_key=True),
        Column("ts_utc", String),
        Column("open", Numeric(20, 5)),
        Column("high", Numeric(20, 5)),
        Column("low", Numeric(20, 5)),
        Column("close", Numeric(20, 5)),
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

    # Start: 2 bougies avant last_ts (meme logique que mt5_fetch_clean)
    if last_ts:
        start_ms = last_ts - 2 * TF_MS + 1
    else:
        start_ms = int((datetime.now(UTC) - timedelta(days=365)).timestamp() * 1000)

    # End: loin dans le futur (on laisse l'API retourner tout)
    end_ms = int((datetime.now(UTC) + timedelta(hours=24)).timestamp() * 1000)

    inserted = 0
    cur_start = start_ms

    with engine.begin() as conn:
        while cur_start < end_ms:
            cur_end = cur_start + TF_MS * MAX_CANDLES
            if cur_end > end_ms: cur_end = end_ms

            candles = fetch_candles(coin, cur_start, cur_end)
            if not candles:
                cur_start = cur_end
                continue

            # Drop la derniere bougie (potentiellement en cours)
            if len(candles) > 1:
                candles = candles[:-1]
            else:
                cur_start = cur_end
                continue

            rows = []
            for c in candles:
                ts_utc = int(c['t'])  # open millis, deja en UTC
                if last_ts and ts_utc <= last_ts: continue

                o = Decimal(str(c['o']))
                h = Decimal(str(c['h']))
                l = Decimal(str(c['l']))
                cl = Decimal(str(c['c']))
                v = float(c['v'])

                rows.append({
                    "ts": ts_utc,
                    "ts_utc": datetime.fromtimestamp(ts_utc / 1000, tz=UTC).isoformat(timespec="seconds"),
                    "open": o, "high": h, "low": l, "close": cl,
                    "volume": v,
                    "exchange": "hyperliquid",
                    "symbol": db_sym,
                    "base": coin, "quote": "USD",
                    "timeframe": TF,
                })
                last_ts = ts_utc

            if rows:
                res = conn.execute(pg_insert(table).values(rows).on_conflict_do_nothing(index_elements=["ts"]))
                inserted += (res.rowcount or 0)

            # Pagination: avancer au dernier timestamp + 1
            if candles:
                cur_start = int(candles[-1]['t']) + 1
            else:
                cur_start = cur_end

    if inserted > 0:
        print(f"[DONE] {coin} ({db_sym}): +{inserted} candles.")
    else:
        print(f"[INFO] {coin}: no new bars.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", type=str, default=None, help="Coins comma-separated (BTC,ETH,SOL)")
    args = ap.parse_args()

    if args.pairs:
        pairs = [x.strip().upper() for x in args.pairs.split(",") if x.strip()]
    else:
        pairs = DEFAULT_PAIRS

    engine = get_pg_engine()

    print(f"[INIT] Hyperliquid fetch: {', '.join(pairs)} ({TF})")

    try:
        while True:
            print(f"[LOOP] {datetime.now(UTC).isoformat(timespec='seconds')}")
            for coin in pairs:
                fetch_and_store(engine, coin)
            time.sleep(LOOP_SLEEP)
    except KeyboardInterrupt:
        print("[STOP]")

if __name__ == "__main__":
    main()
