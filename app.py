import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- CSS DEFINITIVO (BLOcca LEGENDA E STILE MOBILE) ---
st.markdown("""
    <style>
    /* Forza la Legenda e il titolo a rimanere in alto */
    [data-testid="stHeader"] {
        z-index: 999;
    }
    
    .sticky-wrapper {
        position: -webkit-sticky;
        position: sticky;
        top: 0;
        z-index: 1000;
        background-color: white;
        padding: 10px;
        border-bottom: 2px solid #f0f2f6;
    }

    html, body, [class*="css"] { font-size: 14px; }
    button[data-baseweb="tab"] p { font-size: 14px !important; font-weight: bold !important; }
    
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

# --- GESTIONE SESSIONE (FIX LOGOUT) ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# --- LOGICA DI ACCESSO ---
if not st.session_state['authenticated']:
    st.title("🏠 Family Booking")
    st.subheader("🔐 Accesso")
    u_log = st.selectbox("Chi sei?", ["-- Seleziona --"] + list(utenti_config.keys()))
    p_log = st.text_input("PIN", type="password")
    if st.button("Accedi"):
        if u_log != "-- Seleziona --" and p_log == utenti_config[u_log]["pin"]:
            st.session_state['authenticated'] = True
            st.session_state['user_name'] = u_log
            st.rerun()
        else:
            st.error("PIN errato")
else:
    # --- APP DOPO IL LOGIN ---
    current_user = st.session_state['user_name']
    df = get_data()
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Header fisso in alto per i Tab
    st.write(f"Ciao **{current_user}**! 👋")

    tab1, tab2, tab3, tab4 = st.tabs(["📅 PRENOTA", "📊 GESTIONE", "🗓️ CALENDARIO", "📈 STATISTICHE"])

    with tab1:
        st.header("Nuova Prenotazione")
        oggi = datetime.now().date()
        casa_scelta = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
        f_nome = "Noli.jpg" if casa_scelta == "NOLI" else "Limone.jpg"
        if os.path.exists(f_nome): st.image(f_nome, width=250)

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
        if st.button("🚀 INVIA"):
            nuova = pd.DataFrame([{
                "ID": str(datetime.now().timestamp()), "Casa": casa_scelta, "Utente": current_user,
                "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                "Stato": "In Attesa", "Voti_Ok": "", "Note": note
            }])
            conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
            st.success("Richiesta inviata!"); time.sleep(1); st.rerun()

    with tab2:
        st.header("Elenco prenotazioni")
        if not df.empty:
            all_u = set(utenti_config.keys())
            def get_v_d(row):
                v = [x.strip() for x in str(row['Voti_Ok']).split(",") if x.strip()]
                m = list(all_u - (set(v) | {row['Utente']}))
                return ", ".join(v), ", ".join(m)
            df[['Approvato', 'Mancano']] = df.apply(get_v_d, axis=1, result_type='expand')
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato', 'Approvato', 'Mancano']], use_container_width=True)
            
            st.divider()
            st.subheader("🗳️ Approva")
            for idx, row in df.iterrows():
                if row['Utente'] != current_user and row['Stato'] == "In Attesa":
                    v = [x.strip() for x in str(row['Voti_Ok']).split(",") if x.strip()]
                    if current_user not in v:
                        label = f"Approva - {row['Casa']} - ({row['Data_Inizio']}-{row['Data_Fine']}) - {row['Utente']}"
                        if st.button(label, key=f"v_{idx}"):
                            v.append(current_user)
                            df.at[idx, 'Voti_Ok'] = ", ".join(v)
                            if len(v) >= 3: df.at[idx, 'Stato'] = "Confermata"
                            conn.update(worksheet="Prenotazioni", data=df); st.rerun()
            
            st.subheader("🗑️ Elimina le tue")
            for idx, row in df[df['Utente'] == current_user].iterrows():
                if st.button(f"Cancella {row['Casa']} {row['Data_Inizio']}", key=f"del_{idx}"):
                    df = df.drop(idx); conn.update(worksheet="Prenotazioni", data=df); st.rerun()

    with tab3:
        # --- SEZIONE STICKY (LEGENDA BLOCCATA) ---
        legenda_h = "".join([f'<span class="legenda-item" style="background:{c["color"]}">{u}</span>' for u, c in utenti_config.items()])
        legenda_h += '<span class="legenda-item" style="background:#FFFFCC; color:#666; border:1px solid #ffd700">In Attesa</span>'
        
        st.markdown(f"""
            <div class="sticky-wrapper">
                <h3 style="margin:0;">🗓️ Calendario 2026</h3>
                {legenda_h}
            </div>
        """, unsafe_allow_html=True)

        occupied = {}
        df_s = df.sort_values(by="Stato", ascending=False) 
        for _, r in df_s.iterrows():
            try:
                s = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                e = datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date()
                curr = s
                while curr <= e:
                    if curr not in occupied or (occupied[curr]['s'] == "In Attesa" and r['Stato'] == "Confermata"):
                        occupied[curr] = {"u": r['Utente'], "c": r['Casa'], "s": r['Stato']}
                    curr += timedelta(days=1)
            except: continue

        # Visualizzazione mesi
        for riga in range(6):
            cols = st.columns(2)
            for box in range(2):
                m = riga * 2 + box + 1
                with cols[box]:
                    m_date = datetime(2026, m, 1).date()
                    st.write(f"**{m_date.strftime('%B').upper()}**")
                    html = "<table class='cal-table'><tr>"
                    for dn in ['L','M','M','G','V','S','D']: html += f"<th>{dn}</th>"
                    html += "</tr><tr>"
                    wd = m_date.weekday()
                    for _ in range(wd): html += "<td></td>"
                    days = ((datetime(2026, m+1, 1).date() if m < 12 else datetime(2027,1,1).date()) - m_date).days
                    c_col = wd
                    for d in range(1, days + 1):
                        d_obj = m_date.replace(day=d)
                        bg, content = "", f"<div class='day-num'>{d}</div>"
                        if d_obj in occupied:
                            inf = occupied[d_obj]
                            bg = f"background-color: {utenti_config[inf['u']]['color']}; color: white;" if inf['s'] == "Confermata" else "background-color: #FFFFCC; color: #666;"
                            content += f"<div class='full-cell'>{icone_case.get(inf['c'], '')}</div>"
                        html += f"<td class='cal-td' style='{bg}'>{content}</td>"
                        c_col += 1
                        if c_col > 6: html += "</tr><tr>"; c_col = 0
                    st.markdown(html + "</tr></table>", unsafe_allow_html=True)

    with tab4:
        st.header("Statistiche")
        if not df.empty:
            def gc(r):
                try: return (datetime.strptime(r['Data_Fine'], '%d/%m/%Y') - datetime.strptime(r['Data_Inizio'], '%d/%m/%Y')).days + 1
                except: return 0
            df['GG'] = df.apply(gc, axis=1)
            c1, c2 = st.columns(2)
            with c1:
                if os.path.exists("Noli.jpg"): st.image("Noli.jpg", width=120)
                st.metric("NOLI 🏖️", f"{df[(df['Casa'] == 'NOLI') & (df['Stato'] == 'Confermata')]['GG'].sum()} gg")
            with c2:
                if os.path.exists("Limone.jpg"): st.image("Limone.jpg", width=120)
                st.metric("LIMONE 🏔️", f"{df[(df['Casa'] == 'LIMONE') & (df['Stato'] == 'Confermata')]['GG'].sum()} gg")
            
            st.divider()
            stats = []
            for u in utenti_config.keys():
                c = df[(df['Utente'] == u) & (df['Stato'] == "Confermata")]['GG'].sum()
                a = df[(df['Utente'] == u) & (df['Stato'] == "In Attesa")]['GG'].sum()
                stats.append({"Utente": u, "Confermati": int(c), "In attesa": int(a), "Totale": int(c+a)})
            st.dataframe(pd.DataFrame(stats), hide_index=True)
            
            if st.button("Logout"):
                st.session_state['authenticated'] = False
                st.rerun()
