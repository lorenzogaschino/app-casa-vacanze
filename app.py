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
    /* Stile per le celle del calendario */
    .cal-cell {
        border-radius: 5px; 
        text-align: center; 
        height: 50px; 
        vertical-align: middle; 
        border: 1px solid #efefef;
        font-family: sans-serif;
    }
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
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 PRENOTA", "📊 STATO & VOTI", "🗓️ CALENDARIO", "📈 STATISTICHE"])

    # --- TAB 1: PRENOTAZIONE ---
    with tab1:
        st.header("Nuova Prenotazione")
        col_form, col_foto = st.columns([2, 1])
        with col_form:
            casa = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
            
            p_casa = df[df['Casa'] == casa].copy()
            g_conf, g_rich = [], []
            for _, r in p_casa.iterrows():
                try:
                    di = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                    df_ = datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date()
                    info = f"{di.strftime('%d/%m')} al {df_.strftime('%d/%m')} ({r['Utente']})"
                    if r['Stato'] == "Confermata": g_conf.append((di, df_, info))
                    else: g_rich.append((di, df_, info))
                except: continue
            
            if g_conf: st.error(f"🚫 **NON DISPONIBILE:** {', '.join([x[2] for x in g_conf])}")
            if g_rich: st.warning(f"🟡 **GIÀ RICHIESTI:** {', '.join([x[2] for x in g_rich])}")

            d_in = st.date_input("Check-in", value=datetime.today().date() + timedelta(days=1))
            d_out = st.date_input("Check-out", value=d_in + timedelta(days=1))
            
            notti = (d_out - d_in).days
            if notti > 0: st.info(f"🌙 Stai prenotando per **{notti}** notti.")
            note = st.text_area("Note (es. 'Saremo in 4')", placeholder="Scrivi qui...")

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
            if os.path.exists(f_nome):
                st.image(f_nome, caption=f"Vista di {casa}", use_container_width=True)

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
            with c_g:
                st.subheader("🗑️ Le Mie")
                for idx, row in df[df['Utente'] == user].iterrows():
                    if st.button(f"Elimina {row['Casa']} ({row['Data_Inizio']})", key=f"d_b_{idx}"):
                        df = df.drop(idx); conn.update(worksheet="Prenotazioni", data=df); st.rerun()

    # --- TAB 3: CALENDARIO (TABELLA HTML STABILE) ---
    with tab3:
        st.header("🗓️ Calendario Occupazione")
        
        # Legenda Leggera
        leg_cols = st.columns(4)
        for i, (u, cfg) in enumerate(utenti_config.items()):
            leg_cols[i].markdown(f"<div style='background-color:{cfg['color']}; padding:8px; border-radius:5px; text-align:center; color:white; font-size:14px;'>{u}</div>", unsafe_allow_html=True)
        
        st.write("")
        icone_case = {"LIMONE": "🏔️", "NOLI": "🏖️"}

        # Dizionario date occupate
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

        # Visualizzazione Mesi
        start_month = datetime.today().replace(day=1).date()
        for m in range(4):
            month_to_show = (start_month + timedelta(days=m*31)).replace(day=1)
            st.subheader(month_to_show.strftime("%B %Y").upper())
            
            # Calcolo giorni
            if month_to_show.month == 12: next_m = month_to_show.replace(year=month_to_show.year + 1, month=1)
            else: next_m = month_to_show.replace(month=month_to_show.month + 1)
            last_day = (next_m - timedelta(days=1)).day
            first_wd = month_to_show.weekday()

            # Costruzione Tabella
            html_cal = "<table style='width:100%; table-layout: fixed; border-spacing: 4px; border-collapse: separate;'><thead><tr style='text-align:center; font-size:0.7em; color:gray;'><th>L</th><th>M</th><th>M</th><th>G</th><th>V</th><th>S</th><th>D</th></tr></thead><tbody><tr>"
            
            for _ in range(first_wd): html_cal += "<td></td>"
            
            curr_col = first_wd
            for day in range(1, last_day + 1):
                d_obj = month_to_show.replace(day=day)
                if d_obj in occupied_dates:
                    u = occupied_dates[d_obj]['user']
                    c = occupied_dates[d_obj]['casa']
                    color = utenti_config.get(u, {}).get("color", "#EEE")
                    icona = icone_case.get(c, "")
                    style = f"background-color:{color}; color:white;"
                    content = f"<div style='font-size:10px;'>{day}</div><div style='font-size:16px;'>{icona}</div>"
                else:
                    style = "background-color:#f9f9f9; color:#ccc;"
                    content = f"<div style='font-size:10px;'>{day}</div><div style='height:16px;'></div>"

                html_cal += f"<td style='{style} text-align:center; height:50px; border-radius:5px; border:1px solid #eee;'>{content}</td>"
                
                curr_col += 1
                if curr_col > 6:
                    html_cal += "</tr><tr>"
                    curr_col = 0
            
            if curr_col != 0:
                for _ in range(7 - curr_col): html_cal += "<td></td>"
            
            html_cal += "</tr></tbody></table>"
            st.markdown(html_cal, unsafe_allow_html=True)
            st.divider()

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
                st.write(f"**{s_c.idxmax()}** ({s_c.max()} giorni totali)")
else:
    st.title("🏠 Family Booking"); st.info("Esegui il login nella sidebar.")
