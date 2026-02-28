import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- CSS ORIGINALE ---
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
    for col in ['Voti_Ok', 'Stato', 'Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'ID']:
        if col not in data.columns: data[col] = ""
        data[col] = data[col].fillna("").astype(str).str.strip()
    return data

def parse_date(d_str):
    if not d_str or d_str == "": return None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try: return datetime.strptime(d_str, fmt).date()
        except: continue
    return None

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

    tabs = st.tabs(["📅 PRENOTA", "📊 GESTIONE", "🗓️ CALENDARIO", "📈 STATISTICHE"])

    # --- TAB 1: PRENOTA (Corretto con Foto e Filtro Casa) ---
    with tabs[0]:
        st.header("Nuova Prenotazione")
        casa_scelta = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
        
        # FOTO CASE (Ripristinate)
        if casa_scelta == "NOLI":
            st.image("https://allaboutitaly.com/wp-content/uploads/2018/06/Noli.jpg", width=400)
        else:
            st.image("https://www.limonepiemonte.it/images/limone-piemonte-inverno.jpg", width=400)

        st.subheader(f"Stato attuale: {casa_scelta}")
        if not df.empty:
            # FILTRO: Mostra solo prenotazioni della casa selezionata
            df_casa = df[df['Casa'] == casa_scelta]
            for _, r in df_casa.iterrows():
                v_list = [v.strip() for v in str(r['Voti_Ok']).split(',') if v.strip()]
                color, label = ("#FF4B4B", "🔴 CONFERMATA") if len(v_list) >= 3 else ("#FFD700", "⏳ RICHIESTA")
                txt = f"{label}: {r['Data_Inizio']} - {r['Data_Fine']} - {r['Utente']}"
                st.markdown(f"<div style='color:{color}; font-weight:bold; margin-bottom:4px;'>{txt}</div>", unsafe_allow_html=True)

        with st.form("form_prenota"):
            d_in = st.date_input("Check-in", value=datetime.now().date() + timedelta(days=1))
            d_out = st.date_input("Check-out", value=datetime.now().date() + timedelta(days=2))
            note = st.text_area("Note")
            if st.form_submit_button("🚀 INVIA PRENOTAZIONE"):
                conflitto = None
                p_casa = df[df['Casa'] == casa_scelta]
                for _, r in p_casa.iterrows():
                    s_ex, e_ex = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
                    if s_ex and e_ex and (d_in < e_ex) and (d_out > s_ex):
                        conflitto = r; break
                
                if d_out <= d_in:
                    st.error("Errore: Check-out deve essere dopo il Check-in")
                elif conflitto is not None:
                    st.error(f"❌ CONFLITTO: {conflitto['Data_Inizio']} - {conflitto['Data_Fine']} ({conflitto['Utente']})")
                else:
                    new_r = pd.DataFrame([{"ID": str(time.time()), "Casa": casa_scelta, "Utente": mio_nome, 
                                           "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                                           "Stato": "In Attesa", "Voti_Ok": "", "Note": note}])
                    conn.update(worksheet="Prenotazioni", data=pd.concat([df, new_r], ignore_index=True))
                    st.success("Prenotazione inviata!"); time.sleep(1); st.rerun()

    # --- TAB 2: GESTIONE ---
    with tabs[1]:
        st.header("Gestione")
        if not df.empty:
            def process_gest(row):
                v_list = [v.strip() for v in str(row['Voti_Ok']).split(',') if v.strip()]
                mancano = [u for u in utenti_cfg.keys() if u != row['Utente'] and u not in v_list]
                return pd.Series([", ".join(v_list), ", ".join(mancano), "Confermata" if len(mancano) == 0 else "In Attesa"])
            df[['Voti', 'Mancano', 'Stato_R']] = df.apply(process_gest, axis=1)
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Stato_R', 'Mancano']], use_container_width=True, hide_index=True)
            
            st.subheader("👍 Approva")
            pendenti = df[(df['Utente'] != mio_nome) & (df['Stato_R'] == "In Attesa") & (~df['Voti'].str.contains(mio_nome))]
            for idx, r in pendenti.iterrows():
                if st.button(f"APPROVA {r['Casa']} ({r['Data_Inizio']})", key=f"ap_{idx}"):
                    v_new = (str(r['Voti_Ok']) + f", {mio_nome}").strip(", ")
                    df.at[idx, 'Voti_Ok'] = v_new
                    if len(v_new.split(',')) >= 3: df.at[idx, 'Stato'] = "Confermata"
                    conn.update(worksheet="Prenotazioni", data=df.drop(columns=['Voti', 'Mancano', 'Stato_R']))
                    st.rerun()

    # --- TAB 3: CALENDARIO (Versione Corretta e Stabile) ---
    with tabs[2]:
        st.header("Calendario 2026")
        occ = {}
        for _, r in df.iterrows():
            s, e = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
            if s and e:
                curr = s
                while curr < e:
                    voti_count = len([v for v in str(r['Voti_Ok']).split(',') if v.strip()])
                    occ[(curr, r['Casa'])] = {"u": r['Utente'], "v": voti_count}
                    curr += timedelta(days=1)
        
        for m in range(1, 13):
            m_date = datetime(2026, m, 1).date()
            st.write(f"**{m_date.strftime('%B %Y').upper()}**")
            
            # Calcolo ultimo giorno del mese
            if m == 12:
                last_day = 31
            else:
                last_day = (datetime(2026, m+1, 1) - timedelta(days=1)).day
                
            html = "<table class='cal-table'><tr><th>L</th><th>M</th><th>M</th><th>G</th><th>V</th><th>S</th><th>D</th></tr><tr>"
            wd = m_date.weekday() # 0=Lunedì, 6=Domenica
            html += "<td></td>" * wd
            
            curr_c = wd
            for d in range(1, last_day + 1):
                d_obj = m_date.replace(day=d)
                bg, ico = "", ""
                rn, rl = occ.get((d_obj, "NOLI")), occ.get((d_obj, "LIMONE"))
                
                if rn or rl:
                    # Se ci sono entrambe, diamo priorità visiva a quella confermata o alla prima trovata
                    res = rn if rn else rl
                    bg = f"background:{utenti_cfg.get(res['u'], '#eee')};" if res['v'] >= 3 else "background:#FFFFCC;"
                    if rn: ico += "🏖️"
                    if rl: ico += "🏔️"
                
                html += f"<td class='cal-td' style='{bg}'><div class='day-num'>{d}</div>{ico}</td>"
                curr_c += 1
                if curr_c > 6: 
                    html += "</tr><tr>"
                    curr_c = 0
            st.markdown(html + "</tr></table>", unsafe_allow_html=True)

    # --- TAB 4: STATISTICHE (Foto + Tabella Riepilogo) ---
    with tabs[3]:
        st.header("Statistiche 2026")
        def calc_gg(r):
            s, e = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
            return (e-s).days if s and e else 0
        df['GG'] = df.apply(calc_gg, axis=1)
        
        # Metriche con Foto (Ripristinate)
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("NOLI 🏖️")
            st.image("https://allaboutitaly.com/wp-content/uploads/2018/06/Noli.jpg", use_container_width=True)
            st.metric("GG Confermati", int(df[(df['Casa']=='NOLI') & (df['Stato']=='Confermata')]['GG'].sum()))
        with c2:
            st.subheader("LIMONE 🏔️")
            st.image("https://www.limonepiemonte.it/images/limone-piemonte-inverno.jpg", use_container_width=True)
            st.metric("GG Confermati", int(df[(df['Casa']=='LIMONE') & (df['Stato']=='Confermata')]['GG'].sum()))
        
        st.divider()
        st.subheader("Riepilogo Utente")
        # Costruzione Tabella Riepilogo (Vecchio screenshot)
        riepilogo = []
        for u in utenti_cfg.keys():
            conf = df[(df['Utente'] == u) & (df['Stato'] == 'Confermata')]['GG'].sum()
            rich = df[(df['Utente'] == u) & (df['Stato'] != 'Confermata')]['GG'].sum()
            riepilogo.append({"Utente": u, "Confermati 🔴": int(conf), "Richiesti ⏳": int(rich)})
        
        st.table(pd.DataFrame(riepilogo))
