import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- CSS DEFINITIVO (STICKY E OTTIMIZZAZIONE MOBILE) ---
st.markdown("""
    <style>
    [data-testid="stHeader"] { z-index: 999; }
    
    /* BLOCCA RIQUADRI: Legenda e Titolo Calendario */
    .sticky-wrapper {
        position: -webkit-sticky;
        position: sticky;
        top: 0;
        z-index: 1000;
        background-color: white;
        padding: 10px 0;
        border-bottom: 2px solid #f0f2f6;
    }

    /* Stile generale e Tab */
    html, body, [class*="css"] { font-size: 14px; }
    button[data-baseweb="tab"] p { font-size: 15px !important; font-weight: bold !important; }
    
    /* Calendario compatto */
    .cal-table { width:100%; table-layout: fixed; border-spacing: 1px; border-collapse: separate; }
    .cal-td { text-align:center; height:35px; border-radius:3px; border:1px solid #f0f0f0; padding:0 !important; position:relative; }
    .day-num { position: absolute; top: 1px; left: 2px; font-size: 9px; color: #666; z-index: 5; }
    .full-cell { height: 100%; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 14px; }
    
    /* Legenda */
    .legenda-item { display: inline-block; padding: 4px 10px; border-radius: 5px; margin: 2px; color: white; font-size: 11px; font-weight: bold; }
    
    /* Input e Immagini */
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
    try:
        return datetime.strptime(d_str, '%d/%m/%Y').date()
    except:
        return None

# --- CONFIGURAZIONE UTENTI ---
utenti_config = {
    "Anita": {"pin": "1111", "color": "#FF4B4B"},
    "Chiara": {"pin": "4444", "color": "#FFC0CB"},
    "Lorenzo": {"pin": "1234", "color": "#1C83E1"},
    "Gianluca": {"pin": "1191", "color": "#28A745"}
}
icone_case = {"LIMONE": "🏔️", "NOLI": "🏖️"}

# --- GESTIONE LOGIN PERSISTENTE ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.title("🏠 Family Booking")
    st.subheader("🔐 Accesso")
    with st.container():
        u_log = st.selectbox("Chi sei?", ["-- Seleziona --"] + list(utenti_config.keys()))
        p_log = st.text_input("Inserisci il PIN", type="password")
        if st.button("Entra"):
            if u_log != "-- Seleziona --" and p_log == utenti_config[u_log]["pin"]:
                st.session_state['authenticated'] = True
                st.session_state['user_name'] = u_log
                st.rerun()
            else:
                st.error("PIN non corretto")
else:
    # --- APP DOPO IL LOGIN ---
    current_user = st.session_state['user_name']
    df = get_data()
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    st.write(f"Connesso come: **{current_user}**")

    tab1, tab2, tab3, tab4 = st.tabs(["📅 PRENOTA", "📊 GESTIONE", "🗓️ CALENDARIO", "📈 STATISTICHE"])

    # --- TAB 1: PRENOTA (CON VALIDAZIONE DATE) ---
    with tab1:
        st.header("Nuova Prenotazione")
        oggi = datetime.now().date()
        casa_scelta = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
        
        f_nome = "Noli.jpg" if casa_scelta == "NOLI" else "Limone.jpg"
        if os.path.exists(f_nome):
            st.image(f_nome, width=280)

        d_in = st.date_input("Check-in", value=oggi + timedelta(days=1), min_value=oggi)
        d_out = st.date_input("Check-out", value=d_in + timedelta(days=1), min_value=d_in + timedelta(days=1))
        
        # LOGICA DI CONTROLLO SOVRAPPOSIZIONI
        overlap = False
        conflitto_info = ""
        p_casa = df[df['Casa'] == casa_scelta].copy()
        
        for _, r in p_casa.iterrows():
            start_ext = parse_date(r['Data_Inizio'])
            end_ext = parse_date(r['Data_Fine'])
            if start_ext and end_ext:
                # Sovrapposizione se: (Inizio1 <= Fine2) AND (Inizio2 <= Fine1)
                if d_in <= end_ext and start_ext <= d_out:
                    overlap = True
                    conflitto_info = f"{r['Utente']} ({r['Data_Inizio']} - {r['Data_Fine']})"
                    break
        
        if overlap:
            st.error(f"⚠️ **DATE NON DISPONIBILI!** Sovrapposizione con: {conflitto_info}")
        else:
            giorni_p = (d_out - d_in).days + 1
            st.success(f"✅ Date disponibili per **{giorni_p}** giorni")
            note = st.text_area("Note aggiuntive")
            if st.button("🚀 INVIA PRENOTAZIONE"):
                nuova = pd.DataFrame([{
                    "ID": str(datetime.now().timestamp()), "Casa": casa_scelta, "Utente": current_user,
                    "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                    "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                }])
                conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                st.success("Richiesta inviata!"); time.sleep(1); st.rerun()

    # --- TAB 2: GESTIONE (CON GIORNI RICHIESTI) ---
    with tab2:
        st.header("Elenco prenotazioni")
        if not df.empty:
            all_u = set(utenti_config.keys())
            
            def process_gestione(row):
                d1 = parse_date(row['Data_Inizio'])
                d2 = parse_date(row['Data_Fine'])
                diff = (d2 - d1).days + 1 if d1 and d2 else 0
                v = [x.strip() for x in str(row['Voti_Ok']).split(",") if x.strip()]
                m = list(all_u - (set(v) | {row['Utente']}))
                return pd.Series([diff, ", ".join(v), ", ".join(m)])

            # Applica la funzione e crea le colonne calcolate
            calc_cols = df.apply(process_gestione, axis=1)
            df['Giorni richiesti'] = calc_cols[0]
            df['Approvato'] = calc_cols[1]
            df['Mancano'] = calc_cols[2]
            
            # Ordine colonne: Giorni richiesti dopo Data_Fine
            cols_gestione = ['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Giorni richiesti', 'Stato', 'Approvato', 'Mancano']
            st.dataframe(df[cols_gestione], use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("🗳️ Approva")
            for idx, row in df.iterrows():
                if row['Utente'] != current_user and row['Stato'] == "In Attesa":
                    v_list = [x.strip() for x in str(row['Voti_Ok']).split(",") if x.strip()]
                    if current_user not in v_list:
                        if st.button(f"Approva {row['Casa']} ({row['Data_Inizio']})", key=f"v_{idx}"):
                            v_list.append(current_user)
                            df.at[idx, 'Voti_Ok'] = ", ".join(v_list)
                            if len(v_list) >= 3: df.at[idx, 'Stato'] = "Confermata"
                            # Salvataggio pulito senza le colonne calcolate temporanee
                            df_to_save = df.drop(columns=['Giorni richiesti', 'Approvato', 'Mancano'])
                            conn.update(worksheet="Prenotazioni", data=df_to_save)
                            st.rerun()
            
            st.subheader("🗑️ Elimina le tue")
            for idx, row in df[df['Utente'] == current_user].iterrows():
                if st.button(f"Cancella {row['Casa']} {row['Data_Inizio']}", key=f"del_{idx}"):
                    df_save = df.drop(idx).drop(columns=['Giorni richiesti', 'Approvato', 'Mancano'])
                    conn.update(worksheet="Prenotazioni", data=df_save); st.rerun()

    # --- TAB 3: CALENDARIO (STICKY) ---
    with tab3:
        legenda_h = "".join([f'<span class="legenda-item" style="background:{c["color"]}">{u}</span>' for u, c in utenti_config.items()])
        legenda_h += '<span class="legenda-item" style="background:#FFFFCC; color:#666; border:1px solid #ffd700">In Attesa</span>'
        
        st.markdown(f"""
            <div class="sticky-wrapper">
                <h3 style="margin:0; padding-bottom:5px;">🗓️ Calendario 2026</h3>
                {legenda_h}
            </div>
        """, unsafe_allow_html=True)

        occupied = {}
        df_s = df.sort_values(by="Stato", ascending=False) 
        for _, r in df_s.iterrows():
            s_date = parse_date(r['Data_Inizio'])
            e_date = parse_date(r['Data_Fine'])
            if s_date and e_date:
                curr = s_date
                while curr <= e_date:
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
                st.metric("NOLI 🏖️", f"{df[(df['Casa'] == 'NOLI') & (df['Stato'] == 'Confermata')]['GG'].sum()} gg")
            with c2:
                st.metric("LIMONE 🏔️", f"{df[(df['Casa'] == 'LIMONE') & (df['Stato'] == 'Confermata')]['GG'].sum()} gg")
            
            st.divider()
            stats = []
            for u in utenti_config.keys():
                c = df[(df['Utente'] == u) & (df['Stato'] == "Confermata")]['GG'].sum()
                a = df[(df['Utente'] == u) & (df['Stato'] == "In Attesa")]['GG'].sum()
                stats.append({"Utente": u, "Confermati": int(c), "In attesa": int(a), "Totale": int(c+a)})
            st.dataframe(pd.DataFrame(stats), hide_index=True)
            
            st.divider()
            if st.button("🔴 Logout"):
                st.session_state['authenticated'] = False
                st.rerun()
