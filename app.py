import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import hashlib

# --- HỆ THỐNG BẢN QUYỀN ---
SECRET_SALT = "TabayRobot_Secret_2024!@" 

def verify_license(user_key):
    user_key = str(user_key).replace(" ", "").strip()
    if user_key == "TABAY-ADMIN-PRO":
        return True, "Master Key Activated!"
    try:
        exp_date_str, key_hash = user_key.split('-')
        if key_hash.upper() != hashlib.md5(f"{exp_date_str}{SECRET_SALT}".encode()).hexdigest()[:10].upper():
            return False, "Invalid key."
        if datetime.now() > datetime.strptime(exp_date_str, "%Y%m%d"):
            return False, "License expired."
        return True, "Valid license."
    except:
        return False, "Format error."

st.set_page_config(page_title="Tabay Robot Pro", layout="wide", initial_sidebar_state="collapsed")

if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.markdown("<h1 style='text-align: center;'>🔒 Tabay Robot License</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Kích hoạt Master Key (Admin)", use_container_width=True):
            st.session_state.authenticated = True
            st.rerun()
    st.stop() 

# --- GIAO DIỆN & CÀI ĐẶT ---
st.sidebar.markdown("## ⚙️ Cài đặt Phân tích")
symbol = st.sidebar.text_input("Mã giao dịch (VD: DIG.VN, BTC-USD, AAPL):", "BTC-USD")
period = st.sidebar.selectbox("Dữ liệu:", ["3mo", "6mo", "1y", "2y", "5y", "max"], index=1)
interval = st.sidebar.selectbox("Khung:", ["1d", "1wk", "1h", "15m", "5m"], index=0)
sensitivity = st.sidebar.slider("Độ nhạy Robot (WMA):", 2, 100, 13)

st.markdown(f"<h3 style='margin-bottom: 0px; color: #d1d4dc;'>Phân tích: {symbol} | Khung: {interval}</h3>", unsafe_allow_html=True)

if symbol:
    with st.spinner("Đang xử lý thuật toán Tabay Robot..."):
        try:
            df = yf.download(symbol, period=period, interval=interval)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
                
                # --- TOÁN HỌC TABAY ROBOT ---
                # 1. MACD & VWMA
                macd = ta.macd(df['Close'], fast=4, slow=8, signal=5)
                df['MACD'] = macd['MACD_4_8_5']
                df['Signal'] = macd['MACDs_4_8_5']
                df['VWMA_5'] = ta.vwma(df['Close'], df['Volume'], length=5)

                # 2. Tín hiệu Robot
                df['x11'] = (df['High'] + df['Low'] + df['Close']) / 3
                df['x21'] = (df['High'] + df['Low']) / 2
                df['fastSMA'] = df['x11']
                df['slowSMA'] = ta.wma(df['x21'], length=sensitivity)
                df['Buy'] = (df['fastSMA'] > df['slowSMA']) & (df['fastSMA'].shift(1) <= df['slowSMA'].shift(1))
                df['Sell'] = (df['fastSMA'] < df['slowSMA']) & (df['fastSMA'].shift(1) >= df['slowSMA'].shift(1))

                # Xác định xu hướng hiện tại cho bảng màu nền
                df['Trend'] = np.where(df['fastSMA'] > df['slowSMA'], 1, -1)

                # --- VẼ BIỂU ĐỒ ---
                fig = go.Figure()
                
                # Nến chính
                fig.add_trace(go.Candlestick(
                    x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                    increasing_line_color='#089981', increasing_fillcolor='#089981', 
                    decreasing_line_color='#f23645', decreasing_fillcolor='#f23645', name="Nến"
                ))
                    
                # VWMA (Line màu vàng của JCR)
                fig.add_trace(go.Scatter(x=df.index, y=df['VWMA_5'], line=dict(color='yellow', width=1.5), name='VWMA 5'))

                # Nhãn giá Mua / Bán (Label yloc.belowbar / abovebar)
                buys = df[df['Buy']]
                sells = df[df['Sell']]
                
                fig.add_trace(go.Scatter(
                    x=buys.index, y=buys['Low'] * 0.98, mode='markers+text',
                    marker=dict(symbol='triangle-up', size=12, color='#089981'),
                    text=buys['Low'].round(2), textposition="bottom center", textfont=dict(color='#089981'), name='Buy'
                ))
                fig.add_trace(go.Scatter(
                    x=sells.index, y=sells['High'] * 1.02, mode='markers+text',
                    marker=dict(symbol='triangle-down', size=12, color='#f23645'),
                    text=sells['High'].round(2), textposition="top center", textfont=dict(color='#f23645'), name='Sell'
                ))

                # --- TABAY X LINE (KÊNH HỒI QUY) & NHÃN GIÁ GÓC PHẢI ---
                length, dev1, dev2 = 50, 2.0, 1.5
                if len(df) >= length:
                    df_lr = df.tail(length)
                    x_lr = np.arange(length)
                    y_lr = df_lr['Close'].values
                    slope, intercept = np.polyfit(x_lr, y_lr, 1)
                    y_pred = slope * x_lr + intercept
                    std_dev = np.sqrt(np.sum((y_lr - y_pred)**2) / length)
                    
                    color_lr = '#089981' if slope > 0 else '#f23645'
                    last_x = df_lr.index[-1]
                    
                    # Cấu hình các đường và nhãn
                    lines = [
                        (y_pred, color_lr, 2, 'solid', "Trung tâm"),
                        (y_pred + std_dev * dev1, '#2962FF', 1.5, 'dash', "Dev 1 Lên"),
                        (y_pred - std_dev * dev1, '#2962FF', 1.5, 'dash', "Dev 1 Xuống"),
                        (y_pred + std_dev * dev2, '#FF6D00', 1.5, 'dot', "Dev 2 Lên"),
                        (y_pred - std_dev * dev2, '#FF6D00', 1.5, 'dot', "Dev 2 Xuống")
                    ]
                    
                    for y_vals, col, wid, dsh, name in lines:
                        fig.add_trace(go.Scatter(x=df_lr.index, y=y_vals, mode='lines', line=dict(color=col, width=wid, dash=dsh), showlegend=False))
                        # Gắn nhãn giá ở cuối đường (giống TradingView)
                        fig.add_annotation(x=last_x, y=y_vals[-1], text=f"{y_vals[-1]:.2f}", showarrow=False, 
                                           xanchor='left', bgcolor=col, font=dict(color='white', size=10), borderpad=2)

                # Cấu hình UI TradingView Dark Mode
                fig.update_layout(
                    plot_bgcolor='#131722', paper_bgcolor='#131722', font=dict(color='#787b86'),
                    margin=dict(l=0, r=50, b=0, t=10), height=600,
                    xaxis=dict(showgrid=True, gridcolor='#363a45', showline=False, rangeslider=dict(visible=False)),
                    yaxis=dict(side='right', showgrid=True, gridcolor='#363a45', showline=False),
                    hovermode="x unified", showlegend=False
                )
                
                # Highlight màu nền xanh đỏ mờ
                trend_changes = df[df['Trend'].diff() != 0].index.tolist()
                trend_changes.append(df.index[-1])
                for i in range(len(trend_changes) - 1):
                    start_idx, end_idx = trend_changes[i], trend_changes[i+1]
                    is_buy = df.loc[start_idx, 'Trend'] == 1
                    fig.add_vrect(x0=start_idx, x1=end_idx, fillcolor="green" if is_buy else "red", opacity=0.05, layer="below")

                st.plotly_chart(fig, use_container_width=True)

                # --- BẢNG THÔNG TIN TABAYSYSTEM GÓC TRÁI DƯỚI ---
                last_buy = df[df['Buy']]['Low'].iloc[-1] if not df[df['Buy']].empty else 0
                last_sell = df[df['Sell']]['High'].iloc[-1] if not df[df['Sell']].empty else 0
                current_trend = df['Trend'].iloc[-1]
                
                # Tính toán Cutloss
                if current_trend == 1:
                    bg_color, status_text = "#089981", "ĐANG MUA (LONG)"
                    cutloss = last_buy * 0.99975
                    warn1 = f"Buy Around: {last_buy:.2f}<br>Cut Loss: {cutloss:.2f}"
                    warn = "Be careful to Long/Buy:<br>=> When Downtrend<br>or Candles are Red, Violet"
                else:
                    bg_color, status_text = "#f23645", "ĐANG BÁN (SHORT)"
                    cutloss = last_sell * 1.00025
                    warn1 = f"Sell below: {last_sell:.2f}<br>Cut Loss: {cutloss:.2f}"
                    warn = "Be careful to Short/Sell:<br>=> When Uptrend<br>or Candles are Yellow, Green"

                st.markdown(f"""
                <div style="background-color: {bg_color}; color: white; padding: 15px; border-radius: 5px; width: 350px;">
                    <h3 style="margin:0; text-align:center; color: white;">TabaySystem.com</h3>
                    <hr style="margin: 5px 0;">
                    <p style="margin:0; font-weight:bold; text-align:center;">{status_text}</p>
                    <p style="margin:5px 0; text-align:center;">{warn1}</p>
                    <hr style="margin: 5px 0;">
                    <p style="margin:0; font-size:12px; text-align:center;">{warn}</p>
                </div>
                """, unsafe_allow_html=True)
                
            else: st.warning("Không có dữ liệu.")
        except Exception as e: st.error(f"Lỗi: {e}")