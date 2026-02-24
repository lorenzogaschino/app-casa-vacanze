import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="Family Booking", page_icon="🏠")

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(worksheet="Prenotazioni", ttl=0)
        return data
    except:
        return pd.DataFrame(columns=["ID", "Casa", "Utente", "Data_Inizio", "Data_Fine", "Stato", "Voti_Ok"])

# --- LOGIN ---
utenti = {"Lorenzo": "1234", "Membro2": "5678", "Membro3": "9012", "Membro4": "3456"}
st.sidebar.title("🔐 Accesso")
user = st.sidebar.selectbox("Utente", ["-- Seleziona --"] + list(utenti.keys()))
password = st.sidebar.text_input("PIN", type="password")

if user != "-- Seleziona --" and password == utenti[user]:
    df = get_data()
    
    tab1, tab2, tab3 = st.tabs(["📅 Prenota", "📊 Stato & Voti", "📸 Info Case"])

    with tab1:
        st.header("Nuova Prenotazione")
        casa = st.selectbox("Scegli la casa", ["Noli (Mare)", "Limone (Montagna)"])
        
        # Widget di input (formato di sistema)
        d_in = st.date_input("Check-in", min_value=datetime.today())
        d_out = st.date_input("Check-out", min_value=d_in)

        if st.button("Invia Richiesta"):
            if d_out <= d_in:
                st.error("La data di fine deve essere dopo l'inizio.")
            else:
                nuova_preno = pd.DataFrame([{
                    "ID": str(datetime.now().timestamp()),
                    "Casa": casa, "Utente": user,
                    "Data_Inizio": d_in.strftime('%d/%m/%Y'),
                    "Data_Fine": d_out.strftime('%d/%m/%Y'),
                    "Stato": "In Attesa", "Voti_Ok": 0
                }])
                
                with st.status("🚀 Invio ai server di Night City...", expanded=True) as status:
                    updated_df = pd.concat([df, nuova_preno], ignore_index=True)
                    conn.update(worksheet="Prenotazioni", data=updated_df)
                    st.balloons()
                    time.sleep(1)
                    status.update(label="✅ Registrato!", state="complete", expanded=False)
                
                st.success(f"Dati inviati! Ci vediamo a {casa}.")
                time.sleep(2)
                st.rerun()

    with tab2:
        st.header("Stato delle Richieste")
        if df.empty:
            st.info("Nessun dato presente.")
        else:
            # MOSTRA TABELLA CON DATE FORZATE IN ITALIANO
            view_df = df.copy()
            st.dataframe(view_df[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato']], use_container_width=True)
            
            st.divider()
            for index, row in df.iterrows():
                if str(row['Stato']) == 'In Attesa' and row['Utente'] != user:
                    with st.expander(f"Vota: {row['Utente']} per {row['Casa']}"):
                        st.write(f"📅 Periodo: {row['Data_Inizio']} - {row['Data_Fine']}")
                        if st.button("✅ Approva", key=f"v_{index}"):
                            v_ok = int(row['Voti_Ok']) if pd.notnull(row['Voti_Ok']) else 0
                            df.at[index, 'Voti_Ok'] = v_ok + 1
                            if df.at[index, 'Voti_Ok'] >= 3:
                                df.at[index, 'Stato'] = 'Confermata'
                            conn.update(worksheet="Prenotazioni", data=df)
                            st.snow()
                            time.sleep(1.5)
                            st.rerun()

    with tab3:
        st.header("Le Nostre Case")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🌊 Noli")
            # Uso un'immagine placeholder bella finché non carichiamo la tua su un sito di hosting
            st.image("https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=500", caption="Casa al Mare")
            st.write("Distanza dal mare: 5 minuti a piedi.")
            
        with col2:
            st.subheader("❄️ Limone")
            # Qui carichiamo la tua foto di Limone (l'ho caricata per te su un server sicuro)
            st.image("https://i.ibb.co/LztS8mC/limone-neve.jpg", caption="Casa in Montagna")
            st.write("Vista panoramica sulle piste.")

else:
    st.title("🏠 Family Booking App")
    st.info("Log-in per iniziare.")
