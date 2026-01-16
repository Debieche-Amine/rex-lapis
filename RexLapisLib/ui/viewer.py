import streamlit as st
import pandas as pd
import pickle
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="RexLapis Lab", page_icon="🧪")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }
    div[data-testid="metric-container"] {
        background-color: #1c1e26;
        border: 1px solid #2d303e;
        padding: 8px 12px;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. DATA UTILITIES
# ---------------------------------------------------------
SETTINGS_FILE = "view_settings.json"
RESULTS_PATH = "latest_simulation.pkl"

def load_settings():
    default = {"timeframe": "Original", "max_candles": 2000}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f: return json.load(f)
        except: return default
    return default

def save_settings():
    settings = {
        "timeframe": st.session_state.get("sel_tf", "Original"),
        "max_candles": st.session_state.get("sel_limit", 2000)
    }
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

if 'init_done' not in st.session_state:
    saved = load_settings()
    st.session_state['sel_tf'] = saved['timeframe']
    st.session_state['sel_limit'] = saved['max_candles']
    st.session_state['init_done'] = True

@st.cache_data
def load_results():
    if os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH, 'rb') as f:
            return pickle.load(f)
    return None

def resample_data(df, interval):
    if interval == "Original": return df
    
    # Map friendly names to Pandas Offset Aliases
    rule_map = {"1min": "1min", "5min": "5min", "15min": "15min", "1H": "1h", "4H": "4h", "1D": "1D"}
    rule = rule_map.get(interval, "1min")
    
    df_temp = df.set_index('timestamp').copy()
    
    agg_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}
    if 'volume' in df_temp.columns: agg_dict['volume'] = 'sum'
    
    # Handle indicators (take last value)
    for col in df_temp.columns:
        if col not in agg_dict:
            agg_dict[col] = 'last'

    # Resample and drop empty bins immediately to prevent "Invisible Candles"
    return df_temp.resample(rule).agg(agg_dict).dropna().reset_index()

def get_pandas_freq(interval_str):
    """Converts UI interval to Pandas Frequency string for snapping."""
    mapping = {
        "Original": None, "1min": "1min", "5min": "5min", 
        "15min": "15min", "1H": "1h", "4H": "4h", "1D": "1D"
    }
    return mapping.get(interval_str, "1min")

def align_trades_mathematically(trades_df, interval_str):
    """
    FIX: Mathematically floors the trade time to the nearest candle start time.
    This ensures exact X-axis alignment without needing merge_asof.
    """
    if trades_df.empty: return trades_df
    
    df = trades_df.copy()
    df['time'] = pd.to_datetime(df['time'])
    
    freq = get_pandas_freq(interval_str)
    
    if freq:
        # Mathematical Floor: 10:07 -> 10:00 (for 5min/10min/etc)
        df['plot_time'] = df['time'].dt.floor(freq)
    else:
        df['plot_time'] = df['time']
        
    return df

# ---------------------------------------------------------
# 3. SIDEBAR
# ---------------------------------------------------------
results = load_results()
if not results:
    st.error("⚠️ No simulation data found.")
    st.stop()

# Get Full Data
df_full = results['data_with_indicators']
available_cols = [c for c in df_full.columns if c not in ['timestamp', 'open', 'high', 'low', 'close', 'volume']]

# Group Options
overlay_options = [c for c in available_cols if any(x in c.lower() for x in ['ma', 'ema', 'sma', 'bb_', 'supertrend'])]
oscillator_options = []
if 'volume' in df_full.columns: oscillator_options.append('Volume')
if 'rsi' in df_full.columns: oscillator_options.append('RSI')
if 'macd' in df_full.columns: oscillator_options.append('MACD')
if 'score' in df_full.columns: oscillator_options.append('Score')

st.sidebar.markdown("### ⚙️ View Settings")
max_candles = st.sidebar.select_slider("Data Window", [500, 1000, 2000, 5000, 10000], key="sel_limit", on_change=save_settings)
selected_tf = st.sidebar.selectbox("Timeframe", ["Original", "5min", "15min", "1H", "4H", "1D"], key="sel_tf", on_change=save_settings)

st.sidebar.markdown("---")
show_trades = st.sidebar.checkbox("Show Trades", value=True)
selected_overlays = st.sidebar.multiselect("Overlays", overlay_options, default=[])
selected_oscillators = st.sidebar.multiselect("Indicators", oscillator_options, default=[])

# ---------------------------------------------------------
# 4. CHART DATA PREP
# ---------------------------------------------------------
df_display = resample_data(df_full, selected_tf)

# Optimization: Slice
if len(df_display) > max_candles:
    df_display = df_display.tail(max_candles).reset_index(drop=True)

df_trades = pd.DataFrame(results['trades_log'])

# --- KPIs ---
c1, c2, c3, c4 = st.columns(4)
bal = results['final_balance']
pnl = bal - results['initial_balance']
roi = results['roi']
c1.metric("Balance", f"${bal:,.2f}")
c2.metric("PnL", f"${pnl:,.2f}", f"{roi:.2f}%")
c3.metric("Trades", results['total_trades'])
c4.metric("Window", f"{len(df_display)} Candles")

# ---------------------------------------------------------
# 5. PLOTTING
# ---------------------------------------------------------
rows = 1 + len(selected_oscillators)
if rows == 1: row_heights = [1.0]
else:
    sub_h = 0.3 / (rows - 1)
    row_heights = [0.7] + [sub_h] * (rows - 1)

fig = make_subplots(
    rows=rows, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.02, 
    row_heights=row_heights,
    specs=[[{"secondary_y": True}]] + [[{"secondary_y": False}]] * (rows-1)
)

curr = 1

# --- ROW 1: Price ---
fig.add_trace(go.Candlestick(
    x=df_display['timestamp'],
    open=df_display['open'], high=df_display['high'],
    low=df_display['low'], close=df_display['close'],
    name="Price",
    increasing_line_color='#00E676', decreasing_line_color='#FF1744'
), row=curr, col=1)

# Overlays
colors = ['#FFA726', '#2979FF', '#EA80FC', '#00B0FF', '#FFFF00']
for i, overlay in enumerate(selected_overlays):
    if overlay in df_display.columns:
        fig.add_trace(go.Scatter(
            x=df_display['timestamp'], y=df_display[overlay], 
            name=overlay.upper(), line=dict(width=1, color=colors[i%len(colors)])
        ), row=curr, col=1)

# --- TRADES (FIXED POSITIONING) ---
if show_trades and not df_trades.empty:
    # 1. Snap Time
    aligned_trades = align_trades_mathematically(df_trades, selected_tf)
    
    # 2. Get Price Levels for Y-Positioning
    # We merge with candle data ONLY to get High/Low for positioning logic
    # (Not for time alignment anymore)
    visual_data = pd.merge(
        aligned_trades, 
        df_display[['timestamp', 'high', 'low']], 
        left_on='plot_time', 
        right_on='timestamp', 
        how='inner' # Only show trades that exist in visible candles
    )
    
    if not visual_data.empty:
        buys = visual_data[visual_data['type'] == 'Buy']
        sells = visual_data[visual_data['type'].isin(['Sell', 'Close'])]
        
        # FIX: Offset Calculation (e.g., 0.2% away from candle)
        # This prevents the arrow from touching the wick
        
        if not buys.empty:
            fig.add_trace(go.Scatter(
                x=buys['plot_time'], 
                y=buys['low'] * 0.998, # 0.2% below Low
                mode='markers', 
                marker=dict(symbol='triangle-up', size=12, color='#00E676', line=dict(width=1, color='black')),
                name="Buy", hovertemplate="BUY<br>Price: %{customdata:.2f}<extra></extra>",
                customdata=buys['price']
            ), row=curr, col=1)
        
        if not sells.empty:
            fig.add_trace(go.Scatter(
                x=sells['plot_time'], 
                y=sells['high'] * 1.002, # 0.2% above High
                mode='markers', 
                marker=dict(symbol='triangle-down', size=12, color='#FF1744', line=dict(width=1, color='black')),
                name="Sell", hovertemplate="SELL<br>Price: %{customdata:.2f}<extra></extra>",
                customdata=sells['price']
            ), row=curr, col=1)

# --- OSCILLATORS ---
for osc in selected_oscillators:
    curr += 1
    if osc == 'Volume':
        cols = ['#00E676' if c >= o else '#FF1744' for c, o in zip(df_display['close'], df_display['open'])]
        fig.add_trace(go.Bar(x=df_display['timestamp'], y=df_display['volume'], marker_color=cols, name="Vol"), row=curr, col=1)
    elif osc == 'RSI':
        fig.add_trace(go.Scatter(x=df_display['timestamp'], y=df_display['rsi'], name="RSI", line=dict(color='#AB47BC')), row=curr, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="red", row=curr, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="green", row=curr, col=1)
    elif osc == 'MACD':
        if 'macd_hist' in df_display.columns:
            cols = ['#00E676' if v >= 0 else '#FF1744' for v in df_display['macd_hist']]
            fig.add_trace(go.Bar(x=df_display['timestamp'], y=df_display['macd_hist'], marker_color=cols, name="Hist"), row=curr, col=1)
        if 'macd' in df_display.columns:
            fig.add_trace(go.Scatter(x=df_display['timestamp'], y=df_display['macd'], name="MACD", line=dict(color='#2979FF')), row=curr, col=1)
        if 'macd_signal' in df_display.columns:
            fig.add_trace(go.Scatter(x=df_display['timestamp'], y=df_display['macd_signal'], name="Sig", line=dict(color='#FFA726')), row=curr, col=1)
    elif osc == 'Score':
        cols = ['#00E676' if v >= 4 else '#FF1744' if v <= -4 else 'gray' for v in df_display['score']]
        fig.add_trace(go.Bar(x=df_display['timestamp'], y=df_display['score'], marker_color=cols, name="Score"), row=curr, col=1)

# --- VIEWPORT & LAYOUT ---
x_range_start = None
x_range_end = None
if len(df_display) > 0:
    view_width = 150 # Start with 150 candles visible
    end_idx = len(df_display) - 1
    start_idx = max(0, end_idx - view_width)
    x_range_start = df_display['timestamp'].iloc[start_idx]
    x_range_end = df_display['timestamp'].iloc[end_idx]

# Unique UID to keep state when data changes, reset when timeframe changes
zoom_uid = f"uid_{selected_tf}_{len(selected_oscillators)}_{len(selected_overlays)}"

fig.update_layout(
    uirevision=zoom_uid,
    template="plotly_dark",
    height=500 + ((rows-1) * 150),
    margin=dict(l=10, r=60, t=10, b=10),
    dragmode="pan",
    hovermode="x unified",
    
    xaxis=dict(
        range=[x_range_start, x_range_end],
        rangeslider=dict(visible=False),
        gridcolor='#1f222a',
        type='date' # Ensure date axis
    ),
    yaxis=dict(side="right", gridcolor='#1f222a', fixedrange=False),
    legend=dict(orientation="h", y=1.01, x=0),
    paper_bgcolor="#0E1117",
    plot_bgcolor="#0E1117"
)

st.plotly_chart(fig, use_container_width=True, config={
    'scrollZoom': True,
    'displayModeBar': True,
    'modeBarButtons': [['drawline', 'resetScale2d']]
})

with st.expander("📋 Trade Log"):
    if not df_trades.empty:
        cols = ['time', 'type', 'qty', 'price']
        if 'pnl' in df_trades.columns: cols.extend(['pnl'])
        st.dataframe(df_trades[cols].style.format({'price':'{:.2f}', 'pnl':'{:.2f}'}), use_container_width=True)
    else:
        st.write("No trades.")