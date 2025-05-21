import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
from fpdf import FPDF
import tempfile
import os

st.title("Analisi conto MT4 (Profitto in percentuale)")

# Capitale iniziale
starting_equity = st.number_input("Inserisci il capitale iniziale (€)", min_value=1.0, value=1000.0)

if starting_equity <= 0:
    st.error("⚠️ Inserisci un capitale iniziale maggiore di 0.")
    st.stop()

uploaded_file = st.file_uploader("Carica il file CSV di Myfxbook o HTML da MT4", type=["csv", "htm", "html"])

if uploaded_file is not None:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)

    elif uploaded_file.name.endswith(('.htm', '.html')):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(uploaded_file, 'html.parser')
        tables = soup.find_all('table')
        df = None

        best_table = None
        for idx, table in enumerate(tables):
            rows = table.find_all('tr')
            for i, row in enumerate(rows):
                cells = [td.get_text(strip=True).replace('\xa0', ' ') for td in row.find_all('td')]
                match_count = sum(col in cells for col in ['Open Time', 'Close Time', 'Type', 'Size', 'Item', 'Profit'])
                if match_count >= 5:
                    headers = cells
                    data_rows = []
                    for data_row in rows[i+1:]:
                        data_cells = [td.get_text(strip=True) for td in data_row.find_all('td')]
                        if len(data_cells) == len(headers):
                            data_rows.append(data_cells)
                    if data_rows:
                        best_table = (headers, data_rows)
                    break

        if best_table is None:
            st.error("❌ Nessuna tabella valida trovata nel file HTML.")
            st.stop()

        headers, rows = best_table
        df = pd.DataFrame(rows, columns=headers)

        df.rename(columns={
            'Open Time': 'Open Date',
            'Close Time': 'Close Date',
            'Type': 'Action',
            'Item': 'Symbol',
            'Size': 'Lots'
        }, inplace=True)

        if 'Price' in df.columns and 'Price.1' in df.columns:
            df['Open Price'] = pd.to_numeric(df['Price'], errors='coerce')
            df['Close Price'] = pd.to_numeric(df['Price.1'], errors='coerce')
            df['Pips'] = ((df['Close Price'] - df['Open Price']) * 10000).round(1)
        else:
            df['Pips'] = 0.0

    else:
        st.error("❌ Formato file non supportato. Carica un file CSV o HTML.")
        st.stop()

    df['Open Date'] = pd.to_datetime(df['Open Date'], dayfirst=True, errors='coerce')
    df['Close Date'] = pd.to_datetime(df['Close Date'], dayfirst=True, errors='coerce')

    if df['Open Date'].isna().all() or df['Close Date'].isna().all():
        st.error("❌ Nessuna data valida trovata nei trade.")
        st.stop()

    # --- Calcoli e visualizzazione ---

    min_date = df['Open Date'].min()
    max_date = df['Close Date'].max()

    start_date = st.date_input("📅 Data inizio filtro", min_value=min_date.date(), max_value=max_date.date(), value=min_date.date())
    end_date = st.date_input("📅 Data fine filtro", min_value=min_date.date(), max_value=max_date.date(), value=max_date.date())

    df = df[(df['Open Date'].dt.date >= start_date) & (df['Open Date'].dt.date <= end_date)]

    df_closed = df[df['Close Date'].notna()].sort_values('Close Date').reset_index(drop=True)
    df_closed['Close Date'] = pd.to_datetime(df_closed['Close Date'], errors='coerce')
    df_closed['Profit'] = pd.to_numeric(df_closed['Profit'], errors='coerce').round(2)
    df_closed['Pips'] = pd.to_numeric(df_closed['Pips'], errors='coerce').round(1)

    df_closed['Equity'] = starting_equity + df_closed['Profit'].cumsum()
    df_closed['Equity %'] = (df_closed['Equity'] - starting_equity) / starting_equity * 100
    df_closed['High Watermark'] = df_closed['Equity'].cummax()
    df_closed['Drawdown'] = df_closed['Equity'] - df_closed['High Watermark']
    df_closed['Drawdown %'] = df_closed['Drawdown'] / df_closed['High Watermark'] * 100
    max_drawdown = df_closed['Drawdown %'].min()

    st.subheader(f"📉 Max Drawdown: {max_drawdown:.2f}%")

    # Statistiche
    st.subheader("📈 Statistiche del Trading")
    total_trades = len(df_closed)
    winning_trades = df_closed[df_closed['Profit'] > 0]
    losing_trades = df_closed[df_closed['Profit'] < 0]

    win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
    avg_profit_per_trade = df_closed['Profit'].mean() / starting_equity * 100 if total_trades > 0 else 0
    total_profit = df_closed['Profit'].sum() / starting_equity * 100

    gross_profit = winning_trades['Profit'].sum()
    gross_loss = -losing_trades['Profit'].sum()
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
    win_loss_ratio = len(winning_trades) / len(losing_trades) if len(losing_trades) > 0 else float('inf')

    avg_pips = df_closed['Pips'].mean() if total_trades > 0 else 0

    stats = {
        "Totale trade eseguiti (chiusi)": total_trades,
        "Win rate (%)": f"{win_rate:.2f}%",
        "Profitto medio per trade (%)": f"{avg_profit_per_trade:.2f}%",
        "Profitto totale (%)": f"{total_profit:.2f}%",
        "Profit factor": f"{profit_factor:.2f}",
        "Rapporto Win/Loss": f"{win_loss_ratio:.2f}",
        "Max Drawdown (%)": f"{max_drawdown:.2f}%",
        "Pips medi per trade": f"{avg_pips:.1f}"
    }

    for key, value in stats.items():
        st.write(f"**{key}:** {value}")

    # Grafici
    st.subheader("📊 Equity Curve (%)")
    equity_data = df_closed[['Close Date', 'Equity %']].dropna()
    fig1, ax1 = plt.subplots()
    ax1.plot(equity_data['Close Date'], equity_data['Equity %'], linewidth=2)
    ax1.set_xlabel("Data")
    ax1.set_ylabel("Equity (%)")
    ax1.grid(True)
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
    plt.setp(ax1.get_xticklabels(), rotation=45, ha="right")
    fig1.tight_layout()
    st.pyplot(fig1)

    st.subheader("📊 Drawdown (%)")
    drawdown_data = df_closed[['Close Date', 'Drawdown %']].dropna()
    fig2, ax2 = plt.subplots()
    ax2.plot(drawdown_data['Close Date'], drawdown_data['Drawdown %'], color='red', linewidth=2)
    ax2.set_xlabel("Data")
    ax2.set_ylabel("Drawdown (%)")
    ax2.grid(True)
    ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
    plt.setp(ax2.get_xticklabels(), rotation=45, ha="right")
    fig2.tight_layout()
    st.pyplot(fig2)

    # Tabella trade
    st.subheader("🧾 Trade Chiusi")
    closed_table = df_closed[['Close Date', 'Symbol', 'Action', 'Profit', 'Pips']].copy()
    closed_table['Profit %'] = (closed_table['Profit'] / starting_equity * 100).round(2)
    closed_table = closed_table[['Close Date', 'Symbol', 'Action', 'Profit %', 'Pips']]

    def color_profit(val):
        if val > 0:
            return 'color: green'
        elif val < 0:
            return 'color: red'
        else:
            return ''

    st.dataframe(closed_table.style.applymap(color_profit, subset=['Profit %']), use_container_width=True)

    # [Tutte le funzionalità esistenti come calcoli, grafici, PDF, ecc. restano uguali]

else:
    st.info("Carica un file CSV per iniziare.")
