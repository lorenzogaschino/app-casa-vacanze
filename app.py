# --- TAB 3: INFO & STATS ---
    with tab3:
        st.header("📊 Statistiche e Info")
        df_conf = df[df['Stato'] == "Confermata"].copy()
        
        if not df_conf.empty:
            # Calcolo preciso dei giorni per ogni riga
            def get_gg(r): 
                try:
                    d1 = datetime.strptime(r['Data_Inizio'], '%d/%m/%Y')
                    d2 = datetime.strptime(r['Data_Fine'], '%d/%m/%Y')
                    return (d2 - d1).days
                except:
                    return 0
            
            df_conf['GG'] = df_conf.apply(get_gg, axis=1)
            
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🏆 Re delle Vacanze")
                # Sommiamo i giorni (GG) per ogni Utente
                classifica = df_conf.groupby('Utente')['GG'].sum().sort_values(ascending=False)
                for i, (n, g) in enumerate(classifica.items()):
                    st.write(f"{i+1}. **{n}**: {g} giorni totali")
            
            with c2:
                st.subheader("🏠 Meta più scelta (per giorni)")
                # CORREZIONE: Sommiamo i giorni (GG) per ogni Casa, non il numero di righe
                stats_case = df_conf.groupby('Casa')['GG'].sum()
                meta_top = stats_case.idxmax()
                giorni_top = stats_case.max()
                
                st.write(f"La meta preferita è: **{meta_top}**")
                st.write(f"Con un totale di **{giorni_top}** giorni di relax!")
        else:
            st.info("Statistiche non ancora disponibili (attendiamo le prime conferme!).")
