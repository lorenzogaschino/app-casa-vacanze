import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- CSS (Ottimizzato per scorrimento e pulsanti) ---
st.markdown("""
    <style>
    div.stButton > button { width: 100%; border-radius: 10px; font-weight: bold; height: 3.5em; border: 1px solid #ddd; }
    .cal-table { width:100%; table-layout: fixed; border-collapse: collapse; margin-bottom: 20px; }
    .cal-td { text-align:center; height:45px; border:1px solid #f0f0f0; position:relative; vertical-align: middle; }
    .day-num { position: absolute; top: 2px; left: 4px; font-size: 10px; color: #888; }
    .legenda-item { display: inline-block; padding: 4px 10px; border-radius: 5px; margin: 2px; color: white; font-weight: bold; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CORE ---
def get_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(worksheet="Prenotazioni", ttl=0)
        # 1. Rimuove righe completamente vuote
        data = data.dropna(how='all', axis=0)
        # 2. Normalizza i nomi delle colonne (fondamentale per evitare KeyError)
        data.columns = [str(c).strip() for c in data.columns]
        # 3. Converte tutto in stringa per evitare errori di confronto tra ID numerici e stringa
        for col in data.columns:
            data[col] = data[col].astype(str).replace('nan', '').str.strip()
        return data
    except Exception as e:
        st.error(f"Errore connessione Sheet: {e}")
        return pd.DataFrame()

def parse_date(d_str):
    if not d_str or d_str == "": return None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try: return datetime.strptime(d_str, fmt).date()
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
    # --- INTERFACCIA PRINCIPALE ---
    df = get_data()
    mio_nome = st.session_state['user_name']
    utenti_cfg = {"Anita": "#FF4B4B", "Chiara": "#FFC0CB", "Lorenzo": "#1C83E1", "Gianluca": "#28A745"}

    # Header con Logout
    c_inf, c_log = st.columns([0.8, 0.2])
    c_inf.write(f"Ciao **{mio_nome}**!")
    if c_log.button("Logout 🔴"):
        st.session_state['authenticated'] = False
        st.rerun()

    # Navigazione (Senza chiave fissa per evitare TypeError)
    tab1, tab2, tab3, tab4 = st.tabs(["📅 PRENOTA", "📊 GESTIONE", "🗓️ CALENDARIO", "📈 STATISTICHE"])

    with tab1:
        st.header("Nuova Prenotazione")
        casa = st.selectbox("Destinazione", ["NOLI", "LIMONE"])
        with st.form("form_booking"):
            d_in = st.date_input("Check-in", value=datetime.now().date() + timedelta(days=1))
            d_out = st.date_input("Check-out", value=datetime.now().date() + timedelta(days=2))
            note = st.text_area("Note aggiuntive")
            if st.form_submit_button("🚀 INVIA"):
                if d_out <= d_in:
                    st.error("La data di fine deve essere successiva all'inizio.")
                else:
                    new_row = pd.DataFrame([{
                        "ID": str(time.time()), "Casa": casa, "Utente": mio_nome,
                        "Data_Inizio": d_in.strftime('%d/%m/%Y'), 
                        "Data_Fine": d_out.strftime('%d/%m/%Y'),
                        "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                    }])
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(worksheet="Prenotazioni", data=updated_df)
                    st.success("Prenotazione salvata!")
                    time.sleep(1)
                    st.rerun()

    with tab2:
        st.header("Gestione e Approvazioni")
        if not df.empty:
            # Riepilogo tabellare pulito
            view_cols = [c for c in ['Casa', 'Utente', 'Data_Inizio', 'Stato', 'Voti_Ok'] if c in df.columns]
            st.dataframe(df[view_cols], use_container_width=True, hide_index=True)
            
            st.divider()
            # Sezione Approvazioni
            st.subheader("👍 Richieste da Approvare")
            pendenti = df[(df['Utente'] != mio_nome) & (df['Stato'] == "In Attesa")]
            
            count_app = 0
            for idx, r in pendenti.iterrows():
                voti_attuali = str(r.get('Voti_Ok', ""))
                lista_voti = [v.strip() for v in voti_attuali.split(',') if v.strip()]
                
                if mio_nome not in lista_voti:
                    count_app += 1
                    col_b1, col_b2 = st.columns([0.7, 0.3])
                    col_b1.write(f"**{r['Casa']}** | {r['Data_Inizio']} ({r['Utente']})")
                    if col_b2.button("APPROVA", key=f"app_{r['ID']}"):
                        lista_voti.append(mio_nome)
                        nuovi_voti_str = ", ".join(lista_voti)
                        df.at[idx, 'Voti_Ok'] = nuovi_voti_str
                        
                        # Se ha 3 voti totali (escluso l'autore), passa a confermata
                        if len(lista_voti) >= 3:
                            df.at[idx, 'Stato'] = "Confermata"
                        
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        conn.update(worksheet="Prenotazioni", data=df)
                        st.toast("Approvazione inviata!")
                        time.sleep(1)
                        st.rerun()
            
            if count_app == 0:
                st.info("Nessuna prenotazione in attesa del tuo voto.")

    with tab3:
        # Legenda colorata
        legenda_html = "".join([f'<span class="legenda-item" style="background:{color}">{user}</span>' for user, color in utenti_cfg.items()])
        st.markdown(f"**Legenda:** {legenda_html} <span class='legenda-item' style='background:#FFFFCC; color:#666; border:1px solid #ccc'>In Attesa</span>", unsafe_allow_html=True)
        
        # Mappa occupazione
        occ = {}
        for _, r in df.iterrows():
            s, e = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
            if s and e:
                curr = s
                while curr < e:
                    occ[(curr, r['Casa'])] = {"u": r['Utente'], "s": r['Stato']}
                    curr += timedelta(days=1)

        # Calendario a 2 colonne (Mobile friendly)
        for mese in range(1, 13):
            m_date = datetime(2026, mese, 1).date()
            st.write(f"### {m_date.strftime('%B').upper()}")
            
            html = "<table class='cal-table'><tr>" + "".join([f"<th>{d}</th>" for d in ['L','M','M','G','V','S','D']]) + "</tr><tr>"
            
            # Spazi vuoti inizio mese
            primo_gg = m_date.weekday()
            html += "<td></td>" * primo_gg
            
            # Giorni del mese
            ultimo_gg = (datetime(2026, mese % 12 + 1, 1).date() - timedelta(days=1)).day if mese < 12 else 31
            
            curr_col = primo_gg
            for d in range(1, ultimo_gg + 1):
                d_obj = m_date.replace(day=d)
                bg, icone = "", ""
                
                # Check occupazione Noli e Limone
                res_n = occ.get((d_obj, "NOLI"))
                res_l = occ.get((d_obj, "LIMONE"))
                
                if res_n or res_l:
                    # Se almeno una è confermata, colora la cella col colore dell'utente
                    res_prioritario = res_n if res_n and res_n['s'] == "Confermata" else (res_l if res_l and res_l['s'] == "Confermata" else (res_n or res_l))
                    if res_prioritario['s'] == "Confermata":
                        bg = f"background-color: {utenti_cfg.get(res_prioritario['u'], '#ddd')}; color: white;"
                    else:
                        bg = "background-color: #FFFFCC; border: 1px dashed #FFD700;"
                    
                    if res_n: icone += "🏖️"
                    if res_l: icone += "🏔️"
                
                html += f"<td class='cal-td' style='{bg}'><div class='day-num'>{d}</div>{icone}</td>"
                curr_col += 1
                if curr_col > 6:
                    html += "</tr><tr>"
                    curr_col = 0
            
            st.markdown(html + "</tr></table>", unsafe_allow_html=True)

    with tab4:
        st.header("Statistiche 2026")
        if not df.empty:
            df_conf = df[df['Stato'] == "Confermata"]
            if not df_conf.empty:
                st.subheader("N. Prenotazioni per Utente")
                st.bar_chart(df_conf['Utente'].value_counts())
            else:
                st.warning("Nessuna prenotazione confermata per le statistiche.")
