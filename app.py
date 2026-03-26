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
# 1. TACTICAL HUD DESIGN (CUSTOM CSS)
# ==========================================
st.set_page_config(page_title="FPV TACTICAL ACADEMY", page_icon="🪖", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

    /* Global Tactical Theme */
    .stApp {
        background-color: #05070a;
        color: #e0e0e0;
        font-family: 'JetBrains Mono', monospace;
    }

    /* Neon HUD Headers */
    h1, h2, h3 {
        color: #00ff66 !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        border-bottom: 1px solid #00ff6633;
        padding-bottom: 10px;
    }

    /* Tactical Cards (Launchpad) */
    .launch-card {
        padding: 30px;
        border-radius: 5px;
        background: #0a0e14;
        border: 1px solid #00ff6633;
        text-align: center;
        transition: all 0.3s ease;
    }
    .launch-card:hover {
        border-color: #00ff66;
        box-shadow: 0 0 20px #00ff6622;
        background: #0d131a;
    }

    /* Military Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 2px;
        border: 1px solid #00ff66;
        background-color: transparent;
        color: #00ff66;
        text-transform: uppercase;
        font-weight: bold;
        padding: 10px;
    }
    .stButton>button:hover {
        background-color: #00ff66;
        color: #000;
        box-shadow: 0 0 15px #00ff6666;
    }

    /* HUD Metrics */
    [data-testid="stMetric"] {
        background: #0a0e14;
        border: 1px solid #2d333b;
        padding: 15px;
        border-left: 4px solid #00ff66;
    }
    
    /* Popover Styling */
    .stPopover {
        border: 1px solid #00ff6633;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CORE SYSTEM (AI & DECODER)
# ==========================================
def init_ai():
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return True
    return False

def get_ai_intel(prompt):
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        best = next((m for m in models if '1.5-flash' in m), models[0])
        model = genai.GenerativeModel(best)
        return model.generate_content(prompt).text
    except Exception as e:
        return f'{{"ocena": 0, "diagnoza": "INTEL OFFLINE: {str(e)}", "zadanie": "RETRY MISSION"}}'

@st.cache_resource
def get_decoder():
    path = "/tmp/bbt_decode"
    if not os.path.exists(path):
        os.makedirs("/tmp/bbt_src", exist_ok=True)
        urllib.request.urlretrieve("https://github.com/betaflight/blackbox-tools/archive/refs/heads/master.zip", "/tmp/b.zip")
        with zipfile.ZipFile("/tmp/b.zip", 'r') as z: z.extractall("/tmp/bbt_src")
        subprocess.run(["make", "obj/blackbox_decode"], cwd="/tmp/bbt_src/blackbox-tools-master", check=True)
        shutil.copy("/tmp/bbt_src/blackbox-tools-master/obj/blackbox_decode", path)
    os.chmod(path, 0o755)
    return path

# Database Connection
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# ==========================================
# 3. TACTICAL DASHBOARD RENDERER
# ==========================================
def render_tactical_hud(df, mode="drone", show_charts=True):
    try:
        thr = [c for c in df.columns if 'rcCommand[3]' in c or ('rcCommand' in c and '3' in c)][0]
        roll = [c for c in df.columns if 'rcCommand[0]' in c or ('rcCommand' in c and '0' in c)][0]
        pitch = [c for c in df.columns if 'rcCommand[1]' in c or ('rcCommand' in c and '1' in c)][0]
    except:
        st.error("TELEMETRY ERROR: DATA MISMATCH")
        return None

    jr, jp = df[roll].diff().abs().mean(), df[pitch].diff().abs().mean()
    
    # HUD Metrics Row
    m1, m2, m3 = st.columns(3)
    m1.metric("AVG THROTTLE", f"{df[thr].mean():.0f}")
    m2.metric("ROLL SMOOTHNESS", f"{jr:.2f}")
    m3.metric("PITCH SMOOTHNESS", f"{jp:.2f}")

    if show_charts:
        krok = max(1, len(df)//5000)
        pdf = df.iloc[::krok]
        t1, t2, t3 = st.tabs(["📊 SENSOR DATA", "🪐 FLIGHT PATH 3D", "🔋 POWER SYSTEMS"])
        
        with t1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=pdf[thr], name="THR", line=dict(color='#ffaa00', width=2)))
            fig.add_trace(go.Scatter(y=pdf[roll], name="ROLL", opacity=0.4, line=dict(color='#00ff66')))
            fig.update_layout(template="plotly_dark", height=400, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
        with t2:
            fig3 = go.Figure(data=[go.Scatter3d(x=pdf[roll].cumsum()/500, y=pdf[pitch].cumsum()/500, z=np.arange(len(pdf)), 
                             mode='lines', line=dict(color=pdf[thr], colorscale='Electric', width=6))])
            fig3.update_layout(template="plotly_dark", height=500, scene=dict(bgcolor='#05070a'))
            st.plotly_chart(fig3, use_container_width=True)
            
        with t3:
            v_col = [c for c in df.columns if 'vbat' in c.lower()]
            if v_col and mode == "drone":
                f_bat = make_subplots(specs=[[{"secondary_y": True}]])
                f_bat.add_trace(go.Scatter(y=pdf[v_col[0]]/100, name="VOLTAGE (V)", line=dict(color='#00ffff')), secondary_y=False)
                f_bat.add_trace(go.Scatter(y=pdf[thr], name="LOAD", fill='tozeroy', opacity=0.1), secondary_y=True)
                f_bat.update_layout(template="plotly_dark", height=350, title="POWER DEGRADATION (SAG)")
                st.plotly_chart(f_bat, use_container_width=True)
            else: st.info("NO POWER DATA: SIMULATION MODE")
            
    return {"jr": jr, "jp": jp}

# ==========================================
# 4. SESSION & NAVIGATION
# ==========================================
if 'zalogowany_uzytkownik' not in st.session_state: st.session_state.zalogowany_uzytkownik = None
if 'app_mode' not in st.session_state: st.session_state.app_mode = "menu"
if 'draft' not in st.session_state: st.session_state.draft = None

# Authentication Gate
if st.session_state.zalogowany_uzytkownik is None:
    st.title("🪖 FPV TACTICAL ACADEMY")
    st.write("Wprowadź kody autoryzacyjne, aby wejść do systemu.")
    em = st.text_input("USER IDENTIFIER (EMAIL)")
    pw = st.text_input("ACCESS CODE (PASSWORD)", type="password")
    if st.button("AUTHORIZE"):
        res = supabase.table('konta').select('*').eq('email', em).execute()
        if res.data and res.data[0]['haslo'] == pw:
            st.session_state.zalogowany_uzytkownik = em
            st.rerun()
    st.stop()

user_data = supabase.table('konta').select('*').eq('email', st.session_state.zalogowany_uzytkownik).execute().data[0]

# ==========================================
# 5. INSTRUCTOR VIEW (COMMAND CENTER)
# ==========================================
if user_data['rola'] == "Instruktor":
    st.title("👨‍🚀 MISSION COMMAND CENTER")
    
    with st.sidebar:
        st.write(f"COMMANDER: **{user_data['imie']}**")
        if st.button("🏠 RESET VIEW"): st.session_state.draft = None; st.rerun()
        if st.button("🚪 LOGOUT"): st.session_state.zalogowany_uzytkownik = None; st.rerun()

    kursanci = supabase.table('konta').select('*').eq('rola', 'Kursant').execute().data
    wybrany_em = st.selectbox("Wybierz Kadeta do odprawy:", [k['email'] for k in kursanci])
    k_data = next(k for k in kursanci if k['email'] == wybrany_em)

    st.subheader(f"DEBRIEFING: {k_data['imie']}")
    
    col_l, col_v = st.columns(2)
    with col_l: 
        log = st.file_uploader("LOG TELEMETRYCZNY (.bbl/.csv)", type=['bbl', 'csv'])
    with col_v: 
        v_url = st.text_input("LINK DO REJESTRATORA (WIDEO):")

    df_active = None
    if log:
        if log.name.endswith('.csv'): df_active = pd.read_csv(log)
        else:
            with st.spinner("DEKODOWANIE DANYCH..."):
                dec = get_decoder()
                with open("/tmp/i.bbl", "wb") as f: f.write(log.getbuffer())
                subprocess.run([dec, "/tmp/i.bbl"])
                csvs = sorted(glob.glob("/tmp/i*.csv"))
                if csvs: df_active = pd.read_csv(csvs[0])

    if df_active is not None:
        stats = render_tactical_hud(df_active)
        if st.button("🤖 GENERUJ RAPORT AI"):
            if init_ai():
                p = f"Analiza FPV. Roll Jerk: {stats['jr']:.2f}. Zwróć JSON: {{'ocena': 1-10, 'diagnoza': '...', 'zadanie': '...'}}"
                raw = get_ai_intel(p)
                try:
                    js = json.loads(raw.replace("```json","").replace("```","").strip())
                    st.session_state.draft = f"### OCENA MISJI: {js['ocena']}/10\n\n**RAPORT TAKTYCZNY:**\n{js['diagnoza']}\n\n**ROZKAZ TRENINGOWY:**\n{js['zadanie']}"
                    st.session_state.temp_jr = stats['jr']
                except: st.error("AI INTEL ERROR: REFORMAT DATA")
            else: st.error("AI OFFLINE: CHECK KEY")

    if st.session_state.draft:
        st.divider()
        final_rep = st.text_area("✍️ EDYTUJ RAPORT PRZED WYSŁANIEM:", value=st.session_state.draft, height=250)
        if st.button("🚀 WYŚLIJ ODPRAWĘ DO KADETA", type="primary"):
            match = re.search(r"OCENA MISJI: (\d+)/10", final_rep)
            score = int(match.group(1)) if match else 5
            nowy = {
                "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "ocena": score,
                "raport": final_rep,
                "wideo": v_url,
                "jerk": st.session_state.get('temp_jr', 0),
                "premium": True
            }
            zads = k_data['zadania']
            zads.append(nowy)
            supabase.table('konta').update({"zadania": zads}).eq('email', wybrany_em).execute()
            st.session_state.draft = None
            st.success("RAPORT WYSŁANY DO BAZY.")
            time.sleep(1); st.rerun()

# ==========================================
# 6. KURSANT VIEW (TACTICAL LAUNCHPAD)
# ==========================================
else:
    if st.session_state.app_mode == "menu":
        st.title("🚀 TACTICAL LAUNCHPAD")
        st.write("Wybierz środowisko operacyjne do analizy.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="launch-card"><h2>🚁 REAL MISSION</h2><p>Analiza danych z czarnej skrzynki. Trajektoria 3D i stan sprzętu.</p></div>', unsafe_allow_html=True)
            if st.button("URUCHOM ANALIZĘ DRONA"): st.session_state.app_mode = "drone"; st.rerun()
        with c2:
            st.markdown('<div class="launch-card"><h2>🎮 VIRTUAL SIM</h2><p>Trening płynności drążków (Liftoff/Velocidrone).</p></div>', unsafe_allow_html=True)
            if st.button("URUCHOM ANALIZĘ SIM"): st.session_state.app_mode = "sim"; st.rerun()
            
        st.divider()
        st.subheader("📈 PROGRESJA OPERACYJNA")
        zads = user_data.get('zadania', [])
        if len(zads) > 1:
            oceny = [z['ocena'] for z in zads if isinstance(z, dict) and 'ocena' in z]
            fig_p = go.Figure(go.Scatter(y=oceny, mode='lines+markers', line=dict(color='#00ff66', width=4)))
            fig_p.update_layout(template="plotly_dark", height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_p, use_container_width=True)

    else:
        st.header(f"📤 TRANSFER DANYCH: {st.session_state.app_mode.upper()}")
        if st.button("⬅️ ABORT TO MENU"): st.session_state.app_mode = "menu"; st.rerun()
        
        # POPRAWKA: Instrukcja pod ikoną "?"
        with st.popover("❓ INTEL: Jak przygotować plik?"):
            if st.session_state.app_mode == "drone":
                st.markdown("**LOGI BLACKBOX:**\n1. Podłącz drona do Betaflight.\n2. W zakładce Blackbox pobierz plik .bbl z karty SD lub pamięci Flash.\n3. Wgraj go tutaj.")
            else:
                st.markdown("**LOGI SYMULATORA:**\n1. **Liftoff:** Logi CSV są w folderze `Documents/Liftoff/Logs`.\n2. **Velocidrone:** Włącz logging w ustawieniach i wyeksportuj do CSV.")

        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            st.metric("DOSTĘPNE TOKENY 🎟️", user_data['tokeny'])
            pakiet = st.radio("WYBIERZ POZIOM ANALIZY:", ["📄 BASIC (1 Token)", "💎 PREMIUM (2 Tokeny)"])
            koszt = 1 if "BASIC" in pakiet else 2
        with col_p2:
            u_log = st.file_uploader("WGRAJ PLIK LOGU", type=['bbl', 'csv'])
            if u_log and st.button(f"ROZPOCZNIJ ANALIZĘ ({koszt} TOKENY)"):
                if user_data['tokeny'] >= koszt:
                    with st.spinner("ANALIZA TAKTYCZNA..."):
                        dec = get_decoder()
                        with open("/tmp/u.bbl", "wb") as f: f.write(u_log.getbuffer())
                        subprocess.run([dec, "/tmp/u.bbl"])
                        csvs = sorted(glob.glob("/tmp/u*.csv"))
                        if csvs:
                            df = pd.read_csv(csvs[0])
                            stats = render_tactical_hud(df, show_charts=(koszt==2), mode=st.session_state.app_mode)
                            
                            if init_ai():
                                raw_ai = get_ai_intel(f"FPV Analysis. Jerk: {stats['jr']:.2f}. Return JSON.")
                                js = json.loads(raw_ai.replace("```json","").replace("```","").strip())
                                tag = "💎 PREMIUM" if koszt == 2 else "📄 BASIC"
                                final_text = f"### {tag} RAPORT AI\n\n**OCENA:** {js['ocena']}/10\n\n{js['diagnoza']}\n\n**ZADANIE:** {js['zadanie']}"
                                user_data['zadania'].append({"data": datetime.now().strftime("%Y-%m-%d"), "ocena": js['ocena'], "raport": final_text, "premium": (koszt==2)})
                                supabase.table('konta').update({"zadania": user_data['zadania'], "tokeny": user_data['tokeny']-koszt}).eq('email', user_data['email']).execute()
                                st.rerun()
                else: st.error("ACCESS DENIED: INSUFFICIENT TOKENS")

    st.subheader("📋 ARCHIWUM MISJI")
    for z in reversed(user_data.get('zadania', [])):
        if isinstance(z, dict):
            tag = "💎" if z.get('premium') else "📄"
            with st.expander(f"{tag} {z.get('data')} | SCORE: {z.get('ocena')}/10"):
                st.markdown(z.get('raport'))
                if z.get('wideo'): st.video(z.get('wideo'))
