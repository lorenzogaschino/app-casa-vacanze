import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="Family Booking", page_icon="🏠")

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # Leggiamo i dati
        data = conn.read(worksheet="Prenotazioni", ttl=0)
        # Forziamo le colonne delle date a essere trattate come stringhe (testo)
        # così Streamlit non le inverte
        if not data.empty:
            data['Data_Inizio'] = data['Data_Inizio'].astype(str)
            data['Data_Fine'] = data['Data_Fine'].astype(str)
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
        casa = st.selectbox("Scegli la casa", ["Casa Mare", "Casa Montagna"])
        d_in = st.date_input("Check-in", min_value=datetime.today())
        d_out = st.date_input("Check-out", min_value=d_in)

        if st.button("Invia Richiesta"):
            if d_out <= d_in:
                st.error("La data di fine deve essere successiva all'inizio!")
            else:
                nuova_preno = pd.DataFrame([{
                    "ID": str(datetime.now().timestamp()),
                    "Casa": casa, 
                    "Utente": user,
                    "Data_Inizio": d_in.strftime('%d/%m/%Y'),
                    "Data_Fine": d_out.strftime('%d/%m/%Y'),
                    "Stato": "In Attesa", 
                    "Voti_Ok": 0
                }])
                
                # Feedback "Momento WOW"
                with st.status("Salvataggio in corso...", expanded=True) as status:
                    updated_df = pd.concat([df, nuova_preno], ignore_index=True)
                    conn.update(worksheet="Prenotazioni", data=updated_df)
                    st.balloons()
                    status.update(label="✅ Prenotazione Inviata!", state="complete", expanded=False)
                
                st.success(f"Richiesta per {casa} registrata. Reindirizzamento...")
                time.sleep(3) # Pausa per vedere i palloncini
                st.rerun()

    with tab2:
        st.header("Riepilogo e Voti")
        if df.empty:
            st.info("Nessuna prenotazione presente.")
        else:
            # Tabella con date formattate GG/MM/AAAA
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato']], use_container_width=True)
            
            st.divider()
            for index, row in df.iterrows():
                if str(row['Stato']) == 'In Attesa' and row['Utente'] != user:
                    with st.expander(f"Vota: {row['Utente']} ({row['Data_Inizio']})"):
                        if st.button("✅ Approva", key=f"v_{index}"):
                            voti = int(row['Voti_Ok']) if pd.notnull(row['Voti_Ok']) else 0
                            df.at[index, 'Voti_Ok'] = voti + 1
                            if df.at[index, 'Voti_Ok'] >= 3:
                                df.at[index, 'Stato'] = 'Confermata'
                            conn.update(worksheet="Prenotazioni", data=df)
                            st.snow()
                            time.sleep(2)
                            st.rerun()

    with tab3:
        st.header("Info Case")
        st.write("Sezione in aggiornamento con le tue foto reali.")

else:
    st.title("🏠 Family Booking App")
    st.info("Esegui il login per accedere.")
