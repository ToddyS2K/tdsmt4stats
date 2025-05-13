import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

st.title("Analisi conto MT4 (Profitto in percentuale)")

# Inserimento capitale iniziale
starting_equity = st.number_input("Inserisci il capitale iniziale (€)", min_value=1.0, value=1000.0)

# Upload del file CSV
uploaded_file = st.file_uploader("Carica il file CSV esportato da Myfxbook", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # Parsing date
    df['Open Date'] = pd.to_datetime(df['Open Date'], dayfirst=True, errors='coerce')
    df['Close Date'] = pd.to_datetime(df['Close Date'], dayfirst=True, errors='coerce')
    df = df.sort_values('Close Date').reset_index(drop=True)

    # Calcoli principali
    df['Profit'] = pd.to_numeric(df['Profit'], errors='coerce')
    df['Profit %'] = df['Profit'] / starting_equity * 100
    df['Equity %'] = df['Profit %'].cumsum()

    # Calcolo Drawdown %
    df['High Watermark'] = df['Equity %'].cummax()
    df['Drawdown %'] = df['Equity %'] - df['High Watermark']
    max_drawdown = df['Drawdown %'].min()

    st.subheader(f"📉 Max Drawdown: {max_drawdown:.2f}%")

    # === STATISTICHE EXTRA ===
    st.subheader("📈 Statistiche del Trading")

    total_trades = len(df)
    winning_trades = df[df['Profit'] > 0]
    losing_trades = df[df['Profit'] < 0]

    win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
    avg_profit_per_trade = df['Profit %'].mean()
    total_profit = df['Profit %'].sum()

    gross_profit = winning_trades['Profit'].sum()
    gross_loss = -losing_trades['Profit'].sum()  # negativo → positivo
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')
    win_loss_ratio = len(winning_trades) / len(losing_trades) if len(losing_trades) > 0 else float('inf')

    stats = {
        "Totale trade eseguiti": total_trades,
        "Win rate (%)": f"{win_rate:.2f}%",
        "Profitto medio per trade (%)": f"{avg_profit_per_trade:.2f}%",
        "Profitto totale (%)": f"{total_profit:.2f}%",
        "Profit factor": f"{profit_factor:.2f}",
        "Rapporto Win/Loss": f"{win_loss_ratio:.2f}"
    }

    for key, value in stats.items():
        st.write(f"**{key}:** {value}")

    # === Interpolazione Equity e Drawdown giornalieri ===
    daily_data = df[['Close Date', 'Equity %', 'Drawdown %']].copy()
    daily_data = daily_data.set_index('Close Date').resample('D').ffill().reset_index()

    # === Grafico Equity % ===
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

    # === Grafico Drawdown % ===
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

    # Tabella dei trade semplificata
    st.subheader("🧾 Trade Eseguiti (in %)")
    simplified_table = df[['Close Date', 'Symbol', 'Action', 'Profit %']].copy()
    simplified_table['Profit %'] = simplified_table['Profit %'].map("{:.2f}%".format)
    st.dataframe(simplified_table)

else:
    st.info("Carica un file CSV per iniziare.")
