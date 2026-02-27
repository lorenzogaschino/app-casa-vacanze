import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- STILE CSS ---
st.markdown("""
    <style>
    button[data-baseweb="tab"] p { font-size: 16px !important; font-weight: bold !important; }
    .cal-table { width:100%; table-layout: fixed; border-spacing: 1px; border-collapse: separate; }
    .cal-td { text-align:center; height:45px; border-radius:3px; border:1px solid #f0f0f0; padding:0 !important; position:relative; font-size: 11px; }
    .day-num { position: absolute; top: 1px; left: 2px; font-size: 9px; color: #666; z-index: 5; }
    .full-cell { height: 100%; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNESSIONE DATI ---
def get_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(worksheet="Prenotazioni", ttl=0)
    data = data.dropna(axis=1, how='all')
    for col in ['Voti_Ok', 'Note', 'Data_Inizio', 'Data_Fine', 'Stato']:
        if col in data.columns: data[col] = data[col].fillna("").astype(str)
    return data

# --- CONFIGURAZIONE ---
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
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 PRENOTA", "📊 GESTIONE", "🗓️ CALENDARIO", "📈 STATS"])

    # --- TAB 1: PRENOTA ---
    with tab1:
        st.header("Nuova Prenotazione")
        oggi = datetime.now().date()
        col_form, col_foto = st.columns([2, 1])
        with col_form:
            casa_scelta = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
            d_in = st.date_input("Check-in", value=oggi + timedelta(days=1), min_value=oggi)
            d_out = st.date_input("Check-out", value=d_in + timedelta(days=1), min_value=d_in + timedelta(days=1))
            note = st.text_area("Note")
            if st.button("🚀 INVIA RICHIESTA"):
                nuova = pd.DataFrame([{
                    "ID": str(datetime.now().timestamp()), "Casa": casa_scelta, "Utente": user,
                    "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                    "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                }])
                conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                st.success("Richiesta inviata!"); time.sleep(1); st.rerun()
        with col_foto:
            f = f"{casa_scelta.capitalize()}.jpg"
            if os.path.exists(f): st.image(f, use_container_width=True)

    # --- TAB 2: GESTIONE ---
    with tab2:
        st.header("Situazione e Voti")
        if not df.empty:
            all_users = set(utenti_config.keys())
            def get_voti_details(row):
                votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                mancano = list(all_users - (set(votanti) | {row['Utente']}))
                return ", ".join(votanti), ", ".join(mancano)
            
            df[['Già Approvato', 'Mancano']] = df.apply(get_voti_details, axis=1, result_type='expand')
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato', 'Già Approvato', 'Mancano']], use_container_width=True)
            
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🗳️ Approva")
                for idx, row in df.iterrows():
                    if row['Utente'] != user and row['Stato'] == "In Attesa":
                        votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                        if user not in votanti:
                            # Label richiesta: Approva - [casa] - [date]
                            label = f"Approva - {row['Casa']} - ({row['Data_Inizio']} - {row['Data_Fine']})"
                            if st.button(label, key=f"v_{idx}"):
                                votanti.append(user)
                                df.at[idx, 'Voti_Ok'] = ", ".join(votanti)
                                if len(votanti) >= 3: df.at[idx, 'Stato'] = "Confermata"
                                conn.update(worksheet="Prenotazioni", data=df); st.rerun()
            with c2:
                st.subheader("🗑️ Elimina le tue")
                for idx, row in df[df['Utente'] == user].iterrows():
                    if st.button(f"Cancella {row['Casa']} {row['Data_Inizio']}", key=f"del_{idx}"):
                        df = df.drop(idx); conn.update(worksheet="Prenotazioni", data=df); st.rerun()

    # --- TAB 3: CALENDARIO (Giallo per Attesa, Colore Utente per Confermata) ---
    with tab3:
        st.header("Calendario 2026")
        occupied = {}
        # Priorità alle confermate, poi le in attesa
        df_sorted = df.sort_values(by="Stato", ascending=False) 
        for _, r in df_sorted.iterrows():
            try:
                start = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                end = datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date()
                curr = start
                while curr <= end:
                    if curr not in occupied or (occupied[curr]['s'] == "In Attesa" and r['Stato'] == "Confermata"):
                        occupied[curr] = {"u": r['Utente'], "c": r['Casa'], "s": r['Stato']}
                    curr += timedelta(days=1)
            except: continue

        for riga in range(4):
            cols_m = st.columns(3)
            for box in range(3):
                m_idx = riga * 3 + box + 1
                with cols_m[box]:
                    curr_month = datetime(2026, m_idx, 1).date()
                    st.write(f"**{curr_month.strftime('%B').upper()}**")
                    html = "<table class='cal-table'><tr>"
                    for d_name in ['L','M','M','G','V','S','D']: html += f"<th>{d_name}</th>"
                    html += "</tr><tr>"
                    wd = curr_month.weekday()
                    for _ in range(wd): html += "<td></td>"
                    if m_idx == 12: next_m = datetime(2027, 1, 1).date()
                    else: next_m = datetime(2026, m_idx+1, 1).date()
                    days_in_month = (next_m - curr_month).days
                    curr_col = wd
                    for d in range(1, days_in_month + 1):
                        d_obj = curr_month.replace(day=d)
                        bg, content = "", f"<div class='day-num'>{d}</div>"
                        if d_obj in occupied:
                            info = occupied[d_obj]
                            if info['s'] == "Confermata":
                                bg = f"background-color: {utenti_config[info['u']]['color']}; color: white;"
                            else: # In Attesa = GIALLO
                                bg = "background-color: #FFFFCC; color: #666; border: 1px dashed #ffd700;"
                            content += f"<div class='full-cell'>{icone_case.get(info['c'], '')}</div>"
                        html += f"<td class='cal-td' style='{bg}'>{content}</td>"
                        curr_col += 1
                        if curr_col > 6: html += "</tr><tr>"; curr_col = 0
                    st.markdown(html + "</tr></table>", unsafe_allow_html=True)

    # --- TAB 4: STATS (CONTEGGIO GIORNI UTENTE RICHIESTI/CONFERMATI) ---
    with tab4:
        st.header("📈 Statistiche Dettagliate")
        if not df.empty:
            def g_calc(r):
                try: return (datetime.strptime(r['Data_Fine'], '%d/%m/%Y') - datetime.strptime(r['Data_Inizio'], '%d/%m/%Y')).days + 1
                except: return 0
            df['GG'] = df.apply(g_calc, axis=1)
            
            c1, c2 = st.columns(2)
            with c1:
                if os.path.exists("Noli.jpg"): st.image("Noli.jpg", width=200)
                st.metric("NOLI 🏖️", f"{df[(df['Casa'] == 'NOLI') & (df['Stato'] == 'Confermata')]['GG'].sum()} gg")
            with c2:
                if os.path.exists("Limone.jpg"): st.image("Limone.jpg", width=200)
                st.metric("LIMONE 🏔️", f"{df[(df['Casa'] == 'LIMONE') & (df['Stato'] == 'Confermata')]['GG'].sum()} gg")
            
            st.divider()
            st.subheader("🏆 Riepilogo Utenti (Giorni)")
            
            # Calcolo giorni per utente
            stats_u = []
            for u in utenti_config.keys():
                conf = df[(df['Utente'] == u) & (df['Stato'] == "Confermata")]['GG'].sum()
                attesa = df[(df['Utente'] == u) & (df['Stato'] == "In Attesa")]['GG'].sum()
                stats_u.append({"Utente": u, "Confermati ✅": conf, "In Attesa ⏳": attesa, "Totale": conf + attesa})
            
            st.table(pd.DataFrame(stats_u).sort_values(by="Confermati ✅", ascending=False))

else:
    st.title("🏠 Family Booking"); st.info("Esegui il login.")
