import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("Analisi conto MT4 con Myfxbook")

# Caricamento del file CSV
uploaded_file = st.file_uploader("Carica il file CSV esportato da Myfxbook", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # Mostra l'anteprima
    st.subheader("Anteprima dei dati")
    st.write(df.head())

    # Conversione delle date
    df['Open Time'] = pd.to_datetime(df['Open Time'], errors='coerce')
    df['Close Time'] = pd.to_datetime(df['Close Time'], errors='coerce')

    # Calcolo equity nel tempo
    df = df.sort_values('Close Time')
    df['Profit'] = df['Profit'].cumsum()
    df['Equity'] = df['Profit'] + df['Deposit/Withdrawal'].fillna(0).cumsum()

    # Calcolo drawdown corretto
    df['High Watermark'] = df['Equity'].cummax()
    df['Drawdown'] = df['Equity'] - df['High Watermark']
    df['Drawdown %'] = df['Drawdown'] / df['High Watermark'] * 100

    max_drawdown = df['Drawdown %'].min()

    st.subheader(f"Max Drawdown: {max_drawdown:.2f}%")

    # Grafico equity
    st.subheader("Equity Curve")
    fig, ax = plt.subplots()
    ax.plot(df['Close Time'], df['Equity'], label='Equity')
    ax.set_xlabel("Data")
    ax.set_ylabel("Equity")
    ax.legend()
    st.pyplot(fig)

    # Tabella dei trade
    st.subheader("Tabella dei trade eseguiti")
    st.dataframe(df[['Ticket', 'Open Time', 'Close Time', 'Type', 'Lots', 'Symbol', 'Open Price', 'Close Price', 'Profit']])

else:
    st.info("Carica un file CSV per iniziare.")
