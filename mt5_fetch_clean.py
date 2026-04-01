#!/usr/bin/env python3
"""
MT5 -> Postgres — Fetch OHLC brut (pas de modification des prix).
Stocke les vrais OHLC de MT5 sans indicateurs.
Usage: python mt5_fetch_clean.py [--pairs XAUUSD] [--to 2026-01-01T00:00:00Z]
"""
import os, re, sys, time, argparse, csv
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

import MetaTrader5 as mt5
from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData, Table, Column, BigInteger, String, Float, Numeric, select, desc, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

UTC = timezone.utc
BATCH_BARS = 10000

TF_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000, "30m": 1_800_000,
    "1h": 3_600_000, "2h": 7_200_000, "4h": 14_400_000, "6h": 21_600_000,
    "8h": 28_800_000, "12h": 43_200_100, "1d": 86_400_000, "1w": 604_800_000
}
TF_MT5 = {
    "1m": mt5.TIMEFRAME_M1, "3m": mt5.TIMEFRAME_M3, "5m": mt5.TIMEFRAME_M5,
    "15m": mt5.TIMEFRAME_M15, "30m": mt5.TIMEFRAME_M30, "1h": mt5.TIMEFRAME_H1,
    "2h": mt5.TIMEFRAME_H2, "4h": mt5.TIMEFRAME_H4, "6h": mt5.TIMEFRAME_H6,
    "8h": mt5.TIMEFRAME_H8, "12h": mt5.TIMEFRAME_H12,
    "1d": mt5.TIMEFRAME_D1, "1w": mt5.TIMEFRAME_W1
}

# ── DST helpers (IC Markets = US DST) ──
def get_nth_sunday(year, month, n):
    d = datetime(year, month, 1, tzinfo=UTC)
    count = 0
    while True:
        if d.weekday() == 6:
            count += 1
            if count == n: return d.replace(hour=0, minute=0, second=0)
        d += timedelta(days=1)

def get_server_offset_hours(utc_ms):
    dt_utc = datetime.fromtimestamp(utc_ms / 1000, tz=UTC)
    year = dt_utc.year
    dst_start = get_nth_sunday(year, 3, 2) + timedelta(hours=7)
    dst_end = get_nth_sunday(year, 11, 1) + timedelta(hours=6)
    return 3 if dst_start <= dt_utc < dst_end else 2

def utc_ms_to_server_ms(utc_ms):
    return utc_ms + get_server_offset_hours(utc_ms) * 3600 * 1000

def server_ms_to_utc_ms(server_ms):
    approx = server_ms - 2 * 3600 * 1000
    return server_ms - get_server_offset_hours(approx) * 3600 * 1000

# ── Utils ──
def price_scale(base, quote):
    return 3 if "JPY" in (base, quote) else 5

def qround(x, scale):
    return Decimal(str(x)).quantize(Decimal("1").scaleb(-scale), rounding=ROUND_HALF_UP)

def iso_utc(ms):
    return datetime.fromtimestamp(ms / 1000, tz=UTC).isoformat(timespec="seconds")

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

def parse_pairs(path):
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            p = r.get("pair") or r.get("PAIR") or r.get("Pair")
            if p: out.append(p.strip())
    return out

def parse_timeframes(path):
    tfs = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            t = line.strip().lower()
            if t and not t.startswith("#"): tfs.append(t)
    return tfs

def mt5_now_server_ms():
    return utc_ms_to_server_ms(int(time.time() * 1000))

# ── FETCH & STORE ──
def fetch_and_store(engine, pair, tf, user_to_ms, now_server_ms_fixed):
    base, quote = pair[:3], pair[3:]
    sym = None
    for cand in [pair, pair+".a", pair+".i", pair+".pro", pair+".ecn"]:
        if mt5.symbol_info(cand):
            mt5.symbol_select(cand, True); sym = cand; break
    if not sym:
        print(f"[WARN] {pair}: not visible."); return

    meta = MetaData()
    scale = price_scale(base, quote)
    table_name = f"candles_mt5_{sanitize_name(pair)}_{sanitize_name(tf)}"

    table = Table(table_name, meta,
        Column("ts", BigInteger, primary_key=True),
        Column("ts_utc", String),
        Column("open", Numeric(20, scale)),
        Column("high", Numeric(20, scale)),
        Column("low", Numeric(20, scale)),
        Column("close", Numeric(20, scale)),
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
        start_utc = datetime.fromtimestamp((last_ts + 1) / 1000, tz=UTC)
    else:
        start_utc = datetime.now(UTC) - timedelta(days=365)

    start_ms = int(start_utc.timestamp() * 1000)
    offset = get_server_offset_hours(start_ms)
    start_srv = (start_utc + timedelta(hours=offset)).replace(tzinfo=None)

    tf_ms = TF_MS[tf]
    cap_now = (now_server_ms_fixed // tf_ms) * tf_ms - tf_ms
    if user_to_ms:
        cap_to = (utc_ms_to_server_ms(user_to_ms) // tf_ms) * tf_ms - tf_ms
        cap = min(cap_now, cap_to)
    else:
        cap = cap_now

    end_srv = datetime.fromtimestamp(cap / 1000).replace(tzinfo=None) + timedelta(seconds=1)
    if start_srv >= end_srv:
        print(f"[INFO] {pair} {tf}: no new bars."); return

    inserted = 0
    cur = start_srv

    with engine.begin() as conn:
        while cur < end_srv:
            end = cur + timedelta(milliseconds=tf_ms * BATCH_BARS)
            if end > end_srv: end = end_srv

            rates = mt5.copy_rates_range(sym, TF_MT5[tf], cur, end)
            if rates is None or len(rates) == 0:
                cur = end; continue

            # Drop la bougie en cours (non fermee): son timestamp >= debut du candle courant
            current_candle_srv = (now_server_ms_fixed // tf_ms) * tf_ms
            rows = []
            for r in rates:
                bar_srv = int(r["time"]) * 1000
                if bar_srv >= current_candle_srv: continue  # bougie en cours, skip
                if bar_srv > cap: continue

                ts_utc = server_ms_to_utc_ms(bar_srv)
                if user_to_ms and ts_utc > user_to_ms: continue
                if last_ts and ts_utc <= last_ts: continue

                # OHLC BRUT — pas de modification
                o = qround(r["open"], scale)
                h = qround(r["high"], scale)
                l = qround(r["low"], scale)
                c = qround(r["close"], scale)
                v = float(r["tick_volume"])

                rows.append({
                    "ts": ts_utc,
                    "ts_utc": iso_utc(ts_utc),
                    "open": o, "high": h, "low": l, "close": c,
                    "volume": v,
                    "exchange": "mt5",
                    "symbol": sym,
                    "base": base, "quote": quote,
                    "timeframe": tf,
                })
                last_ts = ts_utc

            if rows:
                res = conn.execute(pg_insert(table).values(rows).on_conflict_do_nothing(index_elements=["ts"]))
                inserted += (res.rowcount or 0)

            cur = end

    print(f"[DONE] {pair} {tf}: +{inserted} candles (raw OHLC).")

# ── MAIN ──
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", default=None)
    ap.add_argument("--pairs-file", default=os.getenv("PAIRS_FILE", "pairs_ftmo.txt"))
    ap.add_argument("--timeframes-file", default=os.getenv("TIMEFRAMES_FILE", "timeframes.txt"))
    ap.add_argument("--pairs", type=str, default=None)
    args = ap.parse_args()

    user_to_ms = None
    if args.to:
        s = args.to.strip()
        if re.fullmatch(r"\d{10,13}", s):
            if len(s) == 10: s += "000"
            user_to_ms = int(s)
        else:
            if s.endswith("Z"): s = s.replace("Z", "+00:00")
            user_to_ms = int(datetime.fromisoformat(s).timestamp() * 1000)

    if not mt5.initialize():
        print("[ERR] MT5 init failed"); sys.exit(1)

    engine = get_pg_engine()

    if args.pairs:
        pairs = [x for x in re.split(r"[,\s]+", args.pairs.strip()) if len(x) >= 6]
    else:
        pairs = parse_pairs(args.pairs_file)

    tfs = parse_timeframes(args.timeframes_file)

    print("[INIT] Fetch OHLC brut (pas d'indicateurs)")

    try:
        while True:
            now_srv = mt5_now_server_ms()
            offset = get_server_offset_hours(int(time.time() * 1000))
            print(f"[LOOP] server={iso_utc(now_srv)} (offset=+{offset}h)")
            for p in pairs:
                for tf in tfs:
                    fetch_and_store(engine, p, tf, user_to_ms, now_srv)
            time.sleep(1)
    except KeyboardInterrupt:
        print("[STOP]")
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    main()
