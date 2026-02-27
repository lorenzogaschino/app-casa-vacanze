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
    .cal-table { width:100%; table-layout: fixed; border-spacing: 4px; border-collapse: separate; }
    .cal-td { text-align:center; height:60px; border-radius:5px; border:1px solid #eee; vertical-align:middle; padding:0 !important; overflow:hidden; }
    .split-container { display: flex; height: 100%; width: 100%; }
    .split-half { flex: 1; display: flex; flex-direction: column; justify-content: center; align-items: center; height: 100%; }
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

# --- CONFIGURAZIONE UTENTI E COLORI ---
utenti_config = {
    "Anita": {"pin": "1111", "color": "#FF4B4B"},   # Rosso
    "Chiara": {"pin": "4444", "color": "#FFC0CB"},  # Rosa
    "Lorenzo": {"pin": "1234", "color": "#1C83E1"}, # Blu
    "Gianluca": {"pin": "1191", "color": "#28A745"} # Verde
}
icone_case = {"LIMONE": "🏔️", "NOLI": "🏖️"}

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
            casa_scelta = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
            d_in = st.date_input("Check-in", value=datetime.today().date() + timedelta(days=1))
            d_out = st.date_input("Check-out", value=d_in + timedelta(days=1))
            note = st.text_area("Note")
            if st.button("🚀 INVIA RICHIESTA"):
                nuova = pd.DataFrame([{
                    "ID": str(datetime.now().timestamp()), "Casa": casa_scelta, "Utente": user,
                    "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                    "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                }])
                conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                st.balloons(); time.sleep(1); st.rerun()
        with col_foto:
            f_nome = "Noli.jpg" if casa_scelta == "NOLI" else "Limone.jpg"
            if os.path.exists(f_nome): st.image(f_nome, use_container_width=True)

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
            if st.button("🗑️ Elimina le mie prenotazioni"):
                df = df[df['Utente'] != user]
                conn.update(worksheet="Prenotazioni", data=df); st.rerun()

    # --- TAB 3: CALENDARIO (CON GESTIONE SOVRAPPOSIZIONI) ---
    with tab3:
        st.header("🗓️ Calendario Occupazione")
        
        # Mappatura date: {data: [lista_prenotazioni]}
        occupied_dates = {}
        for _, r in df[df['Stato'] == "Confermata"].iterrows():
            try:
                start = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                end = datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date()
                curr = start
                while curr <= end:
                    if curr not in occupied_dates: occupied_dates[curr] = []
                    occupied_dates[curr].append({"user": r['Utente'], "casa": r['Casa']})
                    curr += timedelta(days=1)
            except: continue

        start_month = datetime.today().replace(day=1).date()
        for m in range(4):
            month_to_show = (start_month + timedelta(days=m*31)).replace(day=1)
            st.subheader(month_to_show.strftime("%B %Y").upper())
            
            if month_to_show.month == 12: next_m = month_to_show.replace(year=month_to_show.year + 1, month=1)
            else: next_m = month_to_show.replace(month=month_to_show.month + 1)
            last_day = (next_m - timedelta(days=1)).day
            first_wd = month_to_show.weekday()

            html_cal = "<table class='cal-table'><thead><tr style='text-align:center; font-size:0.7em; color:gray;'><th>L</th><th>M</th><th>M</th><th>G</th><th>V</th><th>S</th><th>D</th></tr></thead><tbody><tr>"
            for _ in range(first_wd): html_cal += "<td></td>"
            
            curr_col = first_wd
            for day in range(1, last_day + 1):
                d_obj = month_to_show.replace(day=day)
                cell_content = ""
                
                if d_obj in occupied_dates:
                    preds = occupied_dates[d_obj]
                    if len(preds) == 1:
                        # Una sola prenotazione
                        p = preds[0]
                        color = utenti_config.get(p['user'], {}).get("color", "#EEE")
                        icon = icone_case.get(p['casa'], "")
                        cell_content = f"""<div style='background-color:{color}; color:white; height:100%; display:flex; flex-direction:column; justify-content:center;'>
                                            <div style='font-size:10px;'>{day}</div><div>{icon}</div></div>"""
                    else:
                        # SOVRAPPOSIZIONE (Split verticale)
                        cell_content = f"<div class='split-container'><div style='position:absolute; width:100%; font-size:10px; color:white; z-index:10; text-align:center;'>{day}</div>"
                        for p in preds:
                            color = utenti_config.get(p['user'], {}).get("color", "#EEE")
                            icon = icone_case.get(p['casa'], "")
                            cell_content += f"<div class='split-half' style='background-color:{color}; color:white;'>{icon}</div>"
                        cell_content += "</div>"
                else:
                    cell_content = f"<div style='color:#ccc; font-size:10px; padding-top:5px;'>{day}</div>"

                html_cal += f"<td class='cal-td' style='position:relative;'>{cell_content}</td>"
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
            st.subheader("🏆 Re delle Vacanze")
            for n, g in df_c.groupby('Utente')['GG'].sum().sort_values(ascending=False).items():
                st.write(f"**{n}**: {g} giorni")

else:
    st.title("🏠 Family Booking"); st.info("Esegui il login nella sidebar.")
