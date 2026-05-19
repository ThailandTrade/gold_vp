"""
Fetch historical OHLCV depuis Dukascopy pour la liste des syms exness_standard.
Stocke dans DB tables `candles_<sym>_4h` (broker-agnostique, sans suffix 'm').

Usage:
    python dukascopy_fetch.py                       # fetch tous les syms, 4h, depuis 5y back
    python dukascopy_fetch.py --years 10            # 10y back
    python dukascopy_fetch.py --symbol AUDUSD       # un seul sym
    python dukascopy_fetch.py --since 2020-01-01    # depuis date precise

Le script:
1. Lit la liste depuis pairs_exness_standard.txt (strip 'm' suffix)
2. Map vers les instruments Dukascopy via DUKA_MAP
3. Fetch bars 4h bid (OFFER_SIDE_BID)
4. Upsert dans candles_<sym>_4h (postgres)
"""
import os
import sys
import argparse
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
import dukascopy_python
from dukascopy_python import instruments as I

# Mapping sym broker-neutre -> Dukascopy instrument constant
# Sym name = sym de pairs_exness_standard.txt SANS suffix 'm'
DUKA_MAP = {
    # FX majors
    'AUDUSD': I.INSTRUMENT_FX_MAJORS_AUD_USD,
    'EURUSD': I.INSTRUMENT_FX_MAJORS_EUR_USD,
    'GBPUSD': I.INSTRUMENT_FX_MAJORS_GBP_USD,
    'NZDUSD': I.INSTRUMENT_FX_MAJORS_NZD_USD,
    'USDCAD': I.INSTRUMENT_FX_MAJORS_USD_CAD,
    'USDCHF': I.INSTRUMENT_FX_MAJORS_USD_CHF,
    'USDJPY': I.INSTRUMENT_FX_MAJORS_USD_JPY,
    # FX crosses
    'USDCNH': I.INSTRUMENT_FX_CROSSES_USD_CNH,
    'EURJPY': I.INSTRUMENT_FX_CROSSES_EUR_JPY,
    'EURGBP': I.INSTRUMENT_FX_CROSSES_EUR_GBP,
    'GBPJPY': I.INSTRUMENT_FX_CROSSES_GBP_JPY,
    # Metals
    'XAUUSD': I.INSTRUMENT_FX_METALS_XAU_USD,
    # Energy
    'USOIL':  I.INSTRUMENT_CMD_ENERGY_E_LIGHT,   # WTI Light Crude
    # Indices
    'AUS200': I.INSTRUMENT_IDX_ASIA_E_XJO_ASX,         # ASX 200
    'DE30':   I.INSTRUMENT_IDX_EUROPE_E_DAAX,          # DAX 30/40
    'HK50':   I.INSTRUMENT_IDX_ASIA_E_H_KONG,          # Hang Seng
    'JP225':  I.INSTRUMENT_IDX_ASIA_E_N225JAP,         # Nikkei 225
    'UK100':  I.INSTRUMENT_IDX_EUROPE_E_FUTSEE_100,    # FTSE 100
    'US30':   I.INSTRUMENT_IDX_AMERICA_E_D_J_IND,      # Dow Jones
    'US500':  I.INSTRUMENT_IDX_AMERICA_E_SANDP_500,    # S&P 500
    'USTEC':  I.INSTRUMENT_IDX_AMERICA_E_NQ_100,       # Nasdaq 100
    # Crypto
    'BTCUSD': I.INSTRUMENT_VCCY_BTC_USD,
    'ETHUSD': I.INSTRUMENT_VCCY_ETH_USD,
}


def get_conn():
    return psycopg2.connect(
        host=os.getenv('PG_HOST'), port=os.getenv('PG_PORT'),
        dbname=os.getenv('PG_DB'), user=os.getenv('PG_USER'),
        password=os.getenv('PG_PASSWORD'), sslmode=os.getenv('PG_SSLMODE', 'disable'),
    )


def ensure_table(conn, sym, tf):
    """Cree la table candles_<sym>_<tf> si elle n'existe pas."""
    table = f"candles_{sym.lower()}_{tf}"
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                ts TIMESTAMPTZ PRIMARY KEY,
                open  DOUBLE PRECISION NOT NULL,
                high  DOUBLE PRECISION NOT NULL,
                low   DOUBLE PRECISION NOT NULL,
                close DOUBLE PRECISION NOT NULL,
                volume DOUBLE PRECISION
            )
        """)
        conn.commit()
    return table


def fetch_sym(sym, instrument, start, end, tf='4h'):
    """Fetch bid OHLCV pour sym entre start et end. Retourne dataframe pandas."""
    interval = dukascopy_python.INTERVAL_HOUR_4 if tf == '4h' else dukascopy_python.INTERVAL_HOUR_1
    df = dukascopy_python.fetch(
        instrument,
        interval,
        dukascopy_python.OFFER_SIDE_BID,
        start,
        end,
    )
    return df


def upsert_bars(conn, table, df):
    """Upsert dataframe dans la table."""
    if df is None or len(df) == 0:
        return 0
    rows = []
    for ts, row in df.iterrows():
        # ts est tz-aware UTC
        if ts.tzinfo is None:
            ts = ts.tz_localize('UTC')
        rows.append((ts, float(row['open']), float(row['high']),
                     float(row['low']), float(row['close']),
                     float(row.get('volume', 0)) if row.get('volume') is not None else 0.0))
    with conn.cursor() as cur:
        cur.executemany(
            f"""INSERT INTO {table} (ts, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (ts) DO UPDATE SET
                    open=EXCLUDED.open, high=EXCLUDED.high,
                    low=EXCLUDED.low, close=EXCLUDED.close,
                    volume=EXCLUDED.volume""",
            rows,
        )
        conn.commit()
    return len(rows)


def load_pairs(file='pairs_exness_standard.txt'):
    """Lit la liste des syms exness_standard, strip 'm' suffix."""
    syms = []
    with open(file, 'r') as f:
        next(f)  # header
        for line in f:
            line = line.strip()
            if not line or ',' not in line:
                continue
            sym_m = line.split(',')[1]
            sym = sym_m[:-1] if sym_m.endswith('m') else sym_m
            syms.append((sym, sym_m))
    return syms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tf', default='4h', choices=['4h', '1h'])
    ap.add_argument('--years', type=float, default=5.0, help='Annees d historique a fetch (defaut 5)')
    ap.add_argument('--since', default=None, help='Date debut YYYY-MM-DD (override --years)')
    ap.add_argument('--until', default=None, help='Date fin YYYY-MM-DD (defaut: aujourd hui)')
    ap.add_argument('--symbol', default=None, help='Un seul sym (e.g. AUDUSD)')
    ap.add_argument('--pairs-file', default='pairs_exness_standard.txt')
    args = ap.parse_args()

    if args.since:
        start = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
    else:
        start = datetime.now(timezone.utc) - timedelta(days=int(args.years * 365))
    end = (datetime.fromisoformat(args.until).replace(tzinfo=timezone.utc)
           if args.until else datetime.now(timezone.utc))

    print(f"Range: {start.date()} -> {end.date()} | TF: {args.tf}")

    pairs = load_pairs(args.pairs_file)
    if args.symbol:
        pairs = [(s, sm) for s, sm in pairs if s.upper() == args.symbol.upper()]
        if not pairs:
            print(f"ERROR: {args.symbol} introuvable dans {args.pairs_file}")
            sys.exit(1)

    conn = get_conn()
    total_rows = 0
    for sym, sym_m in pairs:
        if sym not in DUKA_MAP:
            print(f"  {sym} ({sym_m}): SKIP (pas dans DUKA_MAP)")
            continue
        instrument = DUKA_MAP[sym]
        table = ensure_table(conn, sym, args.tf)
        print(f"  {sym:<8s} -> {instrument} ...", end='', flush=True)
        try:
            df = fetch_sym(sym, instrument, start, end, tf=args.tf)
            n = upsert_bars(conn, table, df)
            print(f" {n} bars -> {table}")
            total_rows += n
        except Exception as e:
            print(f" ERROR: {e}")
    conn.close()
    print(f"\nTotal: {total_rows} bars")


if __name__ == '__main__':
    main()
