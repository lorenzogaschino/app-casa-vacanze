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
    button[data-baseweb="tab"] p { font-size: 18px !important; font-weight: bold !important; }
    .cal-table { width:100%; table-layout: fixed; border-spacing: 2px; border-collapse: separate; }
    .cal-td { text-align:center; height:70px; border-radius:4px; border:1px solid #eee; padding:0 !important; position:relative; overflow:hidden; }
    .day-num { position: absolute; top: 2px; width: 100%; text-align: center; font-size: 11px; z-index: 10; font-weight: bold; pointer-events: none; }
    .full-cell { height: 100%; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 20px; }
    .split-container { display: flex; height: 100%; width: 100%; }
    .split-half { flex: 1; display: flex; align-items: center; justify-content: center; font-size: 18px; height: 100%; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNESSIONE E DATI ---
def get_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(worksheet="Prenotazioni", ttl=0)
    data = data.dropna(axis=1, how='all')
    for col in ['Voti_Ok', 'Note']:
        if col in data.columns: data[col] = data[col].fillna("").astype(str)
        else: data[col] = ""
    return data

# --- CONFIGURAZIONE UTENTI E ICONE ---
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
        c1, c2 = st.columns([2, 1])
        with c1:
            casa_scelta = st.selectbox("Dove vuoi andare?", ["NOLI", "LIMONE"])
            d_in = st.date_input("Check-in", value=datetime.today().date() + timedelta(days=1))
            d_out = st.date_input("Check-out", value=d_in + timedelta(days=1))
            note = st.text_area("Note (opzionale)")
            if st.button("🚀 INVIA RICHIESTA"):
                nuova = pd.DataFrame([{
                    "ID": str(datetime.now().timestamp()), "Casa": casa_scelta, "Utente": user,
                    "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                    "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                }])
                conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                st.balloons(); time.sleep(1); st.rerun()
        with c2:
            f = f"{casa_scelta.capitalize()}.jpg"
            if os.path.exists(f): st.image(f, use_container_width=True)

    # --- TAB 2: GESTIONE (RIPRISTINATA CANCELLAZIONE SINGOLA) ---
    with tab2:
        st.header("Situazione e Voti")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.divider()
            
            # Sezione Voto
            st.subheader("🗳️ Approva Richieste")
            for idx, row in df.iterrows():
                if row['Utente'] != user and row['Stato'] == "In Attesa":
                    votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                    if user not in votanti:
                        if st.button(f"Approva {row['Utente']} @ {row['Casa']} ({row['Data_Inizio']})", key=f"v_{idx}"):
                            votanti.append(user)
                            df.at[idx, 'Voti_Ok'] = ", ".join(votanti)
                            if len(votanti) >= 3: df.at[idx, 'Stato'] = "Confermata"
                            conn.update(worksheet="Prenotazioni", data=df); st.rerun()

            # Sezione Cancellazione Singola
            st.subheader("🗑️ Le mie prenotazioni")
            mie_p = df[df['Utente'] == user]
            if not mie_p.empty:
                for idx, row in mie_p.iterrows():
                    if st.button(f"Elimina {row['Casa']} dal {row['Data_Inizio']}", key=f"del_{idx}"):
                        df = df.drop(idx)
                        conn.update(worksheet="Prenotazioni", data=df); st.rerun()
            else: st.info("Non hai prenotazioni attive.")

    # --- TAB 3: CALENDARIO (FIX SOVRAPPOSIZIONI E COLORI) ---
    with tab3:
        st.header("Calendario Occupazione")
        
        # 1. Costruiamo la mappa delle date
        map_date = {}
        for _, r in df[df['Stato'] == "Confermata"].iterrows():
            try:
                start = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                end = datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date()
                curr = start
                while curr <= end:
                    if curr not in map_date: map_date[curr] = []
                    # Aggiungiamo solo se non c'è già quella specifica accoppiata utente-casa
                    if not any(x['u'] == r['Utente'] and x['c'] == r['Casa'] for x in map_date[curr]):
                        map_date[curr].append({'u': r['Utente'], 'c': r['Casa']})
                    curr += timedelta(days=1)
            except: continue

        # 2. Generazione Mesi
        start_m = datetime.today().replace(day=1).date()
        for m_offset in range(4):
            show_m = (start_m + timedelta(days=m_offset*31)).replace(day=1)
            st.subheader(show_m.strftime("%B %Y").upper())
            
            # Logica giorni mese
            if show_m.month == 12: next_m = show_m.replace(year=show_m.year+1, month=1)
            else: next_m = show_m.replace(month=show_m.month+1)
            last_d = (next_m - timedelta(days=1)).day
            first_wd = show_m.weekday()

            html = "<table class='cal-table'><tr><th>L</th><th>M</th><th>M</th><th>G</th><th>V</th><th>S</th><th>D</th></tr><tr>"
            for _ in range(first_wd): html += "<td></td>"
            
            curr_col = first_wd
            for d in range(1, last_d + 1):
                d_obj = show_m.replace(day=d)
                td_content = f"<div class='day-num'>{d}</div>"
                
                if d_obj in map_date:
                    bookings = map_date[d_obj]
                    if len(bookings) == 1:
                        # GIORNO SINGOLO: un solo colore, un'icona
                        b = bookings[0]
                        c_bg = utenti_config.get(b['u'], {}).get('color', '#eee')
                        td_content += f"<div class='full-cell' style='background:{c_bg}; color:white;'>{icone_case.get(b['c'], '')}</div>"
                    else:
                        # SOVRAPPOSIZIONE: split verticale, due colori diversi, due icone
                        td_content += "<div class='split-container'>"
                        for b in bookings[:2]:
                            c_bg = utenti_config.get(b['u'], {}).get('color', '#eee')
                            td_content += f"<div class='split-half' style='background:{c_bg}; color:white;'>{icone_case.get(b['c'], '')}</div>"
                        td_content += "</div>"
                
                html += f"<td class='cal-td'>{td_content}</td>"
                curr_col += 1
                if curr_col > 6:
                    html += "</tr><tr>"
                    curr_col = 0
            
            while curr_col != 0 and curr_col <= 6:
                html += "<td></td>"
                curr_col += 1
            
            st.markdown(html + "</tr></table>", unsafe_allow_html=True)
            st.write("")

    # --- TAB 4: STATS (CON FOTO E CONTEGGI) ---
    with tab4:
        st.header("Statistiche Case")
        df_c = df[df['Stato'] == "Confermata"].copy()
        if not df_c.empty:
            def g_calc(r):
                return (datetime.strptime(r['Data_Fine'], '%d/%m/%Y') - datetime.strptime(r['Data_Inizio'], '%d/%m/%Y')).days + 1
            df_c['GG'] = df_c.apply(g_calc, axis=1)
            
            c_noli, c_limo = st.columns(2)
            with c_noli:
                if os.path.exists("Noli.jpg"): st.image("Noli.jpg", width=250)
                val = df_c[df_c['Casa'] == 'NOLI']['GG'].sum()
                st.metric("NOLI 🏖️", f"{val} giorni")
            with c_limo:
                if os.path.exists("Limone.jpg"): st.image("Limone.jpg", width=250)
                val = df_c[df_c['Casa'] == 'LIMONE']['GG'].sum()
                st.metric("LIMONE 🏔️", f"{val} giorni")
            
            st.divider()
            st.subheader("🏆 Re delle Vacanze")
            for u, g in df_c.groupby('Utente')['GG'].sum().sort_values(ascending=False).items():
                st.write(f"**{u}**: {g} giorni totali")
