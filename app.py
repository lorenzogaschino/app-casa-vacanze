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

# --- LOGICA NAVIGAZIONE ---
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if "tab" not in st.query_params: st.query_params["tab"] = "0"

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

    tabs = st.tabs(["📅 PRENOTA", "📊 GESTIONE", "🗓️ CALENDARIO", "📈 STATISTICHE"])

 # --- TAB 1: PRENOTA ---
    with tabs[0]:
        st.header("Nuova Prenotazione")
        
        # 1. Caricamento dati fresco per la visualizzazione iniziale
        # Usiamo get_data() con ttl=0 per essere sicuri di vedere l'ultimo stato reale
        df_fresco = get_data()
        
        casa_scelta = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"], key="select_casa")
        
        # Gestione Foto (Check robusto maiuscole/minuscole)
        img_path = f"{casa_scelta.capitalize()}.jpg"
        if os.path.exists(img_path):
            st.image(img_path, width=350)
        
        st.subheader("Stato attuale")
        p_casa_visualizzazione = df_fresco[df_fresco['Casa'] == casa_scelta].copy()
        
        if p_casa_visualizzazione.empty:
            st.info("Nessuna prenotazione presente per questa casa.")
        else:
            for _, r in p_casa_visualizzazione.iterrows():
                # Definizione Etichette chirurgica
                if str(r['Stato']).strip().lower() == "confermata":
                    label = "CONFERMATA"
                    color = "#FF4B4B" # Rosso
                    icona = "🔴"
                else:
                    label = "RICHIESTA"
                    color = "#FFD700" # Giallo/Oro
                    icona = "⏳"
                
                info = f"{r['Casa']} - {r['Data_Inizio']} - {r['Data_Fine']} - {r['Utente']}"
                st.markdown(f"<div style='font-size: 0.9rem; line-height: 1.8; margin-bottom: 8px;'><span style='color:{color}; font-weight:bold;'>{icona} {label}:</span> {info}</div>", unsafe_allow_html=True)        # FORM DI PRENOTAZIONE
        with st.form("booking_form", clear_on_submit=False):
            oggi = datetime.now().date()
            
            # Input LIBERI: Nessun min_value dinamico per evitare che Streamlit sposti le date da solo
            d_in = st.date_input("Check-in", value=oggi + timedelta(days=1))
            d_out = st.date_input("Check-out", value=oggi + timedelta(days=2))
            note = st.text_area("Note (opzionale)")
            
            submit = st.form_submit_button("🚀 INVIA PRENOTAZIONE")
            
            if submit:
                # --- SICUREZZA 1: Ricarichiamo i dati REALI per il controllo finale ---
                df_reale = get_data() 
                p_casa_reale = df_reale[df_reale['Casa'] == casa_scelta]

                # --- SICUREZZA 2: Validazione Logica ---
                if d_in < oggi:
                    st.error(f"❌ Errore: Non puoi prenotare nel passato (Check-in: {d_in.strftime('%d/%m/%Y')})")
                elif d_out <= d_in:
                    st.error(f"❌ Errore: Il Check-out ({d_out.strftime('%d/%m/%Y')}) deve essere successivo al Check-in.")
                
                else:
                    # --- SICUREZZA 3: Controllo Sovrapposizione Matematico ---
                    conflitto = False
                    dettaglio_conflitto = ""
                    
                    for _, r in p_casa_reale.iterrows():
                        # Pulizia stringhe date dal DB
                        s_ex = parse_date(str(r['Data_Inizio']).strip())
                        e_ex = parse_date(str(r['Data_Fine']).strip())
                        
                        if s_ex and e_ex:
                            # Formula: (Inizio_Nuovo < Fine_Esistente) AND (Fine_Nuovo > Inizio_Esistente)
                            if (d_in < e_ex) and (d_out > s_ex):
                                conflitto = True
                                dettaglio_conflitto = f"{r['Data_Inizio']} - {r['Data_Fine']} ({r['Utente']})"
                                break
                    
                    if conflitto:
                        # BLOCCO TOTALE: Il sistema non "aggiusta" nulla, semplicemente rifiuta.
                        st.error(f"⚠️ PRENOTAZIONE NEGATA: Le date scelte si sovrappongono con: {dettaglio_conflitto}")
                    else:
                        # --- SICUREZZA 4: Scrittura finale su Google Sheets ---
                        try:
                            nuova_riga = pd.DataFrame([{
                                "ID": str(datetime.now().timestamp()), 
                                "Casa": casa_scelta, 
                                "Utente": st.session_state['user_name'],
                                "Data_Inizio": d_in.strftime('%d/%m/%Y'), 
                                "Data_Fine": d_out.strftime('%d/%m/%Y'),
                                "Stato": "In Attesa", 
                                "Voti_Ok": "", 
                                "Note": note
                            }])
                            
                            # Concateniamo i nuovi dati a quelli appena scaricati dal server
                            df_aggiornato = pd.concat([df_reale, nuova_riga], ignore_index=True)
                            conn.update(worksheet="Prenotazioni", data=df_aggiornato)
                            
                            st.balloons()
                            st.success("✅ Richiesta inviata con successo!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Errore tecnico durante il salvataggio: {e}")
    # --- TAB 2: GESTIONE ---
    with tabs[1]:
        st.header("Gestione Prenotazioni")
        if not df.empty:
            # Calcolo GG (Notti effettive)
            def get_gg(r):
                d1, d2 = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
                return (d2 - d1).days if d1 and d2 else 0
            df['GG'] = df.apply(get_gg, axis=1)
            
            # Tabella principale
            st.dataframe(df[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'GG', 'Stato']], use_container_width=True, hide_index=True)

            st.divider()
            col_app, col_del = st.columns(2)
            
            with col_app:
                st.subheader("📥 Approva")
                da_approvare = df[(df['Utente'] != st.session_state['user_name']) & (df['Stato'] == "In Attesa")]
                for idx, row in da_approvare.iterrows():
                    voti = [x.strip() for x in str(row['Voti_Ok']).split(",") if x.strip()]
                    if st.session_state['user_name'] not in voti:
                        # FORMATO PULSANTI: Casa - Data_Inizio - Data_Fine - Utente
                        label_app = f"Approva: {row['Casa']} - {row['Data_Inizio']} - {row['Data_Fine']} - {row['Utente']}"
                        if st.button(label_app, key=f"ap_{idx}"):
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
                    # FORMATO PULSANTI: Casa - Data_Inizio - Data_Fine - Utente
                    label_del = f"Cancella: {row['Casa']} - {row['Data_Inizio']} - {row['Data_Fine']} - {row['Utente']}"
                    if st.button(label_del, key=f"pre_del_{idx}"):
                        st.session_state[f"conf_del_{idx}"] = True
                    
                    if st.session_state.get(f"conf_del_{idx}"):
                        st.error(f"Confermi l'eliminazione?")
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
        st.markdown(f"🗓️ 2026 | {legenda} | <span class='legenda-item' style='background:#FFFFCC; color:#666; border:1px solid #ccc'>In Attesa</span>", unsafe_allow_html=True)
        
        # Mappa occupazione: usiamo (data, casa) come chiave per non sovrapporre Noli e Limone
        occ = {}
        # Ordiniamo per Stato (In Attesa prima, Confermate dopo) così le confermate hanno la priorità visiva
        df_sorted = df.sort_values(by="Stato", ascending=True)
        
        for _, r in df_sorted.iterrows():
            s, e = parse_date(r['Data_Inizio']), parse_date(r['Data_Fine'])
            if s and e:
                curr = s
                while curr < e:
                    # Chiave doppia: data + casa
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
                    
                    wd = m_date.weekday() # 0=Lunedì
                    html += "<td></td>" * wd
                    
                    # Calcolo esatto fine mese
                    if m == 12: last_day = 31
                    else: last_day = (datetime(2026, m+1, 1).date() - timedelta(days=1)).day
                    
                    c_col = wd
                    for d in range(1, last_day + 1):
                        d_obj = m_date.replace(day=d)
                        bg = ""
                        icona = ""
                        
                        # Controllo se il giorno è occupato in ALMENO una delle due case
                        res_noli = occ.get((d_obj, "NOLI"))
                        res_limone = occ.get((d_obj, "LIMONE"))
                        
                        # Priorità cromatica: se c'è almeno una confermata, usa il colore dell'utente
                        # Se sono entrambe in attesa, usa il giallino
                        disponibile = True
                        if res_noli or res_limone:
                            disponibile = False
                            # Scegliamo quale colore mostrare (priorità a chi ha confermato)
                            res = res_noli if res_noli else res_limone
                            if res_noli and res_noli['s'] == "Confermata": res = res_noli
                            elif res_limone and res_limone['s'] == "Confermata": res = res_limone
                            
                            if res['s'] == "Confermata":
                                bg = f"background-color: {utenti_cfg[res['u']]['color']}; color: white;"
                            else:
                                bg = "background-color: #FFFFCC; color: #666; border: 1px dashed #FFD700;"
                            
                            # Icone: mostriamo cosa è occupato
                            if res_noli: icona += "🏖️"
                            if res_limone: icona += "🏔️"

                        content = f"<div class='day-num'>{d}</div><div class='full-cell'>{icona}</div>"
                        html += f"<td class='cal-td' style='{bg}'>{content}</td>"
                        
                        c_col += 1
                        if c_col > 6:
                            html += "</tr><tr>"
                            c_col = 0
                    
                    # Chiudi le celle mancanti a fine mese per mantenere i bordi puliti
                    if c_col != 0:
                        html += "<td></td>" * (7 - c_col)
                        
                    st.markdown(html + "</tr></table>", unsafe_allow_html=True)
# --- TAB 4: STATISTICHE ---
    with tabs[3]:
        st.header("Analisi Occupazione 2026")
        
        # CSS Definitivo: Layout 50/50 e icone piccole
        st.markdown("""
            <style>
                /* Forza le colonne affiancate al 50% su mobile */
                [data-testid="column"] {
                    width: 50% !important;
                    flex: 1 1 50% !important;
                    min-width: 50% !important;
                }
                
                /* Icone piccole (thumbnail) */
                [data-testid="stImage"] img {
                    max-height: 100px !important;
                    width: auto !important;
                    margin: 0 auto;
                    display: block;
                    border-radius: 5px;
                }

                /* Font tabella e metriche */
                .stTable { font-size: 12px !important; }
                [data-testid="stMetricValue"] { font-size: 1.8rem !important; font-weight: bold; }
                
                td { white-space: nowrap; padding: 2px 5px !important; }
            </style>
        """, unsafe_allow_html=True)

        def calc_days(row):
            s = parse_date(str(row['Data_Inizio']).strip())
            e = parse_date(str(row['Data_Fine']).strip())
            return (e - s).days if s and e else 0

        df_stats = df.copy()
        df_stats['GG'] = df_stats.apply(calc_days, axis=1)
        
        # --- LAYOUT SUPERIORE: FOTO PICCOLE E METRICHE ---
        c1, c2 = st.columns(2)
        
        with c1:
            img_noli = "Noli.jpg" if os.path.exists("Noli.jpg") else "noli.jpg"
            if os.path.exists(img_noli):
                st.image(img_noli, use_container_width=False)
            
            noli_conf = df_stats[(df_stats['Casa'] == 'NOLI') & (df_stats['Stato'] == 'Confermata')]['GG'].sum()
            st.metric(label="NOLI 🏖️", value=f"{int(noli_conf)} gg")
            
        with c2:
            img_limone = "Limone.jpg" if os.path.exists("Limone.jpg") else "limone.jpg"
            if os.path.exists(img_limone):
                st.image(img_limone, use_container_width=False)
                
            limone_conf = df_stats[(df_stats['Casa'] == 'LIMONE') & (df_stats['Stato'] == 'Confermata')]['GG'].sum()
            st.metric(label="LIMONE 🏔️", value=f"{int(limone_conf)} gg")
            
        st.divider()
        
        # --- TABELLA RIEPILOGO ---
        st.subheader("Riepilogo Utente")
        
        # 1. Calcolo Confermati
        conf_u = df_stats[df_stats['Stato'] == 'Confermata'].groupby('Utente')['GG'].sum().reset_index()
        conf_u.columns = ['Utente', 'Confermati 🔴']
        
        # 2. Calcolo Richiesti (Tutto ciò che non è confermato)
        rich_u = df_stats[df_stats['Stato'] != 'Confermata'].groupby('Utente')['GG'].sum().reset_index()
        rich_u.columns = ['Utente', 'Richiesti ⏳']
        
        # 3. Unione e Pulizia
        tutti_utenti = pd.DataFrame({'Utente': list(utenti_cfg.keys())})
        final_stats = pd.merge(tutti_utenti, conf_u, on='Utente', how='left')
        final_stats = pd.merge(final_stats, rich_u, on='Utente', how='left').fillna(0)
        
        final_stats['Confermati 🔴'] = final_stats['Confermati 🔴'].astype(int)
        final_stats['Richiesti ⏳'] = final_stats['Richiesti ⏳'].astype(int)
        
        # Tabella ordinata per i confermati
        st.table(final_stats.sort_values(by='Confermati 🔴', ascending=False))
