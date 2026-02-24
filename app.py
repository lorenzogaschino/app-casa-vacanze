import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Family Booking", page_icon="🏠")

# Connessione
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # Prova a leggere il foglio Prenotazioni
        data = conn.read(worksheet="Prenotazioni", ttl=0)
        return data
    except:
        # Se fallisce, crea un database vuoto con le colonne giuste
        return pd.DataFrame(columns=["ID", "Casa", "Utente", "Data_Inizio", "Data_Fine", "Stato", "Voti_Ok"])

# --- LOGIN ---
utenti = {"Lorenzo": "1234", "Membro2": "5678", "Membro3": "9012", "Membro4": "3456"}
st.sidebar.title("🔐 Accesso")
user = st.sidebar.selectbox("Utente", ["-- Seleziona --"] + list(utenti.keys()))
password = st.sidebar.text_input("PIN", type="password")

if user != "-- Seleziona --" and password == utenti[user]:
    df = get_data()
    
    # Assicuriamoci che le colonne esistano sempre
    for col in ["Stato", "Utente", "Voti_Ok"]:
        if col not in df.columns:
            df[col] = "In Attesa" if col == "Stato" else 0

    # --- NOTIFICHE ---
    pendenti = df[(df['Stato'] == 'In Attesa') & (df['Utente'] != user)]
    if not pendenti.empty:
        st.sidebar.warning(f"🔔 Hai {len(pendenti)} richieste da votare!")

    tab1, tab2, tab3 = st.tabs(["📅 Prenota", "📊 Stato & Voti", "📸 Info Case"])

    with tab1:
        st.header("Nuova Prenotazione")
        casa = st.selectbox("Scegli la casa", ["Casa Mare", "Casa Montagna"])
        d_in = st.date_input("Check-in", min_value=datetime.today())
        d_out = st.date_input("Check-out", min_value=d_in)

        if st.button("Invia Richiesta"):
            nuova_preno = pd.DataFrame([{
                "ID": str(datetime.now().timestamp()),
                "Casa": casa, "Utente": user,
                "Data_Inizio": d_in.strftime('%Y-%m-%d'),
                "Data_Fine": d_out.strftime('%Y-%m-%d'),
                "Stato": "In Attesa", "Voti_Ok": 0
            }])
            updated_df = pd.concat([df, nuova_preno], ignore_index=True)
            conn.update(worksheet="Prenotazioni", data=updated_df)
            st.success("Richiesta inviata!")
            st.rerun()

    with tab2:
        st.header("Gestione Approvazioni")
        if df.empty or len(df) == 0:
            st.write("Nessuna prenotazione trovata.")
        else:
            for index, row in df.iterrows():
                with st.expander(f"{row['Casa']} - {row['Data_Inizio']} ({row['Stato']})"):
                    st.write(f"Richiesto da: **{row['Utente']}** | Voti: {row.get('Voti_Ok', 0)}/3")
                    if row['Stato'] == 'In Attesa' and row['Utente'] != user:
                        if st.button("✅ Approva questa richiesta", key=f"btn_{index}"):
                            df.at[index, 'Voti_Ok'] = int(row.get('Voti_Ok', 0)) + 1
                            if df.at[index, 'Voti_Ok'] >= 3:
                                df.at[index, 'Stato'] = 'Confermata'
                            conn.update(worksheet="Prenotazioni", data=df)
                            st.rerun()

    with tab3:
        st.header("Le nostre Case")
        st.subheader("Villa Tramonto (Mare)")
        st.image("https://images.unsplash.com/photo-1499793983690-e29da59ef1c2?w=400")
        st.subheader("Chalet Neve (Montagna)")
        st.image("https://images.unsplash.com/photo-1518780664697-55e3ad937233?w=400")

else:
    st.title("🏠 Family Booking App")
    st.info("Esegui il login per continuare.")
