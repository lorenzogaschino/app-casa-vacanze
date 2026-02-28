import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- CSS DEFINITIVO ---
st.markdown("""
    <style>
    html, body { overflow-y: auto; overscroll-behavior-y: contain; }
    [data-testid="stHeader"] { z-index: 999; }
    button[data-baseweb="tab"] p { font-size: 16px !important; font-weight: bold !important; }
    .cal-table { width:100%; table-layout: fixed; border-spacing: 1px; border-collapse: separate; }
    .cal-td { text-align:center; height:35px; border-radius:3px; border:1px solid #f0f0f0; padding:0 !important; position:relative; }
    .day-num { position: absolute; top: 1px; left: 2px; font-size: 9px; color: #666; z-index: 5; }
    .full-cell { height: 100%; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 14px; }
    .legenda-item { display: inline-block; padding: 4px 10px; border-radius: 5px; margin: 2px; color: white; font-size: 11px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CORE ---
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

# --- LOGICA NAVIGAZIONE PERSISTENTE ---
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False

# Recupero il tab attivo dai parametri URL o default a 0
if "tab" not in st.query_params:
    st.query_params["tab"] = "0"
current_tab = int(st.query_params["tab"])

# --- LOGIN ---
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
    # --- HEADER ---
    c_inf, c_log = st.columns([0.8, 0.2])
    c_inf.write(f"Connesso come: **{st.session_state['user_name']}**")
    if c_log.button("🔴 Logout"):
        st.session_state['authenticated'] = False
        st.query_params.clear()
        st.rerun()

    df = get_data()
    conn = st.connection("gsheets", type=GSheetsConnection)
    utenti_cfg = {"Anita": {"color": "#FF4B4B"}, "Chiara": {"color": "#FFC0CB"}, "Lorenzo": {"color": "#1C83E1"}, "Gianluca": {"color": "#28A745"}}

    # Tab con indice controllato dai query_params
    tabs = st.tabs(["📅 PRENOTA", "📊 GESTIONE", "🗓️ CALENDARIO", "📈 STATISTICHE"])

    # --- TAB 1: PRENOTA ---
    with tabs[0]:
        st.header("Nuova Prenotazione")
        casa_scelta = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
        img_path = f"{casa_scelta.capitalize()}.jpg"
        if os.path.exists(img_path): st.image(img_path, width=300)
        
        st.subheader("Stato attuale")
        p_casa = df[df['Casa'] == casa_scelta].copy()
        if not p_casa.empty:
            for _, r in p_casa.iterrows():
                info = f"{r['Casa']} - {r['Data_Inizio']} - {r['Data_Fine']} - {r['Utente']}"
                if r['Stato'] == "Confermata":
                    st.markdown(f"<span style='color:#FF4B4B; font-weight:bold;'>🔴 CONFERMATA:</span> {info}", unsafe_allow_html=True)
                else:
                    st.markdown(f"<span style='color:#FFD700; font-weight:bold;'>⏳ IN ATTESA:</span> {info}", unsafe_allow_html=True)

        with st.form("booking_form"):
            oggi = datetime.now().date()
            d_in = st.date_input("Check-in (Giorno arrivo)", value=oggi + timedelta(days=1), min_value=oggi)
            d_out = st.date_input("Check-out (Giorno partenza)", value=d_in + timedelta(days=1), min_value=d_in + timedelta(days=1))
            note = st.text_area("Note")
            if st.form_submit_button("🚀 INVIA PRENOTAZIONE"):
                # Check sovrapposizione
                sovrapposizione = False
                for _, r in p_casa[p_casa['Stato'] == "Confermata"].iterrows():
                    s_ex, e_ex = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
                    if s_ex and e_ex and (d_in < e_ex and s_ex < d_out):
                        sovrapposizione = True; break
                
                if sovrapposizione:
                    st.error("⚠️ Date già occupate da una prenotazione confermata!")
                else:
                    nuova = pd.DataFrame([{
                        "ID": str(datetime.now().timestamp()), "Casa": casa_scelta, "Utente": st.session_state['user_name'],
                        "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                        "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                    }])
                    conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                    st.balloons()
                    st.query_params["tab"] = "0"
                    st.rerun()

    # --- TAB 2: GESTIONE ---
    with tabs[1]:
        st.header("Gestione Prenotazioni")
        if not df.empty:
            # Calcolo GG per visualizzazione
            def get_gg(r):
                d1, d2 = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
                return (d2 - d1).days if d1 and d2 else 0
            df['GG'] = df.apply(get_gg, axis=1)
            
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'GG', 'Stato']], use_container_width=True, hide_index=True)

            st.divider()
            col_app, col_del = st.columns(2)
            
            with col_app:
                st.subheader("📥 Approva")
                da_approvare = df[(df['Utente'] != st.session_state['user_name']) & (df['Stato'] == "In Attesa")]
                for idx, row in da_approvare.iterrows():
                    voti = [x.strip() for x in str(row['Voti_Ok']).split(",") if x.strip()]
                    if st.session_state['user_name'] not in voti:
                        if st.button(f"Approva: {row['Casa']} - {row['Data_Inizio']} - {row['Utente']}", key=f"ap_{idx}"):
                            voti.append(st.session_state['user_name'])
                            df.at[idx, 'Voti_Ok'] = ", ".join(voti)
                            if len(voti) >= 3: df.at[idx, 'Stato'] = "Confermata"
                            conn.update(worksheet="Prenotazioni", data=df.drop(columns=['GG']))
                            st.query_params["tab"] = "1"
                            st.rerun()

            with col_del:
                st.subheader("🗑️ Elimina le tue")
                le_mie = df[df['Utente'] == st.session_state['user_name']]
                for idx, row in le_mie.iterrows():
                    if st.button(f"Cancella: {row['Casa']} - {row['Data_Inizio']}", key=f"pre_del_{idx}"):
                        st.session_state[f"conf_del_{idx}"] = True
                    
                    if st.session_state.get(f"conf_del_{idx}"):
                        st.error("Confermi l'eliminazione?")
                        c1, c2 = st.columns(2)
                        if c1.button("SÌ, ELIMINA", key=f"real_del_{idx}"):
                            df_new = df.drop(idx).drop(columns=['GG'])
                            conn.update(worksheet="Prenotazioni", data=df_new)
                            del st.session_state[f"conf_del_{idx}"]
                            st.query_params["tab"] = "1"
                            st.rerun()
                        if c2.button("Annulla", key=f"cancel_{idx}"):
                            del st.session_state[f"conf_del_{idx}"]
                            st.rerun()

    # --- TAB 3: CALENDARIO ---
    with tabs[2]:
        legenda = "".join([f'<span class="legenda-item" style="background:{c["color"]}">{u}</span>' for u, c in utenti_cfg.items()])
        st.markdown(f"🗓️ 2026 | {legenda}", unsafe_allow_html=True)
        occ = {}
        for _, r in df.sort_values(by="Stato", ascending=False).iterrows():
            s, e = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
            if s and e:
                curr = s
                while curr < e: # Check-out escluso dal calendario per permettere arrivo lo stesso giorno
                    if curr not in occ or (occ[curr]['s'] == "In Attesa" and r['Stato'] == "Confermata"):
                        occ[curr] = {"u": r['Utente'], "c": r['Casa'], "s": r['Stato']}
                    curr += timedelta(days=1)
        
        for riga in range(6):
            cols = st.columns(2)
            for box in range(2):
                m = riga * 2 + box + 1
                with cols[box]:
                    m_date = datetime(2026, m, 1).date()
                    st.write(f"**{m_date.strftime('%B').upper()}**")
                    html = "<table class='cal-table'><tr>" + "".join([f"<th>{dn}</th>" for dn in ['L','M','M','G','V','S','D']]) + "</tr><tr>"
                    wd = m_date.weekday()
                    html += "<td></td>" * wd
                    days = ((datetime(2026, m+1, 1).date() if m < 12 else datetime(2027,1,1).date()) - m_date).days
                    c_col = wd
                    for d in range(1, days + 1):
                        d_obj = m_date.replace(day=d)
                        bg, content = "", f"<div class='day-num'>{d}</div>"
                        if d_obj in occ:
                            inf = occ[d_obj]
                            bg = f"background-color: {utenti_cfg[inf['u']]['color']}; color: white;" if inf['s'] == "Confermata" else "background-color: #FFFFCC; color: #666;"
                            content += f"<div class='full-cell'>{'🏖️' if inf['c']=='NOLI' else '🏔️'}</div>"
                        html += f"<td class='cal-td' style='{bg}'>{content}</td>"
                        c_col += 1
                        if c_col > 6: html += "</tr><tr>"; c_col = 0
                    st.markdown(html + "</tr></table>", unsafe_allow_html=True)

    # --- TAB 4: STATISTICHE ---
    with tabs[3]:
        st.header("Statistiche")
        if not df.empty:
            # Assicuro ricalcolo per statistiche
            df['GG'] = df.apply(get_gg, axis=1)
            c1, c2 = st.columns(2)
            noli_gg = df[(df['Casa'] == 'NOLI') & (df['Stato'] == 'Confermata')]['GG'].sum()
            limone_gg = df[(df['Casa'] == 'LIMONE') & (df['Stato'] == 'Confermata')]['GG'].sum()
            with c1: st.metric("NOLI 🏖️", f"{int(noli_gg)} gg")
            with c2: st.metric("LIMONE 🏔️", f"{int(limone_gg)} gg")
            
            st.divider()
            st.subheader("Riepilogo per Utente")
            stats = []
            for u in utenti_cfg.keys():
                confermati = df[(df['Utente'] == u) & (df['Stato'] == "Confermata")]['GG'].sum()
                stats.append({"Utente": u, "Confermati (GG)": int(confermati)})
            st.table(pd.DataFrame(stats))
