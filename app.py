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
import re
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 1. KONFIGURACJA UI & CUSTOM CSS (BRANDING)
# ==========================================
st.set_page_config(page_title="FPV ACADEMY PRO", page_icon="🚁", layout="wide")

st.markdown("""
    <style>
    /* Globalny styl Carbon Tech */
    .stApp {
        background-color: #0e1117;
    }
    .stButton>button {
        border-radius: 10px;
        border: 1px solid #00ffcc;
        background-color: #1a1c23;
        color: #00ffcc;
        transition: all 0.3s ease;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #00ffcc;
        color: #000;
        box-shadow: 0px 0px 15px #00ffcc;
    }
    /* Styl kafelków Launchpad */
    .launch-card {
        padding: 30px;
        border-radius: 20px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
        transition: transform 0.3s ease;
    }
    .launch-card:hover {
        transform: translateY(-5px);
        border-color: #00ffcc;
    }
    /* Nagłówki */
    h1, h2, h3 {
        color: #00ffcc !important;
        font-family: 'Space Mono', monospace;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. BACKEND & AI ENGINE
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def get_ai_analysis(prompt):
    """Inteligentne pobieranie analizy z automatycznym wyborem modelu"""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        best_model = next((m for m in available_models if '1.5-flash' in m), available_models[0])
        model = genai.GenerativeModel(best_model)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f'{{"ocena": 0, "diagnoza": "AI Offline: {str(e)}", "zadanie": "Spróbuj za chwilę"}}'

@st.cache_resource
def get_decoder_path():
    extract_dir = "/tmp/bbt_source"
    executable = f"{extract_dir}/blackbox-tools-master/obj/blackbox_decode"
    if not os.path.exists(executable):
        os.makedirs(extract_dir, exist_ok=True)
        url = "https://github.com/betaflight/blackbox-tools/archive/refs/heads/master.zip"
        urllib.request.urlretrieve(url, "/tmp/b.zip")
        with zipfile.ZipFile("/tmp/b.zip", 'r') as z: z.extractall(extract_dir)
        subprocess.run(["make", "obj/blackbox_decode"], cwd=f"{extract_dir}/blackbox-tools-master", check=True)
    os.chmod(executable, 0o755)
    return executable

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# ==========================================
# 3. DASHBOARD ANALITYCZNY (PRO)
# ==========================================
def render_pro_dashboard(df, mode="drone", show_charts=True):
    # Detekcja osi
    try:
        thr = [c for c in df.columns if 'rcCommand[3]' in c or ('rcCommand' in c and '3' in c)][0]
        roll = [c for c in df.columns if 'rcCommand[0]' in c or ('rcCommand' in c and '0' in c)][0]
        pitch = [c for c in df.columns if 'rcCommand[1]' in c or ('rcCommand' in c and '1' in c)][0]
    except:
        st.error("Nieprawidłowy format pliku. Brak kolumn rcCommand.")
        return None

    j_r = df[roll].diff().abs().mean()
    j_p = df[pitch].diff().abs().mean()
    avg_t = df[thr].mean()
    
    # Grid statystyk
    c1, c2, c3 = st.columns(3)
    c1.metric("Średni Gaz", f"{avg_t:.0f}")
    c2.metric("Płynność Roll (Jerk)", f"{j_r:.2f}")
    c3.metric("Płynność Pitch (Jerk)", f"{j_p:.2f}")
    
    if show_charts:
        krok = max(1, len(df)//5000)
        pdf = df.iloc[::krok]
        
        tabs = st.tabs(["📈 Analiza 2D", "🪐 Trajektoria 3D", "🔋 Systemy"])
        with tabs[0]:
            f2d = go.Figure()
            f2d.add_trace(go.Scatter(y=pdf[thr], name="Throttle", line=dict(color='#ff9900', width=2)))
            f2d.add_trace(go.Scatter(y=pdf[roll], name="Roll", line=dict(color='#00ffcc', width=1), opacity=0.5))
            f2d.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(f2d, use_container_width=True)
        
        with tabs[1]:
            f3d = go.Figure(data=[go.Scatter3d(x=pdf[roll].cumsum()/500, y=pdf[pitch].cumsum()/500, z=np.arange(len(pdf)), 
                            mode='lines', line=dict(color=pdf[thr], colorscale='Viridis', width=5))])
            f3d.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(f3d, use_container_width=True)
            
        with tabs[2]:
            if mode == "drone":
                v_col = [c for c in df.columns if 'vbat' in c.lower()]
                if v_col:
                    st.write("⚡ **Battery Sag Analysis**")
                    f_bat = make_subplots(specs=[[{"secondary_y": True}]])
                    f_bat.add_trace(go.Scatter(y=pdf[v_col[0]]/100, name="Napięcie (V)", line=dict(color='#00ffff')), secondary_y=False)
                    f_bat.add_trace(go.Scatter(y=pdf[thr], name="Gaz", fill='tozeroy', opacity=0.1), secondary_y=True)
                    f_bat.update_layout(template="plotly_dark", height=300)
                    st.plotly_chart(f_bat, use_container_width=True)
            else:
                st.info("Dane z symulatora nie zawierają parametrów elektrycznych drona.")
    
    return {"j_r": j_r, "ocena": 0}

# ==========================================
# 4. SYSTEM SESJI I NAWIGACJI
# ==========================================
if 'zalogowany_uzytkownik' not in st.session_state:
    st.session_state.zalogowany_uzytkownik = None
if 'app_mode' not in st.session_state:
    st.session_state.app_mode = "menu" # menu, drone, sim

# --- LOGOWANIE ---
if st.session_state.zalogowany_uzytkownik is None:
    st.title("🚁 FPV ACADEMY PRO")
    t1, t2 = st.tabs(["🔐 Logowanie", "📝 Rejestracja"])
    with t1:
        em = st.text_input("Email")
        pw = st.text_input("Hasło", type="password")
        if st.button("WEJDŹ DO AKADEMII"):
            res = supabase.table('konta').select('*').eq('email', em).execute()
            if res.data and res.data[0]['haslo'] == pw:
                st.session_state.zalogowany_uzytkownik = em
                st.rerun()
    st.stop()

# Pobranie danych
user_data = supabase.table('konta').select('*').eq('email', st.session_state.zalogowany_uzytkownik).execute().data[0]

with st.sidebar:
    st.subheader(f"Zalogowany: {user_data['imie']}")
    if st.button("🏠 Menu Główne"):
        st.session_state.app_mode = "menu"
        st.rerun()
    if st.button("🚪 Wyloguj"):
        st.session_state.zalogowany_uzytkownik = None
        st.rerun()

# ==========================================
# 5. WIDOK: LAUNCHPAD (MENU WYBORU)
# ==========================================
if st.session_state.app_mode == "menu":
    st.title("🚀 Wybierz moduł szkoleniowy")
    st.write("Wybierz rodzaj danych, które chcesz dzisiaj przeanalizować.")
    
    col_drone, col_sim = st.columns(2)
    
    with col_drone:
        st.markdown('<div class="launch-card"><h2>🚁 REAL FLIGHT</h2><p>Analiza czarnej skrzynki z drona. Pełna telemetria, stan baterii i tunel 3D.</p></div>', unsafe_allow_html=True)
        if st.button("ANALIZUJ LOGI Z DRONA", use_container_width=True):
            st.session_state.app_mode = "drone"
            st.rerun()
            
    with col_sim:
        st.markdown('<div class="launch-card"><h2>🎮 SIMULATOR</h2><p>Analiza treningu z Liftoff / Velocidrone. Skupienie na płynności i technice drążków.</p></div>', unsafe_allow_html=True)
        if st.button("ANALIZUJ TRENING SIM", use_container_width=True):
            st.session_state.app_mode = "sim"
            st.rerun()

# ==========================================
# 6. WIDOK: ANALIZA (DRON LUB SIM)
# ==========================================
else:
    mode = st.session_state.app_mode
    label = "🚁 REAL FLIGHT" if mode == "drone" else "🎮 SIMULATOR"
    st.title(label)
    
    # --- INSTRUKCJE (POPOVER) ---
    with st.popover("❓ Jak przygotować plik? (Instrukcja)"):
        if mode == "drone":
            st.markdown("""
            **Krok po kroku (Blackbox):**
            1. Podłącz drona do Betaflight.
            2. W zakładce **Blackbox** wybierz 'Onboard Flash' lub 'SD Card'.
            3. Sprawdź czy `Blackbox logging rate` jest ustawiony na 1kHz lub 2kHz.
            4. Po locie pobierz plik `.bbl` i wgraj go tutaj.
            """)
        else:
            st.markdown("""
            **Krok po kroku (Simulator):**
            1. **Liftoff:** Logi są w folderze gry `Documents/Liftoff/Logs`.
            2. **Velocidrone:** Włącz 'Logging' w ustawieniach i wyeksportuj do `.csv`.
            3. Wgraj wygenerowany plik tutaj.
            """)

    # --- UPLOADER ---
    u_file = st.file_uploader(f"Wgraj log ({'BBL' if mode=='drone' else 'CSV'})", type=['bbl', 'csv'])
    
    if u_file:
        df = None
        if mode == "drone" and u_file.name.endswith('.bbl'):
            with st.spinner("Dekodowanie czarnej skrzynki..."):
                dec = get_decoder_path()
                with open("/tmp/temp.bbl", "wb") as f: f.write(u_file.getbuffer())
                subprocess.run([dec, "/tmp/temp.bbl"])
                csvs = sorted(glob.glob("/tmp/temp*.csv"))
                if csvs: df = pd.read_csv(csvs[0])
        else:
            df = pd.read_csv(u_file)

        if df is not None:
            # Wybór pakietu (Biznesowa logika tokenów)
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.info(f"Twoje tokeny: {user_data['tokeny']} 🎟️")
                pakiet = st.radio("Wybierz pakiet analizy:", ["📄 Basic (1 Token)", "💎 Premium (2 Tokeny)"])
                koszt = 1 if "Basic" in pakiet else 2

            if st.button(f"🚀 URUCHOM ANALIZĘ ({koszt} Tokeny)"):
                if user_data['tokeny'] >= koszt:
                    with st.spinner("AI przetwarza Twój lot..."):
                        stats = render_pro_dashboard(df, mode=mode, show_charts=(koszt==2))
                        
                        # AI Raport
                        prompt = f"Analiza FPV. Jerk: {stats['j_r']:.2f}. Podaj JSON: {{'ocena': 1-10, 'diagnoza': '...', 'zadanie': '...'}}"
                        ai_raw = get_ai_analysis(prompt)
                        try:
                            js = json.loads(ai_raw.replace("```json","").replace("```","").strip())
                            txt = f"### {'💎 PREMIUM' if koszt==2 else '📄 BASIC'} RAPORT\n\n**Ocena:** {js['ocena']}/10\n\n{js['diagnoza']}\n\n**Trening:** {js['zadanie']}"
                            
                            # Zapis do bazy
                            nowy = {"data": datetime.now().strftime("%Y-%m-%d"), "ocena": js['ocena'], "raport": txt, "premium": (koszt==2)}
                            zads = user_data['zadania']
                            zads.append(nowy)
                            supabase.table('konta').update({"zadania": zads, "tokeny": user_data['tokeny'] - koszt}).eq('email', user_data['email']).execute()
                            st.balloons()
                            st.success("Analiza zakończona! Sprawdź historię poniżej.")
                            time.sleep(1)
                            st.rerun()
                        except: st.error("AI błąd formatowania. Spróbuj ponownie.")
                else: st.error("Brak tokenów!")

    # --- HISTORIA ---
    st.divider()
    st.subheader("📋 Twoja Historia")
    for z in reversed(user_data['zadania']):
        if isinstance(z, dict):
            with st.expander(f"{z.get('data')} | Ocena: {z.get('ocena')}/10"):
                st.markdown(z.get('raport'))
