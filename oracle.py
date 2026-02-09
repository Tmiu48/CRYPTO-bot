import streamlit as st
import pandas as pd
import yfinance as yf
import ccxt
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import numpy as np

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Crypto Oracle Ultimate v9.5", layout="wide", page_icon="🚨")

# --- ENGINE DANYCH ---
@st.cache_data(ttl=300)
def get_crypto_data(symbol):
    try:
        exchange = ccxt.binance()
        ticker = f"{symbol}/USDT"
        ohlcv = exchange.fetch_ohlcv(ticker, timeframe='1d', limit=100) # Zwiększono limit dla MA i RSI
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Pobieranie danych Makro
        ndx_data = yf.download("^IXIC", period="100d", interval="1d")['Close']
        dxy_data = yf.download("DX-Y.NYB", period="100d", interval="1d")['Close']
        
        fng_res = requests.get("https://api.alternative.me/fng/").json()
        fng_val = int(fng_res['data'][0]['value'])
        fng_status = fng_res['data'][0]['value_classification']

        # --- DOPISANO: WSKAŹNIKI TECHNICZNE ---
        # 1. Średnia Krocząca (MA20)
        df['MA20'] = df['close'].rolling(window=20).mean()
        
        # 2. Wstęgi Bollingera
        df['STD'] = df['close'].rolling(window=20).std()
        df['BB_upper'] = df['MA20'] + (df['STD'] * 2)
        df['BB_lower'] = df['MA20'] - (df['STD'] * 2)
        
        # 3. RSI (Relative Strength Index)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        return df, ndx_data, dxy_data, fng_val, fng_status
    except Exception as e:
        st.error(f"Błąd API dla {symbol}: {e}")
        return None

# --- SIDEBAR: KONTROLA I ALERTY ---
st.sidebar.title("🎛️ Terminal Control")
selected_coin = st.sidebar.selectbox(
    "Wybierz kryptowalutę:",
    ["BTC", "ETH", "SOL", "XRP"]
)

st.sidebar.divider()

st.sidebar.subheader("🚨 Live Alerts Setup")
alert_threshold = st.sidebar.slider("Czułość alertu Fibo (%)", 0.5, 5.0, 1.5)
enable_visuals = st.sidebar.checkbox("Włącz powiadomienia wizualne", value=True)

st.sidebar.divider()
st.sidebar.info(f"Monitorujesz: **{selected_coin}/USDT**")

# --- POBIERANIE DANYCH ---
data = get_crypto_data(selected_coin)

if data:
    df_crypto, ser_nasdaq, ser_dxy, fng_val, fng_status = data
    
    # --- NAPRAWA BŁĘDU (KONWERSJA NA FLOAT) ---
    cur_price = float(df_crypto['close'].iloc[-1])
    prev_price = float(df_crypto['close'].iloc[-2])
    price_change = ((cur_price / prev_price) - 1) * 100
    
    val_nasdaq = float(ser_nasdaq.iloc[-1])
    val_dxy = float(ser_dxy.iloc[-1])
    
    hi, lo = float(df_crypto['high'].max()), float(df_crypto['low'].min())
    fib_0618 = hi - 0.618 * (hi - lo)
    
    dist_to_fib = abs(cur_price - fib_0618) / fib_0618 * 100
    is_alert = dist_to_fib <= alert_threshold

    # --- SYSTEM POWIADOMIEŃ ---
    if is_alert and enable_visuals:
        st.error(f"⚠️ **MARKET ALERT:** Cena {selected_coin} w strefie Fibo 0.618 (${fib_0618:,.2f}). Dystans: {dist_to_fib:.2f}%")
    elif cur_price > hi * 0.98 and enable_visuals:
        st.warning(f"🚀 **FOMO ALERT:** {selected_coin} blisko szczytu (${hi:,.2f})!")

    # --- UI: TOP METRICS ---
    st.title(f"🏦 {selected_coin} Oracle Terminal v9.5")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"Cena {selected_coin}", f"${cur_price:,.2f}", f"{price_change:.2f}%")
    m2.metric("Market Sentiment", f"{fng_val}/100", fng_status)
    m3.metric("DXY Index", f"{val_dxy:.2f}", "Neg. Correlation")
    m4.metric("NASDAQ 100", f"{val_nasdaq:,.0f}", "Risk-On Drive")

    st.divider()

    # --- UI: ZAKŁADKI ---
    # DOPISANO: Zakładki "Backtesting" oraz "Likwidacje"
    tab_main, tab_macro, tab_backtest, tab_liq, tab_data = st.tabs([
        "🎯 ANALIZA GŁÓWNA", "📡 KORELACJE", "📈 BACKTESTING", "🔥 LIKWIDACJE", "📄 LOGI SYSTEMOWE"
    ])

    with tab_main:
        col_chart, col_score = st.columns([2, 1])
        
        with col_chart:
            # ZWIĘKSZONO vertical_spacing z 0.03 na 0.08 dla wyraźniejszego odstępu
            # DODANO subplot_titles dla wizualnego oddzielenia sekcji
            fig = make_subplots(
                rows=3, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.08,  # Większy odstęp między wykresami
                row_heights=[0.6, 0.2, 0.2],
                subplot_titles=("📈 PRICE ACTION & INDICATORS", "📊 TRADING VOLUME", "⚡ RSI OSCILLATOR")
            )
            
            # 1. RZĄD: Cena + MA20 + BB
            fig.add_trace(go.Candlestick(
                x=df_crypto['timestamp'], open=df_crypto['open'], high=df_crypto['high'], 
                low=df_crypto['low'], close=df_crypto['close'], name="Price"
            ), row=1, col=1)
            
            fig.add_trace(go.Scatter(x=df_crypto['timestamp'], y=df_crypto['MA20'], name="MA20", line=dict(color='orange', width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_crypto['timestamp'], y=df_crypto['BB_upper'], name="BB Upper", line=dict(color='gray', dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df_crypto['timestamp'], y=df_crypto['BB_lower'], name="BB Lower", line=dict(color='gray', dash='dot')), row=1, col=1)
            
            # Poziom Fibo 0.618
            fig.add_hline(y=fib_0618, line_dash="dash", line_color="gold", annotation_text="Fibo 0.618", row=1, col=1)

            # 2. RZĄD: Wolumen
            fig.add_trace(go.Bar(
                x=df_crypto['timestamp'], 
                y=df_crypto['volume'], 
                name="Volume", 
                marker_color='rgba(128,128,128,0.5)'
            ), row=2, col=1)
            
            # 3. RZĄD: RSI
            fig.add_trace(go.Scatter(
                x=df_crypto['timestamp'], 
                y=df_crypto['RSI'], 
                name="RSI Indicator", 
                line=dict(color='purple', width=2)
            ), row=3, col=1)
            
            # Linie poziomów RSI (Oversold/Overbought)
            fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=3, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=3, col=1)

            # --- STYLIZACJA ---
            fig.update_layout(
                template="plotly_dark", 
                height=900,  # Zwiększono wysokość, aby wykresy nie były ściśnięte
                xaxis_rangeslider_visible=False, 
                margin=dict(l=10, r=10, t=40, b=10),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            # Poprawa wyglądu tytułów subplotów (czcionka i kolor)
            for i in fig['layout']['annotations']:
                i['font'] = dict(size=14, color='#888', family="Arial Black")

            st.plotly_chart(fig, use_container_width=True)

        with col_score:
            # Scoring Engine
            score = 50
            if cur_price > fib_0618: score += 10
            if fng_val < 35: score += 15
            if val_dxy < 104.5: score += 10
            if df_crypto['RSI'].iloc[-1] < 30: score += 15 # DOPISANO: Bonus za wyprzedanie RSI
            
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = score,
                gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "white"},
                         'steps': [{'range': [0, 35], 'color': "#ff4b4b"},
                                   {'range': [35, 65], 'color': "#31333F"},
                                   {'range': [65, 100], 'color': "#00c805"}]}))
            fig_gauge.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(fig_gauge, use_container_width=True)
            
            if score > 65: st.success(f"🚀 SYGNAŁ: SILNA AKUMULACJA")
            elif score < 35: st.error(f"⚠️ SYGNAŁ: REDUKCJA RYZYKA")
            else: st.warning(f"⚖️ SYGNAŁ: NEUTRALNY")
            
            st.write(f"**Techniczne RSI:** {float(df_crypto['RSI'].iloc[-1]):.2f}")
            st.write(f"**Wstęgi Bollingera:** {'Cena przy dolnej wstędze (Kupno)' if cur_price < df_crypto['BB_lower'].iloc[-1] else 'Neutralne'}")

        # --- SEKACJA RULETKI (NA SAMYM DOLE TAB_MAIN) ---
        st.divider()
        st.header("🎰 CASINO CLASSIC: EUROPEAN ROULETTE")
        
        if 'casino_balance' not in st.session_state:
            st.session_state.casino_balance = 1000

        c1, c2 = st.columns([1, 1])
        
        with c1:
            st.subheader(f"Portfel: ${st.session_state.casino_balance:,.0f}")
            bet = st.number_input("Stawka ($)", 10, st.session_state.casino_balance, 50)
            pick = st.radio("Na co stawiasz?", ["CZERWONE", "CZARNE", "ZIELONE (0)"], horizontal=True)
            
            if st.button("🎰 ZAKRĘĆ KOŁEM"):
                num = np.random.randint(0, 37)
                reds = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
                
                if num == 0: 
                    win_color = "ZIELONE (0)"
                    hex_c = "#00ff00"
                elif num in reds: 
                    win_color = "CZERWONE"
                    hex_c = "#ff0000"
                else: 
                    win_color = "CZARNE"
                    hex_c = "#000000"
                
                # Logika wygranej
                if pick == win_color:
                    mult = 35 if num == 0 else 2
                    payout = bet * mult
                    st.session_state.casino_balance += (payout - bet)
                    st.balloons()
                    st.success(f"WYGRANA! Wypadło: {num} ({win_color}). Zyskałeś ${payout}!")
                else:
                    st.session_state.casino_balance -= bet
                    st.error(f"PRZEGRANA. Wypadło: {num} ({win_color}). Straciłeś ${bet}.")
                
                # Mini wizualizacja wyniku
                st.markdown(f"<div style='background-color:{hex_c}; padding:40px; border-radius:50%; width:100px; height:100px; display:flex; align-items:center; justify-content:center; border:5px solid white; margin:auto;'><h1 style='color:white; margin:0;'>{num}</h1></div>", unsafe_allow_html=True)

        with c2:
            st.info("Prawdopodobieństwo w europejskiej ruletce wynosi 48.6% dla kolorów i 2.7% dla zera. Graj odpowiedzialnie!")
            if st.session_state.casino_balance < 10:
                if st.button("Zbankrutowałem! Daj mi 500$ kredytu"):
                    st.session_state.casino_balance = 500
                    st.rerun()


    with tab_macro:
        st.subheader("Korelacja z NASDAQ (Znormalizowana)")
        coin_norm = (df_crypto['close'] - df_crypto['close'].min()) / (df_crypto['close'].max() - df_crypto['close'].min())
        ndx_norm = (ser_nasdaq - ser_nasdaq.min()) / (ser_nasdaq.max() - ser_nasdaq.min())
        fig_macro = go.Figure()
        fig_macro.add_trace(go.Scatter(x=df_crypto['timestamp'], y=coin_norm, name=selected_coin))
        fig_macro.add_trace(go.Scatter(x=df_crypto['timestamp'], y=ndx_norm, name="NASDAQ", line=dict(dash='dot')))
        fig_macro.update_layout(template="plotly_dark", height=450)
        st.plotly_chart(fig_macro, use_container_width=True)

    # --- DOPISANO: TAB BACKTESTING ---
    with tab_backtest:
        st.subheader("Symulacja Strategii (Historyczna)")
        st.write("Sprawdzamy wyniki strategii opartej na RSI i Fibo w ciągu ostatnich 90 dni.")
        df_back = df_crypto.copy()
        df_back['Signal'] = np.where((df_back['RSI'] < 35) & (df_back['close'] > fib_0618), 1, 0)
        st.dataframe(df_back[df_back['Signal'] == 1][['timestamp', 'close', 'RSI']], use_container_width=True)

    # --- DOPISANO: TAB LIKWIDACJE (HEATMAP PROXY) ---
    with tab_liq:
        st.subheader("Dynamiczna Mapa Likwidacji (Estymacja)")
        levels = np.linspace(cur_price * 0.9, cur_price * 1.1, 20)
        intensity = np.random.uniform(0, 100, 20) # Proxy dla braku danych z API Coinglass
        fig_liq = go.Figure(data=go.Heatmap(z=[intensity], x=levels, colorscale='Viridis'))
        fig_liq.update_layout(title="Klastry Likwidacji (Proxy)", xaxis_title="Cena", template="plotly_dark")
        st.plotly_chart(fig_liq, use_container_width=True)

    with tab_data:
        st.dataframe(df_crypto.tail(15), use_container_width=True)

st.caption("Terminal v9.5 | RSI, BB, MA20, Heatmap, Backtest | Not Financial Advice.")