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
# 1. GLOBAL UI & BRANDING (Carbon Design)
# ==========================================
st.set_page_config(page_title="FPV ACADEMY PRO", page_icon="🚁", layout="wide")

st.markdown("""
    <style>
    /* Industrial Dark Theme */
    .stApp { background-color: #0b0d11; color: #e0e0e0; }
    .stButton>button {
        border-radius: 4px;
        border: 1px solid #00ffcc;
        background-color: transparent;
        color: #00ffcc;
        letter-spacing: 1px;
        text-transform: uppercase;
        transition: all 0.4s;
    }
    .stButton>button:hover {
        background-color: #00ffcc;
        color: #000;
        box-shadow: 0 0 20px rgba(0, 255, 204, 0.4);
    }
    .launch-card {
        padding: 30px;
        border-radius: 12px;
        background: #161a21;
        border: 1px solid #2d333b;
        text-align: center;
        margin-bottom: 20px;
    }
    .launch-card:hover { border-color: #00ffcc; }
    .stMetric { background: #1c2128; padding: 20px; border-radius: 8px; border-bottom: 3px solid #00ffcc; }
    h1, h2, h3 { font-family: 'JetBrains Mono', monospace; color: #00ffcc !important; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. INITIALIZATION (Prevent KeyErrors)
# ==========================================
def init_session():
    keys = {
        'zalogowany_uzytkownik': None,
        'app_mode': 'menu',
        'draft': None,
        'temp_stats': {},
        'instruktor_wybrany_kursant': None
    }
    for key, val in keys.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()

# ==========================================
# 3. CORE ENGINES (AI & DECODER)
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def get_best_ai_model():
    """Automatycznie wykrywa najlepszy dostępny model na Twoim koncie Google"""
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        best = next((m for m in models if '1.5-flash' in m), models[0])
        return genai.GenerativeModel(best)
    except:
        st.error("Błąd połączenia z Google AI. Sprawdź klucz API.")
        return None

@st.cache_resource
def get_decoder():
    path = "/tmp/bbt_decode"
    if not os.path.exists(path):
        os.makedirs("/tmp/bbt_src", exist_ok=True)
        urllib.request.urlretrieve("https://github.com/betaflight/blackbox-tools/archive/refs/heads/master.zip", "/tmp/b.zip")
        with zipfile.ZipFile("/tmp/b.zip", 'r') as z: z.extractall("/tmp/bbt_src")
        subprocess.run(["make", "obj/blackbox_decode"], cwd="/tmp/bbt_src/blackbox-tools-master", check=True)
        shutil.copy(f"/tmp/bbt_src/blackbox-tools-master/obj/blackbox_decode", path)
    os.chmod(path, 0o755)
    return path

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# ==========================================
# 4. ANALYTICS ENGINE
# ==========================================
def run_analytics_dashboard(df, show_charts=True, mode="drone"):
    # Detekcja kolumn telemetrii
    try:
        thr = [c for c in df.columns if 'rcCommand[3]' in c or ('rcCommand' in c and '3' in c)][0]
        roll = [c for c in df.columns if 'rcCommand[0]' in c or ('rcCommand' in c and '0' in c)][0]
        pitch = [c for c in df.columns if 'rcCommand[1]' in c or ('rcCommand' in c and '1' in c)][0]
    except Exception:
        st.error("Nieprawidłowy format pliku telemetrii.")
        return None

    jr, jp = df[roll].diff().abs().mean(), df[pitch].diff().abs().mean()
    
    # Wyświetlanie Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Avg Throttle", f"{df[thr].mean():.0f}")
    c2.metric("Smoothness Roll (Jerk)", f"{jr:.2f}")
    c3.metric("Smoothness Pitch (Jerk)", f"{jp:.2f}")

    if show_charts:
        krok = max(1, len(df)//5000)
        pdf = df.iloc[::krok]
        t1, t2, t3 = st.tabs(["📉 2D Telemetry", "🪐 3D Flight Path", "🔋 Hardware Diagnostics"])
        
        with t1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=pdf[thr], name="Throttle", line=dict(color='#ff9900', width=2)))
            fig.add_trace(go.Scatter(y=pdf[roll], name="Roll", opacity=0.4, line=dict(color='#00ffcc')))
            fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)
            
        with t2:
            fig3 = go.Figure(data=[go.Scatter3d(x=pdf[roll].cumsum()/500, y=pdf[pitch].cumsum()/500, z=np.arange(len(pdf)), 
                             mode='lines', line=dict(color=pdf[thr], colorscale='Jet', width=6))])
            fig3.update_layout(template="plotly_dark", height=550, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig3, use_container_width=True)
            
        with t3:
            if mode == "drone":
                v_col = [c for c in df.columns if 'vbat' in c.lower()]
                if v_col:
                    f_bat = make_subplots(specs=[[{"secondary_y": True}]])
                    f_bat.add_trace(go.Scatter(y=pdf[v_col[0]]/100, name="VBat (V)", line=dict(color='#00ffff')), secondary_y=False)
                    f_bat.add_trace(go.Scatter(y=pdf[thr], name="Throttle", fill='tozeroy', opacity=0.1), secondary_y=True)
                    f_bat.update_layout(template="plotly_dark", height=350, title="Battery Voltage vs Load (Sag Analysis)")
                    st.plotly_chart(f_bat, use_container_width=True)
                else: st.info("Brak danych o napięciu baterii.")
            else: st.info("Tryb Symulatora: Brak danych sprzętowych.")
            
    return {"j_r": jr, "j_p": jp, "avg_t": df[thr].mean()}

# ==========================================
# 5. AUTHENTICATION SYSTEM
# ==========================================
if st.session_state.zalogowany_uzytkownik is None:
    st.title("🚁 FPV ACADEMY: COMMAND CENTER")
    t1, t2 = st.tabs(["🔐 Login", "📝 Register"])
    with t1:
        em = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.button("AUTHORIZE ACCESS"):
            res = supabase.table('konta').select('*').eq('email', em).execute()
            if res.data and res.data[0]['haslo'] == pw:
                st.session_state.zalogowany_uzytkownik = em
                st.rerun()
            else: st.error("Access Denied: Invalid Credentials")
    with t2:
        st.info("Nowy profil Kursanta")
        rem, rpw, rnm = st.text_input("New Email"), st.text_input("New Pass", type="password"), st.text_input("Name")
        if st.button("CREATE ACCOUNT"):
            supabase.table('konta').insert({'email': rem, 'haslo': rpw, 'imie': rnm, 'rola': 'Kursant', 'tokeny': 10, 'zadania': []}).execute()
            st.success("Account created successfully.")
    st.stop()

# Get User Data
user_data = supabase.table('konta').select('*').eq('email', st.session_state.zalogowany_uzytkownik).execute().data[0]

# ==========================================
# 6. INSTRUCTOR DASHBOARD (Master View)
# ==========================================
if user_data['rola'] == "Instruktor":
    st.title("👨‍🏫 STRATEGIC INSTRUCTOR PANEL")
    
    with st.sidebar:
        st.image("https://images.unsplash.com/photo-1508614589041-895b88991e3e?q=80&w=200", caption="Master Controller")
        if st.button("🏠 Home / Reset"): st.session_state.draft = None; st.rerun()
        if st.button("🚪 Logout"): st.session_state.zalogowany_uzytkownik = None; st.rerun()

    # Kursant Selection
    kursanci = supabase.table('konta').select('*').eq('rola', 'Kursant').execute().data
    wybrany_em = st.selectbox("Wybierz Kursanta do odprawy:", [k['email'] for k in kursanci])
    k_data = next(k for k in kursanci if k['email'] == wybrany_em)

    with st.expander("📜 Historia Lotów Kursanta"):
        for z in reversed(k_data['zadania']):
            if isinstance(z, dict):
                st.write(f"**{z.get('data')} | Score: {z.get('ocena')}/10**")
                st.caption(z.get('raport'))
                st.divider()

    c1, c2 = st.columns(2)
    with c1: log_file = st.file_uploader("Wgraj Log Lotu (.bbl/.csv)", type=['bbl', 'csv'])
    with c2: vid_link = st.text_input("Link do nagrania (YouTube/Drive):")

    df_active = None
    if log_file:
        if log_file.name.endswith('.csv'): df_active = pd.read_csv(log_file)
        else:
            with st.spinner("Decoding Blackbox Data..."):
                dec = get_decoder()
                with open("/tmp/active.bbl", "wb") as f: f.write(log_file.getbuffer())
                subprocess.run([dec, "/tmp/active.bbl"])
                csvs = sorted(glob.glob("/tmp/active*.csv"))
                if csvs: df_active = pd.read_csv(csvs[0])

    if df_active is not None:
        stats = run_analytics_dashboard(df_active)
        
        if st.button("🤖 GENERUJ DRAFT ANALIZY AI"):
            model = get_best_ai_model()
            prompt = f"Expert FPV Instructor analysis. Roll Jerk: {stats['j_r']:.2f}, Pitch Jerk: {stats['j_p']:.2f}. Return JSON: {{'ocena': 1-10, 'diagnoza': '...', 'zadanie': '...'}}"
            raw_ai = model.generate_content(prompt).text
            try:
                js = json.loads(raw_ai.replace("```json","").replace("```","").strip())
                st.session_state.draft = f"### Ocena Systemu: {js['ocena']}/10\n\n**Analiza Inżynierska:**\n{js['diagnoza']}\n\n**Zadanie Treningowe:**\n{js['zadanie']}"
                st.session_state.temp_stats = stats
            except: st.error("AI Error: Niestandardowy format danych. Spróbuj ponownie.")

    if st.session_state.draft:
        st.divider()
        final_rep = st.text_area("✍️ Edytuj raport przed wysłaniem:", value=st.session_state.draft, height=250)
        if st.button("🚀 ZATWIERDŹ I WYŚLIJ RAPORT PREMIUM", type="primary"):
            score = int(re.search(r"Ocena Systemu: (\d+)/10", final_rep).group(1)) if "Ocena Systemu" in final_rep else 5
            nowy_raport = {
                "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "ocena": score,
                "raport": final_rep,
                "wideo": vid_link,
                "jerk": st.session_state.temp_stats.get('j_r', 0),
                "premium": True
            }
            aktualne = k_data['zadania']
            aktualne.append(nowy_raport)
            supabase.table('konta').update({"zadania": aktualne}).eq('email', wybrany_em).execute()
            st.session_state.draft = None
            st.success(f"Raport przesłany do {k_data['imie']}!")
            time.sleep(1); st.rerun()

# ==========================================
# 7. STUDENT VIEW (Launchpad & Analytics)
# ==========================================
else:
    if st.session_state.app_mode == "menu":
        st.title("🚀 FPV TRAINING LAUNCHPAD")
        col_d, col_s = st.columns(2)
        with col_d:
            st.markdown('<div class="launch-card"><h2>🚁 REAL DRONE</h2><p>Analiza danych z czarnej skrzynki. Trajektoria 3D i stan sprzętu.</p></div>', unsafe_allow_html=True)
            if st.button("ROZPOCZNIJ ANALIZĘ DRONA", use_container_width=True): 
                st.session_state.app_mode = "drone"; st.rerun()
        with col_s:
            st.markdown('<div class="launch-card"><h2>🎮 SIMULATOR</h2><p>Trening płynności drążków (Liftoff/Velocidrone). Statystyki progresu.</p></div>', unsafe_allow_html=True)
            if st.button("ROZPOCZNIJ ANALIZĘ SIM", use_container_width=True): 
                st.session_state.app_mode = "sim"; st.rerun()
        
        st.divider()
        st.subheader("📈 Twoja Krzywa Rozwoju (Performance)")
        zads = user_data.get('zadania', [])
        if len(zads) > 1:
            oceny = [z['ocena'] for z in zads if isinstance(z, dict) and 'ocena' in z]
            fig_p = go.Figure(go.Scatter(y=oceny, mode='lines+markers', line=dict(color='#00ffcc', width=4)))
            fig_p.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig_p, use_container_width=True)

    else:
        st.header(f"📤 Nowa Analiza: {st.session_state.app_mode.upper()}")
        if st.button("⬅️ Powrót do Menu"): st.session_state.app_mode = "menu"; st.rerun()
        
        with st.popover("❓ Jak przygotować dane?"):
            st.write("Wgraj plik .bbl (Dron) lub .csv (Sim). System automatycznie rozpozna parametry.")

        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            st.metric("Dostępne Tokeny 🎟️", user_data['tokeny'])
            pakiet = st.radio("Wybierz Poziom Analizy:", ["📄 Basic (1 Token) - Tylko tekst AI", "💎 Premium (2 Tokeny) - Pełny Dashboard 3D"])
            koszt = 1 if "Basic" in pakiet else 2
        with col_p2:
            u_log = st.file_uploader("Wgraj Log", type=['bbl', 'csv'])
            if u_log and st.button(f"Zatwierdź i zapłać {koszt} Tokeny"):
                if user_data['tokeny'] >= koszt:
                    with st.spinner("Processing Mission Data..."):
                        dec = get_decoder()
                        with open("/tmp/user.bbl", "wb") as f: f.write(u_log.getbuffer())
                        subprocess.run([dec, "/tmp/user.bbl"])
                        csvs = sorted(glob.glob("/tmp/user*.csv"))
                        if csvs:
                            df = pd.read_csv(csvs[0])
                            # Dashboard tylko w Premium
                            stats = run_analytics_dashboard(df, show_charts=(koszt==2), mode=st.session_state.app_mode)
                            
                            model = get_best_ai_model()
                            raw_ai = model.generate_content(f"FPV Pilot Analysis. Jerk: {stats['j_r']:.2f}. Return JSON with 'ocena', 'diagnoza', 'zadanie'.").text
                            js = json.loads(raw_ai.replace("```json","").replace("```","").strip())
                            
                            tag = "💎 PREMIUM" if koszt == 2 else "📄 BASIC"
                            final_text = f"### {tag} RAPORT\n\n**Ocena:** {js['ocena']}/10\n\n{js['diagnoza']}\n\n**Zadanie:** {js['zadanie']}"
                            
                            user_data['zadania'].append({"data": datetime.now().strftime("%Y-%m-%d"), "ocena": js['ocena'], "raport": final_text, "premium": (koszt==2)})
                            supabase.table('konta').update({"zadania": user_data['zadania'], "tokeny": user_data['tokeny']-koszt}).eq('email', user_data['email']).execute()
                            st.balloons(); time.sleep(1); st.rerun()
                else: st.error("Błąd: Niewystarczająca liczba tokenów.")

    st.subheader("📋 Archiwum Twoich Lotów")
    for z in reversed(user_data.get('zadania', [])):
        if isinstance(z, dict):
            tag = "💎" if z.get('premium') else "📄"
            with st.expander(f"{tag} Analiza {z.get('data')} | Score: {z.get('ocena')}/10"):
                st.markdown(z.get('raport'))
                if z.get('wideo'): st.video(z.get('wideo'))
