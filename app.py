import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- CSS DEFINITIVO ---
st.markdown("""
    <style>
    [data-testid="stHeader"] { z-index: 999; }
    .sticky-wrapper {
        position: -webkit-sticky;
        position: sticky;
        top: 0;
        z-index: 1000;
        background-color: white;
        padding: 10px 0;
        border-bottom: 2px solid #f0f2f6;
    }
    html, body, [class*="css"] { font-size: 14px; }
    button[data-baseweb="tab"] p { font-size: 15px !important; font-weight: bold !important; }
    .cal-table { width:100%; table-layout: fixed; border-spacing: 1px; border-collapse: separate; }
    .cal-td { text-align:center; height:35px; border-radius:3px; border:1px solid #f0f0f0; padding:0 !important; position:relative; }
    .day-num { position: absolute; top: 1px; left: 2px; font-size: 9px; color: #666; z-index: 5; }
    .full-cell { height: 100%; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 14px; }
    .legenda-item { display: inline-block; padding: 4px 10px; border-radius: 5px; margin: 2px; color: white; font-size: 11px; font-weight: bold; }
    .stImage > img { border-radius: 10px; }
    
    /* Stile per il tasto Logout in alto */
    .logout-container {
        display: flex;
        justify-content: flex-end;
        padding: 10px;
    }
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

# --- CONFIGURAZIONE UTENTI ---
utenti_config = {
    "Anita": {"pin": "1111", "color": "#FF4B4B"},
    "Chiara": {"pin": "4444", "color": "#FFC0CB"},
    "Lorenzo": {"pin": "1234", "color": "#1C83E1"},
    "Gianluca": {"pin": "1191", "color": "#28A745"}
}
icone_case = {"LIMONE": "🏔️", "NOLI": "🏖️"}

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.title("🏠 Family Booking")
    st.subheader("🔐 Accesso")
    u_log = st.selectbox("Chi sei?", ["-- Seleziona --"] + list(utenti_config.keys()))
    p_log = st.text_input("Inserisci il PIN", type="password")
    if st.button("Entra"):
        if u_log != "-- Seleziona --" and p_log == utenti_config[u_log]["pin"]:
            st.session_state['authenticated'] = True
            st.session_state['user_name'] = u_log
            st.rerun()
        else: st.error("PIN errato")
else:
    # --- LOGOUT IN ALTO (MODIFICA 1) ---
    col_info, col_logout = st.columns([0.8, 0.2])
    with col_info:
        st.write(f"Connesso come: **{st.session_state['user_name']}**")
    with col_logout:
        if st.button("🔴 Logout", key="top_logout"):
            st.session_state['authenticated'] = False
            st.rerun()

    df = get_data()
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📅 PRENOTA", "📊 GESTIONE", "🗓️ CALENDARIO", "📈 STATISTICHE"])

    # --- TAB 1: PRENOTA ---
    with tab1:
        st.header("Nuova Prenotazione")
        oggi = datetime.now().date()
        casa_scelta = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
        
        f_nome = "Noli.jpg" if casa_scelta == "NOLI" else "Limone.jpg"
        if os.path.exists(f_nome): st.image(f_nome, width=280)

        p_casa = df[df['Casa'] == casa_scelta].copy()
        if not p_casa.empty:
            st.write("---")
            for _, r in p_casa.iterrows():
                color = "#FF4B4B" if r['Stato'] == "Confermata" else "#FFD700"
                label = "🚫 OCCUPATO" if r['Stato'] == "Confermata" else "⏳ RICHIESTO"
                st.markdown(f"<span style='color:{color}; font-weight:bold;'>{label}</span>: {r['Data_Inizio']} al {r['Data_Fine']} - {r['Utente']}", unsafe_allow_html=True)
            st.write("---")

        d_in = st.date_input("Check-in", value=oggi + timedelta(days=1), min_value=oggi)
        d_out = st.date_input("Check-out", value=d_in + timedelta(days=1), min_value=d_in + timedelta(days=1))
        
        overlap = False
        conflitto = ""
        for _, r in p_casa.iterrows():
            s_ex = parse_date(r['Data_Inizio'])
            e_ex = parse_date(r['Data_Fine'])
            if s_ex and e_ex:
                if d_in <= e_ex and s_ex <= d_out:
                    overlap = True
                    conflitto = f"{r['Utente']} ({r['Data_Inizio']} - {r['Data_Fine']})"
                    break
        
        if overlap:
            st.error(f"⚠️ DATE GIÀ OCCUPATE da: {conflitto}")
        else:
            giorni_calc = (d_out - d_in).days + 1
            st.success(f"✅ Date disponibili per {giorni_calc} giorni")
            note = st.text_area("Note")
            if st.button("🚀 INVIA PRENOTAZIONE"):
                nuova = pd.DataFrame([{
                    "ID": str(datetime.now().timestamp()), "Casa": casa_scelta, "Utente": st.session_state['user_name'],
                    "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                    "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                }])
                conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                st.success("Inviato!"); time.sleep(1); st.rerun()

    # --- TAB 2: GESTIONE ---
    with tab2:
        st.header("Elenco prenotazioni")
        if not df.empty:
            all_u = set(utenti_config.keys())
            def process_row(row):
                d1, d2 = parse_date(row['Data_Inizio']), parse_date(row['Data_Fine'])
                gg = (d2 - d1).days + 1 if d1 and d2 else 0
                v = [x.strip() for x in str(row['Voti_Ok']).split(",") if x.strip()]
                m = list(all_u - (set(v) | {row['Utente']}))
                return pd.Series([gg, ", ".join(v), ", ".join(m)])

            df[['Giorni richiesti', 'Approvato', 'Mancano']] = df.apply(process_row, axis=1)
            cols = ['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Giorni richiesti', 'Stato', 'Approvato', 'Mancano']
            st.dataframe(df[cols], use_container_width=True, hide_index=True)
            
            st.divider()
            # MODIFICA 2: ETICHETTE PULSANTI DETTAGLIATE
            st.subheader("🗳️ Approva")
            for idx, row in df.iterrows():
                if row['Utente'] != st.session_state['user_name'] and row['Stato'] == "In Attesa":
                    v_list = [x.strip() for x in str(row['Voti_Ok']).split(",") if x.strip()]
                    if st.session_state['user_name'] not in v_list:
                        label_approva = f"Approva: {row['Casa']} | {row['Data_Inizio']} - {row['Data_Fine']} | ({row['Utente']})"
                        if st.button(label_approva, key=f"v_{idx}"):
                            v_list.append(st.session_state['user_name'])
                            df.at[idx, 'Voti_Ok'] = ", ".join(v_list)
                            if len(v_list) >= 3: df.at[idx, 'Stato'] = "Confermata"
                            conn.update(worksheet="Prenotazioni", data=df.drop(columns=['Giorni richiesti', 'Approvato', 'Mancano']))
                            st.rerun()
            
            st.subheader("🗑️ Elimina le tue")
            for idx, row in df[df['Utente'] == st.session_state['user_name']].iterrows():
                label_elimina = f"Cancella: {row['Casa']} | {row['Data_Inizio']} - {row['Data_Fine']}"
                if st.button(label_elimina, key=f"del_{idx}"):
                    df_save = df.drop(idx).drop(columns=['Giorni richiesti', 'Approvato', 'Mancano'])
                    conn.update(worksheet="Prenotazioni", data=df_save); st.rerun()

    # --- TAB 3: CALENDARIO ---
    with tab3:
        leg_h = "".join([f'<span class="legenda-item" style="background:{c["color"]}">{u}</span>' for u, c in utenti_config.items()])
        leg_h += '<span class="legenda-item" style="background:#FFFFCC; color:#666; border:1px solid #ffd700">In Attesa</span>'
        st.markdown(f'<div class="sticky-wrapper"><h3 style="margin:0;">🗓️ Calendario 2026</h3>{leg_h}</div>', unsafe_allow_html=True)

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
            st.divider()
            stats = []
            for u in utenti_config.keys():
                c = df[(df['Utente'] == u) & (df['Stato'] == "Confermata")]['GG'].sum()
                a = df[(df['Utente'] == u) & (df['Stato'] == "In Attesa")]['GG'].sum()
                stats.append({"Utente": u, "Confermati": int(c), "In attesa": int(a), "Totale": int(c+a)})
            st.dataframe(pd.DataFrame(stats), hide_index=True)
