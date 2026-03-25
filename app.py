import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai
from datetime import datetime
from supabase import create_client, Client
import os
import urllib.request
import tarfile
import subprocess
import glob

st.set_page_config(page_title="Trener FPV", page_icon="🚁", layout="wide")

# ==========================================
# AUTO-INSTALATOR DEKODERA BETAFLIGHT (Działa w tle na serwerze)
# ==========================================
@st.cache_resource
def get_decoder_path():
    url = "https://github.com/betaflight/blackbox-tools/releases/download/v0.4.3/blackbox-tools-0.4.3-linux.tar.gz"
    tar_path = "/tmp/bbt.tar.gz"
    extract_dir = "/tmp/bbt_extracted"
    
    # Jeśli serwer jeszcze nie ma dekodera, pobiera go z internetu
    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir, exist_ok=True)
        urllib.request.urlretrieve(url, tar_path)
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=extract_dir)
            
    # Znajduje plik wykonywalny i nadaje mu uprawnienia
    executable = glob.glob(f"{extract_dir}/**/blackbox_decode", recursive=True)
    if executable:
        os.chmod(executable[0], 0o755)
        return executable[0]
    return None

# ==========================================
# POŁĄCZENIE Z BAZĄ SUPABASE
# ==========================================
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase()

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
            try:
                odpowiedz = supabase.table('konta').select('*').eq('email', login_email).execute()
                dane = odpowiedz.data
                if len(dane) > 0 and dane[0]['haslo'] == login_haslo:
                    st.session_state.zalogowany_uzytkownik = login_email
                    st.rerun()
                else:
                    st.error("Nieprawidłowy e-mail lub hasło.")
            except Exception as e:
                st.error(f"Błąd połączenia z bazą: {e}")

    with tab_rejestracja:
        st.info("💡 Rejestracja jest otwarta tylko dla Kursantów.")
        rej_imie = st.text_input("Twoje Imię")
        rej_email = st.text_input("Twój E-mail (będzie Twoim loginem)")
        rej_haslo = st.text_input("Wymyśl Hasło", type="password")

        if st.button("📝 Utwórz konto Kursanta", use_container_width=True):
            if len(rej_haslo) < 4:
                st.error("Hasło musi mieć co najmniej 4 znaki.")
            else:
                try:
                    sprawdzenie = supabase.table('konta').select('email').eq('email', rej_email).execute()
                    if len(sprawdzenie.data) > 0:
                        st.error("Konto z tym adresem e-mail już istnieje!")
                    else:
                        nowy_user = {
                            'email': rej_email, 'haslo': rej_haslo, 'imie': rej_imie,
                            'rola': 'Kursant', 'tokeny': 2, 'zadania': []
                        }
                        supabase.table('konta').insert(nowy_user).execute()
                        st.success("Konto utworzone! Przejdź do zakładki 'Zaloguj się'.")
                except Exception as e:
                    st.error(f"Wystąpił błąd: {e}")
    st.stop()

# ==========================================
# WŁAŚCIWA APLIKACJA (Po zalogowaniu)
# ==========================================
odp = supabase.table('konta').select('*').eq('email', st.session_state.zalogowany_uzytkownik).execute()
user_data = odp.data[0]

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

    wszyscy = supabase.table('konta').select('email, imie, zadania').eq('rola', 'Kursant').execute()
    kursanci = wszyscy.data

    with st.expander("⚙️ Ustawienia API (Rozwiń)"):
        api_key = st.text_input("Wklej klucz API Gemini:", type="password")
        if api_key:
            genai.configure(api_key=api_key)

    st.subheader("🔍 Przeprowadź Analizę")

    if not kursanci:
        st.warning("Nie masz jeszcze żadnych zarejestrowanych kursantów!")
    else:
        opcje_kursantow = {k['email']: f"{k['imie']} ({k['email']})" for k in kursanci}
        wybrany_email = st.selectbox("Wybierz kursanta:", options=list(opcje_kursantow.keys()), format_func=lambda x: opcje_kursantow[x])

        col1, col2 = st.columns(2)
        df = None

        with col1:
            # Zmiana: Teraz przyjmujemy surowe pliki .BBL!
            bbl_file = st.file_uploader("Wgraj SUROWY log z drona (.bbl)", type=['bbl'])
            
            if bbl_file:
                with st.spinner("Dekodowanie czarnej skrzynki..."):
                    decoder_path = get_decoder_path()
                    
                    if decoder_path:
                        # Czyszczenie starych plików tymczasowych
                        for f in glob.glob("/tmp/temp_log*"):
                            os.remove(f)
                            
                        # Zapisanie pliku .bbl na serwerze
                        temp_bbl = "/tmp/temp_log.bbl"
                        with open(temp_bbl, "wb") as f:
                            f.write(bbl_file.getbuffer())
                        
                        # Odpalenie dekodera
                        subprocess.run([decoder_path, temp_bbl], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        
                        # Szukanie wygenerowanego pliku CSV (Betaflight dodaje numery np. 01, 02)
                        csv_files = sorted(glob.glob("/tmp/temp_log*.csv"))
                        
                        if csv_files:
                            st.success(f"✅ Rozkodowano lot! Znaleziono zapisów: {len(csv_files)}. Analizuję pierwszy lot.")
                            df = pd.read_csv(csv_files[0])
                            
                            # Próba narysowania wykresu (szukamy kolumn z gazem i osiami)
                            rc_cols = [col for col in df.columns if 'rcCommand' in col]
                            if rc_cols:
                                st.line_chart(df[rc_cols].head(2000)) # Rysujemy początek lotu
                            else:
                                st.info("Brak kolumn RC. Wyświetlam inne dane telemetryczne.")
                                st.line_chart(df.iloc[:, 1:4].head(2000))
                        else:
                            st.error("Nie udało się wyciągnąć danych z tego pliku .bbl.")
                    else:
                        st.error("Błąd krytyczny: Nie udało się zainstalować dekodera na serwerze.")

        with col2:
            video_file = st.file_uploader("Wgraj wideo z drona (.mp4)", type=['mp4'])
            if video_file:
                st.video(video_file)

        if st.button(f"🚀 Generuj i wyślij zadanie", type="primary"):
            if not api_key:
                st.error("Wklej klucz API w ustawieniach!")
            elif df is not None:
                with st.spinner('AI analizuje i wysyła do bazy...'):
                    try:
                        dostepne_modele = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        wybrany_model = next((m for m in dostepne_modele if 'flash' in m.lower()), dostepne_modele[0])
                        model = genai.GenerativeModel(wybrany_model)
                        
                        # Wysyłamy do AI proste statystyki z lotu, by nie przeciążyć limitów
                        probka_danych = df.head(100).to_string()
                        prompt = f"Jesteś instruktorem FPV. Oto próbka danych z drona:\n{probka_danych}\nZwróć uwagę na płynność i wymyśl jedno konkretne zadanie poprawkowe dla kursanta. Bądź profesjonalny i zwięzły."
                        
                        response = model.generate_content(prompt)
                        nowe_zadanie = response.text
                    except Exception as e:
                        nowe_zadanie = f"Błąd w komunikacji z Gemini. System awaryjnie przypisał trening: Skup się na płynnym przechodzeniu przez bramki. ({e})"

                    data_wygenerowania = datetime.now().strftime("%Y-%m-%d %H:%M")
                    gotowy_raport = f"**Data:** {data_wygenerowania}\n\n{nowe_zadanie}"
                    aktualne_zadania = next(k['zadania'] for k in kursanci if k['email'] == wybrany_email)
                    aktualne_zadania.append(gotowy_raport)
                    supabase.table('konta').update({'zadania': aktualne_zadania}).eq('email', wybrany_email).execute()
                    st.success(f"Zadanie zapisane w bazie chmurowej! Kursant zobaczy je po zalogowaniu.")
            else:
                st.warning("Najpierw wgraj dane telemetryczne!")

# --- WIDOK 2: KURSANT ---
elif user_data['rola'] == "Kursant":
    st.title(f"🎓 Twój Panel Treningowy")
    st.info(f"🎟️ **Darmowe analizy (Tokeny):** {user_data['tokeny']} pozostały")
    st.divider()
    st.subheader("📋 Twoje Raporty i Zadania od AI")
    zadania = user_data['zadania']
    if len(zadania) == 0:
        st.success("Wszystko zrobione! Obecnie nie masz przypisanych żadnych nowych zadań.")
    else:
        for i, zadanie in enumerate(reversed(zadania)):
            with st.expander(f"Raport z analizy lotu #{len(zadania) - i}", expanded=(i==0)):
                st.markdown(zadanie)
