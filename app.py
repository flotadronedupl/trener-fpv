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
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Trener FPV", page_icon="🚁", layout="wide")

# ==========================================
# KONFIGURACJA API GEMINI (Z Bezpiecznych Sekretów)
# ==========================================
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error("🚨 Brak klucza API Gemini! Dodaj GEMINI_API_KEY w ustawieniach Secrets na stronie Streamlit Cloud.")
    st.stop()

# ==========================================
# ZARZĄDZANIE PAMIĘCIĄ SESJI
# ==========================================
if 'raport_draft' not in st.session_state:
    st.session_state.raport_draft = None
if 'raport_meta' not in st.session_state:
    st.session_state.raport_meta = None

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

# ==========================================
# WIDOK 1: INSTRUKTOR
# ==========================================
if user_data['rola'] == "Instruktor":
    st.title("🚁 Panel Instruktora")

    wszyscy = supabase.table('konta').select('email, imie, zadania').eq('rola', 'Kursant').execute()
    kursanci = wszyscy.data

    if not kursanci:
        st.warning("Nie masz jeszcze żadnych zarejestrowanych kursantów!")
    else:
        opcje_kursantow = {k['email']: f"{k['imie']} ({k['email']})" for k in kursanci}
        
        col_select, col_video = st.columns([1, 1])
        with col_select:
            nowy_wybrany_email = st.selectbox("Wybierz kursanta:", options=list(opcje_kursantow.keys()), format_func=lambda x: opcje_kursantow[x])
            if 'poprzedni_kursant' not in st.session_state or st.session_state.poprzedni_kursant != nowy_wybrany_email:
                st.session_state.raport_draft = None
                st.session_state.poprzedni_kursant = nowy_wybrany_email
                
            wybrany_email = nowy_wybrany_email
            wybrany_kursant_dane = next(k for k in kursanci if k['email'] == wybrany_email)

        with col_video:
            video_url = st.text_input("🔗 Wklej link do wideo (Dysk/YouTube):")

        # Historia zadań
        with st.expander(f"📜 Historia zadań kursanta: {wybrany_kursant_dane['imie']}", expanded=False):
            if len(wybrany_kursant_dane['zadania']) == 0:
                st.info("Ten kursant nie ma jeszcze żadnych przypisanych zadań.")
            else:
                for i, zadanie in enumerate(reversed(wybrany_kursant_dane['zadania'])):
                    if isinstance(zadanie, dict): # Nowy, ustrukturyzowany format
                        st.markdown(f"**Raport #{len(wybrany_kursant_dane['zadania']) - i} | Data: {zadanie.get('data', 'Brak')} | Ocena: {zadanie.get('ocena', '?')}/10**")
                        st.markdown(zadanie.get('raport', ''))
                        if zadanie.get('wideo'):
                            st.markdown(f"[🎥 Obejrzyj Lot]({zadanie['wideo']})")
                    else: # Stary format (czysty string)
                        st.markdown(f"**Raport #{len(wybrany_kursant_dane['zadania']) - i}**")
                        st.markdown(zadanie)
                    st.divider()

        st.subheader("🔍 Przeprowadź Analizę Logów")
        uploaded_file = st.file_uploader("Wgraj log z drona (.bbl lub .csv)", type=['bbl', 'csv'])
        
        df = None
        statystyki_lotu = ""

        if uploaded_file:
            nazwa_pliku = uploaded_file.name.lower()
            
            if nazwa_pliku.endswith('.csv'):
                st.success("✅ Wgrano gotowy plik CSV.")
                df = pd.read_csv(uploaded_file)
                
            elif nazwa_pliku.endswith('.bbl'):
                with st.spinner("Dekodowanie czarnej skrzynki w tle..."):
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
                                df = pd.read_csv(csv_files[0])
                                st.success(f"✅ Pomyślnie rozkodowano plik BBL!")
                            else:
                                st.error("Dekoder zadziałał, ale plik był pusty.")
                        else:
                            st.error("Błąd serwera przy budowie dekodera.")
                    except Exception as e:
                        st.error(f"⚠️ Problem z plikiem BBL: {e}")

            if df is not None:
                rc_cols = [col for col in df.columns if 'rcCommand' in col]
                if len(rc_cols) >= 4:
                    roll_col, pitch_col, yaw_col, thr_col = rc_cols[0], rc_cols[1], rc_cols[2], rc_cols[3]
                    
                    avg_thr = df[thr_col].mean()
                    jerk_thr = df[thr_col].diff().abs().mean()
                    jerk_roll = df[roll_col].diff().abs().mean()
                    jerk_pitch = df[pitch_col].diff().abs().mean()
                    
                    # WIDOK PREMIUM: Kafelki statystyk
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    col_m1.metric("Średni Gaz", f"{avg_thr:.0f}")
                    col_m2.metric("Szarpanie Gazu", f"{jerk_thr:.2f}", delta="- idealnie < 10" if jerk_thr > 10 else "Dobra płynność", delta_color="inverse")
                    col_m3.metric("Szarpanie Roll", f"{jerk_roll:.2f}")
                    col_m4.metric("Szarpanie Pitch", f"{jerk_pitch:.2f}")

                    statystyki_lotu = f"- Gaz (Średni: {avg_thr:.1f}, Jerk: {jerk_thr:.2f})\n- Roll Jerk: {jerk_roll:.2f}\n- Pitch Jerk: {jerk_pitch:.2f}"

                    krok = max(1, len(df) // 5000)
                    plot_df = df.iloc[::krok].reset_index(drop=True)
                    
                    # WIDOK PREMIUM: Zakładki
                    tab_2d, tab_3d, tab_bat, tab_vid = st.tabs(["📈 Drążki (2D)", "🪐 Tunel Lotu (3D)", "🔋 Battery Sag", "🎥 Nagranie"])
                    
                    with tab_2d:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(y=plot_df[thr_col], mode='lines', name='Throttle', line=dict(color='orange', width=2)))
                        fig.add_trace(go.Scatter(y=plot_df[roll_col], mode='lines', name='Roll', line=dict(color='blue', width=1), opacity=0.7))
                        fig.add_trace(go.Scatter(y=plot_df[pitch_col], mode='lines', name='Pitch', line=dict(color='green', width=1), opacity=0.7))
                        fig.update_layout(template="plotly_dark", hovermode="x unified", height=350, margin=dict(l=0, r=0, t=30, b=0))
                        st.plotly_chart(fig, use_container_width=True)
                        
                    with tab_3d:
                        x_3d = plot_df[roll_col].cumsum() / 500  
                        y_3d = plot_df[pitch_col].cumsum() / 500 
                        z_3d = np.arange(len(plot_df)) 
                        kolor_gazu = plot_df[thr_col] 
                        fig3d = go.Figure(data=[go.Scatter3d(x=x_3d, y=y_3d, z=z_3d, mode='lines', line=dict(color=kolor_gazu, colorscale='Jet', width=5))])
                        fig3d.update_layout(template="plotly_dark", margin=dict(l=0, r=0, b=0, t=10), height=450)
                        st.plotly_chart(fig3d, use_container_width=True)

                    with tab_bat:
                        if 'vbatLatest' in df.columns:
                            st.info("⚡ Wykres pokazuje tzw. Battery Sag. Zobacz, jak napięcie baterii (niebieska linia) spada pod obciążeniem gazu (pomarańczowa przestrzeń).")
                            fig_bat = make_subplots(specs=[[{"secondary_y": True}]])
                            # Zwykle vbatLatest w blackboxie to np. 1600 dla 16.0V, dlatego dzielimy przez 100
                            napiecie = plot_df['vbatLatest'] / 100 
                            fig_bat.add_trace(go.Scatter(y=napiecie, name="Napięcie (V)", line=dict(color='cyan', width=2)), secondary_y=False)
                            fig_bat.add_trace(go.Scatter(y=plot_df[thr_col], name="Gaz", fill='tozeroy', line=dict(color='orange'), opacity=0.3), secondary_y=True)
                            fig_bat.update_layout(template="plotly_dark", height=350, margin=dict(l=0, r=0, t=30, b=0))
                            fig_bat.update_yaxes(title_text="Napięcie (V)", secondary_y=False)
                            fig_bat.update_yaxes(title_text="Gaz", secondary_y=True)
                            st.plotly_chart(fig_bat, use_container_width=True)
                        else:
                            st.warning("Twój log nie zawiera kolumny 'vbatLatest' z czujnika baterii.")

                    with tab_vid:
                        if video_url:
                            if "drive.google.com" in video_url:
                                embed_url = video_url.replace('/view', '/preview').split('?')[0]
                                st.components.v1.iframe(embed_url, height=400)
                            elif "youtube.com" in video_url or "youtu.be" in video_url:
                                st.video(video_url)
                            else:
                                st.markdown(f"👉 [Otwórz wideo]({video_url})")
                        else:
                            st.info("Nie dodano linku do wideo.")

                    # Zapisujemy parametry do meta, żeby użyć w bazie
                    st.session_state.raport_meta = {
                        "jerk_roll": float(jerk_roll),
                        "jerk_pitch": float(jerk_pitch),
                        "avg_thr": float(avg_thr)
                    }

        st.divider()
        st.subheader("🤖 Generowanie Wniosków AI")
        
        if st.button(f"🪄 Wygeneruj zaawansowany raport JSON", type="secondary"):
            if df is not None and statystyki_lotu != "":
                with st.spinner('Analiza inżynieryjna w toku...'):
                    try:
                        dostepne_modele = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        wybrany_model = next((m for m in dostepne_modele if 'flash' in m.lower()), dostepne_modele[0])
                        model = genai.GenerativeModel(wybrany_model)
                        
                        prompt = f"""
                        Jesteś instruktorem drona FPV. Analizujesz lot kursanta.
                        Dane: {statystyki_lotu}
                        
                        Zwróć odpowiedź WYŁĄCZNIE jako czysty kod JSON o dokładnie takiej strukturze:
                        {{
                            "ocena_plynnosci": (podaj ocenę lotu jako liczbę całkowitą od 1 do 10, gdzie 10 to wybitna płynność),
                            "diagnoza": "(Zwięzła, 2-zdaniowa diagnoza błędów kursanta wynikająca z jerk)",
                            "zadanie_tor": "(Jedno, konkretne polecenie treningowe na tor z bramkami)",
                            "zadanie_symulator": "(Jedno ćwiczenie do wykonania w symulatorze Liftoff/Velocidrone)"
                        }}
                        Nie dodawaj żadnego tekstu przed ani po JSON-ie!
                        """
                        response = model.generate_content(prompt)
                        
                        # Czyszczenie i parsowanie JSON
                        raw_json = response.text.replace("```json", "").replace("```", "").strip()
                        parsed_json = json.loads(raw_json)
                        
                        # Tworzymy piękny draft dla instruktora
                        draft = f"### Ocena Systemu: {parsed_json['ocena_plynnosci']}/10\n\n"
                        draft += f"**🩺 Diagnoza:**\n{parsed_json['diagnoza']}\n\n"
                        draft += f"**🏁 Zadanie na torze:**\n{parsed_json['zadanie_tor']}\n\n"
                        draft += f"**💻 Zadanie na symulator:**\n{parsed_json['zadanie_symulator']}"
                        
                        st.session_state.raport_draft = draft
                        st.session_state.raport_meta['ocena'] = parsed_json['ocena_plynnosci']
                        st.rerun() 
                    except Exception as e:
                        st.error(f"Błąd AI podczas generowania JSON: {e}")
            else:
                st.warning("Najpierw wgraj prawidłowe dane telemetryczne!")

        if st.session_state.raport_draft is not None:
            st.success("Wersja robocza utworzona. Edytuj lub zatwierdź.")
            
            ostateczny_tekst = st.text_area("Edytor raportu dla kursanta:", value=st.session_state.raport_draft, height=250)
            
            if st.button("🚀 Zatwierdź i Wyślij do Bazy Danych", type="primary"):
                with st.spinner("Zapisywanie logów do bazy..."):
                    # Nowoczesny, ustrukturyzowany zapis do bazy danych
                    nowy_wpis_db = {
                        "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "ocena": st.session_state.raport_meta.get('ocena', 0),
                        "jerk_roll": st.session_state.raport_meta.get('jerk_roll', 0),
                        "raport": ostateczny_tekst,
                        "wideo": video_url if 'video_url' in locals() else ""
                    }
                    
                    aktualne_zadania = wybrany_kursant_dane['zadania']
                    aktualne_zadania.append(nowy_wpis_db) # Dodajemy paczkę danych (Słownik), a nie zwykły tekst!
                    supabase.table('konta').update({'zadania': aktualne_zadania}).eq('email', wybrany_email).execute()
                    
                    st.session_state.raport_draft = None 
                    st.success(f"Profesjonalny raport zapisany! Profil {wybrany_kursant_dane['imie']} zaktualizowany.")
                    time.sleep(2)
                    st.rerun()

# ==========================================
# WIDOK 2: KURSANT (Z Grywalizacją!)
# ==========================================
elif user_data['rola'] == "Kursant":
    st.title(f"🎓 Twój Panel FPV")
    
    col_t1, col_t2 = st.columns(2)
    col_t1.info(f"🎟️ **Tokeny na analizę:** {user_data['tokeny']}")
    
    zadania = user_data['zadania']
    
    # SYSTEM ŚLEDZENIA POSTĘPÓW (Wykresy ewolucji ucznia)
    historia_jerk = [z['jerk_roll'] for z in zadania if isinstance(z, dict) and 'jerk_roll' in z]
    historia_ocen = [z['ocena'] for z in zadania if isinstance(z, dict) and 'ocena' in z]
    
    if len(historia_ocen) > 1:
        with st.container():
            st.subheader("📈 Twój Rozwój")
            fig_postepy = make_subplots(specs=[[{"secondary_y": True}]])
            fig_postepy.add_trace(go.Scatter(y=historia_ocen, mode='lines+markers', name='Ocena AI (1-10)', line=dict(color='gold', width=3)), secondary_y=False)
            fig_postepy.add_trace(go.Scatter(y=historia_jerk, mode='lines+markers', name='Szarpanie Roll', line=dict(color='cyan', dash='dot')), secondary_y=True)
            fig_postepy.update_layout(template="plotly_dark", height=300, margin=dict(l=0, r=0, t=10, b=0), hovermode="x unified")
            st.plotly_chart(fig_postepy, use_container_width=True)
    elif len(historia_ocen) == 1:
        col_t2.success(f"🌟 Twój pierwszy lot uzyskał ocenę: {historia_ocen[0]}/10! Lataj dalej, by zobaczyć swój wykres rozwoju.")
    
    st.divider()
    
    st.subheader("📋 Historia Twoich Treningów")
    if len(zadania) == 0:
        st.success("Obecnie nie masz przypisanych żadnych nowych zadań od Instruktora.")
    else:
        for i, zadanie in enumerate(reversed(zadania)):
            with st.expander(f"Zadanie Treningowe #{len(zadania) - i} " + (f"| Ocena: {zadanie.get('ocena')}/10" if isinstance(zadanie, dict) else ""), expanded=(i==0)):
                if isinstance(zadanie, dict):
                    st.caption(f"📅 Data raportu: {zadanie.get('data', 'Brak')}")
                    st.markdown(zadanie.get('raport', ''))
                    if zadanie.get('wideo'):
                        st.markdown(f"**[🎥 Obejrzyj nagranie ze swojego lotu]({zadanie['wideo']})**")
                else:
                    st.markdown(zadanie)
                
    st.divider()
    st.subheader("📤 Zużyj token i prześlij nowy lot do oceny")
    sim_file = st.file_uploader("Wgraj czarną skrzynkę (.bbl)", type=['bbl'])

    if sim_file:
        if st.button("Prześlij do Instruktora (1 Token)"):
            if user_data['tokeny'] > 0:
                nowe_tokeny = user_data['tokeny'] - 1
                supabase.table('konta').update({'tokeny': nowe_tokeny}).eq('email', st.session_state.zalogowany_uzytkownik).execute()
                st.success("Plik wgrany na serwer! Oczekuj na raport w panelu.")
                time.sleep(2)
                st.rerun()
            else:
                st.error("Brak tokenów! Wykup dodatkowe u instruktora.")
