import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("Analisi conto MT4 (Profitto in percentuale)")

# Inserimento del capitale iniziale
starting_equity = st.number_input("Inserisci il capitale iniziale (€)", min_value=1.0, value=1000.0)

uploaded_file = st.file_uploader("Carica il file CSV esportato da Myfxbook", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # Conversione delle date
    df['Open Date'] = pd.to_datetime(df['Open Date'], dayfirst=True, errors='coerce')
    df['Close Date'] = pd.to_datetime(df['Close Date'], dayfirst=True, errors='coerce')

    # Ordina per data di chiusura
    df = df.sort_values('Close Date').reset_index(drop=True)

    # Profitto in € e % per ogni trade
    df['Profit'] = pd.to_numeric(df['Profit'], errors='coerce')
    df['Profit %'] = df['Profit'] / starting_equity * 100

    # Equity cumulativa in percentuale
    df['Equity %'] = df['Profit %'].cumsum()

    # Calcolo drawdown in percentuale
    df['High Watermark'] = df['Equity %'].cummax()
    df['Drawdown'] = df['Equity %'] - df['High Watermark']
    df['Drawdown %'] = df['Drawdown']  # già in percentuale

    max_drawdown = df['Drawdown %'].min()

    st.subheader(f"Max Drawdown: {max_drawdown:.2f}%")

    # Grafico dell’equity in percentuale
    st.subheader("Equity Curve (%)")
    fig, ax = plt.subplots()
    ax.plot(df['Close Date'], df['Equity %'], label='Equity %')
    ax.set_xlabel("Data")
    ax.set_ylabel("Equity (%)")
    ax.legend()
    st.pyplot(fig)

    # Tabella semplificata dei trade
    st.subheader("Trade Eseguiti (in %)")
    simplified_table = df[['Close Date', 'Symbol', 'Action', 'Profit %']]
    simplified_table['Profit %'] = simplified_table['Profit %'].map("{:.2f}%".format)
    st.dataframe(simplified_table)

else:
    st.info("Carica un file CSV per iniziare.")
