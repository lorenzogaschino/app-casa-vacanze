import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- CSS DEFINITIVO 1 (Ripristinato) ---
st.markdown("""
    <style>
    html, body { overflow-y: auto; overscroll-behavior-y: contain; }
    [data-testid="stHeader"] { z-index: 999; }
    button[data-baseweb="tab"] p { font-size: 16px !important; font-weight: bold !important; }
    
    /* Pulsanti Azione Grandi per Mobile */
    div.stButton > button {
        width: 100% !important;
        height: 3.5em !important;
        border-radius: 12px !important;
        font-weight: bold !important;
    }

    /* Stile Tabelle e Calendario */
    .cal-table { width:100%; table-layout: fixed; border-spacing: 1px; border-collapse: separate; }
    .cal-td { text-align:center; height:35px; border-radius:3px; border:1px solid #f0f0f0; padding:0 !important; position:relative; }
    .day-num { position: absolute; top: 1px; left: 2px; font-size: 9px; color: #666; z-index: 5; }
    .full-cell { height: 100%; width: 100%; display: flex; align-items: center; justify-content: center; font-size: 14px; }
    .legenda-item { display: inline-block; padding: 4px 10px; border-radius: 5px; margin: 2px; color: white; font-size: 11px; font-weight: bold; }
    
    /* Statistiche Mobile 50/50 */
    [data-testid="column"] {
        width: 50% !important;
        flex: 1 1 50% !important;
        min-width: 50% !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNZIONI CORE ---
def get_data():
    conn = st.connection("gsheets", type=GSheetsConnection)
    data = conn.read(worksheet="Prenotazioni", ttl=0)
    data = data.dropna(axis=1, how='all')
    # Pulizia colonne per evitare KeyError
    cols_to_fix = ['Voti_Ok', 'Note', 'Data_Inizio', 'Data_Fine', 'Stato', 'Utente', 'Casa', 'ID']
    for col in cols_to_fix:
        if col in data.columns: 
            data[col] = data[col].fillna("").astype(str).str.strip()
    return data

def parse_date(d_str):
    try: return datetime.strptime(d_str, '%d/%m/%Y').date()
    except: return None

# --- AUTENTICAZIONE ---
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
    # --- HEADER ---
    c_inf, c_log = st.columns([0.8, 0.2])
    c_inf.write(f"Connesso come: **{st.session_state['user_name']}**")
    if c_log.button("🔴 Logout"):
        st.session_state['authenticated'] = False
        st.rerun()

    df = get_data()
    conn = st.connection("gsheets", type=GSheetsConnection)
    utenti_cfg = {
        "Anita": {"color": "#FF4B4B"}, 
        "Chiara": {"color": "#FFC0CB"}, 
        "Lorenzo": {"color": "#1C83E1"}, 
        "Gianluca": {"color": "#28A745"}
    }

    tabs = st.tabs(["📅 PRENOTA", "📊 GESTIONE", "🗓️ CALENDARIO", "📈 STATISTICHE"])

    # --- TAB 1: PRENOTA ---
    with tabs[0]:
        st.header("Nuova Prenotazione")
        casa_scelta = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"], key="select_casa")
        
        with st.form("booking_form"):
            oggi = datetime.now().date()
            d_in = st.date_input("Check-in", value=oggi + timedelta(days=1))
            d_out = st.date_input("Check-out", value=oggi + timedelta(days=2))
            note = st.text_area("Note (opzionale)")
            submit = st.form_submit_button("🚀 INVIA PRENOTAZIONE")
            
            if submit:
                df_reale = get_data()
                conflitto = False
                p_casa = df_reale[df_reale['Casa'] == casa_scelta]
                for _, r in p_casa.iterrows():
                    s_ex, e_ex = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
                    if s_ex and e_ex and (d_in < e_ex) and (d_out > s_ex):
                        conflitto = True; break
                
                if d_out <= d_in: st.error("Errore date")
                elif conflitto: st.error("Date già occupate!")
                else:
                    nuova_riga = pd.DataFrame([{
                        "ID": str(datetime.now().timestamp()), 
                        "Casa": casa_scelta, 
                        "Utente": st.session_state['user_name'],
                        "Data_Inizio": d_in.strftime('%d/%m/%Y'), 
                        "Data_Fine": d_out.strftime('%d/%m/%Y'),
                        "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                    }])
                    conn.update(worksheet="Prenotazioni", data=pd.concat([df_reale, nuova_riga], ignore_index=True))
                    st.success("Inviata!")
                    time.sleep(1)
                    st.rerun()

    # --- TAB 2: GESTIONE (Logica Originale Ripristinata) ---
    with tabs[1]:
        st.header("Gestione e Approvazioni")
        df_gest = get_data()
        mio_nome = st.session_state['user_name']
        
        if not df_gest.empty:
            def processa(row):
                v_str = row['Voti_Ok'] if 'Voti_Ok' in row else ""
                voti = [v.strip() for v in str(v_str).split(',') if v.strip()]
                mancano = [u for u in utenti_cfg.keys() if u != row['Utente'] and u not in voti]
                stato = "Confermata" if len(mancano) == 0 else "In Attesa"
                return pd.Series([", ".join(voti) if voti else "Nessuno", ", ".join(mancano) if mancano else "Completo", stato])

            df_gest[['Approvati', 'Mancano', 'Stato_Reale']] = df_gest.apply(processa, axis=1)
            st.subheader("Riepilogo")
            st.dataframe(df_gest[['Casa', 'Utente', 'Data_Inizio', 'Stato_Reale', 'Mancano']], use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("👍 Approva richieste")
            pendenti = df_gest[(df_gest['Utente'] != mio_nome) & (df_gest['Stato_Reale'] == "In Attesa") & (~df_gest['Approvati'].str.contains(mio_nome))]
            
            if not pendenti.empty:
                for _, r in pendenti.iterrows():
                    ico = "⛱️" if r['Casa'] == "NOLI" else "⛰️"
                    if st.button(f"APPROVA: {ico} {r['Casa']} ({r['Data_Inizio']})", key=f"ap_{r['ID']}"):
                        df_raw = get_data()
                        nuovi_voti = f"{r['Voti_Ok']}, {mio_nome}".strip(", ")
                        df_raw.loc[df_raw['ID'] == r['ID'], 'Voti_Ok'] = nuovi_voti
                        # Controllo se diventa confermata
                        v_list = [v.strip() for v in nuovi_voti.split(',') if v.strip()]
                        if len(v_list) >= 3: df_raw.loc[df_raw['ID'] == r['ID'], 'Stato'] = "Confermata"
                        
                        conn.update(worksheet="Prenotazioni", data=df_raw)
                        st.toast(f"Approvato!", icon="✅")
                        time.sleep(1)
                        st.rerun()
            else: st.caption("Nulla da approvare.")

            st.divider()
            st.subheader("🗑️ Elimina le mie")
            mie = df_gest[df_gest['Utente'] == mio_nome]
            if not mie.empty:
                for _, r in mie.iterrows():
                    if st.session_state.get(f"confirm_{r['ID']}", False):
                        st.error(f"Confermi l'eliminazione?")
                        c1, c2 = st.columns(2)
                        if c1.button("SÌ, ELIMINA", key=f"yes_{r['ID']}", type="primary"):
                            df_raw = get_data()
                            df_raw = df_raw[df_raw['ID'] != r['ID']]
                            conn.update(worksheet="Prenotazioni", data=df_raw)
                            st.session_state[f"confirm_{r['ID']}"] = False
                            st.rerun()
                        if c2.button("ANNULLA", key=f"no_{r['ID']}"):
                            st.session_state[f"confirm_{r['ID']}"] = False
                            st.rerun()
                    else:
                        if st.button(f"ELIMINA: {r['Casa']} ({r['Data_Inizio']})", key=f"del_{r['ID']}"):
                            st.session_state[f"confirm_{r['ID']}"] = True
                            st.rerun()

    # --- TAB 3: CALENDARIO (Logica Originale Ripristinata) ---
    with tabs[2]:
        legenda = "".join([f'<span class="legenda-item" style="background:{c["color"]}">{u}</span>' for u, c in utenti_cfg.items()])
        st.markdown(f"🗓️ 2026 | {legenda} | <span class='legenda-item' style='background:#FFFFCC; color:#666; border:1px solid #ccc'>In Attesa</span>", unsafe_allow_html=True)
        
        occ = {}
        for _, r in df_gest.iterrows():
            s, e = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
            if s and e:
                curr = s
                while curr < e:
                    occ[(curr, r['Casa'])] = {"u": r['Utente'], "s": r['Stato_Reale']}
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
                    last_day = (datetime(2026, m % 12 + 1, 1).date() - timedelta(days=1)).day if m < 12 else 31
                    c_col = wd
                    for d in range(1, last_day + 1):
                        d_obj = m_date.replace(day=d)
                        bg, icona = "", ""
                        res_noli, res_lim = occ.get((d_obj, "NOLI")), occ.get((d_obj, "LIMONE"))
                        if res_noli or res_lim:
                            res = res_noli if res_noli and res_noli['s'] == "Confermata" else (res_lim if res_lim and res_lim['s'] == "Confermata" else (res_noli or res_lim))
                            if res['s'] == "Confermata": bg = f"background-color: {utenti_cfg[res['u']]['color']}; color: white;"
                            else: bg = "background-color: #FFFFCC; color: #666; border: 1px dashed #FFD700;"
                            if res_noli: icona += "🏖️"
                            if res_lim: icona += "🏔️"
                        html += f"<td class='cal-td' style='{bg}'><div class='day-num'>{d}</div><div class='full-cell'>{icona}</div></td>"
                        c_col += 1
                        if c_col > 6: html += "</tr><tr>"; c_col = 0
                    st.markdown(html + "</tr></table>", unsafe_allow_html=True)

    # --- TAB 4: STATISTICHE (Logica Originale Ripristinata) ---
    with tabs[3]:
        st.header("Analisi Occupazione 2026")
        def calc_gg(row):
            s, e = parse_date(row['Data_Inizio']), parse_date(row['Data_Fine'])
            return (e - s).days if s and e else 0
        df_st = df_gest.copy()
        df_st['GG'] = df_st.apply(calc_gg, axis=1)
        
        c1, c2 = st.columns(2)
        with c1:
            n_gg = df_st[(df_st['Casa'] == 'NOLI') & (df_st['Stato_Reale'] == 'Confermata')]['GG'].sum()
            st.metric("NOLI 🏖️", f"{int(n_gg)} gg")
        with c2:
            l_gg = df_st[(df_st['Casa'] == 'LIMONE') & (df_st['Stato_Reale'] == 'Confermata')]['GG'].sum()
            st.metric("LIMONE 🏔️", f"{int(l_gg)} gg")
        
        st.divider()
        st.subheader("Riepilogo Utente")
        conf = df_st[df_st['Stato_Reale'] == 'Confermata'].groupby('Utente')['GG'].sum()
        rich = df_st[df_st['Stato_Reale'] != 'Confermata'].groupby('Utente')['GG'].sum()
        res_st = pd.DataFrame({'Utente': utenti_cfg.keys()}).merge(conf.rename('Confermati 🔴'), on='Utente', how='left').merge(rich.rename('Richiesti ⏳'), on='Utente', how='left').fillna(0)
        st.table(res_st.sort_values(by='Confermati 🔴', ascending=False))
