import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
from fpdf import FPDF

st.title("Analisi conto MT4 (Profitto in percentuale)")

# Inserimento capitale iniziale
starting_equity = st.number_input("Inserisci il capitale iniziale (€)", min_value=1.0, value=1000.0)

if starting_equity <= 0:
    st.error("⚠️ Inserisci un capitale iniziale maggiore di 0.")
    st.stop()

# Caricamento CSV
uploaded_file = st.file_uploader("Carica il file CSV esportato da Myfxbook", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # Parsing date
    df['Open Date'] = pd.to_datetime(df['Open Date'], dayfirst=True, errors='coerce')
    df['Close Date'] = pd.to_datetime(df['Close Date'], dayfirst=True, errors='coerce')

    # Separazione trade chiusi
    df_closed = df[df['Close Date'].notna()].sort_values('Close Date').reset_index(drop=True)

    # Calcoli equity/drawdown
    df_all = df_closed.copy()
    df_all['Profit'] = pd.to_numeric(df_all['Profit'], errors='coerce')
    df_all['Equity'] = starting_equity + df_all['Profit'].cumsum()
    df_all['Equity %'] = (df_all['Equity'] - starting_equity) / starting_equity * 100
    df_all['High Watermark'] = df_all['Equity'].cummax()
    df_all['Drawdown'] = df_all['Equity'] - df_all['High Watermark']
    df_all['Drawdown %'] = df_all['Drawdown'] / df_all['High Watermark'] * 100
    max_drawdown = df_all['Drawdown %'].min()

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

    stats = {
        "Totale trade eseguiti (chiusi)": total_trades,
        "Win rate (%)": f"{win_rate:.2f}%",
        "Profitto medio per trade (%)": f"{avg_profit_per_trade:.2f}%",
        "Profitto totale (%)": f"{total_profit:.2f}%",
        "Profit factor": f"{profit_factor:.2f}",
        "Rapporto Win/Loss": f"{win_loss_ratio:.2f}"
    }

    for key, value in stats.items():
        st.write(f"**{key}:** {value}")

    # Interpolazione equity
    daily_data = df_all[['Close Date', 'Equity %', 'Drawdown %']].copy()
    daily_data = (
        daily_data.groupby('Close Date').last()
        .resample('D')
        .ffill()
        .reset_index()
    )

    # Grafico equity
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

    # Grafico drawdown
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

    # Tabella trade chiusi
    st.subheader("🧾 Trade Chiusi (in %)")
    closed_table = df_closed[['Close Date', 'Symbol', 'Action', 'Profit']].copy()
    closed_table['Profit %'] = (closed_table['Profit'] / starting_equity * 100).round(2)
    closed_table = closed_table[['Close Date', 'Symbol', 'Action', 'Profit %']]

    def color_profit(val):
        if val > 0:
            return 'color: green'
        elif val < 0:
            return 'color: red'
        else:
            return ''  # nessun colore per 0

    styled_closed = closed_table.style.applymap(color_profit, subset=['Profit %'])
    st.dataframe(styled_closed)

    # Esportazione PDF
    st.subheader("📄 Esporta PDF")

    def generate_pdf(stats, table):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Report MT4 - Trade Chiusi", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Statistiche", ln=True)
    pdf.set_font("Arial", size=10)
    for key, value in stats.items():
        pdf.cell(200, 8, f"{key}: {value}", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Trade Chiusi", ln=True)
    pdf.set_font("Arial", size=9)
    for index, row in table.iterrows():
        pdf.cell(200, 6, f"{row['Close Date'].date()} | {row['Symbol']} | {row['Action']} | {row['Profit %']}%", ln=True)

    # ✅ Output PDF come bytes
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return BytesIO(pdf_bytes)


    pdf_buffer = generate_pdf(stats, closed_table)
    st.download_button(
        label="📥 Scarica PDF",
        data=pdf_buffer,
        file_name="report_mt4.pdf",
        mime="application/pdf"
    )

else:
    st.info("Carica un file CSV per iniziare.")
