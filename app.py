import sqlite3
import streamlit as st
import pandas as pd
from datetime import date, timedelta
import io

st.set_page_config(page_title="System Biblioteczny", layout="wide")

# Połączenie z bazą danych
conn = sqlite3.connect("biblioteka_kompletna.db", check_same_thread=False)
c = conn.cursor()

# Tworzenie i aktualizacja tabel
c.execute('''
    CREATE TABLE IF NOT EXISTS ksiazki (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tytul TEXT,
        autor TEXT,
        rodzaj TEXT,
        kod_kreskowy TEXT,
        stan TEXT
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS czytelnici (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        imie_nazwisko TEXT,
        kod_karty TEXT UNIQUE,
        pin TEXT DEFAULT '1234'
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS pracownicy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        imie_nazwisko TEXT,
        kod_identyfikator TEXT UNIQUE
    )
''')

c.execute("INSERT OR IGNORE INTO pracownicy (id, imie_nazwisko, kod_identyfikator) VALUES (1, 'Administrator', 'ADMIN123')")
conn.commit()

c.execute('''
    CREATE TABLE IF NOT EXISTS wypozyczenia (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ksiazka_id INTEGER,
        czytelnik TEXT,
        data_wypozyczenia TEXT,
        data_zwrotu TEXT,
        status TEXT,
        FOREIGN KEY(ksiazka_id) REFERENCES ksiazki(id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS rezerwacje (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ksiazka_id INTEGER,
        czytelnik TEXT,
        data_rezerwacji TEXT,
        status TEXT,
        FOREIGN KEY(ksiazka_id) REFERENCES ksiazki(id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS ustawienia (
        klucz TEXT PRIMARY KEY,
        wartosc TEXT
    )
''')
c.execute("INSERT OR IGNORE INTO ustawienia (klucz, wartosc) VALUES ('czas_wypozyczenia', '14')")
conn.commit()

headers = st.context.headers if hasattr(st, "context") and hasattr(st.context, "headers") else {}
host_header = headers.get("Host", "")

if "ngrok" in host_header:
    domyslny_tryb = "Katalog Online OPAC (Czytelnik)"
else:
    domyslny_tryb = "Panel Stacjonarny (Biblioteka)"

st.sidebar.title("📚 System Biblioteki")
tryb = st.sidebar.radio("Wybierz widok:", ["Panel Stacjonarny (Biblioteka)", "Katalog Online OPAC (Czytelnik)"], index=0 if domyslny_tryb == "Panel Stacjonarny (Biblioteka)" else 1)
st.sidebar.divider()

if tryb == "Panel Stacjonarny (Biblioteka)":
    if "zalogowany_admin" not in st.session_state:
        st.session_state["zalogowany_admin"] = False
    if "pracownik_imie" not in st.session_state:
        st.session_state["pracownik_imie"] = ""

    if not st.session_state["zalogowany_admin"]:
        st.title("🔐 System Biblioteka")
        st.markdown("### Logowanie do systemu")
        
        with st.form("form_log_pracownik_kod"):
            st.write("Wpisz kod PIN lub zeskanuj identyfikator:")
            kod_wejscie = st.text_input("Identyfikator:", type="password", label_visibility="collapsed")
            btn = st.form_submit_button("Zaloguj się")
            if btn:
                c.execute("SELECT imie_nazwisko FROM pracownicy WHERE kod_identyfikator = ?", (kod_wejscie,))
                res = c.fetchone()
                if res or kod_wejscie == "ADMIN123":
                    st.session_state["zalogowany_admin"] = True
                    st.session_state["pracownik_imie"] = res[0] if res else "Administrator"
                    st.success("Zalogowano pomyślnie!")
                    st.rerun()
                else:
                    st.error("❌ Błędny identyfikator pracownika!")
        st.stop()

    col_top1, col_top2 = st.columns([8, 2])
    with col_top1:
        st.markdown(f"### Panel Biblioteki — Zalogowany pracownik: **{st.session_state['pracownik_imie']}**")
    with col_top2:
        if st.button("Wyloguj", type="primary"):
            st.session_state["zalogowany_admin"] = False
            st.session_state["pracownik_imie"] = ""
            st.rerun()

    st.divider()
    tab1, tab_import, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Książki i Katalog", 
        "📥 Import z CSV/Sheets",
        "Czytelnici", 
        "Zarządzanie Pracownikami", 
        "Wypożyczenia i Zwroty", 
        "Rezerwacje", 
        "Ustawienia",
        "Raporty i Statystyki"
    ])

    with tab1:
        col_szukaj, col_btn = st.columns([9, 1])
        with col_szukaj:
            szukaj_ksiazki = st.text_input("🔍 Szukaj książki (tytuł, autor, rodzaj, kod):", key="szuk_ks_st")
        with col_btn:
            st.write("")
            if st.button("Wyczyść"):
                st.rerun()

        c1, c2 = st.columns([1, 3])
        with c1:
            st.markdown("#### Dodaj książkę")
            tytul = st.text_input("Tytuł:", key="add_tytul")
            autor = st.text_input("Autor:", key="add_autor")
            rodzaj = st.text_input("Rodzaj / Kategoria:", key="add_rodzaj")
            kod_kreskowy = st.text_input("Kod kreskowy (ISBN):", key="add_kod")
            liczba_sztuk = st.number_input("Liczba sztuk:", min_value=1, value=1, key="add_sztuki")
            
            if st.button("Zapisz książkę w bazie", type="primary"):
                if tytul and autor:
                    for _ in range(liczba_sztuk):
                        c.execute("INSERT INTO ksiazki (tytul, autor, rodzaj, kod_kreskowy, stan) VALUES (?, ?, ?, ?, ?)",
                                  (tytul, autor, rodzaj, kod_kreskowy, "Dostępna"))
                    conn.commit()
                    st.success("Dodano książkę pomyślnie!")
                    st.rerun()
                else:
                    st.error("Wpisz tytuł i autora.")

        with c2:
            if szukaj_ksiazki:
                q = "SELECT * FROM ksiazki WHERE tytul LIKE ? OR autor LIKE ? OR rodzaj LIKE ? OR kod_kreskowy LIKE ?"
                df_ksiazki = pd.read_sql(q, conn, params=(f"%{szukaj_ksiazki}%", f"%{szukaj_ksiazki}%", f"%{szukaj_ksiazki}%", f"%{szukaj_ksiazki}%"))
            else:
                df_ksiazki = pd.read_sql("SELECT * FROM ksiazki", conn)
                
            event = st.dataframe(
                df_ksiazki, 
                use_container_width=True, 
                hide_index=True,
                selection_mode="single-row",
                on_select="rerun",
                key="tabela_ksiazek"
            )
            
            wybrany_id = None
            selected_rows = event.selection.rows if event and hasattr(event, "selection") else []
            if selected_rows:
                row_idx = selected_rows[0]
                wybrany_id = int(df_ksiazki.iloc[row_idx]['id'])

            if not df_ksiazki.empty:
                st.markdown("#### Zarządzanie wybraną książką")
                opcje_select = (df_ksiazki['id'].astype(str) + " - " + df_ksiazki['tytul'] + " (" + df_ksiazki['stan'] + ")").tolist()
                domyslny_index = 0
                if wybrany_id is not None:
                    for idx, opcja in enumerate(opcje_select):
                        if opcja.startswith(str(wybrany_id) + " - "):
                            domyslny_index = idx
                            break

                wybrana_do_wyp = st.selectbox("Kliknij wiersz w tabeli powyżej lub wybierz z listy:", opcje_select, index=domyslny_index)
                
                kid = int(wybrana_do_wyp.split(" - ")[0])
                
                kol_ak1, kol_ak2, kol_ak3 = st.columns(3)
                with kol_ak1:
                    c.execute("SELECT stan FROM ksiazki WHERE id = ?", (kid,))
                    aktualny_stan_ks = c.fetchone()[0]
                    if aktualny_stan_ks == 'Wypożyczona':
                        st.warning("Ta książka jest już wypożyczona.")
                    else:
                        if st.button("Wypożycz tę pozycję"):
                            st.session_state['wypozycz_id'] = kid
                            st.rerun()
                with kol_ak2:
                    if st.button("Edytuj dane książki"):
                        st.session_state['edytuj_ksiazka_id'] = kid
                        st.rerun()
                with kol_ak3:
                    if st.button("Usuń książkę", type="secondary"):
                        c.execute("DELETE FROM ksiazki WHERE id = ?", (kid,))
                        conn.commit()
                        st.success("Usunięto książkę!")
                        st.rerun()

        if 'edytuj_ksiazka_id' in st.session_state:
            st.markdown("---")
            st.subheader("✏️ Edycja danych książki")
            eid = st.session_state['edytuj_ksiazka_id']
            c.execute("SELECT tytul, autor, rodzaj, kod_kreskowy, stan FROM ksiazki WHERE id = ?", (eid,))
            akt_dane = c.fetchone()
            
            if akt_dane:
                with st.form("form_edit_book"):
                    e_tytul = st.text_input("Tytuł:", value=akt_dane[0])
                    e_autor = st.text_input("Autor:", value=akt_dane[1])
                    e_rodzaj = st.text_input("Rodzaj / Kategoria:", value=akt_dane[2])
                    e_kod = st.text_input("Kod kreskowy (ISBN):", value=akt_dane[3] if akt_dane[3] else "")
                    e_stan = st.selectbox("Stan:", ["Dostępna", "Wypożyczona", "Zarezerwowana"], index=["Dostępna", "Wypożyczona", "Zarezerwowana"].index(akt_dane[4]) if akt_dane[4] in ["Dostępna", "Wypożyczona", "Zarezerwowana"] else 0)
                    
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        if st.form_submit_button("Zapisz zmiany"):
                            c.execute("UPDATE ksiazki SET tytul = ?, autor = ?, rodzaj = ?, kod_kreskowy = ?, stan = ? WHERE id = ?",
                                      (e_tytul, e_autor, e_rodzaj, e_kod, e_stan, eid))
                            conn.commit()
                            st.success("Zaktualizowano dane książki!")
                            del st.session_state['edytuj_ksiazka_id']
                            st.rerun()
                    with col_e2:
                        if st.form_submit_button("Anuluj edycję"):
                            del st.session_state['edytuj_ksiazka_id']
                            st.rerun()

        if 'wypozycz_id' in st.session_state:
            st.markdown("---")
            st.subheader("Wypożyczenie pozycji")
            kid = st.session_state['wypozycz_id']
            c.execute("SELECT tytul FROM ksiazki WHERE id = ?", (kid,))
            tyt = c.fetchone()[0]
            st.write(f"Książka: **{tyt}**")
            
            # Pobieramy rezerwację, która jest Aktywna lub Zaakceptowana
            c.execute("SELECT czytelnik FROM rezerwacje WHERE ksiazka_id = ? AND status IN ('Aktywna', 'Zaakceptowana')", (kid,))
            rez_info = c.fetchone()
            
            if rez_info:
                zarezerwowal_kto = rez_info[0]
                st.error(f"🔒 **BLOKADA REZERWACJI:** Ta książka jest zarezerwowana przez: **{zarezerwowal_kto}**. System automatycznie przypisze ją do tej osoby i nie pozwoli wypożyczyć jej nikomu innemu.")
                wybrany_wpis_czyt = zarezerwowal_kto
                st.write(f"Wybrany czytelnik: **{zarezerwowal_kto}**")
            else:
                df_czyt_wyp = pd.read_sql("SELECT imie_nazwisko, kod_karty FROM czytelnici", conn)
                lista_osob = (df_czyt_wyp['imie_nazwisko'] + " (Kod: " + df_czyt_wyp['kod_karty'] + ")").tolist() if not df_czyt_wyp.empty else []
                wybrany_wpis_czyt_box = st.selectbox("Wybierz czytelnika:", lista_osob) if lista_osob else ""
                wybrany_wpis_czyt = wybrany_wpis_czyt_box.split(" (Kod:")[0] if wybrany_wpis_czyt_box else ""
            
            tryb_terminu = st.radio("Termin zwrotu", ["Automatyczny (z ustawień)", "Własna liczba dni"])
            c.execute("SELECT wartosc FROM ustawienia WHERE klucz = 'czas_wypozyczenia'")
            def_dni = int(c.fetchone()[0])
            final_dni = st.number_input("Liczba dni:", min_value=1, value=def_dni) if tryb_terminu == "Własna liczba dni" else def_dni
                
            col_ok, col_an = st.columns(2)
            with col_ok:
                if st.button("Zatwierdź wypożyczenie"):
                    if wybrany_wpis_czyt:
                        dzis = date.today()
                        termin = dzis + timedelta(days=final_dni)
                        c.execute("UPDATE ksiazki SET stan = 'Wypożyczona' WHERE id = ?", (kid,))
                        c.execute("INSERT INTO wypozyczenia (ksiazka_id, czytelnik, data_wypozyczenia, data_zwrotu, status) VALUES (?, ?, ?, ?, ?)",
                                  (kid, wybrany_wpis_czyt, str(dzis), str(termin), 'Wypożyczona'))
                        c.execute("UPDATE rezerwacje SET status = 'Oczekuje na zwrot' WHERE ksiazka_id = ? AND status IN ('Aktywna', 'Zaakceptowana')", (kid,))
                        conn.commit()
                        st.success(f"Wypożyczono pomyślnie dla czytelnika: {wybrany_wpis_czyt}!")
                        del st.session_state['wypozycz_id']
                        st.rerun()
                    else:
                        st.error("Brak wybranego czytelnika!")
            with col_an:
                if st.button("Anuluj"):
                    del st.session_state['wypozycz_id']
                    st.rerun()

    with tab_import:
        st.subheader("📥 Masowy import książek z pliku CSV (np. z Google Sheets)")
        st.markdown("""
        **Instrukcja:**
        1. W Google Sheets stwórz tabelę z następującymi nagłówkami w pierwszej kolumnie: **tytul**, **autor**, **rodzaj**, **kod_kreskowy**.
        2. Wpisz lub wklej swoje książki.
        3. W Google Sheets kliknij **Plik -> Pobierz -> Wartości rozdzielane przecinkami (.csv)**.
        4. Wgraj pobrany plik poniżej i kliknij przycisk importu!
        """)
        
        uploaded_file = st.file_uploader("Wybierz plik CSV z książkami", type=["csv"])
        if uploaded_file is not None:
            try:
                df_import = pd.read_csv(uploaded_file)
                st.write("Podgląd wgranych danych:")
                st.dataframe(df_import, use_container_width=True)
                
                wymagane = ['tytul', 'autor']
                if all(col in df_import.columns for col in wymagane):
                    if st.button("🚀 Importuj te książki do bazy", type="primary"):
                        licznik = 0
                        for _, row in df_import.iterrows():
                            tytul = str(row['tytul'])
                            autor = str(row['autor'])
                            rodzaj = str(row['rodzaj']) if 'rodzaj' in df_import.columns and pd.notna(row['rodzaj']) else ""
                            kod = str(row['kod_kreskowy']) if 'kod_kreskowy' in df_import.columns and pd.notna(row['kod_kreskowy']) else ""
                            
                            c.execute("INSERT INTO ksiazki (tytul, autor, rodzaj, kod_kreskowy, stan) VALUES (?, ?, ?, ?, ?)",
                                      (tytul, autor, rodzaj, kod, "Dostępna"))
                            licznik += 1
                        conn.commit()
                        st.success(f"Pomyślnie zaimportowano {licznik} książek do biblioteki!")
                        st.rerun()
                else:
                    st.error("❌ Plik CSV musi zawierać przynajmniej kolumny o nazwach: `tytul` oraz `autor`!")
            except Exception as e:
                st.error(f"Błąd podczas odczytu pliku: {e}")

    with tab2:
        st.subheader("Baza czytelników")
        col_cz1, col_cz2 = st.columns([1, 2])
        with col_cz1:
            with st.form("form_add_reader"):
                imie_nazwisko = st.text_input("Imię i nazwisko:")
                kod_karty = st.text_input("Kod karty / Identyfikator:")
                if st.form_submit_button("Zapisz czytelnika"):
                    if imie_nazwisko and kod_karty:
                        try:
                            c.execute("INSERT INTO czytelnici (imie_nazwisko, kod_karty) VALUES (?, ?)", (imie_nazwisko, kod_karty))
                            conn.commit()
                            st.success("Dodano czytelnika!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("❌ Taki kod karty już istnieje!")
                    else:
                        st.error("Uzupełnij pola.")
        with col_cz2:
            df_czytelnici = pd.read_sql("SELECT id, imie_nazwisko as [Imię i Nazwisko], kod_karty as [Kod karty] FROM czytelnici", conn)
            st.dataframe(df_czytelnici, use_container_width=True, hide_index=True)
            
            if not df_czytelnici.empty:
                wybrany_czyt_del = st.selectbox("Wybierz czytelnika do usunięcia:", df_czytelnici['id'].astype(str) + " - " + df_czytelnici['Imię i Nazwisko'])
                if st.button("Usuń zaznaczonego czytelnika", type="secondary"):
                    cid = int(wybrany_czyt_del.split(" - ")[0])
                    c.execute("DELETE FROM czytelnici WHERE id = ?", (cid,))
                    conn.commit()
                    st.success("Usunięto czytelnika!")
                    st.rerun()

    with tab3:
        st.subheader("👥 Zarządzanie Pracownikami Biblioteki")
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            with st.form("form_add_pracownik"):
                 imie_prac = st.text_input("Imię i nazwisko pracownika:")
                 kod_prac = st.text_input("Unikalny kod / identyfikator:")
                 if st.form_submit_button("Zapisz pracownika"):
                     if imie_prac and kod_prac:
                         try:
                             c.execute("INSERT INTO pracownicy (imie_nazwisko, kod_identyfikator) VALUES (?, ?)", (imie_prac, kod_prac))
                             conn.commit()
                             st.success(f"Dodano pracownika: {imie_prac}")
                             st.rerun()
                         except sqlite3.IntegrityError:
                             st.error("❌ Taki identyfikator jest już zajęty!")
                     else:
                         st.error("Uzupełnij wszystkie pola.")
                         
        with col_p2:
            df_pracownicy = pd.read_sql("SELECT id, imie_nazwisko as [Imię i Nazwisko], kod_identyfikator as [Kod identyfikacyjny] FROM pracownicy", conn)
            st.dataframe(df_pracownicy, use_container_width=True, hide_index=True)
            
            if not df_pracownicy.empty:
                wybrany_prac_del = st.selectbox("Wybierz pracownika do usunięcia:", df_pracownicy['id'].astype(str) + " - " + df_pracownicy['Imię i Nazwisko'])
                if st.button("Usuń zaznaczonego pracownika", type="secondary"):
                    pid = int(wybrany_prac_del.split(" - ")[0])
                    if pid == 1:
                        st.error("Nie można usunąć głównego konta administratora!")
                    else:
                        c.execute("DELETE FROM pracownicy WHERE id = ?", (pid,))
                        conn.commit()
                        st.success("Usunięto pracownika!")
                        st.rerun()

    with tab4:
        st.subheader("📋 Aktywne wypożyczenia i zwroty")
        
        with st.expander("📷 Szybki zwrot po kodzie kreskowym książki"):
            skan_kod = st.text_input("Wpisz lub zeskanuj kod kreskowy książki:")
            if skan_kod:
                c.execute('''
                    SELECT w.id, w.czytelnik, k.tytul, k.kod_kreskowy, k.id 
                    FROM wypozyczenia w JOIN ksiazki k ON w.ksiazka_id = k.id 
                    WHERE k.kod_kreskowy = ? AND w.status = 'Wypożyczona'
                ''', (skan_kod,))
                wynik_skanu = c.fetchone()
                if wynik_skanu:
                    w_id, w_czyt, w_tytul, w_kod, kid = wynik_skanu
                    st.success(f"Znaleziono książkę: **{w_tytul}** | Czytelnik: **{w_czyt}**")
                    if st.button("Potwierdź zwrot tej książki", type="primary", key="btn_szybki_zwrot"):
                        c.execute("UPDATE ksiazki SET stan = 'Dostępna' WHERE id = ?", (kid,))
                        c.execute("UPDATE wypozyczenia SET status = 'Zwrócona' WHERE id = ?", (w_id,))
                        c.execute("UPDATE rezerwacje SET status = 'Zrealizowana' WHERE ksiazka_id = ? AND status = 'Oczekuje na zwrot'", (kid,))
                        conn.commit()
                        st.success("Przyjęto zwrot książki pomyślnie! Rezerwacja została ostatecznie zamknięta.")
                        st.rerun()
                else:
                    st.warning("❌ Brak aktywnego wypożyczenia dla podanego kodu kreskowego.")

        with st.expander("🔎 Sprawdź stan konta czytelnika (ile ma książek)"):
            szukaj_konta = st.text_input("Wpisz kod karty lub imię/nazwisko czytelnika:")
            if szukaj_konta:
                c.execute("SELECT imie_nazwisko, kod_karty FROM czytelnici WHERE kod_karty LIKE ? OR imie_nazwisko LIKE ?", (f"%{szukaj_konta}%", f"%{szukaj_konta}%"))
                wyniki_czyt = c.fetchall()
                if wyniki_czyt:
                    for imie_szukanego, kod_szukanego in wyniki_czyt:
                        st.markdown(f"**Czytelnik:** {imie_szukanego} (Kod karty: `{kod_szukanego}`)")
                        df_wyp_szukanego = pd.read_sql('''
                            SELECT k.tytul as [Książka], k.kod_kreskowy as [Kod Kreskowy], w.data_wypozyczenia as [Data wypożyczenia], w.data_zwrotu as [Termin zwrotu]
                            FROM wypozyczenia w JOIN ksiazki k ON w.ksiazka_id = k.id 
                            WHERE w.czytelnik = ? AND w.status = 'Wypożyczona'
                        ''', conn, params=(imie_szukanego,))
                        
                        ile_ksiazek = len(df_wyp_szukanego)
                        st.info(f"Aktualnie wypożyczonych książek na koncie: **{ile_ksiazek}**")
                        if ile_ksiazek > 0:
                            st.dataframe(df_wyp_szukanego, use_container_width=True, hide_index=True)
                        st.divider()
                else:
                    st.warning("Nie znaleziono takiego czytelnika w bazie.")
        
        st.markdown("---")
        szukaj_wyp = st.text_input("🔍 Szukaj wypożyczenia (tytuł książki, kod kreskowy lub imię czytelnika):", key="sz_wyp_lupka")
        
        query_wyp = '''
            SELECT w.id, w.czytelnik, k.tytul as [Książka], k.kod_kreskowy as [Kod Kreskowy], w.data_wypozyczenia as [Data wypożyczenia], w.data_zwrotu as [Termin zwrotu]
            FROM wypozyczenia w JOIN ksiazki k ON w.ksiazka_id = k.id WHERE w.status = 'Wypożyczona'
        '''
        
        if szukaj_wyp:
            df_wyp = pd.read_sql(f'''
                SELECT w.id, w.czytelnik, k.tytul as [Książka], k.kod_kreskowy as [Kod Kreskowy], w.data_wypozyczenia as [Data wypożyczenia], w.data_zwrotu as [Termin zwrotu]
                FROM wypozyczenia w JOIN ksiazki k ON w.ksiazka_id = k.id 
                WHERE w.status = 'Wypożyczona' AND (k.tytul LIKE ? OR k.kod_kreskowy LIKE ? OR w.czytelnik LIKE ?)
            ''', conn, params=(f"%{szukaj_wyp}%", f"%{szukaj_wyp}%", f"%{szukaj_wyp}%"))
        else:
            df_wyp = pd.read_sql(query_wyp, conn)
            
        st.dataframe(df_wyp, use_container_width=True, hide_index=True)
        
        if not df_wyp.empty:
            wybrany_zw = st.selectbox("Wybierz wypożyczenie do zwrotu:", df_wyp['id'].astype(str) + " - " + df_wyp['czytelnik'] + " (" + df_wyp['Książka'] + ")")
            if st.button("Przyjmij zwrot", type="primary"):
                wid = int(wybrany_zw.split(" - ")[0])
                c.execute("SELECT ksiazka_id FROM wypozyczenia WHERE id = ?", (wid,))
                kid = c.fetchone()[0]
                c.execute("UPDATE ksiazki SET stan = 'Dostępna' WHERE id = ?", (kid,))
                c.execute("UPDATE wypozyczenia SET status = 'Zwrócona' WHERE id = ?", (wid,))
                c.execute("UPDATE rezerwacje SET status = 'Zrealizowana' WHERE ksiazka_id = ? AND status = 'Oczekuje na zwrot'", (kid,))
                conn.commit()
                st.success("Przyjęto zwrot książki! Rezerwacja została ostatecznie zamknięta.")
                st.rerun()

    with tab5:
        st.subheader("Oczekujące i aktywne rezerwacje od czytelników")
        df_rez = pd.read_sql('''
            SELECT r.id, r.czytelnik, k.tytul as Książka, r.data_rezerwacji, r.status
            FROM rezerwacje r JOIN ksiazki k ON r.ksiazka_id = k.id WHERE r.status IN ('Aktywna', 'Zaakceptowana', 'Oczekuje na zwrot')
        ''', conn)
        st.dataframe(df_rez, use_container_width=True, hide_index=True)
        
        if not df_rez.empty:
            wyb_rez = st.selectbox("Wybierz rezerwację:", df_rez['id'].astype(str) + " - " + df_rez['czytelnik'] + " (" + df_rez['Książka'] + " - " + df_rez['status'] + ")")
            rid = int(wyb_rez.split(" - ")[0])
            
            c.execute("SELECT status FROM rezerwacje WHERE id = ?", (rid,))
            aktualny_status_rez = c.fetchone()[0]
            
            col_rz1, col_rz2, col_rz3 = st.columns(3)
            with col_rz1:
                if aktualny_status_rez == 'Aktywna':
                    if st.button("✅ Zaakceptuj rezerwację (Wyślij komunikat do czytelnika)", type="primary"):
                        c.execute("UPDATE rezerwacje SET status = 'Zaakceptowana' WHERE id = ?", (rid,))
                        c.execute("UPDATE ksiazki SET stan = 'Zarezerwowana' WHERE id = (SELECT ksiazka_id FROM rezerwacje WHERE id = ?)", (rid,))
                        conn.commit()
                        st.success("Zaakceptowano rezerwację! Status książki zmieniony na 'Zarezerwowana'.")
                        st.rerun()
                else:
                    st.info(f"Status rezerwacji: {aktualny_status_rez}")
                    
            with col_rz2:
                if aktualny_status_rez in ('Aktywna', 'Zaakceptowana'):
                    if st.button("📚 Przekształć w wypożyczenie"):
                        c.execute("SELECT ksiazka_id, czytelnik FROM rezerwacje WHERE id = ?", (rid,))
                        r_data = c.fetchone()
                        kid, czytelnik_wyp = r_data[0], r_data[1]
                        
                        dzis = date.today()
                        c.execute("SELECT wartosc FROM ustawienia WHERE klucz = 'czas_wypozyczenia'")
                        def_dni = int(c.fetchone()[0])
                        termin = dzis + timedelta(days=def_dni)
                        
                        c.execute("UPDATE ksiazki SET stan = 'Wypożyczona' WHERE id = ?", (kid,))
                        c.execute("INSERT INTO wypozyczenia (ksiazka_id, czytelnik, data_wypozyczenia, data_zwrotu, status) VALUES (?, ?, ?, ?, ?)",
                                  (kid, czytelnik_wyp, str(dzis), str(termin), 'Wypożyczona'))
                        c.execute("UPDATE rezerwacje SET status = 'Oczekuje na zwrot' WHERE id = ?", (rid,))
                        conn.commit()
                        st.success("Wydano książkę czytelnikowi! Pozycja pozostanie na liście rezerwacji do momentu zwrotu.")
                        st.rerun()
                else:
                    st.info("Książka jest obecnie wypożyczona. Zniknie z rezerwacji po przyjęciu zwrotu w zakładce Wypożyczenia.")

            with col_rz3:
                if st.button("❌ Odrzuć / Anuluj rezerwację"):
                    c.execute("UPDATE ksiazki SET stan = 'Dostępna' WHERE id = (SELECT ksiazka_id FROM rezerwacje WHERE id = ?)", (rid,))
                    c.execute("UPDATE rezerwacje SET status = 'Anulowana' WHERE id = ?", (rid,))
                    conn.commit()
                    st.warning("Anulowano rezerwację. Książka znów jest Dostępna.")
                    st.rerun()

    with tab6:
        with st.form("form_settings"):
            nowy_czas = st.number_input("Domyślny czas trwania wypożyczenia (w dniach):", min_value=1, value=14)
            if st.form_submit_button("Zapisz ustawienia"):
                c.execute("UPDATE ustawienia SET wartosc = ? WHERE klucz = 'czas_wypozyczenia'", (str(nowy_czas),))
                conn.commit()
                st.success("Zapisano ustawienia!")

    with tab7:
        st.subheader("📊 Podsumowanie i Statystyki Biblioteki")
        c_s1, c_s2, c_s3 = st.columns(3)
        with c_s1:
            st.metric("Wszystkich książek", pd.read_sql("SELECT COUNT(*) FROM ksiazki", conn).iloc[0,0])
        with c_s2:
            st.metric("Zarejestrowanych czytelników", pd.read_sql("SELECT COUNT(*) FROM czytelnici", conn).iloc[0,0])
        with c_s3:
            st.metric("Aktywnych wypożyczeń", pd.read_sql("SELECT COUNT(*) FROM wypozyczenia WHERE status='Wypożyczona'", conn).iloc[0,0])

# ==========================================
# 2. KATALOG ONLINE OPAC (CZYTELNIK / ONLINE)
# ==========================================
else:
    if "koszyk" not in st.session_state:
        st.session_state["koszyk"] = []
    if "czytelnik_zalogowany" not in st.session_state:
        st.session_state["czytelnik_zalogowany"] = None

    col_logo, col_info, col_kontrast = st.columns([3, 5, 2])
    with col_logo:
        st.markdown("📖 **OPAC e-Biblioteka**")
    with col_info:
        if st.session_state["czytelnik_zalogowany"]:
            st.markdown(f"Zalogowany: **{st.session_state['czytelnik_zalogowany']}**")
        else:
            st.markdown("⚠️ *Niezalogowany*")
    with col_kontrast:
        ile_w_koszyku = len(st.session_state["koszyk"])
        st.markdown(f"📚 Półka: **{ile_w_koszyku}**")

    st.divider()

    menu_opac = st.radio("Menu:", ["Strona główna / Katalog", "Nowości", "Moja półka (Rezerwacje)", "Moje Konto / Rejestracja"], horizontal=True)
    st.markdown("---")

    if menu_opac == "Strona główna / Katalog":
        st.subheader("Wyszukaj książkę")
        szuk_opac = st.text_input("Szukaj (tytuł, autor, rodzaj)...", key="sz_op")
        
        if szuk_opac:
            q = "SELECT * FROM ksiazki WHERE tytul LIKE ? OR autor LIKE ? OR rodzaj LIKE ?"
            df_kat = pd.read_sql(q, conn, params=(f"%{szukaj_opac}%", f"%{szukaj_opac}%", f"%{szukaj_opac}%"))
        else:
            df_kat = pd.read_sql("SELECT * FROM ksiazki", conn)

        for index, row in df_kat.iterrows():
            col_b1, col_b2 = st.columns([5, 2])
            with col_b1:
                st.markdown(f"**{row['tytul']}** — *{row['autor']}*")
                st.caption(f"Rodzaj: {row['rodzaj']} | Stan: **{row['stan']}**")
            with col_b2:
                if row['stan'] == 'Dostępna':
                    if st.button(f"Dodaj do półki", key=f"rez_{row['id']}"):
                        if row['id'] not in st.session_state["koszyk"]:
                            st.session_state["koszyk"].append(row['id'])
                            st.success("Dodano do półki!")
                            st.rerun()
                elif row['stan'] == 'Zarezerwowana':
                    st.info("🔒 Zarezerwowana")
                else:
                    st.warning("📚 Wypożyczona")
            st.divider()

    elif menu_opac == "Nowości":
        st.subheader("Ostatnio dodane nowości")
        df_nowosci = pd.read_sql("SELECT tytul, autor, rodzaj, stan FROM ksiazki ORDER BY id DESC LIMIT 5", conn)
        st.dataframe(df_nowosci, use_container_width=True, hide_index=True)

    elif menu_opac == "Moja półka (Rezerwacje)":
        st.subheader("Twoja półka rezerwacji")
        st.markdown(f"Liczba pozycji na półce: **{len(st.session_state['koszyk'])}**")
        
        if st.session_state["koszyk"]:
            placeholders = ','.join(['?'] * len(st.session_state["koszyk"]))
            df_koszyk = pd.read_sql(f"SELECT * FROM ksiazki WHERE id IN ({placeholders})", conn, params=tuple(st.session_state["koszyk"]))
            st.dataframe(df_koszyk[['id', 'tytul', 'autor', 'stan']], use_container_width=True, hide_index=True)
            
            if st.button("Zarezerwuj wybrane pozycje"):
                if st.session_state["czytelnik_zalogowany"]:
                    for kid in st.session_state["koszyk"]:
                        c.execute("SELECT stan FROM ksiazki WHERE id = ?", (kid,))
                        aktualny_stan = c.fetchone()[0]
                        if aktualny_stan == 'Dostępna':
                            c.execute("INSERT INTO rezerwacje (ksiazka_id, czytelnik, data_rezerwacji, status) VALUES (?, ?, ?, ?)",
                                      (kid, st.session_state["czytelnik_zalogowany"], str(date.today()), 'Aktywna'))
                            c.execute("UPDATE ksiazki SET stan = 'Zarezerwowana' WHERE id = ?", (kid,))
                    conn.commit()
                    st.session_state["koszyk"] = []
                    st.success("Rezerwacja została wysłana do bibliotekarza!")
                    st.rerun()
                else:
                    st.error("❌ Musisz być zalogowany kodem, aby dokonać rezerwacji!")
            
            if st.button("Wyczyść półkę"):
                st.session_state["koszyk"] = []
                st.rerun()
        else:
            st.info("Twoja półka jest pusta.")

    elif menu_opac == "Moje Konto / Rejestracja":
        st.subheader("Strefa Czytelnika")
        tab_log, tab_reg = st.tabs(["🔑 Zaloguj się kodem", "📝 Zarejestruj nowe konto"])
        
        with tab_log:
            if not st.session_state["czytelnik_zalogowany"]:
                with st.form("form_log_czyt"):
                    kod_wejscie = st.text_input("Wpisz swój unikalny identyfikator / kod karty:")
                    if st.form_submit_button("Zaloguj się"):
                        c.execute("SELECT imie_nazwisko FROM czytelnici WHERE kod_karty = ?", (kod_wejscie,))
                        res = c.fetchone()
                        if res:
                            st.session_state["czytelnik_zalogowany"] = res[0]
                            st.success(f"Witaj, {res[0]}!")
                            st.rerun()
                        else:
                            st.error("Nie znaleziono czytelnika o takim kodzie.")
            else:
                st.write(f"Zalogowany użytkownik: **{st.session_state['czytelnik_zalogowany']}**")
                
                c.execute("SELECT k.tytul FROM rezerwacje r JOIN ksiazki k ON r.ksiazka_id = k.id WHERE r.czytelnik = ? AND r.status = 'Zaakceptowana'", (st.session_state["czytelnik_zalogowany"],))
                zaakceptowane_rezerwacje = c.fetchall()
                
                if zaakceptowane_rezerwacje:
                    st.success("🎉 **Twoja rezerwacja została zaakceptowana! Udaj się do biblioteki i odbierz swoje książki.**")
                    tytuly_zaak = ", ".join([row[0] for row in zaakceptowane_rezerwacje])
                    st.info(f"Dotyczy książek: **{tytuly_zaak}**")

                st.markdown("#### Twoje aktywne wypożyczenia:")
                df_w_cz = pd.read_sql("SELECT k.tytul, w.data_wypozyczenia, w.data_zwrotu FROM wypozyczenia w JOIN ksiazki k ON w.ksiazka_id = k.id WHERE w.czytelnik = ? AND w.status = 'Wypożyczona'", conn, params=(st.session_state["czytelnik_zalogowany"],))
                st.dataframe(df_w_cz, use_container_width=True, hide_index=True)

                st.markdown("#### Twoje aktywne rezerwacje:")
                df_r_cz = pd.read_sql("SELECT k.tytul, r.data_rezerwacji, r.status FROM rezerwacje r JOIN ksiazki k ON r.ksiazka_id = k.id WHERE r.czytelnik = ? AND r.status IN ('Aktywna', 'Zaakceptowana', 'Oczekuje na zwrot')", conn, params=(st.session_state["czytelnik_zalogowany"],))
                st.dataframe(df_r_cz, use_container_width=True, hide_index=True)
                
                if st.button("Wyloguj z konta"):
                    st.session_state["czytelnik_zalogowany"] = None
                    st.rerun()
                    
        with tab_reg:
            with st.form("form_reg_mobilna"):
                nowe_imie = st.text_input("Twoje Imię i Nazwisko:")
                nowy_kod = st.text_input("Wymyśl swój unikalny kod / PIN (np. 1234 lub własny identyfikator):")
                if st.form_submit_button("Zarejestruj się"):
                    if nowe_imie and nowy_kod:
                        try:
                            c.execute("INSERT INTO czytelnici (imie_nazwisko, kod_karty) VALUES (?, ?)", (nowe_imie, nowy_kod))
                            conn.commit()
                            st.success("Konto utworzone pomyślnie! Przejdź do zakładki logowania i wpisz swój kod.")
                        except sqlite3.IntegrityError:
                            st.error("❌ Ten kod/identyfikator jest już zajęty. Wybierz inny.")
                    else:
                        st.warning("Uzupełnij imię i kod.")

    st.markdown("---")
    st.caption("OPAC e-Biblioteka domowa — wersja 3.7")