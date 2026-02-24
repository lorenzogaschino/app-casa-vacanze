import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Gestione Case", layout="centered")

# --- CONNESSIONE AL FOGLIO GOOGLE ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Lettura dati (assumendo che il foglio 'Prenotazioni' sia il primo o specificato)
df_prenotazioni = conn.read(ttl=0) # ttl=0 forza l'aggiornamento dei dati a ogni ricarica

st.title("🏠 Prenotazione Case Vacanze")

# --- LOGIN ---
utenti_validi = {"User1": "1111", "User2": "2222", "User3": "3333", "User4": "4444"}
st.sidebar.header("Area Personale")
nome = st.sidebar.selectbox("Chi sei?", ["Seleziona..."] + list(utenti_validi.keys()))
pin = st.sidebar.text_input("Inserisci PIN", type="password")

if nome != "Seleziona..." and pin == utenti_validi.get(nome):
    st.sidebar.success(f"Loggato come {nome}")
    
    # --- NOTIFICHE ---
    # Contiamo quante prenotazioni sono in stato "Attesa" (simulazione campanella)
    pendenti = len(df_prenotazioni[df_prenotazioni['Stato'] == 'Attesa'])
    if pendenti > 0:
        st.sidebar.warning(f"🔔 Hai {pendenti} richieste da votare!")

    tab1, tab2 = st.tabs(["Casa Mare", "Casa Montagna"])

    with tab1:
        st.header("Villa Tramonto")
        st.write("Descrizione della splendida casa al mare.")
        
        with st.form("form_mare"):
            d_in = st.date_input("Check-in")
            d_out = st.date_input("Check-out")
            submit = st.form_submit_button("Invia Richiesta")
            
            if submit:
                if d_out <= d_in:
                    st.error("La data di fine deve essere dopo quella di inizio!")
                else:
                    # Qui aggiungeremo la funzione per SCRIVERE sul foglio
                    st.success(f"Richiesta inviata per il periodo {d_in} - {d_out}")

else:
    st.info("Inserisci le tue credenziali per procedere.")
