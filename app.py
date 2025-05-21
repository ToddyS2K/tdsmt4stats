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

        best_table = None
        for idx, table in enumerate(tables):
            rows = table.find_all('tr')
            for i, row in enumerate(rows):
                # Cerca la prima riga che somiglia a un'intestazione, anche se fatta con <td>
                cells = [td.get_text(strip=True).replace('\xa0', ' ') for td in row.find_all('td')]
                match_count = sum(col in cells for col in ['Open Time', 'Close Time', 'Type', 'Size', 'Item', 'Profit'])
                if match_count >= 5:
                    headers = cells
                    data_rows = []
                    for data_row in rows[i+1:]:
                        data_cells = [td.get_text(strip=True) for td in data_row.find_all('td')]
                        # Solo righe con numero di celle uguale alle intestazioni
                        if len(data_cells) == len(headers):
                            data_rows.append(data_cells)
                    if data_rows:
                        best_table = (headers, data_rows)
                    break

        if best_table is None:
            st.error("❌ Nessuna tabella valida trovata nel file HTML.")
            st.stop()

        headers, rows = best_table
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

        if 'Price' in df.columns and 'Price.1' in df.columns:
            df['Open Price'] = pd.to_numeric(df['Price'], errors='coerce')
            df['Close Price'] = pd.to_numeric(df['Price.1'], errors='coerce')
            df['Pips'] = ((df['Close Price'] - df['Open Price']) * 10000).round(1)
        else:
            df['Pips'] = 0.0

    else:
        st.error("❌ Formato file non supportato. Carica un file CSV o HTML.")
        st.stop()

    df['Open Date'] = pd.to_datetime(df['Open Date'], dayfirst=True, errors='coerce')
    df['Close Date'] = pd.to_datetime(df['Close Date'], dayfirst=True, errors='coerce')

    if df['Open Date'].isna().all() or df['Close Date'].isna().all():
        st.error("❌ Nessuna data valida trovata nei trade.")
        st.stop()

    # Resto del codice invariato...
    # [Tutte le funzionalità esistenti come calcoli, grafici, PDF, ecc. restano uguali]

else:
    st.info("Carica un file CSV per iniziare.")
