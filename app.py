import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
import os

# Configurazione Pagina
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# Connessione a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(worksheet="Prenotazioni", ttl=0)
        data = data.dropna(axis=1, how='all')
        if 'Voti_Ok' in data.columns:
            data['Voti_Ok'] = data['Voti_Ok'].fillna("").astype(str)
        return data
    except:
        return pd.DataFrame(columns=["ID", "Casa", "Utente", "Data_Inizio", "Data_Fine", "Stato", "Voti_Ok"])

def check_overlap(start1, end1, start2, end2):
    return start1 <= end2 and start2 <= end1

# --- CONFIGURAZIONE MEMBRI ---
utenti = {
    "Anita": "1111", 
    "Chiara": "4444", 
    "Lorenzo": "1234", 
    "Gianluca": "1191"
}

# --- LOGIN NELLA SIDEBAR ---
st.sidebar.title("🔐 Accesso Family")
user = st.sidebar.selectbox("Chi sei?", ["-- Seleziona --"] + list(utenti.keys()))
password = st.sidebar.text_input("PIN", type="password")

if user != "-- Seleziona --" and password == utenti[user]:
    df = get_data()
    
    # Notifica rapida per prenotazioni appena confermate
    mie_preno_conf = df[(df['Utente'] == user) & (df['Stato'] == "Confermata")]
    if not mie_preno_conf.empty:
        st.toast(f"🎉 Grandioso {user}! Hai dei soggiorni confermati!", icon="✅")

    # --- NAVIGAZIONE PRINCIPALE (Sostituisce i Tab) ---
    st.sidebar.divider()
    menu = st.sidebar.radio("VAI A:", ["📅 Prenota", "📊 Stato e Voti", "📸 Info Case"])

    # --- CONTENUTO: PRENOTA ---
    if menu == "📅 Prenota":
        st.header("Nuova Prenotazione")
        col_form, col_foto = st.columns([2, 1])
        
        with col_form:
            casa = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
            
            # Visualizzazione disponibilità
            prenotazioni_casa = df[df['Casa'] == casa].copy()
            if not prenotazioni_casa.empty:
                richieste = prenotazioni_casa[prenotazioni_casa['Stato'] == "In Attesa"]
                confermate = prenotazioni_casa[prenotazioni_casa['Stato'] == "Confermata"]
                
                if not richieste.empty:
                    st.warning("⚠️ **Giorni già RICHIESTI per questa casa:**")
                    for _, r in richieste.iterrows(): 
                        st.write(f"🟡 {r['Data_Inizio']} - {r['Data_Fine']} ({r['Utente']})")
                
                if not confermate.empty:
                    st.error("🚫 **Giorni già PRENOTATI per questa casa:**")
                    for _, r in confermate.iterrows(): 
                        st.write(f"🔴 {r['Data_Inizio']} - {r['Data_Fine']} ({r['Utente']})")
            
            d_in = st.date_input("Check-in", min_value=datetime.today())
            d_out = st.date_input("Check-out", min_value=d_in)
            
            if st.button("🚀 Invia Richiesta"):
                overlap = False
                for _, row in prenotazioni_casa.iterrows():
                    d_i = datetime.strptime(row['Data_Inizio'], '%d/%m/%Y').date()
                    d_f = datetime.strptime(row['Data_Fine'], '%d/%m/%Y').date()
                    if check_overlap(d_in, d_out, d_i, d_f):
                        overlap = True
                        prop, st_sov = row['Utente'], row['Stato']
                        break
                
                if overlap:
                    st.error(f"Impossibile: sovrapposizione con {prop} ({st_sov})")
                elif d_out == d_in:
                    st.warning("Seleziona almeno una notte!")
                else:
                    nuova = pd.DataFrame([{
                        "ID": str(datetime.now().timestamp()),
                        "Casa": casa, "Utente": user,
                        "Data_Inizio": d_in.strftime('%d/%m/%Y'),
                        "Data_Fine": d_out.strftime('%d/%m/%Y'),
                        "Stato": "In Attesa", "Voti_Ok": ""
                    }])
                    with st.status("Salvataggio..."):
                        up_df = pd.concat([df, nuova], ignore_index=True)
                        conn.update(worksheet="Prenotazioni", data=up_df)
                        st.balloons()
                    time.sleep(1.5)
                    st.rerun()

        with col_foto:
            f_nome = "Noli.jpg" if casa == "NOLI" else "Limone.jpg"
            if os.path.exists(f_nome): st.image(f_nome, width=300, caption=f"Anteprima {casa}")

    # --- CONTENUTO: STATO E VOTI ---
    elif menu == "📊 Stato e Voti":
        st.header("Situazione e Gestione")
        if not df.empty:
            # Tabella con calcolo approvazioni (es. 1/3)
            df_view = df.copy()
            def count_v(v_str):
                v_list = [v.strip() for v in str(v_str).split(",") if v.strip()]
                return f"{len(v_list)}/3"
            df_view['Approvazioni'] = df_view['Voti_Ok'].apply(count_v)
            st.dataframe(df_view[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato', 'Approvazioni']], use_container_width=True)
            
            st.divider()
            c_voti, c_gest = st.columns(2)
            
            with c_voti:
                st.subheader("🗳️ Approva Richieste")
                for idx, row in df.iterrows():
                    if row['Utente'] != user and row['Stato'] == "In Attesa":
                        votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                        if user in votanti:
                            st.success(f"✅ Hai approvato {row['Utente']} ({row['Data_Inizio']})")
                        else:
                            if st.button(f"Approva {row['Utente']} ({row['Data_Inizio']})", key=f"v_{idx}"):
                                votanti.append(user)
                                df.at[idx, 'Voti_Ok'] = ", ".join(votanti)
                                if len(votanti) >= 3:
                                    df.at[idx, 'Stato'] = "Confermata"
                                conn.update(worksheet="Prenotazioni", data=df)
                                st.snow()
                                time.sleep(1)
                                st.rerun()

            with c_gest:
                st.subheader("🗑️ Mie Prenotazioni")
                mie = df[df['Utente'] == user]
                for idx, row in mie.iterrows():
                    c_key = f"confirm_del_{idx}"
                    if c_key not in st.session_state:
                        if st.button(f"Elimina {row['Casa']} ({row['Data_Inizio']})", key=f"d_{idx}"):
                            st.session_state[c_key] = True
                            st.rerun()
                    else:
                        st.warning("Sicuro di voler cancellare?")
                        c_si, c_no = st.columns(2)
                        if c_si.button("SÌ, Cancella", key=f"si_{idx}", type="primary"):
                            df = df.drop(idx)
                            conn.update(worksheet="Prenotazioni", data=df)
                            del st.session_state[c_key]
                            st.rerun()
                        if c_no.button("Annulla", key=f"no_{idx}"):
                            del st.session_state[c_key]
                            st.rerun()
        else:
            st.info("Nessun dato presente.")

    # --- CONTENUTO: INFO CASE ---
    elif menu == "📸 Info Case":
        st.header("Le Nostre Case")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🌊 NOLI")
            if os.path.exists("Noli.jpg"): st.image("Noli.jpg", use_container_width=True)
        with c2:
            st.subheader("🏔️ LIMONE")
            if os.path.exists("Limone.jpg"): st.image("Limone.jpg", use_container_width=True)

else:
    st.title("🏠 Family Booking App")
    st.info("Benvenuto! Effettua il login nella barra laterale per iniziare.")
