import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Family Booking", page_icon="🏠")

conn = st.connection("gsheets", type=GSheetsConnection)

def get_data(sheet_name="Prenotazioni"):
    return conn.read(worksheet=sheet_name, ttl=0)

# --- LOGIN ---
utenti = {"Lorenzo": "1234", "Membro2": "5678", "Membro3": "9012", "Membro4": "3456"}
st.sidebar.title("🔐 Accesso")
user = st.sidebar.selectbox("Utente", ["-- Seleziona --"] + list(utenti.keys()))
password = st.sidebar.text_input("PIN", type="password")

if user != "-- Seleziona --" and password == utenti[user]:
    df = get_data("Prenotazioni")
    # Pulizia colonne per sicurezza
    for col in ['Stato', 'Utente', 'Voti_Ok']:
        if col not in df.columns: df[col] = 0 if col == 'Voti_Ok' else "N/A"

    # --- NOTIFICHE ---
    pendenti_altri = df[(df['Stato'] == 'In Attesa') & (df['Utente'] != user)]
    if not pendenti_altri.empty:
        st.sidebar.warning(f"🔔 Hai {len(pendenti_altri)} richieste da votare!")

    tab1, tab2, tab3 = st.tabs(["📅 Prenota", "📊 Stato & Voti", "📸 Info Case"])

    with tab1:
        st.header("Nuova Prenotazione")
        casa = st.selectbox("Scegli la casa", ["Casa Mare", "Casa Montagna"])
        d_in = st.date_input("Check-in", min_value=datetime.today())
        d_out = st.date_input("Check-out", min_value=d_in)

        if st.button("Invia Richiesta"):
            if d_out <= d_in:
                st.error("La data di fine deve essere dopo l'inizio.")
            else:
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
        if df.empty:
            st.write("Nessuna prenotazione.")
        else:
            for index, row in df.iterrows():
                with st.expander(f"{row['Casa']} - {row['Data_Inizio']} ({row['Stato']})"):
                    st.write(f"Richiesto da: **{row['Utente']}**")
                    st.write(f"Voti favorevoli: {row['Voti_Ok']}/3")
                    
                    if row['Stato'] == 'In Attesa' and row['Utente'] != user:
                        col_approva, col_rifiuta = st.columns(2)
                        if col_approva.button("✅ Approva", key=f"ok_{index}"):
                            df.at[index, 'Voti_Ok'] = int(row['Voti_Ok']) + 1
                            if df.at[index, 'Voti_Ok'] >= 3:
                                df.at[index, 'Stato'] = 'Confermata'
                            conn.update(worksheet="Prenotazioni", data=df)
                            st.rerun()
                        if col_rifiuta.button("❌ Rifiuta", key=f"no_{index}"):
                            df.at[index, 'Stato'] = 'Rifiutata'
                            conn.update(worksheet="Prenotazioni", data=df)
                            st.rerun()
            
            st.divider()
            st.subheader("Storico Completo")
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Stato']], use_container_width=True)

    with tab3:
        st.header("Dettagli Case")
        st.write("Qui puoi inserire le foto e le descrizioni delle tue case.")

else:
    st.title("🏠 Family Booking App")
    st.info("Esegui il login per continuare.")
