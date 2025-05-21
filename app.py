import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO, StringIO
from fpdf import FPDF
import tempfile
import os

st.title("Analisi conto MT4 (Profitto in percentuale)")

starting_equity = st.number_input("Inserisci il capitale iniziale (€)", min_value=1.0, value=1000.0)

if starting_equity <= 0:
    st.error("⚠️ Inserisci un capitale iniziale maggiore di 0.")
    st.stop()

uploaded_file = st.file_uploader("Carica il file CSV o HTML esportato da Myfxbook o MT4", type=["csv", "htm"])

if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)

        df['Open Date'] = pd.to_datetime(df['Open Date'], dayfirst=True, errors='coerce')
        df['Close Date'] = pd.to_datetime(df['Close Date'], dayfirst=True, errors='coerce')
        df_closed = df[df['Close Date'].notna()].sort_values('Close Date').reset_index(drop=True)
        df_closed['Profit'] = pd.to_numeric(df_closed['Profit'], errors='coerce').round(2)
        df_closed['Pips'] = pd.to_numeric(df_closed['Pips'], errors='coerce').round(1)

    elif uploaded_file.name.endswith(".htm"):
        html_text = uploaded_file.read().decode("windows-1252")
        tables = pd.read_html(StringIO(html_text))

        target_table = None
        for tbl in tables:
            required_cols = {"Type", "Open Time", "Close Time", "Profit"}
            if required_cols.issubset(tbl.columns):
                target_table = tbl
                break

        if target_table is None:
            st.error("❌ Nessuna tabella valida trovata nel file HTML.")
            st.stop()

        df = target_table.copy()
        df = df[df["Type"].str.lower().isin(["buy", "sell"])]

        df["Open Date"] = pd.to_datetime(df["Open Time"], errors="coerce")
        df["Close Date"] = pd.to_datetime(df["Close Time"], errors="coerce")
        df["Action"] = df["Type"].str.lower()
        df["Symbol"] = df.get("Item") or df.get("Symbol") or ""
        df["Symbol"] = df["Symbol"].astype(str).str.lower()
        df["Profit"] = pd.to_numeric(df["Profit"], errors="coerce")
        df["Open Price"] = pd.to_numeric(df["Price"], errors="coerce")
        df["Close Price"] = pd.to_numeric(df["Close Price"], errors="coerce")

        def calc_pips(row):
            if pd.isna(row["Open Price"]) or pd.isna(row["Close Price"]):
                return None
            symbol = row["Symbol"]
            if "jpy" in symbol:
                multiplier = 100
            elif "btc" in symbol:
                multiplier = 1
            else:
                multiplier = 10000
            if row["Action"] == "buy":
                return (row["Close Price"] - row["Open Price"]) * multiplier
            else:
                return (row["Open Price"] - row["Close Price"]) * multiplier

        df["Pips"] = df.apply(calc_pips, axis=1).round(1)
        df_closed = df[["Open Date", "Close Date", "Action", "Symbol", "Profit", "Pips"]].copy()

    # Il resto del codice prosegue senza modifiche...
