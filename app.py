import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Family Booking", page_icon="🏠", layout="wide")

# --- STILE CSS PERSONALIZZATO PER I TAB ---
st.markdown("""
    <style>
    button[data-baseweb="tab"] p { font-size: 22px !important; font-weight: 800 !important; color: #007bff !important; }
    button[data-baseweb="tab"] { padding: 15px 25px !important; }
    .stAlert { border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# --- CONNESSIONE DATABASE (Google Sheets) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(worksheet="Prenotazioni", ttl=0)
        data = data.dropna(axis=1, how='all')
        for col in ['Voti_Ok', 'Note']:
            if col in data.columns:
                data[col] = data[col].fillna("").astype(str)
            else:
                data[col] = ""
        return data
    except:
        return pd.DataFrame(columns=["ID", "Casa", "Utente", "Data_Inizio", "Data_Fine", "Stato", "Voti_Ok", "Note"])

def check_overlap(start1, end1, start2, end2):
    return start1 <= end2 and start2 <= end1

# --- LISTA UTENTI UFFICIALE ---
utenti = {"Anita": "1111", "Chiara": "4444", "Lorenzo": "1234", "Gianluca": "1191"}

# --- LOGIN ---
st.sidebar.title("🔐 Accesso Family")
user = st.sidebar.selectbox("Chi sei?", ["-- Seleziona --"] + list(utenti.keys()))
password = st.sidebar.text_input("PIN", type="password")

if user != "-- Seleziona --" and password == utenti[user]:
    df = get_data()
    
    # Notifica Toast per conferme recenti
    mie_conf = df[(df['Utente'] == user) & (df['Stato'] == "Confermata")]
    if not mie_conf.empty:
        st.toast(f"🎉 Ciao {user}, hai dei soggiorni confermati!", icon="✅")

    # --- NAVIGAZIONE TAB ---
    tab1, tab2, tab3 = st.tabs(["📅 PRENOTA", "📊 STATO & VOTI", "📸 INFO & STATS"])

    # --- TAB 1: PRENOTAZIONE ---
    with tab1:
        st.header("Nuova Prenotazione")
        col_form, col_foto = st.columns([2, 1])
        
        with col_form:
            casa = st.selectbox("Scegli la meta", ["NOLI", "LIMONE"])
            
            # Analisi disponibilità per box info
            prenotazioni_casa = df[df['Casa'] == casa].copy()
            g_conf_list = []
            g_rich_list = []
            
            if not prenotazioni_casa.empty:
                for _, r in prenotazioni_casa.iterrows():
                    d_i = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                    d_f = datetime.strptime(r['Data_Fine'], '%d/%m/%Y').date()
                    info_txt = f"{d_i.strftime('%d/%m')} al {d_f.strftime('%d/%m')} ({r['Utente']})"
                    if r['Stato'] == "Confermata":
                        g_conf_list.append((d_i, d_f, info_txt))
                    else:
                        g_rich_list.append((d_i, d_f, info_txt))

            # Visualizzazione box disponibilità (Rosso e Giallo)
            if g_conf_list:
                st.error(f"🚫 **NON DISPONIBILE:** {', '.join([x[2] for x in g_conf_list])}")
            if g_rich_list:
                st.warning(f"🟡 **RICHIESTE IN CORSO:** {', '.join([x[2] for x in g_rich_list])}")

            # Selezione date (Default domani per evitare errori su oggi)
            d_in = st.date_input("Check-in", value=datetime.today().date() + timedelta(days=1), min_value=datetime.today().date())
            d_out = st.date_input("Check-out", value=d_in + timedelta(days=1), min_value=d_in)
            
            # Contatore notti
            notti = (d_out - d_in).days
            if notti > 0:
                st.info(f"🌙 Stai prenotando per **{notti}** notti.")
            
            note = st.text_area("Note / Commenti", placeholder="Esempio: Porto il cane, saremo in 4...")

            # Logica conflitti per il tasto invio
            conflitto_conf = False
            conflitto_rich = False
            nome_c = ""

            for start, end, info in g_conf_list:
                if check_overlap(d_in, d_out, start, end):
                    conflitto_conf = True
                    nome_c = info.split('(')[-1].replace(')', '')
                    break
            
            if not conflitto_conf:
                for start, end, info in g_rich_list:
                    if check_overlap(d_in, d_out, start, end):
                        conflitto_rich = True
                        nome_c = info.split('(')[-1].replace(')', '')
                        break

            # Azioni tasti invio
            if conflitto_conf:
                st.error(f"❌ Impossibile prenotare: date già confermate a **{nome_c}**.")
                st.button("🚀 INVIA RICHIESTA", disabled=True, key="btn_dis")
            elif conflitto_rich:
                st.info(f"⚖️ **Sovrapposizione Morbida:** {nome_c} ha già chiesto queste date. Procedi comunque?")
                if st.button("🚀 PROCEDI COMUNQUE", key="btn_morb"):
                    nuova = pd.DataFrame([{
                        "ID": str(datetime.now().timestamp()), "Casa": casa, "Utente": user,
                        "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                        "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                    }])
                    conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                    st.balloons()
                    time.sleep(1); st.rerun()
            else:
                if st.button("🚀 INVIA RICHIESTA", key="btn_ok"):
                    if notti <= 0: st.warning("Scegli almeno una notte!")
                    else:
                        nuova = pd.DataFrame([{
                            "ID": str(datetime.now().timestamp()), "Casa": casa, "Utente": user,
                            "Data_Inizio": d_in.strftime('%d/%m/%Y'), "Data_Fine": d_out.strftime('%d/%m/%Y'),
                            "Stato": "In Attesa", "Voti_Ok": "", "Note": note
                        }])
                        conn.update(worksheet="Prenotazioni", data=pd.concat([df, nuova], ignore_index=True))
                        st.balloons()
                        time.sleep(1); st.rerun()

        with col_foto:
            f_nome = "Noli.jpg" if casa == "NOLI" else "Limone.jpg"
            if os.path.exists(f_nome): st.image(f_nome, width=300)

    # --- TAB 2: STATO & VOTI ---
    with tab2:
        st.header("Situazione e Gestione")
        
        # Countdown vacanze confermate
        if not mie_conf.empty:
            for _, r in mie_conf.iterrows():
                d_i = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y').date()
                diff = (d_i - datetime.today().date()).days
                if diff > 0: st.success(f"⏳ Mancano **{diff} giorni** alla tua vacanza a **{r['Casa']}**!")
                elif diff == 0: st.success(f"🎒 **BUONA VACANZA!** Inizia oggi il tuo soggiorno a {r['Casa']}!")

        if not df.empty:
            df_view = df.copy()
            tutti_utenti = set(utenti.keys())
            
            # Funzione per calcolare Già Approvato e Mancano
            def analizza_voti(row):
                votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                gia_approvato = ", ".join(votanti)
                
                # Chi deve ancora votare? Escludiamo chi ha chiesto e chi ha già votato
                esclusi = set(votanti) | {row['Utente']}
                mancanti = list(tutti_utenti - esclusi)
                non_ancora = ", ".join(mancanti)
                
                return f"{len(votanti)}/3", gia_approvato, non_ancora

            # Applichiamo l'analisi alla tabella
            res = df_view.apply(analizza_voti, axis=1, result_type='expand')
            df_view['Voti'], df_view['Già Approvato'], df_view['Mancano'] = res[0], res[1], res[2]
            
            # Visualizzazione tabella con le nuove colonne
            st.dataframe(
                df_view[['Casa', 'Utente', 'Data_Inizio', 'Data_Fine', 'Stato', 'Voti', 'Già Approvato', 'Mancano', 'Note']], 
                use_container_width=True
            )
            
            st.divider()
            c_voti, c_gest = st.columns(2)
            
            with c_voti:
                st.subheader("🗳️ Vota Richieste")
                for idx, row in df.iterrows():
                    if row['Utente'] != user and row['Stato'] == "In Attesa":
                        votanti = [v.strip() for v in str(row['Voti_Ok']).split(",") if v.strip()]
                        if user not in votanti:
                            if st.button(f"Approva {row['Utente']} ({row['Data_Inizio']})", key=f"v_{idx}"):
                                votanti.append(user)
                                df.at[idx, 'Voti_Ok'] = ", ".join(votanti)
                                if len(votanti) >= 3: df.at[idx, 'Stato'] = "Confermata"
                                conn.update(worksheet="Prenotazioni", data=df)
                                st.rerun()
                        else: st.info(f"✅ Hai approvato {row['Utente']}")

            with c_gest:
                st.subheader("🗑️ Mie Prenotazioni")
                for idx, row in df[df['Utente'] == user].iterrows():
                    key_confirm = f"del_check_{idx}"
                    if key_confirm not in st.session_state:
                        if st.button(f"Elimina {row['Casa']} ({row['Data_Inizio']})", key=f"d_btn_{idx}"):
                            st.session_state[key_confirm] = True; st.rerun()
                    else:
                        st.error("Sei sicuro?")
                        if st.button("SÌ, Elimina", key=f"yes_{idx}", type="primary"):
                            df = df.drop(idx); conn.update(worksheet="Prenotazioni", data=df)
                            del st.session_state[key_confirm]; st.rerun()
                        if st.button("No, annulla", key=f"no_{idx}"):
                            del st.session_state[key_confirm]; st.rerun()

    # --- TAB 3: INFO & STATS ---
    with tab3:
        st.header("📊 Statistiche e Info")
        df_conf = df[df['Stato'] == "Confermata"].copy()
        if not df_conf.empty:
            def get_gg(r): return (datetime.strptime(r['Data_Fine'], '%d/%m/%Y') - datetime.strptime(r['Data_Inizio'], '%d/%m/%Y')).days
            df_conf['GG'] = df_conf.apply(get_gg, axis=1)
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🏆 Re delle Vacanze")
                classifica = df_conf.groupby('Utente')['GG'].sum().sort_values(ascending=False)
                for i, (n, g) in enumerate(classifica.items()):
                    st.write(f"{i+1}. **{n}**: {g} giorni totali")
            with c2:
                st.subheader("🏠 Meta più scelta")
                st.write(f"La meta preferita è: **{df_conf.groupby('Casa').size().idxmax()}**")
        
        st.divider()
        st.header("📸 Foto Case")
        col_n, col_l = st.columns(2)
        with col_n:
            st.subheader("🏖️ NOLI")
            if os.path.exists("Noli.jpg"): st.image("Noli.jpg", use_container_width=True)
        with col_l:
            st.subheader("🏔️ LIMONE")
            if os.path.exists("Limone.jpg"): st.image("Limone.jpg", use_container_width=True)

else:
    st.title("🏠 Family Booking App")
    st.info("Benvenuto! Seleziona il tuo nome e inserisci il PIN per accedere.")
