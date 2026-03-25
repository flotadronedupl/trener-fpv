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
# 1. STYLE & BRANDING (Carbon Tech UI)
# ==========================================
st.set_page_config(page_title="FPV ACADEMY PRO", page_icon="🚁", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1c23;
        border: 1px solid rgba(0, 255, 204, 0.2);
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
        color: white;
    }
    .stTabs [aria-selected="true"] { border-color: #00ffcc !important; box-shadow: 0 0 10px #00ffcc; }
    .launch-card {
        padding: 40px;
        border-radius: 25px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(0, 255, 204, 0.1);
        text-align: center;
        transition: all 0.3s ease;
        margin-bottom: 20px;
    }
    .launch-card:hover { border-color: #00ffcc; box-shadow: 0 0 20px rgba(0, 255, 204, 0.2); transform: translateY(-5px); }
    h1, h2, h3 { color: #00ffcc !important; font-family: 'Space Mono', monospace; }
    .stMetric { background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 15px; border-left: 5px solid #00ffcc; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CORE ENGINES (AI & DECODER)
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def get_ai_analysis(prompt):
    """Inteligentne wykrywanie modeli AI dla stabilności"""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        best_model = next((m for m in available_models if '1.5-flash' in m), None)
        if not best_model:
            best_model = next((m for m in available_models if 'pro' in m), available_models[0])
        model = genai.GenerativeModel(best_model)
        return model.generate_content(prompt).text
    except Exception as e:
        return f'{{"ocena": 0, "diagnoza": "AI Offline: {str(e)}", "zadanie": "Spróbuj później"}}'

@st.cache_resource
def get_decoder():
    path = "/tmp/bbt_source/blackbox-tools-master/obj/blackbox_decode"
    if not os.path.exists(path):
        os.makedirs("/tmp/bbt_source", exist_ok=True)
        urllib.request.urlretrieve("https://github.com/betaflight/blackbox-tools/archive/refs/heads/master.zip", "/tmp/b.zip")
        with zipfile.ZipFile("/tmp/b.zip", 'r') as z: z.extractall("/tmp/bbt_source")
        subprocess.run(["make", "obj/blackbox_decode"], cwd="/tmp/bbt_source/blackbox-tools-master", check=True)
    os.chmod(path, 0o755)
    return path

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# ==========================================
# 3. ANALYTICS DASHBOARD
# ==========================================
def render_pro_dashboard(df, mode="drone", show_charts=True):
    try:
        thr = [c for c in df.columns if 'rcCommand[3]' in c or ('rcCommand' in c and '3' in c)][0]
        roll = [c for c in df.columns if 'rcCommand[0]' in c or ('rcCommand' in c and '0' in c)][0]
        pitch = [c for c in df.columns if 'rcCommand[1]' in c or ('rcCommand' in c and '1' in c)][0]
    except:
        st.error("Błąd kolumn telemetrii. Upewnij się, że log zawiera dane rcCommand.")
        return None

    jr, jp = df[roll].diff().abs().mean(), df[pitch].diff().abs().mean()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Średni Gaz", f"{df[thr].mean():.0f}")
    m2.metric("Płynność Roll", f"{jr:.2f}")
    m3.metric("Płynność Pitch", f"{jp:.2f}")
    
    if show_charts:
        krok = max(1, len(df)//5000)
        pdf = df.iloc[::krok]
        t1, t2, t3 = st.tabs(["📈 Analiza 2D", "🪐 Trajektoria 3D", "🔋 Battery Health"])
        with t1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=pdf[thr], name="Gaz", line=dict(color='#ff9900')))
            fig.add_trace(go.Scatter(y=pdf[roll], name="Roll", opacity=0.4, line=dict(color='#00ffcc')))
            fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=20,b=0))
            st.plotly_chart(fig, use_container_width=True)
        with t2:
            fig3 = go.Figure(data=[go.Scatter3d(x=pdf[roll].cumsum()/500, y=pdf[pitch].cumsum()/500, z=np.arange(len(pdf)), 
                             mode='lines', line=dict(color=pdf[thr], colorscale='Jet', width=5))])
            fig3.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig3, use_container_width=True)
        with t3:
            v_col = [c for c in df.columns if 'vbat' in c.lower()]
            if v_col:
                f_bat = make_subplots(specs=[[{"secondary_y": True}]])
                f_bat.add_trace(go.Scatter(y=pdf[v_col[0]]/100, name="Bateria (V)", line=dict(color='#00ffff')), secondary_y=False)
                f_bat.add_trace(go.Scatter(y=pdf[thr], name="Gaz", fill='tozeroy', opacity=0.1), secondary_y=True)
                f_bat.update_layout(template="plotly_dark", height=300)
                st.plotly_chart(f_bat, use_container_width=True)
            else: st.info("Brak danych o baterii.")
    return {"jr": jr, "jp": jp}

# ==========================================
# 4. INITIALIZATION & AUTH
# ==========================================
# Inicjalizacja sesji (Zapobieganie KeyError)
if 'zalogowany_uzytkownik' not in st.session_state: st.session_state.zalogowany_uzytkownik = None
if 'app_mode' not in st.session_state: st.session_state.app_mode = "menu"
if 'draft' not in st.session_state: st.session_state.draft = None
if 'temp_jr' not in st.session_state: st.session_state.temp_jr = 0

if st.session_state.zalogowany_uzytkownik is None:
    st.title("🚁 FPV ACADEMY PRO")
    t1, t2 = st.tabs(["🔐 Logowanie", "📝 Rejestracja"])
    with t1:
        em = st.text_input("Email")
        pw = st.text_input("Hasło", type="password")
        if st.button("WEJDŹ DO PANELU"):
            res = supabase.table('konta').select('*').eq('email', em).execute()
            if res.data and res.data[0]['haslo'] == pw:
                st.session_state.zalogowany_uzytkownik = em
                st.rerun()
    st.stop()

# Pobranie danych zalogowanego
user_data = supabase.table('konta').select('*').eq('email', st.session_state.zalogowany_uzytkownik).execute().data[0]

# ==========================================
# 5. INSTRUKTOR VIEW (Pełna edycja i wysyłka)
# ==========================================
if user_data['rola'] == "Instruktor":
    st.title("👨‍🏫 Master Instructor Dashboard")
    
    with st.sidebar:
        st.write(f"Zalogowany: **{user_data['imie']}**")
        if st.button("🏠 Reset Widoku"): st.session_state.draft = None; st.rerun()
        if st.button("🚪 Wyloguj"): st.session_state.zalogowany_uzytkownik = None; st.rerun()

    kursanci = supabase.table('konta').select('*').eq('rola', 'Kursant').execute().data
    wybrany_em = st.selectbox("Wybierz Kursanta do odprawy:", [k['email'] for k in kursanci])
    k_data = next(k for k in kursanci if k['email'] == wybrany_em)

    with st.expander("📜 Ostatnie zadania tego kursanta"):
        for z in reversed(k_data['zadania'][-3:]):
            if isinstance(z, dict):
                st.write(f"**{z.get('data')} | Ocena: {z.get('ocena')}/10**")
                st.caption(z.get('raport')[:100] + "...")
            st.divider()

    col_l, col_v = st.columns(2)
    with col_l: log = st.file_uploader("Wgraj log lotu", type=['bbl', 'csv'])
    with col_v: v_url = st.text_input("Link do nagrania (YouTube/Drive):")

    df_active = None
    if log:
        if log.name.endswith('.csv'): df_active = pd.read_csv(log)
        else:
            with st.spinner("Dekodowanie czarnej skrzynki..."):
                dec = get_decoder()
                with open("/tmp/i.bbl", "wb") as f: f.write(log.getbuffer())
                subprocess.run([dec, "/tmp/i.bbl"])
                csvs = sorted(glob.glob("/tmp/i*.csv"))
                if csvs: df_active = pd.read_csv(csvs[0])

    if df_active is not None:
        stats = render_pro_dashboard(df_active)
        if st.button("🤖 GENERUJ PROPOZYCJĘ AI"):
            p = f"Jako instruktor FPV oceń lot. Roll Jerk: {stats['jr']:.2f}. Zwróć JSON: {{'ocena': 1-10, 'diagnoza': '...', 'zadanie': '...'}}"
            raw = get_ai_analysis(p)
            try:
                js = json.loads(raw.replace("```json","").replace("```","").strip())
                st.session_state.draft = f"### Ocena Systemu: {js['ocena']}/10\n\n**Odprawa Instruktorska:**\n{js['diagnoza']}\n\n**Zadanie:**\n{js['zadanie']}"
                st.session_state.temp_jr = stats['jr']
            except: st.error("AI błąd formatowania. Spróbuj jeszcze raz.")

    # Bezpieczne wyświetlanie edytora raportu
    if st.session_state.get('draft'):
        st.divider()
        st.subheader("📝 Edytuj raport przed wysłaniem")
        final_rep = st.text_area("Możesz zmienić treść lub ocenę ręcznie:", value=st.session_state.draft, height=250)
        
        if st.button("🚀 ZATWIERDŹ I WYŚLIJ DO KURSANTA", type="primary"):
            # Wyciąganie oceny z tekstu edytora
            match = re.search(r"Ocena Systemu: (\d+)/10", final_rep)
            score = int(match.group(1)) if match else 5
            
            nowy = {
                "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "ocena": score,
                "raport": final_rep,
                "wideo": v_url,
                "jerk": st.session_state.get('temp_jr', 0),
                "premium": True
            }
            
            aktualne = k_data['zadania']
            aktualne.append(nowy)
            supabase.table('konta').update({"zadania": aktualne}).eq('email', wybrany_em).execute()
            
            st.session_state.draft = None
            st.success(f"Raport wysłany do kursanta {k_data['imie']}!")
            time.sleep(1)
            st.rerun()

# ==========================================
# 6. KURSANT VIEW (LAUNCHPAD)
# ==========================================
else:
    if st.session_state.app_mode == "menu":
        st.title("🚀 Wybierz moduł treningowy")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="launch-card"><h2>🚁 REAL FLIGHT</h2><p>Analiza czarnej skrzynki. Bateria i tunel 3D.</p></div>', unsafe_allow_html=True)
            if st.button("ANALIZA LOGÓW DRONA", use_container_width=True): st.session_state.app_mode = "drone"; st.rerun()
        with c2:
            st.markdown('<div class="launch-card"><h2>🎮 SIMULATOR</h2><p>Trening płynności z Liftoff/Velocidrone.</p></div>', unsafe_allow_html=True)
            if st.button("ANALIZA TRENINGU SIM", use_container_width=True): st.session_state.app_mode = "sim"; st.rerun()
            
        st.divider()
        st.subheader("📈 Twoja Krzywa Rozwoju")
        zads = user_data.get('zadania', [])
        if len(zads) > 1:
            oceny = [z['ocena'] for z in zads if isinstance(z, dict) and 'ocena' in z]
            st.plotly_chart(go.Figure(go.Scatter(y=oceny, mode='lines+markers', line=dict(color='#00ffcc', width=3))).update_layout(template="plotly_dark", height=250, margin=dict(l=0,r=0,t=0,b=0)), use_container_width=True)

    else:
        st.header(f"📤 Nowa Analiza: {'Dron' if st.session_state.app_mode == 'drone' else 'Symulator'}")
        if st.button("⬅️ Powrót do menu"): st.session_state.app_mode = "menu"; st.rerun()
        
        with st.popover("❓ Pomoc"):
            st.write("Wgraj plik .bbl lub .csv, aby otrzymać natychmiastową informację zwrotną.")

        col_t1, col_t2 = st.columns([1, 2])
        with col_t1:
            st.metric("Twoje Tokeny 🎟️", user_data['tokeny'])
            pakiet = st.radio("Usługa:", ["📄 Basic (1 Token)", "💎 Premium (2 Tokeny)"])
            koszt = 1 if "Basic" in pakiet else 2
            
        with col_t2:
            u_log = st.file_uploader("Wgraj plik", type=['bbl', 'csv'])
            if u_log and st.button(f"Zatwierdź analizę ({koszt} Tokeny)"):
                if user_data['tokeny'] >= koszt:
                    with st.spinner("AI przetwarza Twój lot..."):
                        dec = get_decoder()
                        with open("/tmp/u.bbl", "wb") as f: f.write(u_log.getbuffer())
                        subprocess.run([dec, "/tmp/u.bbl"])
                        csvs = sorted(glob.glob("/tmp/u*.csv"))
                        if csvs:
                            df = pd.read_csv(csvs[0])
                            # Pokazujemy dashboard tylko w premium
                            stats = render_pro_dashboard(df, mode=st.session_state.app_mode, show_charts=(koszt == 2))
                            
                            raw_ai = get_ai_analysis(f"Analiza FPV. Jerk: {stats['jr']:.2f}. Podaj JSON z oceną 1-10 i diagnozą.")
                            try:
                                js = json.loads(raw_ai.replace("```json","").replace("```","").strip())
                                txt = f"### {pakiet} RAPORT\n\n**Ocena:** {js['ocena']}/10\n\n{js['diagnoza']}\n\n**Zadanie:** {js['zadanie']}"
                                
                                user_data['zadania'].append({
                                    "data": datetime.now().strftime("%Y-%m-%d"),
                                    "ocena": js['ocena'],
                                    "raport": txt,
                                    "premium": (koszt==2),
                                    "jerk": stats['jr']
                                })
                                
                                supabase.table('konta').update({
                                    "zadania": user_data['zadania'], 
                                    "tokeny": user_data['tokeny'] - koszt
                                }).eq('email', user_data['email']).execute()
                                
                                st.balloons()
                                time.sleep(1)
                                st.rerun()
                            except: st.error("AI błąd formatowania.")
                else: st.error("Brak tokenów!")

    st.subheader("📋 Historia Twoich Analiz")
    for z in reversed(user_data.get('zadania', [])):
        if isinstance(z, dict):
            tag = "💎" if z.get('premium') else "📄"
            with st.expander(f"{tag} Analiza {z.get('data')} | Ocena: {z.get('ocena')}/10"):
                st.markdown(z.get('raport'))
                if z.get('wideo'): st.video(z.get('wideo'))
