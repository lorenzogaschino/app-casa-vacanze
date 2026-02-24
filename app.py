import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
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

# Funzione per controllare se due periodi si sovrappongono
def check_overlap(start1, end1, start2, end2):
    return start1 <= end2 and start2 <= end1

if 'user' not in st.session_state:
    st.session_state.user = None

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
            
            # --- LOGICA DI CONTROLLO DISPONIBILITÀ ---
            prenotazioni_casa = df[df['Casa'] == casa].copy()
            if not prenotazioni_casa.empty:
                st.write("⚠️ **Giorni già occupati per questa casa:**")
                for _, row in prenotazioni_casa.iterrows():
                    color = "🔴" if row['Stato'] == "Confermata" else "🟡"
                    st.write(f"{color} {row['Data_Inizio']} - {row['Data_Fine']} ({row['Utente']})")
            
            d_in = st.date_input("Check-in", min_value=datetime.today())
            d_out = st.date_input("Check-out", min_value=d_in)
            
            if st.button("🚀 Invia Richiesta"):
                # Convertiamo gli input in datetime per il confronto
                overlap_found = False
                for _, row in prenotazioni_casa.iterrows():
                    # Convertiamo le date dallo sheet (stringhe) a oggetti datetime
                    data_inizio_esistente = datetime.strptime(row['Data_Inizio'], '%d/%m/%Y').date()
                    data_fine_esistente = datetime.strptime(row['Data_Fine'], '%d/%m/%Y').date()
                    
                    if check_overlap(d_in, d_out, data_inizio_esistente, data_fine_esistente):
                        overlap_found = True
                        proprietario = row['Utente']
                        stato_sovrapp = row['Stato']
                        break
                
                if overlap_found:
                    st.error(f"❌ Errore: Le date scelte si sovrappongono con una prenotazione di **{proprietario}** (Stato: {stato_sovrapp}). Scegli un altro periodo!")
                elif d_out == d_in:
                    st.warning("Il check-out deve essere almeno il giorno dopo il check-in!")
                else:
                    nuova_preno = pd.DataFrame([{
                        "ID": str(datetime.now().timestamp()),
                        "Casa": casa, "Utente": user,
                        "Data_Inizio": d_in.strftime('%d/%m/%Y'),
                        "Data_Fine": d_out.strftime('%d/%m/%Y'),
                        "Stato": "In Attesa", "Voti_Ok": 0
                    }])
                    with st.status("Verifica disponibilità e salvataggio...", expanded=True) as status:
                        updated_df = pd.concat([df, nuova_preno], ignore_index=True)
                        conn.update(worksheet="Prenotazioni", data=updated_df)
                        st.balloons()
                        status.update(label="✅ Richiesta salvata!", state="complete")
                    time.sleep(2)
                    st.rerun()

        with col_foto:
            st.write("🔍 **Anteprima:**")
            nome_file = "Noli.jpg" if casa == "NOLI" else "Limone.jpg"
            if os.path.exists(nome_file):
                st.image(nome_file, width=250)
            else:
                st.info("Carica le foto su GitHub per l'anteprima")

    with tab2:
        st.header("Situazione Attuale")
        if not df.empty:
            # Ordiniamo per data (un po' complesso essendo stringhe, ma mostriamo lo sheet così com'è)
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato']], use_container_width=True)
            
            st.divider()
            st.subheader("Vota Richieste Pendenti")
            # Logica voti (omessa per brevità, resta quella precedente)
            for index, row in df.iterrows():
                if str(row.get('Stato')) == 'In Attesa' and row.get('Utente') != user:
                    with st.expander(f"Vota: {row['Utente']} a {row['Casa']}"):
                        st.write(f"📅 Dal {row['Data_Inizio']} al {row['Data_Fine']}")
                        if st.button("Approva ✅", key=f"v_{index}"):
                            v = int(row['Voti_Ok']) if pd.notnull(row['Voti_Ok']) else 0
                            df.at[index, 'Voti_Ok'] = v + 1
                            if df.at[index, 'Voti_Ok'] >= 3:
                                df.at[index, 'Stato'] = 'Confermata'
                            conn.update(worksheet="Prenotazioni", data=df)
                            st.snow()
                            time.sleep(1)
                            st.rerun()
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
