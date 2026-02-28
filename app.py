import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- CSS ORIGINALE RIPRISTINATO (Ottimizzato) ---
st.markdown("""
    <style>
    html, body { overflow-y: auto; overscroll-behavior-y: contain; }
    [data-testid="stHeader"] { z-index: 999; }
    button[data-baseweb="tab"] p { font-size: 16px !important; font-weight: bold !important; }
    div.stButton > button {
        width: 100% !important;
        height: 3.5em !important;
        border-radius: 12px !important;
        font-weight: bold !important;
    }
    .cal-table { width:100%; table-layout: fixed; border-spacing: 1px; border-collapse: separate; }
    .cal-td { text-align:center; height:35px; border-radius:3px; border:1px solid #f0f0f0; padding:0 !important; position:relative; }
    .day-num { position: absolute; top: 1px; left: 2px; font-size: 9px; color: #666; z-index: 5; }
    .full-cell { height: 100%; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 14px; }
    .legenda-item { display: inline-block; padding: 4px 10px; border-radius: 5px; margin: 2px; color: white; font-size: 11px; font-weight: bold; }
    [data-testid="column"] { width: 50% !important; flex: 1 1 50% !important; min-width: 50% !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CORE ---
def get_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(worksheet="Prenotazioni", ttl=0)
    data = data.dropna(axis=1, how='all').dropna(axis=0, how='all')
    # Normalizzazione per evitare KeyError
    data.columns = [str(c).strip() for c in data.columns]
    cols_to_fix = ['ID', 'Voti_Ok', 'Note', 'Data_Inizio', 'Data_Fine', 'Stato', 'Utente', 'Casa']
    for col in cols_to_fix:
        if col in data.columns: 
            data[col] = data[col].fillna("").astype(str).str.strip()
    return data

def parse_date(d_str):
    try: return datetime.strptime(d_str, '%d/%m/%Y').date()
    except: return None

# --- AUTH ---
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.title("🏠 Family Booking")
    utenti_log = {"Anita": "1111", "Chiara": "4444", "Lorenzo": "1234", "Gianluca": "1191"}
    u_log = st.selectbox("Chi sei?", ["-- Seleziona --"] + list(utenti_log.keys()))
    p_log = st.text_input("PIN", type="password")
    if st.button("Entra"):
        if u_log != "-- Seleziona --" and p_log == utenti_log[u_log]:
            st.session_state['authenticated'] = True
            st.session_state['user_name'] = u_log
            st.rerun()
        else: st.error("PIN errato")
else:
    # --- APP ---
    df = get_data()
    conn = st.connection("gsheets", type=GSheetsConnection)
    mio_nome = st.session_state['user_name']
    utenti_cfg = {"Anita": {"color": "#FF4B4B"}, "Chiara": {"color": "#FFC0CB"}, "Lorenzo": {"color": "#1C83E1"}, "Gianluca": {"color": "#28A745"}}

    tabs = st.tabs(["📅 PRENOTA", "📊 GESTIONE", "🗓️ CALENDARIO", "📈 STATISTICHE"])

    # --- TAB 1: PRENOTA ---
    with tabs[0]:
        st.header("Nuova Prenotazione")
        casa_scelta = st.selectbox("Meta", ["NOLI", "LIMONE"])
        with st.form("booking_form"):
            d_in = st.date_input("Check-in", value=datetime.now().date() + timedelta(days=1))
            d_out = st.date_input("Check-out", value=datetime.now().date() + timedelta(days=2))
            note = st.text_area("Note")
            if st.form_submit_button("🚀 INVIA"):
                # Controllo sovrapposizioni
                conflitto = False
                p_casa = df[df['Casa'] == casa_scelta]
                for _, r in p_casa.iterrows():
                    s_ex, e_ex = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
                    if s_ex and e_ex and (d_in < e_ex) and (d_out > s_ex):
                        conflitto = True; break
                
                if d_out <= d_in: st.error("Errore date")
                elif conflitto: st.error("Date già occupate!")
                else:
                    nuova_riga = pd.DataFrame([{
                        "ID": str(datetime.now().timestamp()), "Casa": casa_scelta, "Utente": mio_nome,
                        "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                        "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                    }])
                    conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova_riga], ignore_index=True))
                    st.success("Inviata!")
                    time.sleep(1); st.rerun()

    # --- TAB 2: GESTIONE ---
    with tabs[1]:
        st.header("Gestione")
        if not df.empty:
            # Calcolo dinamico mancano/stato
            def processa(row):
                voti = [v.strip() for v in str(row['Voti_Ok']).split(',') if v.strip()]
                mancano = [u for u in utenti_cfg.keys() if u != row['Utente'] and u not in voti]
                stato = "Confermata" if len(mancano) == 0 else "In Attesa"
                return pd.Series([", ".join(voti), ", ".join(mancano), stato])

            df[['Approvati', 'Mancano', 'Stato_Reale']] = df.apply(processa, axis=1)
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Stato_Reale', 'Mancano']], use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("👍 Approva")
            pendenti = df[(df['Utente'] != mio_nome) & (df['Stato_Reale'] == "In Attesa") & (~df['Approvati'].str.contains(mio_nome))]
            for _, r in pendenti.iterrows():
                if st.button(f"APPROVA {r['Casa']} ({r['Data_Inizio']})", key=f"ap_{r['ID']}"):
                    df_raw = get_data()
                    nuovi_voti = f"{r['Voti_Ok']}, {mio_nome}".strip(", ")
                    df_raw.loc[df_raw['ID'] == r['ID'], 'Voti_Ok'] = nuovi_voti
                    if len(nuovi_voti.split(',')) >= 3: df_raw.loc[df_raw['ID'] == r['ID'], 'Stato'] = "Confermata"
                    conn.update(worksheet="Prenotazioni", data=df_raw)
                    st.rerun()

            st.divider()
            st.subheader("🗑️ Elimina")
            mie = df[df['Utente'] == mio_nome]
            for _, r in mie.iterrows():
                if st.button(f"ELIMINA {r['Casa']} ({r['Data_Inizio']})", key=f"del_{r['ID']}"):
                    df_raw = get_data()
                    df_raw = df_raw[df_raw['ID'] != r['ID']]
                    conn.update(worksheet="Prenotazioni", data=df_raw)
                    st.rerun()

    # --- TAB 3: CALENDARIO ---
    with tabs[2]:
        legenda = "".join([f'<span class="legenda-item" style="background:{c["color"]}">{u}</span>' for u, c in utenti_cfg.items()])
        st.markdown(f"🗓️ 2026 | {legenda} | <span class='legenda-item' style='background:#FFFFCC; color:#666; border:1px solid #ccc'>In Attesa</span>", unsafe_allow_html=True)
        occ = {}
        for _, r in df.iterrows():
            s, e = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
            if s and e:
                curr = s
                while curr < e:
                    occ[(curr, r['Casa'])] = {"u": r['Utente'], "s": r['Stato']}
                    curr += timedelta(days=1)
        
        for riga in range(6):
            cols = st.columns(2)
            for box in range(2):
                m = riga * 2 + box + 1
                if m > 12: continue
                with cols[box]:
                    m_date = datetime(2026, m, 1).date()
                    st.write(f"**{m_date.strftime('%B').upper()}**")
                    html = "<table class='cal-table'><tr>" + "".join([f"<th>{dn}</th>" for dn in ['L','M','M','G','V','S','D']]) + "</tr><tr>"
                    wd = m_date.weekday()
                    html += "<td></td>" * wd
                    ld = (datetime(2026, m % 12 + 1, 1).date() - timedelta(days=1)).day
                    c_col = wd
                    for d in range(1, ld + 1):
                        d_obj = m_date.replace(day=d)
                        bg, icona = "", ""
                        rn, rl = occ.get((d_obj, "NOLI")), occ.get((d_obj, "LIMONE"))
                        if rn or rl:
                            res = rn if rn and rn['s'] == "Confermata" else (rl if rl and rl['s'] == "Confermata" else (rn or rl))
                            bg = f"background-color: {utenti_cfg[res['u']]['color']}; color: white;" if res['s'] == "Confermata" else "background-color: #FFFFCC; border: 1px dashed #FFD700;"
                            if rn: icona += "🏖️"
                            if rl: icona += "🏔️"
                        html += f"<td class='cal-td' style='{bg}'><div class='day-num'>{d}</div><div class='full-cell'>{icona}</div></td>"
                        c_col += 1
                        if c_col > 6: html += "</tr><tr>"; c_col = 0
                    st.markdown(html + "</tr></table>", unsafe_allow_html=True)

    # --- TAB 4: STATISTICHE ---
    with tabs[3]:
        st.header("Analisi 2026")
        df['GG'] = df.apply(lambda r: (parse_date(r['Data_Fine']) - parse_date(r['Data_Inizio'])).days if parse_date(r['Data_Fine']) else 0, axis=1)
        c1, c2 = st.columns(2)
        with c1: st.metric("NOLI 🏖️", f"{int(df[(df['Casa']=='NOLI') & (df['Stato']=='Confermata')]['GG'].sum())} gg")
        with c2: st.metric("LIMONE 🏔️", f"{int(df[(df['Casa']=='LIMONE') & (df['Stato']=='Confermata')]['GG'].sum())} gg")
        st.table(df[df['Stato']=='Confermata'].groupby('Utente')['GG'].sum().sort_values(ascending=False))
