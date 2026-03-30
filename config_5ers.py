"""
Config 5ers — Multi-instrument (re-optimise 2026-03-29 avec 110 strats)
Max DD 5ers: 4% challenge
TEST LIVE: XAUUSD seul pour le moment
REGLE: PAS de strats open (timing impossible a reproduire exactement en live)
"""
BROKER = '5ers'

INSTRUMENTS = {
    'XAUUSD': {
        'risk_pct': 0.0005,
        'portfolio': [
            'IDX_VWAP_BOUNCE',  # ex-Calmar 19, open strats retirees -> 14 close strats
            'ALL_STOCH_OB',
            'ALL_FIB_618',
            'ALL_MACD_STD_SIG',
            'ALL_PSAR_EMA',
            'TOK_FISHER',
            'ALL_BB_TIGHT',
            'ALL_MSTAR',
            'ALL_SUPERTREND',
            'PO3_SWEEP',
            'IDX_CONSEC_REV',
            'D8',
            'TOK_WILLR',
            'IDX_NR4',
        ],
        # Sans open: PF 1.60 | WR 74% | 3235 trades | 14 strats
    },
    # ── DESACTIVE pour test live XAUUSD seul — decommenter pour activer ──
    # 'JPN225': {
    #     'risk_pct': 0.0005,
    #     'portfolio': [
    #         'ALL_FIB_618','ALL_NR4','ALL_STOCH_PIVOT','ALL_MTF_BRK',
    #         'LON_DC10','ALL_FISHER_9','IDX_GAP_CONT','ALL_MACD_RSI','IDX_LATE_REV',
    #         'TOK_NR4','ALL_WILLR_14','ALL_PIVOT_BOUNCE','LON_DC10_MOM','ALL_CMO_14',
    #         'D8','ALL_STOCH_RSI','ALL_MACD_MED_SIG',
    #     ],
    #     # ex-Calmar21 sans open (LON_GAP, LON_TOKEND, TOK_PREVEXT, NY_LONEND retirees)
    # },
    # 'DAX40': {
    #     'risk_pct': 0.0005,
    #     'portfolio': [
    #         'ALL_FVG_BULL','ALL_STOCH_OB','ALL_CCI_20_ZERO','ALL_MACD_HIST',
    #         'ALL_ELDER_BULL','ALL_ADX_RSI50','ALL_MACD_STD_SIG',
    #         'ALL_FISHER_9','ALL_INSIDE_BRK','TOK_WILLR','ALL_BB_TIGHT',
    #         'TOK_BIG','ALL_RSI_DIV','ALL_DC10','ALL_DC10_EMA',
    #     ],
    #     # ex-PF17 sans open (TOK_FADE, TOK_PREVEXT retirees)
    # },
    # 'NAS100': {
    #     'risk_pct': 0.0005,
    #     'portfolio': [
    #         'D8','ALL_HMA_CROSS','ALL_SUPERTREND','TOK_NR4',
    #         'ALL_RSI_50','ALL_PIVOT_BOUNCE','ALL_MSTAR','IDX_PREV_HL',
    #         'ALL_MACD_HIST','ALL_FVG_BULL','IDX_NY_MOM','ALL_NR4',
    #         'ALL_ELDER_BULL','ALL_DC50',
    #         'IDX_TREND_DAY','ALL_STOCH_PIVOT',
    #     ],
    #     # ex-Calmar19 sans open (TOK_FADE, TOK_PREVEXT, LON_BIGGAP retirees)
    # },
    # 'SP500': {
    #     'risk_pct': 0.0005,
    #     'portfolio': [
    #         'ALL_DOJI_REV','TOK_FISHER','IDX_CONSEC_REV','ALL_ICHI_TK',
    #         'ALL_DC50','ALL_RSI_EXTREME','ALL_FVG_BULL',
    #         'ALL_3SOLDIERS','ALL_PSAR_EMA','ALL_SUPERTREND','ALL_MACD_HIST',
    #         'IDX_RSI_REV','ALL_ELDER_BULL','ALL_STOCH_CROSS','ALL_MACD_FAST_SIG',
    #     ],
    #     # ex-Calmar16 sans open (LON_PREV retiree)
    # },
    # 'UK100': {
    #     'risk_pct': 0.0005,
    #     'portfolio': [
    #         'ALL_CONSEC_REV','NY_HMA_CROSS','NY_ELDER','ALL_ELDER_BULL',
    #         'IDX_TREND_DAY','IDX_LATE_REV','ALL_MACD_DIV',
    #         'IDX_CONSEC_REV','ALL_HAMMER','TOK_NR4','ALL_MSTAR',
    #     ],
    #     # ex-Calmar14 sans open (LON_BIGGAP, LON_GAP, LON_PREV retirees)
    # },
}

# Backward compat: default instrument
RISK_PCT = INSTRUMENTS['XAUUSD']['risk_pct']
PORTFOLIO = INSTRUMENTS['XAUUSD']['portfolio']
