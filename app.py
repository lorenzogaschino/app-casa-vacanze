import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
import os

st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(worksheet="Prenotazioni", ttl=0)
        # Pulizia: rimuove colonne vuote (D, E) e assicura che le date siano stringhe
        data = data.dropna(axis=1, how='all')
        if not data.empty:
            for col in ['Data_Inizio', 'Data_Fine']:
                if col in data.columns:
                    data[col] = data[col].astype(str)
        return data
    except:
        return pd.DataFrame(columns=["ID", "Casa", "Utente", "Data_Inizio", "Data_Fine", "Stato", "Voti_Ok"])

# --- LOGIN ---
utenti = {"Lorenzo": "1234", "Membro2": "5678", "Membro3": "9012", "Membro4": "3456"}
st.sidebar.title("🔐 Accesso")
user = st.sidebar.selectbox("Chi sei?", ["-- Seleziona --"] + list(utenti.keys()))
password = st.sidebar.text_input("PIN", type="password")

if user != "-- Seleziona --" and password == utenti[user]:
    df = get_data()
    tab1, tab2, tab3 = st.tabs(["📅 Prenota", "📊 Stato & Voti", "📸 Info Case"])

    with tab1:
        st.header("Nuova Prenotazione")
        casa = st.selectbox("Scegli la casa", ["NOLI", "LIMONE"])
        col1, col2 = st.columns(2)
        with col1:
            d_in = st.date_input("Check-in", min_value=datetime.today())
        with col2:
            d_out = st.date_input("Check-out", min_value=d_in)

        if st.button("Invia Richiesta"):
            nuova_preno = pd.DataFrame([{
                "ID": str(datetime.now().timestamp()),
                "Casa": casa, "Utente": user,
                "Data_Inizio": d_in.strftime('%d/%m/%Y'),
                "Data_Fine": d_out.strftime('%d/%m/%Y'),
                "Stato": "In Attesa", "Voti_Ok": 0
            }])
            with st.status("Salvataggio nel database...", expanded=True) as status:
                updated_df = pd.concat([df, nuova_preno], ignore_index=True)
                conn.update(worksheet="Prenotazioni", data=updated_df)
                st.balloons()
                status.update(label="✅ Richiesta inviata!", state="complete")
            time.sleep(2)
            st.rerun()

    with tab2:
        st.header("Situazione Attuale")
        if not df.empty:
            # Mostra tabella pulita
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato']], use_container_width=True)
        else:
            st.info("Nessuna prenotazione presente.")

    with tab3:
        st.header("Le Nostre Case")
        c1, c2 = st.columns(2)
        
        # Gestione Foto Noli
        with c1:
            st.subheader("🏖️ NOLI")
            # Cerchiamo il file ignorando maiuscole/minuscole
            if os.path.exists("Noli.jpg"):
                st.image("Noli.jpg", use_container_width=True)
            elif os.path.exists("noli.jpg"):
                st.image("noli.jpg", use_container_width=True)
            else:
                st.warning("Carica 'Noli.jpg' su GitHub")
            st.caption("La perla della Liguria")

        # Gestione Foto Limone
        with c2:
            st.subheader("🏔️ LIMONE")
            if os.path.exists("Limone.jpg"):
                st.image("Limone.jpg", use_container_width=True)
            elif os.path.exists("limone.jpg"):
                st.image("limone.jpg", use_container_width=True)
            else:
                st.warning("Carica 'Limone.jpg' su GitHub")
            st.caption("Relax sulle Alpi")

else:
    st.title("🏠 Family Booking App")
    st.info("Esegui il login per accedere alle prenotazioni di famiglia.")
