"""
Dashboard VP Swing — streamlit run dashboard.py
"""
import streamlit as st
import json, os, time
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import itertools
import plotly.graph_objects as go
from plotly.subplots import make_subplots

LOG_FILE = "paper_trades.json"
CAPITAL_INITIAL = 1000.0

STRATS = {
    'AC':'Absorption Tokyo','D':'GAP Tokyo→London','E':'KZ London fade',
    'F':'2BAR Tokyo rev','G':'NY 1st candle','H':'TOKEND 3b',
    'I':'FADE NY 1h','O':'BigCandle Tokyo','P':'ORB NY 30min','V':'CandleRatio Tokyo'
}
SESS_STRATS = {'Tokyo':['AC','F','O','V'], 'London':['D','E','H'], 'New York':['G','I','P']}

st.set_page_config(page_title="VP Swing Dashboard", layout="wide")
st.markdown("""<style>
.block-container {padding:2.5rem 2rem 1rem 2rem;}
.metric-card {background:#0e1117; border:1px solid #262730; border-radius:8px; padding:16px; text-align:center;}
.metric-label {color:#808495; font-size:0.7rem; text-transform:uppercase; letter-spacing:1.5px; margin-bottom:4px;}
.metric-value {font-size:1.6rem; font-weight:700; color:#fafafa;}
.metric-delta {font-size:0.8rem; margin-top:2px;}
.green {color:#00c853;} .red {color:#ff1744;} .gray {color:#808495;}
.pos-row {background:linear-gradient(135deg, #16213e 0%, #1a1a2e 100%); border:1px solid #2a3a5e; border-radius:10px; padding:16px 20px; margin:10px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.3);}
.big-num {font-size:2.4rem; font-weight:800; letter-spacing:-1px;}
</style>""", unsafe_allow_html=True)

def load_state():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as f: return json.load(f)
    return {'capital':CAPITAL_INITIAL,'trades':[],'open_positions':[]}

def get_price():
    try:
        from phase1_poc_calculator import get_conn
        c=get_conn(); c.autocommit=True; cur=c.cursor()
        cur.execute("SELECT bid,ask FROM market_ticks_xauusd ORDER BY ts DESC LIMIT 1")
        r=cur.fetchone(); cur.close(); c.close()
        if r: return float(r[0]),float(r[1])
    except: pass
    return None,None

def plotly_layout(title="", height=300):
    return dict(
        template="plotly_dark", height=height, margin=dict(l=0,r=0,t=30,b=0),
        title=dict(text=title, font=dict(size=14)),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='#1a1a2e'), yaxis=dict(gridcolor='#1a1a2e'),
        font=dict(color='#ccc'),
    )

state = load_state()
capital = state['capital']; trades = state['trades']; positions = state['open_positions']
bid,ask = get_price()
now = datetime.now(timezone.utc)
h = now.hour
sess = "Tokyo" if 0<=h<6 else "London" if 8<=h<14 else "New York" if 14<=h<21 else "Off"
pnl = capital - CAPITAL_INITIAL
pnl_pct = pnl/CAPITAL_INITIAL*100

# ═══════════════════════════════════════════
# TOP BAR
# ═══════════════════════════════════════════
t1,t2,t3 = st.columns([3,1,1])
with t1:
    pnl_c = "green" if pnl>=0 else "red"
    st.markdown(f'<div class="big-num">${capital:,.2f}</div><div class="{pnl_c}" style="font-size:1.1rem;font-weight:600;">{"+$" if pnl>=0 else "-$"}{abs(pnl):,.2f} ({pnl_pct:+.1f}%)</div>', unsafe_allow_html=True)
with t2:
    if bid:
        st.markdown(f'<div class="metric-label">XAUUSD</div><div class="metric-value">{bid:,.2f}</div><div class="gray">spread {ask-bid:.3f}</div>', unsafe_allow_html=True)
with t3:
    sess_colors = {'Tokyo':'#5c6bc0','London':'#66bb6a','New York':'#ef5350','Off':'#555'}
    cache={}
    for k,v in state.get('daily_cache',{}).items(): cache=v; break
    atr_str = f"ATR {cache['atr']:.2f}" if cache.get('atr') else ""
    st.markdown(f'<div class="metric-label">SESSION</div><div class="metric-value" style="color:{sess_colors.get(sess,"#888")}">{sess}</div><div class="gray">{now.strftime("%H:%M")} UTC · {atr_str}</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
# KPIs
# ═══════════════════════════════════════════
n_trades = len(trades)
df = None
if n_trades > 0:
    df = pd.DataFrame(trades)
    for c in ['pnl_dollar','entry','exit','pnl_oz']: df[c]=df[c].astype(float)
    df['entry_time']=pd.to_datetime(df['entry_time']); df['exit_time']=pd.to_datetime(df['exit_time'])
    df['cum']=df['capital_after'].astype(float); df['date']=df['entry_time'].dt.date
    df['duration']=(df['exit_time']-df['entry_time']).dt.total_seconds()/60
    wins=df[df['pnl_dollar']>0]; losses=df[df['pnl_dollar']<=0]
    gp=wins['pnl_dollar'].sum() if len(wins) else 0
    gl=abs(losses['pnl_dollar'].sum())+0.01
    pf=gp/gl; wr=len(wins)/n_trades*100
    caps=pd.concat([pd.Series([CAPITAL_INITIAL]),df['cum']]).reset_index(drop=True)
    max_dd=((caps-caps.cummax())/caps.cummax()*100).min()
    today_df=df[df['date']==now.date()]
    today_pnl=today_df['pnl_dollar'].sum() if len(today_df) else 0
    today_n=len(today_df)

    def kpi_card(label, value, delta="", color=""):
        d_html = f'<div class="metric-delta {color}">{delta}</div>' if delta else ""
        return f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div>{d_html}</div>'

    k1,k2,k3,k4,k5,k6 = st.columns(6)
    with k1: st.markdown(kpi_card("Trades",n_trades,f"{today_n} aujourd'hui","gray"), unsafe_allow_html=True)
    with k2: st.markdown(kpi_card("Win Rate",f"{wr:.0f}%",f"{len(wins)}W / {len(losses)}L","gray"), unsafe_allow_html=True)
    with k3: st.markdown(kpi_card("Profit Factor",f"{pf:.2f}"), unsafe_allow_html=True)
    with k4:
        avg_w = f"${wins['pnl_dollar'].mean():+,.2f}" if len(wins) else "—"
        st.markdown(kpi_card("Avg Win",avg_w,"","green"), unsafe_allow_html=True)
    with k5:
        avg_l = f"${losses['pnl_dollar'].mean():+,.2f}" if len(losses) else "—"
        st.markdown(kpi_card("Avg Loss",avg_l,"","red"), unsafe_allow_html=True)
    with k6:
        dd_c = "red" if max_dd < -5 else "green"
        st.markdown(kpi_card("Max Drawdown",f"{max_dd:.1f}%","","red"), unsafe_allow_html=True)

st.markdown("")

# ═══════════════════════════════════════════
# POSITIONS OUVERTES
# ═══════════════════════════════════════════
if positions:
    st.markdown(f"#### {len(positions)} Position{'s' if len(positions)>1 else ''} ouverte{'s' if len(positions)>1 else ''}")
    total_unr=0
    for p in positions:
        e=p.get('entry',0);s=p.get('stop',0);best=p.get('best',e)
        d=p.get('strat_dir','');sn=p.get('strat','')
        oz=p.get('pos_oz',0);bars=p.get('bars_held',0)
        trail=p.get('trail_active',False);lots=p.get('lots',0)
        et=str(p.get('entry_time',''))[:16]
        px="—";pnl_d=0;pnl_oz_v=0
        if bid:
            px_v=bid if d=='long' else ask
            pnl_oz_v=(px_v-e) if d=='long' else (e-px_v)
            pnl_d=pnl_oz_v*oz; total_unr+=pnl_d
            px=f"{px_v:.2f}"
        c = "#00c853" if pnl_d>=0 else "#ff1744"
        bar_w = min(int(bars/12*100),100)
        st.markdown(f"""<div class="pos-row" style="border-left:4px solid {c}">
<div style="display:flex;justify-content:space-between;align-items:flex-start;">
<div>
<span style="font-size:1.2rem;font-weight:700;">{sn}</span>
<span style="color:#808495;"> — {STRATS.get(sn,'')}</span><br>
<span style="color:{c};font-weight:600;font-size:0.9rem;">{d.upper()}</span>
<span class="gray"> · ouvert {et}</span>
</div>
<div style="text-align:right;">
<div style="font-size:1.4rem;font-weight:700;color:{c};">${pnl_d:+,.2f}</div>
<div class="gray">{pnl_oz_v:+.2f} oz</div>
</div>
</div>
<div style="display:flex;gap:24px;margin-top:10px;font-size:0.82rem;">
<div><span class="gray">Entree</span><br><b>{e:.2f}</b></div>
<div><span class="gray">Prix actuel</span><br><b>{px}</b></div>
<div><span class="gray">Stop</span><br><b>{s:.2f}</b></div>
<div><span class="gray">Best</span><br><b>{best:.2f}</b></div>
<div><span class="gray">Trail</span><br><b>{'🔒 ON' if trail else '—'}</b></div>
<div><span class="gray">Lots</span><br><b>{lots:.3f}</b></div>
<div><span class="gray">Bars</span><br><b>{bars}/12</b></div>
</div>
<div style="margin-top:8px;background:#1a1a2e;border-radius:3px;height:3px;">
<div style="background:{c};width:{bar_w}%;height:100%;border-radius:3px;"></div>
</div>
</div>""", unsafe_allow_html=True)

    if bid and total_unr != 0:
        c = "#00c853" if total_unr>=0 else "#ff1744"
        st.markdown(f'<div style="text-align:right;font-size:1rem;color:{c};font-weight:600;margin:4px 16px;">PnL latent total: ${total_unr:+,.2f}</div>', unsafe_allow_html=True)
    st.markdown("")

# ═══════════════════════════════════════════
# EQUITY + DRAWDOWN (Plotly)
# ═══════════════════════════════════════════
if df is not None and len(df)>1:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        row_heights=[0.7, 0.3], subplot_titles=("Equity","Drawdown %"))
    eq_x = [df['entry_time'].iloc[0]-pd.Timedelta(minutes=30)] + df['entry_time'].tolist()
    eq_y = [CAPITAL_INITIAL] + df['cum'].tolist()
    fig.add_trace(go.Scatter(x=eq_x, y=eq_y, fill='tozeroy', fillcolor='rgba(0,200,83,0.1)',
                             line=dict(color='#00c853',width=2), name='Capital'), row=1,col=1)
    peak = pd.Series(eq_y).cummax()
    dd = ((pd.Series(eq_y)-peak)/peak*100)
    fig.add_trace(go.Scatter(x=eq_x, y=dd, fill='tozeroy', fillcolor='rgba(255,23,68,0.15)',
                             line=dict(color='#ff1744',width=1.5), name='DD'), row=2,col=1)
    fig.update_layout(**plotly_layout(height=420))
    fig.update_layout(showlegend=False)
    fig.update_yaxes(title_text="$", row=1, col=1)
    fig.update_yaxes(title_text="%", row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════
# TRADES
# ═══════════════════════════════════════════
if df is not None and len(df)>0:
    st.markdown(f"#### Historique ({n_trades} trades)")
    show=df.iloc[::-1].copy()
    show['Ouverture']=show['entry_time'].dt.strftime('%d/%m %H:%M')
    show['Fermeture']=show['exit_time'].dt.strftime('%d/%m %H:%M')
    show['Nom']=show['strat'].map(STRATS)
    show['Dir']=show['dir'].str.upper()
    show['In']=show['entry'].apply(lambda x:f"{x:.2f}")
    show['Out']=show['exit'].apply(lambda x:f"{x:.2f}")
    show['PnL']=show['pnl_dollar'].apply(lambda x:f"${x:+,.2f}")
    show['oz']=show['pnl_oz'].apply(lambda x:f"{x:+.3f}")
    show['Sortie']=show['exit_reason']
    show['Bars']=show['bars_held']
    show['Duree']=show['duration'].apply(lambda x:f"{x:.0f}m")
    show['Cap']=show['capital_after'].apply(lambda x:f"${float(x):,.2f}")

    tbl=show[['Ouverture','Fermeture','strat','Nom','Dir','In','Out','PnL','oz','Sortie','Bars','Duree','Cap']].copy()
    tbl.columns=['Ouverture','Fermeture','Strat','Nom','Dir','In','Out','PnL','PnL oz','Sortie','Bars','Duree','Capital']

    def cpnl(row):
        try:
            v=float(row['PnL'].replace('$','').replace(',','').replace('+',''))
            c='color:#00c853' if v>0 else 'color:#ff1744'
        except: c=''
        return [c]*len(row)
    st.dataframe(tbl.style.apply(cpnl,axis=1), use_container_width=True, hide_index=True, height=min(n_trades*38+40,500))

    st.markdown("")

    # ═══════════════════════════════════════════
    # ANALYTICS
    # ═══════════════════════════════════════════
    st.markdown("#### Analyse")

    # Par strat
    srows=[]
    for sn in sorted(df['strat'].unique()):
        s=df[df['strat']==sn]; n=len(s); w=(s['pnl_dollar']>0).sum()
        gps=s[s['pnl_dollar']>0]['pnl_dollar'].sum(); gls=abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
        srows.append({'Strat':sn,'Nom':STRATS.get(sn,''),'Trades':n,'Wins':w,'Losses':n-w,
            'WR':f"{w/n*100:.0f}%",'PF':f"{gps/gls:.2f}",'PnL':f"${s['pnl_dollar'].sum():+,.2f}",
            'Avg':f"${s['pnl_dollar'].mean():+,.2f}",'Best':f"${s['pnl_dollar'].max():+,.2f}",
            'Worst':f"${s['pnl_dollar'].min():+,.2f}"})
    st.dataframe(pd.DataFrame(srows), use_container_width=True, hide_index=True)

    # Charts
    c1,c2 = st.columns(2)
    with c1:
        pnl_strat = df.groupby('strat')['pnl_dollar'].sum().sort_values()
        colors = ['#00c853' if v>=0 else '#ff1744' for v in pnl_strat.values]
        fig2 = go.Figure(go.Bar(y=pnl_strat.index, x=pnl_strat.values, orientation='h',
                                marker_color=colors, text=[f"${v:+,.0f}" for v in pnl_strat.values],
                                textposition='outside'))
        fig2.update_layout(**plotly_layout("PnL par strategie", 280))
        st.plotly_chart(fig2, use_container_width=True)

    with c2:
        daily = df.groupby('date')['pnl_dollar'].sum()
        colors_d = ['#00c853' if v>=0 else '#ff1744' for v in daily.values]
        fig3 = go.Figure(go.Bar(x=daily.index, y=daily.values, marker_color=colors_d))
        fig3.update_layout(**plotly_layout("PnL journalier", 280))
        st.plotly_chart(fig3, use_container_width=True)

    # Details
    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown("##### Direction")
        for dn in ['long','short']:
            s=df[df['dir']==dn]
            if len(s)==0: continue
            w=(s['pnl_dollar']>0).sum(); gd=s[s['pnl_dollar']>0]['pnl_dollar'].sum()
            ld=abs(s[s['pnl_dollar']<0]['pnl_dollar'].sum())+0.01
            c = "green" if s['pnl_dollar'].sum()>=0 else "red"
            st.markdown(f"**{dn.upper()}** · {len(s)} trades · WR {w/len(s)*100:.0f}% · PF {gd/ld:.2f}")
            st.markdown(f":{c}[**${s['pnl_dollar'].sum():+,.2f}**]")
    with c2:
        st.markdown("##### Sorties")
        for reason in sorted(df['exit_reason'].unique()):
            s=df[df['exit_reason']==reason]; w=(s['pnl_dollar']>0).sum()
            st.markdown(f"**{reason}** · {len(s)} ({w}W / {len(s)-w}L)")
    with c3:
        st.markdown("##### Stats")
        ls=max((sum(1 for _ in g) for k,g in itertools.groupby(df['pnl_dollar']<0) if k),default=0)
        ws=max((sum(1 for _ in g) for k,g in itertools.groupby(df['pnl_dollar']>0) if k),default=0)
        st.markdown(f"Max wins: **{ws}** · Max losses: **{ls}**")
        if len(wins): st.markdown(f"Avg win: :green[**${wins['pnl_dollar'].mean():+,.2f}**]")
        if len(losses): st.markdown(f"Avg loss: :red[**${losses['pnl_dollar'].mean():+,.2f}**]")
        st.markdown(f"Duree moy: **{df['duration'].mean():.0f}min** · Bars moy: **{df['bars_held'].mean():.1f}**")

else:
    # No trades yet
    st.markdown("")
    c1,c2,c3 = st.columns([1,2,1])
    with c2:
        st.markdown(f"""<div style="text-align:center; padding:60px 20px; background:#0e1117; border:1px solid #262730; border-radius:12px;">
        <div style="font-size:2rem;">⏳</div>
        <div style="font-size:1.2rem; color:#ccc; margin:12px 0;">En attente du premier trade</div>
        <div style="color:#808495;">10 strategies surveillent XAUUSD 5 minutes</div>
        <div style="margin-top:16px; color:#555; font-size:0.85rem;">
            <b style="color:#5c6bc0;">Tokyo</b>: {', '.join(SESS_STRATS['Tokyo'])} ·
            <b style="color:#66bb6a;">London</b>: {', '.join(SESS_STRATS['London'])} ·
            <b style="color:#ef5350;">NY</b>: {', '.join(SESS_STRATS['New York'])}
        </div>
        </div>""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("#### Config")
    st.caption("Trailing pessimiste")
    st.caption("SL 1.5 · ACT 0.3 · TRAIL 0.3 · T12")
    st.divider()
    for s_name, s_strats in SESS_STRATS.items():
        st.markdown(f"**{s_name}**")
        for s in s_strats:
            st.caption(f"{s} — {STRATS[s]}")

time.sleep(10)
st.rerun()
