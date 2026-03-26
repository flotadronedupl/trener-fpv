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
# 1. KONFIGURACJA SESJI
# ==========================================
st.set_page_config(page_title="FPV AI Academy", page_icon="🚁", layout="wide", initial_sidebar_state="expanded")

# GŁÓWNY KOLOR PREMIUM (Wyścigowa, głęboka zieleń)
PRIMARY_COLOR = "#336600"
ACCENT_LIGHT = "#4d9900" # Jaśniejsza zieleń do gradientów i poświaty

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
# 2. MODERN PREMIUM UI (CSS & Dark Forest/Glass Theme)
# ==========================================
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Głębsze, ciemniejsze tło z baaardzo delikatnym zielonym gradientem na górze */
    .stApp {{ 
        background: radial-gradient(circle at 50% 0%, #0d1a00 0%, #050a0a 40%, #000000 100%); 
        color: #F8FAFC; 
        font-family: 'Inter', sans-serif; 
    }}
    
    /* Karty Bento - Ultra Premium */
    .bento-card {{
        background: rgba(10, 15, 10, 0.6); 
        backdrop-filter: blur(16px);
        border: 1px solid rgba(51, 102, 0, 0.2); 
        border-radius: 20px;
        padding: 30px; 
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); 
        box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.8);
    }}
    .bento-card:hover {{ 
        border-color: rgba(77, 153, 0, 0.5); 
        box-shadow: 0 20px 50px -10px rgba(51, 102, 0, 0.3); 
        transform: translateY(-3px); 
    }}
    
    /* Typografia */
    h1, h2, h3, h4 {{ font-weight: 800 !important; color: #FFFFFF !important; letter-spacing: -0.5px; }}
    .mono-text {{ 
        font-family: 'Inter', sans-serif; 
        color: #8cbf8c; 
        font-size: 0.75rem; 
        text-transform: uppercase; 
        font-weight: 700; 
        letter-spacing: 0.15em; 
    }}
    
    /* Metryki z zielonym blaskiem */
    div[data-testid="stMetric"] {{
        background: linear-gradient(180deg, rgba(20, 30, 20, 0.8) 0%, rgba(10, 15, 10, 0.9) 100%); 
        border: 1px solid rgba(51, 102, 0, 0.3); 
        border-radius: 16px; 
        padding: 24px;
        box-shadow: inset 0 2px 15px 0 rgba(51, 102, 0, 0.05);
        border-top: 2px solid {ACCENT_LIGHT};
    }}
    div[data-testid="stMetricValue"] {{ font-weight: 800; color: #FFFFFF; font-size: 2.2rem; text-shadow: 0 0 15px rgba(77, 153, 0, 0.4); }}
    
    /* Przyciski standardowe */
    .stButton>button {{
        background: rgba(20, 30, 20, 0.8); border: 1px solid rgba(51,102,0,0.4); color: #E2E8F0; border-radius: 10px; font-weight: 600; transition: all 0.3s ease;
    }}
    .stButton>button:hover {{ background: rgba(51,102,0,0.2); color: #FFFFFF; border-color: {ACCENT_LIGHT}; box-shadow: 0 0 15px rgba(51,102,0,0.4); }}
    
    /* Główny przycisk akcji (CTA) - Esencja Premium */
    .cta-btn>button {{ 
        background: linear-gradient(135deg, {PRIMARY_COLOR}, {ACCENT_LIGHT}); 
        color: #FFFFFF; 
        border: none; 
        font-weight: 700; 
        letter-spacing: 1px; 
        box-shadow: 0 6px 25px 0 rgba(51, 102, 0, 0.5); 
        border-radius: 10px; 
        padding: 0.75rem 2rem;
        text-transform: uppercase;
    }}
    .cta-btn>button:hover {{ box-shadow: 0 8px 35px rgba(77, 153, 0, 0.7); transform: scale(1.03); }}
    
    /* Pola wprowadzania danych */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {{ 
        background: rgba(10, 15, 10, 0.8) !important; border: 1px solid rgba(51,102,0,0.3) !important; color: #FFFFFF !important; border-radius: 10px !important; 
    }}
    .stTextInput input:focus, .stTextArea textarea:focus {{ border-color: {ACCENT_LIGHT} !important; box-shadow: 0 0 0 2px rgba(51,102,0,0.3) !important; }}
    
    section[data-testid="stSidebar"] {{ background-color: rgba(5, 10, 5, 0.95) !important; border-right: 1px solid rgba(51,102,0,0.2); backdrop-filter: blur(20px); }}
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# BEZPIECZNE LOGO HTML (Sformatowane w jednej linii, by uniknąć błędu Markdown)
def render_logo():
    logo_html = f"""<div style='text-align:center; padding-bottom:3rem; display:flex; flex-direction:column; align-items:center;'><svg width='80' height='80' viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M5.5 5.5h.01M18.5 5.5h.01M5.5 18.5h.01M18.5 18.5h.01' stroke='{ACCENT_LIGHT}' stroke-width='3' stroke-linecap='round'/><path d='M12 12L5.5 5.5M12 12l6.5-6.5M12 12l-6.5 6.5M12 12l6.5 6.5' stroke='#4d9900' stroke-width='1.5' stroke-linecap='round'/><circle cx='12' cy='12' r='3' fill='#050a0a' stroke='{ACCENT_LIGHT}' stroke-width='2'/></svg><h1 style='font-size:3rem; margin:10px 0 0 0; background:linear-gradient(90deg, #FFFFFF, #8cbf8c); -webkit-background-clip:text; -webkit-text-fill-color:transparent;'>FPV AI Academy</h1><p style='color:#64748B; font-size:1.1rem; margin-top:0.5rem; font-weight:600; letter-spacing:2px;'>NEXT-GEN FLIGHT ANALYTICS</p></div>"""
    st.markdown(logo_html, unsafe_allow_html=True)

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
        return f'{{"ocena": 0, "diagnoza": "Błąd komunikacji z AI.", "zadanie": "Brak zadań."}}'

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
# 4. SILNIK WIZUALIZACJI (NOWE METRYKI!)
# ==========================================
def render_terminal_hud(df, mode="Real", premium=False):
    try:
        thr = [c for c in df.columns if 'rcCommand[3]' in c or ('rcCommand' in c and '3' in c)][0]
        roll = [c for c in df.columns if 'rcCommand[0]' in c or ('rcCommand' in c and '0' in c)][0]
        pitch = [c for c in df.columns if 'rcCommand[1]' in c or ('rcCommand' in c and '1' in c)][0]
        yaw_cols = [c for c in df.columns if 'rcCommand[2]' in c or ('rcCommand' in c and '2' in c)]
        yaw = yaw_cols[0] if yaw_cols else None
        
        # Szukanie danych akcelerometru (do G-Force)
        acc_x = [c for c in df.columns if 'accSmooth[0]' in c]
        acc_y = [c for c in df.columns if 'accSmooth[1]' in c]
        acc_z = [c for c in df.columns if 'accSmooth[2]' in c]
        has_acc = bool(acc_x and acc_y and acc_z)
        
        # Szukanie Gyro
        gyro_r = [c for c in df.columns if 'gyroADC[0]' in c]
    except:
        st.error("Nie znaleziono podstawowych danych telemetrycznych w logu.")
        return None

    # Obliczenia
    jr, jp = df[roll].diff().abs().mean(), df[pitch].diff().abs().mean()
    jy = df[yaw].diff().abs().mean() if yaw else 0
    smoothness = max(0, 10 - ((jr + jp + jy) * 0.8))
    avg_t = df[thr].mean()
    
    # Obliczanie max G-Force
    max_g = 1.0 # Domyślnie 1G (Grawitacja ziemska)
    if has_acc:
        # W Betaflight akcelerometr często ma skale gdzie 1G = 2048 lub 4096. Zakładamy zgrubnie 2048 dla wektora 3D
        g_vector = np.sqrt(df[acc_x[0]]**2 + df[acc_y[0]]**2 + df[acc_z[0]]**2) / 2048.0
        max_g = g_vector.max()

    st.markdown("<p class='mono-text'>DASHBOARD TELEMETRYCZNY</p>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Płynność Lotu", f"{smoothness:.1f} / 10")
    m2.metric("Średni Gaz", f"{avg_t:.0f}")
    m3.metric("Max Przeciążenie", f"{max_g:.1f} G" if has_acc else "Brak Danych")
    
    health = max(0, min(100, 100 - ((jr + jp) * 12)))
    m4.metric("Kondycja / Wibracje", f"{health:.0f}%")

    if premium:
        st.markdown("<br><p class='mono-text'>ANALIZA ZAAWANSOWANA (PREMIUM)</p>", unsafe_allow_html=True)
        t1, t2, t3, t4 = st.tabs(["Telemetria Drążków", "Analiza Przeciążeń (G-Force)", "Przestrzenna Trajektoria 3D", "Silniki i Energia"])
        
        pdf = df.iloc[::max(1, len(df)//3000)] # Downsampling
        
        with t1:
            st.markdown("<p style='color: #8cbf8c; font-size: 0.9em;'>Analiza pracy aparaturą. Agresywne skoki oznaczają nerwowe ruchy pilota.</p>", unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=pdf[thr], name="Gaz (Throttle)", line=dict(color='#2f3b2f', width=2, fill='tozeroy')))
            fig.add_trace(go.Scatter(y=pdf[roll], name="Roll", line=dict(color=ACCENT_LIGHT, width=2)))
            if yaw: fig.add_trace(go.Scatter(y=pdf[yaw], name="Yaw", line=dict(color='#FFFFFF', width=1, dash='dot')))
            fig.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
        with t2:
            if has_acc:
                st.markdown("<p style='color: #8cbf8c; font-size: 0.9em;'>Wykres prezentujący siły grawitacyjne (G-Force) działające na ramę drona podczas manewrów.</p>", unsafe_allow_html=True)
                g_series = np.sqrt(pdf[acc_x[0]]**2 + pdf[acc_y[0]]**2 + pdf[acc_z[0]]**2) / 2048.0
                fig_g = go.Figure()
                fig_g.add_trace(go.Scatter(y=g_series, name="G-Force", line=dict(color='#ff3333', width=2)))
                fig_g.add_hline(y=1.0, line_dash="dash", line_color="#8cbf8c", annotation_text="Grawitacja Ziemska (1G)")
                fig_g.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=10,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_g, use_container_width=True)
            else:
                st.info("Brak danych z akcelerometru w tym logu by wygenerować wykres G-Force.")

        with t3:
            fig3 = go.Figure(data=[go.Scatter3d(x=pdf[roll].cumsum()/500, y=pdf[pitch].cumsum()/500, z=np.arange(len(pdf)), 
                                mode='lines', line=dict(color=pdf[thr], colorscale='Greens', width=6))])
            fig3.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', scene=dict(bgcolor='rgba(0,0,0,0)'))
            st.plotly_chart(fig3, use_container_width=True)
            
        with t4:
            v_col = [c for c in df.columns if 'vbat' in c.lower()]
            mot_cols = [c for c in df.columns if 'motor[' in c.lower() or 'motor0' in c.lower()]
            
            if mot_cols and len(mot_cols) >= 4:
                mot_avgs = [df[m].mean() for m in mot_cols[:4]]
                fig_mot = go.Figure(data=[go.Bar(x=['Silnik 1', 'Silnik 2', 'Silnik 3', 'Silnik 4'], y=mot_avgs, marker_color=ACCENT_LIGHT)])
                fig_mot.update_layout(title="Średnie obciążenie silników", template="plotly_dark", height=250, margin=dict(l=0,r=0,t=40,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_mot, use_container_width=True)
            elif v_col and mode == "Real":
                f_bat = go.Figure()
                f_bat.add_trace(go.Scatter(y=pdf[v_col[0]]/100, name="Napięcie (V)", line=dict(color=ACCENT_LIGHT, width=3)))
                f_bat.update_layout(title="Spadek Napięcia Baterii", template="plotly_dark", height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(f_bat, use_container_width=True)
            else:
                st.info("Brak wystarczających danych o napędzie w logu symulatora.")
            
    return {"jr": float(jr), "jp": float(jp), "health": float(health), "avg_t": float(avg_t), "max_g": float(max_g)}

# ==========================================
# 5. EKRAN LOGOWANIA
# ==========================================
if st.session_state.auth_user is None:
    render_logo()
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Zaloguj się", "Załóż konto"])
        with t1:
            em = st.text_input("Adres Email")
            pw = st.text_input("Hasło", type="password")
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("Wejdź do centrum dowodzenia"):
                res = supabase.table('konta').select('*').eq('email', em).execute()
                if res.data and res.data[0]['haslo'] == pw:
                    st.session_state.auth_user = em
                    st.session_state.role = res.data[0]['rola']
                    st.rerun()
                else: st.error("Nieprawidłowy email lub hasło.")
            st.markdown("</div>", unsafe_allow_html=True)
        with t2:
            rem = st.text_input("Nowy Email")
            rpw = st.text_input("Hasło", type="password", key="reg_pass")
            rnm = st.text_input("Pilot (Pseudonim)")
            if st.button("Zarejestruj się"):
                supabase.table('konta').insert({'email': rem, 'haslo': rpw, 'imie': rnm, 'rola': 'Kursant', 'tokeny': 10, 'zadania': []}).execute()
                st.success("Konto założone! Możesz się teraz zalogować.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

user_data = supabase.table('konta').select('*').eq('email', st.session_state.auth_user).execute().data[0]

def render_history_stats(stats_dict):
    st.markdown("<p class='mono-text' style='margin-top: 15px;'>METRYKI ZAPISANE W BAZIE</p>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Kondycja", f"{stats_dict.get('health', 0):.0f}%")
    c2.metric("Roll Jerk", f"{stats_dict.get('jr', 0):.2f}")
    c3.metric("Pitch Jerk", f"{stats_dict.get('jp', 0):.2f}")
    c4.metric("Max G", f"{stats_dict.get('max_g', 0):.1f} G")

# ==========================================
# 6. PANEL INSTRUKTORA
# ==========================================
if user_data['rola'] == "Instruktor":
    render_logo()
    col_nav, col_main = st.columns([1, 3])
    
    with col_nav:
        st.markdown(f"<div class='bento-card'><p class='mono-text'>AKTYWNI KURSANCI</p>", unsafe_allow_html=True)
        cadets = supabase.table('konta').select('*').eq('rola', 'Kursant').execute().data
        if not cadets: st.warning("Brak kursantów."); st.stop()
        selected_email = st.radio("Wybierz pilota:", [k['email'] for k in cadets], label_visibility="collapsed")
        target_data = next(k for k in cadets if k['email'] == selected_email)
        
        st.markdown(f"<br><p class='mono-text'>STAN KONTA: <span style='color: {ACCENT_LIGHT}; font-weight: bold;'>{target_data.get('tokeny', 0)} Tokenów</span></p>", unsafe_allow_html=True)
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1: dodaj_tok = st.number_input("Dodaj", min_value=1, max_value=100, value=5, label_visibility="collapsed")
        with col_t2:
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("ZASIL"):
                supabase.table('konta').update({"tokeny": target_data.get('tokeny', 0) + dodaj_tok}).eq('email', selected_email).execute()
                st.toast("Zasilono konto.", icon="🟢")
                time.sleep(1)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><p class='mono-text'>KONFIGURACJA LOTU</p>", unsafe_allow_html=True)
        inst_env = st.selectbox("Środowisko", ["Lot Rzeczywisty", "Symulator"])
        inst_ind = "Standard"
        if inst_env == "Lot Rzeczywisty": inst_ind = st.selectbox("Styl Lotu", ["Cinematic / Płynny", "Racing (Wyścigi)", "Freestyle"])
        inst_skill = st.selectbox("Poziom Pilota", ["Początkujący", "Średniozaawansowany", "Ekspert"])
        
        st.markdown("<br><p class='mono-text'>OPCJE</p>", unsafe_allow_html=True)
        if st.button("Zakończ Sesję"): st.session_state.auth_user = None; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_main:
        st.markdown(f"<h2>Akta Pilota: <span style='color:{ACCENT_LIGHT}'>{target_data['imie']}</span></h2>", unsafe_allow_html=True)
        
        c_upl, c_vid = st.columns(2)
        with c_upl: log_file = st.file_uploader("Wgraj Plik Czarną Skrzynkę (BBL/CSV)", type=['bbl', 'csv'], label_visibility="collapsed")
        with c_vid: vid_link = st.text_input("Opcjonalny link do nagrania (YouTube/DVR)", placeholder="https://...")

        df_active = None
        if log_file:
            with st.status("Ekstrakcja danych balistycznych...", expanded=False) as status:
                if log_file.name.endswith('.csv'): 
                    df_active = pd.read_csv(log_file)
                else:
                    dec = get_decoder()
                    with open("/tmp/i.bbl", "wb") as f: f.write(log_file.getbuffer())
                    subprocess.run([dec, "/tmp/i.bbl"], stdout=subprocess.DEVNULL)
                    csvs = sorted(glob.glob("/tmp/i*.csv"))
                    if csvs: df_active = pd.read_csv(csvs[0])
                status.update(label="Dane zdekodowane i gotowe.", state="complete", expanded=False)

        if df_active is not None:
            stats = render_terminal_hud(df_active, mode="Real" if inst_env=="Lot Rzeczywisty" else "Sim", premium=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("GENERUJ RAPORT AI"):
                if init_ai():
                    prompt = f"""
                    Jesteś profesjonalnym instruktorem dronów FPV. Analizujesz parametry czarnej skrzynki pilota.
                    Poziom: {inst_skill}. Styl: {inst_ind}.
                    
                    DANE LOTU:
                    - Płynność Roll: {stats['jr']:.2f} (niskie wartości to gładki ruch)
                    - Płynność Pitch: {stats['jp']:.2f}
                    - Przeciążenia G-Force (Max): {stats['max_g']:.1f} G
                    
                    ZADANIE:
                    1. "ocena": Skala 1-10.
                    2. "diagnoza": Skomentuj styl lotu i przeciążenia. Jeżeli G-Force jest wysokie (>3G), zaznacz że dron musiał wykonywać agresywne manewry lub ostre nawroty. Dopasuj słownictwo do profilu {inst_skill}.
                    3. "zadanie": Narzuć jedno wysoce rygorystyczne zadanie do wykonania w goglach na następnej baterii.
                    
                    ZWRÓĆ TYLKO JSON: {{"ocena": 8, "diagnoza": "Cześć...", "zadanie": "Wykonaj..."}}
                    """
                    raw = generate_intel(prompt)
                    try:
                        js = json.loads(raw.replace("```json","").replace("```","").strip())
                        st.session_state.instructor_draft = f"### Analiza Taktyczna: {inst_ind}\n**WYDAJNOŚĆ:** {js['ocena']}/10\n\n**ODPRAWA TRENERA:**\n{js['diagnoza']}\n\n**CEL MISJI (NASTĘPNY LOT):**\n{js['zadanie']}"
                        st.session_state.temp_metrics = stats
                    except: st.error("AI napotkało problem przy analizie. Ponów.")
            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.instructor_draft:
            st.markdown("<p class='mono-text'>MODYFIKACJA RAPORTU PRZED WYSŁANIEM</p>", unsafe_allow_html=True)
            final_rep = st.text_area("Edytor", value=st.session_state.instructor_draft, height=250, label_visibility="collapsed")
            
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("ZATWIERDŹ I WYŚLIJ DO PILOTA"):
                match = re.search(r"WYDAJNOŚĆ:\s*(\d+)/10", final_rep)
                score = int(match.group(1)) if match else 5
                
                new_record = {
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "ocena": score, "raport": final_rep, 
                    "wideo": vid_link, "type": inst_ind, "premium": True, "stats": st.session_state.temp_metrics
                }
                history = target_data.get('zadania', [])
                history.append(new_record)
                supabase.table('konta').update({"zadania": history}).eq('email', selected_email).execute()
                
                st.session_state.instructor_draft = None
                st.success("Raport wprowadzony do systemu.")
                time.sleep(1)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
        st.markdown("<br><p class='mono-text'>ARCHIWUM MISJI</p>", unsafe_allow_html=True)
        for z in reversed(target_data.get('zadania', [])):
            if isinstance(z, dict):
                with st.expander(f"Misja: {z.get('data')} | Ocena: {z.get('ocena')}/10"):
                    st.markdown(z.get('raport'))
                    if 'stats' in z: render_history_stats(z['stats'])

# ==========================================
# 7. PANEL KURSANTA
# ==========================================
else:
    with st.sidebar:
        st.markdown(f"<p class='mono-text'>ZALOGOWANY PILOT: <br><span style='color: {ACCENT_LIGHT}; font-size: 1.2em;'>{user_data['imie']}</span></p>", unsafe_allow_html=True)
        st.metric("DOSTĘPNE TOKENY", user_data.get('tokeny', 0))
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("Zakończ Sesję"): st.session_state.auth_user = None; st.rerun()

    if st.session_state.flow_state == 'launchpad':
        render_logo()
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div class='bento-card'><h3>🚁 ANALIZA LOTU RZECZYWISTEGO</h3><p class='mono-text'>Formaty Blackbox: .BBL</p></div>", unsafe_allow_html=True)
            col_m, col_r, col_f = st.columns(3)
            if col_m.button("Cinematic"): st.session_state.industry_select="Cinematic / Płynny"; st.session_state.env_select="Real"; st.rerun()
            if col_r.button("Racing"): st.session_state.industry_select="Racing (Wyścigi)"; st.session_state.env_select="Real"; st.rerun()
            if col_f.button("Freestyle"): st.session_state.industry_select="Freestyle"; st.session_state.env_select="Real"; st.rerun()
        with c2:
            st.markdown("<div class='bento-card'><h3>🎮 DANE Z SYMULATORA</h3><p class='mono-text'>Velocidrone / Liftoff (.CSV)</p></div>", unsafe_allow_html=True)
            if st.button("Uruchom silnik analityczny symulatora", use_container_width=True): 
                st.session_state.industry_select="Symulator Treningowy"; st.session_state.env_select="Sim"; st.rerun()
        
        if st.session_state.industry_select:
            st.markdown("<br><h2>TWOJA RANGI I DOŚWIADCZENIE</h2>", unsafe_allow_html=True)
            skill = st.select_slider("Wskaż poziom wtajemniczenia dla Sztucznej Inteligencji:", options=["Początkujący", "Średniozaawansowany", "Ekspert"], value=st.session_state.skill_select, label_visibility="collapsed")
            st.session_state.skill_select = skill
            
            st.markdown("<br><div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("ZAINICJUJ PRZESYŁ DANYCH"):
                st.session_state.flow_state = 'upload'
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    elif st.session_state.flow_state == 'upload':
        st.markdown(f"<h2>SEKWENCJA ANALIZY: <span style='color: {ACCENT_LIGHT};'>{st.session_state.industry_select.upper()}</span></h2>", unsafe_allow_html=True)
        if st.button("← Przerwij i wróć"): 
            st.session_state.flow_state = 'launchpad'
            st.session_state.env_select = None
            st.session_state.industry_select = None
            st.rerun()

        c_tier, c_drop = st.columns([1, 2])
        with c_tier:
            st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
            st.markdown("<p class='mono-text'>WYBÓR MODUŁU ANALIZY</p>", unsafe_allow_html=True)
            tier = st.radio("Poziom szczegółowości:", ["Standard (1 Token)", "Premium + G-Force (2 Tokeny)"], label_visibility="collapsed")
            cost = 1 if "Standard" in tier else 2
            st.markdown(f"<p style='font-size: 0.9em; color: #8cbf8c; margin-top: 10px;'>Dostępne: <b>{user_data.get('tokeny', 0)} Tokenów</b></p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c_drop:
            u_log = st.file_uploader("Wrzuć logi lotu w to pole", type=['bbl', 'csv'], label_visibility="collapsed")
            
            if u_log:
                st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
                if st.button(f"ROZPOCZNIJ PRZETWARZANIE (-{cost} TOKENÓW)"):
                    if user_data.get('tokeny', 0) >= cost:
                        with st.status("Analizowanie fizyki lotu...", expanded=True) as status:
                            dec = get_decoder()
                            with open("/tmp/u.bbl", "wb") as f: f.write(u_log.getbuffer())
                            subprocess.run([dec, "/tmp/u.bbl"], stdout=subprocess.DEVNULL)
                            csvs = sorted(glob.glob("/tmp/u*.csv"))
                            
                            if csvs:
                                df = pd.read_csv(csvs[0])
                                stats = render_terminal_hud(df, mode=st.session_state.env_select, premium=(cost==2))
                                
                                if init_ai():
                                    prompt = f"""
                                    Jesteś zaawansowanym komputerem taktycznym i trenerem FPV. Pilot to {user_data['imie']}.
                                    Poziom: {st.session_state.skill_select}. Cel lotu: {st.session_state.industry_select}.
                                    
                                    DANE Z CZARNEJ SKRZYNKI:
                                    - Płynność Roll/Pitch: ~{stats['jr']:.2f} (niskie wartości oznaczają płynne wejścia w zakręty).
                                    - Maksymalne przeciążenie (G-Force): {stats['max_g']:.1f} G. 
                                    (Jeśli przeciążenie jest wysokie, np. ponad 3-4G, powiedz że pilot robił ekstremalne manewry.)
                                    
                                    ZADANIE:
                                    1. "ocena": 1-10.
                                    2. "diagnoza": Wykorzystaj wojskowy, techniczny styl (odpowiedni dla {st.session_state.skill_select}). Zinterpretuj wskaźniki G-Force i szarpania.
                                    3. "zadanie": Podaj jeden konkretny plan treningowy na następne podłączenie zasilania do drona.
                                    
                                    Formatuj w czystym JSON: {{"ocena": 8, "diagnoza": "...", "zadanie": "..."}}
                                    """
                                    raw_ai = generate_intel(prompt)
                                    try:
                                        js = json.loads(raw_ai.replace("```json","").replace("```","").strip())
                                        tag = "ANALIZA PREMIUM" if cost == 2 else "ANALIZA STANDARD"
                                        txt = f"### {tag}\n**SKUTECZNOŚĆ OPERACYJNA:** {js['ocena']}/10\n\n**DIAGNOZA SYSTEMOWA:**\n{js['diagnoza']}\n\n**CEL OPERACYJNY (TRENING):**\n{js['zadanie']}"
                                        
                                        history = user_data.get('zadania', [])
                                        history.append({
                                            "data": datetime.now().strftime("%Y-%m-%d %H:%M"), "ocena": js['ocena'], 
                                            "raport": txt, "type": st.session_state.industry_select, 
                                            "premium": (cost==2), "stats": stats
                                        })
                                        
                                        supabase.table('konta').update({
                                            "zadania": history, "tokeny": user_data['tokeny'] - cost
                                        }).eq('email', user_data['email']).execute()
                                        
                                        status.update(label="Analiza zakończona sukcesem.", state="complete", expanded=False)
                                        time.sleep(1)
                                        st.rerun()
                                    except: st.error("Awaria procesora AI. Zainicjuj ponownie.")
                    else: st.error("Niewystarczające zasoby (Tokeny).")
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><p class='mono-text'>ARCHIWUM OPERACJI</p>", unsafe_allow_html=True)
        for z in reversed(user_data.get('zadania', [])):
            if isinstance(z, dict):
                icon = "🟢" if z.get('premium') else "📄"
                with st.expander(f"{icon} {z.get('data')} | {z.get('type','Lot')} | Ocena: {z.get('ocena')}/10"):
                    st.markdown(z.get('raport'))
                    if 'stats' in z and z.get('premium'): render_history_stats(z['stats'])
            else:
                with st.expander("Stare zapisy"): st.markdown(str(z))
