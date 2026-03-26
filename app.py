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
# 2. MODERN PREMIUM UI (CSS)
# ==========================================
accent = st.session_state.theme_color

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Modern Slate Theme */
    .stApp {{ background-color: #0F172A; color: #F8FAFC; font-family: 'Inter', sans-serif; }}
    
    /* Eleganckie karty (Bento Box) */
    .bento-card {{
        background: #1E293B; border: 1px solid #334155; border-radius: 16px;
        padding: 24px; transition: all 0.3s ease; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }}
    .bento-card:hover {{ border-color: {accent}; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3); transform: translateY(-2px); }}
    
    /* Typografia */
    h1, h2, h3, h4 {{ font-weight: 700 !important; color: #FFFFFF !important; }}
    .mono-text {{ font-family: 'Inter', sans-serif; color: #94A3B8; font-size: 0.85em; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; }}
    
    /* Metryki i dane */
    div[data-testid="stMetric"] {{
        background: #1E293B; border: 1px solid #334155; border-radius: 12px; padding: 20px;
    }}
    div[data-testid="stMetricValue"] {{ font-weight: 700; color: {accent}; }}
    
    /* Przyciski standardowe */
    .stButton>button {{
        background: #1E293B; border: 1px solid #475569; color: #F8FAFC; border-radius: 8px;
        font-weight: 500; transition: 0.2s;
    }}
    .stButton>button:hover {{ background: #334155; color: #FFFFFF; border-color: #94A3B8; }}
    
    /* Przycisk Głównego Działania (CTA) */
    .cta-btn>button {{ background: {accent}; color: #FFFFFF; border: none; font-weight: 600; box-shadow: 0 4px 14px 0 {accent}40; }}
    .cta-btn>button:hover {{ background: {accent}EE; box-shadow: 0 6px 20px rgba(0,0,0,0.23); }}
    
    /* Pola tekstowe */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {{ background: #0F172A !important; border: 1px solid #334155 !important; color: #F8FAFC !important; border-radius: 8px !important; }}
    .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {{ border-color: {accent} !important; box-shadow: 0 0 0 1px {accent} !important; }}
    
    /* Panel boczny */
    section[data-testid="stSidebar"] {{ background-color: #0B0F19 !important; border-right: 1px solid #1E293B; }}
    
    /* Ukrycie elementów Streamlit */
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# GŁÓWNE LOGO PLATFORMY
def render_logo():
    st.markdown("""
        <div style='text-align: center; padding-bottom: 2rem;'>
            <h1 style='font-size: 2.5rem; margin-bottom: 0;'><span style='color: #3B82F6;'>🚁 FPV</span> AI Academy</h1>
            <p style='color: #94A3B8; font-size: 1.1rem; margin-top: 0.5rem;'>Inteligentna platforma analityczna dla pilotów</p>
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
            fig3.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', scene=dict(bgcolor='#0F172A'))
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
            # NAPRAWA: Dodano parametr key="reg_pass", aby Streamlit nie mylił tego pola z hasłem z pierwszej zakładki
            rpw = st.text_input("Hasło", type="password", key="reg_pass")
            rnm = st.text_input("Imię i Nazwisko / Pseudonim")
            if st.button("Zarejestruj się"):
                supabase.table('konta').insert({'email': rem, 'haslo': rpw, 'imie': rnm, 'rola': 'Kursant', 'tokeny': 10, 'zadania': []}).execute()
                st.success("Konto założone! Możesz się teraz zalogować.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# Pobieranie danych użytkownika
user_data = supabase.table('konta').select('*').eq('email', st.session_state.auth_user).execute().data[0]

# Funkcja do renderowania statystyk z historii
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
        
        # Zarządzanie tokenami
        st.markdown(f"<br><p class='mono-text'>PORTFEL KURSANTA: <span style='color: {accent}; font-weight: bold;'>{target_data.get('tokeny', 0)} Tokenów</span></p>", unsafe_allow_html=True)
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            dodaj_tok = st.number_input("Dodaj", min_value=1, max_value=100, value=5, label_visibility="collapsed")
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
                    prompt = f"""
                    Jesteś doświadczonym, empatycznym instruktorem dronów FPV (First Person View).
                    Analizujesz logi z lotu swojego ucznia. To jest DRON FPV (nie samochód, nie samolot pasażerski).
                    
                    Kontekst ucznia:
                    - Poziom umiejętności: {inst_skill}.
                    - Styl lotu: {inst_ind}.
                    
                    Dane z czarnej skrzynki:
                    - Szarpnięcia drążków (Jerk): {stats['jr']:.2f} (niższy wynik to płynniejszy lot).
                    - Wibracje na silnikach / kondycja: {stats['health']}%.
                    
                    Twoje zadanie:
                    1. Oceń lot w skali 1-10.
                    2. Napisz "diagnozę". Mów jak człowiek do człowieka (np. "Cześć! Widzę, że świetnie radzisz sobie z... ale popracuj nad..."). Używaj przyjaznego tonu instruktora FPV.
                    3. Zaproponuj JEDNO realne, praktyczne zadanie treningowe z drona FPV na następny lot (np. "Wylataj dwa pakiety robiąc gładkie Power Loopy" lub "Zrób 5 okrążeń wokół drzewa ćwicząc stałą wysokość").
                    
                    Zwróć TYLKO czysty JSON: {{"ocena": 8, "diagnoza": "Twój komentarz", "zadanie": "Ćwiczenie"}}
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
            final_rep = st.text_area("Możesz dowolnie zmienić ten tekst przed wysłaniem:", value=st.session_state.instructor_draft, height=250, label_visibility="collapsed")
            
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("WYŚLIJ RAPORT DO KURSANTA"):
                match = re.search(r"OCENA:\s*(\d+)/10", final_rep)
                score = int(match.group(1)) if match else 5
                
                new_record = {
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "ocena": score, "raport": final_rep, "wideo": vid_link, 
                    "type": inst_ind, "premium": True,
                    "stats": st.session_state.temp_metrics  # ZAPISUJEMY STATYSTYKI DO HISTORII!
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
                                    prompt = f"""
                                    Jesteś doświadczonym, empatycznym instruktorem dronów FPV. Twój kursant to {user_data['imie']}.
                                    Poziom ucznia: {st.session_state.skill_select}. Styl lotu: {st.session_state.industry_select}.
                                    
                                    Dane z czarnej skrzynki DRONA FPV (to nie jazda autem!):
                                    - Płynność (Jerk): {stats['jr']:.2f}.
                                    
                                    Twoje zadanie:
                                    1. Oceń lot (1-10).
                                    2. Diagnoza: Przywitaj się, pochwal go za postępy, powiedz co zrobił dobrze, a nad czym musi popracować w locie FPV. Używaj przyjaznego, naturalnego języka.
                                    3. Zadanie: Zaproponuj JEDNO realne ćwiczenie (np. "Wylataj dwa pakiety wokół tego samego drzewa").
                                    
                                    Zwróć TYLKO czysty JSON: {{"ocena": 8, "diagnoza": "Cześć! Super lot...", "zadanie": "Następnym razem..."}}
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
                                            "stats": stats # ZAPISUJEMY WYNIKI NUMERYCZNE DLA WYKRESÓW W HISTORII!
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
                    # Jeśli raport ma zapisane statystyki (np. był Premium) - wyświetlamy je!
                    if 'stats' in z and z.get('premium'):
                        render_history_stats(z['stats'])
            else:
                with st.expander("Stary Raport (Archiwum)"): st.markdown(str(z))
