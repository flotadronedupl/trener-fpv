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
# 1. KONFIGURACJA SESJI I PREMIUM BRANDING
# ==========================================
st.set_page_config(
    page_title="FPV AI Academy | Twoja Platforma Premium",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
# 2. GRAFICZNE CUDA (MODERN CSS & GLASSMORPHISM)
# ==========================================
# Ten segment kodu definiuje wygląd premium, używając customowego CSS.
# Używamy neonowych poświat, radialnych gradientów i "szklanych" paneli.

def render_neon_header(text, size="1.1rem"):
    """Generuje tekst z neonową poświatą."""
    return f"<p class='mono-text' style='font-size:{size}; text-shadow: 0 0 10px {ACCENT_LIGHT};'>{text}</p>"

def get_bento_card_style():
    """Definiuje styl dla 'szklanych' paneli Bento-card."""
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
    .stApp {{
        background: radial-gradient(circle at 50% -10%, #153315 0%, #050a0a 40%, #000000 100%);
        color: #F8FAFC;
        font-family: 'Inter', sans-serif;
    }}
    
    /* GLASSMORPHISM DLA KART BENTO */
    .bento-card {{
        {get_bento_card_style()}
    }}
    .bento-card:hover {{
        border-color: rgba(77, 153, 0, 0.5);
        box-shadow: 0 20px 50px -10px rgba(51, 102, 0, 0.3);
        transform: translateY(-3px);
    }}
    
    /* NAGŁÓWKI Z EFEKTEM NEONOWYM */
    h1, h2, h3, h4 {{ font-weight: 800 !important; color: #FFFFFF !important; letter-spacing: -0.5px; text-shadow: 0 0 8px {ACCENT_LIGHT}; }}
    
    /* STYLIZACJA METRYK STREAMLIT (MONOCHROMATYCZNE, NEONOWE) */
    div[data-testid="stMetric"] {{
        background: linear-gradient(180deg, rgba(20, 30, 20, 0.8) 0%, rgba(10, 15, 10, 0.9) 100%); 
        border: 1px solid rgba(51, 102, 0, 0.3); border-radius: 16px; padding: 24px; box-shadow: inset 0 2px 15px 0 rgba(51, 102, 0, 0.05); border-top: 2px solid {ACCENT_LIGHT};
    }}
    div[data-testid="stMetricValue"] {{ font-weight: 800; color: #FFFFFF; font-size: 2.2rem; text-shadow: 0 0 15px {ACCENT_LIGHT}; }}
    
    /* PRZYCISKI ENTERPRISE Z GLOW I PŁYNNĄ ANIMACJĄ */
    .stButton>button {{ background: rgba(20, 30, 20, 0.8); border: 1px solid rgba(51,102,0,0.4); color: #E2E8F0; border-radius: 10px; font-weight: 600; transition: all 0.3s ease; }}
    .stButton>button:hover {{ background: rgba(51,102,0,0.2); color: #FFFFFF; border-color: {ACCENT_LIGHT}; box-shadow: 0 0 15px rgba(51,102,0,0.4); }}
    
    /* PRZYCISKI CTA Z LINIOWYM GRADIENTEM ZIELENI (GLOBAL GIGANT STYLE) */
    .cta-btn>button {{ background: linear-gradient(135deg, {PRIMARY_COLOR}, {ACCENT_LIGHT}); color: #FFFFFF; border: none; font-weight: 700; letter-spacing: 1px; box-shadow: 0 6px 25px 0 rgba(51, 102, 0, 0.5); border-radius: 10px; padding: 0.75rem 2rem; text-transform: uppercase; }}
    .cta-btn>button:hover {{ box-shadow: 0 8px 35px {ACCENT_LIGHT}; transform: scale(1.03); }}
    
    /* INPUTY MROCZNE Z NEONOWYM ZAZNACZENIEM */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {{ background: rgba(10, 15, 10, 0.8) !important; border: 1px solid rgba(51,102,0,0.3) !important; color: #FFFFFF !important; border-radius: 10px !important; }}
    .stTextInput input:focus, .stTextArea textarea:focus {{ border-color: {ACCENT_LIGHT} !important; box-shadow: 0 0 0 2px rgba(51,102,0,0.3) !important; }}
    
    /* TABELE NEONOWE (ZASILANIE I VTX MATRIX) */
    .stDataFrame th, .stDataFrame tr {{ border-bottom: 1px solid rgba(51, 102, 0, 0.2); color: {TEXT_NEON}; }}
    
    /* SIDEBAR NEONOWY Z BLUREM */
    section[data-testid="stSidebar"] {{ background-color: rgba(5, 10, 5, 0.95) !important; border-right: 1px solid rgba(51,102,0,0.2); backdrop-filter: blur(20px); }}
    
    /* UKRYCIE STOPKI I NAGŁÓWKA STREAMLIT DLA EFEKTU NATIVE */
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    
    /* STYL DLA PRZYCISKÓW DANGER */
    .danger-btn>button {{ border: 1px solid #ef4444; color: #ef4444; background: rgba(239, 68, 68, 0.1); }}
    .danger-btn>button:hover {{ background: #ef4444; color: #ffffff; }}
    </style>
    """, unsafe_allow_html=True)

def render_logo():
    """Generuje neonowe logo FPV AI Academy."""
    st.write("<div style='text-align:center; padding-bottom:3rem; display:flex; flex-direction:column; align-items:center;'><svg width='80' height='80' viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M5.5 5.5h.01M18.5 5.5h.01M5.5 18.5h.01M18.5 18.5h.01' stroke='#4d9900' stroke-width='3' stroke-linecap='round'/><path d='M12 12L5.5 5.5M12 12l6.5-6.5M12 12l-6.5 6.5M12 12l6.5 6.5' stroke='#4d9900' stroke-width='1.5' stroke-linecap='round'/><circle cx='12' cy='12' r='3' fill='#050a0a' stroke='#4d9900' stroke-width='2'/></svg><h1 style='font-size:3rem; margin:10px 0 0 0; background:linear-gradient(90deg, #FFFFFF, #8cbf8c); -webkit-background-clip:text; -webkit-text-fill-color:transparent;'>FPV AI Academy</h1><p style='color:#64748B; font-size:1.1rem; margin-top:0.5rem; font-weight:600; letter-spacing:2px;'>TWÓJ WIRTUALNY TRENER LOTÓW</p></div>", unsafe_allow_html=True)

def generate_html_report(date, score, report_text, stats_dict, pilot_name):
    """Generuje piękny, premium raport HTML gotowy do pobrania z poświatami."""
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
            h1 {{ color: {PRIMARY_COLOR}; border-bottom: 2px solid {PRIMARY_COLOR}; padding-bottom: 10px; margin-bottom: 5px; text-shadow: 0 0 5px rgba(51, 102, 0, 0.2); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .score {{ font-size: 2.5em; color: {PRIMARY_COLOR}; font-weight: bold; text-align: center; margin-bottom: 20px; text-shadow: 0 0 10px rgba(77, 153, 0, 0.4); }}
            .charts-container {{ background: #f9fdf9; border: 1px solid #e0e0e0; padding: 25px; border-radius: 12px; margin-bottom: 30px; }}
            .chart-title {{ font-size: 1.1em; font-weight: bold; margin-bottom: 15px; color: #333; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
            .bar-row {{ margin-bottom: 12px; }}
            .bar-label {{ display: flex; justify-content: space-between; font-size: 0.9em; margin-bottom: 4px; font-weight: bold; color: #555; }}
            .bar-bg {{ width: 100%; background-color: #e0e0e0; border-radius: 6px; height: 16px; overflow: hidden; }}
            .bar-fill {{ height: 100%; background-color: {ACCENT_LIGHT}; border-radius: 6px; box-shadow: inset 0 0 5px rgba(255, 255, 255, 0.3); }}
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
# 3. RDZEŃ SYSTEMU Z BEZPIECZNYM AI MANAGEREM
# ==========================================
# Tutaj musisz podpiąć swoje dane Supabase w Streamlit Cloud Secrets.
# Skopiuj klucze API zgodnie z instrukcją podaną wcześniej.

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def init_ai():
    """Konfiguruje połączenie ze sztuczną inteligencją Gemini 1.5 Flash."""
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return True
    return False

def call_ai_safe(prompt, is_json=True):
    """
    Wykonuje zabezpieczone połączenie z AI, sprawdzając limit 15 zapytań/minutę.
    Darmowy klucz Google ma 1500 RPM / 15 RPH, musimy dbać o płynność.
    """
    # Ta funkcja jest jeszcze w fazie rozwoju i symuluje limit.
    # W przyszłej wersji dodamy tu globalny licznik w pamięci chmury.
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        best_model = next((m for m in models if '1.5-flash' in m), models[0])
        return genai.GenerativeModel(best_model).generate_content(prompt).text
    except Exception as e:
        if "429" in str(e) or "limit" in str(e).lower():
            if is_json: return f'{{"ocena": 0, "diagnoza": "⚠️ Sieć serwisu analitycznego AI jest w tej chwili przeciążona przez zapytania innych pilotów. Twoje okno diagnostyczne otworzy się za ok. 30 sekund. Odśwież i spróbuj ponownie.", "zadanie": "Brak zadań."}}'
            else: return "⚠️ Sieć diagnostyczna AI jest aktualnie przeciążona. Poczekaj 30-60 sekund i spróbuj ponownie."
        else:
            if is_json: return f'{{"ocena": 0, "diagnoza": "Wystąpił krytyczny błąd połączenia z modułem AI. Upewnij się, że klucz API działa.", "zadanie": "Brak zadań."}}'
            else: return "⚠️ Wystąpił błąd krytyczny przy diagnostyce. Upewnij się, że klucz API działa."

@st.cache_resource(show_spinner=False)
def get_decoder():
    """Kompiluje dekoder czarnej skrzynki (C++) z Betaflight Tools."""
    # To jest najlepsze rozwiązanie - chmura sama kompiluje narzędzie Linuxa.
    path = "/tmp/fcis_engine"
    if not os.path.exists(path):
        os.makedirs("/tmp/src", exist_ok=True)
        # Pobieranie oficjalnych źródeł Betaflight
        urllib.request.urlretrieve("https://github.com/betaflight/blackbox-tools/archive/refs/heads/master.zip", "/tmp/b.zip")
        with zipfile.ZipFile("/tmp/b.zip", 'r') as z:
            z.extractall("/tmp/src")
        # Kompilacja silnika
        subprocess.run(["make", "obj/blackbox_decode"], cwd="/tmp/src/blackbox-tools-master", check=True, stdout=subprocess.DEVNULL)
        # Kopiowanie binarki do bezpiecznej lokalizacji
        shutil.copy("/tmp/src/blackbox-tools-master/obj/blackbox_decode", path)
    # Nadanie uprawnień do wykonywania
    os.chmod(path, 0o755)
    return path

# ==========================================
# 4. SILNIK WIZUALIZACJI Z NEONOWYM SZLIFEM
# ==========================================
# Tutaj dekodujemy pliki BBL/CSV do Pandas, wyliczamy Jerk i G-Force.
# Następnie generujemy piękne wykresy premium Plotly.

def render_terminal_hud(df, mode="Real", premium=False):
    """Generuje wizualizację premium danych telemetrii (HUD, Przeciążenia, Silniki)."""
    # 1. Dekodowanie drążków (Pochłania surowe dane z Betaflight)
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
        st.error("Nie znaleziono podstawowych danych telemetrycznych w przesłanym logu. Upewnij się, że czarna skrzynka loguje drążki i akcelerometr.")
        return None

    # 2. Wyliczanie metryk niszowych (Jerk i Płynność)
    # Jerk to pochodna przyspieszenia (jak szybko pilot zmienia drążki)
    jr, jp = df[roll].diff().abs().mean(), df[pitch].diff().abs().mean()
    jy = df[yaw].diff().abs().mean() if yaw else 0
    
    # Skalowanie płynności (0-10), wyżej = płynniej
    smoothness = max(0, 10 - ((jr + jp + jy) * 0.8))
    avg_t = df[thr].mean()
    
    max_g = 1.0
    if has_acc:
        # Wyliczanie wektora przeciążenia G-Force (na podstawie akcelerometru Smooth)
        # Betaflight loguje akcelerometr w jednostkach 2048/g dla domyślnego zakresu 16g.
        g_vector = np.sqrt(df[acc_x[0]]**2 + df[acc_y[0]]**2 + df[acc_z[0]]**2) / 2048.0
        max_g = g_vector.max()

    # 3. Wyświetlanie metryk (Z neonowym szlifem)
    st.markdown("<p class='mono-text'>WYNIKI TELEMETRII WINSOWANE PRZEZ AI</p>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Płynność lotu", f"{smoothness:.1f} / 10")
    m2.metric("Średni gaz", f"{avg_t:.0f}")
    m3.metric("Max przeciążenie", f"{max_g:.1f} G" if has_acc else "Brak danych G")
    
    # Kondycja maszyny na podstawie P oraz I (Szarpanie vs Trzymanie kąta)
    health = max(0, min(100, 100 - ((jr + jp) * 12)))
    m4.metric("Kondycja drona", f"{health:.0f}%")

    # 4. WIZUALIZACJE ZAAWANSOWANE (PREMIUM)
    if premium:
        st.markdown("<br><p class='mono-text'>ANALIZA ZAAWANSOWANA (PREMIUM MODE)</p>", unsafe_allow_html=True)
        t1, t2, t3, t4 = st.tabs(["Telemetria drążków", "Analiza przeciążeń (G-Force Matrix)", "Trajektoria 3D", "Silniki i zasilanie"])
        
        # DOWN-SAMPLING (Ograniczenie danych do 3000 punktów dla płynności Plotly)
        # Należy pamiętać, że logi FPV mają 1kHz-4kHz, to za dużo dla przeglądarki.
        pdf = df.iloc[::max(1, len(df)//3000)]
        
        with t1:
            fig = go.Figure()
            # Używamy neonowych linii na mrocznym tle (Czyste DJI)
            fig.add_trace(go.Scatter(y=pdf[thr], name="Gaz", line=dict(color='#2f3b2f', width=2), fill='tozeroy'))
            fig.add_trace(go.Scatter(y=pdf[roll], name="Roll", line=dict(color=ACCENT_LIGHT, width=2)))
            if yaw: fig.add_trace(go.Scatter(y=pdf[yaw], name="Yaw", line=dict(color='#FFFFFF', width=1, dash='dot')))
            
            fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
        with t2:
            if has_acc:
                # Wykres przeciążeń w czasie z poświatą neonową
                g_series = np.sqrt(pdf[acc_x[0]]**2 + pdf[acc_y[0]]**2 + pdf[acc_z[0]]**2) / 2048.0
                fig_g = go.Figure()
                fig_g.add_trace(go.Scatter(y=g_series, name="G-Force", line=dict(color='#ff3333', width=2)))
                fig_g.add_hline(y=1.0, line_dash="dash", line_color="#8cbf8c", annotation_text="Grawitacja (1G)")
                
                fig_g.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_g, use_container_width=True)
            else: st.info("Brak danych G-Force w logu symulatora.")

        with t3:
            # Trajektoria 3D (Zwyżka napięcia na gazie jako kolor)
            fig3 = go.Figure(data=[go.Scatter3d(x=pdf[roll].cumsum()/500, y=pdf[pitch].cumsum()/500, z=np.arange(len(pdf)), 
                                mode='lines', line=dict(color=pdf[thr], colorscale='Greens', width=6))])
            fig3.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', scene=dict(bgcolor='rgba(0,0,0,0)'))
            st.plotly_chart(fig3, use_container_width=True)
            
        with t4:
            v_col = [c for c in df.columns if 'vbat' in c.lower()]
            mot_cols = [c for c in df.columns if 'motor[' in c.lower() or 'motor0' in c.lower()]
            has_data = False
            
            # Subplot dla silników i zasilania
            if mot_cols and len(mot_cols) >= 4:
                has_data = True
                mot_avgs = [df[m].mean() for m in mot_cols[:4]]
                fig_mot = go.Figure(data=[go.Bar(x=['Silnik 1', 'Silnik 2', 'Silnik 3', 'Silnik 4'], y=mot_avgs, marker_color=ACCENT_LIGHT)])
                fig_mot.update_layout(title="Średnie obciążenie silników (0-2048)", template="plotly_dark", height=250, margin=dict(l=0,r=0,t=40,b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_mot, use_container_width=True)
            
            if v_col and mode == "Real":
                has_data = True
                f_bat = make_subplots(specs=[[{"secondary_y": True}]])
                f_bat.add_trace(go.Scatter(y=pdf[v_col[0]]/100, name="Napięcie (V)", line=dict(color='#F8FAFC', width=2)), secondary_y=False)
                f_bat.add_trace(go.Scatter(y=pdf[thr], name="Gaz", line=dict(color=ACCENT_LIGHT, width=1), fill='tozeroy', opacity=0.3), secondary_y=True)
                f_bat.update_layout(title="Napięcie vs Gaz (Spadek napięcia)", template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(f_bat, use_container_width=True)
                
            if not has_data: st.info("Brak wystarczających danych o silnikach/zasilaniu w logu symulatora.")
            
    # Zwracanie metryk dla AI (W formacie słownika)
    return {"jr": float(jr), "jp": float(jp), "health": float(health), "avg_t": float(avg_t), "max_g": float(max_g)}

# ==========================================
# 5. EKRAN LOGOWANIA I REJESTRACJI (REDUX)
# ==========================================
# Tutaj musisz podpiąć swoje dane Supabase w Streamlit Cloud Secrets.
# Stworzyliśmy ekonomię tokenową: Analiza koszuje 1 lub 2 monety.

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
                # TO-DO: Użyj supabase.auth.sign_in_with_password dla lepszego security
                res = supabase.table('konta').select('*').eq('email', em).execute()
                if res.data and res.data[0]['haslo'] == pw:
                    
                    is_verified = res.data[0].get('zweryfikowany')
                    if em.lower() == 'admin@fpv.pl':
                        is_verified = True # Admin jest zawsze zweryfikowany
                        
                    if is_verified is False:
                        st.error("⚠️ Twoje konto oczekuje na weryfikację e-mail. Sprawdź skrzynkę odbiorczą (lub folder SPAM).")
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
                # TO-DO: Użyj supabase.auth.sign_up dla automatycznej weryfikacji maila
                email_check = supabase.table('konta').select('email').eq('email', rem).execute()
                if email_check.data:
                    st.error("Konto z tym adresem e-mail już istnieje w naszym systemie!")
                else:
                    # PROSTA WALIDACJA HASŁA
                    if len(rpw) < 6 or not any(c.isupper() for c in rpw) or not any(not c.isalnum() for c in rpw):
                        st.error("⚠️ Hasło musi mieć co najmniej 6 znaków, jedną wielką literę i jeden znak specjalny.")
                    else:
                        # Tworzenie kursanta z 10 monetami na start i flagą False
                        supabase.table('konta').insert({
                            'email': rem, 'haslo': rpw, 'imie': rnm, 'rola': 'Kursant', 
                            'tokeny': 10, 'zadania': [], 'zweryfikowany': False
                        }).execute()
                        st.success("Konto założone pomyślnie! Sprawdź swoją skrzynkę e-mail i kliknij link weryfikacyjny (sprawdź też folder SPAM).")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 6. LOGIKA UPRAWNIEŃ I SESJI
# ==========================================
# Tutaj pobieramy aktualne dane użytkownika z bazy, aby mieć pewność co do liczby tokenów.
user_data = supabase.table('konta').select('*').eq('email', st.session_state.auth_user).execute().data[0]

# Kto jest kim w systemie
is_admin = (user_data['rola'].lower() == 'admin') or (user_data['email'].lower() == 'admin@fpv.pl')
is_instructor = (user_data['rola'].lower() in ['instruktor', 'admin']) or is_admin

# FUNKCJA POMOCNICZA DLA HISTORII (The Masterpiece UX)
def render_history_stats(stats_dict):
    """Generuje mroczne metryki premium w historii lotów kursanta."""
    st.markdown("<p class='mono-text' style='margin-top: 15px;'>METRYKI ZAPISANE W BAZIE</p>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Kondycja", f"{stats_dict.get('health', 0):.0f}%")
    c2.metric("Roll Jerk", f"{stats_dict.get('jr', 0):.2f}")
    c3.metric("Pitch Jerk", f"{stats_dict.get('jp', 0):.2f}")
    c4.metric("Max G", f"{stats_dict.get('max_g', 0):.1f} G")

# ==========================================
# 7. PANEL INSTRUKTORA / ADMINA (White-Label)
# ==========================================
if is_instructor:
    render_logo()
    col_nav, col_main = st.columns([1, 3])
    
    with col_nav:
        # 1. Nawigacja po kursantach (Wybierz pilota)
        if is_admin:
            st.markdown(f"<div class='bento-card'>{render_neon_header('ZARZĄDZANIE (ADMIN MODE)')}", unsafe_allow_html=True)
            # Admin widzi wszystkich oprócz siebie
            cadets = supabase.table('konta').select('*').neq('email', user_data['email']).execute().data
        else:
            st.markdown(f"<div class='bento-card'>{render_neon_header('TWOI KURSANCI')}", unsafe_allow_html=True)
            # Instruktor widzi tylko kursantów
            cadets = supabase.table('konta').select('*').eq('rola', 'Kursant').execute().data
            
        if not cadets: st.warning("Brak użytkowników w bazie danych."); st.stop()
        
        # Tworzenie ładnej listy radio z pseudonimami
        display_names = [f"✅ {k['email']}" if k.get('zweryfikowany', True) is True else f"❌ {k['email']}" for k in cadets]
        selected_display = st.radio("Wybierz użytkownika:", display_names, label_visibility="collapsed")
        
        # Wyciąganie czystego e-maila
        selected_email = selected_display[2:] 
        target_data = next(k for k in cadets if k['email'] == selected_email)
        
        # Wyświetlanie stanu konta i zasilanie
        st.markdown(f"<br><p class='mono-text'>STAN KONTA: <span style='color: {ACCENT_LIGHT}; font-weight: bold;'>{target_data.get('tokeny', 0)} Tokenów</span></p>", unsafe_allow_html=True)
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1: dodaj_tok = st.number_input("Zasil", min_value=1, max_value=100, value=5, label_visibility="collapsed")
        with col_t2:
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("ZASIL", use_container_width=True):
                supabase.table('konta').update({"tokeny": target_data.get('tokeny', 0) + dodaj_tok}).eq('email', selected_email).execute()
                st.toast(f"Zasilono konto {target_data['imie']} o {dodaj_tok} Tokenów.", icon="🟢")
                time.sleep(1)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # 2. Konfiguracja Analizy Premium
        st.markdown("<br><p class='mono-text'>KONFIGURACJA ANALIZY PREMIUM</p>", unsafe_allow_html=True)
        inst_env = st.selectbox("Środowisko", ["Lot rzeczywisty", "Symulator"])
        inst_ind = st.selectbox("Styl lotu (Zastosowanie)", ["Cinematic / Płynny", "Racing (Wyścigi)", "Freestyle"]) if inst_env == "Lot rzeczywisty" else "Standard"
        inst_skill = st.selectbox("Poziom zaawansowania", ["Początkujący", "Średniozaawansowany", "Ekspert"])
        
        # Opcje Admina (Zarządzanie rangami)
        if is_admin:
            st.markdown("<br><p class='mono-text'>ZARZĄDZANIE KONTAMI (ADMIN)</p>", unsafe_allow_html=True)
            
            # Weryfikacja konta (Wpuszczanie)
            if target_data.get('zweryfikowany') is False:
                if st.button("✅ Zweryfikuj to konto (Wpuść)", use_container_width=True):
                    supabase.table('konta').update({"zweryfikowany": True}).eq('email', selected_email).execute()
                    st.success("Konto zweryfikowane! Pilot może się teraz zalogować.")
                    time.sleep(1)
                    st.rerun()
            
            # Zarządzanie Rangą Instruktora
            if target_data['rola'].lower() == 'kursant':
                if st.button("🌟 Nadaj Rangę Instruktora", use_container_width=True):
                    supabase.table('konta').update({"rola": "Instruktor"}).eq('email', selected_email).execute()
                    st.success(f"Pilot {target_data['imie']} otrzymał uprawnienia Instruktora!")
                    time.sleep(1)
                    st.rerun()
            elif target_data['rola'].lower() == 'instruktor':
                if st.button("🔻 Odbierz Rangę Instruktora", use_container_width=True):
                    supabase.table('konta').update({"rola": "Kursant"}).eq('email', selected_email).execute()
                    st.warning(f"Pilot {target_data['imie']} został zdegradowany do roli Kursanta.")
                    time.sleep(1)
                    st.rerun()

        st.markdown("<br><p class='mono-text'>OPCJE SESJI</p>", unsafe_allow_html=True)
        if st.button("Wyloguj się", use_container_width=True):
            st.session_state.auth_user = None; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_main:
        # Główny panel profilu kursanta
        st.markdown(f"<h2>Profil pilota: <span style='color:{ACCENT_LIGHT}; text-shadow:0 0 10px {ACCENT_LIGHT};'>{target_data['imie']} ({target_data['rola']})</span></h2>", unsafe_allow_html=True)
        
        # ADMIN: Edycja surowych danych (The Ultimate Power)
        if is_admin:
            with st.expander("⚙️ Surowa Edycja Konta w Bazie (Tylko Admin)"):
                with st.form("edit_raw_user"):
                    e_haslo = st.text_input("Hasło (surowe)", value=target_data['haslo'])
                    e_rola = st.selectbox("Rola w systemie", ["Admin", "Instruktor", "Kursant"], index=["Admin", "Instruktor", "Kursant"].index(target_data['rola']))
                    if st.form_submit_button("Zapisz zmiany w bazie Supabase"):
                        supabase.table('konta').update({'haslo': e_haslo, 'rola': e_rola}).eq('email', target_data['email']).execute()
                        st.success("Dane zaktualizowane pomyślnie w bazie.")
                        time.sleep(1)
                        st.rerun()
                
                # STREFA NIEBEZPIECZNA
                st.markdown("<br><hr style='border-color: #ef4444;'><p style='color: #ef4444; font-weight:bold;'>STREFA NIEBEZPIECZNA</p>", unsafe_allow_html=True)
                if st.button("🗑️ USUŃ TO KONTO BEZPOWROTNIE", use_container_width=True):
                    st.session_state[f'confirm_delete_{target_data["email"]}'] = True
                
                if st.session_state.get(f'confirm_delete_{target_data["email"]}'):
                    st.warning(f"Czy na pewno chcesz usunąć bezpowrotnie konto {target_data['imie']} ({target_data['email']})? Wszystkie logi i raporty przepadną.")
                    if st.button("🗑️ TAK, USUŃ TO KONTO TERAZ!", use_container_width=True, key=f"dl_{target_data['email']}"):
                        supabase.table('konta').delete().eq('email', target_data['email']).execute()
                        st.error("Konto usunięte z systemu.")
                        del st.session_state[f'confirm_delete_{target_data["email"]}']
                        time.sleep(1)
                        st.rerun()
                    if st.button("🔻 Anuluj usuwanie", use_container_width=True, key=f"anuluj_{target_data['email']}"):
                        del st.session_state[f'confirm_delete_{target_data["email"]}']
                        st.rerun()
        
        # Statystyki z dziennika zadań
        zad = target_data.get('zadania', [])
        loty = [z for z in zad if isinstance(z, dict) and 'ocena' in z and z.get('type') != 'Mechanik AI']
        mech_uses = len([z for z in zad if isinstance(z, dict) and z.get('type') == 'Mechanik AI'])
        avg_score = sum(z['ocena'] for z in loty) / len(loty) if loty else 0
        
        st.markdown("<div class='bento-card' style='margin-bottom: 30px;'>", unsafe_allow_html=True)
        st.markdown("<p class='mono-text' style='margin-bottom: 20px;'>PODSUMOWANIE AKTYWNOŚCI AI</p>", unsafe_allow_html=True)
        cm1, cm2, cm3 = st.columns(3)
        cm1.metric("Wykonane Analizy", len(loty))
        cm2.metric("Średnia Ocena AI", f"{avg_score:.1f}/10")
        cm3.metric("Zapytania do Warsztatu AI", mech_uses)
        
        # Wykres historii płynności (Jeśli jest > 1 lot)
        if len(loty) > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            dates = [z['data'] for z in loty if 'stats' in z]
            roll_jerks = [z['stats'].get('jr', 0) for z in loty if 'stats' in z]
            pitch_jerks = [z['stats'].get('jp', 0) for z in loty if 'stats' in z]
            
            if dates:
                fig_prog_inst = go.Figure()
                fig_prog_inst.add_trace(go.Scatter(x=dates, y=roll_jerks, mode='lines+markers', name='Roll Jerk (Mniej=lepiej)', line=dict(color=ACCENT_LIGHT, width=2)))
                fig_prog_inst.add_trace(go.Scatter(x=dates, y=pitch_jerks, mode='lines+markers', name='Pitch Jerk (Mniej=lepiej)', line=dict(color='#FFFFFF', dash='dot')))
                fig_prog_inst.update_layout(title="Historia płynności kursanta w czasie (Analizy Premium)", template="plotly_dark", height=250, margin=dict(l=0,r=0,t=40,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_prog_inst, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # 3. INTERFEJS DEKODOWANIA (PRACA INSTRUKTORA)
        # To jest niszowe rozwiązanie - Instruktor dekoduje czarną skrzynkę na żywo.
        vid_link = st.text_input("Opcjonalny link do nagrania (YouTube)", placeholder="https://youtube.com/watch?v=...")
        log_file = st.file_uploader("Zdekoduj plik z czarnej skrzynki pilota (BBL lub CSV)", type=['bbl', 'csv'], label_visibility="collapsed")

        df_active = None
        if log_file:
            with st.status("Działania telemetryczne: Kalibracja silników AI...", expanded=False) as status:
                if log_file.name.endswith('.csv'):
                    # Symulator CSV: Po prostu wczytaj Pandas
                    df_active = pd.read_csv(log_file)
                else:
                    # Rzeczywisty BBL: Potrzebujemy oficjalnego Betaflight Engine (fcis_engine)
                    dec = get_decoder()
                    # Zapisywanie pliku tymczasowo do /tmp (Zgodnie z Security Chmury)
                    with open("/tmp/inst_log.bbl", "wb") as f:
                        f.write(log_file.getbuffer())
                    
                    # Wykonanie dekodera C++ (generuje kilka plików .csv, jeśli log był przerywany)
                    subprocess.run([dec, "/tmp/inst_log.bbl"], stdout=subprocess.DEVNULL)
                    
                    # Wczytanie pierwszego wykrytego udanego lotu
                    csvs = sorted(glob.glob("/tmp/inst_log*.csv"))
                    if csvs:
                        df_active = pd.read_csv(csvs[0])
                status.update(label="Plik telemetryczny zdekodowany pomyślnie.", state="complete", expanded=False)

        if df_active is not None:
            # Generowanie wizualizacji Premium HUD i wykresów Plotly
            stats = render_terminal_hud(df_active, mode="Real" if inst_env=="Lot rzeczywisty" else "Sim", premium=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button(" GENERUJ WSKAZÓWKI AI Z TELEMETRII", use_container_width=True):
                # TO-DO: Skonfiguruj Gemini API w Streamlit Cloud Secrets.
                if init_ai():
                    prompt = f"Jesteś personalnym trenerem FPV Academy dla kursanta o pseudonimie {target_data['imie']}. Uczeń jest na poziomie: {inst_skill}. Przeanalizuj jego logi zastosowania przemysłowego {inst_ind}. Wyliczona kondycja drona: {stats['health']:.0f}%, płynność osi roll {stats['jr']:.2f}, max przeciążenie: {stats['max_g']:.1f}G. Bądź merytoryczny, niszowy, Zachęcaj do ćwiczeń. Wygeneruj czysty, niszowy JSON: {{\"ocena\": 8, \"diagnoza\": \"Opis objawów...\", \"zadanie\": \"Konkretne zadanie w Betaflight lub ćwiczenie na symulatorze...\"}}"
                    raw_ai = call_ai_safe(prompt, is_json=True)
                    try:
                        js = json.loads(raw_ai.replace("```json","").replace("```","").strip())
                        
                        # Generowanie mrocznego draftu do edycji
                        st.session_state.instructor_draft = f"### Analiza niszowa: {inst_ind}\n**OCENA LOTU:** {js['ocena']}/10\n\n**WSKAZÓWKI TRENERA FPV:**\n{js['diagnoza']}\n\n**ZADANIE NA NASTĘPNY TRENING:**\n{js['zadanie']}"
                        st.session_state.temp_metrics = stats
                    except: st.error("Niestety wystąpił problem podczas łączenia się z modułem AI.")
            st.markdown("</div>", unsafe_allow_html=True)

        # 4. EDYCJA I ZATWIERDZENIE RAPORTU (OSTATNIE SŁOWO TRENERA)
        if st.session_state.instructor_draft:
            final_rep = st.text_area("Edytuj raport przed wysłaniem do pilota (Pamiętaj o niszowym słownictwie!)", value=st.session_state.instructor_draft, height=250)
            if st.button("ZATWIERDŹ I WYŚLIJ RAPORT PREMIUM DO PILOTA", use_container_width=True):
                # Ekstrakcja oceny (Dla rankingu)
                match = re.search(r"OCENA LOTU:\s*(\d+)/10", final_rep)
                score = int(match.group(1)) if match else 5
                
                # Budowanie nowego rekordu (Zapisywanie wariantu)
                new_record = {
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "ocena": score, 
                    "raport": final_rep, "wideo": vid_link, "type": inst_ind, 
                    "premium": True, "stats": st.session_state.temp_metrics
                }
                
                # Aktualizacja bazy (Dziennik zadań + Płatność tokenami)
                # To jest najlepsze rozwiązanie - transakcja SQL na Supabase.
                history = target_data.get('zadania', [])
                history.append(new_record)
                
                # Aktualizacja danych kursanta w Supabase
                supabase.table('konta').update({
                    "zadania": history[-10:] # Zapisujemy tylko 10 ostatnich
                }).eq('email', selected_email).execute()
                
                # Czyszczenie sesji
                st.session_state.instructor_draft = None
                st.toast("Raport Premium został wysłany do kursanta!", icon="🟢")
                time.sleep(1)
                st.rerun()
            
        # 5. DZIENNIK ZADAŃ KURSANT (Zapisane Raporty)
        st.markdown("<br><p class='mono-text'>OSTATNIE ZADANIA ZAPISANE W DZIENNIKU PILOTA</p>", unsafe_allow_html=True)
        # FPV Masterpiece UX: Reversed history (ostatnie na górze)
        for z in reversed(target_data.get('zadania', [])):
            if isinstance(z, dict):
                if z.get('type') == 'Mechanik AI':
                    with st.expander(f"🤖 {z.get('data')} | Warsztat FPV Academy: Zapytanie techniczne do serwisu AI"):
                        st.markdown(z.get('raport'))
                else:
                    # The Masterpiece UX - Dynamic Color Ocena
                    ocena_score = z.get('ocena', 5)
                    score_color = "#ef4444" if ocena_score < 5 else ACCENT_LIGHT
                    
                    with st.expander(f"📄 {z.get('data')} | {z.get('type','Lot')} | Ocena: <span style='color:{score_color}; font-weight:bold;'>{ocena_score}/10</span>", unsafe_allow_html=True):
                        st.markdown(z.get('raport'))
                        if 'stats' in z: 
                            # Wyświetlanie niszowych metryk (health, Jerk, max G)
                            render_history_stats(z['stats'])
                            
                            # GENEROWANIE RAPORTU HTML (WHITE-LABEL DO POBRANIA)
                            html_report = generate_html_report(z.get('data'), z.get('ocena'), z.get('raport'), z['stats'], target_data['imie'])
                            st.download_button(label="📥 Pobierz Dokument (PDF Premium)", data=html_report, file_name=f"FPV_Raport_{z.get('data').split(' ')[0]}.html", mime="text/html", key=f"dl_{z.get('data')}")

# ==========================================
# 8. PANEL KURSANTA (THE MASTERPIECE UX)
# ==========================================
else:
    # Sidebar dla Kursanta
    with st.sidebar:
        st.write(render_neon_header(f"Zalogowany Pilot: <br><span style='font-size:1.5em; text-shadow: 0 0 15px {ACCENT_LIGHT};'>{user_data['imie']}</span>"))
        st.write("<br><hr style='border-color: rgba(51,102,0,0.2);'><br>", unsafe_allow_html=True)
        # Tutaj pobieramy świeże dane o tokenach
        st.metric("DOSTĘPNE TOKENY", user_data.get('tokeny', 0))
        st.write("<br>", unsafe_allow_html=True)
        st.info("💡 Gdy Instruktor prześle Ci nowy raport, użyj poniższego przycisku, aby odświeżyć dane.")
        if st.button("🔄 Synchronizuj z Bazy Danych", use_container_width=True): 
            st.rerun()
        st.write("<br><br><br>", unsafe_allow_html=True)
        if st.button("Wyloguj się z platformy", use_container_width=True):
            st.session_state.auth_user = None; st.rerun()

    # Stan Flow: Wybór ścieżki na Launchpadzie
    if st.session_state.flow_state == 'launchpad':
        render_logo()
        # Neowe powitanie dla kursantów
        st.markdown(f"<div style='text-align:center; padding-bottom:3rem;'><h1 style='font-size:4rem; text-shadow: 0 0 20px {ACCENT_LIGHT};'>Cześć {user_data['imie']}! 🚁</h1><p style='color:#64748B; font-size:1.3rem; margin-top:0.5rem; font-weight:600;'>Wybierz swoją ścieżkę treningową i wzbij się na wyższy poziom.</p></div>", unsafe_allow_html=True)
        
        tab_main, tab_rank, tab_workshop = st.tabs(["🚀 Dostępne Ścieżki i Trener AI", "🏆 Ranking Globalny FPV Academy", "🛠️ Warsztat FPV (Betaflight tools)"])
        
        with tab_main:
            col_d, col_r = st.columns(2)
            with col_d:
                # Lot rzeczywisty - wymaga dekodera Linuxa
                st.markdown("<div class='bento-card' style='height:100%; border-color:#d9534f;'><h3>🚁 LOT RZECZYWISTY (Blackbox)</h3><p class='mono-text'>Analiza surowej telemetrii z drona (.BBL/CSV)</p></div>", unsafe_allow_html=True)
                col_m1, col_r1, col_f1 = st.columns(3)
                if col_m1.button("Cinematic"): st.session_state.industry_select="Cinematic / Płynny"; st.session_state.env_select="Real"; st.rerun()
                if col_r1.button("Racing"): st.session_state.industry_select="Racing (Wyścigi)"; st.session_state.env_select="Real"; st.rerun()
                if col_f1.button("Freestyle"): st.session_state.industry_select="Freestyle"; st.session_state.env_select="Real"; st.rerun()
            with col_r:
                # Symulator - proste CSV (Liftoff/Velocidrone)
                st.markdown("<div class='bento-card' style='height:100%;'><h3>🎮 SYMULATOR FPV (NSTS)</h3><p class='mono-text'>Analiza danych z Liftoff / Velocidrone (CSV)</p></div>", unsafe_allow_html=True)
                st.markdown("<br><br><br>", unsafe_allow_html=True)
                if st.button("URUCHOM ANALIZĘ SYMULATORA", use_container_width=True): 
                    st.session_state.industry_select="Symulator treningowy"; st.session_state.env_select="Sim"; st.rerun()
            
            # 1. Po wybieraniu środowiska - wybór poziomu AI
            if st.session_state.industry_select:
                st.write("<br><br>", unsafe_allow_html=True)
                st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
                st.write(render_neon_header("WYBÓR POZIOMU DOŚWIADCZENIA AI DLA TRENERA"))
                skill = st.select_slider("Wybierz poziom do oceny przez AI:", options=["Początkujący", "Średniozaawansowany", "Ekspert"], value=st.session_state.skill_select, label_visibility="collapsed")
                st.session_state.skill_select = skill
                st.write("<br>", unsafe_allow_html=True)
                st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
                if st.button("PRZEJDŹ DO WGRYWANIA PLIKU LOTU", use_container_width=True): st.session_state.flow_state = 'upload'; st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # 2. Ostatnie raporty dla Kursanta (FPV Masterpiece UX)
            st.write("<br><br>", unsafe_allow_html=True)
            st.write(render_neon_header("OSTATNIE RAPORTY I WSKAZÓWKI W TWOIM DZIENNIKU ZADAŃ"))
            # Reversed history
            for z in reversed(user_data.get('zadania', [])):
                if isinstance(z, dict):
                    if z.get('type') == 'Mechanik AI':
                        with st.expander(f"🤖 {z.get('data')} | Warsztat FPV Academy: Diagnoza serwisowa"):
                            st.markdown(z.get('raport'))
                    else:
                        ocena_score = z.get('ocena', 5)
                        score_color = "#ef4444" if ocena_score < 5 else ACCENT_LIGHT
                        with st.expander(f"📄 {z.get('data')} | {z.get('type','Lot')} | Ocena: <span style='color:{score_color}; font-weight:bold;'>{ocena_score}/10</span>", unsafe_allow_html=True):
                            st.markdown(z.get('raport'))
                            if 'stats' in z: 
                                render_history_stats(z['stats'])
                                html_report = generate_html_report(z.get('data'), z.get('ocena'), z.get('raport'), z['stats'], user_data['imie'])
                                st.download_button(label="📥 Pobierz Raport (PDF Premium)", data=html_report, file_name=f"FPV_Raport_{z.get('data').split(' ')[0]}.html", mime="text/html", key=f"dl_{z.get('data')}")
                else:
                    with st.expander("Stare zapisy archiwalne"): st.markdown(str(z))

        with tab_rank:
            # Ranking Globalny FPV Academy (Kto jest najlepszy w Polsce?)
            st.markdown(f"<h2>Top Piloci FPV AI Academy</h2>", unsafe_allow_html=True)
            # Pobieranie wszystkich kursantów
            all_cadets = supabase.table('konta').select('imie, zadania').eq('rola', 'Kursant').execute().data
            
            leaderboard = []
            for k in all_cadets:
                # Tylko płatne raporty lotu się liczą
                zad = k.get('zadania', [])
                valid_zad = [z for z in zad if isinstance(z, dict) and 'ocena' in z and z.get('type') != 'Mechanik AI']
                if valid_zad:
                    avg_ocena = sum(z['ocena'] for z in valid_zad) / len(valid_zad)
                    max_g = max((z.get('stats', {}).get('max_g', 0) for z in valid_zad), default=0)
                    leaderboard.append({"Pilot": k['imie'], "Średnia Ocena AI": round(avg_ocena, 1), "Max Przeciążenie G": round(max_g, 1), "Ukończone Analizy": len(valid_zad)})
            
            if leaderboard:
                df_leaderboard = pd.DataFrame(leaderboard).sort_values(by="Średnia Ocena AI", ascending=False).reset_index(drop=True)
                # Nadanie numeracji rankingu
                df_leaderboard.index += 1
                st.dataframe(df_leaderboard, use_container_width=True)
            else:
                st.info("Brak wystarczających danych do wygenerowania rankingu. Wykonaj analizę premium!")

        with tab_workshop:
            # WARSZTAT FPV ACADEMY: Tabela VTX, Słowniczek
            st.markdown(f"<h2>🛠️ Warsztat i Wiedza FPV Academy</h2><p style='color:#64748B;'>Twoje niszowe centrum wiedzy technicznej.</p>", unsafe_allow_html=True)
            
            w_mech, w_vtx, w_dict = st.tabs(["🤖 Wirtualny Mechanik AI", "📡 Ściągawka Częstotliwości VTX", "📚 Słowniczek Techniczny"])
            
            with w_mech:
                st.markdown("### Sztuczna Inteligencja Serwisowa")
                mech_query = st.text_area("Opisz problem ze sprzętem (Gorące silniki, propwash, zakłócenia wideo...):", placeholder="Np. Dron po zrobieniu flipa na chwilę traci moc i dziwnie wyje...")
                st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
                # Zapytanie do Warsztatu AI jest darmowe (Dla płynności API chmury)
                if st.button("POPROŚ O DIAGNOZĘ MECHANIKA"):
                    if mech_query and init_ai():
                        with st.spinner("Moduł serwisowy FPV analizuje problem..."):
                            prompt = f"Jesteś przyjaznym i profesjonalnym serwisantem dronów FPV Academy. Krótko i zwięźle w punktach pomóż rozwiązać problem techniczny, dając niszowe rady. Problem: {mech_query}"
                            mech_resp = call_ai_safe(prompt, is_json=False)
                            # Zapisywanie darmowego zapytania technicznego
                            supabase.table('konta').update({"zadania": user_data.get('zadania', []) + [{"data": datetime.now().strftime("%Y-%m-%d %H:%M"), "type": "Mechanik AI", "raport": f"**Pytanie do serwisu:** {mech_query}\n\n**Diagnoza Mechanika FPV:**\n{mech_resp}"}]}).eq('email', user_data['email']).execute()
                            st.success("Wskazówki zostały zapisane w Twoim dzienniku zadań:")
                            st.markdown(mech_resp)
                st.markdown("</div>", unsafe_allow_html=True)

            with w_vtx:
                # Najlepsze rozwiązanie: Tabela częstotliwości VTX z podświetlaniem IMD
                st.markdown("### Pełna Macierz Częstotliwości VTX (5.8 GHz)")
                st.write("Wybierz liczbę pilotów w grupie, a system podpowie optymalne kanały Betaflight, dbając o odległość częstotliwości (zgodnie z IMD).")
                
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
                
                pilots_count = st.slider("Ilu pilotów leci jednocześnie w grupie?", 1, 8, 4)
                
                # Niszowe mapowanie IMD-safe ( Raceband/Fatshark)
                optimal_freqs = {
                    1: [5658],
                    2: [5658, 5917], # R1, R8
                    3: [5658, 5769, 5917], # R1, R4, R8
                    4: [5658, 5732, 5843, 5917], # R1, R3, R6, R8
                    5: [5645, 5705, 5769, 5843, 5917], # E4, E1, R4, R6, R8
                    6: [5645, 5695, 5760, 5800, 5860, 5917], # E4, R2, F2, F4, F7, R8
                    7: [5645, 5695, 5740, 5780, 5820, 5860, 5917], # E4, R2, F1, F3, F5, F7, R8
                    8: [5645, 5685, 5725, 5760, 5800, 5840, 5880, 5917] # E4, E2, A8, F2, F4, F6, R7, R8
                }
                active_freqs = optimal_freqs[pilots_count]
                
                # Customowe podświetlanie IMD w tabeli z neonowym glow
                def highlight_active(row):
                    return ['background-color: #336600; color: white; font-weight: bold; border: 1px solid #4d9900; box-shadow: 0 0 5px #4d9900;' if val in active_freqs else '' for val in row]
                
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
                # Biblioteka wiedzy Betaflight tools
                st.markdown("### Słowniczek Techniczny FPV Academy (Betaflight tools)")
                with st.expander("P-I-D (Proportional, Integral, Derivative)"): 
                    st.write("**P (Proportional)** - Szybkość reakcji drona na drążki i wiatr. Zbyt niskie = dron 'pływa', zbyt wysokie = szybkie wibracje (oscylacje).\n\n**I (Integral)** - Trzymanie zadanego kąta. Pomaga dronowi nie ulegać wpływom wiatru i odchyleniom środka ciężkości baterii.\n\n**D (Derivative)** - 'Amortyzator' dla wartości P. Zapobiega przelatywaniu poza cel (overshoot) po ostrym manewrze. Zbyt wysokie D powoduje bardzo mocne grzanie silników.")
                with st.expander("Rates (RC Rate, Super Rate/Expo)"):
                    st.write("**RC Rate** - Czułość na samym środku drążka. Im wyższa, tym szybciej dron reaguje na najdrobniejsze ruchy palcami.\n\n**Super Rate / Expo** - Czułość na samych krawędziach wychylenia drążka. Pozwala na super szybkie flipy i rolle, zachowując przy tym miękki środek niezbędny do płynnego lotu (Cinematic).")
                with st.expander("Propwash (Oscylacje po zejściu)"):
                    st.write("Wibracje drona, które pojawiają się, gdy gwałtownie zawracasz lub opadasz pionowo we własne 'brudne powietrze' wyrzucone wcześniej przez śmigła. Zjawisko to redukujemy m.in. optymalizując wartość 'D' w Betaflight.")
                with st.expander("RPM Filtering (Filtry dwukierunkowe DShot)"):
                    st.write("Bardzo zaawansowana funkcja, gdzie regulator ESC na żywo wysyła do kontrolera lotu informację z jaką prędkością obraca się każdy z czterech silników. Dzięki temu Betaflight filtruje tylko te konkretne częstotliwości, które generują wibracje z silników, pozwalając dronom latać znacznie czyściej.")

    # Stan Flow: Wgrywanie pliku i płatność
    elif st.session_state.flow_state == 'upload':
        st.markdown(f"<h2>ANALIZA LOTU: <span style='color: {ACCENT_LIGHT};'>{st.session_state.industry_select.upper()} ({st.session_state.env_select})</span></h2>", unsafe_allow_html=True)
        if st.button("← Wróć do panelu głównego"): 
            st.session_state.flow_state = 'launchpad'; st.session_state.env_select = None; st.session_state.industry_select = None; st.rerun()

        col_tier, col_drop = st.columns([1, 2])
        with col_tier:
            st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
            st.markdown("<p class='mono-text'>WYBÓR PAKIETU ANALITYCZNEGO</p>", unsafe_allow_html=True)
            tier = st.radio("Poziom szczegółowości:", ["Standardowy (1 Token)", "Premium + G-Force Matrix (2 Tokeny)"], label_visibility="collapsed")
            cost = 1 if "Standardowy" in tier else 2
            st.markdown(f"<p style='font-size: 0.9em; color: {TEXT_NEON}; margin-top: 10px;'>Dostępne środki: <b>{user_data.get('tokeny', 0)} Tokenów</b></p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with col_drop:
            u_log = st.file_uploader("Upuść plik z logami z lotu (Betaflight tools BBL lub CSV symulatora)", type=['bbl', 'csv'], label_visibility="collapsed")
            if u_log:
                # To jest najlepsze rozwiązanie: Wczytanie dekodera z cache'u chmury
                with st.spinner("Trwa kalibracja dekodera Linuxa (fcis_engine)..."):
                    dec = get_decoder()
                
                st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
                if st.button(f"ROZPOCZNIJ ANALIZĘ AI (-{cost} TOKENÓW)", use_container_width=True):
                    # Sprawdzanie wypłacalności
                    if user_data.get('tokeny', 0) >= cost:
                        with st.status("Trwa wczytywanie, dekodowanie i niszowa analiza danych...", expanded=True) as status:
                            if u_log.name.endswith('.csv'):
                                # Symulator CSV: Po prostu wczytaj Pandas
                                df = pd.read_csv(u_log)
                            else:
                                # Rzeczywisty BBL: Wymaga oficjalnego Betaflight Engine (fcis_engine)
                                # Zapisywanie pliku tymczasowo do /tmp (Zgodnie z Security Chmury)
                                with open("/tmp/u_log.bbl", "wb") as f:
                                    f.write(u_log.getbuffer())
                                subprocess.run([dec, "/tmp/u_log.bbl"], stdout=subprocess.DEVNULL)
                                csvs = sorted(glob.glob("/tmp/u_log*.csv"))
                                if csvs: df = pd.read_csv(csvs[0])
                            
                            # Generowanie wizualizacji Premium HUD i metryk G
                            stats = render_terminal_hud(df, mode=st.session_state.env_select, premium=(cost==2))
                            
                            if init_ai():
                                # TO-DO: Skonfiguruj Gemini API w Streamlit Cloud Secrets.
                                prompt = f"Trener personalny FPV Academy. Uczeń jest na poziomie: {st.session_state.skill_select}. Zdekodowałem jego logi lotu {st.session_state.industry_select}. Wyliczone: płynność {stats['jr']:.2f}, max przeciążenie: {stats['max_g']:.1f}G. Bądź merytoryczny, Zachęcaj do ćwiczeń. Wygeneruj JSON: {{\"ocena\": 8, \"diagnoza\": \"...\", \"zadanie\": \"...\"}}"
                                raw_ai = call_ai_safe(prompt, is_json=True)
                                try:
                                    js = json.loads(raw_ai.replace("```json","").replace("```","").strip())
                                    
                                    # Generowanie niszowego raportu
                                    tag = "RAPORT PREMIUM G-FORCE" if cost == 2 else "RAPORT STANDARDOWY"
                                    txt = f"### {tag}\n**OCENA LOTU:** {js['ocena']}/10\n\n**WSKAZÓWKI TRENERA:**\n{js['diagnoza']}\n\n**ZADANIE NA NASTĘPNY TRENING:**\n{js['zadanie']}"
                                    
                                    # Aktualizacja bazy (Dziennik zadań + Płatność tokenami)
                                    # To jest najlepsze rozwiązanie - transakcja SQL na Supabase.
                                    history = user_data.get('zadania', [])
                                    history.append({
                                        "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "ocena": js['ocena'], 
                                        "raport": txt, "type": st.session_state.industry_select, 
                                        "premium": (cost==2), "stats": stats
                                    })
                                    
                                    # Aktualizacja danych kursanta w Supabase
                                    supabase.table('konta').update({
                                        "zadania": history[-10:], # Zapisujemy tylko 10 ostatnich
                                        "tokeny": user_data['tokeny'] - cost
                                    }).eq('email', user_data['email']).execute()
                                    
                                    status.update(label="Gotowe! Wyniki zostały zapisane w Twoim dzienniku zadań.", state="complete", expanded=False)
                                    time.sleep(1)
                                    st.session_state.flow_state = 'launchpad' 
                                    st.rerun()
                                except: st.error("Niestety wystąpił problem podczas łączenia się z modułem AI.")
                    else:
                        st.error("Niewystarczająca liczba tokenów na koncie. Zasil konto lub wybierz darmowe Zapytanie techniczne do mechanika.")
                st.markdown("</div>", unsafe_allow_html=True)
