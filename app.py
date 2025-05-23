import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
from fpdf import FPDF
import tempfile
import os
from bs4 import BeautifulSoup

st.title("Analisi conto MT4 / Myfxbook")

starting_equity = st.number_input("Inserisci il capitale iniziale (€)", min_value=1.0, value=1000.0)

if starting_equity <= 0:
    st.error("⚠️ Inserisci un capitale iniziale maggiore di 0.")
    st.stop()

uploaded_file = st.file_uploader("Carica il file CSV (Myfxbook) o HTML (MT4)", type=["csv", "htm", "html"])

df = None

if uploaded_file is not None:
    filename = uploaded_file.name.lower()

    if filename.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        df['Open Date'] = pd.to_datetime(df['Open Date'], dayfirst=True, errors='coerce')
        df['Close Date'] = pd.to_datetime(df['Close Date'], dayfirst=True, errors='coerce')

        df_closed = df[df['Close Date'].notna()].sort_values('Close Date').reset_index(drop=True)
        df_closed['Profit'] = pd.to_numeric(df_closed['Profit'], errors='coerce').round(2)
        df_closed['Pips'] = pd.to_numeric(df_closed['Pips'], errors='coerce').round(1)

        df_closed['Symbol'] = df_closed['Symbol'] if 'Symbol' in df_closed else 'N/A'
        df_closed['Action'] = df_closed['Action'] if 'Action' in df_closed else 'N/A'

    elif filename.endswith(".htm") or filename.endswith(".html"):
        soup = BeautifulSoup(uploaded_file, "html.parser")
        if not soup.find(string=lambda text: text and "Closed Transactions:" in text):
            st.error("Errore: Il file HTML non sembra essere un'esportazione valida da MetaTrader 4.")
            st.stop()

        headers = [
            "Ticket", "Open Time", "Type", "Size", "Item", "Open Price", "S/L", "T/P",
            "Close Time", "Close Price", "Commission", "Taxes", "Swap", "Profit"
        ]

        rows = soup.find_all("tr")
        found_table = False
        data_rows = []

        for row in rows:
            cols = row.find_all("td")
            texts = [col.get_text(strip=True).replace('\xa0', ' ') for col in cols]

            if "Closed Transactions:" in "".join(texts):
                found_table = True
                continue

            if found_table:
                if len(texts) == 14 and texts[0] != "Ticket":
                    data_rows.append(texts)
                elif "Open Trades:" in "".join(texts):
                    break

        if not data_rows:
            st.error("Errore: Nessuna riga valida trovata nella tabella Closed Transactions.")
            st.stop()

        df_closed = pd.DataFrame(data_rows, columns=headers)
        df_closed['Profit'] = pd.to_numeric(df_closed['Profit'].str.replace(' ', '').str.replace(',', ''), errors='coerce')
        df_closed['Pips'] = None
        df_closed['Symbol'] = df_closed['Item']
        df_closed['Action'] = df_closed['Type']
        df_closed['Close Date'] = pd.to_datetime(df_closed['Close Time'], errors='coerce')

    else:
        st.error("Formato file non supportato.")
        st.stop()

    df_closed['Equity'] = starting_equity + df_closed['Profit'].cumsum()
    df_closed['Equity %'] = (df_closed['Equity'] - starting_equity) / starting_equity * 100
    df_closed['High Watermark'] = df_closed['Equity'].cummax()
    df_closed['Drawdown'] = df_closed['Equity'] - df_closed['High Watermark']
    df_closed['Drawdown %'] = df_closed['Drawdown'] / df_closed['High Watermark'] * 100
    max_drawdown = df_closed['Drawdown %'].min()

    st.subheader(f"📉 Max Drawdown: {max_drawdown:.2f}%")

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

    avg_pips = df_closed['Pips'].mean() if 'Pips' in df_closed and df_closed['Pips'].notna().any() else 0

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

    daily_data = df_closed[['Close Date', 'Equity %', 'Drawdown %']].copy()
    daily_data = (
        daily_data.groupby('Close Date').last()
        .resample('D')
        .ffill()
        .reset_index()
    )

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

    st.markdown("### 🧾 Trade Chiusi (in % e Pips)")
    closed_table = df_closed[['Close Date', 'Symbol', 'Action', 'Profit', 'Pips']].copy()
    closed_table['Close Date'] = closed_table['Close Date'].dt.strftime('%d-%m-%Y')
    closed_table['Profit %'] = (closed_table['Profit'] / starting_equity * 100).map(lambda x: f"{x:.2f}")
    closed_table['Pips'] = closed_table['Pips'].map(lambda x: f"{x:.1f}".rstrip('0').rstrip('.') if pd.notnull(x) else '')
    closed_table = closed_table[['Close Date', 'Symbol', 'Action', 'Profit %', 'Pips']]

    def color_profit(val):
        try:
            val = float(val.replace('%', ''))
            if val > 0:
                return 'color: green'
            elif val < 0:
                return 'color: red'
        except:
            pass
        return ''

    styled_closed = closed_table.style.applymap(color_profit, subset=['Profit %'])
    st.dataframe(styled_closed, use_container_width=True)

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
            try:
                profit_percent = float(row['Profit %'].replace('%', ''))
            except:
                profit_percent = 0
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
            pdf.cell(col_widths[3], 8, f"{row['Profit %']}%", border=1, align='R')
            pdf.cell(col_widths[4], 8, str(pips), border=1, align='R')
            pdf.ln()

        pdf.set_text_color(0, 0, 0)
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        return BytesIO(pdf_bytes)

    st.subheader("📄 Esporta PDF")
    pdf_buffer = generate_pdf(stats, closed_table, temp_eq_path.name, temp_dd_path.name)
    st.download_button(
        label="📅 Scarica PDF con grafici",
        data=pdf_buffer,
        file_name="report_mt4_completo.pdf",
        mime="application/pdf"
    )

    os.remove(temp_eq_path.name)
    os.remove(temp_dd_path.name)

else:
    st.info("Carica un file CSV o HTML per iniziare.")
