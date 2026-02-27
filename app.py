import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- STILE CSS PER CALENDARIO COMPATTO ---
st.markdown("""
    <style>
    button[data-baseweb="tab"] p { font-size: 18px !important; font-weight: bold !important; }
    .cal-table { width:100%; table-layout: fixed; border-spacing: 1px; border-collapse: separate; }
    .cal-td { text-align:center; height:35px; border-radius:3px; border:1px solid #f0f0f0; padding:0 !important; position:relative; overflow:hidden; font-size: 11px; }
    .day-num { position: absolute; top: 1px; left: 2px; font-size: 9px; color: #666; z-index: 5; }
    .full-cell { height: 100%; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 14px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNESSIONE DATI ---
def get_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(worksheet="Prenotazioni", ttl=0)
    data = data.dropna(axis=1, how='all')
    for col in ['Voti_Ok', 'Note']:
        if col in data.columns: data[col] = data[col].fillna("").astype(str)
        else: data[col] = ""
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
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 PRENOTA", "📊 STATO & VOTI", "🗓️ CALENDARIO ANNUALE", "📈 STATS"])

    # --- TAB 1: PRENOTAZIONE (CON ALERT DISPONIBILITÀ) ---
    with tab1:
        st.header("Nuova Prenotazione")
        
        col_form, col_foto = st.columns([2, 1])
        with col_form:
            casa_scelta = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
            
            # Logica Alert Date Occupate (Screenshot 1 fix)
            p_casa = df[df['Casa'] == casa_scelta].copy()
            g_conf, g_rich = [], []
            for _, r in p_casa.iterrows():
                try:
                    di = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                    df_ = datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date()
                    info = f"{di.strftime('%d/%m')} - {df_.strftime('%d/%m')} ({r['Utente']})"
                    if r['Stato'] == "Confermata": g_conf.append(info)
                    else: g_rich.append(info)
                except: continue
            
            if g_conf: st.error(f"🚫 **DATE OCCUPATE:** {', '.join(g_conf)}")
            if g_rich: st.warning(f"🟡 **RICHIESTE IN CORSO:** {', '.join(g_rich)}")

            d_in = st.date_input("Check-in", value=datetime.today().date() + timedelta(days=1))
            d_out = st.date_input("Check-out", value=d_in + timedelta(days=1))
            notti = (d_out - d_in).days
            if notti > 0: st.info(f"🌙 Soggiorno di {notti} notti.")
            
            note = st.text_area("Note / Commenti")
            if st.button("🚀 INVIA RICHIESTA"):
                nuova = pd.DataFrame([{
                    "ID": str(datetime.now().timestamp()), "Casa": casa_scelta, "Utente": user,
                    "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                    "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                }])
                conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                st.balloons(); time.sleep(1); st.rerun()
        
        with col_foto:
            f = f"{casa_scelta.capitalize()}.jpg"
            if os.path.exists(f): st.image(f, use_container_width=True)

    # --- TAB 2: STATO & VOTI (DETTAGLIATO) ---
    with tab2:
        st.header("Situazione e Gestione")
        if not df.empty:
            # Calcolo colonne Approvato/Mancano (Screenshot 2 fix)
            all_users = set(utenti_config.keys())
            def get_voti_details(row):
                votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                mancano = list(all_users - (set(votanti) | {row['Utente']}))
                return ", ".join(votanti), ", ".join(mancano)
            
            df[['Già Approvato', 'Mancano']] = df.apply(get_voti_details, axis=1, result_type='expand')
            
            # Visualizzazione tabella ordinata
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato', 'Già Approvato', 'Mancano', 'Note']], use_container_width=True)
            
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🗳️ Vota")
                for idx, row in df.iterrows():
                    if row['Utente'] != user and row['Stato'] == "In Attesa":
                        votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                        if user not in votanti:
                            if st.button(f"Approva {row['Utente']} per {row['Casa']}", key=f"v_{idx}"):
                                votanti.append(user)
                                df.at[idx, 'Voti_Ok'] = ", ".join(votanti)
                                if len(votanti) >= 3: df.at[idx, 'Stato'] = "Confermata"
                                conn.update(worksheet="Prenotazioni", data=df); st.rerun()
            with c2:
                st.subheader("🗑️ Elimina le tue")
                for idx, row in df[df['Utente'] == user].iterrows():
                    if st.button(f"Elimina {row['Casa']} ({row['Data_Inizio']})", key=f"del_{idx}"):
                        df = df.drop(idx); conn.update(worksheet="Prenotazioni", data=df); st.rerun()

    # --- TAB 3: CALENDARIO ANNUALE COMPATTO (NO SOVRAPPOSIZIONI) ---
    with tab3:
        st.header("Calendario 2026")
        
        # Mappa occupazione (Semplice: il primo che conferma vince la visualizzazione)
        occupied = {}
        for _, r in df[df['Stato'] == "Confermata"].iterrows():
            try:
                start = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                end = datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date()
                curr = start
                while curr <= end:
                    if curr not in occupied: # Solo la prima prenotazione trovata viene mostrata
                        occupied[curr] = {"u": r['Utente'], "c": r['Casa']}
                    curr += timedelta(days=1)
            except: continue

        # Griglia 3 mesi per riga
        cols_m = st.columns(3)
        for m in range(1, 13):
            with cols_m[(m-1)%3]:
                curr_month = datetime(2026, m, 1).date()
                st.write(f"**{curr_month.strftime('%B').upper()}**")
                
                # Header giorni
                html = "<table class='cal-table'><tr>"
                for d_name in ['L','M','M','G','V','S','D']: html += f"<th style='font-size:9px;'>{d_name}</th>"
                html += "</tr><tr>"
                
                # Giorni vuoti inizio mese
                wd = curr_month.weekday()
                for _ in range(wd): html += "<td></td>"
                
                # Giorni mese
                if m == 12: next_m = datetime(2027, 1, 1).date()
                else: next_m = datetime(2026, m+1, 1).date()
                days_in_month = (next_m - curr_month).days
                
                curr_col = wd
                for d in range(1, days_in_month + 1):
                    d_obj = curr_month.replace(day=d)
                    bg, content = "", f"<div class='day-num'>{d}</div>"
                    
                    if d_obj in occupied:
                        u, c = occupied[d_obj]['u'], occupied[d_obj]['c']
                        bg = f"background-color: {utenti_config[u]['color']}; color: white;"
                        content += f"<div class='full-cell'>{icone_case.get(c, '')}</div>"
                    
                    html += f"<td class='cal-td' style='{bg}'>{content}</td>"
                    curr_col += 1
                    if curr_col > 6:
                        html += "</tr><tr>"
                        curr_col = 0
                
                st.markdown(html + "</tr></table>", unsafe_allow_html=True)
                st.write("")

    # --- TAB 4: STATISTICHE ---
    with tab4:
        st.header("📊 Statistiche Confermate")
        df_c = df[df['Stato'] == "Confermata"].copy()
        if not df_c.empty:
            def g_calc(r):
                return (datetime.strptime(r['Data_Fine'], '%d/%m/%Y') - datetime.strptime(r['Data_Inizio'], '%d/%m/%Y')).days + 1
            df_c['GG'] = df_c.apply(g_calc, axis=1)
            
            c1, c2 = st.columns(2)
            with c1:
                st.image("Noli.jpg", width=200)
                st.metric("NOLI 🏖️", f"{df_c[df_c['Casa'] == 'NOLI']['GG'].sum()} giorni")
            with c2:
                st.image("Limone.jpg", width=200)
                st.metric("LIMONE 🏔️", f"{df_c[df_c['Casa'] == 'LIMONE']['GG'].sum()} giorni")
            
            st.divider()
            st.subheader("🏆 Classifica")
            for u, g in df_c.groupby('Utente')['GG'].sum().sort_values(ascending=False).items():
                st.write(f"**{u}**: {g} giorni")

else:
    st.title("🏠 Family Booking"); st.info("Esegui il login nella sidebar.")
