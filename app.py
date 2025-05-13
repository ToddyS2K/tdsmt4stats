import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("Analisi conto MT4 (Myfxbook CSV)")

uploaded_file = st.file_uploader("Carica il file CSV esportato da Myfxbook", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # Conversione delle date
    df['Open Date'] = pd.to_datetime(df['Open Date'], dayfirst=True, errors='coerce')
    df['Close Date'] = pd.to_datetime(df['Close Date'], dayfirst=True, errors='coerce')

    # Ordina per data di chiusura
    df = df.sort_values('Close Date').reset_index(drop=True)

    # Calcolo equity cumulativa
    df['Profit'] = pd.to_numeric(df['Profit'], errors='coerce')
    df['Equity'] = df['Profit'].cumsum()

    # Calcolo drawdown
    df['High Watermark'] = df['Equity'].cummax()
    df['Drawdown'] = df['Equity'] - df['High Watermark']
    df['Drawdown %'] = df['Drawdown'] / df['High Watermark'] * 100

    max_drawdown = df['Drawdown %'].min()

    st.subheader(f"Max Drawdown: {max_drawdown:.2f}%")

    # Grafico Equity
    st.subheader("Equity Curve")
    fig, ax = plt.subplots()
    ax.plot(df['Close Date'], df['Equity'], label='Equity')
    ax.set_xlabel("Data")
    ax.set_ylabel("Equity (€)")
    ax.legend()
    st.pyplot(fig)

    # Tabella dei trade
    st.subheader("Trade Eseguiti")
    st.dataframe(df[['Ticket', 'Open Date', 'Close Date', 'Symbol', 'Action', 'Units/Lots', 'Open Price', 'Close Price', 'Profit']])

else:
    st.info("Carica un file CSV per iniziare.")
