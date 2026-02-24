import streamlit as st
import pandas as pd

# Configurazione Pagina
st.set_page_config(page_title="Gestione Case Famiglia", layout="centered")

# URL del tuo Google Sheet (versione export CSV)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Lu2sqaGkc57rphmTkC2VTjjy2nu1P9TTUCrpZW2EU10/export?format=csv"

st.title("🏠 Prenotazione Case Vacanze")

# Sidebar per il Login semplice
st.sidebar.header("Login Utente")
utente = st.sidebar.selectbox("Chi sei?", ["Seleziona...", "Utente 1", "Utente 2", "Utente 3", "Utente 4"])
pin = st.sidebar.text_input("Inserisci PIN", type="password")

if utente != "Seleziona..." and pin == "1234": # Useremo 1234 come test
    st.sidebar.success(f"Benvenuto {utente}!")
    
    tab1, tab2 = st.tabs(["Casa Al Mare", "Casa in Montagna"])

    with tab1:
        st.header("Villa Tramonto")
        st.image("https://via.placeholder.com/800x400.png?text=Foto+Casa+Mare") # Metteremo le tue foto vere dopo
        st.write("Splendida villa con vista mare, 3 camere da letto.")
        
        # Calendario
        d_inizio = st.date_input("Inizio permanenza", key="mare_in")
        d_fine = st.date_input("Fine permanenza", key="mare_out")
        
        if st.button("Richiedi Prenotazione Mare"):
            if d_fine <= d_inizio:
                st.error("Errore: La data di fine deve essere successiva a quella di inizio!")
            else:
                st.info(f"Richiesta inviata per il periodo {d_inizio} - {d_fine}. In attesa di approvazione.")

    with tab2:
        st.header("Chalet Neve")
        st.image("https://via.placeholder.com/800x400.png?text=Foto+Casa+Montagna")
        st.write("Accogliente chalet vicino alle piste da sci.")
        # Simile a sopra...
        
else:
    st.warning("Per favore, effettua il login dalla barra laterale per vedere le disponibilità.")
