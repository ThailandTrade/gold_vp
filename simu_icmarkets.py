"""
Backtest ICMarkets — 14 strats
Usage: python simu_icmarkets.py [capital] [risk%]
  Ex: python simu_icmarkets.py 100000 0.1
"""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv; load_dotenv()
from phase1_poc_calculator import get_conn, compute_atr, get_trading_days
from phase3_analyze import load_candles_5m
from config_icmarkets import PORTFOLIO, BROKER
from backtest_engine import run_backtest

capital = float(sys.argv[1]) if len(sys.argv) > 1 else 1000.0
risk = float(sys.argv[2]) / 100 if len(sys.argv) > 2 else 0.01

conn = get_conn()
candles = load_candles_5m(conn)
daily_atr, global_atr = compute_atr(conn)
trading_days = get_trading_days(conn)
cur = conn.cursor()
cur.execute("""SELECT DATE_TRUNC('month', time), AVG(ask-bid) FROM market_ticks_xauusd WHERE ask>bid AND ask-bid<10 GROUP BY 1""")
monthly_spread = {r[0].strftime("%Y-%m"): float(r[1]) for r in cur.fetchall()}
cur.close(); conn.close()

print(f"Collecte [{BROKER}]...", flush=True)
run_backtest(candles, daily_atr, global_atr, trading_days, monthly_spread, PORTFOLIO, BROKER, capital, risk)
