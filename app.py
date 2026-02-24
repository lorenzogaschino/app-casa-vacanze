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
        data = data.dropna(axis=1, how='all')
        return data
    except:
        return pd.DataFrame(columns=["ID", "Casa", "Utente", "Data_Inizio", "Data_Fine", "Stato", "Voti_Ok"])

def check_overlap(start1, end1, start2, end2):
    return start1 <= end2 and start2 <= end1

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
        col_form, col_foto = st.columns([2, 1])
        
        with col_form:
            casa = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
            
            # --- VISUALIZZAZIONE DISPONIBILITÀ ---
            prenotazioni_casa = df[df['Casa'] == casa].copy()
            if not prenotazioni_casa.empty:
                richieste = prenotazioni_casa[prenotazioni_casa['Stato'] == "In Attesa"]
                confermate = prenotazioni_casa[prenotazioni_casa['Stato'] == "Confermata"]
                
                if not richieste.empty:
                    st.warning("⚠️ **Giorni già RICHIESTI per questa casa:**")
                    for _, r in richieste.iterrows():
                        st.write(f"🟡 {r['Data_Inizio']} - {r['Data_Fine']} ({r['Utente']})")
                
                if not confermate.empty:
                    st.error("🚫 **Giorni già PRENOTATI per questa casa:**")
                    for _, r in confermate.iterrows():
                        st.write(f"🔴 {r['Data_Inizio']} - {r['Data_Fine']} ({r['Utente']})")
            
            d_in = st.date_input("Check-in", min_value=datetime.today())
            d_out = st.date_input("Check-out", min_value=d_in)
            
            if st.button("🚀 Invia Richiesta"):
                overlap_found = False
                for _, row in prenotazioni_casa.iterrows():
                    d_inizio_es = datetime.strptime(row['Data_Inizio'], '%d/%m/%Y').date()
                    d_fine_es = datetime.strptime(row['Data_Fine'], '%d/%m/%Y').date()
                    if check_overlap(d_in, d_out, d_inizio_es, d_fine_es):
                        overlap_found = True
                        proprietario, stato_sovrapp = row['Utente'], row['Stato']
                        break
                
                if overlap_found:
                    st.error(f"Impossibile procedere: sovrapposizione con {proprietario} ({stato_sovrapp})")
                elif d_out == d_in:
                    st.warning("Il soggiorno deve durare almeno una notte!")
                else:
                    nuova_preno = pd.DataFrame([{
                        "ID": str(datetime.now().timestamp()),
                        "Casa": casa, "Utente": user,
                        "Data_Inizio": d_in.strftime('%d/%m/%Y'),
                        "Data_Fine": d_out.strftime('%d/%m/%Y'),
                        "Stato": "In Attesa", "Voti_Ok": 0
                    }])
                    with st.status("Salvataggio...", expanded=True):
                        updated_df = pd.concat([df, nuova_preno], ignore_index=True)
                        conn.update(worksheet="Prenotazioni", data=updated_df)
                        st.balloons()
                    time.sleep(2)
                    st.rerun()

        with col_foto:
            nome_file = "Noli.jpg" if casa == "NOLI" else "Limone.jpg"
            if os.path.exists(nome_file): st.image(nome_file, width=250)

    with tab2:
        st.header("Situazione e Gestione")
        if not df.empty:
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato']], use_container_width=True)
            
            st.divider()
            col_voti, col_gestione = st.columns(2)
            
            with col_voti:
                st.subheader("🗳️ Vota richieste altrui")
                for index, row in df.iterrows():
                    if str(row.get('Stato')) == 'In Attesa' and row.get('Utente') != user:
                        if st.button(f"Approva {row['Utente']} a {row['Casa']} ({row['Data_Inizio']})", key=f"v_{index}"):
                            v = int(row['Voti_Ok']) if pd.notnull(row['Voti_Ok']) else 0
                            df.at[index, 'Voti_Ok'] = v + 1
                            if df.at[index, 'Voti_Ok'] >= 3:
                                df.at[index, 'Stato'] = 'Confermata'
                            conn.update(worksheet="Prenotazioni", data=df)
                            st.snow()
                            time.sleep(1)
                            st.rerun()

            with col_gestione:
                st.subheader("🗑️ Le mie prenotazioni")
                mie_preno = df[df['Utente'] == user]
                if not mie_preno.empty:
                    for index, row in mie_preno.iterrows():
                        if st.button(f"Elimina: {row['Casa']} ({row['Data_Inizio']})", key=f"del_{index}"):
                            df = df.drop(index)
                            conn.update(worksheet="Prenotazioni", data=df)
                            st.warning("Prenotazione eliminata.")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.write("Non hai prenotazioni attive.")
        else:
            st.info("Nessuna prenotazione presente.")

    with tab3:
        st.header("Le Nostre Case")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🏖️ NOLI")
            if os.path.exists("Noli.jpg"): st.image("Noli.jpg", use_container_width=True)
        with c2:
            st.subheader("🏔️ LIMONE")
            if os.path.exists("Limone.jpg"): st.image("Limone.jpg", use_container_width=True)

else:
    st.title("🏠 Family Booking App")
    st.info("Esegui il login.")
