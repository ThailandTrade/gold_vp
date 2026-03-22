"""Generate PDF report with complete analysis of all combos."""
import warnings; warnings.filterwarnings('ignore')
import sys; sys.stdout.reconfigure(encoding='utf-8')
import math
from fpdf import FPDF

class Report(FPDF):
    def header(self):
        self.set_font('Helvetica','B',10)
        self.cell(0,6,'VP Swing - Rapport Complet ICMarkets',align='C',new_x='LMARGIN',new_y='NEXT')
        self.line(10,self.get_y(),200,self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica','I',8)
        self.cell(0,10,f'Page {self.page_no()}/{{nb}}',align='C')

# Data from find_best_combo results
combos_raw = [
    (3, 'ALL_KC_BRK + LON_PREV + TOK_2BAR', 748, 1.59, 24, -25.4, 4837, '12/13'),
    (4, 'ALL_DC10 + ALL_DC10_EMA + ALL_KC_BRK + LON_PREV', 1144, 1.73, 26, -55.2, 22670, '10/13'),
    (5, 'ALL_ADX_FAST + ALL_DC10_EMA + ALL_KC_BRK + LON_PREV + TOK_2BAR', 1294, 1.60, 26, -46.6, 29608, '11/13'),
    (6, 'ALL_ADX_FAST + ALL_BB_TIGHT + ALL_DC10 + ALL_DC10_EMA + ALL_KC_BRK + LON_PREV', 1703, 1.62, 28, -65.1, 57996, '10/13'),
    (7, 'ALL_ADX_FAST + ALL_BB_TIGHT + ALL_CCI_14_ZERO + ALL_DC10 + ALL_DC10_EMA + ALL_KC_BRK + LON_PREV', 1948, 1.67, 28, -68.8, 110625, '9/13'),
    (8, '+ALL_CCI_20_ZERO', 2212, 1.62, 29, -75.2, 125166, '10/13'),
    (9, '+ALL_MACD_MED_SIG', 2471, 1.63, 29, -77.9, 367775, '11/13'),
    (10, '+ALL_MACD_RSI', 2714, 1.65, 28, -76.1, 642097, '11/13'),
    (11, '+ALL_WILLR_7', 3024, 1.73, 32, -82.3, 1181272, '10/13'),
    (12, '+LON_GAP', 3291, 1.70, 31, -86.3, 1274674, '10/13'),
    (13, '+ALL_HMA_CROSS', 3555, 1.59, 30, -90.1, 1028393, '10/13'),
    (14, '+ALL_EMA_921', 3829, 1.57, 29, -92.1, 1333922, '11/13'),
]

# Individual strats data
strats_data = [
    ('ALL_ADX_FAST','TRAIL','SL=0.50 ACT=0.50 TR=0.50',297,35,1.91,'24h','ADX(7)+DI cross+EMA21'),
    ('ALL_BB_TIGHT','TPSL','SL=0.50 TP=1.50',310,25,1.43,'24h','BB(10,1.5) breakout'),
    ('ALL_CCI_14_ZERO','TRAIL','SL=0.50 ACT=1.00 TR=0.30',299,28,1.68,'24h','CCI(14) zero cross'),
    ('ALL_CCI_20_ZERO','TRAIL','SL=0.50 ACT=0.30 TR=0.50',296,31,1.50,'24h','CCI(20) zero cross'),
    ('ALL_DC10','TRAIL','SL=0.50 ACT=0.75 TR=0.50',309,33,1.63,'24h','Donchian 10 breakout'),
    ('ALL_DC10_EMA','TPSL','SL=0.50 TP=3.00',309,20,1.61,'24h','Donchian 10 + EMA21 filter'),
    ('ALL_DC50','TRAIL','SL=1.50 ACT=0.30 TR=0.75',297,45,1.54,'24h','Donchian 50 breakout'),
    ('ALL_EMA_513','TPSL','SL=0.50 TP=1.00',294,25,1.54,'24h','EMA 5/13 crossover'),
    ('ALL_EMA_821','TPSL','SL=0.50 TP=3.00',289,13,1.38,'24h','EMA 8/21 crossover'),
    ('ALL_EMA_921','TPSL','SL=0.50 TP=3.00',289,14,1.54,'24h','EMA 9/21 crossover'),
    ('ALL_EMA_TREND_PB','TRAIL','SL=1.00 ACT=0.75 TR=0.75',284,40,1.25,'24h','EMA 50/200 trend pullback'),
    ('ALL_HMA_CROSS','TPSL','SL=0.75 TP=3.00',309,19,1.66,'24h','HMA 9/21 crossover'),
    ('ALL_HMA_DIR','TPSL','SL=0.50 TP=1.50',309,25,1.47,'24h','HMA 9 direction change'),
    ('ALL_ICHI_TK','TPSL','SL=0.50 TP=3.00',267,16,1.51,'24h','Ichimoku TK cross above cloud'),
    ('ALL_KC_BRK','TPSL','SL=0.50 TP=3.00',301,20,1.50,'24h','Keltner Channel breakout'),
    ('ALL_MACD_ADX','TRAIL','SL=0.50 ACT=0.30 TR=0.50',292,34,1.72,'24h','MACD std + ADX>25'),
    ('ALL_MACD_FAST_SIG','TRAIL','SL=0.75 ACT=0.50 TR=0.75',310,35,1.43,'24h','MACD(5,13,1) signal cross'),
    ('ALL_MACD_MED_SIG','TRAIL','SL=0.50 ACT=1.00 TR=0.30',301,27,1.84,'24h','MACD(8,17,9) signal cross'),
    ('ALL_MACD_RSI','TRAIL','SL=0.50 ACT=0.50 TR=0.50',288,37,2.42,'24h','MACD(8,17,9)+RSI>50'),
    ('ALL_MACD_STD_SIG','TRAIL','SL=0.50 ACT=0.75 TR=0.30',298,42,1.38,'24h','MACD(12,26,9) signal cross'),
    ('ALL_MOM_10','TRAIL','SL=1.50 ACT=0.75 TR=0.50',301,57,1.48,'24h','Momentum ROC(10) zero cross'),
    ('ALL_MOM_14','TRAIL','SL=2.00 ACT=0.50 TR=1.00',295,49,1.53,'24h','Momentum ROC(14) zero cross'),
    ('ALL_RSI_50','TRAIL','SL=0.50 ACT=0.30 TR=0.30',294,35,1.48,'24h','RSI(14) centerline cross'),
    ('ALL_RSI_DIV','TRAIL','SL=1.50 ACT=0.30 TR=0.75',296,46,1.62,'24h','RSI divergence'),
    ('ALL_WILLR_14','TRAIL','SL=2.00 ACT=0.50 TR=0.75',305,48,1.67,'24h','Williams %R(14)'),
    ('ALL_WILLR_7','TPSL','SL=0.50 TP=3.00',309,16,1.76,'24h','Williams %R(7)'),
    ('D8','TRAIL','SL=1.00 ACT=1.00 TR=0.75',48,56,1.69,'London','Inside day breakout'),
    ('LON_BIGGAP','TRAIL','SL=1.00 ACT=0.30 TR=0.75',223,39,1.59,'London','GAP Tok>Lon >1ATR'),
    ('LON_DC10','TPSL','SL=1.00 TP=1.00',256,41,1.22,'London','Donchian 10 London'),
    ('LON_DC10_MOM','TPSL','SL=1.00 TP=1.00',256,41,1.22,'London','DC10+Momentum London'),
    ('LON_GAP','TRAIL','SL=1.00 ACT=0.30 TR=0.75',243,39,1.63,'London','GAP Tok>Lon >0.5ATR'),
    ('LON_KZ','TRAIL','SL=2.00 ACT=0.30 TR=0.30',220,74,1.82,'London','KZ 8h-10h fade'),
    ('LON_PREV','TRAIL','SL=0.50 ACT=0.75 TR=0.50',231,35,1.58,'London','Prev day continuation'),
    ('LON_TOKEND','TPSL','SL=0.50 TP=2.00',117,21,1.98,'London','3 last Tokyo >1ATR'),
    ('NY_DAYMOM','TPSL','SL=0.50 TP=2.00',231,21,1.43,'NY','Day move >1.5ATR cont.'),
    ('NY_GAP','TPSL','SL=0.75 TP=3.00',179,17,1.38,'NY','GAP Lon>NY >0.5ATR'),
    ('NY_HMA_CROSS','TRAIL','SL=1.00 ACT=0.75 TR=0.50',257,39,1.40,'NY','HMA cross NY'),
    ('NY_LONEND','TPSL','SL=0.50 TP=3.00',152,16,1.78,'NY','3 last London >1ATR'),
    ('NY_LONMOM','TPSL','SL=0.50 TP=3.00',202,17,1.79,'NY','3 last London >0.5ATR'),
    ('TOK_2BAR','TPSL','SL=0.50 TP=3.00',240,19,2.01,'Tokyo','2-bar reversal'),
    ('TOK_BIG','TRAIL','SL=1.00 ACT=0.30 TR=0.75',254,38,1.55,'Tokyo','Big candle >1ATR'),
    ('TOK_FADE','TRAIL','SL=0.50 ACT=0.30 TR=0.50',231,29,1.59,'Tokyo','Fade prev day >1ATR'),
    ('TOK_MACD_MED','TRAIL','SL=1.00 ACT=0.50 TR=0.75',256,40,1.64,'Tokyo','MACD(8,17,9) Tokyo'),
    ('TOK_PREVEXT','TRAIL','SL=1.50 ACT=0.75 TR=1.00',43,51,1.53,'Tokyo','Prev day close extreme'),
    ('TOK_WILLR','TRAIL','SL=2.00 ACT=0.50 TR=0.75',256,49,1.76,'Tokyo','Williams %R Tokyo'),
]

pdf = Report('L','mm','A4')  # Landscape
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=20)

# ?? PAGE 1: RESUME ??
pdf.add_page()
pdf.set_font('Helvetica','B',16)
pdf.cell(0,10,'ANALYSE COMPLETE - ICMarkets',align='C',new_x='LMARGIN',new_y='NEXT')
pdf.set_font('Helvetica','',10)
pdf.cell(0,6,'45 strategies (price action + indicators) | Exits optimises par strat | Donnees mars 2025 - mars 2026',align='C',new_x='LMARGIN',new_y='NEXT')
pdf.cell(0,6,'Config: trailing sur CLOSE, check entry candle, zero look-ahead',align='C',new_x='LMARGIN',new_y='NEXT')
pdf.ln(5)

# Combo table
pdf.set_font('Helvetica','B',11)
pdf.cell(0,8,'MEILLEURS COMBOS PAR TAILLE - Capital $100,000 | Risk 0.1%',new_x='LMARGIN',new_y='NEXT')
pdf.ln(2)

# Headers
pdf.set_font('Helvetica','B',8)
cols = [('Sz',10),('Trades',15),('PF',12),('WR',10),('DD 1%',15),('DD 0.1%',15),('Rend 1%',22),('Rend 0.1%',18),('Cap final',25),('M+',12),('R/DD',12),('Strats',111)]
for name, w in cols:
    pdf.cell(w, 6, name, border=1, align='C')
pdf.ln()

# Data
pdf.set_font('Helvetica','',7)
for sz, combo, n, pf, wr, dd, rend, mp in combos_raw:
    dd_01 = dd / 10
    rend_01 = (math.pow(1 + rend/100, 0.1) - 1) * 100
    cap = 100000 * (1 + rend_01/100)
    ratio = abs(rend_01 / dd_01) if dd_01 != 0 else 0

    pdf.cell(10, 5, str(sz), border=1, align='C')
    pdf.cell(15, 5, str(n), border=1, align='C')
    pdf.cell(12, 5, f'{pf:.2f}', border=1, align='C')
    pdf.cell(10, 5, f'{wr}%', border=1, align='C')
    pdf.cell(15, 5, f'{dd:+.1f}%', border=1, align='C')
    pdf.cell(15, 5, f'{dd_01:+.1f}%', border=1, align='C')
    pdf.cell(22, 5, f'+{rend:,}%', border=1, align='C')
    pdf.cell(18, 5, f'+{rend_01:.1f}%', border=1, align='C')
    pdf.cell(25, 5, f'${cap:,.0f}', border=1, align='C')
    pdf.cell(12, 5, mp, border=1, align='C')
    pdf.cell(12, 5, f'{ratio:.1f}x', border=1, align='C')
    pdf.cell(111, 5, combo[:65], border=1)
    pdf.ln()

pdf.ln(5)
pdf.set_font('Helvetica','I',8)
pdf.multi_cell(0, 4, 'Notes:\n- DD 0.1% = DD 1% / 10 (approximation lineaire, valide pour petits risques)\n- Rend 0.1% = (1+Rend_1%)^0.1 - 1 (compound scaling)\n- R/DD = ratio rendement/drawdown a 0.1% risk\n- Toutes les strats sont backtestees sans look-ahead, avec check de la bougie d\'entree pour le SL')

# ?? PAGE 2: STRATS INDIVIDUELLES ??
pdf.add_page()
pdf.set_font('Helvetica','B',11)
pdf.cell(0,8,'45 STRATEGIES INDIVIDUELLES - PF optimise par strat',new_x='LMARGIN',new_y='NEXT')
pdf.ln(2)

# Headers
pdf.set_font('Helvetica','B',7)
cols2 = [('Strat',35),('Exit',10),('Config',40),('n',10),('WR',10),('PF',10),('Sess.',14),('Description',148)]
for name, w in cols2:
    pdf.cell(w, 6, name, border=1, align='C')
pdf.ln()

# Data sorted by PF
pdf.set_font('Helvetica','',6.5)
for sn, etype, cfg, n, wr, pf, sess, desc in sorted(strats_data, key=lambda x: -x[5]):
    pdf.cell(35, 4.5, sn, border=1)
    pdf.cell(10, 4.5, etype, border=1, align='C')
    pdf.cell(40, 4.5, cfg, border=1)
    pdf.cell(10, 4.5, str(n), border=1, align='C')
    pdf.cell(10, 4.5, f'{wr}%', border=1, align='C')
    pdf.cell(10, 4.5, f'{pf:.2f}', border=1, align='C')
    pdf.cell(14, 4.5, sess, border=1, align='C')
    pdf.cell(148, 4.5, desc, border=1)
    pdf.ln()

# ?? PAGE 3: RECOMMANDATIONS ??
pdf.add_page('P')
pdf.set_font('Helvetica','B',14)
pdf.cell(0,10,'RECOMMANDATIONS',align='C',new_x='LMARGIN',new_y='NEXT')
pdf.ln(5)

pdf.set_font('Helvetica','B',11)
pdf.cell(0,7,'Combo recommande: 5 strats',new_x='LMARGIN',new_y='NEXT')
pdf.set_font('Helvetica','',9)
pdf.multi_cell(0,5,'ALL_ADX_FAST + ALL_DC10_EMA + ALL_KC_BRK + LON_PREV + TOK_2BAR\n\nA $100k, 0.1% risk:\n  - Rendement: +76.7% (~$177k)\n  - DD max: -4.7%\n  - PF: 1.60\n  - 1294 trades (4.1/jour)\n  - 11/13 mois positifs\n  - Ratio Rend/DD: 16.5x\n\nMix de 3 sessions (Tokyo + London + 24h indicators)\nLong + Short equilibre')

pdf.ln(5)
pdf.set_font('Helvetica','B',11)
pdf.cell(0,7,'Combo agressif: 10 strats',new_x='LMARGIN',new_y='NEXT')
pdf.set_font('Helvetica','',9)
pdf.multi_cell(0,5,'ALL_ADX_FAST + ALL_BB_TIGHT + ALL_CCI_14_ZERO + ALL_CCI_20_ZERO\n+ ALL_DC10 + ALL_DC10_EMA + ALL_KC_BRK + ALL_MACD_MED_SIG\n+ ALL_MACD_RSI + LON_PREV\n\nA $100k, 0.1% risk:\n  - Rendement: +140.3% (~$240k)\n  - DD max: -7.6%\n  - PF: 1.65\n  - 2714 trades (8.6/jour)\n  - 11/13 mois positifs\n  - Ratio Rend/DD: 18.4x')

pdf.ln(5)
pdf.set_font('Helvetica','B',11)
pdf.cell(0,7,'Risques et limitations',new_x='LMARGIN',new_y='NEXT')
pdf.set_font('Helvetica','',9)
pdf.multi_cell(0,5,'- Backtest sur 13 mois seulement (mars 2025 - mars 2026)\n- Exits optimises sur les memes donnees (risque d\'overfitting)\n- Les SL serres (0.5 ATR) augmentent la volatilite\n- Le spread reel peut differer du 2x monthly average\n- Les gaps weekend ne sont pas modelises (slippage potentiel)\n- Performance passee ne garantit pas la performance future\n\nRecommandation: commencer avec 0.05% de risque, augmenter apres 2-3 mois de live.')

out = 'rapport_icmarkets.pdf'
pdf.output(out)
print(f'PDF genere: {out}')
