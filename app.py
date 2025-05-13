import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("Analisi conto MT4 (Profitto in percentuale)")

# Inserimento capitale iniziale
starting_equity = st.number_input("Inserisci il capitale iniziale (€)", min_value=1.0, value=1000.0)

# Upload CSV
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

    # Calcolo Drawdown
    df['High Watermark'] = df['Equity %'].cummax()
    df['Drawdown %'] = df['Equity %'] - df['High Watermark']

    max_drawdown = df['Drawdown %'].min()

    st.subheader(f"Max Drawdown: {max_drawdown:.2f}%")

    # === Grafico Equity % ===
    st.subheader("Equity Curve (%)")
    fig1, ax1 = plt.subplots()
    ax1.plot(df['Close Date'], df['Equity %'], linewidth=2)
    ax1.set_xlabel("Data")
    ax1.set_ylabel("Equity (%)")
    ax1.grid(True)
    st.pyplot(fig1)

    # === Grafico Drawdown % ===
    st.subheader("Drawdown (%)")
    fig2, ax2 = plt.subplots()
    ax2.plot(df['Close Date'], df['Drawdown %'], color='red', linewidth=2)
    ax2.set_xlabel("Data")
    ax2.set_ylabel("Drawdown (%)")
    ax2.grid(True)
    st.pyplot(fig2)

    # Tabella semplificata
    st.subheader("Trade Eseguiti (in %)")
    simplified_table = df[['Close Date', 'Symbol', 'Action', 'Profit %']].copy()
    simplified_table['Profit %'] = simplified_table['Profit %'].map("{:.2f}%".format)
    st.dataframe(simplified_table)

else:
    st.info("Carica un file CSV per iniziare.")
