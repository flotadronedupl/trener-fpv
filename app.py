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
import plotly.graph_objects as go

st.set_page_config(page_title="Trener FPV", page_icon="🚁", layout="wide")

# ==========================================
# AUTO-INSTALATOR DEKODERA BETAFLIGHT
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
        
        url = "https://github.com/betaflight/blackbox-tools/archive/refs/heads/master.zip"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        
        try:
            with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                out_file.write(response.read())
                
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                
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
        statystyki_lotu = ""

        with col1:
            uploaded_file = st.file_uploader("Wgraj log z drona (.bbl lub .csv)", type=['bbl', 'csv'])
            
            if uploaded_file:
                nazwa_pliku = uploaded_file.name.lower()
                
                if nazwa_pliku.endswith('.csv'):
                    st.success("✅ Wgrano gotowy plik CSV. Analizuję...")
                    df = pd.read_csv(uploaded_file)
                    
                elif nazwa_pliku.endswith('.bbl'):
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
                                    st.error("Dekoder zadziałał, ale nie znalazł danych lotu (być może plik jest pusty).")
                            else:
                                st.error("Nie udało się zbudować dekodera na serwerze.")
                        except Exception as e:
                            st.error(f"⚠️ Wystąpił problem z surowym plikiem BBL: {e}")
                            st.info("Wyeksportuj log jako .csv w Betaflight Blackbox Explorer i wgraj go tutaj.")

                if df is not None:
                    rc_cols = [col for col in df.columns if 'rcCommand' in col]
                    if len(rc_cols) >= 4:
                        roll_col, pitch_col, yaw_col, thr_col = rc_cols[0], rc_cols[1], rc_cols[2], rc_cols[3]
                        
                        avg_thr = df[thr_col].mean()
                        jerk_thr = df[thr_col].diff().abs().mean()
                        jerk_roll = df[roll_col].diff().abs().mean()
                        jerk_pitch = df[pitch_col].diff().abs().mean()
                        
                        statystyki_lotu = (
                            f"- Średnia wartość przepustnicy (Throttle): {avg_thr:.1f}\n"
                            f"- Wskaźnik szarpania gazem (Jerk): {jerk_thr:.2f} (im wyższy, tym gorsza płynność)\n"
                            f"- Wskaźnik szarpania osią Roll: {jerk_roll:.2f}\n"
                            f"- Wskaźnik szarpania osią Pitch: {jerk_pitch:.2f}"
                        )
                        st.info("🧠 Zebrano dane telemetryczne dla AI (Jerk, Średnie Wychylenia).")

                        # ==========================================
                        # KLASYCZNY WYKRES 2D (SZARPANIE)
                        # ==========================================
                        st.subheader("📈 Interaktywna Telemetria (2D)")
                        plot_df = df.head(3000)
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(y=plot_df[thr_col], mode='lines', name='Throttle (Gaz)', line=dict(color='orange', width=2)))
                        fig.add_trace(go.Scatter(y=plot_df[roll_col], mode='lines', name='Roll (Obrót)', line=dict(color='blue', width=1), opacity=0.7))
                        fig.add_trace(go.Scatter(y=plot_df[pitch_col], mode='lines', name='Pitch (Pochylenie)', line=dict(color='green', width=1), opacity=0.7))
                        
                        fig.update_layout(
                            title="Ruchy drążków w czasie",
                            xaxis_title="Czas (mikrosekundy / próbki)",
                            yaxis_title="Wartość z drążka",
                            template="plotly_dark",
                            hovermode="x unified",
                            height=350,
                            margin=dict(l=0, r=0, t=40, b=0)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # ==========================================
                        # NOWOŚĆ: IMMERSYJNY TUNEL LOTU (3D)
                        # ==========================================
                        st.markdown("---")
                        st.subheader("🪐 Przestrzenny Tunel Lotu (3D)")
                        st.info("Eksperymentalna symulacja! Oś pionowa to czas lotu, a osie płaskie to Twoje ruchy drążkami. Kolor linii oznacza poziom gazu (niebieski - dół, czerwony - pełny gaz). Obracaj wykres myszką!")
                        
                        # Matematyka całkowania ruchów drążków
                        x_3d = plot_df[roll_col].cumsum() / 500  
                        y_3d = plot_df[pitch_col].cumsum() / 500 
                        z_3d = np.arange(len(plot_df)) 
                        kolor_gazu = plot_df[thr_col] 
                        
                        fig3d = go.Figure(data=[go.Scatter3d(
                            x=x_3d,
                            y=y_3d,
                            z=z_3d,
                            mode='lines',
                            line=dict(
                                color=kolor_gazu,
                                colorscale='Jet', 
                                width=5
                            )
                        )])
                        
                        fig3d.update_layout(
                            template="plotly_dark",
                            margin=dict(l=0, r=0, b=0, t=10),
                            scene=dict(
                                xaxis_title='Wychylenie Roll',
                                yaxis_title='Wychylenie Pitch',
                                zaxis_title='Czas Lotu (Postęp)',
                                camera=dict(
                                    up=dict(x=0, y=0, z=1),
                                    center=dict(x=0, y=0, z=0),
                                    eye=dict(x=1.5, y=1.5, z=1.5)
                                )
                            ),
                            height=450
                        )
                        st.plotly_chart(fig3d, use_container_width=True)

                    else:
                        st.warning("Plik nie zawiera standardowych kolumn 'rcCommand'. Wyświetlam podstawowy wykres.")
                        st.line_chart(df.iloc[:, 1:4].head(2000))

        # ==========================================
        # MODUŁ WIDEO (CHMURA / LINKI)
        # ==========================================
        with col2:
            st.markdown("### 🎥 Wideo z lotu")
            st.info("💡 Wklej link do nagrania (YouTube lub Dysk Google), aby ominąć wszelkie limity wielkości plików.")
            video_url = st.text_input("🔗 Wklej link do wideo:")
            
            if video_url:
                try:
                    if "drive.google.com" in video_url:
                        embed_url = video_url.replace('/view', '/preview').split('?')[0]
                        st.components.v1.iframe(embed_url, height=400)
                    elif "youtube.com" in video_url or "youtu.be" in video_url:
                        st.video(video_url)
                    else:
                        st.markdown(f"👉 [Kliknij tutaj, aby otworzyć wideo w nowej karcie]({video_url})")
                except Exception as e:
                    st.error("Nie udało się załadować podglądu wideo. Upewnij się, że link jest poprawny.")

        if st.button(f"🚀 Generuj i wyślij zadanie", type="primary"):
            if not api_key:
                st.error("Wklej klucz API w ustawieniach!")
            elif df is not None and statystyki_lotu != "":
                with st.spinner('AI analizuje parametry lotu i wysyła do bazy...'):
                    try:
                        dostepne_modele = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        wybrany_model = next((m for m in dostepne_modele if 'flash' in m.lower()), dostepne_modele[0])
                        model = genai.GenerativeModel(wybrany_model)
                        
                        prompt = f"""
                        Jesteś eksperckim instruktorem drona FPV (Acro mode). 
                        Przeanalizowałem matematycznie logi z lotu z czarnej skrzynki mojego kursanta. 
                        Oto precyzyjne wyniki:
                        {statystyki_lotu}
                        
                        Zinterpretuj te dane. Zwróć uwagę na wskaźnik szarpania (Jerk - idealny pilot ma go jak najniższego). 
                        Napisz dla ucznia krótką, profesjonalną diagnozę (2-3 zdania) i podaj mu 1 konkretne zadanie treningowe na symulator lub na tor, które poprawi jego płynność. Pisz bezpośrednio do ucznia na 'Ty'.
                        """
                        
                        response = model.generate_content(prompt)
                        nowe_zadanie = response.text
                    except Exception as e:
                        nowe_zadanie = f"Błąd AI: {e}. Awaryjne zadanie: Skup się na płynnym przechodzeniu przez bramki."

                    data_wygenerowania = datetime.now().strftime("%Y-%m-%d %H:%M")
                    raport_wideo = f"\n\n**Twój lot:** [Obejrzyj nagranie]({video_url})" if video_url else ""
                    gotowy_raport = f"**Data:** {data_wygenerowania}\n\n{nowe_zadanie}{raport_wideo}"
                    
                    aktualne_zadania = next(k['zadania'] for k in kursanci if k['email'] == wybrany_email)
                    aktualne_zadania.append(gotowy_raport)
                    supabase.table('konta').update({'zadania': aktualne_zadania}).eq('email', wybrany_email).execute()
                    st.success(f"Zadanie zapisane w bazie chmurowej! Kursant zobaczy je po zalogowaniu.")
            else:
                st.warning("Najpierw wgraj prawidłowe dane telemetryczne (z kolumnami rcCommand)!")

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
