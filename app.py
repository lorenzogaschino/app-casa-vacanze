import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- CSS OTTIMIZZATO (CON BLOCCA RIQUADRI PER LEGENDA) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 14px; }
    button[data-baseweb="tab"] p { font-size: 14px !important; font-weight: bold !important; }
    
    /* EFFETTO BLOCCA RIQUADRI PER CALENDARIO */
    .sticky-header {
        position: -webkit-sticky;
        position: sticky;
        top: 0;
        background-color: white;
        z-index: 100;
        padding: 10px 0;
        border-bottom: 1px solid #eee;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* Calendario compatto */
    .cal-table { width:100%; table-layout: fixed; border-spacing: 1px; border-collapse: separate; }
    .cal-td { text-align:center; height:32px; border-radius:2px; border:1px solid #f0f0f0; padding:0 !important; position:relative; }
    .day-num { position: absolute; top: 0px; left: 1px; font-size: 8px; color: #666; z-index: 5; }
    .full-cell { height: 100%; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 12px; }
    
    /* Legenda */
    .legenda-item { display: inline-block; padding: 2px 8px; border-radius: 4px; margin: 2px; color: white; font-size: 11px; font-weight: bold; }
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

# --- CONFIGURAZIONE UTENTI ---
utenti_config = {
    "Anita": {"pin": "1111", "color": "#FF4B4B"},
    "Chiara": {"pin": "4444", "color": "#FFC0CB"},
    "Lorenzo": {"pin": "1234", "color": "#1C83E1"},
    "Gianluca": {"pin": "1191", "color": "#28A745"}
}
icone_case = {"LIMONE": "🏔️", "NOLI": "🏖️"}

# --- GESTIONE LOGIN ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.title("🏠 Family Booking")
    st.subheader("🔐 Accesso")
    user_input = st.selectbox("Chi sei?", ["-- Seleziona --"] + list(utenti_config.keys()))
    pass_input = st.text_input("Inserisci il tuo PIN", type="password")
    if st.button("Accedi"):
        if user_input != "-- Seleziona --" and pass_input == utenti_config[user_input]["pin"]:
            st.session_state['authenticated'] = True
            st.session_state['user'] = user_input
            st.rerun()
        else:
            st.error("PIN errato")
else:
    user = st.session_state['user']
    df = get_data()
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    col_tit, col_log = st.columns([5,1])
    with col_tit: st.write(f"Ciao **{user}**! 👋")
    with col_log:
        if st.button("Logout"):
            st.session_state['authenticated'] = False
            st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["📅 PRENOTA", "📊 GESTIONE", "🗓️ CALENDARIO", "📈 STATISTICHE"])

    # --- TAB 1: PRENOTA ---
    with tab1:
        st.header("Nuova Prenotazione")
        oggi = datetime.now().date()
        casa_scelta = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
        f_nome = "Noli.jpg" if casa_scelta == "NOLI" else "Limone.jpg"
        if os.path.exists(f_nome): st.image(f_nome, width=280)

        p_casa = df[df['Casa'] == casa_scelta].copy()
        g_conf, g_att = [], []
        for _, r in p_casa.iterrows():
            info = f"{r['Data_Inizio']}-{r['Data_Fine']} ({r['Utente']})"
            if r['Stato'] == "Confermata": g_conf.append(info)
            else: g_att.append(info)
        
        if g_conf: st.error(f"🚫 **OCCUPATO:** {', '.join(g_conf)}")
        if g_att: st.warning(f"⏳ **RICHIESTO:** {', '.join(g_att)}")

        d_in = st.date_input("Check-in", value=oggi + timedelta(days=1), min_value=oggi)
        d_out = st.date_input("Check-out", value=d_in + timedelta(days=1), min_value=d_in + timedelta(days=1))
        notti = (d_out - d_in).days
        if notti > 0: st.info(f"🌙 Soggiorno di **{notti}** notti")
        
        note = st.text_area("Note")
        if st.button("🚀 INVIA RICHIESTA"):
            nuova = pd.DataFrame([{
                "ID": str(datetime.now().timestamp()), "Casa": casa_scelta, "Utente": user,
                "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                "Stato": "In Attesa", "Voti_Ok": "", "Note": note
            }])
            conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
            st.success("Inviata!"); time.sleep(1); st.rerun()

    # --- TAB 2: GESTIONE ---
    with tab2:
        st.header("Elenco prenotazioni")
        if not df.empty:
            all_users = set(utenti_config.keys())
            def get_voti_details(row):
                votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                mancano = list(all_users - (set(votanti) | {row['Utente']}))
                return ", ".join(votanti), ", ".join(mancano)
            df[['Approvato', 'Mancano']] = df.apply(get_voti_details, axis=1, result_type='expand')
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato', 'Approvato', 'Mancano']], use_container_width=True)
            
            st.divider()
            st.subheader("🗳️ Approva")
            for idx, row in df.iterrows():
                if row['Utente'] != user and row['Stato'] == "In Attesa":
                    votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                    if user not in votanti:
                        label = f"Approva - {row['Casa']} - ({row['Data_Inizio']}-{row['Data_Fine']}) - {row['Utente']}"
                        if st.button(label, key=f"v_{idx}"):
                            votanti.append(user)
                            df.at[idx, 'Voti_Ok'] = ", ".join(votanti)
                            if len(votanti) >= 3: df.at[idx, 'Stato'] = "Confermata"
                            conn.update(worksheet="Prenotazioni", data=df); st.rerun()
            
            st.subheader("🗑️ Elimina le tue")
            for idx, row in df[df['Utente'] == user].iterrows():
                if st.button(f"Cancella {row['Casa']} {row['Data_Inizio']}", key=f"del_{idx}"):
                    df = df.drop(idx); conn.update(worksheet="Prenotazioni", data=df); st.rerun()

    # --- TAB 3: CALENDARIO (CON BLOCCA RIQUADRI) ---
    with tab3:
        # CONTENITORE BLOCCATO (Titolo + Legenda)
        legenda_html = ""
        for u, cfg in utenti_config.items():
            legenda_html += f'<span class="legenda-item" style="background:{cfg["color"]}">{u}</span>'
        legenda_html += '<span class="legenda-item" style="background:#FFFFCC; color:#666; border:1px solid #ffd700">In Attesa</span>'
        
        st.markdown(f"""
            <div class="sticky-header">
                <h2 style="margin:0; padding-bottom:5px;">Calendario 2026</h2>
                {legenda_html}
            </div>
        """, unsafe_allow_html=True)

        occupied = {}
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

        # Griglia dei mesi che scorre sotto la header
        for riga in range(6):
            cols_m = st.columns(2)
            for box in range(2):
                m_idx = riga * 2 + box + 1
                with cols_m[box]:
                    curr_month = datetime(2026, m_idx, 1).date()
                    st.write(f"**{curr_month.strftime('%b').upper()}**")
                    html = "<table class='cal-table'><tr>"
                    for d_name in ['L','M','M','G','V','S','D']: html += f"<th>{d_name}</th>"
                    html += "</tr><tr>"
                    wd = curr_month.weekday()
                    for _ in range(wd): html += "<td></td>"
                    days_in_month = ( (datetime(2026, m_idx+1, 1).date() if m_idx < 12 else datetime(2027,1,1).date()) - curr_month).days
                    curr_col = wd
                    for d in range(1, days_in_month + 1):
                        d_obj = curr_month.replace(day=d)
                        bg, content = "", f"<div class='day-num'>{d}</div>"
                        if d_obj in occupied:
                            info = occupied[d_obj]
                            bg = f"background-color: {utenti_config[info['u']]['color']}; color: white;" if info['s'] == "Confermata" else "background-color: #FFFFCC; color: #666;"
                            content += f"<div class='full-cell'>{icone_case.get(info['c'], '')}</div>"
                        html += f"<td class='cal-td' style='{bg}'>{content}</td>"
                        curr_col += 1
                        if curr_col > 6: html += "</tr><tr>"; curr_col = 0
                    st.markdown(html + "</tr></table>", unsafe_allow_html=True)

    # --- TAB 4: STATISTICHE ---
    with tab4:
        st.header("Statistiche")
        if not df.empty:
            def g_calc(r):
                try: return (datetime.strptime(r['Data_Fine'], '%d/%m/%Y') - datetime.strptime(r['Data_Inizio'], '%d/%m/%Y')).days + 1
                except: return 0
            df['GG'] = df.apply(g_calc, axis=1)
            c1, c2 = st.columns(2)
            with c1:
                if os.path.exists("Noli.jpg"): st.image("Noli.jpg", width=150)
                st.metric("NOLI 🏖️", f"{df[(df['Casa'] == 'NOLI') & (df['Stato'] == 'Confermata')]['GG'].sum()} gg")
            with c2:
                if os.path.exists("Limone.jpg"): st.image("Limone.jpg", width=150)
                st.metric("LIMONE 🏔️", f"{df[(df['Casa'] == 'LIMONE') & (df['Stato'] == 'Confermata')]['GG'].sum()} gg")
            
            st.divider()
            stats_u = []
            for u in utenti_config.keys():
                conf = df[(df['Utente'] == u) & (df['Stato'] == "Confermata")]['GG'].sum()
                att = df[(df['Utente'] == u) & (df['Stato'] == "In Attesa")]['GG'].sum()
                stats_u.append({"Utente": u, "Confermati": int(conf), "In attesa": int(att), "Totale": int(conf + att)})
            st.dataframe(pd.DataFrame(stats_u), hide_index=True)
