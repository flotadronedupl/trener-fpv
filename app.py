import streamlit as st
import pandas as pd
import numpy as np
import google.generativeai as genai
from datetime import datetime
from supabase import create_client, Client
import os
import urllib.request
import zipfile
import subprocess
import glob
import shutil
import time

st.set_page_config(page_title="Trener FPV", page_icon="🚁", layout="wide")

# ==========================================
# AUTO-INSTALATOR DEKODERA BETAFLIGHT (Działa w tle na serwerze)
# ==========================================
@st.cache_resource
def get_decoder_path():
    extract_dir = "/tmp/bbt_source"
    zip_path = "/tmp/bbt_src.zip"
    executable = f"{extract_dir}/blackbox-tools-master/obj/blackbox_decode"
    
    if not os.path.exists(executable):
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir, exist_ok=True)
        
        # Pobieramy czysty kod źródłowy z GitHuba
        url = "https://github.com/betaflight/blackbox-tools/archive/refs/heads/master.zip"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        
        try:
            with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                out_file.write(response.read())
                
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                
            # KOMPILACJA NA ŻYWO NA SERWERZE (Magia Linuxa)
            source_dir = f"{extract_dir}/blackbox-tools-master"
            subprocess.run(["make", "obj/blackbox_decode"], cwd=source_dir, check=True, capture_output=True)
            
        except Exception as e:
            st.cache_resource.clear()
            raise RuntimeError(f"Serwer nie poradził sobie z kompilacją kodu: {e}")
            
    if os.path.exists(executable):
        os.chmod(executable, 0o755)
        return executable
        
    st.cache_resource.clear()
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
try:
    odp = supabase.table('konta').select('*').eq('email', st.session_state.zalogowany_uzytkownik).execute()
    user_data = odp.data[0]
except Exception as e:
    st.error("Błąd pobierania danych z bazy. Odśwież stronę.")
    st.stop()

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
            # PANCERNA OBSŁUGA PLIKÓW: BBL oraz CSV
            uploaded_file = st.file_uploader("Wgraj log z drona (.bbl lub .csv)", type=['bbl', 'csv'])
            
            if uploaded_file:
                # Scenariusz 1: Użytkownik wgrał plik CSV (działa po staremu!)
                if uploaded_file.name.endswith('.csv'):
                    st.success("✅ Wgrano gotowy plik CSV. Analizuję...")
                    df = pd.read_csv(uploaded_file)
                    
                # Scenariusz 2: Użytkownik wgrał surowy plik BBL
                elif uploaded_file.name.endswith('.bbl'):
                    with st.spinner("Kompilowanie narzędzi i dekodowanie czarnej skrzynki..."):
                        try:
                            decoder_path = get_decoder_path()
                            if decoder_path:
                                for f in glob.glob("/tmp/temp_log*"):
                                    try: os.remove(f)
                                    except: pass
                                    
                                temp_bbl = "/tmp/temp_log.bbl"
                                with open(temp_bbl, "wb") as f:
                                    f.write(uploaded_file.getbuffer())
                                
                                subprocess.run([decoder_path, temp_bbl], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                
                                csv_files = sorted(glob.glob("/tmp/temp_log*.csv"))
                                if csv_files:
                                    st.success(f"✅ Pomyślnie rozkodowano plik BBL!")
                                    df = pd.read_csv(csv_files[0])
                                else:
                                    st.error("Dekoder zadziałał, ale nie wygenerował pliku CSV.")
                            else:
                                st.error("Nie udało się zbudować dekodera na serwerze.")
                        except Exception as e:
                            st.error(f"⚠️ Wystąpił problem z surowym plikiem BBL: {e}")
                            st.info("Zalecenie: Twój stary sprawdzony sposób działa! Wyeksportuj log jako .csv w Betaflight Blackbox Explorer i wgraj go tutaj.")

                # Rysowanie wykresu
                if df is not None:
                    rc_cols = [col for col in df.columns if 'rcCommand' in col]
                    if rc_cols:
                        st.line_chart(df[rc_cols].head(2000))
                    else:
                        st.info("Brak kolumn RC. Wyświetlam inne dane telemetryczne.")
                        st.line_chart(df.iloc[:, 1:4].head(2000))

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
                        
                        probka_danych = df.head(100).to_string()
                        prompt = f"Jesteś instruktorem FPV. Oto próbka danych z drona:\n{probka_danych}\nZwróć uwagę na płynność i wymyśl jedno konkretne zadanie poprawkowe dla kursanta. Bądź profesjonalny i zwięzły."
                        
                        response = model.generate_content(prompt)
                        nowe_zadanie = response.text
                    except Exception as e:
                        nowe_zadanie = f"Błąd AI: {e}. Awaryjne zadanie: Skup się na płynnym przechodzeniu przez bramki."

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
                
    st.divider()
    st.subheader("📤 Zużyj token i przeanalizuj lot")
    sim_file = st.file_uploader("Wgraj plik z symulatora (.csv)", type=['csv'])

    if sim_file:
        if st.button("Wyślij do chmury (Zużywa 1 token)"):
            if user_data['tokeny'] > 0:
                nowe_tokeny = user_data['tokeny'] - 1
                supabase.table('konta').update({'tokeny': nowe_tokeny}).eq('email', st.session_state.zalogowany_uzytkownik).execute()
                st.success("Plik wgrany! Trwa analiza... Token zużyty.")
                time.sleep(2)
                st.rerun()
            else:
                st.error("Nie masz już darmowych tokenów. Skontaktuj się z instruktorem.")
