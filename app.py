import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- STILE CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    /* Tab grandi e Bold per facilitare il tocco su mobile */
    button[data-baseweb="tab"] p {
        font-size: 22px !important;
        font-weight: 800 !important;
        color: #007bff !important;
    }
    button[data-baseweb="tab"] {
        padding: 15px 25px !important;
    }
    /* Stile per i messaggi di avviso */
    .stAlert {
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONNESSIONE DATABASE ---
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
    
    # Notifica automatica per soggiorni confermati
    mie_conf = df[(df['Utente'] == user) & (df['Stato'] == "Confermata")]
    if not mie_conf.empty:
        st.toast(f"🎉 Ciao {user}, hai dei soggiorni confermati!", icon="✅")

    # --- NAVIGAZIONE CENTRALE ---
    tab1, tab2, tab3 = st.tabs(["📅 PRENOTA", "📊 STATO & VOTI", "📸 INFO CASE"])

    # --- TAB 1: PRENOTAZIONE ---
    with tab1:
        st.header("Nuova Prenotazione")
        col_form, col_foto = st.columns([2, 1])
        
        with col_form:
            casa = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
            
            # Analisi disponibilità per la casa scelta
            prenotazioni_casa = df[df['Casa'] == casa].copy()
            g_conf_info = []
            g_rich_info = []
            
            if not prenotazioni_casa.empty:
                for _, r in prenotazioni_casa.iterrows():
                    d_i = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                    d_f = datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date()
                    txt = f"{d_i.strftime('%d/%m')} al {d_f.strftime('%d/%m')} ({r['Utente']})"
                    if r['Stato'] == "Confermata":
                        g_conf_info.append((d_i, d_f, txt))
                    else:
                        g_rich_info.append((d_i, d_f, txt))

            # Visualizzazione avvisi rapidi in alto
            if g_conf_info:
                st.error(f"🚫 **NON DISPONIBILE:** {', '.join([x[2] for x in g_conf_info])}")
            if g_rich_info:
                st.warning(f"🟡 **GIÀ RICHIESTI:** {', '.join([x[2] for x in g_rich_info])}")

            # Date Input con default a domani per evitare conflitti immediati con "oggi"
            default_in = datetime.today().date() + timedelta(days=1)
            d_in = st.date_input("Check-in", value=default_in, min_value=datetime.today().date())
            d_out = st.date_input("Check-out", value=d_in + timedelta(days=1), min_value=d_in)
            
            # Controllo conflitti in tempo reale
            is_conf_conflict = False
            is_rich_conflict = False
            nome_conflitto = ""

            for start, end, info in g_conf_info:
                if check_overlap(d_in, d_out, start, end):
                    is_conf_conflict = True
                    nome_conflitto = info.split('(')[-1].replace(')', '')
                    break
            
            if not is_conf_conflict:
                for start, end, info in g_rich_info:
                    if check_overlap(d_in, d_out, start, end):
                        is_rich_conflict = True
                        nome_conflitto = info.split('(')[-1].replace(')', '')
                        break

            # Gestione dinamica dei pulsanti di invio
            if is_conf_conflict:
                st.error(f"❌ Impossibile procedere: date già confermate a **{nome_conflitto}**.")
                st.button("🚀 INVIA RICHIESTA", disabled=True, key="btn_no")
            elif is_rich_conflict:
                st.info(f"⚖️ **Sovrapposizione Morbida:** {nome_conflitto} ha già chiesto queste date. Vuoi procedere comunque?")
                if st.button("🚀 PROCEDI COMUNQUE", key="btn_maybe"):
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
                if st.button("🚀 INVIA RICHIESTA", key="btn_ok"):
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
            if os.path.exists(f_nome):
                st.image(f_nome, width=300, caption=f"Anteprima {casa}")

    # --- TAB 2: STATO E VOTI ---
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
                            st.success(f"✅ Hai approvato {row['Utente']} ({row['Data_Inizio']})")
                        else:
                            if st.button(f"Approva {row['Utente']} a {row['Casa']}", key=f"v_{idx}"):
                                votanti.append(user)
                                df.at[idx, 'Voti_Ok'] = ", ".join(votanti)
                                if len(votanti) >= 3:
                                    df.at[idx, 'Stato'] = "Confermata"
                                conn.update(worksheet="Prenotazioni", data=df)
                                st.snow()
                                time.sleep(1)
                                st.rerun()

            with c_gest:
                st.subheader("🗑️ Le Mie Prenotazioni")
                for idx, row in df[df['Utente'] == user].iterrows():
                    c_key = f"confirm_{idx}"
                    if c_key not in st.session_state:
                        if st.button(f"Elimina {row['Casa']} ({row['Data_Inizio']})", key=f"d_{idx}"):
                            st.session_state[c_key] = True
                            st.rerun()
                    else:
                        st.warning("⚠️ Confermi l'eliminazione?")
                        col_y, col_n = st.columns(2)
                        if col_y.button("SÌ", key=f"y_{idx}", type="primary"):
                            df = df.drop(idx)
                            conn.update(worksheet="Prenotazioni", data=df)
                            del st.session_state[c_key]
                            st.rerun()
                        if col_n.button("NO", key=f"n_{idx}"):
                            del st.session_state[c_key]
                            st.rerun()
        else:
            st.info("Nessuna prenotazione presente.")

    # --- TAB 3: INFO CASE ---
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
    st.info("Benvenuto! Seleziona il tuo nome e inserisci il PIN per accedere.")
