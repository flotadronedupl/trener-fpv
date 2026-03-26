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
# 1. INICJALIZACJA SESJI I ZMIENNYCH
# ==========================================
st.set_page_config(page_title="FCIS | FPV Command Hub", page_icon="🪖", layout="wide")

def init_session():
    defaults = {
        'zalogowany': None, 'rola': None, 'app_mode': 'menu', 
        'mission_type': 'Military/Recon', 'theme_color': '#00ff66',
        'draft': None, 'temp_stats': {}, 'skill_level': 'Pilot'
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

init_session()

# ==========================================
# 2. DYNAMICZNY SILNIK WIZUALNY (CSS)
# ==========================================
primary_color = st.session_state.theme_color

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&display=swap');
    
    .stApp {{ background-color: #05070a; color: #e0e0e0; font-family: 'JetBrains Mono', monospace; }}
    
    /* Neomorphism & Glassmorphism */
    .stMetric, .stExpander, .launch-card, .stAlert, div[data-testid="stPopoverBody"] {{
        background: rgba(10, 14, 20, 0.85) !important;
        border: 1px solid {primary_color}33 !important;
        border-radius: 6px !important;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }}
    
    h1, h2, h3 {{ color: {primary_color} !important; text-transform: uppercase; letter-spacing: 2px; font-weight: 800; }}
    
    /* Tactical Buttons */
    .stButton>button {{
        border: 1px solid {primary_color}; background: transparent; color: {primary_color};
        text-transform: uppercase; font-weight: 700; width: 100%;
        transition: 0.3s; letter-spacing: 1.5px;
    }}
    .stButton>button:hover {{ 
        background: {primary_color}; color: #000; 
        box-shadow: 0 0 25px {primary_color}88; 
    }}
    
    /* Sidebar */
    section[data-testid="stSidebar"] {{ background-color: #07090f !important; border-right: 1px solid {primary_color}33; }}
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {{ width: 6px; }}
    ::-webkit-scrollbar-track {{ background: #05070a; }}
    ::-webkit-scrollbar-thumb {{ background: {primary_color}; }}
    
    .leaderboard-row {{ display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #333; }}
    .rank-1 {{ color: #ffd700; font-weight: bold; text-shadow: 0 0 10px #ffd700; }}
    .rank-2 {{ color: #c0c0c0; font-weight: bold; }}
    .rank-3 {{ color: #cd7f32; font-weight: bold; }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. CORE ENGINES (AI & DECODER & DB)
# ==========================================
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def init_ai():
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return True
    return False

def get_ai_intel(prompt):
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        best = next((m for m in models if '1.5-flash' in m), models[0])
        return genai.GenerativeModel(best).generate_content(prompt).text
    except Exception as e:
        return f'{{"ocena": 0, "diagnoza": "AI COMMS LINK LOST", "zadanie": "RECALIBRATE"}}'

@st.cache_resource
def get_decoder():
    path = "/tmp/fcis_decode"
    if not os.path.exists(path):
        os.makedirs("/tmp/bbt_src", exist_ok=True)
        urllib.request.urlretrieve("https://github.com/betaflight/blackbox-tools/archive/refs/heads/master.zip", "/tmp/b.zip")
        with zipfile.ZipFile("/tmp/b.zip", 'r') as z: z.extractall("/tmp/bbt_src")
        subprocess.run(["make", "obj/blackbox_decode"], cwd="/tmp/bbt_src/blackbox-tools-master", check=True)
        shutil.copy("/tmp/bbt_src/blackbox-tools-master/obj/blackbox_decode", path)
    os.chmod(path, 0o755)
    return path

# ==========================================
# 4. ADVANCED TACTICAL HUD (ANALYTICS)
# ==========================================
def render_tactical_hud(df, mode="Real", mission="Military", premium=False):
    color = st.session_state.theme_color
    try:
        thr = [c for c in df.columns if 'rcCommand[3]' in c or ('rcCommand' in c and '3' in c)][0]
        roll = [c for c in df.columns if 'rcCommand[0]' in c or ('rcCommand' in c and '0' in c)][0]
        pitch = [c for c in df.columns if 'rcCommand[1]' in c or ('rcCommand' in c and '1' in c)][0]
    except:
        st.error("SYSTEM ERROR: UNRECOGNIZED TELEMETRY FORMAT")
        return None

    jr, jp = df[roll].diff().abs().mean(), df[pitch].diff().abs().mean()
    avg_t = df[thr].mean()
    
    # Hardware Health Heuristic (Symulacja na podstawie wibracji drążków)
    health_score = max(0, min(100, 100 - ((jr + jp) * 12)))
    health_status = "OPTIMAL" if health_score > 80 else "WARNING" if health_score > 50 else "CRITICAL"
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("AVG THROTTLE", f"{avg_t:.0f}")
    m2.metric("FLIGHT SMOOTHNESS", f"{10 - (jr+jp):.1f}/10")
    m3.metric("ROLL JERK", f"{jr:.2f}")
    m4.metric("HARDWARE HEALTH", f"{health_score:.0f}%", health_status)

    if premium:
        krok = max(1, len(df)//5000)
        pdf = df.iloc[::krok]
        t1, t2, t3, t4 = st.tabs(["📊 2D TELEMETRY", "🪐 3D TRAJECTORY", "🔋 DIAGNOSTICS", "📱 VIRAL HUD"])
        
        with t1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=pdf[thr], name="THR", line=dict(color='#ffaa00', width=2)))
            fig.add_trace(go.Scatter(y=pdf[roll], name="ROLL", line=dict(color=color), opacity=0.5))
            fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig, use_container_width=True)
            
        with t2:
            fig3 = go.Figure(data=[go.Scatter3d(x=pdf[roll].cumsum()/500, y=pdf[pitch].cumsum()/500, z=np.arange(len(pdf)), 
                                mode='lines', line=dict(color=pdf[thr], colorscale='Electric', width=6))])
            fig3.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(fig3, use_container_width=True)
            
        with t3:
            v_col = [c for c in df.columns if 'vbat' in c.lower()]
            if v_col and mode == "Real":
                f_bat = make_subplots(specs=[[{"secondary_y": True}]])
                f_bat.add_trace(go.Scatter(y=pdf[v_col[0]]/100, name="VBAT (V)", line=dict(color='#00ffff')), secondary_y=False)
                f_bat.add_trace(go.Scatter(y=pdf[thr], name="LOAD", fill='tozeroy', opacity=0.15, line=dict(color='#ffaa00')), secondary_y=True)
                f_bat.update_layout(template="plotly_dark", height=350, title=f"BATTERY SAG ANALYSIS")
                st.plotly_chart(f_bat, use_container_width=True)
            else: st.info("HARDWARE TELEMETRY UNAVAILABLE IN THIS DATASET")
            
        with t4:
            st.markdown(f"**SOCIAL MEDIA 9:16 HUD GENERATOR**")
            st.write("Podgląd nakładki na drążki. Idealne do publikacji na TikTok/Reels.")
            f_soc = go.Figure()
            f_soc.add_trace(go.Scatter(x=pdf[roll].tail(150), y=pdf[pitch].tail(150), mode='lines+markers', line=dict(color=color, width=4)))
            f_soc.update_layout(template="plotly_dark", width=320, height=568, xaxis=dict(range=[-500,500], showgrid=False), yaxis=dict(range=[-500,500], showgrid=False), title="STICK TRACE")
            st.plotly_chart(f_soc)
            
    return {"jr": jr, "jp": jp, "health": health_score}

# ==========================================
# 5. AUTHENTICATION & GATEWAY
# ==========================================
if st.session_state.zalogowany is None:
    st.title("🪖 FCIS | CENTRAL GATEWAY")
    t1, t2 = st.tabs(["🔐 AUTHORIZE", "📝 ENLIST (NEW CADET)"])
    with t1:
        em = st.text_input("OPERATOR ID (EMAIL)")
        pw = st.text_input("CLEARANCE CODE", type="password")
        if st.button("INITIATE UPLINK"):
            res = supabase.table('konta').select('*').eq('email', em).execute()
            if res.data and res.data[0]['haslo'] == pw:
                st.session_state.zalogowany = em
                st.session_state.rola = res.data[0]['rola']
                st.rerun()
            else: st.error("ACCESS DENIED.")
    with t2:
        rem, rpw, rnm = st.text_input("NEW ID"), st.text_input("NEW CODE", type="password"), st.text_input("CALLSIGN / NAME")
        r_level = st.select_slider("CURRENT SKILL LEVEL", options=["Cadet", "Pilot", "Veteran", "Elite"])
        if st.button("REGISTER PROFILE"):
            supabase.table('konta').insert({'email': rem, 'haslo': rpw, 'imie': rnm, 'rola': 'Kursant', 'tokeny': 10, 'level': r_level, 'zadania': []}).execute()
            st.success("PROFILE CREATED. YOU MAY LOGIN.")
    st.stop()

# Load User Data
user_data = supabase.table('konta').select('*').eq('email', st.session_state.zalogowany).execute().data[0]

# ==========================================
# 6. INSTRUCTOR COMMAND CENTER
# ==========================================
if user_data['rola'] == "Instruktor":
    st.title("👨‍🚀 TACTICAL COMMAND OVERSEER")
    
    with st.sidebar:
        st.write(f"COMMANDER: **{user_data['imie']}**")
        if st.button("🏠 RESET CONSOLE"): st.session_state.draft = None; st.rerun()
        if st.button("🚪 SEVER CONNECTION"): st.session_state.zalogowany = None; st.rerun()

    wszyscy = supabase.table('konta').select('*').eq('rola', 'Kursant').execute().data
    if not wszyscy: 
        st.warning("NO CADETS IN DATABASE.")
        st.stop()
    
    wybrany_em = st.selectbox("SELECT CADET TO DEBRIEF:", [k['email'] for k in wszyscy])
    k_data = next(k for k in wszyscy if k['email'] == wybrany_em)

    st.sidebar.divider()
    st.sidebar.write(f"**TARGET:** {k_data['imie']}")
    st.sidebar.write(f"**RANK:** {k_data.get('level', 'Unknown')}")
    m_type = st.sidebar.selectbox("SET MISSION TYPE:", ["Military/Recon", "Pro-Racing", "Freestyle"])
    
    st.session_state.theme_color = '#00ff66' if 'Military' in m_type else '#ff4400' if 'Racing' in m_type else '#00ccff'

    # WSPARCIE DLA STARYCH DANYCH (LEGACY SAFEGUARD)
    with st.expander(f"📜 DOSSIER: {k_data['imie']}", expanded=False):
        for z in reversed(k_data.get('zadania', [])):
            if isinstance(z, dict):
                st.write(f"**{z.get('data')} | SCORE: {z.get('ocena')}/10 | {z.get('type','N/A')}**")
                st.caption(z.get('raport')[:150] + "...")
            else:
                st.write("**ARCHIVE LOG (LEGACY)**")
                st.caption(str(z)[:100] + "...")
            st.divider()

    c1, c2 = st.columns(2)
    with c1: log = st.file_uploader("UPLOAD RAW TELEMETRY", type=['bbl', 'csv'])
    with c2: v_url = st.text_input("VIDEO RECON LINK (YT/Drive):")

    df_active = None
    if log:
        if log.name.endswith('.csv'): df_active = pd.read_csv(log)
        else:
            with st.spinner("DECRYPTING BLACKBOX..."):
                dec = get_decoder()
                with open("/tmp/i.bbl", "wb") as f: f.write(log.getbuffer())
                subprocess.run([dec, "/tmp/i.bbl"])
                csvs = sorted(glob.glob("/tmp/i*.csv"))
                if csvs: df_active = pd.read_csv(csvs[0])

    if df_active is not None:
        stats = render_tactical_hud(df_active, mode="Real", mission=m_type, premium=True)
        if st.button("🤖 GENERATE AI TACTICAL ASSESSMENT"):
            if init_ai():
                p = f"""System FPV. Operator: {k_data.get('level', 'Pilot')}. Misja: {m_type}. 
                Roll Jerk: {stats['jr']:.2f}, Pitch: {stats['jp']:.2f}, Health: {stats['health']}%.
                Zwróć TYLKO czysty format JSON bez dodatkowego tekstu ani markdown: {{"ocena": 1-10, "diagnoza": "Krótko wojskowym żargonem", "zadanie": "Konkret"}}"""
                raw = get_ai_intel(p)
                try:
                    js = json.loads(raw.replace("```json","").replace("```","").strip())
                    st.session_state.draft = f"### MISSION RATING: {js['ocena']}/10 [{m_type}]\n\n**TACTICAL DIAGNOSIS:**\n{js['diagnoza']}\n\n**NEW DIRECTIVE:**\n{js['zadanie']}"
                    st.session_state.temp_stats = stats
                except: st.error("AI DATA CORRUPTION. PROSZĘ SPRÓBOWAĆ PONOWNIE.")

    if st.session_state.draft:
        st.divider()
        final_rep = st.text_area("✍️ COMMANDER OVERRIDE (EDIT):", value=st.session_state.draft, height=250)
        if st.button("🚀 DEPLOY TO CADET", type="primary"):
            match = re.search(r"MISSION RATING: (\d+)/10", final_rep)
            score = int(match.group(1)) if match else 5
            nowy = {
                "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "ocena": score, "raport": final_rep, "wideo": v_url, 
                "type": m_type, "premium": True, "health": st.session_state.temp_stats.get('health', 100)
            }
            zads = k_data.get('zadania', [])
            zads.append(nowy)
            supabase.table('konta').update({"zadania": zads}).eq('email', wybrany_em).execute()
            st.session_state.draft = None
            st.success("MISSION DEPLOYED SUCCESSFULLY.")
            time.sleep(1); st.rerun()

# ==========================================
# 7. CADET LAUNCHPAD & MISSIONS
# ==========================================
else:
    with st.sidebar:
        st.write(f"OPERATOR: **{user_data['imie']}**")
        st.write(f"RANK: **{user_data.get('level','Cadet')}**")
        st.metric("TOKENS", user_data.get('tokeny', 0))
        if st.button("🚪 DISCONNECT"): st.session_state.zalogowany = None; st.rerun()

    if st.session_state.app_mode == "menu":
        st.session_state.theme_color = '#00ff66' 
        st.title("🚀 MISSION LAUNCHPAD")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="launch-card"><h2>🚁 REAL FLIGHT</h2><p>Militarny, Racing, Freestyle. Blackbox Intel.</p></div>', unsafe_allow_html=True)
            col_m, col_r, col_f = st.columns(3)
            if col_m.button("MILITARY"): st.session_state.mission_type="Military/Recon"; st.session_state.theme_color="#00ff66"; st.session_state.app_mode="drone"; st.rerun()
            if col_r.button("RACING"): st.session_state.mission_type="Pro-Racing"; st.session_state.theme_color="#ff4400"; st.session_state.app_mode="drone"; st.rerun()
            if col_f.button("FREESTYLE"): st.session_state.mission_type="Freestyle"; st.session_state.theme_color="#00ccff"; st.session_state.app_mode="drone"; st.rerun()
        with c2:
            st.markdown('<div class="launch-card"><h2>🎮 VIRTUAL SIM</h2><p>Trening wirtualny. Liftoff & Velocidrone CSV.</p></div>', unsafe_allow_html=True)
            if st.button("ENTER SIMULATOR", use_container_width=True): 
                st.session_state.mission_type="Simulator"; st.session_state.theme_color="#b026ff"; st.session_state.app_mode="sim"; st.rerun()
        
        # GLOBAL LEADERBOARD "TOP GUN" (LEGACY SAFEGUARD)
        st.divider()
        st.subheader("🏆 GLOBAL TOP GUN LEADERBOARD")
        wszyscy = supabase.table('konta').select('imie, zadania').eq('rola', 'Kursant').execute().data
        ranking = []
        for k in wszyscy:
            zads = k.get('zadania', [])
            valid_zads = [z for z in zads if isinstance(z, dict) and 'ocena' in z]
            if len(valid_zads) > 0:
                avg_score = sum([z['ocena'] for z in valid_zads]) / len(valid_zads)
                ranking.append({"Name": k['imie'], "Avg Score": round(avg_score, 1), "Missions": len(valid_zads)})
        
        if ranking:
            df_rank = pd.DataFrame(ranking).sort_values(by="Avg Score", ascending=False).reset_index(drop=True)
            for i, row in df_rank.head(5).iterrows():
                klasa = f"rank-{i+1}" if i < 3 else ""
                st.markdown(f'<div class="leaderboard-row {klasa}"><span>#{i+1} {row["Name"]}</span> <span>AVG: {row["Avg Score"]}/10 ({row["Missions"]} Ops)</span></div>', unsafe_allow_html=True)
        else: st.info("NO DATA FOR LEADERBOARD.")

    else:
        st.header(f"📤 INTEL UPLOAD: {st.session_state.mission_type.upper()}")
        if st.button("⬅️ ABORT TO LAUNCHPAD"): st.session_state.app_mode = "menu"; st.rerun()
        
        with st.popover("❓ FIELD MANUAL (HOW-TO)"):
            st.markdown("""
            **BETAFLIGHT BLACKBOX:** `set blackbox_device = SDCARD`, `set blackbox_rate = 1/1`. Wgraj plik .bbl.
            **SIMULATOR:** Liftoff (Documents/Liftoff/Logs), Velocidrone (Export to CSV).
            """)

        c_p1, c_p2 = st.columns([1, 2])
        with c_p1:
            pakiet = st.radio("SERVICE TIER:", ["📄 BASIC (1 Token) - AI Text", "💎 PREMIUM (2 Tokens) - 3D HUD & Analytics"])
            koszt = 1 if "BASIC" in pakiet else 2
        with c_p2:
            u_log = st.file_uploader("UPLOAD DATA", type=['bbl', 'csv'])
            if u_log and st.button(f"EXECUTE ANALYSIS ({koszt} TOKENS)"):
                if user_data.get('tokeny',0) >= koszt:
                    with st.spinner("PROCESSING TELEMETRY..."):
                        dec = get_decoder()
                        with open("/tmp/u.bbl", "wb") as f: f.write(u_log.getbuffer())
                        subprocess.run([dec, "/tmp/u.bbl"])
                        csvs = sorted(glob.glob("/tmp/u*.csv"))
                        if csvs:
                            df = pd.read_csv(csvs[0])
                            is_real = "Real" if st.session_state.app_mode == "drone" else "Sim"
                            stats = render_tactical_hud(df, mode=is_real, mission=st.session_state.mission_type, premium=(koszt==2))
                            
                            if init_ai():
                                raw_ai = get_ai_intel(f"Pilot: {user_data['imie']} ({user_data.get('level','Cadet')}). Misja: {st.session_state.mission_type}. Jerk: {stats['jr']:.2f}. Zwróć TYLKO czysty obiekt JSON bez znaczników markdown: {{\"ocena\": 1-10, \"diagnoza\": \"Tekst\", \"zadanie\": \"Zadanie\"}}")
                                try:
                                    js = json.loads(raw_ai.replace("```json","").replace("```","").strip())
                                    tag = "💎 PREMIUM" if koszt == 2 else "📄 BASIC"
                                    txt = f"### {tag} DEBRIEF [{st.session_state.mission_type}]\n\n**SCORE:** {js['ocena']}/10\n\n{js['diagnoza']}"
                                    
                                    zads = user_data.get('zadania', [])
                                    zads.append({"data": datetime.now().strftime("%Y-%m-%d"), "ocena": js['ocena'], "raport": txt, "type": st.session_state.mission_type, "premium": (koszt==2)})
                                    supabase.table('konta').update({"zadania": zads, "tokeny": user_data['tokeny']-koszt}).eq('email', user_data['email']).execute()
                                    st.rerun()
                                except: st.error("AI DATA CORRUPTION. PROSZĘ SPRÓBOWAĆ PONOWNIE.")
                else: st.error("INSUFFICIENT TOKENS. CONTACT COMMAND.")

    st.subheader("📋 PERSONAL MISSION ARCHIVE")
    for z in reversed(user_data.get('zadania', [])):
        if isinstance(z, dict):
            ico = "💎" if z.get('premium') else "📄"
            with st.expander(f"{ico} {z.get('data')} | {z.get('type','Op')} | SCORE: {z.get('ocena')}/10"):
                st.markdown(z.get('raport'))
                if z.get('wideo'): st.video(z.get('wideo'))
        else:
            with st.expander(f"📄 LEGACY MISSION LOG"):
                st.markdown(str(z))
