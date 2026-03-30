"""
Config 5ers — Multi-instrument (re-optimise 2026-03-30 close-only, sans open strats)
Max DD 5ers: 4% challenge
LIVE: XAUUSD seul pour le moment
REGLE: PAS de strats open (timing impossible a reproduire exactement en live)
"""
BROKER = '5ers'

INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0005,
        'portfolio': [
            'IDX_VWAP_BOUNCE',   # PF*WR 19 — score 1.41
            'IDX_CONSEC_REV',
            'PO3_SWEEP',
            'ALL_PSAR_EMA',
            'ALL_SUPERTREND',
            'ALL_PIVOT_BRK',
            'ALL_MACD_STD_SIG',
            'ALL_ELDER_BULL',
            'D8',
            'IDX_NY_MOM',
            'ALL_FIB_618',
            'ALL_MSTAR',
            'ALL_CCI_20_ZERO',
            'ALL_MACD_RSI',
            'ALL_BB_SQUEEZE',
            'TOK_FISHER',
            'TOK_BIG',
            'ALL_STOCH_OB',
            'TOK_WILLR',
        ],
        # PF*WR 19: PF 1.53 | WR 80% | DD -0.7% | Rend +20% | 13/13
    },
    # ── DESACTIVE pour test live XAUUSD seul — decommenter pour activer ──
    # 'JPN225': {
    #     'risk_pct': 0.0005,
    #     'portfolio': [
    #         'ALL_FIB_618','ALL_MTF_BRK','ALL_WILLR_14','LON_DC10_MOM',
    #         'IDX_GAP_CONT','TOK_NR4','ALL_PIVOT_BOUNCE','ALL_STOCH_PIVOT',
    #         'ALL_NR4','ALL_MACD_FAST_SIG','LON_DC10','TOK_MACD_MED',
    #         'ALL_DC10_EMA','IDX_NR4','ALL_CMO_14','ALL_EMA_821',
    #         'D8','IDX_LATE_REV','ALL_FISHER_9',
    #     ],
    #     # Sharpe 19: PF 1.57 | WR 75% | DD -0.8% | Rend +32% | 13/13
    # },
    # 'DAX40': {
    #     'risk_pct': 0.0005,
    #     'portfolio': [
    #         'ALL_FVG_BULL','ALL_STOCH_OB','ALL_CCI_20_ZERO','ALL_MACD_HIST',
    #         'ALL_ELDER_BULL','ALL_ADX_RSI50','ALL_MACD_STD_SIG','ALL_ENGULF',
    #         'IDX_ENGULF','ALL_HMA_CROSS','ALL_CMO_9','ALL_DOJI_REV',
    #         'ALL_KB_SQUEEZE','TOK_WILLR','ALL_FIB_618',
    #     ],
    #     # PF 15: PF 1.82 | WR 72% | DD -1.1% | Rend +41% | 12/13
    # },
    # 'NAS100': {
    #     'risk_pct': 0.0005,
    #     'portfolio': [
    #         'D8','ALL_HMA_CROSS','ALL_SUPERTREND','TOK_NR4',
    #         'ALL_ELDER_BULL','ALL_MSTAR','LON_STOCH','ALL_PIVOT_BOUNCE',
    #         'ALL_MACD_HIST','ALL_RSI_50','IDX_TREND_DAY','ALL_WILLR_14',
    #         'ALL_ADX_RSI50','TOK_FISHER','ALL_PSAR_EMA','ALL_EMA_821',
    #     ],
    #     # Calmar 16: PF 1.45 | WR 72% | DD -1.0% | Rend +21% | 13/13
    # },
    # 'SP500': {
    #     'risk_pct': 0.0005,
    #     'portfolio': [
    #         'ALL_DOJI_REV','TOK_FISHER','IDX_CONSEC_REV','ALL_ICHI_TK',
    #         'ALL_DC50','ALL_RSI_EXTREME','ALL_FVG_BULL','ALL_HAMMER',
    #         'ALL_MACD_FAST_SIG','IDX_RSI_REV','ALL_KB_SQUEEZE',
    #         'ALL_SUPERTREND','ALL_PSAR_EMA',
    #     ],
    #     # Calmar 13: PF 1.47 | WR 73% | DD -0.8% | Rend +19% | 13/13
    # },
    # 'UK100': {
    #     'risk_pct': 0.0005,
    #     'portfolio': [
    #         'ALL_CONSEC_REV','NY_HMA_CROSS','NY_ELDER','IDX_LATE_REV',
    #         'ALL_ELDER_BULL','TOK_NR4','IDX_CONSEC_REV','ALL_MSTAR',
    #         'IDX_TREND_DAY','ALL_HAMMER','ALL_MACD_DIV','IDX_VWAP_BOUNCE',
    #     ],
    #     # PF 12: PF 1.49 | WR 74% | DD -0.8% | Rend +18% | 12/13
    # },
}

# Backward compat: default instrument
RISK_PCT = INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = INSTRUMENTS['XAUUSD']['portfolio']
