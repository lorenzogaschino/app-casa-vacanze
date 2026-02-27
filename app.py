import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar # <--- Nuova libreria
import time
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- STILE CSS PERSONALIZZATO ---
st.markdown("""
    <style>
    button[data-baseweb="tab"] p { font-size: 20px !important; font-weight: 800 !important; color: #007bff !important; }
    button[data-baseweb="tab"] { padding: 10px 20px !important; }
    .stAlert { border-radius: 12px; }
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

# --- CONFIGURAZIONE UTENTI E COLORI ---
utenti_config = {
    "Anita": {"pin": "1111", "color": "#FF0000"},   # Rosso
    "Chiara": {"pin": "4444", "color": "#FFC0CB"},  # Rosa
    "Lorenzo": {"pin": "1234", "color": "#0000FF"}, # Blu
    "Gianluca": {"pin": "1191", "color": "#008000"} # Verde
}

# --- LOGIN ---
st.sidebar.title("🔐 Accesso Family")
user = st.sidebar.selectbox("Chi sei?", ["-- Seleziona --"] + list(utenti_config.keys()))
password = st.sidebar.text_input("PIN", type="password")

if user != "-- Seleziona --" and password == utenti_config[user]["pin"]:
    df = get_data()
    
    # Notifica Toast
    mie_conf = df[(df['Utente'] == user) & (df['Stato'] == "Confermata")]
    if not mie_conf.empty:
        st.toast(f"🎉 Ciao {user}!", icon="✅")

    # --- NAVIGAZIONE TAB ---
    tab1, tab2, tab4, tab3 = st.tabs(["📅 PRENOTA", "📊 STATO & VOTI", "🗓️ CALENDARIO", "📸 INFO & STATS"])

    # --- TAB 1: PRENOTAZIONE ---
    with tab1:
        st.header("Nuova Prenotazione")
        col_form, col_foto = st.columns([2, 1])
        with col_form:
            casa = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
            prenotazioni_casa = df[df['Casa'] == casa].copy()
            g_conf_list = []
            g_rich_list = []
            if not prenotazioni_casa.empty:
                for _, r in prenotazioni_casa.iterrows():
                    try:
                        d_i = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                        d_f = datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date()
                        txt = f"{d_i.strftime('%d/%m')} al {d_f.strftime('%d/%m')} ({r['Utente']})"
                        if r['Stato'] == "Confermata": g_conf_list.append((d_i, d_f, txt))
                        else: g_rich_list.append((d_i, d_f, txt))
                    except: continue

            if g_conf_list: st.error(f"🚫 **NON DISPONIBILE:** {', '.join([x[2] for x in g_conf_list])}")
            if g_rich_list: st.warning(f"🟡 **RICHIESTE IN CORSO:** {', '.join([x[2] for x in g_rich_list])}")

            d_in = st.date_input("Check-in", value=datetime.today().date() + timedelta(days=1), min_value=datetime.today().date())
            d_out = st.date_input("Check-out", value=d_in + timedelta(days=1), min_value=d_in)
            notti = (d_out - d_in).days
            if notti > 0: st.info(f"🌙 Stai prenotando per **{notti}** notti.")
            note = st.text_area("Note", placeholder="Dettagli...")

            if st.button("🚀 INVIA RICHIESTA"):
                nuova = pd.DataFrame([{
                    "ID": str(datetime.now().timestamp()), "Casa": casa, "Utente": user,
                    "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                    "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                }])
                conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                st.balloons(); time.sleep(1); st.rerun()

        with col_foto:
            f_nome = "Noli.jpg" if casa == "NOLI" else "Limone.jpg"
            if os.path.exists(f_nome): st.image(f_nome, width=300)

    # --- TAB 2: STATO & VOTI ---
    with tab2:
        st.header("Situazione e Gestione")
        if not df.empty:
            df_view = df.copy()
            tutti_utenti_lista = set(utenti_config.keys())
            def info_voti(row):
                votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                esclusi = set(votanti) | {row['Utente']}
                mancanti = ", ".join(list(tutti_utenti_lista - esclusi))
                return f"{len(votanti)}/3", ", ".join(votanti), mancanti

            res = df_view.apply(info_voti, axis=1, result_type='expand')
            df_view['Voti'], df_view['Già Approvato'], df_view['Mancano'] = res[0], res[1], res[2]
            st.dataframe(df_view[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato', 'Voti', 'Già Approvato', 'Mancano', 'Note']], use_container_width=True)
            
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
                                conn.update(worksheet="Prenotazioni", data=df); st.rerun()

            with c_gest:
                st.subheader("🗑️ Le Mie Prenotazioni")
                for idx, row in df[df['Utente'] == user].iterrows():
                    if st.button(f"Elimina {row['Casa']} ({row['Data_Inizio']})", key=f"d_b_{idx}"):
                        df = df.drop(idx); conn.update(worksheet="Prenotazioni", data=df); st.rerun()

    # --- TAB 4: CALENDARIO RIASSUNTIVO (NUOVO) ---
    with tab4:
        st.header("🗓️ Calendario Occupazione")
        st.markdown("**Legenda:** 🔴 Anita | 🌸 Chiara | 🔵 Lorenzo | 🟢 Gianluca")
        
        calendar_events = []
        for _, row in df[df['Stato'] == "Confermata"].iterrows():
            try:
                # Trasformiamo le date nel formato ISO per il calendario
                d_i = datetime.strptime(row['Data_Inizio'], '%d/%m/%Y').date()
                d_f = datetime.strptime(row['Data_Fine'], '%d/%m/%Y').date() + timedelta(days=1)
                
                calendar_events.append({
                    "title": f"{row['Casa']} - {row['Utente']}",
                    "start": d_i.isoformat(),
                    "end": d_f.isoformat(),
                    "color": utenti_config.get(row['Utente'], {}).get("color", "#CCCCCC"),
                    "allDay": True
                })
            except: continue

        calendar_options = {
            "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,dayGridWeek"},
            "initialView": "dayGridMonth",
            "locale": "it",
            "selectable": False, # Non editabile
            "editable": False
        }
        
        calendar(events=calendar_events, options=calendar_options)

    # --- TAB 3: INFO & STATS ---
    with tab3:
        st.header("📊 Statistiche")
        df_conf = df[df['Stato'] == "Confermata"].copy()
        if not df_conf.empty:
            def calc_gg(r):
                try:
                    d1 = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y')
                    d2 = datetime.strptime(r['Data_Fine'], '%d/%m/%Y')
                    return (d2 - d1).days
                except: return 0
            df_conf['GG_Reali'] = df_conf.apply(calc_gg, axis=1)
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🏆 Re delle Vacanze")
                for n, g in df_conf.groupby('Utente')['GG_Reali'].sum().sort_values(ascending=False).items():
                    st.write(f"**{n}**: {g} giorni totali")
            with c2:
                st.subheader("🏠 Meta più scelta")
                stats_case = df_conf.groupby('Casa')['GG_Reali'].sum()
                st.write(f"**{stats_case.idxmax()}** con {stats_case.max()} giorni")
        
        st.divider()
        c_n, c_l = st.columns(2)
        with c_n: 
            st.subheader("NOLI"); st.image("Noli.jpg", use_container_width=True) if os.path.exists("Noli.jpg") else None
        with c_l: 
            st.subheader("LIMONE"); st.image("Limone.jpg", use_container_width=True) if os.path.exists("Limone.jpg") else None

else:
    st.title("🏠 Family Booking"); st.info("Login sidebar richiesto.")
