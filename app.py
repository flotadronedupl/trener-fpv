import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai
from datetime import datetime

st.set_page_config(page_title="Trener FPV", page_icon="🚁", layout="wide")

# ==========================================
# BAZA DANYCH W PAMIĘCI (Struktura)
# ==========================================
if 'users_db' not in st.session_state:
    st.session_state.users_db = {
        # Twoje konto instruktorskie (nie da się go założyć przez stronę)
        'admin@fpv.pl': {
            'haslo': 'admin123', 
            'rola': 'Instruktor', 
            'imie': 'Główny Instruktor'
        },
        # Przykładowy kursant
        'janek@fpv.pl': {
            'haslo': 'janek123', 
            'rola': 'Kursant', 
            'imie': 'Janek', 
            'tokeny': 2, 
            'zadania': [] # <-- Tu będą wpadać raporty od AI
        }
    }

if 'zalogowany_uzytkownik' not in st.session_state:
    st.session_state.zalogowany_uzytkownik = None

# ==========================================
# EKRAN LOGOWANIA I REJESTRACJI
# ==========================================
if st.session_state.zalogowany_uzytkownik is None:
    st.title("🚁 Akademia FPV")
    st.markdown("Zaloguj się, aby uzyskać dostęp do panelu treningowego.")
    
    tab_logowanie, tab_rejestracja = st.tabs(["🔐 Zaloguj się", "📝 Zarejestruj nowe konto"])
    
    with tab_logowanie:
        login_email = st.text_input("Adres E-mail")
        login_haslo = st.text_input("Hasło", type="password")
        
        if st.button("🔓 Zaloguj", use_container_width=True):
            if login_email in st.session_state.users_db and st.session_state.users_db[login_email]['haslo'] == login_haslo:
                st.session_state.zalogowany_uzytkownik = login_email
                st.rerun()
            else:
                st.error("Nieprawidłowy e-mail lub hasło.")
                
    with tab_rejestracja:
        st.info("💡 Rejestracja jest otwarta tylko dla Kursantów. Konta instruktorskie nadaje administrator.")
        rej_imie = st.text_input("Twoje Imię")
        rej_email = st.text_input("Twój E-mail (będzie Twoim loginem)")
        rej_haslo = st.text_input("Wymyśl Hasło", type="password")
        
        if st.button("📝 Utwórz konto Kursanta", use_container_width=True):
            if rej_email in st.session_state.users_db:
                st.error("Konto z tym adresem e-mail już istnieje!")
            elif len(rej_haslo) < 4:
                st.error("Hasło musi mieć co najmniej 4 znaki.")
            else:
                # Zapisujemy zawsze jako Kursanta z pustą listą zadań
                st.session_state.users_db[rej_email] = {
                    'haslo': rej_haslo, 
                    'rola': 'Kursant', 
                    'imie': rej_imie,
                    'tokeny': 2,
                    'zadania': []
                }
                st.success("Konto utworzone! Przejdź do zakładki 'Zaloguj się'.")
                
    st.stop()

# ==========================================
# WŁAŚCIWA APLIKACJA
# ==========================================
user_email = st.session_state.zalogowany_uzytkownik
user_data = st.session_state.users_db[user_email]

with st.sidebar:
    st.image("https://images.unsplash.com/photo-1581404112613-3345155f308a?auto=format&fit=crop&q=80&w=200", caption="FPV Academy")
    st.success(f"Witaj, {user_data['imie']}!")
    st.write(f"**Rola:** {user_data['rola']}")
    st.divider()
    if st.button("🚪 Wyloguj się"):
        st.session_state.zalogowany_uzytkownik = None
        st.rerun()

# --- WIDOK 1: INSTRUKTOR ---
if user_data['rola'] == "Instruktor":
    st.title("🚁 Panel Instruktora")

    # Pobieramy listę tylko kursantów z naszej bazy
    lista_kursantow = [email for email, dane in st.session_state.users_db.items() if dane['rola'] == 'Kursant']

    with st.expander("⚙️ Ustawienia API (Rozwiń)"):
        api_key = st.text_input("Wklej klucz API Gemini:", type="password")
        if api_key:
            genai.configure(api_key=api_key)

    st.subheader("🔍 Przeprowadź Analizę")
    
    if not lista_kursantow:
        st.warning("Nie masz jeszcze żadnych zarejestrowanych kursantów!")
    else:
        # Instruktor wybiera komu przypisze lot!
        wybrany_kursant_email = st.selectbox(
            "Wybierz kursanta, którego lot analizujesz:", 
            lista_kursantow, 
            format_func=lambda x: f"{st.session_state.users_db[x]['imie']} ({x})"
        )
        
        st.info(f"Obecnie analizujesz lot dla: **{st.session_state.users_db[wybrany_kursant_email]['imie']}**")

        col1, col2 = st.columns(2)
        df = None 

        with col1:
            blackbox_file = st.file_uploader("Wgraj log (.csv)", type=['csv'])
            if blackbox_file:
                df = pd.read_csv(blackbox_file)
                st.line_chart(df.set_index(df.columns[0]))

        with col2:
            video_file = st.file_uploader("Wgraj wideo (.mp4)", type=['mp4'])
            if video_file:
                st.video(video_file)

        if st.button(f"🚀 Generuj i wyślij zadanie do: {st.session_state.users_db[wybrany_kursant_email]['imie']}", type="primary"):
            if not api_key:
                st.error("Wklej klucz API w ustawieniach!")
            elif df is not None:
                with st.spinner('AI analizuje...'):
                    # Tutaj AI generuje zadanie. Zrobimy tu symulację jeśli klucz zawiedzie, by aplikacja nie padła:
                    try:
                        dostepne_modele = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        wybrany_model = next((m for m in dostepne_modele if 'flash' in m.lower()), dostepne_modele[0])
                        model = genai.GenerativeModel(wybrany_model)
                        response = model.generate_content("Jesteś instruktorem FPV. Krótko opisz błąd poszarpanego gazu i wymyśl jedno krótkie zadanie.")
                        nowe_zadanie = response.text
                    except Exception as e:
                        nowe_zadanie = f"Wygenerowano awaryjnie: Zwróć uwagę na płynność gazu w zakrętach. (Błąd API: {e})"
                    
                    # MAGIA: Przypisujemy zadanie bezpośrednio do bazy wybranego kursanta!
                    data_wygenerowania = datetime.now().strftime("%Y-%m-%d %H:%M")
                    gotowy_raport = f"**Data:** {data_wygenerowania}\n\n{nowe_zadanie}"
                    
                    st.session_state.users_db[wybrany_kursant_email]['zadania'].append(gotowy_raport)
                    st.success(f"Zadanie pomyślnie przypisane do konta kursanta: {st.session_state.users_db[wybrany_kursant_email]['imie']}!")
            else:
                st.warning("Najpierw wgraj dane telemetryczne!")

# --- WIDOK 2: KURSANT ---
elif user_data['rola'] == "Kursant":
    st.title(f"🎓 Twój Panel Treningowy")

    st.info(f"🎟️ **Darmowe analizy (Tokeny):** {user_data['tokeny']} pozostały")

    st.divider()

    st.subheader("📋 Twoje Raporty i Zadania od AI")
    
    # Wyświetlamy tylko te zadania, które należą do tego kursanta!
    zadania = st.session_state.users_db[user_email]['zadania']
    
    if len(zadania) == 0:
        st.success("Wszystko zrobione! Obecnie nie masz przypisanych żadnych nowych zadań.")
    else:
        # Wyświetlamy zadania w odwrotnej kolejności (najnowsze na górze)
        for i, zadanie in enumerate(reversed(zadania)):
            with st.expander(f"Raport z analizy lotu #{len(zadania) - i}", expanded=(i==0)):
                st.markdown(zadanie)
    
    st.divider()

    st.subheader("📤 Zużyj token i przeanalizuj lot")
    sim_file = st.file_uploader("Wgraj plik z symulatora (.csv)", type=['csv'])
    
    if sim_file:
        if st.button("Wyślij do chmury (Zużywa 1 token)"):
            if st.session_state.users_db[user_email]['tokeny'] > 0:
                st.session_state.users_db[user_email]['tokeny'] -= 1
                st.success("Plik wgrany! Trwa analiza... (Odśwież stronę)")
            else:
                st.error("Nie masz już darmowych tokenów. Skontaktuj się z instruktorem.")
