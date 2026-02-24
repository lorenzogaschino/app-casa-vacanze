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
        # Pulizia: forziamo tutto a stringa appena letto per evitare conversioni browser
        for col in ['Data_Inizio', 'Data_Fine']:
            if col in data.columns:
                data[col] = data[col].astype(str)
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
        casa = st.selectbox("Scegli la casa", ["NOLI", "LIMONE"])
        
        # Input data (visualizzazione browser)
        d_in = st.date_input("Check-in", min_value=datetime.today())
        d_out = st.date_input("Check-out", min_value=d_in)

        if st.button("Invia Richiesta"):
            nuova_preno = pd.DataFrame([{
                "ID": str(datetime.now().timestamp()),
                "Casa": casa, "Utente": user,
                "Data_Inizio": d_in.strftime('%d/%m/%Y'),
                "Data_Fine": d_out.strftime('%d/%m/%Y'),
                "Stato": "In Attesa", "Voti_Ok": 0
            }])
            
            with st.status("🚀 Invio richiesta in corso...", expanded=True) as status:
                updated_df = pd.concat([df, nuova_preno], ignore_index=True)
                conn.update(worksheet="Prenotazioni", data=updated_df)
                st.balloons()
                status.update(label="✅ Richiesta Salvata!", state="complete")
            
            st.success(f"Fatto! La tua richiesta per {casa} è ora visibile agli altri.")
            time.sleep(2)
            st.rerun()

    with tab2:
        st.header("Stato e Approvazioni")
        if not df.empty:
            # Mostriamo la tabella forzando la visualizzazione corretta
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato']], use_container_width=True)
            
            st.divider()
            for index, row in df.iterrows():
                if str(row['Stato']) == 'In Attesa' and row['Utente'] != user:
                    with st.expander(f"Vota: {row['Utente']} ({row['Data_Inizio']})"):
                        if st.button("✅ Approva", key=f"v_{index}"):
                            v_ok = int(row['Voti_Ok']) if pd.notnull(row['Voti_Ok']) else 0
                            df.at[index, 'Voti_Ok'] = v_ok + 1
                            if df.at[index, 'Voti_Ok'] >= 3:
                                df.at[index, 'Stato'] = 'Confermata'
                            conn.update(worksheet="Prenotazioni", data=df)
                            st.snow()
                            time.sleep(1.5)
                            st.rerun()
        else:
            st.info("Nessuna prenotazione attiva.")

    with tab3:
        st.header("Le Nostre Case")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🏖️ NOLI")
            st.image("https://i.ibb.co/VpL4X4L/noli-mare.jpg", use_container_width=True)
            st.caption("La perla del Ponente Ligure")
        with c2:
            st.subheader("🏔️ LIMONE")
            st.image("https://i.ibb.co/LztS8mC/limone-neve.jpg", use_container_width=True)
            st.caption("Sulle piste da sci")

else:
    st.title("🏠 Family Booking App")
    st.info("Effettua il login per iniziare.")
