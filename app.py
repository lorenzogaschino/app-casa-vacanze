import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    button[data-baseweb="tab"] p { font-size: 22px !important; font-weight: 800 !important; color: #007bff !important; }
    button[data-baseweb="tab"] { padding: 15px 25px !important; }
    .stAlert { border-radius: 12px; }
    .stats-card { background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNESSIONE DATABASE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(worksheet="Prenotazioni", ttl=0)
        data = data.dropna(axis=1, how='all')
        for col in ['Voti_Ok', 'Note']:
            if col in data.columns:
                data[col] = data[col].fillna("").astype(str)
            else:
                data[col] = ""
        return data
    except:
        return pd.DataFrame(columns=["ID", "Casa", "Utente", "Data_Inizio", "Data_Fine", "Stato", "Voti_Ok", "Note"])

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
    
    # Notifica Toast
    mie_conf = df[(df['Utente'] == user) & (df['Stato'] == "Confermata")]
    if not mie_conf.empty:
        st.toast(f"🎉 Ciao {user}, controlla i tuoi countdown!", icon="✅")

    # --- MEMORIA DEL TAB ---
    # Usiamo un parametro query o session_state per mantenere il tab attivo
    if 'current_tab' not in st.session_state:
        st.session_state.current_tab = "📅 PRENOTA"

    # Definiamo i tab
    tab1, tab2, tab3 = st.tabs(["📅 PRENOTA", "📊 STATO & VOTI", "📸 INFO & STATS"])

    # --- TAB 1: PRENOTAZIONE ---
    with tab1:
        st.header("Nuova Prenotazione")
        col_form, col_foto = st.columns([2, 1])
        
        with col_form:
            casa = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
            
            # Analisi disponibilità
            prenotazioni_casa = df[df['Casa'] == casa].copy()
            g_conf_info = []
            if not prenotazioni_casa.empty:
                for _, r in prenotazioni_casa.iterrows():
                    d_i = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                    d_f = datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date()
                    if r['Stato'] == "Confermata":
                        g_conf_info.append((d_i, d_f, f"{d_i.strftime('%d/%m')} al {d_f.strftime('%d/%m')} ({r['Utente']})"))
            
            d_in = st.date_input("Check-in", value=datetime.today().date() + timedelta(days=1), min_value=datetime.today().date())
            d_out = st.date_input("Check-out", value=d_in + timedelta(days=1), min_value=d_in)
            
            # --- CALCOLO NOTTI ---
            notti = (d_out - d_in).days
            if notti > 0:
                st.info(f"🌙 Stai prenotando per **{notti}** notti.")
            
            # --- CAMPO NOTE ---
            note = st.text_area("Commenti / Note (es. 'Saremo in 4', 'Porto il cane')", placeholder="Scrivi qui...")

            # Logica conflitti
            is_conf_conflict = False
            for start, end, info in g_conf_info:
                if check_overlap(d_in, d_out, start, end):
                    is_conf_conflict = True
                    st.error(f"❌ Già confermata a {info.split('(')[-1]}")
                    break

            if st.button("🚀 INVIA RICHIESTA", disabled=is_conf_conflict):
                if notti <= 0:
                    st.warning("Seleziona almeno una notte!")
                else:
                    nuova = pd.DataFrame([{
                        "ID": str(datetime.now().timestamp()), "Casa": casa, "Utente": user,
                        "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                        "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                    }])
                    conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

        with col_foto:
            f_nome = "Noli.jpg" if casa == "NOLI" else "Limone.jpg"
            if os.path.exists(f_nome): st.image(f_nome, width=300)

    # --- TAB 2: STATO & VOTI ---
    with tab2:
        st.header("Situazione e Gestione")
        
        # --- CONTO ALLA ROVESCIA ---
        if not mie_conf.empty:
            for _, r in mie_conf.iterrows():
                d_i = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                diff = (d_i - datetime.today().date()).days
                if diff > 0:
                    st.success(f"⏳ Mancano **{diff} giorni** alla tua vacanza a **{r['Casa']}**! (dal {r['Data_Inizio']})")
                elif diff == 0:
                    st.balloons()
                    st.success(f"🎒 **È OGGI!** Buona vacanza a {r['Casa']}!")

        if not df.empty:
            df_view = df.copy()
            df_view['Approvazioni'] = df_view['Voti_Ok'].apply(lambda v: f"{len([x for x in str(v).split(',') if x.strip()])}/3")
            st.dataframe(df_view[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato', 'Approvazioni', 'Note']], use_container_width=True)
            
            st.divider()
            c_voti, c_gest = st.columns(2)
            
            with c_voti:
                st.subheader("🗳️ Vota Richieste")
                for idx, row in df.iterrows():
                    if row['Utente'] != user and row['Stato'] == "In Attesa":
                        votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                        if user not in votanti:
                            if st.button(f"Approva {row['Utente']} ({row['Data_Inizio']})", key=f"v_{idx}"):
                                votanti.append(user)
                                df.at[idx, 'Voti_Ok'] = ", ".join(votanti)
                                if len(votanti) >= 3: df.at[idx, 'Stato'] = "Confermata"
                                conn.update(worksheet="Prenotazioni", data=df)
                                st.rerun()
                        else: st.write(f"✅ Hai approvato {row['Utente']}")

            with c_gest:
                st.subheader("🗑️ Mie Prenotazioni")
                for idx, row in df[df['Utente'] == user].iterrows():
                    if f"del_{idx}" not in st.session_state:
                        if st.button(f"Elimina {row['Casa']} ({row['Data_Inizio']})", key=f"btn_d_{idx}"):
                            st.session_state[f"del_{idx}"] = True
                            st.rerun()
                    else:
                        st.error("Confermi?")
                        if st.button("SÌ, Cancella", key=f"si_{idx}"):
                            df = df.drop(idx)
                            conn.update(worksheet="Prenotazioni", data=df)
                            del st.session_state[f"del_{idx}"]
                            st.rerun()
                        if st.button("Annulla", key=f"no_{idx}"):
                            del st.session_state[f"del_{idx}"]
                            st.rerun()

    # --- TAB 3: INFO & STATISTICHE ---
    with tab3:
        st.header("📊 Statistiche di Famiglia")
        if not df.empty:
            df_conf = df[df['Stato'] == "Confermata"].copy()
            if not df_conf.empty:
                # Calcolo giorni totali per utente
                def calc_days(row):
                    d1 = datetime.strptime(row['Data_Inizio'], '%d/%m/%Y')
                    d2 = datetime.strptime(row['Data_Fine'], '%d/%m/%Y')
                    return (d2 - d1).days
                
                df_conf['Giorni'] = df_conf.apply(calc_days, axis=1)
                classifica = df_conf.groupby('Utente')['Giorni'].sum().sort_values(ascending=False)
                casa_fav = df_conf.groupby('Casa').size().idxmax()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🏆 Re delle Vacanze")
                    for i, (nom, gg) in enumerate(classifica.items()):
                        st.write(f"{i+1}. **{nom}**: {gg} giorni totali")
                with col2:
                    st.subheader("🏠 Casa Preferita")
                    st.write(f"La meta più prenotata è: **{casa_fav}**")
            else:
                st.info("Statistiche disponibili dopo le prime conferme.")
        
        st.divider()
        st.header("📸 Le Case")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🏖️ NOLI")
            if os.path.exists("Noli.jpg"): st.image("Noli.jpg", use_container_width=True)
        with c2:
            st.subheader("🏔️ LIMONE")
            if os.path.exists("Limone.jpg"): st.image("Limone.jpg", use_container_width=True)

else:
    st.title("🏠 Family Booking App")
    st.info("Accedi dalla sidebar.")
