import streamlit as st
import sqlite3
from datetime import date

st.set_page_config(page_title="System Biblioteczny Pro+", layout="wide")

# --- BAZA DANYCH ---
def zainicjalizuj_baze():
    conn = sqlite3.connect("biblioteka_nowa.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            genre TEXT,
            barcode TEXT,
            available_copies INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            barcode TEXT UNIQUE
        )
    """)

    cursor.execute("PRAGMA table_info(Users)")
    kolumny_users = [k[1] for k in cursor.fetchall()]
    if "barcode" not in kolumny_users:
        try:
            cursor.execute("ALTER TABLE Users ADD COLUMN barcode TEXT UNIQUE")
        except sqlite3.OperationalError:
            pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER,
            user_id INTEGER,
            borrow_date TEXT,
            due_date TEXT,
            FOREIGN KEY (book_id) REFERENCES Books(id),
            FOREIGN KEY (user_id) REFERENCES Users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO Settings (key, value) VALUES ('loan_days', '14')")
    conn.commit()
    conn.close()

zainicjalizuj_baze()

# --- STAN SESJI DO LOGOWANIA ---
if "zalogowany_user" not in st.session_state:
    st.session_state["zalogowany_user"] = None
if "zalogowany_id" not in st.session_state:
    st.session_state["zalogowany_id"] = None

# --- EKRAN LOGOWANIA ---
if st.session_state["zalogowany_user"] is None:
    st.title("📚 System Biblioteczny Pro+")
    st.write("Zeskanuj kod kreskowy lub wpisz swój identyfikator (Wpisz **1234** dla administratora):")

    with st.form("form_logowania"):
        kod = st.text_input("Identyfikator / Kod kreskowy:", type="password")
        submit = st.form_submit_button("Zaloguj się", type="primary")

        if submit:
            kod = kod.strip()
            if kod == "1234":
                st.session_state["zalogowany_user"] = "Administrator"
                st.session_state["zalogowany_id"] = "admin"
                st.rerun()
            else:
                conn = sqlite3.connect("biblioteka_nowa.db")
                cursor = conn.cursor()
                cursor.execute("SELECT id, name FROM Users WHERE barcode = ? OR id = ?", (kod, kod))
                uzytkownik = cursor.fetchone()
                conn.close()

                if uzytkownik:
                    st.session_state["zalogowany_id"] = uzytkownik[0]
                    st.session_state["zalogowany_user"] = uzytkownik[1]
                    st.rerun()
                else:
                    st.error("Błędny identyfikator pracownika lub użytkownika!")
    st.stop()

# --- GŁÓWNA APLIKACIJA STREAMLIT ---
st.sidebar.markdown(f"👤 **Zalogowany:** {st.session_state['zalogowany_user']}")
if st.sidebar.button("Wyloguj"):
    st.session_state["zalogowany_user"] = None
    st.session_state["zalogowany_id"] = None
    st.rerun()

menu = st.sidebar.radio("Nawigacja", ["Książki", "Użytkownicy", "Wypożyczenia", "Ustawienia"])

conn = sqlite3.connect("biblioteka_nowa.db")
cursor = conn.cursor()

if menu == "Książki":
    st.header("📚 Katalog Książek")
    
    if str(st.session_state["zalogowany_id"]) == "admin":
        with st.expander("Dodaj nową książkę"):
            with st.form("dodaj_ksiazke_form"):
                tytul = st.text_input("Tytuł")
                autor = st.text_input("Autor")
                gatunek = st.text_input("Gatunek")
                kod_k = st.text_input("Kod kreskowy")
                sztuki = st.number_input("Liczba egzemplarzy", min_value=1, value=1)
                if st.form_submit_button("Dodaj"):
                    cursor.execute("INSERT INTO Books (title, author, genre, barcode, available_copies) VALUES (?, ?, ?, ?, ?)", 
                                   (tytul, autor, gatunek, kod_k, sztuki))
                    conn.commit()
                    st.success("Dodano książkę!")
                    st.rerun()

    szukaj = st.text_input("🔍 Szukaj książki:")
    if szukaj:
        cursor.execute("SELECT * FROM Books WHERE title LIKE ? OR author LIKE ?", (f"%{szukaj}%", f"%{szukaj}%"))
    else:
        cursor.execute("SELECT * FROM Books")
    
    ksiazki = cursor.fetchall()
    for k in ksiazki:
        st.write(f"**ID:** {k[0]} | **{k[1]}** - {k[2]} (Dostępne sztuki: {k[5]})")

elif menu == "Użytkownicy":
    st.header("👤 Użytkownicy")
    if str(st.session_state["zalogowany_id"]) == "admin":
        with st.form("dodaj_czytelnika"):
            nazwa = st.text_input("Imię i nazwisko")
            kod_b = st.text_input("Kod kreskowy / Login")
            if st.form_submit_button("Zarejestruj czytelnika"):
                try:
                    cursor.execute("INSERT INTO Users (name, barcode) VALUES (?, ?)", (nazwa, kod_b if kod_b else None))
                    conn.commit()
                    st.success("Zarejestrowano użytkownika!")
                    st.rerun()
                except:
                    st.error("Ten kod jest już zajęty!")
        
        cursor.execute("SELECT * FROM Users")
        for u in cursor.fetchall():
            st.write(f"ID: {u[0]} | Nazwa: {u[1]} | Kod: {u[2]}")
    else:
        st.write(f"Twoje dane ID: {st.session_state['zalogowany_id']}")

elif menu == "Wypożyczenia":
    st.header("🔄 Wypożyczenia")
    cursor.execute("SELECT Loans.id, Users.name, Books.title, Loans.borrow_date, Loans.due_date FROM Loans JOIN Users ON Loans.user_id = Users.id JOIN Books ON Loans.book_id = Books.id")
    wypozyczenia = cursor.fetchall()
    for w in wypozyczenia:
        st.write(f"Wypożyczenie ID: {w[0]} | Czytelnik: {w[1]} | Książka: {w[2]} (Od: {w[3]} do: {w[4]})")

elif menu == "Ustawienia":
    st.header("⚙️ Ustawienia systemu")
    st.write(f"Zalogowany jako: {st.session_state['zalogowany_user']}")

conn.close()
