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
    button[data-baseweb="tab"] p { font-size: 20px !important; font-weight: 800 !important; color: #007bff !important; }
    .stAlert { border-radius: 12px; }
    .legenda-box { padding: 10px; border-radius: 5px; margin: 5px; display: inline-block; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNESSIONE DATABASE ---
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

# --- CONFIGURAZIONE UTENTI E COLORI ---
utenti_config = {
    "Anita": {"pin": "1111", "color": "#FF4B4B", "label": "🔴 Rosso"},
    "Chiara": {"pin": "4444", "color": "#FFC0CB", "label": "🌸 Rosa"},
    "Lorenzo": {"pin": "1234", "color": "#1C83E1", "label": "🔵 Blu"},
    "Gianluca": {"pin": "1191", "color": "#28A745", "label": "🟢 Verde"}
}

# --- LOGIN ---
st.sidebar.title("🔐 Accesso Family")
user = st.sidebar.selectbox("Chi sei?", ["-- Seleziona --"] + list(utenti_config.keys()))
password = st.sidebar.text_input("PIN", type="password")

if user != "-- Seleziona --" and password == utenti_config[user]["pin"]:
    df = get_data()
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 PRENOTA", "📊 STATO & VOTI", "🗓️ CALENDARIO STABILE", "📈 STATISTICHE"])

    # --- TAB 1: PRENOTAZIONE (RIPRISTINATO CON FOTO) ---
    with tab1:
        st.header("Nuova Prenotazione")
        col_form, col_foto = st.columns([2, 1])
        with col_form:
            casa = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
            
            # Box Disponibilità dinamici
            p_casa = df[df['Casa'] == casa].copy()
            g_conf, g_rich = [], []
            for _, r in p_casa.iterrows():
                try:
                    di = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                    df_ = datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date()
                    info = f"{di.strftime('%d/%m')} al {df_.strftime('%d/%m')} ({r['Utente']})"
                    if r['Stato'] == "Confermata": g_conf.append(info)
                    else: g_rich.append(info)
                except: continue
            
            if g_conf: st.error(f"🚫 **NON DISPONIBILE:** {', '.join(g_conf)}")
            if g_rich: st.warning(f"🟡 **RICHIESTE IN CORSO:** {', '.join(g_rich)}")

            d_in = st.date_input("Check-in", value=datetime.today().date() + timedelta(days=1))
            d_out = st.date_input("Check-out", value=d_in + timedelta(days=1))
            notti = (d_out - d_in).days
            if notti > 0: st.info(f"🌙 Soggiorno di **{notti}** notti.")
            note = st.text_area("Note", placeholder="Esempio: Porto il gatto...")

            if st.button("🚀 INVIA RICHIESTA"):
                nuova = pd.DataFrame([{
                    "ID": str(datetime.now().timestamp()), "Casa": casa, "Utente": user,
                    "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                    "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                }])
                conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                st.balloons(); time.sleep(1); st.rerun()

        with col_foto:
            # RIPRISTINO IMMAGINI
            f_nome = "Noli.jpg" if casa == "NOLI" else "Limone.jpg"
            if os.path.exists(f_nome):
                st.image(f_nome, caption=f"Vista di {casa}", use_container_width=True)
            else:
                st.info(f"Carica {f_nome} su GitHub per vedere la foto!")

    # --- TAB 2: STATO & VOTI (FUNZIONALITÀ COMPLETE) ---
    with tab2:
        st.header("Situazione e Gestione")
        if not df.empty:
            df_view = df.copy()
            t_utenti = set(utenti_config.keys())
            def analizza_voti(row):
                votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                mancano = list(t_utenti - (set(votanti) | {row['Utente']}))
                return f"{len(votanti)}/3", ", ".join(votanti), ", ".join(mancano)
            
            res = df_view.apply(analizza_voti, axis=1, result_type='expand')
            df_view['Voti'], df_view['Approvato da'], df_view['Mancano'] = res[0], res[1], res[2]
            st.dataframe(df_view[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato', 'Voti', 'Approvato da', 'Mancano', 'Note']], use_container_width=True)
            
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
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
            with c2:
                st.subheader("🗑️ Mie Prenotazioni")
                for idx, row in df[df['Utente'] == user].iterrows():
                    if st.button(f"Elimina {row['Casa']} ({row['Data_Inizio']})", key=f"d_{idx}"):
                        df = df.drop(idx); conn.update(worksheet="Prenotazioni", data=df); st.rerun()

    # --- TAB 3: CALENDARIO STABILE (NIENTE SFARFALLIO) ---
    with tab3:
        st.header("🗓️ Calendario Occupazione")
        st.write("Visualizzazione dei giorni confermati (Legenda in alto)")
        
        # Legenda colorata
        leg_cols = st.columns(4)
        for i, (u, cfg) in enumerate(utenti_config.items()):
            leg_cols[i].markdown(f"<div style='background-color:{cfg['color']}; padding:10px; border-radius:5px; text-align:center; color:white;'>{u}</div>", unsafe_allow_html=True)
        
        # Creazione di una lista di date occupate
        occupied_dates = {}
        for _, r in df[df['Stato'] == "Confermata"].iterrows():
            try:
                start = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                end = datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date()
                curr = start
                while curr <= end:
                    occupied_dates[curr] = {"user": r['Utente'], "casa": r['Casa']}
                    curr += timedelta(days=1)
            except: continue

        # Mostra i prossimi 4 mesi in tabelle
        start_month = datetime.today().replace(day=1).date()
        for m in range(4):
            month_to_show = (start_month + timedelta(days=m*31)).replace(day=1)
            st.subheader(month_to_show.strftime("%B %Y").upper())
            
            days_in_month = pd.date_range(start=month_to_show, periods=month_to_show.day + 30, freq='D')
            days_in_month = [d.date() for d in days_in_month if d.month == month_to_show.month]
            
            # Creiamo una griglia stile calendario
            cols = st.columns(7)
            days_labels = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
            for i, l in enumerate(days_labels): cols[i].caption(l)
            
            # Offset per il primo giorno del mese
            first_weekday = month_to_show.weekday()
            curr_col = first_weekday
            
            for d in days_in_month:
                with cols[curr_col]:
                    if d in occupied_dates:
                        u = occupied_dates[d]['user']
                        c = occupied_dates[d]['casa']
                        color = utenti_config.get(u, {}).get("color", "#EEE")
                        st.markdown(f"<div style='background-color:{color}; color:white; padding:5px; border-radius:3px; text-align:center; font-size:12px; margin-bottom:2px;'>{d.day}<br>{c[:1]}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='background-color:#f0f2f6; padding:5px; border-radius:3px; text-align:center; font-size:12px; margin-bottom:2px;'>{d.day}</div>", unsafe_allow_html=True)
                
                curr_col += 1
                if curr_col > 6: curr_col = 0

    # --- TAB 4: STATISTICHE (CORRETTE) ---
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
                classifica = df_c.groupby('Utente')['GG'].sum().sort_values(ascending=False)
                for n, g in classifica.items(): st.write(f"**{n}**: {g} giorni totali")
            with c2:
                st.subheader("🏠 Meta Preferita")
                s_c = df_c.groupby('Casa')['GG'].sum()
                st.write(f"**{s_c.idxmax()}** ({s_c.max()} giorni totali)")

else:
    st.title("🏠 Family Booking"); st.info("Inserisci il PIN nella sidebar per accedere.")
