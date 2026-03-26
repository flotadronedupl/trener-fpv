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
st.set_page_config(page_title="FPV AI Academy", page_icon="🛩️", layout="wide", initial_sidebar_state="expanded")

def init_session():
    defaults = {
        'auth_user': None, 'role': None, 'flow_state': 'launchpad',
        'env_select': None, 'industry_select': None, 'skill_select': 'Średniozaawansowany',
        'theme_color': '#3B82F6', 'instructor_draft': None, 'temp_metrics': {}
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

init_session()

# ==========================================
# 2. MODERN PREMIUM UI (CSS & Glassmorphism)
# ==========================================
accent = st.session_state.theme_color

# Dodajemy nowoczesne efekty wizualne
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Globalne Tło - bardzo ciemny, głęboki granat z subtelnym gradientem */
    .stApp {{ 
        background: radial-gradient(circle at top, #111827, #030712); 
        color: #F8FAFC; 
        font-family: 'Inter', sans-serif; 
    }}
    
    /* Eleganckie karty z efektem Glassmorphism (szkła) */
    .bento-card {{
        background: rgba(30, 41, 59, 0.4); 
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08); 
        border-radius: 24px;
        padding: 30px; 
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1); 
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }}
    .bento-card:hover {{ 
        border-color: {accent}80; 
        box-shadow: 0 20px 40px -10px {accent}40; 
        transform: translateY(-4px); 
    }}
    
    /* Typografia i nagłówki z gradientem */
    h1, h2, h3, h4 {{ font-weight: 800 !important; color: #FFFFFF !important; letter-spacing: -0.5px; }}
    .mono-text {{ 
        font-family: 'Inter', sans-serif; 
        color: #94A3B8; 
        font-size: 0.8rem; 
        text-transform: uppercase; 
        font-weight: 700; 
        letter-spacing: 0.1em; 
    }}
    
    /* Nowoczesne Metryki */
    div[data-testid="stMetric"] {{
        background: rgba(30, 41, 59, 0.4); 
        border: 1px solid rgba(255, 255, 255, 0.05); 
        border-radius: 16px; 
        padding: 24px;
        box-shadow: inset 0 2px 4px 0 rgba(255, 255, 255, 0.02);
    }}
    div[data-testid="stMetricValue"] {{ font-weight: 800; color: {accent}; font-size: 2.2rem; }}
    
    /* Standardowe Przyciski */
    .stButton>button {{
        background: rgba(30, 41, 59, 0.6); 
        border: 1px solid rgba(255,255,255,0.1); 
        color: #E2E8F0; 
        border-radius: 12px;
        font-weight: 600; 
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }}
    .stButton>button:hover {{ 
        background: rgba(255,255,255,0.1); 
        color: #FFFFFF; 
        border-color: {accent}; 
    }}
    
    /* Główny przycisk akcji (Glow effect) */
    .cta-btn>button {{ 
        background: linear-gradient(135deg, {accent}, #6366F1); 
        color: #FFFFFF; 
        border: none; 
        font-weight: 700; 
        letter-spacing: 0.5px;
        box-shadow: 0 4px 20px 0 {accent}60; 
        border-radius: 12px;
        padding: 0.75rem 1.5rem;
    }}
    .cta-btn>button:hover {{ 
        box-shadow: 0 8px 30px rgba(99, 102, 241, 0.6); 
        transform: scale(1.02);
    }}
    
    /* Pola wprowadzania danych */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {{ 
        background: rgba(15, 23, 42, 0.6) !important; 
        border: 1px solid rgba(255,255,255,0.1) !important; 
        color: #F8FAFC !important; 
        border-radius: 12px !important; 
        padding: 10px 15px !important;
    }}
    .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {{ 
        border-color: {accent} !important; 
        box-shadow: 0 0 0 2px {accent}40 !important; 
    }}
    
    /* Panele, menu i ukrycie brandingu Streamlit */
    section[data-testid="stSidebar"] {{ background-color: rgba(3, 7, 18, 0.8) !important; border-right: 1px solid rgba(255,255,255,0.05); backdrop-filter: blur(10px); }}
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# NOWE WŁASNE LOGO WEKTOROWE
def render_logo():
    # Profesjonalne wektorowe logo drona w formacie SVG
    svg_logo = f"""
    <svg width="80" height="80" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M5.5 5.5h.01M18.5 5.5h.01M5.5 18.5h.01M18.5 18.5h.01" stroke="{accent}" stroke-width="3" stroke-linecap="round"/>
      <path d="M12 12L5.5 5.5M12 12l6.5-6.5M12 12l-6.5 6.5M12 12l6.5 6.5" stroke="#94A3B8" stroke-width="1.5" stroke-linecap="round"/>
      <circle cx="12" cy="12" r="3" fill="#1E293B" stroke="{accent}" stroke-width="2"/>
    </svg>
    """
    st.markdown(f"""
        <div style='text-align: center; padding-bottom: 3rem; display: flex; flex-direction: column; align-items: center;'>
            {svg_logo}
            <h1 style='font-size: 3rem; margin-bottom: 0; margin-top: 10px; background: linear-gradient(90deg, #FFFFFF, #94A3B8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
                FPV AI Academy
            </h1>
            <p style='color: #64748B; font-size: 1.1rem; margin-top: 0.5rem; font-weight: 500; letter-spacing: 1px;'>NEXT-GEN FLIGHT ANALYTICS</p>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 3. RDZEŃ SYSTEMU (Supabase & Gemini)
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
        return f'{{"ocena": 0, "diagnoza": "Przepraszamy, wystąpił błąd komunikacji z AI. Instruktor musi dodać komentarz ręcznie.", "zadanie": "Brak zadań - błąd systemu."}}'

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
# 4. SILNIK WIZUALIZACJI DANYCH
# ==========================================
def render_terminal_hud(df, mode="Real", premium=False):
    color = st.session_state.theme_color
    try:
        thr = [c for c in df.columns if 'rcCommand[3]' in c or ('rcCommand' in c and '3' in c)][0]
        roll = [c for c in df.columns if 'rcCommand[0]' in c or ('rcCommand' in c and '0' in c)][0]
        pitch = [c for c in df.columns if 'rcCommand[1]' in c or ('rcCommand' in c and '1' in c)][0]
    except:
        st.error("Wystąpił problem: Nie znaleziono danych o wychyleniach drążków w tym pliku.")
        return None

    jr, jp = df[roll].diff().abs().mean(), df[pitch].diff().abs().mean()
    avg_t = df[thr].mean()
    smoothness = max(0, 10 - (jr + jp))
    health = max(0, min(100, 100 - ((jr + jp) * 12)))
    
    st.markdown("<p class='mono-text'>KLUCZOWE WSKAŹNIKI LOTU</p>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("Średni Gaz", f"{avg_t:.0f}")
    m2.metric("Płynność Lotu", f"{smoothness:.1f} / 10")
    m3.metric("Kondycja Sprzętu", f"{health:.0f}%")

    if premium:
        st.markdown("<br><p class='mono-text'>ZAAWANSOWANA ANALIZA</p>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["Wykres Drążków", "Trajektoria 3D", "Zużycie Baterii"])
        
        pdf = df.iloc[::max(1, len(df)//5000)]
        
        with t1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=pdf[thr], name="Gaz", line=dict(color='#64748B', width=1)))
            fig.add_trace(go.Scatter(y=pdf[roll], name="Roll", line=dict(color=color, width=2)))
            fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
        with t2:
            fig3 = go.Figure(data=[go.Scatter3d(x=pdf[roll].cumsum()/500, y=pdf[pitch].cumsum()/500, z=np.arange(len(pdf)), 
                                mode='lines', line=dict(color=pdf[thr], colorscale='Blues', width=5))])
            fig3.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', scene=dict(bgcolor='rgba(15, 23, 42, 0)'))
            st.plotly_chart(fig3, use_container_width=True)
            
        with t3:
            v_col = [c for c in df.columns if 'vbat' in c.lower()]
            if v_col and mode == "Real":
                f_bat = make_subplots(specs=[[{"secondary_y": True}]])
                f_bat.add_trace(go.Scatter(y=pdf[v_col[0]]/100, name="Napięcie (V)", line=dict(color='#F8FAFC')), secondary_y=False)
                f_bat.add_trace(go.Scatter(y=pdf[thr], name="Gaz", fill='tozeroy', opacity=0.1, line=dict(color=color)), secondary_y=True)
                f_bat.update_layout(template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(f_bat, use_container_width=True)
            else:
                st.info("Brak danych o baterii w przypadku symulatora.")
            
    return {"jr": float(jr), "jp": float(jp), "health": float(health), "avg_t": float(avg_t)}

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
            if st.button("Wejdź do panelu"):
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
            rnm = st.text_input("Imię i Nazwisko / Pseudonim")
            if st.button("Zarejestruj się"):
                supabase.table('konta').insert({'email': rem, 'haslo': rpw, 'imie': rnm, 'rola': 'Kursant', 'tokeny': 10, 'zadania': []}).execute()
                st.success("Konto założone! Możesz się teraz zalogować.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

user_data = supabase.table('konta').select('*').eq('email', st.session_state.auth_user).execute().data[0]

def render_history_stats(stats_dict):
    st.markdown("<p class='mono-text' style='margin-top: 15px;'>ZAPISANE PARAMETRY LOTU</p>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Kondycja drona", f"{stats_dict.get('health', 0):.0f}%")
    c2.metric("Szarpnięcia Roll", f"{stats_dict.get('jr', 0):.2f}")
    c3.metric("Szarpnięcia Pitch", f"{stats_dict.get('jp', 0):.2f}")

# ==========================================
# 6. PANEL INSTRUKTORA
# ==========================================
if user_data['rola'] == "Instruktor":
    render_logo()
    
    col_nav, col_main = st.columns([1, 3])
    
    with col_nav:
        st.markdown(f"<div class='bento-card'><p class='mono-text'>TWOI KURSANCI</p>", unsafe_allow_html=True)
        cadets = supabase.table('konta').select('*').eq('rola', 'Kursant').execute().data
        if not cadets: st.warning("Brak kursantów w bazie."); st.stop()
        selected_email = st.radio("Wybierz kursanta:", [k['email'] for k in cadets], label_visibility="collapsed")
        target_data = next(k for k in cadets if k['email'] == selected_email)
        
        st.markdown(f"<br><p class='mono-text'>PORTFEL KURSANTA: <span style='color: {accent}; font-weight: bold;'>{target_data.get('tokeny', 0)} Tokenów</span></p>", unsafe_allow_html=True)
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1: dodaj_tok = st.number_input("Dodaj", min_value=1, max_value=100, value=5, label_visibility="collapsed")
        with col_t2:
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("DODAJ"):
                nowy_stan = target_data.get('tokeny', 0) + dodaj_tok
                supabase.table('konta').update({"tokeny": nowy_stan}).eq('email', selected_email).execute()
                st.toast(f"Zasilono konto o {dodaj_tok} tokenów.", icon="💰")
                time.sleep(1)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><p class='mono-text'>PARAMETRY ANALIZY</p>", unsafe_allow_html=True)
        inst_env = st.selectbox("Środowisko", ["Lot Rzeczywisty", "Symulator"])
        inst_ind = "Standard"
        if inst_env == "Lot Rzeczywisty":
            inst_ind = st.selectbox("Styl Lotu", ["Cinematic / Płynny", "Racing (Wyścigi)", "Freestyle"])
        inst_skill = st.selectbox("Zaawansowanie Kursanta", ["Początkujący", "Średniozaawansowany", "Ekspert"])
        
        st.session_state.theme_color = '#10B981' if 'Cinematic' in inst_ind else '#F59E0B' if 'Racing' in inst_ind else '#3B82F6'
        
        st.markdown("<br><p class='mono-text'>USTAWIENIA</p>", unsafe_allow_html=True)
        if st.button("Wyloguj się"): st.session_state.auth_user = None; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_main:
        st.markdown(f"<h2>Profil: {target_data['imie']}</h2>", unsafe_allow_html=True)
        
        c_upl, c_vid = st.columns(2)
        with c_upl: log_file = st.file_uploader("Wgraj Plik Telemetrii (BBL/CSV)", type=['bbl', 'csv'], label_visibility="collapsed")
        with c_vid: vid_link = st.text_input("Link do wideo (YouTube/Drive)", placeholder="https://...")

        df_active = None
        if log_file:
            with st.status("Przetwarzanie danych lotu...", expanded=False) as status:
                if log_file.name.endswith('.csv'): 
                    df_active = pd.read_csv(log_file)
                else:
                    st.write("Dekodowanie czarnej skrzynki...")
                    dec = get_decoder()
                    with open("/tmp/i.bbl", "wb") as f: f.write(log_file.getbuffer())
                    subprocess.run([dec, "/tmp/i.bbl"], stdout=subprocess.DEVNULL)
                    csvs = sorted(glob.glob("/tmp/i*.csv"))
                    if csvs: df_active = pd.read_csv(csvs[0])
                status.update(label="Dane załadowane pomyślnie", state="complete", expanded=False)

        if df_active is not None:
            stats = render_terminal_hud(df_active, mode="Real" if inst_env=="Lot Rzeczywisty" else "Sim", premium=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("GENERUJ OPINIĘ AI"):
                if init_ai():
                    # ZAAWANSOWANY PROMPT INSTRUKTORSKI
                    prompt = f"""
                    Jesteś elitarnym, empatycznym instruktorem dronów FPV. Analizujesz lot kursanta.
                    Poziom umiejętności: {inst_skill}. Styl lotu: {inst_ind}.
                    
                    ZASADY KOMUNIKACJI WEDŁUG POZIOMU:
                    - Początkujący: Skup się na podstawach, trzymaniu wysokości, płynnych ruchach. Unikaj trudnego żargonu, chwal za drobne sukcesy.
                    - Średniozaawansowany: Wprowadzaj pojęcia takie jak 'throttle management', 'proporcje roll/pitch'. Analizuj dokładniej płynność zakrętów.
                    - Ekspert: Oczekuj perfekcji. Używaj profesjonalnego żargonu (propwash, rates, PID tuning, micro-adjustments, feedforward). Bądź bardzo surowy w ocenie płynności drążków.
                    
                    DANE TELEMETRYCZNE:
                    - Płynność drążków (Jerk): {stats['jr']:.2f} (wynik bliżej 0-2 to lot bardzo płynny, powyżej 4 to nerwowy/szarpany).
                    - Wibracje i stabilność (Kondycja): {stats['health']}%.
                    
                    Twoje zadanie to wygenerowanie oceny, komentarza i zadania domowego w formacie JSON.
                    1. Oceń lot (1-10). Bądź obiektywny względem poziomu zaawansowania.
                    2. Stwórz diagnozę dostosowaną językowo do poziomu ({inst_skill}). Wskaż na podstawie danych z Jerk i Kondycji, co kursant robi dobrze, a co musi poprawić.
                    3. Zaproponuj JEDNO precyzyjne ćwiczenie na następny trening z użyciem gogli FPV.
                    
                    Zwróć TYLKO czysty obiekt JSON:
                    {{"ocena": 8, "diagnoza": "Cześć! Super lot, jednak...", "zadanie": "Następnym razem zrób..."}}
                    """
                    raw = generate_intel(prompt)
                    try:
                        js = json.loads(raw.replace("```json","").replace("```","").strip())
                        st.session_state.instructor_draft = f"### Raport z lotu: {inst_ind}\n**OCENA:** {js['ocena']}/10\n\n**KOMENTARZ TRENERA:**\n{js['diagnoza']}\n\n**CEL NA NASTĘPNY TRENING:**\n{js['zadanie']}"
                        st.session_state.temp_metrics = stats
                    except: st.error("Problem z wygenerowaniem odpowiedzi AI. Spróbuj jeszcze raz.")
            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.instructor_draft:
            st.markdown("<p class='mono-text'>TWÓJ KOMENTARZ (DO EDYCJI)</p>", unsafe_allow_html=True)
            final_rep = st.text_area("Możesz edytować ten tekst przed wysłaniem:", value=st.session_state.instructor_draft, height=250, label_visibility="collapsed")
            
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("WYŚLIJ RAPORT DO KURSANTA"):
                match = re.search(r"OCENA:\s*(\d+)/10", final_rep)
                score = int(match.group(1)) if match else 5
                
                new_record = {
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "ocena": score, "raport": final_rep, "wideo": vid_link, 
                    "type": inst_ind, "premium": True,
                    "stats": st.session_state.temp_metrics
                }
                history = target_data.get('zadania', [])
                history.append(new_record)
                supabase.table('konta').update({"zadania": history}).eq('email', selected_email).execute()
                
                st.session_state.instructor_draft = None
                st.success("Raport wysłany pomyślnie!")
                time.sleep(1)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
        st.markdown("<br><p class='mono-text'>HISTORIA RAPORTÓW KURSANTA</p>", unsafe_allow_html=True)
        for z in reversed(target_data.get('zadania', [])):
            if isinstance(z, dict):
                with st.expander(f"Data: {z.get('data')} | Ocena: {z.get('ocena')}/10"):
                    st.markdown(z.get('raport'))
                    if 'stats' in z: render_history_stats(z['stats'])
            else:
                with st.expander("Stary Raport (Archiwum)"): st.markdown(str(z))

# ==========================================
# 7. PANEL KURSANTA
# ==========================================
else:
    with st.sidebar:
        st.markdown(f"<p class='mono-text'>ZALOGOWANO JAKO: <br><span style='color: #fff; font-size: 1.2em;'>{user_data['imie']}</span></p>", unsafe_allow_html=True)
        st.metric("TWÓJ PORTFEL (TOKENY)", user_data.get('tokeny', 0))
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("Wyloguj się"): st.session_state.auth_user = None; st.rerun()

    if st.session_state.flow_state == 'launchpad':
        render_logo()
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div class='bento-card'><h3>🚁 LOT RZECZYWISTY</h3><p class='mono-text'>Wgraj plik z drona (.bbl)</p></div>", unsafe_allow_html=True)
            col_m, col_r, col_f = st.columns(3)
            if col_m.button("Cinematic"): st.session_state.industry_select="Cinematic / Płynny"; st.session_state.theme_color="#10B981"; st.session_state.env_select="Real"; st.rerun()
            if col_r.button("Racing"): st.session_state.industry_select="Racing (Wyścigi)"; st.session_state.theme_color="#F59E0B"; st.session_state.env_select="Real"; st.rerun()
            if col_f.button("Freestyle"): st.session_state.industry_select="Freestyle"; st.session_state.theme_color="#3B82F6"; st.session_state.env_select="Real"; st.rerun()
        with c2:
            st.markdown("<div class='bento-card'><h3>🎮 SYMULATOR</h3><p class='mono-text'>Wgraj logi z Liftoff / Velocidrone (.csv)</p></div>", unsafe_allow_html=True)
            if st.button("Analizuj lot z symulatora", use_container_width=True): 
                st.session_state.industry_select="Symulator Treningowy"; st.session_state.theme_color="#8B5CF6"; st.session_state.env_select="Sim"; st.rerun()
        
        if st.session_state.industry_select:
            st.markdown("<br><h2>TWOJE DOŚWIADCZENIE</h2>", unsafe_allow_html=True)
            skill = st.select_slider("Wybierz swój aktualny poziom, byśmy mogli dostosować ocenę AI:", options=["Początkujący", "Średniozaawansowany", "Ekspert"], value=st.session_state.skill_select, label_visibility="collapsed")
            st.session_state.skill_select = skill
            
            st.markdown("<br><div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("PRZEJDŹ DO WGRYWANIA PLIKU"):
                st.session_state.flow_state = 'upload'
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    elif st.session_state.flow_state == 'upload':
        st.markdown(f"<h2>ANALIZA LOTU: <span style='color: {st.session_state.theme_color};'>{st.session_state.industry_select.upper()}</span></h2>", unsafe_allow_html=True)
        if st.button("← Wróć do menu głównego"): 
            st.session_state.flow_state = 'launchpad'
            st.session_state.env_select = None
            st.session_state.industry_select = None
            st.rerun()

        c_tier, c_drop = st.columns([1, 2])
        with c_tier:
            st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
            st.markdown("<p class='mono-text'>WYBÓR PAKIETU</p>", unsafe_allow_html=True)
            tier = st.radio("Jaki raport wygenerować?", ["Podstawowy (1 Token)", "Premium (2 Tokeny)"], label_visibility="collapsed")
            cost = 1 if "Podstawowy" in tier else 2
            st.markdown(f"<p style='font-size: 0.9em; color: #94A3B8; margin-top: 10px;'>Posiadasz: <b>{user_data.get('tokeny', 0)} Tokenów</b></p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with c_drop:
            u_log = st.file_uploader("Upuść tutaj plik .bbl lub .csv", type=['bbl', 'csv'], label_visibility="collapsed")
            
            if u_log:
                st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
                if st.button(f"ROZPOCZNIJ ANALIZĘ (-{cost} TOKENÓW)"):
                    if user_data.get('tokeny', 0) >= cost:
                        with st.status("Analizowanie danych...", expanded=True) as status:
                            st.write("Wydobywanie danych telemetrycznych...")
                            dec = get_decoder()
                            with open("/tmp/u.bbl", "wb") as f: f.write(u_log.getbuffer())
                            subprocess.run([dec, "/tmp/u.bbl"], stdout=subprocess.DEVNULL)
                            csvs = sorted(glob.glob("/tmp/u*.csv"))
                            
                            if csvs:
                                st.write("Tworzenie wizualizacji...")
                                df = pd.read_csv(csvs[0])
                                
                                stats = render_terminal_hud(df, mode=st.session_state.env_select, premium=(cost==2))
                                
                                st.write("Opracowywanie raportu przez instruktora AI...")
                                if init_ai():
                                    # ZAAWANSOWANY PROMPT KURSANT
                                    prompt = f"""
                                    Jesteś elitarnym trenerem dronów FPV. Przeprowadzasz analizę automatyczną dla kursanta: {user_data['imie']}.
                                    Poziom ucznia: {st.session_state.skill_select}. Styl lotu: {st.session_state.industry_select}.
                                    
                                    WYTYCZNE ZALEŻNE OD POZIOMU:
                                    - Początkujący: Motywuj i chwal za odwagę. Skup się na gładkim poruszaniu prawym drążkiem (pitch/roll). Używaj języka łatwego do przyswojenia.
                                    - Średniozaawansowany: Analizuj "throttle management" (kontrolę gazu) i zjawisko szarpania. Wskaż, że gładkie ruchy = lepsze wideo.
                                    - Ekspert: Zero litości. Wejdź głęboko w detale mikrokorekt drążków i zjawiska "propwash". Wymagaj pełnej integracji człowieka z maszyną.

                                    DANE Z CZARNEJ SKRZYNKI:
                                    - Płynność drążków (Jerk): {stats['jr']:.2f} (optymalnie poniżej 2).
                                    - Kondycja / stabilność lotu: {stats['health']}%.
                                    
                                    WYMAGANY WYNIK - Czysty JSON:
                                    1. "ocena": Oceń lot 1-10 stosownie do wybranego poziomu.
                                    2. "diagnoza": Wyjaśnij kursantowi, co oznacza jego wskaźnik "Jerk" ({stats['jr']:.2f}) w praktyce i co musi zmienić w obsłudze aparatury.
                                    3. "zadanie": Daj JEDNO wysoce precyzyjne ćwiczenie na kolejny lot FPV (np. 'Lataj ósemki z zablokowaną kamerą pod kątem 30 stopni').
                                    
                                    Zwróć TYLKO czysty obiekt JSON:
                                    {{"ocena": 8, "diagnoza": "Cześć! Super lot...", "zadanie": "Następnym razem..."}}
                                    """
                                    raw_ai = generate_intel(prompt)
                                    try:
                                        js = json.loads(raw_ai.replace("```json","").replace("```","").strip())
                                        tag = "PREMIUM" if cost == 2 else "PODSTAWOWY"
                                        txt = f"### RAPORT {tag}\n**OCENA:** {js['ocena']}/10\n\n**KOMENTARZ TRENERA:**\n{js['diagnoza']}\n\n**CEL NA NASTĘPNY TRENING:**\n{js['zadanie']}"
                                        
                                        history = user_data.get('zadania', [])
                                        history.append({
                                            "data": datetime.now().strftime("%Y-%m-%d %H:%M"), 
                                            "ocena": js['ocena'], 
                                            "raport": txt, 
                                            "type": st.session_state.industry_select, 
                                            "premium": (cost==2),
                                            "stats": stats
                                        })
                                        
                                        supabase.table('konta').update({
                                            "zadania": history, 
                                            "tokeny": user_data['tokeny'] - cost
                                        }).eq('email', user_data['email']).execute()
                                        
                                        status.update(label="Raport Gotowy", state="complete", expanded=False)
                                        time.sleep(1)
                                        st.rerun()
                                    except: st.error("Niestety AI miało problem z przetworzeniem zapytania. Spróbuj ponownie.")
                    else: st.error("Niewystarczająca liczba tokenów na koncie.")
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><p class='mono-text'>TWOJE POSTĘPY I HISTORIA LOTÓW</p>", unsafe_allow_html=True)
        for z in reversed(user_data.get('zadania', [])):
            if isinstance(z, dict):
                icon = "💎" if z.get('premium') else "📄"
                with st.expander(f"{icon} {z.get('data')} | {z.get('type','Lot')} | Ocena: {z.get('ocena')}/10"):
                    st.markdown(z.get('raport'))
                    if 'stats' in z and z.get('premium'):
                        render_history_stats(z['stats'])
            else:
                with st.expander("Stary Raport (Archiwum)"): st.markdown(str(z))
