import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

st.title("Analisi conto MT4 (Profitto in percentuale)")

# Inserimento capitale iniziale
starting_equity = st.number_input("Inserisci il capitale iniziale (€)", min_value=1.0, value=1000.0)

if starting_equity <= 0:
    st.error("⚠️ Inserisci un capitale iniziale maggiore di 0.")
    st.stop()

# Upload del file CSV
uploaded_file = st.file_uploader("Carica il file CSV esportato da Myfxbook", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # Parsing delle date
    df['Open Date'] = pd.to_datetime(df['Open Date'], dayfirst=True, errors='coerce')
    df['Close Date'] = pd.to_datetime(df['Close Date'], dayfirst=True, errors='coerce')

    # Separazione trade chiusi e aperti
    df_closed = df[df['Close Date'].notna()].sort_values('Close Date').reset_index(drop=True)
    df_open = df[df['Close Date'].isna()]

    # Calcoli equity su TUTTI i trade (chiusi + aperti)
    df_all = pd.concat([df_closed, df_open])
    df_all = df_all.sort_values(by='Close Date', na_position='last').reset_index(drop=True)
    df_all['Profit'] = pd.to_numeric(df_all['Profit'], errors='coerce')
    df_all['Equity'] = starting_equity + df_all['Profit'].cumsum()
    df_all['Equity %'] = (df_all['Equity'] - starting_equity) / starting_equity * 100
    df_all['High Watermark'] = df_all['Equity'].cummax()
    df_all['Drawdown'] = df_all['Equity'] - df_all['High Watermark']
    df_all['Drawdown %'] = df_all['Drawdown'] / df_all['High Watermark'] * 100
    max_drawdown = df_all['Drawdown %'].min()

    st.subheader(f"📉 Max Drawdown: {max_drawdown:.2f}%")

    # Statistiche sui trade CHIUSI
    st.subheader("📈 Statistiche del Trading")

    total_trades = len(df_closed)
    winning_trades = df_closed[df_closed['Profit'] > 0]
    losing_trades = df_closed[df_closed['Profit'] < 0]

    win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
    avg_profit_per_trade = (df_closed['Profit'].sum() / total_trades) / starting_equity * 100 if total_trades > 0 else 0
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

    # Interpolazione giornaliera (solo con date disponibili)
    daily_data = df_all[df_all['Close Date'].notna()][['Close Date', 'Equity %', 'Drawdown %']].copy()
    daily_data = (
        daily_data.groupby('Close Date').last()
        .resample('D')
        .ffill()
        .reset_index()
    )

    # Grafico Equity %
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

    # Grafico Drawdown %
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

    # Tabella solo trade chiusi con colori
    st.subheader("🧾 Trade Eseguiti (in %)")

    simplified_table = df_closed[['Close Date', 'Symbol', 'Action', 'Profit']].copy()
    simplified_table['Profit %'] = (simplified_table['Profit'] / starting_equity * 100).round(2)
    simplified_table = simplified_table[['Close Date', 'Symbol', 'Action', 'Profit %']]

    def color_profit(val):
        color = 'green' if val > 0 else 'red' if val < 0 else 'black'
        return f'color: {color}'

    styled_table = simplified_table.style.applymap(color_profit, subset=['Profit %'])
    st.dataframe(styled_table)

else:
    st.info("Carica un file CSV per iniziare.")
