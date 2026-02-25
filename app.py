import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# Configurazione Pagina
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# CSS per i Tab e stile messaggi
st.markdown("""
    <style>
    button[data-baseweb="tab"] p { font-size: 24px !important; font-weight: 800 !important; color: #007bff !important; }
    button[data-baseweb="tab"] { padding: 20px 30px !important; }
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

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

# --- LISTA UTENTI UFFICIALE ---
utenti = {"Anita": "1111", "Chiara": "4444", "Lorenzo": "1234", "Gianluca": "1191"}

# --- LOGIN ---
st.sidebar.title("🔐 Accesso Family")
user = st.sidebar.selectbox("Chi sei?", ["-- Seleziona --"] + list(utenti.keys()))
password = st.sidebar.text_input("PIN", type="password")

if user != "-- Seleziona --" and password == utenti[user]:
    df = get_data()
    
    tab1, tab2, tab3 = st.tabs(["📅 PRENOTA", "📊 STATO & VOTI", "📸 INFO CASE"])

    with tab1:
        st.header("Nuova Prenotazione")
        col_form, col_foto = st.columns([2, 1])
        
        with col_form:
            casa = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
            
            # --- ANALISI DISPONIBILITÀ ---
            prenotazioni_casa = df[df['Casa'] == casa].copy()
            giorni_confermati = []
            giorni_richiesti = []
            
            if not prenotazioni_casa.empty:
                for _, r in prenotazioni_casa.iterrows():
                    d_i = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                    d_f = datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date()
                    info = f"{d_i.strftime('%d/%m')} al {d_f.strftime('%d/%m')} ({r['Utente']})"
                    if r['Stato'] == "Confermata":
                        giorni_confermati.append(info)
                    else:
                        giorni_richiesti.append(info)

            # Messaggi informativi pre-selezione
            if giorni_confermati:
                st.error(f"🚫 **NON DISPONIBILE:** {', '.join(giorni_confermati)}")
            if giorni_richiesti:
                st.warning(f"🟡 **RICHIESTE IN CORSO:** {', '.join(giorni_richiesti)}")

            d_in = st.date_input("Check-in", min_value=datetime.today())
            d_out = st.date_input("Check-out", min_value=d_in)
            
            # --- LOGICA DI OVERLAP DINAMICO ---
            overlap_confermato = False
            overlap_richiesto = False
            utente_conflitto = ""

            for _, row in prenotazioni_casa.iterrows():
                d_i_esistente = datetime.strptime(row['Data_Inizio'], '%d/%m/%Y').date()
                d_f_esistente = datetime.strptime(row['Data_Fine'], '%d/%m/%Y').date()
                
                if check_overlap(d_in, d_out, d_i_esistente, d_f_esistente):
                    utente_conflitto = row['Utente']
                    if row['Stato'] == "Confermata":
                        overlap_confermato = True
                    else:
                        overlap_richiesto = True

            # --- GESTIONE TASTO INVIO ---
            if overlap_confermato:
                st.error(f"❌ Impossibile prenotare: La casa è già stata confermata a **{utente_conflitto}** per queste date.")
                st.button("🚀 INVIA RICHIESTA", disabled=True)
            elif overlap_richiesto:
                st.info(f"⚖️ **Sovrapposizione Morbida:** Attenzione, **{utente_conflitto}** ha già richiesto queste date ma non è ancora confermato. Vuoi comunque procedere e parlarne con lui?")
                if st.button("🚀 PROCEDI COMUNQUE"):
                    # Salvataggio identico a quello standard
                    nuova = pd.DataFrame([{
                        "ID": str(datetime.now().timestamp()), "Casa": casa, "Utente": user,
                        "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                        "Stato": "In Attesa", "Voti_Ok": ""
                    }])
                    conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                    st.balloons()
                    time.sleep(1.5)
                    st.rerun()
            else:
                if st.button("🚀 INVIA RICHIESTA"):
                    if d_out == d_in:
                        st.warning("Seleziona almeno una notte!")
                    else:
                        nuova = pd.DataFrame([{
                            "ID": str(datetime.now().timestamp()), "Casa": casa, "Utente": user,
                            "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                            "Stato": "In Attesa", "Voti_Ok": ""
                        }])
                        conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                        st.balloons()
                        time.sleep(1.5)
                        st.rerun()

        with col_foto:
            f_nome = "Noli.jpg" if casa == "NOLI" else "Limone.jpg"
            if os.path.exists(f_nome): st.image(f_nome, width=300)

    with tab2:
        st.header("Situazione e Gestione")
        if not df.empty:
            df_view = df.copy()
            df_view['Approvazioni'] = df_view['Voti_Ok'].apply(lambda v: f"{len([x for x in str(v).split(',') if x.strip()])}/3")
            st.dataframe(df_view[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato', 'Approvazioni']], use_container_width=True)
            
            st.divider()
            c_voti, c_gest = st.columns(2)
            with c_voti:
                st.subheader("🗳️ Vota Richieste")
                for idx, row in df.iterrows():
                    if row['Utente'] != user and row['Stato'] == "In Attesa":
                        votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                        if user in votanti:
                            st.success(f"✅ Approvato da te: {row['Utente']}")
                        else:
                            if st.button(f"Approva {row['Utente']} ({row['Data_Inizio']})", key=f"v_{idx}"):
                                votanti.append(user)
                                df.at[idx, 'Voti_Ok'] = ", ".join(votanti)
                                if len(votanti) >= 3: df.at[idx, 'Stato'] = "Confermata"
                                conn.update(worksheet="Prenotazioni", data=df)
                                st.snow()
                                time.sleep(1)
                                st.rerun()
            with c_gest:
                st.subheader("🗑️ Mie Prenotazioni")
                for idx, row in df[df['Utente'] == user].iterrows():
                    if f"confirm_{idx}" not in st.session_state:
                        if st.button(f"Elimina {row['Casa']} ({row['Data_Inizio']})", key=f"d_{idx}"):
                            st.session_state[f"confirm_{idx}"] = True
                            st.rerun()
                    else:
                        st.warning("⚠️ Confermi?")
                        if st.button("SÌ", key=f"y_{idx}", type="primary"):
                            df = df.drop(idx)
                            conn.update(worksheet="Prenotazioni", data=df)
                            del st.session_state[f"confirm_{idx}"]
                            st.rerun()
                        if st.button("NO", key=f"n_{idx}"):
                            del st.session_state[f"confirm_{idx}"]
                            st.rerun()

    with tab3:
        st.header("Le Nostre Case")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🏖️ NOLI")
            if os.path.exists("Noli.jpg"): st.image("Noli.jpg", use_container_width=True)
        with c2:
            st.subheader("🏔️ LIMONE")
            if os.path.exists("Limone.jpg"): st.image("Limone.jpg", use_container_width=True)

else:
    st.title("🏠 Family Booking App")
    st.info("Login richiesto.")
