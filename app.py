import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

st.markdown("""
    <style>
    div.stButton > button { width: 100% !important; height: 3.5em !important; border-radius: 12px !important; font-weight: bold !important; }
    .cal-table { width:100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 20px; }
    .cal-td { text-align:center; border:1px solid #eee; height:45px; position:relative; vertical-align: middle; }
    .day-num { position: absolute; top: 2px; left: 4px; font-size: 10px; color: #999; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CORE ---
def get_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(worksheet="Prenotazioni", ttl=0)
    data = data.dropna(how='all', axis=0)
    data.columns = [str(c).strip() for c in data.columns]
    cols = ['ID', 'Casa', 'Utente', 'Stato', 'Voti_Ok', 'Data_Inizio', 'Data_Fine', 'Note']
    for col in cols:
        if col not in data.columns: data[col] = ""
        data[col] = data[col].fillna("").astype(str).str.strip()
    return data[cols]

def parse_date(d_str):
    if not d_str or str(d_str).lower() in ["", "nan", "none", "nat"]: return None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try: return datetime.strptime(str(d_str), fmt).date()
        except: continue
    return None

def scrivi_log(utente, azione, dettaglio):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        log_df = conn.read(worksheet="Log", ttl=0)
        nuovo_log = pd.DataFrame([{
            "Data_Ora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "Utente": utente,
            "Azione": azione,
            "Dettaglio": dettaglio
        }])
        updated_log = pd.concat([log_df, nuovo_log], ignore_index=True)
        conn.update(worksheet="Log", data=updated_log)
    except:
        st.warning("Impossibile scrivere il Log. Verifica che esista il foglio 'Log'.")

# --- AUTENTICAZIONE ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

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
    df = get_data()
    conn = st.connection("gsheets", type=GSheetsConnection)
    mio_nome = st.session_state['user_name']
    utenti_cfg = {"Anita": "#FF4B4B", "Chiara": "#FFC0CB", "Lorenzo": "#1C83E1", "Gianluca": "#28A745"}
    db_cols = ['ID', 'Casa', 'Utente', 'Stato', 'Voti_Ok', 'Data_Inizio', 'Data_Fine', 'Note']

    tabs = st.tabs(["📅 PRENOTA", "📊 GESTIONE", "🗓️ CALENDARIO", "📈 STATISTICHE"])

    # --- TAB 1: PRENOTA ---
    with tabs[0]:
        st.header("Nuova Prenotazione")
        casa_scelta = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
        
        img_file = "Noli.jpg" if casa_scelta == "NOLI" else "Limone.jpg"
        if os.path.exists(img_file):
            st.image(img_file, width=500)

        st.subheader(f"Stato attuale: {casa_scelta}")
        df_casa = df[df['Casa'] == casa_scelta]
        for _, r in df_casa.iterrows():
            v_list = [v.strip() for v in str(r['Voti_Ok']).split(',') if v.strip()]
            color, label = ("#FF4B4B", "🔴 CONFERMATA") if len(v_list) >= 3 else ("#FFD700", "⏳ RICHIESTA")
            st.markdown(f"<div style='color:{color}; font-weight:bold;'>{label}: {r['Data_Inizio']} - {r['Data_Fine']} - {r['Utente']}</div>", unsafe_allow_html=True)

        with st.form("form_prenota"):
            d_in = st.date_input("Check-in", value=datetime.now().date())
            d_out = st.date_input("Check-out", value=datetime.now().date() + timedelta(days=1))
            note = st.text_area("Note")
            if st.form_submit_button("🚀 INVIA PRENOTAZIONE"):
                conflitto = False
                for _, r in df_casa.iterrows():
                    s_ex, e_ex = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
                    if s_ex and e_ex and (d_in < e_ex) and (d_out > s_ex):
                        conflitto = True
                        st.error(f"❌ Errore: Date occupate da {r['Utente']} ({r['Data_Inizio']} - {r['Data_Fine']})")
                        break
                
                if not conflitto:
                    if d_out <= d_in: st.error("La data di fine deve essere successiva all'inizio")
                    else:
                        new_r = pd.DataFrame([{"ID": str(time.time()), "Casa": casa_scelta, "Utente": mio_nome, "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'), "Stato": "In Attesa", "Voti_Ok": "", "Note": note}])
                        conn.update(worksheet="Prenotazioni", data=pd.concat([df, new_r], ignore_index=True)[db_cols])
                        scrivi_log(mio_nome, "PRENOTAZIONE", f"{casa_scelta}: {d_in} al {d_out}")
                        st.success("Prenotazione salvata!"); time.sleep(1); st.rerun()

    # --- TAB 2: GESTIONE ---
    with tabs[1]:
        st.header("Gestione Prenotazioni")
        if not df.empty:
            def processa(row):
                voti = [v.strip() for v in str(row['Voti_Ok']).split(',') if v.strip()]
                mancano = [u for u in utenti_cfg.keys() if u != row['Utente'] and u not in voti]
                return pd.Series([", ".join(voti), ", ".join(mancano), "Confermata" if len(voti) >= 3 else "In Attesa"])
            
            df_view = df.copy()
            df_view[['Approvati', 'Mancano', 'Stato_R']] = df_view.apply(processa, axis=1)
            
            st.subheader("Tabella Riepilogativa")
            st.dataframe(df_view[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato_R', 'Mancano']], use_container_width=True, hide_index=True)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("👍 Approva")
                pendenti = df_view[(df_view['Utente'] != mio_nome) & (df_view['Stato_R'] == "In Attesa") & (~df_view['Approvati'].str.contains(mio_nome))]
                for idx, r in pendenti.iterrows():
                    if st.button(f"APPROVA: {r['Casa']} - {r['Utente']} ({r['Data_Inizio']})", key=f"ap_{idx}"):
                        df.at[idx, 'Voti_Ok'] = (str(r['Voti_Ok']) + f", {mio_nome}").strip(", ")
                        conn.update(worksheet="Prenotazioni", data=df[db_cols])
                        scrivi_log(mio_nome, "APPROVAZIONE", f"Approvato {r['Utente']} per {r['Casa']} ({r['Data_Inizio']})")
                        st.rerun()
            with col_b:
                st.subheader("🗑️ Elimina")
                mie_pren = df[df['Utente'] == mio_nome]
                for idx, r in mie_pren.iterrows():
                    if st.button(f"ELIMINA: {r['Casa']} ({r['Data_Inizio']})", key=f"del_{idx}"):
                        conn.update(worksheet="Prenotazioni", data=df.drop(index=idx)[db_cols])
                        scrivi_log(mio_nome, "ELIMINAZIONE", f"Cancellata prenotazione {r['Casa']} del {r['Data_Inizio']}")
                        st.rerun()

    # --- TAB 3: CALENDARIO ---
    with tabs[2]:
        st.header("Calendario Occupazioni 2026")
        occ = {}
        for _, r in df.iterrows():
            s, e = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
            if s and e:
                curr = s
                while curr < e:
                    v_count = len([v for v in str(r['Voti_Ok']).split(',') if v.strip()])
                    occ[(curr, r['Casa'])] = {"u": r['Utente'], "v": v_count}
                    curr += timedelta(days=1)
        
        for m in range(1, 13):
            m_date = datetime(2026, m, 1).date()
            st.write(f"### {m_date.strftime('%B %Y').upper()}")
            if m == 12: last_day = datetime(2026, 12, 31).date()
            else: last_day = datetime(2026, m + 1, 1).date() - timedelta(days=1)
            
            html = "<table class='cal-table'><tr><th>L</th><th>M</th><th>M</th><th>G</th><th>V</th><th>S</th><th>D</th></tr><tr>"
            wd = m_date.weekday()
            html += "<td></td>" * wd
            curr_c = wd
            for d in range(1, last_day.day + 1):
                d_obj = m_date.replace(day=d)
                bg, ico = "", ""
                for meta, sym in [("NOLI", "🏖️"), ("LIMONE", "🏔️")]:
                    res = occ.get((d_obj, meta))
                    if res:
                        bg = f"background:{utenti_cfg.get(res['u'], '#eee')};" if res['v'] >= 3 else "background:#FFFFCC;"
                        ico += sym
                html += f"<td class='cal-td' style='{bg}'><div class='day-num'>{d}</div>{ico}</td>"
                curr_c += 1
                if curr_c > 6: html += "</tr><tr>"; curr_c = 0
            st.markdown(html + "</tr></table>", unsafe_allow_html=True)

    # --- TAB 4: STATISTICHE ---
    with tabs[3]:
        st.header("Statistiche 2026")
        def calc_gg(r):
            s, e = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
            return (e-s).days if s and e else 0
        df['GG'] = df.apply(calc_gg, axis=1)
        df['Conf'] = df['Voti_Ok'].apply(lambda x: len([v for v in str(x).split(',') if v.strip()]) >= 3)
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("NOLI 🏖️")
            st.metric("Giorni Confermati", int(df[(df['Casa']=='NOLI') & (df['Conf'])]['GG'].sum()))
        with c2:
            st.subheader("LIMONE 🏔️")
            st.metric("Giorni Confermati", int(df[(df['Casa']=='LIMONE') & (df['Conf'])]['GG'].sum()))
        
        st.divider()
        st.subheader("Riepilogo per Utente")
        stats = []
        for u in utenti_cfg.keys():
            stats.append({
                "Utente": u,
                "Confermati 🔴 (gg)": int(df[(df['Utente']==u) & (df['Conf'])]['GG'].sum()),
                "Richiesti ⏳ (gg)": int(df[(df['Utente']==u) & (~df['Conf'])]['GG'].sum())
            })
        st.table(pd.DataFrame(stats))
