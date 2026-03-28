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
import uuid
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ==========================================
# 1. KONFIGURACJA SESJI
# ==========================================
st.set_page_config(page_title="FPV AI Academy", page_icon="🚁", layout="wide", initial_sidebar_state="expanded")

PRIMARY_COLOR = "#336600"
ACCENT_LIGHT = "#4d9900" 

def init_session():
    defaults = {
        'auth_user': None, 'role': None, 'flow_state': 'launchpad',
        'env_select': None, 'industry_select': None, 'skill_select': 'Średniozaawansowany',
        'theme_color': PRIMARY_COLOR, 'instructor_draft': None, 'temp_metrics': {}
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

init_session()

# WALIDACJA HASŁA
def is_password_strong(password):
    if len(password) < 6:
        return False, "Hasło musi mieć co najmniej 6 znaków."
    if not re.search(r"[A-Z]", password):
        return False, "Hasło musi zawierać co najmniej jedną wielką literę."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Hasło musi zawierać co najmniej jeden znak specjalny."
    return True, ""

# ==========================================
# 2. MODERN PREMIUM UI (CSS)
# ==========================================
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    .stApp {{ background: radial-gradient(circle at 50% 0%, #0d1a00 0%, #050a0a 40%, #000000 100%); color: #F8FAFC; font-family: 'Inter', sans-serif; }}
    
    .bento-card {{
        background: rgba(10, 15, 10, 0.6); backdrop-filter: blur(16px); border: 1px solid rgba(51, 102, 0, 0.2); 
        border-radius: 20px; padding: 30px; transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.8);
    }}
    .bento-card:hover {{ border-color: rgba(77, 153, 0, 0.5); box-shadow: 0 20px 50px -10px rgba(51, 102, 0, 0.3); transform: translateY(-3px); }}
    
    h1, h2, h3, h4 {{ font-weight: 800 !important; color: #FFFFFF !important; letter-spacing: -0.5px; }}
    .mono-text {{ font-family: 'Inter', sans-serif; color: #8cbf8c; font-size: 0.75rem; text-transform: uppercase; font-weight: 700; letter-spacing: 0.15em; }}
    
    div[data-testid="stMetric"] {{
        background: linear-gradient(180deg, rgba(20, 30, 20, 0.8) 0%, rgba(10, 15, 10, 0.9) 100%); 
        border: 1px solid rgba(51, 102, 0, 0.3); border-radius: 16px; padding: 24px; box-shadow: inset 0 2px 15px 0 rgba(51, 102, 0, 0.05); border-top: 2px solid {ACCENT_LIGHT};
    }}
    div[data-testid="stMetricValue"] {{ font-weight: 800; color: #FFFFFF; font-size: 2.2rem; text-shadow: 0 0 15px rgba(77, 153, 0, 0.4); }}
    
    .stButton>button {{ background: rgba(20, 30, 20, 0.8); border: 1px solid rgba(51,102,0,0.4); color: #E2E8F0; border-radius: 10px; font-weight: 600; transition: all 0.3s ease; }}
    .stButton>button:hover {{ background: rgba(51,102,0,0.2); color: #FFFFFF; border-color: {ACCENT_LIGHT}; box-shadow: 0 0 15px rgba(51,102,0,0.4); }}
    
    .cta-btn>button {{ background: linear-gradient(135deg, {PRIMARY_COLOR}, {ACCENT_LIGHT}); color: #FFFFFF; border: none; font-weight: 700; letter-spacing: 1px; box-shadow: 0 6px 25px 0 rgba(51, 102, 0, 0.5); border-radius: 10px; padding: 0.75rem 2rem; text-transform: uppercase; }}
    .cta-btn>button:hover {{ box-shadow: 0 8px 35px rgba(77, 153, 0, 0.7); transform: scale(1.03); }}
    
    .stTextInput input, .stTextArea textarea, .stNumberInput input {{ background: rgba(10, 15, 10, 0.8) !important; border: 1px solid rgba(51,102,0,0.3) !important; color: #FFFFFF !important; border-radius: 10px !important; }}
    .stTextInput input:focus, .stTextArea textarea:focus {{ border-color: {ACCENT_LIGHT} !important; box-shadow: 0 0 0 2px rgba(51,102,0,0.3) !important; }}
    
    .stDataFrame {{ background: rgba(10, 15, 10, 0.6); border-radius: 10px; }}
    section[data-testid="stSidebar"] {{ background-color: rgba(5, 10, 5, 0.95) !important; border-right: 1px solid rgba(51,102,0,0.2); backdrop-filter: blur(20px); }}
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    
    .danger-btn>button {{ border: 1px solid #ef4444; color: #ef4444; background: rgba(239, 68, 68, 0.1); }}
    .danger-btn>button:hover {{ background: #ef4444; color: #ffffff; }}
    </style>
    """, unsafe_allow_html=True)

def render_logo():
    st.write("<div style='text-align:center; padding-bottom:3rem; display:flex; flex-direction:column; align-items:center;'><svg width='80' height='80' viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M5.5 5.5h.01M18.5 5.5h.01M5.5 18.5h.01M18.5 18.5h.01' stroke='#4d9900' stroke-width='3' stroke-linecap='round'/><path d='M12 12L5.5 5.5M12 12l6.5-6.5M12 12l-6.5 6.5M12 12l6.5 6.5' stroke='#4d9900' stroke-width='1.5' stroke-linecap='round'/><circle cx='12' cy='12' r='3' fill='#050a0a' stroke='#4d9900' stroke-width='2'/></svg><h1 style='font-size:3rem; margin:10px 0 0 0; background:linear-gradient(90deg, #FFFFFF, #8cbf8c); -webkit-background-clip:text; -webkit-text-fill-color:transparent;'>FPV AI Academy</h1><p style='color:#64748B; font-size:1.1rem; margin-top:0.5rem; font-weight:600; letter-spacing:2px;'>TWÓJ WIRTUALNY TRENER LOTÓW</p></div>", unsafe_allow_html=True)

def generate_html_report(date, score, report_text, stats_dict, pilot_name):
    html_text = report_text.replace('<', '&lt;').replace('>', '&gt;')
    html_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html_text)
    html_text = re.sub(r'### (.*)', r'<h3>\1</h3>', html_text)
    html_text = html_text.replace('\n', '<br>')
    
    health_pct = max(0, min(100, stats_dict.get('health', 0)))
    roll_jerk = stats_dict.get('jr', 0)
    roll_pct = max(0, min(100, 100 - (roll_jerk * 12)))
    pitch_jerk = stats_dict.get('jp', 0)
    pitch_pct = max(0, min(100, 100 - (pitch_jerk * 12)))
    max_g = stats_dict.get('max_g', 1)
    g_pct = max(0, min(100, (max_g / 10.0) * 100))
    
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #111; background: #fff; padding: 40px; line-height: 1.6; }}
            h1 {{ color: {PRIMARY_COLOR}; border-bottom: 2px solid {PRIMARY_COLOR}; padding-bottom: 10px; margin-bottom: 5px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .score {{ font-size: 2.5em; color: {PRIMARY_COLOR}; font-weight: bold; text-align: center; margin-bottom: 20px; }}
            .charts-container {{ background: #f9fdf9; border: 1px solid #e0e0e0; padding: 25px; border-radius: 12px; margin-bottom: 30px; }}
            .chart-title {{ font-size: 1.1em; font-weight: bold; margin-bottom: 15px; color: #333; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
            .bar-row {{ margin-bottom: 12px; }}
            .bar-label {{ display: flex; justify-content: space-between; font-size: 0.9em; margin-bottom: 4px; font-weight: bold; color: #555; }}
            .bar-bg {{ width: 100%; background-color: #e0e0e0; border-radius: 6px; height: 16px; overflow: hidden; }}
            .bar-fill {{ height: 100%; background-color: {ACCENT_LIGHT}; border-radius: 6px; }}
            .bar-fill.gforce {{ background-color: #d9534f; }}
            .content-box {{ margin-top: 20px; padding: 25px; background: #fafafa; border-radius: 12px; border-left: 5px solid {ACCENT_LIGHT}; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Raport Treningowy FPV</h1>
            <p style="color: #666; font-size: 1.1em;">Data lotu: <b>{date}</b> | Pilot: <b>{pilot_name}</b></p>
        </div>
        <div class="score">Ocena lotu: {score}/10</div>
        <div class="charts-container">
            <div class="chart-title">Analiza Telemetryczna (Wizualizacja)</div>
            <div class="bar-row"><div class="bar-label"><span>Kondycja maszyny</span><span>{health_pct:.0f}%</span></div><div class="bar-bg"><div class="bar-fill" style="width: {health_pct}%;"></div></div></div>
            <div class="bar-row"><div class="bar-label"><span>Płynność Osi Roll (Mniej = lepiej)</span><span>{roll_jerk:.2f}</span></div><div class="bar-bg"><div class="bar-fill" style="width: {roll_pct}%;"></div></div></div>
            <div class="bar-row"><div class="bar-label"><span>Płynność Osi Pitch (Mniej = lepiej)</span><span>{pitch_jerk:.2f}</span></div><div class="bar-bg"><div class="bar-fill" style="width: {pitch_pct}%;"></div></div></div>
            <div class="bar-row"><div class="bar-label"><span>Max Przeciążenie</span><span>{max_g:.1f} G</span></div><div class="bar-bg"><div class="bar-fill gforce" style="width: {g_pct}%;"></div></div></div>
        </div>
        <div class="content-box">{html_text}</div>
    </body>
    </html>
    """
    return html

# ==========================================
# 3. RDZEŃ SYSTEMU
# ==========================================
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def init_ai():
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return True
    return False

def generate_intel(prompt):
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        best = next((m for m in models if '1.5-flash' in m), models[0])
        return genai.GenerativeModel(best).generate_content(prompt).text
    except Exception as e:
        return f'{{"ocena": 0, "diagnoza": "Błąd komunikacji z systemem AI.", "zadanie": "Brak zadań."}}'

@st.cache_resource(show_spinner=False)
def get_decoder():
    path = "/tmp/fcis_engine"
    if not os.path.exists(path):
        os.makedirs("/tmp/src", exist_ok=True)
        urllib.request.urlretrieve("https://github.com/betaflight/blackbox-tools/archive/refs/heads/master.zip", "/tmp/b.zip")
        with zipfile.ZipFile("/tmp/b.zip", 'r') as z: z.extractall("/tmp/src")
        subprocess.run(["make", "obj/blackbox_decode"], cwd="/tmp/src/blackbox-tools-master", check=True, stdout=subprocess.DEVNULL)
        shutil.copy("/tmp/src/blackbox-tools-master/obj/blackbox_decode", path)
    os.chmod(path, 0o755)
    return path

# ==========================================
# INTELIGENTNE DEKODOWANIE (NOWA FUNKCJA)
# ==========================================
@st.cache_data(show_spinner=False)
def decode_file(file_bytes, file_name):
    """Zapisuje, dekoduje plik BBL i zwraca listę poprawnych (niepustych) lotów CSV."""
    temp_dir = f"/tmp/fpv_decode_{uuid.uuid4().hex[:8]}"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file_name)
    
    with open(file_path, "wb") as f:
        f.write(file_bytes)
        
    if file_name.lower().endswith('.csv'):
        return [file_path]
    else:
        dec = get_decoder()
        subprocess.run([dec, file_path], stdout=subprocess.DEVNULL, cwd=temp_dir)
        csvs = sorted(glob.glob(os.path.join(temp_dir, "*.csv")))
        
        # Filtrowanie plików, usuwamy śmieci i "puste" uzbrojenia (< 3KB to przeważnie same nagłówki)
        valid_csvs = [c for c in csvs if os.path.getsize(c) > 3072] 
        return valid_csvs

# ==========================================
# 4. SILNIK WIZUALIZACJI
# ==========================================
def render_terminal_hud(df, mode="Real", premium=False):
    try:
        thr = [c for c in df.columns if 'rcCommand[3]' in c or ('rcCommand' in c and '3' in c)][0]
        roll = [c for c in df.columns if 'rcCommand[0]' in c or ('rcCommand' in c and '0' in c)][0]
        pitch = [c for c in df.columns if 'rcCommand[1]' in c or ('rcCommand' in c and '1' in c)][0]
        yaw_cols = [c for c in df.columns if 'rcCommand[2]' in c or ('rcCommand' in c and '2' in c)]
        yaw = yaw_cols[0] if yaw_cols else None
        
        acc_x = [c for c in df.columns if 'accSmooth[0]' in c]
        acc_y = [c for c in df.columns if 'accSmooth[1]' in c]
        acc_z = [c for c in df.columns if 'accSmooth[2]' in c]
        has_acc = bool(acc_x and acc_y and acc_z)
    except:
        st.error("Nie znaleziono podstawowych danych telemetrycznych w przesłanym logu.")
        return None

    jr, jp = df[roll].diff().abs().mean(), df[pitch].diff().abs().mean()
    jy = df[yaw].diff().abs().mean() if yaw else 0
    smoothness = max(0, 10 - ((jr + jp + jy) * 0.8))
    avg_t = df[thr].mean()
    
    max_g = 1.0
    if has_acc:
        g_vector = np.sqrt(df[acc_x[0]]**2 + df[acc_y[0]]**2 + df[acc_z[0]]**2) / 2048.0
        max_g = g_vector.max()

    st.markdown("<p class='mono-text'>WYNIKI TELEMETRII</p>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Płynność lotu", f"{smoothness:.1f} / 10")
    m2.metric("Średni gaz", f"{avg_t:.0f}")
    m3.metric("Max przeciążenie", f"{max_g:.1f} G" if has_acc else "Brak danych")
    
    health = max(0, min(100, 100 - ((jr + jp) * 12)))
    m4.metric("Kondycja drona", f"{health:.0f}%")

    if premium:
        st.markdown("<br><p class='mono-text'>ANALIZA ZAAWANSOWANA (PREMIUM)</p>", unsafe_allow_html=True)
        t1, t2, t3, t4 = st.tabs(["Telemetria drążków", "Analiza przeciążeń (G-Force)", "Trajektoria 3D", "Silniki i zasilanie"])
        
        pdf = df.iloc[::max(1, len(df)//3000)]
        
        with t1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=pdf[thr], name="Gaz", line=dict(color='#2f3b2f', width=2), fill='tozeroy'))
            fig.add_trace(go.Scatter(y=pdf[roll], name="Roll", line=dict(color=ACCENT_LIGHT, width=2)))
            if yaw: fig.add_trace(go.Scatter(y=pdf[yaw], name="Yaw", line=dict(color='#FFFFFF', width=1, dash='dot')))
            fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
        with t2:
            if has_acc:
                g_series = np.sqrt(pdf[acc_x[0]]**2 + pdf[acc_y[0]]**2 + pdf[acc_z[0]]**2) / 2048.0
                fig_g = go.Figure()
                fig_g.add_trace(go.Scatter(y=g_series, name="G-Force", line=dict(color='#ff3333', width=2)))
                fig_g.add_hline(y=1.0, line_dash="dash", line_color="#8cbf8c", annotation_text="1G")
                fig_g.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_g, use_container_width=True)
            else: st.info("Brak danych G-Force.")

        with t3:
            fig3 = go.Figure(data=[go.Scatter3d(x=pdf[roll].cumsum()/500, y=pdf[pitch].cumsum()/500, z=np.arange(len(pdf)), 
                                mode='lines', line=dict(color=pdf[thr], colorscale='Greens', width=6))])
            fig3.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', scene=dict(bgcolor='rgba(0,0,0,0)'))
            st.plotly_chart(fig3, use_container_width=True)
            
        with t4:
            v_col = [c for c in df.columns if 'vbat' in c.lower()]
            mot_cols = [c for c in df.columns if 'motor[' in c.lower() or 'motor0' in c.lower()]
            has_data = False
            
            if mot_cols and len(mot_cols) >= 4:
                has_data = True
                mot_avgs = [df[m].mean() for m in mot_cols[:4]]
                fig_mot = go.Figure(data=[go.Bar(x=['Silnik 1', 'Silnik 2', 'Silnik 3', 'Silnik 4'], y=mot_avgs, marker_color=ACCENT_LIGHT)])
                fig_mot.update_layout(title="Średnie obciążenie silników", template="plotly_dark", height=250, margin=dict(l=0,r=0,t=40,b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_mot, use_container_width=True)
            
            if v_col and mode == "Real":
                has_data = True
                f_bat = make_subplots(specs=[[{"secondary_y": True}]])
                f_bat.add_trace(go.Scatter(y=pdf[v_col[0]]/100, name="Napięcie (V)", line=dict(color='#F8FAFC', width=2)), secondary_y=False)
                f_bat.add_trace(go.Scatter(y=pdf[thr], name="Gaz", line=dict(color=ACCENT_LIGHT, width=1), fill='tozeroy', opacity=0.3), secondary_y=True)
                f_bat.update_layout(title="Spadek napięcia a użycie gazu", template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(f_bat, use_container_width=True)
                
            if not has_data: st.info("Brak wystarczających danych o zasilaniu w logu symulatora.")
            
    return {"jr": float(jr), "jp": float(jp), "health": float(health), "avg_t": float(avg_t), "max_g": float(max_g)}

# ==========================================
# 5. EKRAN LOGOWANIA I REJESTRACJI
# ==========================================
if st.session_state.auth_user is None:
    render_logo()
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Zaloguj się", "Załóż konto"])
        with t1:
            em = st.text_input("Adres e-mail")
            pw = st.text_input("Hasło", type="password")
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("Zaloguj się do panelu"):
                res = supabase.table('konta').select('*').eq('email', em).execute()
                if res.data and res.data[0]['haslo'] == pw:
                    
                    is_verified = res.data[0].get('zweryfikowany')
                    if em.lower() == 'admin@fpv.pl':
                        is_verified = True 
                        
                    if is_verified is False:
                        st.error("⚠️ Twoje konto oczekuje na weryfikację. Skontaktuj się z Administratorem.")
                    else:
                        st.session_state.auth_user = em
                        st.session_state.role = res.data[0]['rola']
                        st.rerun()
                else: st.error("Nieprawidłowy adres e-mail lub hasło.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with t2:
            rem = st.text_input("Nowy adres e-mail")
            rpw = st.text_input("Nowe hasło", type="password", key="reg_pass")
            rnm = st.text_input("Imię lub pseudonim pilota")
            if st.button("Zarejestruj się"):
                email_check = supabase.table('konta').select('email').eq('email', rem).execute()
                if email_check.data:
                    st.error("Konto z tym adresem e-mail już istnieje w naszym systemie!")
                else:
                    is_valid, msg = is_password_strong(rpw)
                    if not is_valid:
                        st.error(msg)
                    else:
                        supabase.table('konta').insert({
                            'email': rem, 'haslo': rpw, 'imie': rnm, 'rola': 'Kursant', 
                            'tokeny': 10, 'zadania': [], 'zweryfikowany': False
                        }).execute()
                        st.success("Konto założone pomyślnie! Oczekuj na weryfikację przez Administratora.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 6. LOGIKA UPRAWNIEŃ (KTO JEST KIM)
# ==========================================
user_data = supabase.table('konta').select('*').eq('email', st.session_state.auth_user).execute().data[0]

is_admin = (user_data['rola'].lower() == 'admin') or (user_data['email'].lower() == 'admin@fpv.pl')
is_instructor = (user_data['rola'].lower() in ['instruktor', 'admin']) or is_admin

def render_history_stats(stats_dict):
    st.markdown("<p class='mono-text' style='margin-top: 15px;'>METRYKI ZAPISANE W BAZIE</p>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Kondycja", f"{stats_dict.get('health', 0):.0f}%")
    c2.metric("Roll Jerk", f"{stats_dict.get('jr', 0):.2f}")
    c3.metric("Pitch Jerk", f"{stats_dict.get('jp', 0):.2f}")
    c4.metric("Max G", f"{stats_dict.get('max_g', 0):.1f} G")

# ==========================================
# 7. PANEL INSTRUKTORA / ADMINA
# ==========================================
if is_instructor:
    render_logo()
    col_nav, col_main = st.columns([1, 3])
    
    with col_nav:
        if is_admin:
            st.markdown(f"<div class='bento-card'><p class='mono-text'>ZARZĄDZANIE (ADMIN)</p>", unsafe_allow_html=True)
            cadets = supabase.table('konta').select('*').neq('email', user_data['email']).execute().data
        else:
            st.markdown(f"<div class='bento-card'><p class='mono-text'>TWOI KURSANCI</p>", unsafe_allow_html=True)
            cadets = supabase.table('konta').select('*').eq('rola', 'Kursant').execute().data
            
        if not cadets: st.warning("Brak użytkowników w bazie danych."); st.stop()
        
        display_names = [f"✅ {k['email']}" if k.get('zweryfikowany', True) is True else f"❌ {k['email']}" for k in cadets]
        selected_display = st.radio("Wybierz użytkownika:", display_names, label_visibility="collapsed")
        
        selected_email = selected_display[2:] 
        target_data = next(k for k in cadets if k['email'] == selected_email)
        
        st.markdown(f"<br><p class='mono-text'>STAN KONTA: <span style='color: {ACCENT_LIGHT}; font-weight: bold;'>{target_data.get('tokeny', 0)} Tokenów</span></p>", unsafe_allow_html=True)
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1: dodaj_tok = st.number_input("Dodaj", min_value=1, max_value=100, value=5, label_visibility="collapsed")
        with col_t2:
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("ZASIL"):
                supabase.table('konta').update({"tokeny": target_data.get('tokeny', 0) + dodaj_tok}).eq('email', selected_email).execute()
                st.toast("Zasilono konto użytkownika.", icon="🟢")
                time.sleep(1)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><p class='mono-text'>DANE DO ANALIZY</p>", unsafe_allow_html=True)
        inst_env = st.selectbox("Środowisko", ["Lot rzeczywisty", "Symulator"])
        inst_ind = st.selectbox("Styl lotu", ["Cinematic / Płynny", "Racing (Wyścigi)", "Freestyle"]) if inst_env == "Lot rzeczywisty" else "Standard"
        inst_skill = st.selectbox("Poziom zaawansowania", ["Początkujący", "Średniozaawansowany", "Ekspert"])
        
        if is_admin:
            st.markdown("<br><p class='mono-text'>ZARZĄDZANIE KONTAMI (ADMIN)</p>", unsafe_allow_html=True)
            
            if target_data.get('zweryfikowany') is False:
                if st.button("✅ Zweryfikuj to konto (Wpuść)", use_container_width=True):
                    supabase.table('konta').update({"zweryfikowany": True}).eq('email', selected_email).execute()
                    st.success("Konto zweryfikowane! Użytkownik może się teraz zalogować.")
                    time.sleep(1)
                    st.rerun()
            
            if target_data['rola'].lower() == 'kursant':
                if st.button("🌟 Nadaj Rangę Instruktora", use_container_width=True):
                    supabase.table('konta').update({"rola": "Instruktor"}).eq('email', selected_email).execute()
                    st.success(f"{target_data['imie']} otrzymał uprawnienia trenerskie!")
                    time.sleep(1)
                    st.rerun()
            elif target_data['rola'].lower() == 'instruktor':
                if st.button("🔻 Odbierz Rangę Instruktora", use_container_width=True):
                    supabase.table('konta').update({"rola": "Kursant"}).eq('email', selected_email).execute()
                    st.warning(f"{target_data['imie']} został zdegradowany do roli Kursanta.")
                    time.sleep(1)
                    st.rerun()

        st.markdown("<br><p class='mono-text'>OPCJE</p>", unsafe_allow_html=True)
        if st.button("Wyloguj się"): st.session_state.auth_user = None; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_main:
        st.markdown(f"<h2>Profil użytkownika: <span style='color:{ACCENT_LIGHT}'>{target_data['imie']} ({target_data['rola']})</span></h2>", unsafe_allow_html=True)
        
        if is_admin:
            with st.expander("⚙️ Edycja danych użytkownika (Tylko Admin)"):
                with st.form("edit_user_form"):
                    e_imie = st.text_input("Imię / Pseudonim", value=target_data['imie'])
                    e_email = st.text_input("Adres E-mail", value=target_data['email'])
                    e_haslo = st.text_input("Hasło", value=target_data['haslo'])
                    if st.form_submit_button("Zapisz zmiany w bazie"):
                        supabase.table('konta').update({
                            'imie': e_imie,
                            'email': e_email,
                            'haslo': e_haslo
                        }).eq('email', target_data['email']).execute()
                        st.success("Zaktualizowano dane użytkownika!")
                        time.sleep(1)
                        st.rerun()
                
                st.markdown("<hr style='border-color: #334155;'>", unsafe_allow_html=True)
                st.markdown("<p style='color: #ef4444; font-weight: bold; margin-bottom: 5px;'>Strefa Niebezpieczna</p>", unsafe_allow_html=True)
                st.markdown("<div class='danger-btn'>", unsafe_allow_html=True)
                if st.button("🗑️ USUŃ TO KONTO BEZPOWROTNIE", use_container_width=True):
                    supabase.table('konta').delete().eq('email', target_data['email']).execute()
                    st.error(f"Konto użytkownika {target_data['imie']} zostało pomyślnie i bezpowrotnie usunięte z systemu.")
                    time.sleep(1.5)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        
        zad = target_data.get('zadania', [])
        loty = [z for z in zad if isinstance(z, dict) and 'ocena' in z and z.get('type') != 'Mechanik AI']
        mech_uses = len([z for z in zad if isinstance(z, dict) and z.get('type') == 'Mechanik AI'])
        avg_score = sum(z['ocena'] for z in loty) / len(loty) if loty else 0
        
        st.markdown("<div class='bento-card' style='margin-bottom: 30px;'>", unsafe_allow_html=True)
        st.markdown("<p class='mono-text' style='margin-bottom: 20px;'>PODSUMOWANIE POSTĘPÓW</p>", unsafe_allow_html=True)
        cm1, cm2, cm3 = st.columns(3)
        cm1.metric("Wykonane Analizy", len(loty))
        cm2.metric("Średnia Ocena AI", f"{avg_score:.1f}/10")
        cm3.metric("Zapytania do Warsztatu AI", mech_uses)
        
        if len(loty) > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            dates = [z['data'] for z in loty if 'stats' in z]
            roll_jerks = [z['stats'].get('jr', 0) for z in loty if 'stats' in z]
            pitch_jerks = [z['stats'].get('jp', 0) for z in loty if 'stats' in z]
            
            if dates:
                fig_prog_inst = go.Figure()
                fig_prog_inst.add_trace(go.Scatter(x=dates, y=roll_jerks, mode='lines+markers', name='Roll Jerk', line=dict(color=ACCENT_LIGHT, width=2)))
                fig_prog_inst.add_trace(go.Scatter(x=dates, y=pitch_jerks, mode='lines+markers', name='Pitch Jerk', line=dict(color='#FFFFFF', dash='dot')))
                fig_prog_inst.update_layout(title="Historia płynności kursanta (im niżej, tym płynniejszy lot)", template="plotly_dark", height=250, margin=dict(l=0,r=0,t=40,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_prog_inst, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        c_upl, c_vid = st.columns(2)
        with c_upl: log_file = st.file_uploader("Wgraj plik z logami lotu (BBL/CSV)", type=['bbl', 'csv'], label_visibility="collapsed")
        with c_vid: vid_link = st.text_input("Opcjonalny link do nagrania (np. YouTube)", placeholder="https://...")

        df_active = None
        if log_file:
            # NOWA LOGIKA DEKODOWANIA I WYBORU LOTU (INSTRUKTOR)
            valid_csvs = decode_file(log_file.getvalue(), log_file.name)
            if not valid_csvs:
                st.warning("⚠️ Ten plik nie zawiera poprawnych danych lotu (jest pusty lub to był tylko szybki test uzbrojenia silników).")
            else:
                if len(valid_csvs) > 1:
                    options = {c: f"Zapis nr {i+1} (Rozmiar: {os.path.getsize(c)//1024} KB)" for i, c in enumerate(valid_csvs)}
                    selected_csv = st.selectbox("Wykryto kilka lotów w tym pliku. Wybierz jeden do analizy:", list(options.keys()), format_func=lambda x: options[x])
                else:
                    selected_csv = valid_csvs[0]
                    
                with st.status("Ekstrakcja danych...", expanded=False) as status:
                    df_active = pd.read_csv(selected_csv)
                    status.update(label="Dane zdekodowane pomyślnie.", state="complete", expanded=False)

        if df_active is not None:
            stats = render_terminal_hud(df_active, mode="Real" if inst_env=="Lot rzeczywisty" else "Sim", premium=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("GENERUJ WSKAZÓWKI AI"):
                if init_ai():
                    prompt = f"Instruktor FPV. Kursant: {inst_skill}, Styl: {inst_ind}. Płynność Roll: {stats['jr']:.2f}, G-Force: {stats['max_g']:.1f}G. Wygeneruj JSON: {{\"ocena\": 8, \"diagnoza\": \"...\", \"zadanie\": \"...\"}}"
                    raw = generate_intel(prompt)
                    try:
                        js = json.loads(raw.replace("```json","").replace("```","").strip())
                        st.session_state.instructor_draft = f"### Analiza lotu: {inst_ind}\n**OCENA LOTU:** {js['ocena']}/10\n\n**WSKAZÓWKI TRENERA:**\n{js['diagnoza']}\n\n**ZADANIE NA NASTĘPNY TRENING:**\n{js['zadanie']}"
                        st.session_state.temp_metrics = stats
                    except: st.error("Wystąpił błąd w generowaniu odpowiedzi przez AI.")
            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.instructor_draft:
            final_rep = st.text_area("Edytuj raport przed wysłaniem", value=st.session_state.instructor_draft, height=250)
            if st.button("ZATWIERDŹ I WYŚLIJ DO UŻYTKOWNIKA"):
                match = re.search(r"OCENA LOTU:\s*(\d+)/10", final_rep)
                score = int(match.group(1)) if match else 5
                new_record = {"data": datetime.now().strftime("%Y-%m-%d %H:%M"), "ocena": score, "raport": final_rep, "wideo": vid_link, "type": inst_ind, "premium": True, "stats": st.session_state.temp_metrics}
                
                history = target_data.get('zadania', [])
                history.append(new_record)
                history = history[-10:]
                
                supabase.table('konta').update({"zadania": history}).eq('email', selected_email).execute()
                st.session_state.instructor_draft = None
                st.rerun()
            
        st.markdown("<br><p class='mono-text'>HISTORIA AKTYWNOŚCI UŻYTKOWNIKA</p>", unsafe_allow_html=True)
        for z in reversed(target_data.get('zadania', [])):
            if isinstance(z, dict):
                if z.get('type') == 'Mechanik AI':
                    with st.expander(f"🤖 {z.get('data')} | Warsztat: Zapytanie o pomoc techniczną"):
                        st.markdown(z.get('raport'))
                else:
                    with st.expander(f"📄 {z.get('data')} | Ocena: {z.get('ocena')}/10"):
                        st.markdown(z.get('raport'))
                        if 'stats' in z: 
                            render_history_stats(z['stats'])
                            html_report = generate_html_report(z.get('data'), z.get('ocena'), z.get('raport'), z['stats'], target_data['imie'])
                            st.download_button(label="📥 Pobierz Dokument (PDF z Wykresami)", data=html_report, file_name=f"Raport_{z.get('data').split(' ')[0]}.html", mime="text/html", key=f"inst_dl_{z.get('data')}")

# ==========================================
# 8. PANEL KURSANTA
# ==========================================
else:
    with st.sidebar:
        st.markdown(f"<p class='mono-text'>ZALOGOWANY PILOT: <br><span style='color: {ACCENT_LIGHT}; font-size: 1.2em;'>{user_data['imie']}</span></p>", unsafe_allow_html=True)
        st.metric("DOSTĘPNE TOKENY", user_data.get('tokeny', 0))
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("💡 Gdy Instruktor prześle Ci nowy raport, użyj poniższego przycisku, aby odświeżyć dane bez wylogowywania się z konta.")
        if st.button("🔄 Synchronizuj z serwerem", use_container_width=True): 
            st.rerun()
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Wyloguj się"): st.session_state.auth_user = None; st.rerun()

    if st.session_state.flow_state == 'launchpad':
        render_logo()
        
        tab_main, tab_prog, tab_rank, tab_workshop = st.tabs(["🚀 Panel Główny", "📈 Twoje Postępy", "🏆 Globalny Ranking", "🛠️ Warsztat FPV"])
        
        with tab_main:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("<div class='bento-card'><h3>🚁 LOT RZECZYWISTY</h3><p class='mono-text'>Analiza z plików drona (.BBL)</p></div>", unsafe_allow_html=True)
                col_m, col_r, col_f = st.columns(3)
                if col_m.button("Cinematic"): st.session_state.industry_select="Cinematic / Płynny"; st.session_state.env_select="Real"; st.rerun()
                if col_r.button("Racing"): st.session_state.industry_select="Racing (Wyścigi)"; st.session_state.env_select="Real"; st.rerun()
                if col_f.button("Freestyle"): st.session_state.industry_select="Freestyle"; st.session_state.env_select="Real"; st.rerun()
            with c2:
                st.markdown("<div class='bento-card'><h3>🎮 SYMULATOR</h3><p class='mono-text'>Liftoff / Velocidrone (.CSV)</p></div>", unsafe_allow_html=True)
                if st.button("Uruchom analizę symulatora", use_container_width=True): 
                    st.session_state.industry_select="Symulator treningowy"; st.session_state.env_select="Sim"; st.rerun()
            
            if st.session_state.industry_select:
                st.markdown("<br><h2>TWÓJ POZIOM DOŚWIADCZENIA</h2>", unsafe_allow_html=True)
                skill = st.select_slider("Poziom do oceny przez AI:", options=["Początkujący", "Średniozaawansowany", "Ekspert"], value=st.session_state.skill_select, label_visibility="collapsed")
                st.session_state.skill_select = skill
                
                st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
                if st.button("PRZEJDŹ DO WGRYWANIA PLIKU"): st.session_state.flow_state = 'upload'; st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<br><p class='mono-text'>TWOJE OSTATNIE LOTY I WSKAZÓWKI</p>", unsafe_allow_html=True)
            for z in reversed(user_data.get('zadania', [])):
                if isinstance(z, dict):
                    if z.get('type') == 'Mechanik AI':
                        with st.expander(f"🤖 {z.get('data')} | Warsztat: Diagnoza sprzętu"):
                            st.markdown(z.get('raport'))
                    else:
                        icon = "🟢" if z.get('premium') else "📄"
                        with st.expander(f"{icon} {z.get('data')} | {z.get('type','Lot')} | Ocena: {z.get('ocena')}/10"):
                            st.markdown(z.get('raport'))
                            if 'stats' in z and z.get('premium'): 
                                render_history_stats(z['stats'])
                                html_report = generate_html_report(z.get('data'), z.get('ocena'), z.get('raport'), z['stats'], user_data['imie'])
                                st.download_button(label="📥 Pobierz Raport (PDF z Wykresami)", data=html_report, file_name=f"FPV_Raport_{z.get('data').split(' ')[0]}.html", mime="text/html", key=f"dl_{z.get('data')}")
                else:
                    with st.expander("Stare zapisy archiwalne"): st.markdown(str(z))

        with tab_prog:
            st.markdown("### Monitorowanie Płynności Lotu")
            st.markdown("<p style='color: #8cbf8c;'>Śledź, jak na przestrzeni czasu rozwija się Twoja technika. Im niżej wykres schodzi w dół (mniejsze szarpanie drążkami), tym lepszym jesteś pilotem!</p>", unsafe_allow_html=True)
            history = [z for z in user_data.get('zadania', []) if isinstance(z, dict) and 'stats' in z and z.get('type') != 'Mechanik AI']
            if len(history) > 1:
                dates = [z['data'] for z in history]
                roll_jerks = [z['stats'].get('jr', 0) for z in history]
                pitch_jerks = [z['stats'].get('jp', 0) for z in history]
                
                fig_prog = go.Figure()
                fig_prog.add_trace(go.Scatter(x=dates, y=roll_jerks, mode='lines+markers', name='Roll Jerk (Obrót)', line=dict(color=ACCENT_LIGHT, width=3)))
                fig_prog.add_trace(go.Scatter(x=dates, y=pitch_jerks, mode='lines+markers', name='Pitch Jerk (Przód/Tył)', line=dict(color='#FFFFFF', dash='dot')))
                fig_prog.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_prog, use_container_width=True)
            else:
                st.info("Wykonaj co najmniej dwie analizy lotu, aby zobaczyć tutaj swój wykres postępu.")

        with tab_rank:
            st.markdown("### Top Piloci FPV Academy")
            all_cadets = supabase.table('konta').select('imie, zadania').eq('rola', 'Kursant').execute().data
            leaderboard = []
            
            for k in all_cadets:
                zad = k.get('zadania', [])
                valid_zad = [z for z in zad if isinstance(z, dict) and 'ocena' in z and z.get('type') != 'Mechanik AI']
                if valid_zad:
                    avg_ocena = sum(z['ocena'] for z in valid_zad) / len(valid_zad)
                    max_g = max((z.get('stats', {}).get('max_g', 0) for z in valid_zad), default=0)
                    leaderboard.append({"Pilot": k['imie'], "Średnia Ocena": round(avg_ocena, 1), "Max G-Force": round(max_g, 1), "Ukończone Analizy": len(valid_zad)})
            
            if leaderboard:
                df_leaderboard = pd.DataFrame(leaderboard).sort_values(by="Średnia Ocena", ascending=False).reset_index(drop=True)
                df_leaderboard.index += 1
                st.dataframe(df_leaderboard, use_container_width=True)
            else:
                st.info("Brak wystarczających danych do wygenerowania rankingu.")

        with tab_workshop:
            st.markdown("## 🛠️ Warsztat i Wiedza FPV")
            st.markdown("<p style='color: #8cbf8c;'>Twoje centrum diagnozy usterek, konfiguracji sprzętu i poszerzania wiedzy lotniczej.</p>", unsafe_allow_html=True)
            
            w_mech, w_calc, w_vtx, w_dict = st.tabs(["🤖 Wirtualny Mechanik AI", "⚖️ Kalkulator Napędu", "📡 Ściągawka VTX", "📚 Słowniczek Betaflight"])
            
            with w_mech:
                st.markdown("### Sztuczna Inteligencja Serwisowa")
                st.write("Opisz objawy, jakie daje Twój dron (np. wibracje przy opadaniu, gorące silniki), a AI postara się zdiagnozować usterkę.")
                mech_query = st.text_area("Opisz problem ze sprzętem:", placeholder="Np. Dron po zrobieniu flipa na chwilę traci moc i dziwnie wyje...")
                st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
                if st.button("POPROŚ O DIAGNOZĘ (-0 TOKENÓW)"):
                    if mech_query and init_ai():
                        with st.spinner("Nasz mechanik analizuje problem..."):
                            prompt = f"Jesteś przyjaznym i profesjonalnym serwisantem dronów FPV. Krótko i zwięźle pomóż rozwiązać problem użytkownika, udzielając porad w punktach. Problem: {mech_query}"
                            try:
                                models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                                best_model = next((m for m in models if '1.5-flash' in m), models[0])
                                mech_resp = genai.GenerativeModel(best_model).generate_content(prompt).text
                                
                                user_history = user_data.get('zadania', [])
                                user_history.append({
                                    "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    "type": "Mechanik AI",
                                    "raport": f"**Pytanie do systemu:** {mech_query}\n\n**Diagnoza Mechanika:**\n{mech_resp}"
                                })
                                user_history = user_history[-10:]
                                supabase.table('konta').update({"zadania": user_history}).eq('email', user_data['email']).execute()
                                
                                st.success("Analiza zakończona! Wskazówki zostały zapisane w Twojej historii lotów:")
                                st.markdown(mech_resp)
                            except Exception as e:
                                st.error(f"Błąd połączenia z modułem serwisowym AI. Upewnij się, że klucz API działa.")
                st.markdown("</div>", unsafe_allow_html=True)

            with w_calc:
                st.markdown("### Kreator Setupu Drona")
                frame_size = st.selectbox("Rozmiar ramy:", ["TinyWhoop (65-75mm)", "3 Cale (Cinewhoop / Micro)", "5 Cali (Freestyle / Race)", "7 Cali (Long Range)"])
                
                specs = {
                    "TinyWhoop (65-75mm)": {"Silniki": "0702 - 0802 (19000KV - 25000KV)", "Bateria": "1S (300mAh - 450mAh) BT2.0", "ESC": "5A - 12A (AIO)", "Śmigła": "31mm - 40mm Bi-blade / Tri-blade"},
                    "3 Cale (Cinewhoop / Micro)": {"Silniki": "1404 - 1504 (3000KV - 4500KV)", "Bateria": "4S (650mAh - 850mAh)", "ESC": "20A - 35A", "Śmigła": "3 cale Tri-blade (z osłonami lub bez)"},
                    "5 Cali (Freestyle / Race)": {"Silniki": "2207 - 2306 (1750KV - 1950KV dla 6S)", "Bateria": "6S (1050mAh - 1300mAh)", "ESC": "45A - 60A", "Śmigła": "5.1 cala Tri-blade (np. 5143, 51466)"},
                    "7 Cali (Long Range)": {"Silniki": "2806.5 - 2809 (1300KV - 1500KV)", "Bateria": "6S Li-Ion (4000mAh) lub LiPo (2000mAh+)", "ESC": "50A - 60A", "Śmigła": "7 cali Bi-blade / Tri-blade (np. 7040)"}
                }
                
                st.markdown(f"#### Zalecany sprzęt dla ramy: {frame_size}")
                c1, c2 = st.columns(2)
                with c1:
                    st.info(f"**⚡ Silniki (Statory & KV):**\n\n{specs[frame_size]['Silniki']}")
                    st.info(f"**🔋 Bateria (Napięcie & Pojemność):**\n\n{specs[frame_size]['Bateria']}")
                with c2:
                    st.info(f"**🔌 ESC (Regulator obrotów):**\n\n{specs[frame_size]['ESC']}")
                    st.info(f"**🚁 Śmigła (Props):**\n\n{specs[frame_size]['Śmigła']}")

            with w_vtx:
                st.markdown("### Pełna Macierz Częstotliwości VTX (5.8 GHz)")
                st.write("Wszystkie najpopularniejsze pasma i kanały wideo używane w lotach FPV.")
                
                vtx_matrix = pd.DataFrame({
                    "Pasmo": ["Band A", "Band B", "Band E (Boscam)", "Fatshark (F)", "Raceband (R)"],
                    "CH 1": [5865, 5733, 5705, 5740, 5658],
                    "CH 2": [5845, 5752, 5685, 5760, 5695],
                    "CH 3": [5825, 5771, 5665, 5780, 5732],
                    "CH 4": [5805, 5790, 5645, 5800, 5769],
                    "CH 5": [5785, 5809, 5885, 5820, 5806],
                    "CH 6": [5765, 5828, 5905, 5840, 5843],
                    "CH 7": [5745, 5847, 5925, 5860, 5880],
                    "CH 8": [5725, 5866, 5945, 5880, 5917]
                })
                vtx_matrix = vtx_matrix.set_index('Pasmo')
                
                st.markdown("#### Dobór częstotliwości do wspólnego latania")
                st.write("Wybierz liczbę pilotów w grupie, a system podpowie optymalne kanały. Aplikacja upewnia się, że częstotliwości są od siebie możliwie daleko, by zlikwidować zakłócenia obrazu w goglach.")
                pilots_count = st.slider("Ilu pilotów leci jednocześnie?", 1, 8, 4)
                
                optimal_freqs = {
                    1: [5658],
                    2: [5658, 5917],
                    3: [5658, 5769, 5917],
                    4: [5658, 5732, 5843, 5917],
                    5: [5645, 5705, 5769, 5843, 5917], 
                    6: [5645, 5695, 5760, 5800, 5860, 5917], 
                    7: [5645, 5695, 5740, 5780, 5820, 5860, 5917], 
                    8: [5645, 5685, 5725, 5760, 5800, 5840, 5880, 5917] 
                }
                active_freqs = optimal_freqs[pilots_count]
                
                def highlight_active(row):
                    return ['background-color: #336600; color: white; font-weight: bold' if val in active_freqs else '' for val in row]
                
                st.dataframe(vtx_matrix.style.apply(highlight_active, axis=1), use_container_width=True)
                
                freq_to_name = {
                    5658: "R1", 5917: "R8", 5769: "R4", 5732: "R3", 5843: "R6",
                    5645: "E4", 5705: "E1", 5695: "R2", 5760: "F2", 5800: "F4",
                    5860: "F7", 5740: "F1", 5780: "F3", 5820: "F5", 5685: "E2",
                    5725: "A8", 5840: "F6", 5880: "R7"
                }
                ch_names = [freq_to_name.get(f, str(f)) for f in active_freqs]
                st.success(f"Zalecane ułożenie kanałów dla {pilots_count} osób: **{', '.join(ch_names)}**")

            with w_dict:
                st.markdown("### Słowniczek FPV (Betaflight)")
                
                with st.expander("P-I-D (Proportional, Integral, Derivative)"):
                    st.write("**P (Proportional)** - Szybkość reakcji drona na drążki i wiatr. Zbyt niskie = dron 'pływa', zbyt wysokie = szybkie wibracje (oscylacje).")
                    st.write("**I (Integral)** - Trzymanie zadanego kąta. Pomaga dronowi nie ulegać wpływom wiatru i odchyleniom środka ciężkości baterii.")
                    st.write("**D (Derivative)** - 'Amortyzator' dla wartości P. Zapobiega przelatywaniu poza cel (overshoot) po ostrym manewrze. Zbyt wysokie D powoduje bardzo mocne grzanie silników.")
                
                with st.expander("Rates (RC Rate, Super Rate/Expo)"):
                    st.write("**RC Rate** - Czułość na samym środku drążka. Im wyższa, tym szybciej dron reaguje na najdrobniejsze ruchy palcami.")
                    st.write("**Super Rate / Expo** - Czułość na samych krawędziach wychylenia drążka. Pozwala na super szybkie flipy i rolle, zachowując przy tym miękki środek niezbędny do płynnego lotu (Cinematic).")
                
                with st.expander("Propwash (Oscylacje po zejściu)"):
                    st.write("Wibracje drona, które pojawiają się, gdy gwałtownie zawracasz lub opadasz pionowo we własne 'brudne powietrze' wyrzucone wcześniej przez śmigła. Zjawisko to redukujemy m.in. optymalizując wartość 'D' w Betaflight.")
                
                with st.expander("RPM Filtering (Filtry dwukierunkowe DShot)"):
                    st.write("Bardzo zaawansowana funkcja, gdzie regulator ESC na żywo wysyła do kontrolera lotu informację z jaką prędkością obraca się każdy z czterech silników. Dzięki temu Betaflight filtruje tylko te konkretne częstotliwości, które generują wibracje z silników, pozwalając dronom latać znacznie czyściej.")

    elif st.session_state.flow_state == 'upload':
        st.markdown(f"<h2>ANALIZA LOTU: <span style='color: {ACCENT_LIGHT};'>{st.session_state.industry_select.upper()}</span></h2>", unsafe_allow_html=True)
        if st.button("← Wróć do panelu głównego"): 
            st.session_state.flow_state = 'launchpad'
            st.session_state.env_select = None
            st.session_state.industry_select = None
            st.rerun()

        c_tier, c_drop = st.columns([1, 2])
        with c_tier:
            st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
            st.markdown("<p class='mono-text'>WYBÓR PAKIETU ANALITYCZNEGO</p>", unsafe_allow_html=True)
            tier = st.radio("Poziom szczegółowości:", ["Standardowy (1 Token)", "Premium + G-Force (2 Tokeny)"], label_visibility="collapsed")
            cost = 1 if "Standardowy" in tier else 2
            st.markdown(f"<p style='font-size: 0.9em; color: #8cbf8c; margin-top: 10px;'>Dostępne środki: <b>{user_data.get('tokeny', 0)} Tokenów</b></p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c_drop:
            u_log = st.file_uploader("Upuść plik z logami z lotu (.bbl lub .csv)", type=['bbl', 'csv'], label_visibility="collapsed")
            
            if u_log:
                # NOWA LOGIKA DEKODOWANIA I WYBORU LOTU (KURSANT)
                valid_csvs = decode_file(u_log.getvalue(), u_log.name)
                
                if not valid_csvs:
                    st.warning("⚠️ Ten plik nie zawiera poprawnych danych lotu (jest pusty lub to był tylko szybki test uzbrojenia silników). Wgraj inny plik.")
                else:
                    if len(valid_csvs) > 1:
                        options = {c: f"Zapis nr {i+1} (Rozmiar: {os.path.getsize(c)//1024} KB)" for i, c in enumerate(valid_csvs)}
                        selected_csv = st.selectbox("Wykryto kilka lotów w tym pliku. Wybierz ten, który chcesz przeanalizować:", list(options.keys()), format_func=lambda x: options[x])
                    else:
                        selected_csv = valid_csvs[0]
                        st.success("✅ Wykryto 1 poprawny lot w pliku.")
                        
                    st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
                    if st.button(f"ROZPOCZNIJ ANALIZĘ (-{cost} TOKENÓW)"):
                        if user_data.get('tokeny', 0) >= cost:
                            with st.status("Trwa wczytywanie i analiza danych...", expanded=True) as status:
                                df = pd.read_csv(selected_csv)
                                stats = render_terminal_hud(df, mode=st.session_state.env_select, premium=(cost==2))
                                
                                if init_ai():
                                    prompt = f"Trener personalny FPV. Uczeń: {user_data['imie']}, Poziom: {st.session_state.skill_select}, Styl: {st.session_state.industry_select}. Płynność Roll: {stats['jr']:.2f}, Max G: {stats['max_g']:.1f}G. Bądź przyjazny, zachęcaj do ćwiczeń. Wygeneruj czysty JSON: {{\"ocena\": 8, \"diagnoza\": \"...\", \"zadanie\": \"...\"}}"
                                    raw_ai = generate_intel(prompt)
                                    try:
                                        js = json.loads(raw_ai.replace("```json","").replace("```","").strip())
                                        tag = "RAPORT PREMIUM" if cost == 2 else "RAPORT STANDARDOWY"
                                        txt = f"### {tag}\n**OCENA LOTU:** {js['ocena']}/10\n\n**WSKAZÓWKI TRENERA:**\n{js['diagnoza']}\n\n**ZADANIE NA NASTĘPNY TRENING:**\n{js['zadanie']}"
                                        
                                        history = user_data.get('zadania', [])
                                        history.append({
                                            "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "ocena": js['ocena'], 
                                            "raport": txt, "type": st.session_state.industry_select, 
                                            "premium": (cost==2), "stats": stats
                                        })
                                        history = history[-10:] 
                                        
                                        supabase.table('konta').update({
                                            "zadania": history, "tokeny": user_data['tokeny'] - cost
                                        }).eq('email', user_data['email']).execute()
                                        
                                        status.update(label="Gotowe! Wyniki zapisane w Twoim profilu.", state="complete", expanded=False)
                                        time.sleep(1)
                                        st.session_state.flow_state = 'launchpad' 
                                        st.rerun()
                                    except: st.error("Niestety wystąpił problem podczas łączenia się z modułem AI.")
                        else: st.error("Niewystarczająca liczba tokenów na koncie, aby rozpocząć.")
                    st.markdown("</div>", unsafe_allow_html=True)
