import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai

st.set_page_config(page_title="Trener FPV", page_icon="🚁", layout="wide")

# --- BAZA DANYCH W PAMIĘCI (Do testów) ---
# Te dane znikną po restarcie serwera. Docelowo podepniemy tu prawdziwą bazę.
if 'users_db' not in st.session_state:
    st.session_state.users_db = {
        'admin@fpv.pl': {'haslo': 'admin123', 'rola': 'Instruktor', 'imie': 'Szef'},
        'janek@fpv.pl': {'haslo': 'janek123', 'rola': 'Kursant', 'imie': 'Janek', 'tokeny': 2}
    }

# Zmienna przechowująca informację, kto jest zalogowany
if 'zalogowany_uzytkownik' not in st.session_state:
    st.session_state.zalogowany_uzytkownik = None

# ==========================================
# EKRAN LOGOWANIA I REJESTRACJI
# ==========================================
if st.session_state.zalogowany_uzytkownik is None:
    st.title("🚁 Akademia FPV")
    st.markdown("Zaloguj się, aby uzyskać dostęp do panelu treningowego.")
    
    # Tworzymy dwie zakładki na środku ekranu
    tab_logowanie, tab_rejestracja = st.tabs(["🔐 Zaloguj się", "📝 Zarejestruj nowe konto"])
    
    with tab_logowanie:
        st.subheader("Masz już konto?")
        login_email = st.text_input("Adres E-mail")
        login_haslo = st.text_input("Hasło", type="password") # Kropki zamiast liter!
        
        if st.button("🔓 Zaloguj", use_container_width=True):
            if login_email in st.session_state.users_db and st.session_state.users_db[login_email]['haslo'] == login_haslo:
                st.session_state.zalogowany_uzytkownik = login_email
                st.success("Zalogowano pomyślnie!")
                st.rerun() # Odświeża stronę, by wczytać odpowiedni panel
            else:
                st.error("Nieprawidłowy e-mail lub hasło.")
                
    with tab_rejestracja:
        st.subheader("Dołącz do Akademii")
        rej_imie = st.text_input("Twoje Imię")
        rej_email = st.text_input("Twój E-mail (będzie Twoim loginem)")
        rej_haslo = st.text_input("Wymyśl Hasło", type="password")
        rej_rola = st.selectbox("Kim jesteś?", ["Kursant", "Instruktor"])
        
        if st.button("📝 Utwórz konto", use_container_width=True):
            if rej_email in st.session_state.users_db:
                st.error("Konto z tym adresem e-mail już istnieje!")
            elif len(rej_haslo) < 4:
                st.error("Hasło musi mieć co najmniej 4 znaki.")
            else:
                # Zapisujemy nowego użytkownika do naszej "bazy"
                st.session_state.users_db[rej_email] = {
                    'haslo': rej_haslo, 
                    'rola': rej_rola, 
                    'imie': rej_imie,
                    'tokeny': 2 if rej_rola == "Kursant" else 999
                }
                st.success("Konto utworzone! Przejdź do zakładki 'Zaloguj się'.")
                
    st.stop() # Bardzo ważne: zatrzymuje ładowanie reszty kodu, dopóki ktoś się nie zaloguje!

# ==========================================
# WŁAŚCIWA APLIKACJA (Po zalogowaniu)
# ==========================================

# Pobieramy dane zalogowanego użytkownika
user_email = st.session_state.zalogowany_uzytkownik
user_data = st.session_state.users_db[user_email]

# --- WSPÓLNY PASEK BOCZNY ---
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1581404112613-3345155f308a?auto=format&fit=crop&q=80&w=200", caption="FPV Academy")
    st.success(f"Witaj, {user_data['imie']}!")
    st.write(f"**Rola:** {user_data['rola']}")
    st.write(f"**E-mail:** {user_email}")
    
    st.divider()
    
    if st.button("🚪 Wyloguj się"):
        st.session_state.zalogowany_uzytkownik = None
        st.rerun()

# --- WIDOK 1: INSTRUKTOR ---
if user_data['rola'] == "Instruktor":
    st.title("🚁 Panel Instruktora")
    st.markdown("Zarządzaj flotą, analizuj loty i zlecaj zadania.")

    with st.expander("⚙️ Ustawienia API (Rozwiń)"):
        api_key = st.text_input("Wklej klucz API Gemini:", type="password")
        if api_key:
            genai.configure(api_key=api_key)
            st.success("Klucz API podłączony!")

    st.subheader("🔍 Nowa Analiza Lotu")
    col1, col2 = st.columns(2)
    df = None 

    with col1:
        blackbox_file = st.file_uploader("Wgraj log (.csv)", type=['csv'])
        if blackbox_file:
            df = pd.read_csv(blackbox_file)
            st.line_chart(df.set_index(df.columns[0]))
        else:
            st.info("Oczekiwanie na plik z logami...")

    with col2:
        video_file = st.file_uploader("Wgraj wideo z drona (.mp4)", type=['mp4'])
        if video_file:
            st.video(video_file)

    if st.button("🚀 Wygeneruj Raport AI (Dla Janka)"):
        if not api_key:
            st.error("Wklej klucz API w ustawieniach!")
        elif df is not None:
            st.success("Symulacja raportu: Uczeń szarpie gazem. Zadanie wysłane!")
        else:
            st.warning("Najpierw wgraj dane!")

# --- WIDOK 2: KURSANT ---
elif user_data['rola'] == "Kursant":
    st.title(f"🎓 Cześć {user_data['imie']}!")
    st.markdown("Oto Twój osobisty panel treningowy.")

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"🎟️ **Darmowe analizy (Tokeny):** {user_data['tokeny']} pozostały")
    with col2:
        st.success("✅ **Twój poziom:** Oczekuje na weryfikację")

    st.divider()

    st.subheader("📋 Twoje zadania od AI")
    st.warning("Brak nowych zadań. Wgraj swój pierwszy lot, aby AI mogło Cię ocenić!")
    
    st.divider()

    st.subheader("📤 Wgraj lot z symulatora")
    sim_file = st.file_uploader("Wgraj plik z symulatora", type=['csv', 'txt'])
    
    if sim_file:
        if st.button("Wyślij do chmury (Zużywa 1 token)"):
            if st.session_state.users_db[user_email]['tokeny'] > 0:
                st.session_state.users_db[user_email]['tokeny'] -= 1
                st.success("Plik wgrany! Trwa analiza...")
                st.rerun() # Odświeżamy, żeby licznik tokenów spadł
            else:
                st.error("Nie masz już darmowych tokenów. Skontaktuj się z instruktorem.")
