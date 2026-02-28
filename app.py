import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- CSS ORIGINALE (VERSIONE 1) ---
st.markdown("""
    <style>
    div.stButton > button { width: 100%; border-radius: 12px; font-weight: bold; height: 3.5em; }
    .cal-table { width:100%; border-collapse: collapse; table-layout: fixed; }
    .cal-td { text-align:center; border:1px solid #eee; height:45px; position:relative; vertical-align: middle; }
    .day-num { position: absolute; top: 2px; left: 4px; font-size: 10px; color: #999; }
    .legenda-item { display: inline-block; padding: 4px 10px; border-radius: 6px; margin: 2px; color: white; font-size: 12px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CORE ---
def get_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(worksheet="Prenotazioni", ttl=0)
    data = data.dropna(how='all', axis=0)
    # Pulizia nomi colonne per evitare KeyError (spazi bianchi)
    data.columns = [str(c).strip() for c in data.columns]
    return data

def parse_date(d_str):
    if not d_str or str(d_str).lower() == "nan": return None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try: return datetime.strptime(str(d_str), fmt).date()
        except: continue
    return None

# --- AUTH ---
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
    # --- APP REALE (VERSIONE DEFINITIVA 1) ---
    df = get_data()
    mio_nome = st.session_state['user_name']
    utenti_cfg = {"Anita": "#FF4B4B", "Chiara": "#FFC0CB", "Lorenzo": "#1C83E1", "Gianluca": "#28A745"}

    st.write(f"Connesso come: **{mio_nome}**")
    if st.button("Logout", key="lo_btn"): 
        st.session_state['authenticated'] = False
        st.rerun()

    # Tabs con icone originali
    tab1, tab2, tab3, tab4 = st.tabs(["📅 PRENOTA", "📊 GESTIONE", "🗓️ CALENDARIO", "📈 STATISTICHE"])

    with tab1:
        st.header("Nuova Prenotazione")
        casa = st.selectbox("Meta", ["NOLI", "LIMONE"])
        with st.form("new_book"):
            d_in = st.date_input("Check-in")
            d_out = st.date_input("Check-out")
            note = st.text_input("Note")
            if st.form_submit_button("🚀 INVIA"):
                new_row = pd.DataFrame([{
                    "ID": str(time.time()), "Casa": casa, "Utente": mio_nome,
                    "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                    "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                }])
                conn = st.connection("gsheets", type=GSheetsConnection)
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Prenotazioni", data=updated_df)
                st.success("Richiesta inviata!")
                time.sleep(1)
                st.rerun()

    with tab2:
        st.header("Gestione e Approvazioni")
        if not df.empty:
            st.subheader("Riepilogo")
            # Mostra solo colonne utili
            view_df = df[['Casa', 'Utente', 'Data_Inizio', 'Stato']].copy()
            st.dataframe(view_df, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("👍 Richieste da Approvare")
            # Filtro: Non mie, In attesa, e non ancora votate da me
            pendenti = df[(df['Utente'] != mio_nome) & (df['Stato'] == "In Attesa")]
            for idx, r in pendenti.iterrows():
                voti = str(r.get('Voti_Ok', ""))
                if mio_nome not in voti:
                    if st.button(f"Approva: {r['Casa']} | {r['Data_Inizio']} ({r['Utente']})", key=f"app_{idx}"):
                        new_voti = (voti + f", {mio_nome}").strip(", ")
                        df.at[idx, 'Voti_Ok'] = new_voti
                        # Se ha 3 voti, conferma
                        if len(new_voti.split(',')) >= 3:
                            df.at[idx, 'Stato'] = "Confermata"
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        conn.update(worksheet="Prenotazioni", data=df)
                        st.rerun()

    with tab3:
        st.header("Calendario 2026")
        legenda_html = "".join([f'<span class="legenda-item" style="background:{c}">{u}</span>' for u, c in utenti_cfg.items()])
        st.markdown(f"**Legenda:** {legenda_html}", unsafe_allow_html=True)
        
        # Mappa occupazione
        occ = {}
        for _, r in df.iterrows():
            s, e = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
            if s and e:
                curr = s
                while curr < e:
                    occ[(curr, r['Casa'])] = {"u": r['Utente'], "s": r['Stato']}
                    curr += timedelta(days=1)

        # Griglia mesi
        for m in range(3, 10): # Visualizza da Marzo a Settembre 2026
            m_date = datetime(2026, m, 1).date()
            st.write(f"### {m_date.strftime('%B 2026')}")
            
            html = "<table class='cal-table'><tr><th>L</th><th>M</th><th>M</th><th>G</th><th>V</th><th>S</th><th>D</th></tr><tr>"
            
            # Padding iniziale
            wd = m_date.weekday()
            html += "<td></td>" * wd
            
            # Giorni del mese
            last_day = (datetime(2026, m % 12 + 1, 1).date() - timedelta(days=1)).day if m < 12 else 31
            curr_col = wd
            for d in range(1, last_day + 1):
                d_obj = m_date.replace(day=d)
                bg, icona = "", ""
                
                rn, rl = occ.get((d_obj, "NOLI")), occ.get((d_obj, "LIMONE"))
                if rn or rl:
                    res = rn if rn else rl
                    if res['s'] == "Confermata":
                        bg = f"background-color: {utenti_cfg.get(res['u'], '#ddd')}; color: white;"
                    else:
                        bg = "background-color: #FFFFCC;"
                    if rn: icona += "🏖️"
                    if rl: icona += "🏔️"
                
                html += f"<td class='cal-td' style='{bg}'><div class='day-num'>{d}</div>{icona}</td>"
                curr_col += 1
                if curr_col > 6:
                    html += "</tr><tr>"
                    curr_col = 0
            
            st.markdown(html + "</tr></table>", unsafe_allow_html=True)

    with tab4:
        st.header("Statistiche")
        if not df.empty:
            conf = df[df['Stato'] == "Confermata"]
            st.bar_chart(conf['Utente'].value_counts())
