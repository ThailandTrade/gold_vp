"""
Compare bougies MT5 vs DB — trouver les differences
"""
import sys, os, json, argparse; sys.stdout.reconfigure(encoding='utf-8')
import warnings; warnings.filterwarnings('ignore')
import MetaTrader5 as mt5
import pandas as pd
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn

parser = argparse.ArgumentParser()
parser.add_argument('--broker', default='icm', choices=['icm','ftmo','5ers'])
args = parser.parse_args()
with open(os.path.join(os.path.dirname(__file__), 'broker_offsets.json')) as f:
    _offsets = json.load(f)
BROKER_OFFSET_H = _offsets[args.broker]

mt5.initialize()
rates = mt5.copy_rates_from_pos('XAUUSD', mt5.TIMEFRAME_M5, 0, 100)
mt5.shutdown()
mt5_df = pd.DataFrame(rates)
mt5_df['time_utc'] = pd.to_datetime(mt5_df['time'], unit='s') - pd.Timedelta(hours=BROKER_OFFSET_H)
for c in ['open','high','low','close']: mt5_df[c] = mt5_df[c].astype(float)

conn = get_conn(); conn.autocommit = True
cur = conn.cursor()
cur.execute('SELECT ts, open, high, low, close FROM candles_mt5_xauusd_5m ORDER BY ts DESC LIMIT 100')
rows = cur.fetchall(); cur.close(); conn.close()
db_df = pd.DataFrame(rows, columns=['ts','open','high','low','close']).sort_values('ts').reset_index(drop=True)
db_df['time_utc'] = pd.to_datetime(db_df['ts'], unit='ms', utc=True).dt.tz_localize(None)
for c in ['open','high','low','close']: db_df[c] = db_df[c].astype(float)

n_compared = 0
n_exact = 0
n_minor = 0  # < 0.02
n_major = 0  # >= 0.02
majors = []

for _, mt5_r in mt5_df.iterrows():
    t = mt5_r['time_utc']
    db_match = db_df[(db_df['time_utc'] - t).abs() < pd.Timedelta(seconds=10)]
    if len(db_match) == 0:
        continue
    n_compared += 1
    db_r = db_match.iloc[0]
    do = abs(mt5_r['open'] - db_r['open'])
    dh = abs(mt5_r['high'] - db_r['high'])
    dl = abs(mt5_r['low'] - db_r['low'])
    dc = abs(mt5_r['close'] - db_r['close'])
    worst = max(do, dh, dl, dc)

    if worst < 0.005:
        n_exact += 1
    elif worst < 0.50:
        n_minor += 1
    else:
        n_major += 1
        majors.append({
            'time': str(t),
            'do': do, 'dh': dh, 'dl': dl, 'dc': dc,
            'mt5_o': mt5_r['open'], 'mt5_h': mt5_r['high'], 'mt5_l': mt5_r['low'], 'mt5_c': mt5_r['close'],
            'db_o': db_r['open'], 'db_h': db_r['high'], 'db_l': db_r['low'], 'db_c': db_r['close'],
        })

print(f"Bougies comparees: {n_compared}")
print(f"  Identiques (<$0.005):   {n_exact} ({n_exact/n_compared*100:.0f}%)")
print(f"  Mineurs ($0.005-0.50):  {n_minor} ({n_minor/n_compared*100:.0f}%)")
print(f"  MAJEURS (>=$0.50):      {n_major} ({n_major/n_compared*100:.0f}%)")

if majors:
    print(f"\nDETAIL DES DIFFERENCES MAJEURES:")
    for m in majors:
        print(f"\n  {m['time']}")
        print(f"    MT5: O={m['mt5_o']:.2f} H={m['mt5_h']:.2f} L={m['mt5_l']:.2f} C={m['mt5_c']:.2f}")
        print(f"    DB:  O={m['db_o']:.2f} H={m['db_h']:.2f} L={m['db_l']:.2f} C={m['db_c']:.2f}")
        print(f"    Diff: O={m['do']:.2f} H={m['dh']:.2f} L={m['dl']:.2f} C={m['dc']:.2f}")

# Verifier si c'est un probleme bid/ask
# MT5 copy_rates = prix BID. Le script de fetch peut stocker ask ou mid
print("\n" + "="*60)
print("NOTE: MT5 copy_rates_from_pos retourne les prix BID.")
print("Si le script de fetch utilise une autre source, les prix")
print("peuvent diverger du spread (typ. $0.05-0.15)")
print("="*60)

# Verifier le script de fetch
import os
fetch_files = [f for f in os.listdir('.') if 'fetch' in f.lower() or 'bulk' in f.lower() or 'harvest' in f.lower()]
print(f"\nScripts de fetch trouves: {fetch_files}")
