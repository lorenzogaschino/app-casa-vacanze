import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
from streamlit_calendar import calendar
import time
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- STILE CSS ---
st.markdown("""
    <style>
    button[data-baseweb="tab"] p { font-size: 20px !important; font-weight: 800 !important; color: #007bff !important; }
    .stAlert { border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNESSIONE E CACHE ---
def get_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(worksheet="Prenotazioni", ttl=0)
    data = data.dropna(axis=1, how='all')
    for col in ['Voti_Ok', 'Note']:
        if col in data.columns:
            data[col] = data[col].fillna("").astype(str)
        else:
            data[col] = ""
    return data

def check_overlap(start1, end1, start2, end2):
    return start1 <= end2 and start2 <= end1

# --- CONFIGURAZIONE UTENTI ---
utenti_config = {
    "Anita": {"pin": "1111", "color": "#FF4B4B"},   # Rosso
    "Chiara": {"pin": "4444", "color": "#FFC0CB"},  # Rosa
    "Lorenzo": {"pin": "1234", "color": "#1C83E1"}, # Blu
    "Gianluca": {"pin": "1191", "color": "#28A745"} # Verde
}

# --- LOGIN ---
st.sidebar.title("🔐 Accesso Family")
user = st.sidebar.selectbox("Chi sei?", ["-- Seleziona --"] + list(utenti_config.keys()))
password = st.sidebar.text_input("PIN", type="password")

if user != "-- Seleziona --" and password == utenti_config[user]["pin"]:
    df = get_data()
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Notifica Toast per soggiorni confermati
    mie_conf = df[(df['Utente'] == user) & (df['Stato'] == "Confermata")]
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 PRENOTA", "📊 STATO & VOTI", "🗓️ CALENDARIO", "📈 STATISTICHE"])

    # --- TAB 1: PRENOTAZIONE ---
    with tab1:
        st.header("Nuova Prenotazione")
        col_form, col_foto = st.columns([2, 1])
        with col_form:
            casa = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
            
            # Box Disponibilità (Rosso/Giallo)
            p_casa = df[df['Casa'] == casa].copy()
            g_conf, g_rich = [], []
            for _, r in p_casa.iterrows():
                try:
                    di, df_ = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date(), datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date()
                    info = f"{di.strftime('%d/%m')} al {df_.strftime('%d/%m')} ({r['Utente']})"
                    if r['Stato'] == "Confermata": g_conf.append((di, df_, info))
                    else: g_rich.append((di, df_, info))
                except: continue
            
            if g_conf: st.error(f"🚫 **NON DISPONIBILE:** {', '.join([x[2] for x in g_conf])}")
            if g_rich: st.warning(f"🟡 **GIÀ RICHIESTI:** {', '.join([x[2] for x in g_rich])}")

            d_in = st.date_input("Check-in", value=datetime.today().date() + timedelta(days=1), min_value=datetime.today().date())
            d_out = st.date_input("Check-out", value=d_in + timedelta(days=1), min_value=d_in)
            
            notti = (d_out - d_in).days
            if notti > 0: st.info(f"🌙 Stai prenotando per **{notti}** notti.")
            note = st.text_area("Note (es. 'Saremo in 4')", placeholder="Scrivi qui...")

            # Controllo conflitti per tasto invio
            c_conf, c_rich, nome_c = False, False, ""
            for s, e, i in g_conf:
                if check_overlap(d_in, d_out, s, e): c_conf, nome_c = True, i.split('(')[-1].replace(')', ''); break
            if not c_conf:
                for s, e, i in g_rich:
                    if check_overlap(d_in, d_out, s, e): c_rich, nome_c = True, i.split('(')[-1].replace(')', ''); break

            if c_conf:
                st.error(f"❌ Impossibile procedere: già confermata a **{nome_c}**.")
            else:
                btn_label = "🚀 PROCEDI COMUNQUE" if c_rich else "🚀 INVIA RICHIESTA"
                if c_rich: st.warning(f"⚖️ {nome_c} ha già chiesto queste date.")
                if st.button(btn_label):
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
            t_utenti = set(utenti_config.keys())
            def analizza(row):
                votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                mancano = list(t_utenti - (set(votanti) | {row['Utente']}))
                return f"{len(votanti)}/3", ", ".join(votanti), ", ".join(mancano)
            
            res = df_view.apply(analizza, axis=1, result_type='expand')
            df_view['Voti'], df_view['Approvato da'], df_view['Mancano'] = res[0], res[1], res[2]
            st.dataframe(df_view[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato', 'Voti', 'Approvato da', 'Mancano', 'Note']], use_container_width=True)
            
            st.divider()
            c_v, c_g = st.columns(2)
            with c_v:
                st.subheader("🗳️ Vota")
                for idx, row in df.iterrows():
                    if row['Utente'] != user and row['Stato'] == "In Attesa":
                        votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                        if user not in votanti:
                            if st.button(f"Approva {row['Utente']} ({row['Data_Inizio']})", key=f"v_{idx}"):
                                votanti.append(user)
                                df.at[idx, 'Voti_Ok'] = ", ".join(votanti)
                                if len(votanti) >= 3: df.at[idx, 'Stato'] = "Confermata"
                                conn.update(worksheet="Prenotazioni", data=df); st.rerun()
                        else: st.info(f"✅ Hai approvato {row['Utente']}")
            with c_g:
                st.subheader("🗑️ Le Mie")
                for idx, row in df[df['Utente'] == user].iterrows():
                    k_del = f"del_mem_{idx}"
                    if k_del not in st.session_state:
                        if st.button(f"Elimina {row['Casa']} ({row['Data_Inizio']})", key=f"d_b_{idx}"):
                            st.session_state[k_del] = True; st.rerun()
                    else:
                        st.error("Confermi?")
                        if st.button("SÌ", key=f"y_{idx}", type="primary"):
                            df = df.drop(idx); conn.update(worksheet="Prenotazioni", data=df)
                            del st.session_state[k_del]; st.rerun()
                        if st.button("NO", key=f"n_{idx}"): del st.session_state[k_del]; st.rerun()

    # --- TAB 3: CALENDARIO ---
    with tab3:
        st.header("🗓️ Calendario Occupazione")
        st.markdown("**Legenda:** 🔴 Anita | 🌸 Chiara | 🔵 Lorenzo | 🟢 Gianluca")
        evs = []
        for _, r in df[df['Stato'] == "Confermata"].iterrows():
            try:
                start = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                end = datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date() + timedelta(days=1)
                evs.append({
                    "title": f"{r['Casa']} ({r['Utente']})", "start": start.isoformat(), "end": end.isoformat(),
                    "backgroundColor": utenti_config.get(r['Utente'], {}).get("color", "#CCC"),
                    "borderColor": utenti_config.get(r['Utente'], {}).get("color", "#CCC"), "allDay": True
                })
            except: continue
        calendar(events=evs, options={"initialView": "dayGridMonth", "locale": "it"}, key="family_cal")

    # --- TAB 4: STATISTICHE ---
    with tab4:
        st.header("📊 Statistiche")
        df_c = df[df['Stato'] == "Confermata"].copy()
        if not df_c.empty:
            def g_calc(r):
                try: return (datetime.strptime(r['Data_Fine'], '%d/%m/%Y') - datetime.strptime(r['Data_Inizio'], '%d/%m/%Y')).days
                except: return 0
            df_c['GG'] = df_c.apply(g_calc, axis=1)
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🏆 Re delle Vacanze")
                for n, g in df_c.groupby('Utente')['GG'].sum().sort_values(ascending=False).items(): st.write(f"**{n}**: {g} giorni")
            with c2:
                st.subheader("🏠 Meta Preferita")
                s_c = df_c.groupby('Casa')['GG'].sum()
                st.write(f"**{s_c.idxmax()}** ({s_c.max()} giorni)")
        else: st.info("Nessuna prenotazione confermata.")

else:
    st.title("🏠 Family Booking"); st.info("Accedi con il PIN")
