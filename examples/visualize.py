# how to run --> python -m streamlit run examples\visualize.py 
# Requirements: pip install streamlit plotly pandas numpy
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ---------------------------------------------------------
# 1. SETUP & CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    layout="wide", 
    page_title="RexLapis XAUT Pro Terminal",
    page_icon="👑",
    initial_sidebar_state="expanded"
)

# Professional Dark & Gold Theme CSS
st.markdown("""
<style>
    /* Main Background */
    .stApp { background-color: #0e1117; }
    
    /* Buttons */
    div.stButton > button:first-child {
        background-color: #d4af37; 
        color: black; 
        border: none; 
        font-weight: bold;
        transition: 0.3s;
    }
    div.stButton > button:first-child:hover {
        background-color: #f4cf57; 
        transform: scale(1.02);
    }

    /* Metrics */
    [data-testid="stMetricValue"] { 
        font-family: 'monospace'; 
        color: #d4af37; 
    }
    [data-testid="stMetricLabel"] {
        color: #9ca3af;
    }

    /* Custom Signal Boxes */
    .signal-box {
        padding: 15px; 
        border-radius: 8px; 
        text-align: center; 
        font-weight: bold; 
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. INTERNAL LIBRARY
# ---------------------------------------------------------
class LocalDataProcessor:
    def __init__(self, df=None):
        self.df = df

    @staticmethod
    def normalize_columns(df):
        """Standardizes column names to lowercase for the engine."""
        df.columns = df.columns.str.lower().str.strip()
        rename_map = {
            'date': 'timestamp', 'time': 'timestamp', 'datetime': 'timestamp',
            'vol': 'volume', 'qty': 'volume'
        }
        df.rename(columns=rename_map, inplace=True)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df

    @staticmethod
    def resample_candles(df, interval):
        """Resamples OHLCV data to higher timeframes."""
        if interval is None:
            return df
        
        df = df.set_index('timestamp')
        agg_dict = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }
        # Handle cases where volume might be missing
        if 'volume' not in df.columns:
            del agg_dict['volume']
            
        df_res = df.resample(interval).agg(agg_dict).dropna().reset_index()
        return df_res

# ---------------------------------------------------------
# 3. ALGORITHMIC ENGINE (No Cheating / Pure Math)
# ---------------------------------------------------------

def calculate_rsi(series, period=14):
    """
    Relative Strength Index.
    Expects a pandas Series (e.g., df['close']), not the whole DataFrame.
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(df, fast=12, slow=26, signal=9):
    """
    Moving Average Convergence Divergence.
    Trend-following momentum indicator.
    """
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    df['macd'] = ema_fast - ema_slow
    df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    return df

def calculate_bollinger_bands(df, period=20, std_dev=2):
    """
    Bollinger Bands for volatility measurement.
    """
    df['bb_mid'] = df['close'].rolling(window=period).mean()
    df['bb_std'] = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * std_dev)
    df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * std_dev)
    return df

def calculate_supertrend(df, period=10, multiplier=3):
    """
    SuperTrend Algorithm (Iterative).
    Uses ATR to detect trend direction.
    Logic is strictly based on t-1 to avoid look-ahead bias.
    """
    hl2 = (df['high'] + df['low']) / 2
    # ATR Calculation
    df['tr0'] = abs(df['high'] - df['low'])
    df['tr1'] = abs(df['high'] - df['close'].shift(1))
    df['tr2'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
    df['atr'] = df['tr'].ewm(alpha=1/period, adjust=False).mean()

    # Basic Bands
    upper_basic = hl2 + (multiplier * df['atr'])
    lower_basic = hl2 - (multiplier * df['atr'])

    # Numpy Optimization for Speed
    close = df['close'].values
    ub = upper_basic.values
    lb = lower_basic.values
    
    # Initialize arrays
    upper_band = np.zeros(len(df))
    lower_band = np.zeros(len(df))
    supertrend = np.zeros(len(df), dtype=bool) # True = Bullish, False = Bearish
    trend_line = np.zeros(len(df))

    # Iterative calculation respecting Time (t)
    for i in range(1, len(df)):
        # Calculate Final Upper Band
        if ub[i] < upper_band[i-1] or close[i-1] > upper_band[i-1]:
            upper_band[i] = ub[i]
        else:
            upper_band[i] = upper_band[i-1]

        # Calculate Final Lower Band
        if lb[i] > lower_band[i-1] or close[i-1] < lower_band[i-1]:
            lower_band[i] = lb[i]
        else:
            lower_band[i] = lower_band[i-1]

        # Determine Trend Direction
        if supertrend[i-1] == True and close[i] <= lower_band[i]:
            supertrend[i] = False
        elif supertrend[i-1] == False and close[i] >= upper_band[i]:
            supertrend[i] = True
        else:
            supertrend[i] = supertrend[i-1]
            
        # Set line for visualization
        if supertrend[i]:
            trend_line[i] = lower_band[i]
        else:
            trend_line[i] = upper_band[i]

    df['supertrend_line'] = trend_line
    df['trend_direction'] = supertrend
    return df

def analyze_market_sentiment(row):
    """
    Calculates a 'Score' based on the confluence of indicators.
    This acts as the 'Prediction' engine for the current moment.
    """
    score = 0
    
    # 1. SuperTrend (Heavy Weight)
    if row['trend_direction']: score += 3
    else: score -= 3
    
    # 2. RSI (Mean Reversion logic)
    if row['rsi'] < 30: score += 2    # Oversold -> Bullish
    elif row['rsi'] > 70: score -= 2  # Overbought -> Bearish
    
    # 3. MACD (Momentum)
    if row['macd'] > row['macd_signal']: score += 1
    else: score -= 1
    
    # 4. Price vs Bollinger Mid (Simple Trend)
    if row['close'] > row['bb_mid']: score += 1
    else: score -= 1
    
    return score

# ---------------------------------------------------------
# 4. UI & DATA HANDLING
# ---------------------------------------------------------
st.sidebar.header("🕹️ Terminal Config")

# A. Data Source
with st.sidebar.expander("📂 Data Source", expanded=True):
    data_source = st.radio("Select Source", ["Upload CSV", "Demo Data"])
    
    df_raw = pd.DataFrame()
    
    if data_source == "Upload CSV":
        uploaded_file = st.file_uploader("Upload OHLCV Data", type=['csv'])
        if uploaded_file:
            df_raw = pd.read_csv(uploaded_file)
            df_raw = LocalDataProcessor.normalize_columns(df_raw)
    else:
        # Generate clean demo data for XAUT context
        dates = pd.date_range(start="2024-01-01", periods=1000, freq='1h')
        base_price = 2000
        np.random.seed(42)
        prices = base_price + np.cumsum(np.random.randn(1000) * 2)
        df_raw = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices + 5,
            'low': prices - 5,
            'close': prices + np.random.randn(1000),
            'volume': np.random.randint(100, 5000, 1000)
        })

# B. Settings
with st.sidebar.expander("⚙️ Chart & Strategy", expanded=True):
    # Timeframe
    resample_map = {"Original": None, "15m": "15min", "1h": "h", "4h": "4h", "1d": "D"}
    resample_option = st.selectbox("Interval", list(resample_map.keys()), index=0)
    
    # Visuals
    candle_limit = st.slider("Zoom (Candles)", 100, 1500, 300)
    chart_height = st.slider("Canvas Height", 500, 1200, 800)
    
    # Algorithm Params
    st.caption("Algorithm Sensitivity")
    atr_period = st.number_input("ATR Period", value=10)
    atr_mult = st.number_input("ATR Factor", value=3.0, step=0.1)

# ---------------------------------------------------------
# 5. EXECUTION & VISUALIZATION
# ---------------------------------------------------------
if not df_raw.empty:
    
    # 1. Processing
    interval = resample_map[resample_option]
    df = LocalDataProcessor.resample_candles(df_raw, interval)
    
    # 2. Calculating Indicators (ORDER MATTERS)
    # Corrected: RSI now receives only the Close series, avoiding the TypeError
    df = calculate_supertrend(df, period=atr_period, multiplier=atr_mult)
    df['rsi'] = calculate_rsi(df['close']) 
    df = calculate_macd(df)
    df = calculate_bollinger_bands(df)
    
    # 3. Generating Confluence Score (The "Prediction")
    df['score'] = df.apply(analyze_market_sentiment, axis=1)

    # 4. Slicing for View
    plot_df = df.tail(int(candle_limit)).copy()
    last_candle = plot_df.iloc[-1]
    prev_candle = plot_df.iloc[-2]

    # --- TOP HUD ROW ---
    st.markdown("### 📊 Market Intelligence")
    
    # Determine Sentiment Text
    score = last_candle['score']
    if score >= 4: sent_text, sent_color = "STRONG BUY", "#00ff00"
    elif score >= 1: sent_text, sent_color = "WEAK BUY", "#b2ffb2"
    elif score <= -4: sent_text, sent_color = "STRONG SELL", "#ff0000"
    elif score <= -1: sent_text, sent_color = "WEAK SELL", "#ffb2b2"
    else: sent_text, sent_color = "NEUTRAL / CHOPPY", "#cccccc"

    col1, col2, col3, col4 = st.columns(4)
    
    # Metric 1: Price
    change = last_candle['close'] - prev_candle['close']
    col1.metric("Close Price", f"{last_candle['close']:.2f}", f"{change:.2f}")
    
    # Metric 2: AI Sentiment (The Confluence)
    with col2:
        st.markdown(f"""
        <div class="signal-box" style="border: 1px solid {sent_color}; color: {sent_color}; box-shadow: 0 0 10px {sent_color}40;">
            SIGNAL: {sent_text}<br>
            <span style="font-size:0.8em; opacity:0.8">Score: {score}/7</span>
        </div>
        """, unsafe_allow_html=True)
        
    # Metric 3: SuperTrend Status
    st_status = "BULLISH" if last_candle['trend_direction'] else "BEARISH"
    st_color = "#00b15d" if last_candle['trend_direction'] else "#ff3b30"
    with col3:
         st.markdown(f"""
        <div class="signal-box" style="background-color: {st_color}20; color: {st_color};">
            TREND: {st_status}
        </div>
        """, unsafe_allow_html=True)
         
    # Metric 4: Volatility
    col4.metric("Volatility (ATR)", f"{last_candle['atr']:.2f}", "Points")

    # --- ADVANCED CHARTING ---
    fig = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.01, 
        row_heights=[0.6, 0.2, 0.2]
    )

    # ROW 1: Price + SuperTrend + Bollinger
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=plot_df['timestamp'],
        open=plot_df['open'], high=plot_df['high'],
        low=plot_df['low'], close=plot_df['close'],
        name="Price",
        increasing_line_color='#00b15d', decreasing_line_color='#ff3b30'
    ), row=1, col=1)

    # SuperTrend Line
    st_line_color = ["#00b15d" if x else "#ff3b30" for x in plot_df['trend_direction']]
    fig.add_trace(go.Scatter(
        x=plot_df['timestamp'], y=plot_df['supertrend_line'],
        mode='markers', marker=dict(size=2, color=st_line_color),
        name="SuperTrend Trailing Stop"
    ), row=1, col=1)
    
    # Bollinger Bands (Subtle)
    fig.add_trace(go.Scatter(
        x=plot_df['timestamp'], y=plot_df['bb_upper'],
        line=dict(width=1, color='rgba(255, 255, 255, 0.1)'), name="BB Upper"
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=plot_df['timestamp'], y=plot_df['bb_lower'],
        line=dict(width=1, color='rgba(255, 255, 255, 0.1)'), fill='tonexty', 
        fillcolor='rgba(255, 255, 255, 0.02)', name="BB Lower"
    ), row=1, col=1)

    # Buy/Sell Arrows (Calculated purely on trend flip)
    # We find where trend_direction changes from False to True (Buy) or True to False (Sell)
    buy_signals = plot_df[(plot_df['trend_direction'] == True) & (plot_df['trend_direction'].shift(1) == False)]
    sell_signals = plot_df[(plot_df['trend_direction'] == False) & (plot_df['trend_direction'].shift(1) == True)]
    
    fig.add_trace(go.Scatter(
        x=buy_signals['timestamp'], y=buy_signals['low'] - (buy_signals['atr']*0.5),
        mode='markers', marker=dict(symbol='triangle-up', size=14, color='#00ff00'),
        name="BUY FLIP"
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=sell_signals['timestamp'], y=sell_signals['high'] + (sell_signals['atr']*0.5),
        mode='markers', marker=dict(symbol='triangle-down', size=14, color='#ff0000'),
        name="SELL FLIP"
    ), row=1, col=1)

    # ROW 2: MACD
    fig.add_trace(go.Bar(
        x=plot_df['timestamp'], y=plot_df['macd_hist'],
        marker_color=['#00b15d' if x >= 0 else '#ff3b30' for x in plot_df['macd_hist']],
        name="MACD Histogram"
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=plot_df['timestamp'], y=plot_df['macd'], line=dict(color='white', width=1), name="MACD Line"
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=plot_df['timestamp'], y=plot_df['macd_signal'], line=dict(color='orange', width=1), name="Signal Line"
    ), row=2, col=1)

    # ROW 3: RSI
    fig.add_trace(go.Scatter(
        x=plot_df['timestamp'], y=plot_df['rsi'],
        line=dict(color='#d4af37', width=1.5), name="RSI"
    ), row=3, col=1)
    
    # RSI Zones
    fig.add_hline(y=70, line_dash="dot", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="green", row=3, col=1)
    fig.add_hrect(y0=30, y1=70, fillcolor="gray", opacity=0.1, line_width=0, row=3, col=1)

    # Layout Engine
    fig.update_layout(
        template="plotly_dark",
        height=chart_height,
        margin=dict(l=10, r=80, t=20, b=40),
        dragmode="pan",
        hovermode="x unified",
        paper_bgcolor="black",
        plot_bgcolor="black",
        showlegend=False,
        xaxis_rangeslider_visible=False
    )

    # Axis Settings (Scalability)
    # Row 1 (Price): Dynamic Y-axis
    fig.update_yaxes(side="right", fixedrange=False, gridcolor="#222", row=1, col=1)
    # Row 2 (MACD): Fixed Y-axis
    fig.update_yaxes(side="right", fixedrange=False, gridcolor="#222", row=2, col=1)
    # Row 3 (RSI): Fixed Range 0-100
    fig.update_yaxes(side="right", range=[0, 100], fixedrange=True, gridcolor="#222", row=3, col=1)
    
    # X-Axis Grid
    fig.update_xaxes(gridcolor="#222", showline=True, linecolor="#444")

    # Render
    st.plotly_chart(fig, use_container_width=True, config={
        'scrollZoom': True,
        'displayModeBar': False,
        'responsive': True
    })

    # Strategy Explanation
    with st.expander("ℹ️ Strategy & Algorithms Documentation"):
        st.markdown("""
        **No-Cheat Principle:** All indicators calculate values for time `t` using data from `t` and prior. No future data is ever accessed.
        
        1.  **SuperTrend (Primary Trend):** 
            *   Calculates volatility using ATR.
            *   If Price > Band, Trend is Bullish. If Price < Band, Trend is Bearish.
            *   Acts as a dynamic Support/Resistance.
        
        2.  **Confluence Score (The "Signal"):**
            *   Combines SuperTrend, RSI, MACD, and Bollinger Bands.
            *   Score > 4: Strong statistical probability of upward movement.
            *   Score < -4: Strong statistical probability of downward movement.
        """)

else:
    st.info("Waiting for data... Upload a CSV or select 'Demo Data' in the sidebar.")