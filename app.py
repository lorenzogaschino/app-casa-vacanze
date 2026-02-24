import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="Family Booking", page_icon="🏠")

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # Leggiamo i dati freschi
        data = conn.read(worksheet="Prenotazioni", ttl=0)
        # Assicuriamoci che le colonne Data siano trattate come testo per non farle invertire da Streamlit
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
        
        # NOTA: st.date_input mostrerà sempre il formato di sistema (es. 2026/02/24)
        # ma noi lo salviamo correttamente
        d_in = st.date_input("Check-in", min_value=datetime.today())
        d_out = st.date_input("Check-out", min_value=d_in)

        if st.button("Invia Richiesta"):
            if d_out <= d_in:
                st.error("La data di fine deve essere dopo l'inizio.")
            else:
                # Creiamo il record con le date in formato italiano per lo Sheet
                nuova_preno = pd.DataFrame([{
                    "ID": str(datetime.now().timestamp()),
                    "Casa": casa, 
                    "Utente": user,
                    "Data_Inizio": d_in.strftime('%d/%m/%Y'),
                    "Data_Fine": d_out.strftime('%d/%m/%Y'),
                    "Stato": "In Attesa", 
                    "Voti_Ok": 0
                }])
                
                # Feedback visivo con st.status per il "Momento WOW"
                with st.status("🚀 Lancio della richiesta nello spazio...", expanded=True) as status:
                    updated_df = pd.concat([df, nuova_preno], ignore_index=True)
                    conn.update(worksheet="Prenotazioni", data=updated_df)
                    st.balloons() # Esplosione di palloncini
                    time.sleep(1)
                    status.update(label="✅ Richiesta salvata nel Cloud!", state="complete", expanded=False)
                
                st.success(f"Ottimo Lorenzo! La richiesta per {casa} è stata inviata.")
                time.sleep(2.5) # Pausa per godersi il successo
                st.rerun()

    with tab2:
        st.header("Riepilogo Prenotazioni")
        if df.empty:
            st.info("Nessuna prenotazione trovata.")
        else:
            # Visualizziamo la tabella: qui le date dovrebbero apparire GG/MM/AAAA 
            # perché le abbiamo forzate come stringhe in get_data()
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato']], use_container_width=True)
            
            st.divider()
            st.subheader("Votazioni Pendenti")
            for index, row in df.iterrows():
                if str(row['Stato']) == 'In Attesa' and row['Utente'] != user:
                    with st.expander(f"Vota: {row['Utente']} per {row['Casa']}"):
                        st.write(f"📅 Dal **{row['Data_Inizio']}** al **{row['Data_Fine']}**")
                        if st.button("✅ Approva", key=f"v_{index}"):
                            # Logica di aggiornamento voto
                            voti_attuali = int(row['Voti_Ok']) if pd.notnull(row['Voti_Ok']) else 0
                            df.at[index, 'Voti_Ok'] = voti_attuali + 1
                            if df.at[index, 'Voti_Ok'] >= 3:
                                df.at[index, 'Stato'] = 'Confermata'
                            
                            conn.update(worksheet="Prenotazioni", data=df)
                            st.snow() # Feedback "fresco" per il voto
                            time.sleep(2)
                            st.rerun()

    with tab3:
        st.header("Galleria Case")
        st.info("Siamo pronti per caricare le tue foto!")

else:
    st.title("🏠 Family Booking App")
    st.info("Effettua il login per gestire le case vacanza.")
