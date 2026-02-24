import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configurazione Pagina
st.set_page_config(page_title="Family Booking", page_icon="🏠")

# --- CONNESSIONE AL DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Funzione per leggere i dati aggiornati
def get_data():
    return conn.read(worksheet="Prenotazioni", ttl=0)

# --- LOGIN ---
# Sostituisci i PIN con quelli che preferisci
utenti = {
    "Lorenzo": "1234",
    "Membro2": "5678",
    "Membro3": "9012",
    "Membro4": "3456"
}

st.sidebar.title("🔐 Accesso")
user = st.sidebar.selectbox("Utente", ["-- Seleziona --"] + list(utenti.keys()))
password = st.sidebar.text_input("PIN", type="password")

if user != "-- Seleziona --" and password == utenti[user]:
    st.sidebar.success(f"Ciao {user}!")
    
    # Caricamento dati
    df = get_data()
    
    # --- NOTIFICHE ---
    # Notifica se ci sono prenotazioni "In Attesa" che NON sono state create dall'utente attuale
    pendenti = df[(df['Stato'] == 'In Attesa') & (df['Utente'] != user)]
    if not pendenti.empty:
        st.sidebar.warning(f"🔔 Ci sono {len(pendenti)} richieste da approvare!")

    # --- CONTENUTO PRINCIPALE ---
    tab1, tab2, tab3 = st.tabs(["📅 Prenota", "📊 Stato Richieste", "📸 Info Case"])

    with tab1:
        st.header("Nuova Prenotazione")
        casa = st.selectbox("Scegli la casa", ["Casa Mare", "Casa Montagna"])
        
        col1, col2 = st.columns(2)
        with col1:
            d_in = st.date_input("Check-in", min_value=datetime.today())
        with col2:
            d_out = st.date_input("Check-out", min_value=d_in)

        if st.button("Invia Richiesta"):
            if d_out <= d_in:
                st.error("La data di fine deve essere successiva all'inizio.")
            else:
                # Controllo sovrapposizioni
                overlap = df[
                    (df['Casa'] == casa) & 
                    (df['Stato'] == 'Confermata') & 
                    ((pd.to_datetime(df['Data_Inizio']).dt.date <= d_out) & (pd.to_datetime(df['Data_Fine']).dt.date >= d_in))
                ]
                
                if not overlap.empty:
                    st.error("Spiacente, la casa è già occupata in queste date!")
                else:
                    # Preparazione nuova riga
                    nuova_preno = pd.DataFrame([{
                        "ID": str(datetime.now().timestamp()),
                        "Casa": casa,
                        "Utente": user,
                        "Data_Inizio": d_in.strftime('%Y-%m-%d'),
                        "Data_Fine": d_out.strftime('%Y-%m-%d'),
                        "Stato": "In Attesa"
                    }])
                    
                    # Scrittura sul foglio
                    updated_df = pd.concat([df, nuova_preno], ignore_index=True)
                    conn.update(worksheet="Prenotazioni", data=updated_df)
                    st.success("Richiesta inviata! Ora gli altri membri devono approvare.")
                    st.balloons()

    with tab2:
        st.header("Riepilogo Prenotazioni")
        if df.empty:
            st.write("Nessuna prenotazione presente.")
        else:
            # Mostra la tabella formattata bene
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato']], use_container_width=True)

    with tab3:
        st.header("Dettagli Case")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.subheader("Casa Mare")
            st.image("https://images.unsplash.com/photo-1499793983690-e29da59ef1c2?auto=format&fit=crop&q=80&w=400", caption="Villa Tramonto")
            st.write("Vista oceano, 4 posti letto, aria condizionata.")
        with col_c2:
            st.subheader("Casa Montagna")
            st.image("https://images.unsplash.com/photo-1518780664697-55e3ad937233?auto=format&fit=crop&q=80&w=400", caption="Chalet Neve")
            st.write("Vicino alle piste, camino a legna, sauna.")

else:
    st.title("🏠 Family Booking App")
    st.info("Esegui il login per gestire le case vacanze.")
    st.info("Inserisci le tue credenziali per procedere.")
