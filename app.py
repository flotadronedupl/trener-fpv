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
st.set_page_config(page_title="FPV AI Academy | Twoja Platforma Premium", page_icon="🚁", layout="wide", initial_sidebar_state="expanded")

# OFICJALNA PALETA BARW (GLOBAL GIGANT STYLE)
PRIMARY_COLOR = "#336600" # Mroczna zieleń tła
ACCENT_LIGHT = "#4d9900"  # Neonowa zieleń metryk
TEXT_NEON = "#ccff99"     # Blado-zielony neon dla tekstu

def init_session():
    defaults = {
        'auth_user': None, 'role': None, 'flow_state': 'launchpad',
        'env_select': None, 'industry_select': None, 'skill_select': 'Średniozaawansowany',
        'theme_color': PRIMARY_COLOR, 'instructor_draft': None, 'temp_metrics': {}
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

init_session()

# ==========================================
# 1B. GLOBALNY TRACKER AI (RATE LIMITING)
# ==========================================
@st.cache_resource
def get_ai_tracker():
    return []

def get_ai_capacity():
    tracker = get_ai_tracker()
    now = time.time()
    # Usuwamy zapytania starsze niż 60 sekund
    tracker[:] = [t for t in tracker if now - t < 60]
    
    available = max(0, 15 - len(tracker))
    wait_time = 0
    if available == 0 and len(tracker) > 0:
        wait_time = 60 - (now - tracker[0])
        
    return available, wait_time

def register_ai_call():
    get_ai_tracker().append(time.time())

# ==========================================
# 2. GRAFICZNE CUDA (MODERN CSS & DYNAMIC BG)
# ==========================================
def render_neon_header(text, size="1.1rem"):
    return f"<p class='mono-text' style='font-size:{size}; text-shadow: 0 0 10px {ACCENT_LIGHT};'>{text}</p>"

def get_bento_card_style():
    return f"""
        background: rgba(10, 15, 10, 0.6); 
        backdrop-filter: blur(16px); 
        border: 1px solid rgba(51, 102, 0, 0.2); 
        border-radius: 20px; 
        padding: 30px; 
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); 
        box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.8);
    """

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* RADIALNY GRADIENT TŁA I NEONOWE BLASKI */
    .stApp {{ background: radial-gradient(circle at 50% -10%, #153315 0%, #050a0a 40%, #000000 100%); color: #F8FAFC; font-family: 'Inter', sans-serif; }}
    
    /* GLASSMORPHISM DLA KART */
    .bento-card {{
        {get_bento_card_style()}
    }}
    .bento-card:hover {{ border-color: rgba(77, 153, 0, 0.5); box-shadow: 0 20px 50px -10px rgba(51, 102, 0, 0.3); transform: translateY(-3px); }}
    
    /* NAGŁÓWKI Z EFEKTEM NEONOWYM */
    h1, h2, h3, h4 {{ font-weight: 800 !important; color: #FFFFFF !important; letter-spacing: -0.5px; text-shadow: 0 0 8px {ACCENT_LIGHT}; }}
    
    /* JEDNOKOLOROWE, CZYSTE METRYKI */
    div[data-testid="stMetric"] {{
        background: linear-gradient(180deg, rgba(20, 30, 20, 0.8) 0%, rgba(10, 15, 10, 0.9) 100%); 
        border: 1px solid rgba(51, 102, 0, 0.3); border-radius: 16px; padding: 24px; box-shadow: inset 0 2px 15px 0 rgba(51, 102, 0, 0.05); border-top: 2px solid {ACCENT_LIGHT};
    }}
    div[data-testid="stMetricValue"] {{ font-weight: 800; color: #FFFFFF; font-size: 2.2rem; text-shadow: 0 0 15px {ACCENT_LIGHT}; }}
    
    /* PRZYCISKI ENTERPRISE Z GLOW */
    .stButton>button {{ background: rgba(20, 30, 20, 0.8); border: 1px solid rgba(51,102,0,0.4); color: #E2E8F0; border-radius: 10px; font-weight: 600; transition: all 0.3s ease; }}
    .stButton>button:hover {{ background: rgba(51,102,0,0.2); color: #FFFFFF; border-color: {ACCENT_LIGHT}; box-shadow: 0 0 15px rgba(51,102,0,0.4); }}
    
    /* PRZYCISKI CTA Z LINIOWYM GRADIENTEM ZIELENI */
    .cta-btn>button {{ background: linear-gradient(135deg, {PRIMARY_COLOR}, {ACCENT_LIGHT}); color: #FFFFFF; border: none; font-weight: 700; letter-spacing: 1px; box-shadow: 0 6px 25px 0 rgba(51, 102, 0, 0.5); border-radius: 10px; padding: 0.75rem 2rem; text-transform: uppercase; }}
    .cta-btn>button:hover {{ box-shadow: 0 8px 35px {ACCENT_LIGHT}; transform: scale(1.03); }}
    
    /* INPUTY MROCZNE Z ZIELONYM FOCUS */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {{ background: rgba(10, 15, 10, 0.8) !important; border: 1px solid rgba(51,102,0,0.3) !important; color: #FFFFFF !important; border-radius: 10px !important; }}
    .stTextInput input:focus, .stTextArea textarea:focus {{ border-color: {ACCENT_LIGHT} !important; box-shadow: 0 0 0 2px rgba(51,102,0,0.3) !important; }}
    
    /* TABELE NEONOWE */
    .stDataFrame th, .stDataFrame tr {{ border-bottom: 1px solid rgba(51, 102, 0, 0.2); color: {TEXT_NEON}; }}
    
    /* SIDEBAR NEONOWY */
    section[data-testid="stSidebar"] {{ background-color: rgba(5, 10, 5, 0.95) !important; border-right: 1px solid rgba(51,102,0,0.2); backdrop-filter: blur(20px); }}
    
    /* UKRYCIE STOPKI I NAGŁÓWKA */
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# NOWA FUNKCJA: GENEROWANIE DYNAMICZNEGO TŁA SYMULACYJNEGO (Z BUTÓW WYKRĘCONE)
def render_live_background():
    """Generuje dynamiczne, mroczno-zielone tło trajektorii FPV"""
    # Symulacja trajektorii
    t = np.linspace(0, 10 * np.pi, 500)
    x = t * np.cos(t) + np.random.normal(0, 0.2, len(t))
    y = t * np.sin(t) + np.random.normal(0, 0.2, len(t))
    z = np.linspace(0, 20, len(t))

    fig = go.Figure(data=go.Scatter3d(x=x, y=y, z=z, mode='lines', line=dict(color=ACCENT_LIGHT, width=0.8, dash='dot')))
    
    # Styl mroczny premium
    fig.update_layout(
        template="plotly_dark",
        scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False), zaxis=dict(visible=False), bgcolor='rgba(0,0,0,0)',
            camera=dict(up=dict(x=0, y=0, z=1), center=dict(x=0, y=0, z=0), eye=dict(x=1.2, y=1.2, z=0.8))),
        margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', hovermode=False)
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ==========================================
# 3. RDZEŃ SYSTEMU Z BEZPIECZNYM AI MANAGEREM
# ==========================================
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def init_ai():
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return True
    return False

def call_ai_safe(prompt, is_json=True):
    """Zabezpieczona funkcja komunikacji z AI dbająca o limity sieciowe"""
    avail, wait = get_ai_capacity()
    
    if avail <= 0:
        if is_json:
            return f'{{"ocena": 0, "diagnoza": "Sieć analityczna jest aktualnie przeciążona przez zapytania innych pilotów. Twoje okno diagnostyczne otworzy się za {int(wait)} sekund. Proszę odczekać i spróbować ponownie.", "zadanie": "Wykorzystaj ten czas na naładowanie pakietu."}}'
        else:
            return f"⚠️ Sieć serwisu AI jest obecnie w pełni obciążona. Twoje okno diagnostyczne otworzy się za {int(wait)} sekund. Proszę odświeżyć system i spróbować ponownie."
            
    try:
        register_ai_call()
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        best = next((m for m in models if '1.5-flash' in m), models[0])
        return genai.GenerativeModel(best).generate_content(prompt).text
    except Exception as e:
        if is_json: return f'{{"ocena": 0, "diagnoza": "Wystąpił krytyczny błąd połączenia z modułem sztucznej inteligencji.", "zadanie": "Brak zadań."}}'
        else: return "Wystąpił krytyczny błąd połączenia z modułem sztucznej inteligencji."

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

@st.cache_data(show_spinner=False)
def decode_file(file_bytes, file_name):
    temp_dir = f"/tmp/fpv_decode_{uuid.uuid4().hex[:8]}"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file_name)
    with open(file_path, "wb") as f: f.write(file_bytes)
        
    if file_name.lower().endswith('.csv'): return [file_path]
    else:
        dec = get_decoder()
        subprocess.run([dec, file_path], stdout=subprocess.DEVNULL, cwd=temp_dir)
        csvs = sorted(glob.glob(os.path.join(temp_dir, "*.csv")))
        return [c for c in csvs if os.path.getsize(c) > 3072] 

# ==========================================
# 4. SILNIK WIZUALIZACJI Z NEONOWYM SZLIFEM
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
    smoothness = max(0, 10 - ((jr + jp) * 0.8))
    avg_t = df[thr].mean()
    max_g = (np.sqrt(df[acc_x[0]]**2 + df[acc_y[0]]**2 + df[acc_z[0]]**2)/2048.0).max() if has_acc else 1.0
    health = max(0, min(100, 100 - ((jr + jp) * 12)))

    st.markdown("<p class='mono-text'>WYNIKI TELEMETRII</p>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Płynność lotu", f"{smoothness:.1f} / 10")
    m2.metric("Średni gaz", f"{avg_t:.0f}")
    m3.metric("Max przeciążenie", f"{max_g:.1f} G" if has_acc else "Brak danych")
    m4.metric("Kondycja drona", f"{health:.0f}%")

    if premium:
        st.markdown("<br><p class='mono-text'>ANALIZA ZAAWANSOWANA (PREMIUM)</p>", unsafe_allow_html=True)
        t1, t2, t3, t4 = st.tabs(["Telemetria drążków", "Analiza przeciążeń (G-Force)", "Trajektoria 3D", "Silniki i zasilanie"])
        pdf = df.iloc[::max(1, len(df)//3000)]
        
        with t1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=pdf[thr], name="Gaz", line=dict(color='#2f3b2f', width=2), fill='tozeroy'))
            fig.add_trace(go.Scatter(y=pdf[roll], name="Roll", line=dict(color=ACCENT_LIGHT, width=2)))
            fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
        with t2:
            if has_acc:
                g_series = np.sqrt(pdf[acc_x[0]]**2 + pdf[acc_y[0]]**2 + pdf[acc_z[0]]**2) / 2048.0
                fig_g = go.Figure()
                fig_g.add_trace(go.Scatter(y=g_series, name="G-Force", line=dict(color='#ff3333', width=2)))
                fig_g.add_hline(y=1.0, line_dash="dash", line_color=ACCENT_LIGHT, annotation_text="1G")
                fig_g.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_g, use_container_width=True)
            else: st.info("Brak danych G-Force.")
        with t3:
            fig3 = go.Figure(data=[go.Scatter3d(x=pdf[roll].cumsum()/500, y=pdf[pitch].cumsum()/500, z=np.arange(len(pdf)), mode='lines', line=dict(color=pdf[thr], colorscale='Greens', width=6))])
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
                fig_mot.update_layout(title="Średnie obciążenie", template="plotly_dark", height=250, margin=dict(l=0,r=0,t=40,b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_mot, use_container_width=True)
            if v_col and mode == "Real":
                has_data = True
                f_bat = make_subplots(specs=[[{"secondary_y": True}]])
                f_bat.add_trace(go.Scatter(y=pdf[v_col[0]]/100, name="Napięcie (V)", line=dict(color='#F8FAFC', width=2)), secondary_y=False)
                f_bat.add_trace(go.Scatter(y=pdf[thr], name="Gaz", line=dict(color=ACCENT_LIGHT, width=1), fill='tozeroy', opacity=0.3), secondary_y=True)
                f_bat.update_layout(title="Spadek napięcia a gaz", template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(f_bat, use_container_width=True)
            if not has_data: st.info("Brak danych o zasilaniu w logu.")
            
    return {"jr": float(jr), "jp": float(jp), "health": float(health), "avg_t": float(avg_t), "max_g": float(max_g)}

# ==========================================
# 5. EKRAN LOGOWANIA I REJESTRACJI (REDUX)
# ==========================================
if st.session_state.auth_user is None:
    render_logo()
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Zaloguj się", "Załóż konto"])
        with t1:
            em = st.text_input("Adres e-mail", placeholder="pilot@akademia.pl")
            pw = st.text_input("Hasło", type="password", placeholder="••••••••")
            st.markdown("<div class='cta-btn' style='margin-top: 20px;'>", unsafe_allow_html=True)
            if st.button("Zaloguj się do panelu", use_container_width=True):
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
            rem = st.text_input("Nowy adres e-mail", placeholder="nowy.pilot@akademia.pl")
            rpw = st.text_input("Nowe hasło", type="password", key="reg_pass", placeholder="Co najmniej 6 znaków, wielka litera, znak specjalny")
            rnm = st.text_input("Pseudonim pilota / Imię", placeholder="NiebieskiPilot")
            if st.button("Zarejestruj się", use_container_width=True):
                email_check = supabase.table('konta').select('email').eq('email', rem).execute()
                if email_check.data:
                    st.error("Konto z tym adresem e-mail już istnieje w systemie!")
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
# 6. LOGIKA UPRAWNIEŃ I SESJI
# ==========================================
user_data = supabase.table('konta').select('*').eq('email', st.session_state.auth_user).execute().data[0]
is_admin = (user_data['rola'].lower() == 'admin') or (user_data['email'].lower() == 'admin@fpv.pl')
is_instructor = (user_data['rola'].lower() in ['instruktor', 'admin']) or is_admin

# ==========================================
# 7. PANEL INSTRUKTORA / ADMINA
# ==========================================
if is_instructor:
    render_logo()
    col_nav, col_main = st.columns([1, 3])
    
    with col_nav:
        if is_admin:
            st.markdown(f"<div class='bento-card'>{render_neon_header('ZARZĄDZANIE (ADMIN)')}", unsafe_allow_html=True)
            cadets = supabase.table('konta').select('*').neq('email', user_data['email']).execute().data
        else:
            st.markdown(f"<div class='bento-card'>{render_neon_header('TWOI KURSANCI')}", unsafe_allow_html=True)
            cadets = supabase.table('konta').select('*').eq('rola', 'Kursant').execute().data
            
        if not cadets: st.warning("Brak użytkowników w bazie danych."); st.stop()
        
        display_names = [f"✅ {k['email']}" if k.get('zweryfikowany') is not False else f"❌ {k['email']}" for k in cadets]
        selected_display = st.radio("Wybierz użytkownika:", display_names, label_visibility="collapsed")
        
        selected_email = selected_display[2:] 
        target_data = next(k for k in cadets if k['email'] == selected_email)
        
        st.markdown(f"<br><p class='mono-text'>STAN KONTA: <span style='color: {ACCENT_LIGHT}; font-weight: bold;'>{target_data.get('tokeny', 0)} Tokenów</span></p>", unsafe_allow_html=True)
        dodaj_tok = st.number_input("Zasil", min_value=1, max_value=100, value=5, label_visibility="collapsed")
        st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
        if st.button("ZASIL KONTA", use_container_width=True):
            supabase.table('konta').update({"tokeny": target_data.get('tokeny', 0) + dodaj_tok}).eq('email', selected_email).execute()
            st.toast(f"Zasilono konto {target_data['imie']} o {dodaj_tok} Tokenów.", icon="🟢")
            time.sleep(1)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><p class='mono-text'>DANE DO ANALIZY</p>", unsafe_allow_html=True)
        inst_env = st.selectbox("Środowisko", ["Lot rzeczywisty", "Symulator"])
        inst_ind = st.selectbox("Styl lotu", ["Cinematic / Płynny", "Racing (Wyścigi)", "Freestyle"]) if inst_env == "Lot rzeczywisty" else "Standard"
        inst_skill = st.selectbox("Poziom zaawansowania", ["Początkujący", "Średniozaawansowany", "Ekspert"])
        
        if is_admin:
            st.markdown("<br><p class='mono-text'>ADMIN ODPRAWA</p>", unsafe_allow_html=True)
            if target_data.get('zweryfikowany') is False:
                if st.button("✅ Weryfikuj konto", use_container_width=True):
                    supabase.table('konta').update({"zweryfikowany": True}).eq('email', selected_email).execute()
                    st.toast("Konto zweryfikowane.", icon="🟢")
                    time.sleep(1)
                    st.rerun()
            if target_data['rola'].lower() == 'kursant':
                if st.button("🌟 Nadaj Rangę Instruktora", use_container_width=True):
                    supabase.table('konta').update({"rola": "Instruktor"}).eq('email', selected_email).execute()
                    st.rerun()
            elif target_data['rola'].lower() == 'instruktor':
                if st.button("🔻 Odbierz Rangę Instruktora", use_container_width=True):
                    supabase.table('konta').update({"rola": "Kursant"}).eq('email', selected_email).execute()
                    st.rerun()

        st.markdown("<br><p class='mono-text'>OPCJE</p>", unsafe_allow_html=True)
        if st.button("Wyloguj się", use_container_width=True): st.session_state.auth_user = None; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_main:
        st.markdown(f"<h2>Profil: <span style='color:{ACCENT_LIGHT}; text-shadow:0 0 10px {ACCENT_LIGHT};'>{target_data['imie']} ({target_data['rola']})</span></h2>", unsafe_allow_html=True)
        loty = [z for z in target_data.get('zadania', []) if isinstance(z, dict) and 'ocena' in z and z.get('type') != 'Mechanik AI']
        avg_score = sum(z['ocena'] for z in loty) / len(loty) if loty else 0
        
        st.markdown("<div class='bento-card' style='margin-bottom: 30px;'>", unsafe_allow_html=True)
        cm1, cm2 = st.columns(2)
        cm1.metric("Wykonane Analizy", len(loty))
        cm2.metric("Średnia Ocena AI", f"{avg_score:.1f}/10")
        
        if len(loty) > 1:
            dates = [z['data'] for z in loty]
            scores = [z['ocena'] for z in loty]
            fig_prog_inst = go.Figure()
            fig_prog_inst.add_trace(go.Scatter(x=dates, y=scores, mode='lines+markers', name='Ocena AI', line=dict(color=ACCENT_LIGHT, width=2)))
            fig_prog_inst.update_layout(title="Historia ocen (im wyżej, tym lepiej)", template="plotly_dark", height=250, margin=dict(l=0,r=0,t=40,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_prog_inst, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        vid_link = st.text_input("Opcjonalny link do nagrania (YouTube)", placeholder="https://youtube.com/...")
        log_file = st.file_uploader("Zdekoduj plik z czarnej skrzynki (BBL/CSV)", type=['bbl', 'csv'], label_visibility="collapsed")

        df_active = None
        if log_file:
            # NOWA LOGIKA DEKODOWANIA I WYBORU LOTU (INSTRUKTOR)
            valid_csvs = decode_file(log_file.getvalue(), log_file.name)
            if not valid_csvs:
                st.warning("⚠️ Ten plik nie zawiera poprawnych danych lotu (jest pusty lub to był tylko szybki test uzbrojenia silników).")
            else:
                if len(valid_csvs) > 1:
                    options = {c: f"Zapis nr {i+1} (Rozmiar: {os.path.getsize(c)//1024} KB)" for i, c in enumerate(valid_csvs)}
                    selected_csv = st.selectbox("Wykryto kilka lotów w pliku:", list(options.keys()), format_func=lambda x: options[x])
                else: selected_csv = valid_csvs[0]
                    
                with st.status("Ekstrakcja danych telemetrycznych...", expanded=False) as status:
                    df_active = pd.read_csv(selected_csv)
                    status.update(label="Dane zdekodowane.", state="complete", expanded=False)

        if df_active is not None:
            stats = render_terminal_hud(df_active, mode="Real" if inst_env=="Lot rzeczywisty" else "Sim", premium=True)
            st.markdown("<br>", unsafe_allow_html=True)
            
            # WYSWIETLANIE STATUSU AI
            avail, wait = get_ai_capacity()
            if avail > 0: st.markdown(f"<div style='text-align: right; color: #8cbf8c;'>🟢 Sieć AI Gotowa | {avail}/15 wolnych kanałów</div>", unsafe_allow_html=True)
            else: st.markdown(f"<div style='text-align: right; color: #ef4444;'>🔴 Sieć AI Przeciążona | Następne okno za: {int(wait)} s</div>", unsafe_allow_html=True)
            
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button(" GENERUJ WSKAZÓWKI AI"):
                if init_ai():
                    prompt = f"Instruktor FPV Academy. Kursant: {target_data['imie']}, Poziom: {inst_skill}, Styl: {inst_ind}. Wygeneruj JSON: {{\"ocena\": 8, \"diagnoza\": \"...\", \"zadanie\": \"...\"}}"
                    raw = call_ai_safe(prompt, is_json=True)
                    try:
                        js = json.loads(raw.replace("```json","").replace("```","").strip())
                        if js.get('ocena') == 0 and "Przeciążenie" in js.get('diagnoza', ''):
                            st.error(js.get('diagnoza'))
                        else:
                            st.session_state.instructor_draft = f"### Analiza lotu: {inst_ind}\n**OCENA LOTU:** {js['ocena']}/10\n\n**WSKAZÓWKI TRENERA:**\n{js['diagnoza']}\n\n**ZADANIE NA NASTĘPNY TRENING:**\n{js['zadanie']}"
                            st.session_state.temp_metrics = stats
                    except: st.error("Krytyczny błąd połączenia z modułem AI.")
            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.instructor_draft:
            final_rep = st.text_area("Edytuj raport przed wysłaniem do bazy", value=st.session_state.instructor_draft, height=250)
            if st.button("ZATWIERDŹ I WYŚLIJ RAPORT DO PILOTA"):
                match = re.search(r"OCENA LOTU:\s*(\d+)/10", final_rep)
                score = int(match.group(1)) if match else 5
                new_record = {"data": datetime.now().strftime("%Y-%m-%d %H:%M"), "ocena": score, "raport": final_rep, "wideo": vid_link, "type": inst_ind, "premium": True, "stats": st.session_state.temp_metrics}
                
                history = target_data.get('zadania', [])
                history.append(new_record)
                supabase.table('konta').update({"zadania": history[-10:]}).eq('email', selected_email).execute()
                st.session_state.instructor_draft = None
                st.toast("Wysłano raport.", icon="✅")
                time.sleep(1)
                st.rerun()
            
        st.markdown("<br><p class='mono-text'>OSTATNIE ZADANIA PILOTA</p>", unsafe_allow_html=True)
        for z in reversed(loty):
            if isinstance(z, dict):
                with st.expander(f"📄 {z.get('data')} | Ocena: {z.get('ocena')}/10"):
                    st.markdown(z.get('raport'))

# ==========================================
# 8. PANEL KURSANTA (THE MASTERPIECE UX)
# ==========================================
else:
    # side-menu kursanta
    with st.sidebar:
        render_logo()
        st.write(render_neon_header(f"Witaj, <br><span style='font-size:1.5em; text-shadow: 0 0 15px {ACCENT_LIGHT};'>{user_data['imie']}</span>"))
        st.write("<br><hr style='border-color: rgba(51,102,0,0.2);'><br>", unsafe_allow_html=True)
        st.metric("DOSTĘPNE TOKENY", user_data.get('tokeny', 0))
        st.write("<br>", unsafe_allow_html=True)
        
        st.markdown(f"""
            <div class='stAlert' style='{get_bento_card_style()} padding: 15px;'>
            <p style='color: {TEXT_NEON}; font-size: 0.9em; margin:0;'>💡 Aby odświeżyć dane od Instruktora, użyj poniższego przycisku serwera.</p>
            </div><br>
        """, unsafe_allow_html=True)
        
        if st.button("🔄 Synchronizuj z Bazy Danych", use_container_width=True): st.rerun()
        st.write("<br><br>", unsafe_allow_html=True)
        if st.button("Wyloguj się z platformy", use_container_width=True): st.session_state.auth_user = None; st.rerun()

    # launcher launchpada
    if st.session_state.flow_state == 'launchpad':
        
        # NEONOWY NAGŁÓWEK GŁÓWNY (GLOBAL GIGANT STYLE)
        st.markdown(f"<div style='text-align:center; padding-bottom:3rem;'><p class='mono-text' style='letter-spacing:0.3em;'>THE ULTIMATE TRAINING GROUND</p><h1 style='font-size:5rem; text-shadow: 0 0 25px {ACCENT_LIGHT};'>FPV AI Academy</h1></div>", unsafe_allow_html=True)
        
        # DYNAMICZNE TŁO SYMULACYJNE W TLE
        col_bg, col_m, col_b = st.columns([0.1, 10, 0.1])
        with col_m:
            with st.container():
                render_live_background()

        tab_main, tab_rank, tab_workshop = st.tabs(["🚀 Dostępne Ścieżki", "🏆 Ranking Globalny", "🛠️ Warsztat i Wiedza"])
        
        with tab_main:
            col_d, col_r = st.columns(2)
            with col_d:
                st.markdown(f"<div class='bento-card' style='height:100%; border-color:{ACCENT_LIGHT};'><h3>🚁 ANALIZA LOTU RZECZYWISTEGO</h3><p class='mono-text'>Import z plików czarnej skrzynki (.BBL)</p></div>", unsafe_allow_html=True)
                col_m1, col_r1, col_f1 = st.columns(3)
                if col_m1.button("Cinematic"): st.session_state.industry_select="Cinematic / Płynny"; st.session_state.env_select="Real"; st.rerun()
                if col_r1.button("Wyścigi (Race)"): st.session_state.industry_select="Racing"; st.session_state.env_select="Real"; st.rerun()
                if col_f1.button("Freestyle"): st.session_state.industry_select="Freestyle"; st.session_state.env_select="Real"; st.rerun()
            with col_r:
                st.markdown(f"<div class='bento-card' style='height:100%;'><h3>🎮 ANALIZA SYMULATORA</h3><p class='mono-text'>Import z plików CSV (Velocidrone/Liftoff)</p></div>", unsafe_allow_html=True)
                st.markdown("<br><br><br>", unsafe_allow_html=True)
                if st.button("URUCHOM ANALIZĘ SYMULATORA", use_container_width=True): 
                    st.session_state.industry_select="Symulator treningowy"; st.session_state.env_select="Sim"; st.rerun()
            
            if st.session_state.industry_select:
                st.write("<br><br>", unsafe_allow_html=True)
                st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
                st.write(render_neon_header("WYBÓR POZIOMU DOŚWIADCZENIA AI"))
                skill = st.select_slider("Wybierz poziom do oceny:", options=["Początkujący", "Średniozaawansowany", "Ekspert"], value=st.session_state.skill_select, label_visibility="collapsed")
                st.session_state.skill_select = skill
                st.write("<br>", unsafe_allow_html=True)
                st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
                if st.button("PRZEJDŹ DO WGRYWANIA LOGU", use_container_width=True): st.session_state.flow_state = 'upload'; st.rerun()
                st.markdown("</div></div>", unsafe_allow_html=True)

            # HISTORIA LOTÓW KURSANT (Z NEONOWYM SZLIFEM)
            st.write("<br><br>", unsafe_allow_html=True)
            st.write(render_neon_header("OSTATNIE RAPORTY I WSKAZÓWKI"))
            valid_zadania = [z for z in user_data.get('zadania', []) if isinstance(z, dict)]
            
            for z in reversed(valid_zadania):
                if z.get('type') == 'Mechanik AI':
                    with st.expander(f"🤖 {z.get('data')} | Warsztat: Diagnoza sprzętu"):
                        st.markdown(z.get('raport'))
                else:
                    color = "#ef4444" if z.get('ocena') < 5 else ACCENT_LIGHT
                    with st.expander(f"📄 {z.get('data')} | {z.get('type','Lot')} | Ocena: <span style='color:{color}; font-weight:bold;'>{z.get('ocena')}/10</span>", unsafe_allow_html=True):
                        st.markdown(z.get('raport'))

        with tab_rank:
            st.markdown(f"<h2>Top Piloci FPV Academy</h2>", unsafe_allow_html=True)
            all_cadets = supabase.table('konta').select('imie, zadania').eq('rola', 'Kursant').execute().data
            leaderboard = []
            for k in all_cadets:
                zad = k.get('zadania', [])
                valid_zad = [z for z in zad if isinstance(z, dict) and 'ocena' in z and z.get('type') != 'Mechanik AI']
                if valid_zad:
                    avg_ocena = sum(z['ocena'] for z in valid_zad) / len(valid_zad)
                    max_g = max((z.get('stats', {}).get('max_g', 0) for z in valid_zad), default=0)
                    leaderboard.append({"Pilot": k['imie'], "Średnia Ocena": round(avg_ocena, 1), "Max Przeciążenie (G)": round(max_g, 1), "Ukończone Analizy": len(valid_zad)})
            
            if leaderboard:
                df_leaderboard = pd.DataFrame(leaderboard).sort_values(by="Średnia Ocena", ascending=False).reset_index(drop=True)
                df_leaderboard.index += 1
                st.dataframe(df_leaderboard, use_container_width=True)
            else: st.info("Brak wystarczających danych do rankingu.")

        with tab_workshop:
            st.markdown(f"<h2>🛠️ Warsztat i Wiedza FPV Academy</h2>", unsafe_allow_html=True)
            w_mech, w_vtx, w_dict = st.tabs(["🤖 Wirtualny Mechanik AI", "📡 Ściągawka VTX", "📚 Słowniczek"])
            
            with w_mech:
                st.markdown("### Sztuczna Inteligencja Serwisowa")
                mech_query = st.text_area("Opisz problem ze sprzętem:", placeholder="Np. Dron po zrobieniu flipa na chwilę traci moc i dziwnie wyje...")
                
                # STATUS AI
                avail, wait = get_ai_capacity()
                if avail > 0: st.markdown(f"<div style='text-align: right; color: #8cbf8c;'>🟢 Sieć Gotowa | {avail}/15 wolnych kanałów</div>", unsafe_allow_html=True)
                else: st.markdown(f"<div style='text-align: right; color: #ef4444;'>🔴 Sieć Przeciążona | Następne okno za: {int(wait)} s</div>", unsafe_allow_html=True)
                
                st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
                if st.button("POPROŚ O DIAGNOZĘ MECHANIKA"):
                    if mech_query and init_ai():
                        with st.spinner("Nasz mechanik AI analizuje problem..."):
                            prompt = f"Serwisant dronów FPV Academy. Krótko pomóż rozwiązać problem w punktach. Problem: {mech_query}"
                            mech_resp = call_ai_safe(prompt, is_json=False)
                            if "Przeciążenie" not in mech_resp and "Błąd" not in mech_resp:
                                supabase.table('konta').update({"zadania": valid_zadania + [{"data": datetime.now().strftime("%Y-%m-%d %H:%M"), "type": "Mechanik AI", "raport": f"**Pytanie:** {mech_query}\n\n**Diagnoza Mechanika:**\n{mech_resp}"}]}).eq('email', user_data['email']).execute()
                                st.success("Wskazówki zostały zapisane w historii lotów:")
                            else:
                                st.warning(mech_resp)
                            st.markdown(mech_resp)
                st.markdown("</div>", unsafe_allow_html=True)

            with w_vtx:
                # TUTAJ WRÓCIŁA CAŁA DZIAŁAJĄCA TABELA VTX
                st.markdown("### Pełna Macierz Częstotliwości VTX (5.8 GHz)")
                vtx_matrix = pd.DataFrame({
                    "Pasmo": ["Band A", "Band B", "Band E (Boscam)", "Fatshark (F)", "Raceband (R)"],
                    "CH 1": [5865, 5733, 5705, 5740, 5658], "CH 2": [5845, 5752, 5685, 5760, 5695], "CH 3": [5825, 5771, 5665, 5780, 5732], "CH 4": [5805, 5790, 5645, 5800, 5769],
                    "CH 5": [5785, 5809, 5885, 5820, 5806], "CH 6": [5765, 5828, 5905, 5840, 5843], "CH 7": [5745, 5847, 5925, 5860, 5880], "CH 8": [5725, 5866, 5945, 5880, 5917]
                }).set_index('Pasmo')
                
                pilots_count = st.slider("Ilu pilotów leci jednocześnie?", 1, 8, 4)
                optimal_freqs = {1:[5658], 2:[5658,5917], 3:[5658,5769,5917], 4:[5658,5732,5843,5917], 5:[5645,5705,5769,5843,5917], 6:[5645,5695,5760,5800,5860,5917], 7:[5645,5695,5740,5780,5820,5860,5917], 8:[5645,5685,5725,5760,5800,5840,5880,5917]}
                active_freqs = optimal_freqs[pilots_count]
                
                def highlight_active(row):
                    return ['background-color: #336600; color: white; font-weight: bold' if val in active_freqs else '' for val in row]
                
                st.dataframe(vtx_matrix.style.apply(highlight_active, axis=1), use_container_width=True)
                
                freq_to_name = {5658:"R1", 5917:"R8", 5769:"R4", 5732:"R3", 5843:"R6", 5645:"E4", 5705:"E1", 5695:"R2", 5760:"F2", 5800:"F4", 5860:"F7", 5740:"F1", 5780:"F3", 5820:"F5", 5685:"E2", 5725:"A8", 5840:"F6", 5880:"R7"}
                ch_names = [freq_to_name.get(f, str(f)) for f in active_freqs]
                st.success(f"Zalecane ułożenie kanałów dla {pilots_count} pilotów: **{', '.join(ch_names)}**")

            with w_dict:
                # TUTAJ WRÓCIŁA CAŁA DZIAŁAJĄCA TREŚĆ SŁOWNICZKA
                st.markdown("### Słowniczek Techniczny Betaflight")
                with st.expander("P-I-D (Proportional, Integral, Derivative)"): 
                    st.write("**P (Proportional)** - Szybkość reakcji drona na drążki. Zbyt niskie = dron 'pływa', zbyt wysokie = szybkie wibracje (oscylacje).\n\n**I (Integral)** - Trzymanie zadanego kąta. Pomaga dronowi nie ulegać wpływom wiatru i odchyleniom środka ciężkości baterii.\n\n**D (Derivative)** - 'Amortyzator' dla wartości P. Zapobiega przelatywaniu poza cel (overshoot) po ostrym manewrze. Zbyt wysokie D powoduje mocne grzanie silników.")
                with st.expander("Rates (RC Rate, Super Rate/Expo)"):
                    st.write("**RC Rate** - Czułość na samym środku drążka. Im wyższa, tym szybciej dron reaguje na najdrobniejsze ruchy palcami.\n\n**Super Rate / Expo** - Czułość na krawędziach wychylenia drążka. Pozwala na super szybkie flipy i rolle, zachowując przy tym miękki środek.")
                with st.expander("Propwash (Oscylacje po zejściu)"):
                    st.write("Wibracje drona, które pojawiają się, gdy gwałtownie zawracasz we własne 'brudne powietrze' wyrzucone wcześniej przez śmigła. Zjawisko to redukujemy m.in. optymalizując wartość 'D'.")

    # upload flow
    elif st.session_state.flow_state == 'upload':
        st.markdown(f"<h2>ANALIZA DANYCH: <span style='color: {ACCENT_LIGHT}; text-shadow:0 0 10px {ACCENT_LIGHT};'>{st.session_state.industry_select.upper()} ({st.session_state.env_select})</span></h2>", unsafe_allow_html=True)
        if st.button("← Wróć do launchpada"): 
            st.session_state.flow_state = 'launchpad'; st.session_state.env_select = None; st.session_state.industry_select = None; st.rerun()

        st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
        st.write(render_neon_header("WYBÓR PAKIETU ANALITYCZNEGO"))
        tier = st.radio("Poziom szczegółowości:", ["Standardowy (1 Token)", "Premium + G-Force (2 Tokeny)"], label_visibility="collapsed")
        cost = 1 if "Standardowy" in tier else 2
        st.markdown(f"<p style='color:{TEXT_NEON};'>Środki: <b>{user_data.get('tokeny', 0)} Tokenów</b></p>", unsafe_allow_html=True)
        u_log = st.file_uploader("Upuść plik z logami", type=['bbl', 'csv'], label_visibility="collapsed")
        
        if u_log:
            # NOWA LOGIKA DEKODOWANIA I WYBORU LOTU (KURSANT)
            valid_csvs = decode_file(u_log.getvalue(), u_log.name)
            if not valid_csvs:
                st.warning("⚠️ Ten plik nie zawiera poprawnych danych lotu (jest pusty lub to był tylko szybki test uzbrojenia silników).")
            else:
                if len(valid_csvs) > 1:
                    options = {c: f"Zapis nr {i+1} (Rozmiar: {os.path.getsize(c)//1024} KB)" for i, c in enumerate(valid_csvs)}
                    selected_csv = st.selectbox("Wykryto kilka lotów w pliku:", list(options.keys()), format_func=lambda x: options[x])
                else: selected_csv = valid_csvs[0]
                    
                render_ai_status()
                st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
                if st.button(f"ROZPOCZNIJ ANALIZĘ AI (-{cost} TOKENÓW)", use_container_width=True):
                    if user_data.get('tokeny', 0) >= cost:
                        with st.status("Ekstrakcja danych i łączenie się z siecią AI...", expanded=True) as status:
                            df = pd.read_csv(selected_csv)
                            stats = render_terminal_hud(df, mode=st.session_state.env_select, premium=(cost==2))
                            
                            if init_ai():
                                prompt = f"Trener FPV Academy. Uczeń: {user_data['imie']}, Poziom: {st.session_state.skill_select}. Wygeneruj JSON: {{\"ocena\": 8, \"diagnoza\": \"...\", \"zadanie\": \"...\"}}"
                                raw_ai = call_ai_safe(prompt, is_json=True)
                                try:
                                    js = json.loads(raw_ai.replace("```json","").replace("```","").strip())
                                    if js.get('ocena') == 0 and "Przeciążenie" in js.get('diagnoza', ''):
                                        st.error(js.get('diagnoza'))
                                    else:
                                        tag = "RAPORT PREMIUM" if cost == 2 else "RAPORT STANDARDOWY"
                                        # NOWY DZIENNIK ZADAN DLA KURSANTÓW
                                        user_history = target_data.get('zadania', [])
                                        user_history.append({"data": datetime.now().strftime("%Y-%m-%d %H:%M"), "ocena": js['ocena'], "raport": f"### {tag}\n**OCENA AI:** {js['ocena']}/10\n\n**DIAGNOZA:**\n{js['diagnoza']}\n\n**ZADANIE OD TRENERA AI:**\n{js['zadanie']}", "type": st.session_state.industry_select})
                                        supabase.table('konta').update({"zadania": user_history[-10:], "tokeny": user_data['tokeny'] - cost}).eq('email', user_data['email']).execute()
                                        
                                        status.update(label="Wyniki zapisane.", state="complete", expanded=False)
                                        time.sleep(1)
                                        st.session_state.flow_state = 'launchpad'; st.rerun()
                                except: st.error("Błąd parsowania AI lub sieć jest przeciążona.")
                    else: st.error("Niewystarczająca liczba Tokenów.")
                st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
