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
        for table in tables:
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            if {'Open Time', 'Close Time', 'Type', 'Size', 'Item', 'Profit'}.issubset(set(headers)):
                rows = []
                for row in table.find_all('tr')[1:]:
                    cells = [td.get_text(strip=True) for td in row.find_all('td')]
                    if cells:
                        rows.append(cells)
                df = pd.DataFrame(rows, columns=headers)
                from pandas.io.parsers import ParserBase
                df.columns = ParserBase({'names': df.columns})._maybe_dedup_names(df.columns)
                df.rename(columns={
                'Open Time': 'Open Date',
                'Close Time': 'Close Date',
                'Type': 'Action',
                'Item': 'Symbol',
                'Size': 'Lots'
            }, inplace=True)
            if df is not None:
                if 'Price' in df.columns and 'Price.1' in df.columns:
                    df['Open Price'] = pd.to_numeric(df['Price'], errors='coerce')
                    df['Close Price'] = pd.to_numeric(df['Price.1'], errors='coerce')
                    df['Pips'] = ((df['Close Price'] - df['Open Price']) * 10000).round(1)
                else:
                    df['Pips'] = 0.0
                break

        if df is None:
            st.error("Non è stato possibile trovare la tabella dei trade chiusi nel file HTML.")
            st.stop()
        df.rename(columns={
            'Open Time': 'Open Date',
            'Close Time': 'Close Date',
            'Type': 'Action'
        }, inplace=True)
    else:
        st.error("Formato file non supportato. Carica un file CSV o HTML.")
        st.stop()

    # Parsing date
    df['Open Date'] = pd.to_datetime(df['Open Date'], dayfirst=True, errors='coerce')
    df['Close Date'] = pd.to_datetime(df['Close Date'], dayfirst=True, errors='coerce')

    # Solo trade chiusi
    df['Open Date'] = pd.to_datetime(df['Open Date'], dayfirst=True, errors='coerce')
    df['Close Date'] = pd.to_datetime(df['Close Date'], dayfirst=True, errors='coerce')

    min_date = df['Open Date'].min()
    max_date = df['Close Date'].max()

    start_date = st.date_input("📅 Data inizio filtro", min_value=min_date.date(), max_value=max_date.date(), value=min_date.date())
    
    end_date = st.date_input("📅 Data fine filtro", min_value=min_date.date(), max_value=max_date.date(), value=max_date.date())
    

    df = df[(df['Open Date'].dt.date >= start_date) & (df['Open Date'].dt.date <= end_date)]

    df_closed = df[df['Close Date'].notna()].sort_values('Close Date').reset_index(drop=True)
    df_closed['Close Date'] = df_closed['Close Date'].dt.strftime('%d/%m/%Y')
    df_closed['Profit'] = pd.to_numeric(df_closed['Profit'], errors='coerce').round(2)
    df_closed['Pips'] = pd.to_numeric(df_closed['Pips'], errors='coerce').round(1)

    # Equity e Drawdown
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

    # Interpolazione Equity/Drawdown giornaliero
    daily_data = df_closed[['Close Date', 'Equity %', 'Drawdown %']].copy()
    daily_data['Close Date'] = pd.to_datetime(daily_data['Close Date'], dayfirst=True, errors='coerce')
    daily_data = (
        daily_data.groupby('Close Date').last()
        .resample('D')
        .ffill()
        .reset_index()
    )

    # Grafico Equity
    st.subheader("📊 Equity Curve (%)")
    fig1, ax1 = plt.subplots()
    ax1.plot(daily_data['Close Date'], daily_data['Equity %'], linewidth=2)
    ax1.set_xlabel("Data")
    ax1.set_ylabel("Equity (%)")
    ax1.grid(True)
    ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
    plt.setp(ax1.get_xticklabels(), rotation=45, ha="right")
    fig1.tight_layout()
    st.pyplot(fig1)

    temp_eq_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig1.savefig(temp_eq_path.name)

    # Grafico Drawdown
    st.subheader("📊 Drawdown (%)")
    fig2, ax2 = plt.subplots()
    ax2.plot(daily_data['Close Date'], daily_data['Drawdown %'], color='red', linewidth=2)
    ax2.set_xlabel("Data")
    ax2.set_ylabel("Drawdown (%)")
    ax2.grid(True)
    ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
    plt.setp(ax2.get_xticklabels(), rotation=45, ha="right")
    fig2.tight_layout()
    st.pyplot(fig2)

    temp_dd_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    fig2.savefig(temp_dd_path.name)

    # Tabella con Profit % e Pips
    st.markdown("### 🧾 Trade Chiusi (in % e Pips)")
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

    styled_closed = closed_table.style.applymap(color_profit, subset=['Profit %'])
    st.dataframe(styled_closed, use_container_width=True)

    # PDF con statistica + Pips
    def generate_pdf(stats, table, equity_img, drawdown_img):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, "Report MT4 - Trade Chiusi", ln=True, align='C')
        pdf.ln(8)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, "Statistiche", ln=True)
        pdf.set_font("Arial", size=10)

        col1_width = 90
        col2_width = 90

        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(col1_width, 8, "Parametro", border=1, fill=True)
        pdf.cell(col2_width, 8, "Valore", border=1, ln=True, fill=True)
        pdf.set_font("Arial", size=10)

        for key, value in stats.items():
            pdf.cell(col1_width, 8, key, border=1)
            pdf.cell(col2_width, 8, str(value), border=1, ln=True)

        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, "Equity Curve", ln=True)
        pdf.image(equity_img, w=180)
        pdf.ln(5)

        pdf.cell(200, 10, "Drawdown", ln=True)
        pdf.image(drawdown_img, w=180)
        pdf.ln(5)

        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, "Trade Chiusi", ln=True)
        pdf.set_font("Arial", 'B', 10)
        col_widths = [35, 35, 25, 35, 30]
        headers = ['Data Chiusura', 'Simbolo', 'Azione', 'Profitto %', 'Pips']
        for i, header in enumerate(headers):
            pdf.set_fill_color(220, 220, 220)
            pdf.cell(col_widths[i], 8, header, border=1, align='C', fill=True)
        pdf.ln()

        pdf.set_font("Arial", size=10)
        for _, row in table.iterrows():
            profit_percent = row['Profit %']
            pips = row['Pips']
            if profit_percent > 0:
                pdf.set_text_color(0, 128, 0)
            elif profit_percent < 0:
                pdf.set_text_color(255, 0, 0)
            else:
                pdf.set_text_color(0, 0, 0)

            pdf.cell(col_widths[0], 8, row['Close Date'], border=1)
            pdf.cell(col_widths[1], 8, str(row['Symbol']), border=1)
            pdf.cell(col_widths[2], 8, str(row['Action']), border=1)
            pdf.cell(col_widths[3], 8, f"{profit_percent:.2f}%", border=1, align='R')
            pdf.cell(col_widths[4], 8, f"{pips:.1f}", border=1, align='R')
            pdf.ln()

        pdf.set_text_color(0, 0, 0)
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        return BytesIO(pdf_bytes)

    st.subheader("📄 Esporta PDF")
    pdf_buffer = generate_pdf(stats, closed_table, temp_eq_path.name, temp_dd_path.name)
    st.download_button(
        label="📥 Scarica PDF con grafici",
        data=pdf_buffer,
        file_name="report_mt4_completo.pdf",
        mime="application/pdf"
    )

    os.remove(temp_eq_path.name)
    os.remove(temp_dd_path.name)

else:
    st.info("Carica un file CSV per iniziare.")
