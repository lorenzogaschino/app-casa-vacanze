import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    html, body { overflow-y: auto; overscroll-behavior-y: contain; }
    [data-testid="stHeader"] { z-index: 999; }
    html, body, [class*="css"] { font-size: 14px; }
    button[data-baseweb="tab"] p { font-size: 15px !important; font-weight: bold !important; }
    .cal-table { width:100%; table-layout: fixed; border-spacing: 1px; border-collapse: separate; }
    .cal-td { text-align:center; height:35px; border-radius:3px; border:1px solid #f0f0f0; padding:0 !important; position:relative; }
    .day-num { position: absolute; top: 1px; left: 2px; font-size: 9px; color: #666; z-index: 5; }
    .full-cell { height: 100%; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 14px; }
    .legenda-item { display: inline-block; padding: 4px 10px; border-radius: 5px; margin: 2px; color: white; font-size: 11px; font-weight: bold; }
    .stImage > img { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI UTILITY ---
def get_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(worksheet="Prenotazioni", ttl=0)
    data = data.dropna(axis=1, how='all')
    for col in ['Voti_Ok', 'Note', 'Data_Inizio', 'Data_Fine', 'Stato']:
        if col in data.columns: data[col] = data[col].fillna("").astype(str)
    return data

def parse_date(d_str):
    try: return datetime.strptime(d_str, '%d/%m/%Y').date()
    except: return None

# --- SESSIONE ---
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.title("🏠 Family Booking")
    utenti_log = {"Anita": "1111", "Chiara": "4444", "Lorenzo": "1234", "Gianluca": "1191"}
    u_log = st.selectbox("Chi sei?", ["-- Seleziona --"] + list(utenti_log.keys()))
    p_log = st.text_input("Inserisci il PIN", type="password")
    if st.button("Entra"):
        if u_log != "-- Seleziona --" and p_log == utenti_log[u_log]:
            st.session_state['authenticated'] = True
            st.session_state['user_name'] = u_log
            st.rerun()
        else: st.error("PIN errato")
else:
    # --- LOGOUT ---
    c_inf, c_log = st.columns([0.8, 0.2])
    with c_inf: st.write(f"Connesso come: **{st.session_state['user_name']}**")
    with c_log:
        if st.button("🔴 Logout"):
            st.session_state['authenticated'] = False
            st.rerun()

    df = get_data()
    conn = st.connection("gsheets", type=GSheetsConnection)
    utenti_config = {"Anita": {"color": "#FF4B4B"}, "Chiara": {"color": "#FFC0CB"}, "Lorenzo": {"color": "#1C83E1"}, "Gianluca": {"color": "#28A745"}}
    icone_case = {"LIMONE": "🏔️", "NOLI": "🏖️"}

    tab1, tab2, tab3, tab4 = st.tabs(["📅 PRENOTA", "📊 GESTIONE", "🗓️ CALENDARIO", "📈 STATISTICHE"])

    # --- TAB 1: PRENOTA ---
    with tab1:
        st.header("Nuova Prenotazione")
        casa_scelta = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
        f_nome = "Noli.jpg" if casa_scelta == "NOLI" else "Limone.jpg"
        if os.path.exists(f_nome): st.image(f_nome, width=280)
        
        # ELENCO PRENOTAZIONI CON DETTAGLIO COMPLETO
        p_casa = df[df['Casa'] == casa_scelta].copy()
        if not p_casa.empty:
            st.write("---")
            for _, r in p_casa.iterrows():
                formato_info = f"{r['Casa']} - {r['Data_Inizio']} - {r['Data_Fine']} - {r['Utente']}"
                if r['Stato'] == "Confermata":
                    st.markdown(f"<span style='color:#FF4B4B; font-weight:bold;'>🔴 CONFERMATA:</span> {formato_info}", unsafe_allow_html=True)
                else:
                    st.markdown(f"<span style='color:#FFD700; font-weight:bold;'>⏳ IN ATTESA:</span> {formato_info}", unsafe_allow_html=True)
            st.write("---")

        with st.form("booking_form"):
            d_in = st.date_input("Check-in", value=datetime.now().date() + timedelta(days=1), min_value=datetime.now().date())
            d_out = st.date_input("Check-out", value=d_in + timedelta(days=1), min_value=datetime.now().date())
            note = st.text_area("Note")
            if st.form_submit_button("🚀 INVIA PRENOTAZIONE"):
                if d_out <= d_in: st.error("❌ La data di fine deve essere successiva all'inizio.")
                else:
                    nuova = pd.DataFrame([{
                        "ID": str(datetime.now().timestamp()), "Casa": casa_scelta, "Utente": st.session_state['user_name'],
                        "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                        "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                    }])
                    conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                    st.success("✅ Prenotazione registrata!"); time.sleep(1.5); st.rerun()

    # --- TAB 2: GESTIONE ---
    with tab2:
        st.header("Gestione Prenotazioni")
        if not df.empty:
            st.subheader("📥 Approva")
            da_approvare = df[(df['Utente'] != st.session_state['user_name']) & (df['Stato'] == "In Attesa")]
            if da_approvare.empty:
                st.info("Nessuna prenotazione da approvare.")
            else:
                for idx, row in da_approvare.iterrows():
                    voti = [x.strip() for x in str(row['Voti_Ok']).split(",") if x.strip()]
                    if st.session_state['user_name'] not in voti:
                        # FORMATO: Approva: Casa - Data_Inizio - Data_fine - Utente
                        label_app = f"Approva: {row['Casa']} - {row['Data_Inizio']} - {row['Data_Fine']} - {row['Utente']}"
                        if st.button(label_app, key=f"app_{idx}"):
                            voti.append(st.session_state['user_name'])
                            df.at[idx, 'Voti_Ok'] = ", ".join(voti)
                            if len(voti) >= 3: df.at[idx, 'Stato'] = "Confermata"
                            conn.update(worksheet="Prenotazioni", data=df)
                            st.rerun()

            st.divider()
            st.subheader("🗑️ Elimina le tue")
            le_mie = df[df['Utente'] == st.session_state['user_name']]
            if le_mie.empty:
                st.info("Non hai prenotazioni attive.")
            else:
                for idx, row in le_mie.iterrows():
                    # FORMATO: Cancella: Casa - Data_Inizio - Data_fine - Utente
                    label_del = f"Cancella: {row['Casa']} - {row['Data_Inizio']} - {row['Data_Fine']} - {row['Utente']}"
                    
                    if st.button(label_del, key=f"pre_del_{idx}"):
                        st.session_state[f"confirm_{idx}"] = True
                    
                    if st.session_state.get(f"confirm_{idx}"):
                        st.error(f"Confermi l'eliminazione della prenotazione?")
                        c1, c2 = st.columns(2)
                        if c1.button("✅ SÌ, ELIMINA DEFINITIVAMENTE", key=f"real_del_{idx}"):
                            df_new = df.drop(idx)
                            conn.update(worksheet="Prenotazioni", data=df_new)
                            del st.session_state[f"confirm_{idx}"]
                            st.rerun()
                        if c2.button("❌ ANNULLA", key=f"stop_del_{idx}"):
                            del st.session_state[f"confirm_{idx}"]
                            st.rerun()

    # --- TAB 3: CALENDARIO (Invariato per stabilità) ---
    with tab3:
        leg_h = "".join([f'<span class="legenda-item" style="background:{c["color"]}">{u}</span>' for u, c in utenti_config.items()])
        st.markdown(f'<div style="background:white; padding:10px; border-radius:10px;">🗓️ 2026 {leg_h}</div>', unsafe_allow_html=True)
        occupied = {}
        for _, r in df.sort_values(by="Stato", ascending=False).iterrows():
            s, e = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
            if s and e:
                curr = s
                while curr <= e:
                    if curr not in occupied or (occupied[curr]['s'] == "In Attesa" and r['Stato'] == "Confermata"):
                        occupied[curr] = {"u": r['Utente'], "c": r['Casa'], "s": r['Stato']}
                    curr += timedelta(days=1)
        for riga in range(6):
            cols = st.columns(2)
            for box in range(2):
                m = riga * 2 + box + 1
                with cols[box]:
                    m_date = datetime(2026, m, 1).date()
                    st.write(f"**{m_date.strftime('%B').upper()}**")
                    html = "<table class='cal-table'><tr>" + "".join([f"<th>{d}</th>" for d in ['L','M','M','G','V','S','D']]) + "</tr><tr>"
                    wd = m_date.weekday()
                    html += "<td></td>" * wd
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

    # --- TAB 4: STATISTICHE ---
    with tab4:
        st.header("Statistiche")
        if not df.empty:
            df['GG'] = df.apply(lambda r: (parse_date(r['Data_Fine']) - parse_date(r['Data_Inizio'])).days + 1 if parse_date(r['Data_Inizio']) else 0, axis=1)
            c1, c2 = st.columns(2)
            with c1:
                if os.path.exists("Noli.jpg"): st.image("Noli.jpg", width=150)
                st.metric("NOLI 🏖️", f"{df[(df['Casa'] == 'NOLI') & (df['Stato'] == 'Confermata')]['GG'].sum()} gg")
            with c2:
                if os.path.exists("Limone.jpg"): st.image("Limone.jpg", width=150)
                st.metric("LIMONE 🏔️", f"{df[(df['Casa'] == 'LIMONE') & (df['Stato'] == 'Confermata')]['GG'].sum()} gg")
