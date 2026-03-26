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
# 1. ENTERPRISE CONFIG & STATE
# ==========================================
st.set_page_config(page_title="FCIS | Dowództwo Danych", page_icon="⬛", layout="wide", initial_sidebar_state="collapsed")

def init_session():
    defaults = {
        'auth_user': None, 'role': None, 'flow_state': 'launchpad',
        'env_select': None, 'industry_select': None, 'skill_select': 'Pilot',
        'theme_color': '#ededed', 'instructor_draft': None, 'temp_metrics': {}
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

init_session()

# ==========================================
# 2. VERCEL / PALANTIR DARK UI (CSS) - BEZ ZMIAN WIZUALNYCH
# ==========================================
accent = st.session_state.theme_color

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    /* Vercel Ultra-Dark Theme */
    .stApp {{ background-color: #000000; color: #ededed; font-family: 'Inter', sans-serif; }}
    
    /* Bento Box UI Cards */
    .bento-card {{
        background: #0a0a0a; border: 1px solid #222; border-radius: 12px;
        padding: 24px; transition: all 0.3s ease;
    }}
    .bento-card:hover {{ border-color: {accent}55; box-shadow: 0 8px 30px rgba(0,0,0,0.5); transform: translateY(-2px); }}
    
    /* Typography */
    h1, h2, h3 {{ font-weight: 800 !important; letter-spacing: -0.05em !important; color: #fff !important; }}
    .mono-text {{ font-family: 'JetBrains Mono', monospace; color: #888; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.1em; }}
    
    /* Minimalist Metrics */
    div[data-testid="stMetric"] {{
        background: #0a0a0a; border: 1px solid #1a1a1a; border-radius: 8px; padding: 20px;
    }}
    div[data-testid="stMetricValue"] {{ font-family: 'JetBrains Mono', monospace; font-weight: 700; color: {accent}; }}
    
    /* Stealth Buttons */
    .stButton>button {{
        background: #111; border: 1px solid #333; color: #ededed; border-radius: 6px;
        font-family: 'Inter', sans-serif; font-weight: 600; transition: 0.2s;
    }}
    .stButton>button:hover {{ background: #ededed; color: #000; border-color: #ededed; }}
    
    /* Primary CTA */
    .cta-btn>button {{ background: {accent}; color: #000; border: none; }}
    .cta-btn>button:hover {{ background: #fff; box-shadow: 0 0 15px {accent}88; }}
    
    /* Clean Inputs */
    .stTextInput input, .stTextArea textarea, .stNumberInput input {{ background: #0a0a0a !important; border: 1px solid #333 !important; color: #fff !important; }}
    .stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {{ border-color: {accent} !important; box-shadow: none !important; }}
    
    /* Hide Streamlit Branding */
    #MainMenu {{visibility: hidden;}} footer {{visibility: hidden;}} header {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. CORE INFRASTRUCTURE (Supabase & Gemini)
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
        return f'{{"ocena": 0, "diagnoza": "BŁĄD SYSTEMU: BRAK POŁĄCZENIA Z AI", "zadanie": "WYMAGANA RĘCZNA KOREKTA"}}'

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
# 4. DATA VISUALIZATION ENGINE (Palantir Style)
# ==========================================
def render_terminal_hud(df, mode="Real", premium=False):
    color = st.session_state.theme_color
    try:
        thr = [c for c in df.columns if 'rcCommand[3]' in c or ('rcCommand' in c and '3' in c)][0]
        roll = [c for c in df.columns if 'rcCommand[0]' in c or ('rcCommand' in c and '0' in c)][0]
        pitch = [c for c in df.columns if 'rcCommand[1]' in c or ('rcCommand' in c and '1' in c)][0]
    except:
        st.error("BŁĄD DANYCH: Nie odnaleziono osi telemetrii w pliku.")
        return None

    jr, jp = df[roll].diff().abs().mean(), df[pitch].diff().abs().mean()
    avg_t = df[thr].mean()
    smoothness = max(0, 10 - (jr + jp))
    health = max(0, min(100, 100 - ((jr + jp) * 12)))
    
    st.markdown("<p class='mono-text'>GŁÓWNE WSKAŹNIKI SYSTEMU (KPI)</p>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("OBCIĄŻENIE GAZU", f"{avg_t:.0f}")
    m2.metric("PŁYNNOŚĆ LOTU", f"{smoothness:.1f} / 10")
    m3.metric("INTEGRALNOŚĆ SPRZĘTU", f"{health:.0f}%")

    if premium:
        st.markdown("<br><p class='mono-text'>GŁĘBOKA ANALITYKA</p>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["TELEMETRIA OSI", "WEKTOROWA ŚCIEŻKA 3D", "DIAGNOSTYKA ZASILANIA"])
        
        pdf = df.iloc[::max(1, len(df)//5000)] # Downsample for web performance
        
        with t1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(y=pdf[thr], name="GAZ (THR)", line=dict(color='#333', width=1)))
            fig.add_trace(go.Scatter(y=pdf[roll], name="ROLL", line=dict(color=color, width=2)))
            fig.update_layout(template="plotly_dark", height=300, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)
            
        with t2:
            fig3 = go.Figure(data=[go.Scatter3d(x=pdf[roll].cumsum()/500, y=pdf[pitch].cumsum()/500, z=np.arange(len(pdf)), 
                                mode='lines', line=dict(color=pdf[thr], colorscale='Greys', width=4))])
            fig3.update_layout(template="plotly_dark", height=450, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', scene=dict(bgcolor='#000'))
            st.plotly_chart(fig3, use_container_width=True)
            
        with t3:
            v_col = [c for c in df.columns if 'vbat' in c.lower()]
            if v_col and mode == "Real":
                f_bat = make_subplots(specs=[[{"secondary_y": True}]])
                f_bat.add_trace(go.Scatter(y=pdf[v_col[0]]/100, name="NAPIĘCIE (V)", line=dict(color='#ededed')), secondary_y=False)
                f_bat.add_trace(go.Scatter(y=pdf[thr], name="OBCIĄŻENIE", fill='tozeroy', opacity=0.1, line=dict(color=color)), secondary_y=True)
                f_bat.update_layout(template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(f_bat, use_container_width=True)
            else:
                st.info("Brak telemetrii zasilania w pliku z Symulatora.")
            
    return {"jr": jr, "jp": jp, "health": health}

# ==========================================
# 5. ZERO-FRICTION AUTHENTICATION
# ==========================================
if st.session_state.auth_user is None:
    st.markdown("<br><br><br><h1 style='text-align: center;'>FCIS</h1><p class='mono-text' style='text-align: center;'>ZAAWANSOWANY SYSTEM DOWODZENIA FPV</p><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
        t1, t2 = st.tabs(["Logowanie", "Rejestracja"])
        with t1:
            em = st.text_input("ID Operatora (Email)")
            pw = st.text_input("Kod Autoryzacyjny (Hasło)", type="password")
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("Autoryzuj Dostęp"):
                res = supabase.table('konta').select('*').eq('email', em).execute()
                if res.data and res.data[0]['haslo'] == pw:
                    st.session_state.auth_user = em
                    st.session_state.role = res.data[0]['rola']
                    st.rerun()
                else: st.error("Odmowa dostępu. Nieprawidłowe dane.")
            st.markdown("</div>", unsafe_allow_html=True)
        with t2:
            rem = st.text_input("Nowe ID Operatora")
            rpw = st.text_input("Nowy Kod Autoryzacyjny", type="password")
            rnm = st.text_input("Kryptonim / Imię")
            if st.button("Zainicjuj Profil"):
                supabase.table('konta').insert({'email': rem, 'haslo': rpw, 'imie': rnm, 'rola': 'Kursant', 'tokeny': 10, 'zadania': []}).execute()
                st.success("Profil utworzony. Przejdź do zakładki Logowanie.")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# Load specific user profile
user_data = supabase.table('konta').select('*').eq('email', st.session_state.auth_user).execute().data[0]

# ==========================================
# 6. INSTRUCTOR WORKFLOW (SPLIT VIEW)
# ==========================================
if user_data['rola'] == "Instruktor":
    st.markdown("<p class='mono-text'>TERMINAL DOWÓDCY OPERACYJNEGO</p>", unsafe_allow_html=True)
    
    col_nav, col_main = st.columns([1, 3])
    
    with col_nav:
        st.markdown(f"<div class='bento-card'><p class='mono-text'>AKTYWNY PERSONEL</p>", unsafe_allow_html=True)
        cadets = supabase.table('konta').select('*').eq('rola', 'Kursant').execute().data
        if not cadets: st.warning("Baza danych pusta."); st.stop()
        selected_email = st.radio("Wybierz Cel:", [k['email'] for k in cadets], label_visibility="collapsed")
        target_data = next(k for k in cadets if k['email'] == selected_email)
        
        # SYSTEM ZARZĄDZANIA TOKENAMI DLA INSTRUKTORA
        st.markdown(f"<br><p class='mono-text'>ZASOBY KADETA: {target_data.get('tokeny', 0)} TOKENÓW</p>", unsafe_allow_html=True)
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            dodaj_tok = st.number_input("Ilość", min_value=1, max_value=100, value=5, label_visibility="collapsed")
        with col_t2:
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("DODAJ"):
                nowy_stan = target_data.get('tokeny', 0) + dodaj_tok
                supabase.table('konta').update({"tokeny": nowy_stan}).eq('email', selected_email).execute()
                st.toast(f"Dodano {dodaj_tok} tokenów.", icon="💳")
                time.sleep(1)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><p class='mono-text'>KONFIGURACJA MISJI</p>", unsafe_allow_html=True)
        inst_env = st.selectbox("Środowisko", ["Lot Rzeczywisty", "Symulator"])
        inst_ind = "Standard"
        if inst_env == "Lot Rzeczywisty":
            inst_ind = st.selectbox("Skupienie taktyczne", ["Militarny/Rozpoznanie", "Pro-Racing", "Freestyle"])
        inst_skill = st.selectbox("Poziom Umiejętności Celu", ["Kadet", "Pilot", "Elita"])
        
        st.session_state.theme_color = '#00ff66' if 'Militarny' in inst_ind else '#ff4400' if 'Racing' in inst_ind else '#ededed'
        
        st.markdown("<br><p class='mono-text'>SYSTEM</p>", unsafe_allow_html=True)
        if st.button("Zakończ Sesję"): st.session_state.auth_user = None; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_main:
        st.markdown(f"<h2>AKTA: {target_data['imie'].upper()}</h2>", unsafe_allow_html=True)
        
        # Triage Upload
        c_upl, c_vid = st.columns(2)
        with c_upl: log_file = st.file_uploader("Upuść Telemetrię (BBL/CSV)", type=['bbl', 'csv'], label_visibility="collapsed")
        with c_vid: vid_link = st.text_input("URL Nagrania z Misji", placeholder="https://...")

        df_active = None
        if log_file:
            with st.status("Przetwarzanie Danych Binarnych...", expanded=False) as status:
                if log_file.name.endswith('.csv'): 
                    df_active = pd.read_csv(log_file)
                else:
                    st.write("Ekstrakcja wektorów Blackbox...")
                    dec = get_decoder()
                    with open("/tmp/i.bbl", "wb") as f: f.write(log_file.getbuffer())
                    subprocess.run([dec, "/tmp/i.bbl"], stdout=subprocess.DEVNULL)
                    csvs = sorted(glob.glob("/tmp/i*.csv"))
                    if csvs: df_active = pd.read_csv(csvs[0])
                status.update(label="Dane Rozkodowane", state="complete", expanded=False)

        if df_active is not None:
            stats = render_terminal_hud(df_active, mode="Real" if inst_env=="Lot Rzeczywisty" else "Sim", premium=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("GENERUJ RAPORT TAKTYCZNY AI"):
                if init_ai():
                    prompt = f"""
                    Jesteś elitarnym dowódcą i ekspertem od dronów FPV (First Person View).
                    Analizujesz surowe dane z lotu DRONA FPV (to NIE JEST samochód, ani samolot komercyjny!).
                    
                    DANE OPERACYJNE:
                    - Poziom pilota: {inst_skill}. (Kadet: chwal i ucz podstaw; Elita: punktuj bezlitośnie każdy najmniejszy błąd).
                    - Typ Misji: {inst_ind}. (Jeśli Militarny: najważniejsza jest stabilność obrazu i brak wibracji. Jeśli Racing: kluczowa jest agresja, szybkie wchodzenie w zakręty. Jeśli Freestyle: liczy się kontrola przepustnicy i płynność (flow)).
                    - Szarpnięcia drążków (Jerk): {stats['jr']:.2f}.
                    - Kondycja elektroniki (Health): {stats['health']}%.
                    
                    Zwróć TYLKO czysty obiekt JSON bez znaczników markdown. Struktura musi wyglądać tak:
                    {{"ocena": 1-10, "diagnoza": "Krótka, inżynieryjna ocena lotu FPV", "zadanie": "Konkretne zadanie treningowe dla drona FPV na kolejny lot"}}
                    """
                    raw = generate_intel(prompt)
                    try:
                        js = json.loads(raw.replace("```json","").replace("```","").strip())
                        st.session_state.instructor_draft = f"### ODPRAWA: {inst_ind}\n**OCENA:** {js['ocena']}/10\n\n**DIAGNOZA:**\n{js['diagnoza']}\n\n**ROZKAZ TRENINGOWY:**\n{js['zadanie']}"
                        st.session_state.temp_metrics = stats
                    except: st.error("Błąd parsowania AI. Proszę spróbować ponownie.")
            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.instructor_draft:
            st.markdown("<p class='mono-text'>RĘCZNA KOREKTA (NADOBOWIĄZKOWA)</p>", unsafe_allow_html=True)
            final_rep = st.text_area("Edytuj wygenerowany raport AI:", value=st.session_state.instructor_draft, height=250, label_visibility="collapsed")
            
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("ZATWIERDŹ I WYŚLIJ DO KADETA"):
                match = re.search(r"OCENA:\s*(\d+)/10", final_rep)
                score = int(match.group(1)) if match else 5
                
                new_record = {
                    "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "ocena": score, "raport": final_rep, "wideo": vid_link, 
                    "type": inst_ind, "premium": True
                }
                history = target_data.get('zadania', [])
                history.append(new_record)
                supabase.table('konta').update({"zadania": history}).eq('email', selected_email).execute()
                
                st.session_state.instructor_draft = None
                st.toast("Pomyślnie wysłano do Kadeta.", icon="✅")
                time.sleep(1)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
            
        # Legacy History View
        st.markdown("<br><p class='mono-text'>ARCHIWUM OPERACJI</p>", unsafe_allow_html=True)
        for z in reversed(target_data.get('zadania', [])):
            if isinstance(z, dict):
                with st.expander(f"OP: {z.get('data')} | OCENA: {z.get('ocena')}/10"):
                    st.markdown(z.get('raport'))
            else:
                with st.expander("STARE ZAPISY"): st.markdown(str(z))

# ==========================================
# 7. CADET WORKFLOW (BENTO LAUNCHPAD)
# ==========================================
else:
    # Sidebar Minimalist
    with st.sidebar:
        st.markdown(f"<p class='mono-text'>ID: {user_data['imie']}</p>", unsafe_allow_html=True)
        st.metric("DOSTĘPNE TOKENY", user_data.get('tokeny', 0))
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("Wyloguj Się"): st.session_state.auth_user = None; st.rerun()

    # --- PHASE 2: BENTO BOX LAUNCHPAD ---
    if st.session_state.flow_state == 'launchpad':
        st.markdown("<h1>WYBIERZ OPERACJĘ</h1>", unsafe_allow_html=True)
        
        # STEP 1: Environment
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div class='bento-card'><h3>🚁 LOT RZECZYWISTY</h3><p class='mono-text'>Telemetria Sprzętowa Drona</p></div>", unsafe_allow_html=True)
            if st.button("Wybierz Lot Rzeczywisty", key="btn_real"): 
                st.session_state.env_select = "Real"
                st.rerun()
        with c2:
            st.markdown("<div class='bento-card'><h3>🎮 SYMULATOR</h3><p class='mono-text'>Trening Wirtualny</p></div>", unsafe_allow_html=True)
            if st.button("Wybierz Symulator", key="btn_sim"): 
                st.session_state.env_select = "Sim"
                st.session_state.industry_select = "Trening Sim"
                st.session_state.theme_color = "#b026ff"
                st.rerun()

        # STEP 2: Industry (Cascade)
        if st.session_state.env_select == "Real":
            st.markdown("<br><h2>WYBIERZ SPECJALIZACJĘ</h2>", unsafe_allow_html=True)
            i1, i2, i3 = st.columns(3)
            with i1:
                st.markdown("<div class='bento-card' style='border-color:#00ff6633;'><h4 style='color:#00ff66!important;'>MILITARNY/ROZPOZNANIE</h4><p class='mono-text'>Skrytość & Stabilność</p></div>", unsafe_allow_html=True)
                if st.button("Wybierz Militarny", key="ind_mil"): st.session_state.industry_select = "Militarny/Rozpoznanie"; st.session_state.theme_color = "#00ff66"; st.rerun()
            with i2:
                st.markdown("<div class='bento-card' style='border-color:#ff440033;'><h4 style='color:#ff4400!important;'>PRO-RACING</h4><p class='mono-text'>Zwinność & Prędkość</p></div>", unsafe_allow_html=True)
                if st.button("Wybierz Racing", key="ind_rac"): st.session_state.industry_select = "Pro-Racing"; st.session_state.theme_color = "#ff4400"; st.rerun()
            with i3:
                st.markdown("<div class='bento-card' style='border-color:#00ccff33;'><h4 style='color:#00ccff!important;'>FREESTYLE</h4><p class='mono-text'>Flow & Kontrola</p></div>", unsafe_allow_html=True)
                if st.button("Wybierz Freestyle", key="ind_fre"): st.session_state.industry_select = "Freestyle"; st.session_state.theme_color = "#00ccff"; st.rerun()

        # STEP 3: Skill Level (Cascade)
        if st.session_state.industry_select:
            st.markdown("<br><h2>KLASYFIKACJA OPERATORA</h2>", unsafe_allow_html=True)
            skill = st.select_slider("Wybierz swój aktualny poziom", options=["Kadet", "Pilot", "Elita"], value=st.session_state.skill_select, label_visibility="collapsed")
            st.session_state.skill_select = skill
            
            st.markdown("<br><div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("ZAINICJUJ TRANSFER DANYCH"):
                st.session_state.flow_state = 'upload'
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # --- PHASE 3/4: UPLOAD & DASHBOARD ---
    elif st.session_state.flow_state == 'upload':
        st.markdown(f"<h2>TERMINAL DANYCH: {st.session_state.industry_select.upper()}</h2>", unsafe_allow_html=True)
        if st.button("← Przerwij i Wróć"): 
            st.session_state.flow_state = 'launchpad'
            st.session_state.env_select = None
            st.session_state.industry_select = None
            st.rerun()

        c_tier, c_drop = st.columns([1, 2])
        with c_tier:
            st.markdown("<div class='bento-card'>", unsafe_allow_html=True)
            st.markdown("<p class='mono-text'>POZIOM ANALIZY</p>", unsafe_allow_html=True)
            tier = st.radio("Wybierz Pakiet:", ["Podstawowy (1 Token)", "Premium (2 Tokeny)"], label_visibility="collapsed")
            cost = 1 if "Podstawowy" in tier else 2
            st.markdown("</div>", unsafe_allow_html=True)

        with c_drop:
            u_log = st.file_uploader("Upuść Plik Telemetrii (.bbl lub .csv)", type=['bbl', 'csv'], label_visibility="collapsed")
            
            if u_log:
                st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
                if st.button(f"WYKONAJ PROTOKÓŁ (-{cost} TOKENÓW)"):
                    if user_data.get('tokeny', 0) >= cost:
                        with st.status("Analizowanie...", expanded=True) as status:
                            st.write("Ekstrakcja wektorów binarnych...")
                            dec = get_decoder()
                            with open("/tmp/u.bbl", "wb") as f: f.write(u_log.getbuffer())
                            subprocess.run([dec, "/tmp/u.bbl"], stdout=subprocess.DEVNULL)
                            csvs = sorted(glob.glob("/tmp/u*.csv"))
                            
                            if csvs:
                                st.write("Przetwarzanie telemetrii...")
                                df = pd.read_csv(csvs[0])
                                
                                st.write("Łączenie z modułem AI...")
                                stats = render_terminal_hud(df, mode=st.session_state.env_select, premium=(cost==2))
                                
                                if init_ai():
                                    prompt = f"""
                                    Jesteś zaawansowanym asystentem AI szkolącym pilotów DRONÓW FPV (First Person View).
                                    To NIE JEST symulacja jazdy samochodem, ani lotu Boeingiem.
                                    
                                    DANE DO ANALIZY:
                                    - Poziom ucznia: {st.session_state.skill_select}.
                                    - Typ lotu drona FPV: {st.session_state.industry_select}.
                                    - Wskaźnik szarpnięć (Jerk): {stats['jr']:.2f}.
                                    
                                    Wymagania: Zwróć uwagę na specyfikę lotu dronem wyścigowym/freestyle.
                                    Zwróć TYLKO czysty obiekt JSON bez znaczników markdown: {{"ocena": 1-10, "diagnoza": "Inżynieryjny i techniczny tekst oceniający drążki", "zadanie": "Ćwiczenie FPV"}}
                                    """
                                    raw_ai = generate_intel(prompt)
                                    try:
                                        js = json.loads(raw_ai.replace("```json","").replace("```","").strip())
                                        tag = "PREMIUM" if cost == 2 else "PODSTAWOWY"
                                        txt = f"### ODPRAWA {tag}\n**OCENA:** {js['ocena']}/10\n\n**DIAGNOZA:**\n{js['diagnoza']}\n\n**ZADANIE NA NASTĘPNY LOT:**\n{js['zadanie']}"
                                        
                                        history = user_data.get('zadania', [])
                                        history.append({
                                            "data": datetime.now().strftime("%Y-%m-%d"), 
                                            "ocena": js['ocena'], 
                                            "raport": txt, 
                                            "type": st.session_state.industry_select, 
                                            "premium": (cost==2)
                                        })
                                        
                                        supabase.table('konta').update({
                                            "zadania": history, 
                                            "tokeny": user_data['tokeny'] - cost
                                        }).eq('email', user_data['email']).execute()
                                        
                                        status.update(label="Analiza Zakończona", state="complete", expanded=False)
                                        time.sleep(1)
                                        st.rerun()
                                    except: st.error("Uszkodzenie pakietu danych AI. Spróbuj ponownie.")
                    else: st.error("BRAK WYSTARCZAJĄCYCH ŚRODKÓW NA KONCIE (TOKENÓW).")
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><p class='mono-text'>ARCHIWUM MISJI</p>", unsafe_allow_html=True)
        for z in reversed(user_data.get('zadania', [])):
            if isinstance(z, dict):
                icon = "💎" if z.get('premium') else "📄"
                with st.expander(f"{icon} {z.get('data')} | {z.get('type','Op')} | OCENA: {z.get('ocena')}/10"):
                    st.markdown(z.get('raport'))
            else:
                with st.expander("STARE ZAPISY"): st.markdown(str(z))
