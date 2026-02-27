import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import time
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- STILE CSS ---
st.markdown("""
    <style>
    button[data-baseweb="tab"] p { font-size: 20px !important; font-weight: 800 !important; color: #007bff !important; }
    .stAlert { border-radius: 12px; }
    /* Nasconde il menu di Streamlit per dare più stabilità */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- CONNESSIONE DATABASE ---
# Usiamo il caching per evitare di ricaricare i dati ad ogni micro-sfarfallio
@st.cache_data(ttl=10)
def get_data_cached():
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(worksheet="Prenotazioni", ttl=0)
    data = data.dropna(axis=1, how='all')
    for col in ['Voti_Ok', 'Note']:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str)
        else:
            data[col] = ""
    return data

def check_overlap(start1, end1, start2, end2):
    return start1 <= end2 and start2 <= end1

# --- CONFIGURAZIONE UTENTI ---
utenti_config = {
    "Anita": {"pin": "1111", "color": "#FF4B4B"},   # Rosso Streamlit
    "Chiara": {"pin": "4444", "color": "#FFC0CB"},  # Rosa
    "Lorenzo": {"pin": "1234", "color": "#1C83E1"}, # Blu Streamlit
    "Gianluca": {"pin": "1191", "color": "#28A745"} # Verde
}

# --- LOGIN ---
st.sidebar.title("🔐 Accesso Family")
user = st.sidebar.selectbox("Chi sei?", ["-- Seleziona --"] + list(utenti_config.keys()))
password = st.sidebar.text_input("PIN", type="password")

if user != "-- Seleziona --" and password == utenti_config[user]["pin"]:
    # Carichiamo i dati
    df = get_data_cached()
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 PRENOTA", "📊 STATO & VOTI", "🗓️ CALENDARIO", "📸 INFO & STATS"])

    # --- TAB 1: PRENOTAZIONE ---
    with tab1:
        st.header("Nuova Prenotazione")
        col_form, col_foto = st.columns([2, 1])
        with col_form:
            casa = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
            # Filtro rapido disponibilità
            prenotazioni_casa = df[df['Casa'] == casa].copy()
            if not prenotazioni_casa.empty:
                for _, r in prenotazioni_casa[prenotazioni_casa['Stato'] == "Confermata"].iterrows():
                    st.error(f"🚫 Occupato: {r['Data_Inizio']} - {r['Data_Fine']} ({r['Utente']})")
            
            d_in = st.date_input("Check-in", value=datetime.today().date() + timedelta(days=1))
            d_out = st.date_input("Check-out", value=d_in + timedelta(days=1))
            note = st.text_area("Note")

            if st.button("🚀 INVIA RICHIESTA", key="send_req"):
                nuova = pd.DataFrame([{
                    "ID": str(datetime.now().timestamp()), "Casa": casa, "Utente": user,
                    "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                    "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                }])
                conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                st.cache_data.clear() # Svuota cache per aggiornare dati
                st.success("Richiesta inviata!")
                st.rerun()

    # --- TAB 2: STATO & VOTI ---
    with tab2:
        st.header("Situazione e Gestione")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.divider()
            # Logica Voti semplificata per stabilità
            for idx, row in df.iterrows():
                if row['Utente'] != user and row['Stato'] == "In Attesa":
                    votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                    if user not in votanti:
                        if st.button(f"Approva {row['Utente']} per {row['Casa']}", key=f"v_{idx}"):
                            votanti.append(user)
                            df.at[idx, 'Voti_Ok'] = ", ".join(votanti)
                            if len(votanti) >= 3: df.at[idx, 'Stato'] = "Confermata"
                            conn.update(worksheet="Prenotazioni", data=df)
                            st.cache_data.clear()
                            st.rerun()

    # --- TAB 3: CALENDARIO (VERSIONE STABILE) ---
    with tab3:
        st.header("🗓️ Calendario Occupazione")
        st.markdown("**Legenda:** 🔴 Anita | 🌸 Chiara | 🔵 Lorenzo | 🟢 Gianluca")
        
        events = []
        for _, row in df[df['Stato'] == "Confermata"].iterrows():
            try:
                # Formato ISO richiesto dal calendario
                start = datetime.strptime(row['Data_Inizio'], '%d/%m/%Y').date().isoformat()
                # Aggiungiamo un giorno alla fine perché FullCalendar esclude il giorno finale
                end_dt = datetime.strptime(row['Data_Fine'], '%d/%m/%Y').date() + timedelta(days=1)
                events.append({
                    "title": f"{row['Casa']} ({row['Utente']})",
                    "start": start,
                    "end": end_dt.isoformat(),
                    "backgroundColor": utenti_config.get(row['Utente'], {}).get("color", "#CCCCCC"),
                    "borderColor": utenti_config.get(row['Utente'], {}).get("color", "#CCCCCC"),
                    "allDay": True
                })
            except: continue

        # Opzioni calendario ridotte all'essenziale per evitare flickering
        cal_options = {
            "initialView": "dayGridMonth",
            "locale": "it",
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": ""},
            "editable": False,
            "selectable": False
        }
        
        # Il componente calendar viene visualizzato senza salvare il suo stato in una variabile
        # Questo blocca il loop di ricaricamento
        calendar(events=events, options=cal_options, key="family_calendar")

    # --- TAB 4: STATISTICHE ---
    with tab4:
        st.header("📊 Statistiche")
        # ... (stessa logica di prima) ...
        st.info("Qui trovi il riepilogo dei giorni spesi!")

else:
    st.title("🏠 Family Booking")
    st.info("Accedi con il tuo PIN")
