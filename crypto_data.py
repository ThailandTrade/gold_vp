"""
Loader candles crypto (Hyperliquid/Binance Futures via hl_fetch).
Separe de phase3_analyze pour garantir zero impact sur le pipeline MT5.
"""
import re
import numpy as np
import pandas as pd

TF_DEFAULT = '15m'


def _table_name(symbol, tf=TF_DEFAULT):
    sym_san = re.sub(r'[^a-z0-9]+', '_', symbol.lower()).strip('_')
    return f'candles_hl_{sym_san}_{tf}'


def load_candles_hl(conn, symbol, tf=TF_DEFAULT):
    """
    Load candles crypto depuis la table candles_hl_<symbol>_<tf>.
    Retourne un DataFrame indexe par bar avec ts_dt UTC, ohlc, hour.
    """
    table = _table_name(symbol, tf)
    cur = conn.cursor()
    cur.execute(f"SELECT ts, open, high, low, close FROM {table} ORDER BY ts")
    rows = cur.fetchall()
    cur.close()
    df = pd.DataFrame(rows, columns=['ts', 'open', 'high', 'low', 'close'])
    df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms', utc=True)
    for c in ['open', 'high', 'low', 'close']:
        df[c] = df[c].astype(float)
    df['date'] = df['ts_dt'].dt.date
    df['hour'] = df['ts_dt'].dt.hour + df['ts_dt'].dt.minute / 60.0
    return df


def compute_atr_hl(conn, symbol, tf=TF_DEFAULT, period=14):
    """ATR calcule sur les candles HL 15m. Retourne (daily_atr dict, global_atr float)."""
    table = _table_name(symbol, tf)
    cur = conn.cursor()
    cur.execute(f"SELECT ts, open, high, low, close FROM {table} ORDER BY ts")
    rows = cur.fetchall()
    cur.close()
    df = pd.DataFrame(rows, columns=['ts', 'open', 'high', 'low', 'close'])
    df['ts_dt'] = pd.to_datetime(df['ts'], unit='ms', utc=True)
    for c in ['high','low','close']:
        df[c] = df[c].astype(float)
    df['prev_close'] = df['close'].shift(1)
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(abs(df['high'] - df['prev_close']), abs(df['low'] - df['prev_close']))
    )
    df['atr'] = df['tr'].ewm(span=period, adjust=False).mean()
    df['date'] = df['ts_dt'].dt.date
    daily_atr = df.groupby('date')['atr'].last().to_dict()
    global_atr = df['atr'].mean()
    return daily_atr, global_atr


def get_trading_days_hl(conn, symbol, tf=TF_DEFAULT):
    """Jours uniques disponibles dans les candles HL."""
    table = _table_name(symbol, tf)
    cur = conn.cursor()
    cur.execute(f"SELECT DISTINCT DATE(to_timestamp(ts/1000)) FROM {table} ORDER BY 1")
    days = [r[0].date() if hasattr(r[0], 'date') else r[0] for r in cur.fetchall()]
    cur.close()
    return days
