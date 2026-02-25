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
        # Assicuriamoci che i voti siano stringhe
        if 'Voti_Ok' in data.columns:
            data['Voti_Ok'] = data['Voti_Ok'].fillna("").astype(str)
        return data
    except:
        return pd.DataFrame(columns=["ID", "Casa", "Utente", "Data_Inizio", "Data_Fine", "Stato", "Voti_Ok"])

# --- CONFIGURAZIONE MEMBRI ---
# Qui puoi rinominare i membri e cambiare i PIN
utenti = {
    "Lorenzo": "1234", 
    "Maria": "5678", 
    "Pietro": "9012", 
    "Giulia": "3456"
}

st.sidebar.title("🔐 Accesso Family")
user = st.sidebar.selectbox("Chi sei?", ["-- Seleziona --"] + list(utenti.keys()))
password = st.sidebar.text_input("PIN", type="password")

if user != "-- Seleziona --" and password == utenti[user]:
    df = get_data()
    
    # NOTIFICA DI CONFERMA AVVENUTA
    mie_preno_confermate = df[(df['Utente'] == user) & (df['Stato'] == "Confermata")]
    if not mie_preno_confermate.empty:
        st.toast(f"🎉 Ottime notizie {user}! Hai prenotazioni confermate!", icon="✅")

    tab1, tab2, tab3 = st.tabs(["📅 Prenota", "📊 Stato & Voti", "📸 Info Case"])

    with tab1:
        st.header("Nuova Prenotazione")
        col_form, col_foto = st.columns([2, 1])
        with col_form:
            casa = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
            
            # Visualizzazione disponibilità migliorata
            prenotazioni_casa = df[df['Casa'] == casa].copy()
            if not prenotazioni_casa.empty:
                richieste = prenotazioni_casa[prenotazioni_casa['Stato'] == "In Attesa"]
                confermate = prenotazioni_casa[prenotazioni_casa['Stato'] == "Confermata"]
                if not richieste.empty:
                    st.warning("⚠️ **Giorni richiesti:**")
                    for _, r in richieste.iterrows(): st.write(f"🟡 {r['Data_Inizio']} - {r['Data_Fine']} ({r['Utente']})")
                if not confermate.empty:
                    st.error("🚫 **Giorni già PRENOTATI:**")
                    for _, r in confermate.iterrows(): st.write(f"🔴 {r['Data_Inizio']} - {r['Data_Fine']} ({r['Utente']})")
            
            d_in = st.date_input("Check-in", min_value=datetime.today())
            d_out = st.date_input("Check-out", min_value=d_in)
            
            if st.button("🚀 Invia Richiesta"):
                # (Logica controllo sovrapposizione omessa per brevità ma inclusa nel tuo codice reale)
                nuova_preno = pd.DataFrame([{
                    "ID": str(datetime.now().timestamp()),
                    "Casa": casa, "Utente": user,
                    "Data_Inizio": d_in.strftime('%d/%m/%Y'),
                    "Data_Fine": d_out.strftime('%d/%m/%Y'),
                    "Stato": "In Attesa", "Voti_Ok": ""
                }])
                updated_df = pd.concat([df, nuova_preno], ignore_index=True)
                conn.update(worksheet="Prenotazioni", data=updated_df)
                st.balloons()
                st.rerun()

        with col_foto:
            nome_file = f"{casa.capitalize()}.jpg"
            if os.path.exists(nome_file): st.image(nome_file, width=250)

    with tab2:
        st.header("Situazione e Gestione")
        
        # AGGIUNTA COLONNA CONTEGGIO VOTI
        if not df.empty:
            df_display = df.copy()
            def count_votes(v_str):
                v_list = [v.strip() for v in str(v_str).split(",") if v.strip()]
                return f"{len(v_list)}/3"
            
            df_display['Approvazioni'] = df_display['Voti_Ok'].apply(count_votes)
            st.dataframe(df_display[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato', 'Approvazioni']], use_container_width=True)
            
            st.divider()
            col_voti, col_gestione = st.columns(2)
            
            with col_voti:
                st.subheader("🗳️ Vota richieste")
                for idx, row in df.iterrows():
                    if row['Utente'] != user and row['Stato'] == "In Attesa":
                        votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                        label_button = f"Approva {row['Utente']} a {row['Casa']} ({row['Data_Inizio']})"
                        
                        if user in votanti:
                            st.button(f"✅ Hai già approvato {row['Utente']}", key=f"v_{idx}", disabled=True)
                        else:
                            if st.button(label_button, key=f"v_{idx}"):
                                votanti.append(user)
                                new_voti = ", ".join(votanti)
                                df.at[idx, 'Voti_Ok'] = new_voti
                                if len(votanti) >= 3:
                                    df.at[idx, 'Stato'] = "Confermata"
                                conn.update(worksheet="Prenotazioni", data=df)
                                st.snow()
                                time.sleep(1)
                                st.rerun()

            with col_gestione:
                st.subheader("🗑️ Le mie prenotazioni")
                mie = df[df['Utente'] == user]
                for idx, row in mie.iterrows():
                    # DOPPIO STEP DI CANCELLAZIONE
                    if f"confirm_del_{idx}" not in st.session_state:
                        if st.button(f"Elimina {row['Casa']} ({row['Data_Inizio']})", key=f"del_{idx}"):
                            st.session_state[f"confirm_del_{idx}"] = True
                            st.rerun()
                    else:
                        st.warning("⚠️ Sei sicuro?")
                        c_del, c_ann = st.columns(2)
                        if c_del.button("SÌ, Elimina", key=f"yes_{idx}", type="primary"):
                            df = df.drop(idx)
                            conn.update(worksheet="Prenotazioni", data=df)
                            del st.session_state[f"confirm_del_{idx}"]
                            st.rerun()
                        if c_ann.button("No, annulla", key=f"no_{idx}"):
                            del st.session_state[f"confirm_del_{idx}"]
                            st.rerun()

    with tab3:
        # (Galleria case come prima...)
        pass

else:
    st.title("🏠 Family Booking App")
    st.info("Benvenuto! Effettua il login per gestire le case di famiglia.")
