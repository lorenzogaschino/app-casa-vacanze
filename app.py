import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="Family Booking", page_icon="🏠")

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # ttl=0 forza l'app a scaricare i dati freschi ogni volta
        return conn.read(worksheet="Prenotazioni", ttl=0)
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
                # Creazione riga con data GG/MM/AAAA
                nuova_preno = pd.DataFrame([{
                    "ID": str(datetime.now().timestamp()),
                    "Casa": casa, 
                    "Utente": user,
                    "Data_Inizio": d_in.strftime('%d/%m/%Y'),
                    "Data_Fine": d_out.strftime('%d/%m/%Y'),
                    "Stato": "In Attesa", 
                    "Voti_Ok": 0
                }])
                
                with st.spinner('Comunicazione con Night City in corso...'):
                    updated_df = pd.concat([df, nuova_preno], ignore_index=True)
                    conn.update(worksheet="Prenotazioni", data=updated_df)
                    
                    # MOMENTO WOW POTENZIATO
                    st.balloons()
                    st.success(f"🔥 Grande {user}! Richiesta per {casa} salvata correttamente.")
                    
                    # Aspettiamo 3 secondi per goderci i palloncini prima del refresh
                    time.sleep(3)
                    st.rerun()

    with tab2:
        st.header("Riepilogo e Voti")
        if df.empty:
            st.info("Nessuna prenotazione presente.")
        else:
            # Mostra tabella pulita
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato']], use_container_width=True)
            
            st.divider()
            # Sezione Votazione
            for index, row in df.iterrows():
                if str(row['Stato']) == 'In Attesa' and row['Utente'] != user:
                    with st.expander(f"Vota richiesta di {row['Utente']} ({row['Data_Inizio']})"):
                        if st.button("✅ Approva", key=f"v_{index}"):
                            # Logica voto
                            voti = int(row['Voti_Ok']) if pd.notnull(row['Voti_Ok']) else 0
                            df.at[index, 'Voti_Ok'] = voti + 1
                            if df.at[index, 'Voti_Ok'] >= 3:
                                df.at[index, 'Stato'] = 'Confermata'
                            conn.update(worksheet="Prenotazioni", data=df)
                            st.snow() # Neve per il voto!
                            time.sleep(2)
                            st.rerun()

    with tab3:
        st.header("Info Case")
        st.write("Prossimamente: le tue foto reali!")

else:
    st.title("🏠 Family Booking App")
    st.info("Esegui il login per accedere alle funzioni.")
