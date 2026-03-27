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
    </style>
    """, unsafe_allow_html=True)

def render_logo():
    logo_html = f"""<div style='text-align:center; padding-bottom:3rem; display:flex; flex-direction:column; align-items:center;'><svg width='80' height='80' viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'><path d='M5.5 5.5h.01M18.5 5.5h.01M5.5 18.5h.01M18.5 18.5h.01' stroke='{ACCENT_LIGHT}' stroke-width='3' stroke-linecap='round'/><path d='M12 12L5.5 5.5M12 12l6.5-6.5M12 12l-6.5 6.5M12 12l6.5 6.5' stroke='#4d9900' stroke-width='1.5' stroke-linecap='round'/><circle cx='12' cy='12' r='3' fill='#050a0a' stroke='{ACCENT_LIGHT}' stroke-width='2'/></svg><h1 style='font-size:3rem; margin:10px 0 0 0; background:linear-gradient(90deg, #FFFFFF, #8cbf8c); -webkit-background-clip:text; -webkit-text-fill-color:transparent;'>FPV AI Academy</h1><p style='color:#64748B; font-size:1.1rem; margin-top:0.5rem; font-weight:600; letter-spacing:2px;'>NEXT-GEN FLIGHT ANALYTICS</p></div>"""
    st.markdown(logo_html, unsafe_allow_html=True)

def generate_html_report(date, score, report_text, stats_dict, pilot_name):
    import markdown
    md_text = markdown.markdown(report_text)
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #111; background: #fff; padding: 40px; line-height: 1.6; }}
            h1 {{ color: {PRIMARY_COLOR}; border-bottom: 2px solid {PRIMARY_COLOR}; padding-bottom: 10px; }}
            .header {{ text-align: center; margin-bottom: 40px; }}
            .stats-box {{ background: #f4fdf4; border: 1px solid {ACCENT_LIGHT}; padding: 20px; border-radius: 10px; margin: 20px 0; display: flex; justify-content: space-around; }}
            .stat {{ text-align: center; font-weight: bold; font-size: 1.2em; }}
            .stat span {{ display: block; font-size: 0.8em; color: #666; font-weight: normal; text-transform: uppercase; }}
            .score {{ font-size: 2em; color: {PRIMARY_COLOR}; font-weight: bold; text-align: center; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Certyfikowany Raport Lotu FPV</h1>
            <p>Data operacji: <b>{date}</b> | Pilot: <b>{pilot_name}</b></p>
        </div>
        <div class="score">Skuteczność: {score}/10</div>
        <div class="stats-box">
            <div class="stat"><span>Kondycja</span>{stats_dict.get('health', 0):.0f}%</div>
            <div class="stat"><span>Roll Jerk</span>{stats_dict.get('jr', 0):.2f}</div>
            <div class="stat"><span>Pitch Jerk</span>{stats_dict.get('jp', 0):.2f}</div>
            <div class="stat"><span>Max G-Force</span>{stats_dict.get('max_g', 0):.1f} G</div>
        </div>
        <div>{md_text}</div>
        <p style="margin-top: 50px; text-align: center; color: #999; font-size: 0.8em;">Wygenerowano automatycznie przez FPV AI Academy</p>
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

    st.markdown("<p class='mono-text'>DASHBOARD TELEMETRYCZNY</p>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Płynność lotu", f"{smoothness:.1f} / 10")
    m2.metric("Średni gaz", f"{avg_t:.0f}")
    m3.metric("Max przeciążenie", f"{max_g:.1f} G" if has_acc else "Brak danych")
    
    health = max(0, min(100, 100 - ((jr + jp) * 12)))
    m4.metric("Kondycja drona", f"{health:.0f}%")

    if premium:
        st.markdown("<br><p class='mono-text'>ANALIZA ZAAWANSOWANA (PREMIUM)</p>", unsafe_allow_html=True)
        t1, t2, t3, t4 = st.tabs(["Telemetria drążków", "Analiza przeciążeń (G-Force)", "Przestrzenna trajektoria 3D", "Silniki i zasilanie"])
        
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
                fig_mot.update_layout(title="Średnie obciążenie", template="plotly_dark", height=250, margin=dict(l=0,r=0,t=40,b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_mot, use_container_width=True)
            
            if v_col and mode == "Real":
                has_data = True
                f_bat = make_subplots(specs=[[{"secondary_y": True}]])
                f_bat.add_trace(go.Scatter(y=pdf[v_col[0]]/100, name="Napięcie (V)", line=dict(color='#F8FAFC', width=2)), secondary_y=False)
                f_bat.add_trace(go.Scatter(y=pdf[thr], name="Gaz", line=dict(color=ACCENT_LIGHT, width=1), fill='tozeroy', opacity=0.3), secondary_y=True)
                f_bat.update_layout(title="Spadek napięcia a gaz", template="plotly_dark", height=300, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=0,r=0,t=40,b=0))
                st.plotly_chart(f_bat, use_container_width=True)
                
            if not has_data: st.info("Brak danych o zasilaniu w logu symulatora.")
            
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
            em = st.text_input("Adres e-mail")
            pw = st.text_input("Hasło", type="password")
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("Wejdź do centrum dowodzenia"):
                res = supabase.table('konta').select('*').eq('email', em).execute()
                if res.data and res.data[0]['haslo'] == pw:
                    st.session_state.auth_user = em
                    st.session_state.role = res.data[0]['rola']
                    st.rerun()
                else: st.error("Nieprawidłowy e-mail lub hasło.")
            st.markdown("</div>", unsafe_allow_html=True)
        with t2:
            rem = st.text_input("Nowy adres e-mail")
            rpw = st.text_input("Nowe hasło", type="password", key="reg_pass")
            rnm = st.text_input("Imię lub pseudonim pilota")
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
        if not cadets: st.warning("Brak kursantów w bazie danych."); st.stop()
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
        inst_env = st.selectbox("Środowisko", ["Lot rzeczywisty", "Symulator"])
        inst_ind = st.selectbox("Styl lotu", ["Cinematic / Płynny", "Racing (Wyścigi)", "Freestyle"]) if inst_env == "Lot rzeczywisty" else "Standard"
        inst_skill = st.selectbox("Poziom zaawansowania", ["Początkujący", "Średniozaawansowany", "Ekspert"])
        
        st.markdown("<br><p class='mono-text'>OPCJE</p>", unsafe_allow_html=True)
        if st.button("Wyloguj się"): st.session_state.auth_user = None; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_main:
        st.markdown(f"<h2>Akta pilota: <span style='color:{ACCENT_LIGHT}'>{target_data['imie']}</span></h2>", unsafe_allow_html=True)
        
        c_upl, c_vid = st.columns(2)
        with c_upl: log_file = st.file_uploader("Wgraj plik (BBL/CSV)", type=['bbl', 'csv'], label_visibility="collapsed")
        with c_vid: vid_link = st.text_input("Opcjonalny link do nagrania (YouTube)", placeholder="https://...")

        df_active = None
        if log_file:
            with st.status("Ekstrakcja danych...", expanded=False) as status:
                if log_file.name.endswith('.csv'): df_active = pd.read_csv(log_file)
                else:
                    dec = get_decoder()
                    with open("/tmp/i.bbl", "wb") as f: f.write(log_file.getbuffer())
                    subprocess.run([dec, "/tmp/i.bbl"], stdout=subprocess.DEVNULL)
                    csvs = sorted(glob.glob("/tmp/i*.csv"))
                    if csvs: df_active = pd.read_csv(csvs[0])
                status.update(label="Dane zdekodowane.", state="complete", expanded=False)

        if df_active is not None:
            stats = render_terminal_hud(df_active, mode="Real" if inst_env=="Lot rzeczywisty" else "Sim", premium=True)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
            if st.button("GENERUJ RAPORT AI"):
                if init_ai():
                    prompt = f"Instruktor FPV. Kursant: {inst_skill}, Styl: {inst_ind}. Płynność Roll: {stats['jr']:.2f}, G-Force: {stats['max_g']:.1f}G. Wygeneruj JSON: {{\"ocena\": 8, \"diagnoza\": \"...\", \"zadanie\": \"...\"}}"
                    raw = generate_intel(prompt)
                    try:
                        js = json.loads(raw.replace("```json","").replace("```","").strip())
                        st.session_state.instructor_draft = f"### Analiza lotu: {inst_ind}\n**OCENA WYDAJNOŚCI:** {js['ocena']}/10\n\n**KOMENTARZ TRENERA:**\n{js['diagnoza']}\n\n**CEL TRENINGOWY:**\n{js['zadanie']}"
                        st.session_state.temp_metrics = stats
                    except: st.error("Błąd AI.")
            st.markdown("</div>", unsafe_allow_html=True)

        if st.session_state.instructor_draft:
            final_rep = st.text_area("Edytor", value=st.session_state.instructor_draft, height=250)
            if st.button("ZATWIERDŹ I WYŚLIJ"):
                match = re.search(r"OCENA WYDAJNOŚCI:\s*(\d+)/10", final_rep)
                score = int(match.group(1)) if match else 5
                new_record = {"data": datetime.now().strftime("%Y-%m-%d %H:%M"), "ocena": score, "raport": final_rep, "wideo": vid_link, "type": inst_ind, "premium": True, "stats": st.session_state.temp_metrics}
                history = target_data.get('zadania', [])
                history.append(new_record)
                supabase.table('konta').update({"zadania": history}).eq('email', selected_email).execute()
                st.session_state.instructor_draft = None
                st.rerun()
            
        st.markdown("<br><p class='mono-text'>ARCHIWUM RAPORTÓW</p>", unsafe_allow_html=True)
        for z in reversed(target_data.get('zadania', [])):
            if isinstance(z, dict):
                with st.expander(f"Data: {z.get('data')} | Ocena: {z.get('ocena')}/10"):
                    st.markdown(z.get('raport'))
                    if 'stats' in z: 
                        render_history_stats(z['stats'])
                        html_report = generate_html_report(z.get('data'), z.get('ocena'), z.get('raport'), z['stats'], target_data['imie'])
                        st.download_button(label="📥 Pobierz jako Dokument (HTML do PDF)", data=html_report, file_name=f"Raport_{z.get('data').split(' ')[0]}.html", mime="text/html")

# ==========================================
# 7. PANEL KURSANTA (NOWE ZAKŁADKI)
# ==========================================
else:
    with st.sidebar:
        st.markdown(f"<p class='mono-text'>ZALOGOWANY PILOT: <br><span style='color: {ACCENT_LIGHT}; font-size: 1.2em;'>{user_data['imie']}</span></p>", unsafe_allow_html=True)
        st.metric("DOSTĘPNE TOKENY", user_data.get('tokeny', 0))
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("Wyloguj się"): st.session_state.auth_user = None; st.rerun()

    if st.session_state.flow_state == 'launchpad':
        render_logo()
        
        # 4 GŁÓWNE ZAKŁADKI DLA KURSANTA (W TYM NOWY WARSZTAT FPV)
        tab_main, tab_prog, tab_rank, tab_workshop = st.tabs(["🚀 Centrum Dowodzenia", "📈 Analiza Postępów", "🏆 Globalny Ranking", "🛠️ Warsztat FPV"])
        
        with tab_main:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("<div class='bento-card'><h3>🚁 LOT RZECZYWISTY</h3><p class='mono-text'>Analiza logów (.BBL)</p></div>", unsafe_allow_html=True)
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
                skill = st.select_slider("Poziom do oceny AI:", options=["Początkujący", "Średniozaawansowany", "Ekspert"], value=st.session_state.skill_select, label_visibility="collapsed")
                st.session_state.skill_select = skill
                
                st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
                if st.button("PRZEJDŹ DO WGRYWANIA PLIKU"): st.session_state.flow_state = 'upload'; st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # HISTORIA I EKSPORT NA GŁÓWNYM WIDOKU
            st.markdown("<br><p class='mono-text'>HISTORIA LOTÓW</p>", unsafe_allow_html=True)
            for z in reversed(user_data.get('zadania', [])):
                if isinstance(z, dict):
                    icon = "🟢" if z.get('premium') else "📄"
                    with st.expander(f"{icon} {z.get('data')} | {z.get('type','Lot')} | Ocena: {z.get('ocena')}/10"):
                        st.markdown(z.get('raport'))
                        if 'stats' in z and z.get('premium'): 
                            render_history_stats(z['stats'])
                            html_report = generate_html_report(z.get('data'), z.get('ocena'), z.get('raport'), z['stats'], user_data['imie'])
                            st.download_button(label="📥 Pobierz jako Dokument (HTML do PDF)", data=html_report, file_name=f"FPV_Raport_{z.get('data').split(' ')[0]}.html", mime="text/html", key=f"dl_{z.get('data')}")
                else:
                    with st.expander("Stare zapisy archiwalne"): st.markdown(str(z))

        with tab_prog:
            st.markdown("### Monitorowanie Płynności Lotu")
            st.markdown("<p style='color: #8cbf8c;'>Śledź, jak na przestrzeni czasu zmniejsza się Twój wskaźnik szarpania drążkami (Jerk). Im niżej na wykresie, tym lepszy pilot!</p>", unsafe_allow_html=True)
            history = [z for z in user_data.get('zadania', []) if isinstance(z, dict) and 'stats' in z]
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
                st.info("Zrób co najmniej dwie analizy z telemetrią, aby zobaczyć tutaj swój wykres postępu.")

        with tab_rank:
            st.markdown("### Top Piloci FPV Academy")
            all_cadets = supabase.table('konta').select('imie, zadania').eq('rola', 'Kursant').execute().data
            leaderboard = []
            
            for k in all_cadets:
                zad = k.get('zadania', [])
                valid_zad = [z for z in zad if isinstance(z, dict) and 'ocena' in z]
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

        # ==========================================
        # NOWY MODUŁ: WARSZTAT FPV
        # ==========================================
        with tab_workshop:
            st.markdown("## 🛠️ Warsztat i Wiedza FPV")
            st.markdown("<p style='color: #8cbf8c;'>Twoje centrum diagnozy usterek, konfiguracji sprzętu i poszerzania wiedzy lotniczej.</p>", unsafe_allow_html=True)
            
            w_mech, w_calc, w_vtx, w_dict = st.tabs(["🤖 Wirtualny Mechanik AI", "⚖️ Kalkulator Napędu", "📡 Ściągawka VTX", "📚 Słowniczek Betaflight"])
            
            with w_mech:
                st.markdown("### Sztuczna Inteligencja Serwisowa")
                st.write("Opisz objawy, jakie daje Twój dron (np. wibracje przy opadaniu, gorące silniki), a AI postara się zdiagnozować usterkę.")
                mech_query = st.text_area("Twój problem ze sprzętem:", placeholder="Np. Dron po zrobieniu flipa na chwilę traci moc i dziwnie wyje...")
                st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
                if st.button("ZAPYTAJ MECHANIKA (-0 TOKENÓW)"):
                    if mech_query and init_ai():
                        with st.spinner("Mechanik analizuje objawy..."):
                            prompt = f"Jesteś profesjonalnym serwisantem dronów FPV. Krótko i zwięźle pomóż rozwiązać problem użytkownika w punktach. Problem: {mech_query}"
                            try:
                                mech_resp = genai.GenerativeModel('gemini-1.5-flash').generate_content(prompt).text
                                st.success("Diagnoza zakończona:")
                                st.markdown(mech_resp)
                            except:
                                st.error("Błąd połączenia z modułem serwisowym AI.")
                st.markdown("</div>", unsafe_allow_html=True)

            with w_calc:
                st.markdown("### Kreator Setupu Drona")
                frame_size = st.selectbox("Rozmiar ramy:", ["TinyWhoop (65-75mm)", "3 Cale (Cinewhoop / Micro)", "5 Cali (Freestyle / Race)", "7 Cali (Long Range)"])
                
                # Słownik z rekomendacjami
                specs = {
                    "TinyWhoop (65-75mm)": {"Silniki": "0702 - 0802 (19000KV - 25000KV)", "Bateria": "1S (300mAh - 450mAh) BT2.0", "ESC": "5A - 12A (AIO)", "Śmigła": "31mm - 40mm Bi-blade / Tri-blade"},
                    "3 Cale (Cinewhoop / Micro)": {"Silniki": "1404 - 1504 (3000KV - 4500KV)", "Bateria": "4S (650mAh - 850mAh)", "ESC": "20A - 35A", "Śmigła": "3 cale Tri-blade (z osłonami lub bez)"},
                    "5 Cali (Freestyle / Race)": {"Silniki": "2207 - 2306 (1750KV - 1950KV dla 6S)", "Bateria": "6S (1050mAh - 1300mAh)", "ESC": "45A - 60A", "Śmigła": "5.1 cala Tri-blade (np. 5143, 51466)"},
                    "7 Cali (Long Range)": {"Silniki": "2806.5 - 2809 (1300KV - 1500KV)", "Bateria": "6S Li-Ion (4000mAh) lub LiPo (2000mAh+)", "ESC": "50A - 60A", "Śmigła": "7 cali Bi-blade / Tri-blade (np. 7040)"}
                }
                
                st.markdown(f"#### Zalecany setup dla: {frame_size}")
                c1, c2 = st.columns(2)
                with c1:
                    st.info(f"**⚡ Silniki (Statory & KV):**\n\n{specs[frame_size]['Silniki']}")
                    st.info(f"**🔋 Bateria (Napięcie & Pojemność):**\n\n{specs[frame_size]['Bateria']}")
                with c2:
                    st.info(f"**🔌 ESC (Regulator obrotów):**\n\n{specs[frame_size]['ESC']}")
                    st.info(f"**🚁 Śmigła (Props):**\n\n{specs[frame_size]['Śmigła']}")

            with w_vtx:
                st.markdown("### Częstotliwości VTX (Raceband)")
                st.write("Wybierz liczbę pilotów latających jednocześnie, a system wskaże najbezpieczniejsze kanały do ustawienia na nadajnikach (VTx) i goglach.")
                
                pilots_count = st.slider("Liczba pilotów w grupie:", 1, 8, 3)
                
                # Złota zasada separacji Raceband
                safe_channels = {
                    1: ["R1"],
                    2: ["R1", "R8"],
                    3: ["R1", "R4", "R8"],
                    4: ["R1", "R3", "R6", "R8"],
                    5: ["R1", "R3", "R5", "R7", "R8"], # Zaczyna być ciasno
                    6: ["R1", "R2", "R4", "R6", "R7", "R8"],
                    7: ["R1", "R2", "R3", "R4", "R6", "R7", "R8"],
                    8: ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"] # Max zapchany eter
                }
                
                active_ch = safe_channels[pilots_count]
                
                # Tabela Raceband
                rb_data = {
                    "Kanał": ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"],
                    "Częstotliwość (MHz)": [5658, 5695, 5732, 5769, 5806, 5843, 5880, 5917]
                }
                df_rb = pd.DataFrame(rb_data)
                
                def highlight_active(row):
                    if row['Kanał'] in active_ch: return ['background-color: #336600; color: white; font-weight: bold'] * len(row)
                    return [''] * len(row)
                
                st.dataframe(df_rb.style.apply(highlight_active, axis=1), use_container_width=True)
                st.success(f"Zalecany podział kanałów dla {pilots_count} pilotów: **{', '.join(active_ch)}**")

            with w_dict:
                st.markdown("### Słowniczek Żargonu Betaflight")
                
                with st.expander("P-I-D (Proportional, Integral, Derivative)"):
                    st.write("**P (Proportional)** - Szybkość reakcji drona na drążki i wiatr. Zbyt niskie = dron 'pływa', zbyt wysokie = szybkie wibracje (oscylacje).")
                    st.write("**I (Integral)** - Trzymanie zadanego kąta. Pomaga dronowi nie ulegać wpływom wiatru i środka ciężkości baterii.")
                    st.write("**D (Derivative)** - 'Amortyzator' dla wartości P. Zapobiega przelatywaniu poza cel (overshoot) po ostrym manewrze. Zbyt wysokie D powoduje bardzo mocne grzanie silników.")
                
                with st.expander("Rates (RC Rate, Super Rate/Expo)"):
                    st.write("**RC Rate** - Czułość na samym środku drążka. Im wyższa, tym szybciej dron reaguje na małe ruchy.")
                    st.write("**Super Rate / Expo** - Czułość na samych krawędziach drążka. Pozwala na super szybkie flipy, zachowując przy tym miękki środek do płynnego lotu (Cinematic).")
                
                with st.expander("Propwash (Oscylacje po zejściu)"):
                    st.write("Wibracje drona, które pojawiają się, gdy gwałtownie zawracasz lub opadasz pionowo we własne 'brudne powietrze' wyrzucone wcześniej przez śmigła. Zwalczamy to podnosząc wartość 'D' i optymalizując filtry.")
                
                with st.expander("RPM Filtering (Filtry dwukierunkowe DShot)"):
                    st.write("Bardzo zaawansowana funkcja, gdzie regulator ESC na żywo wysyła do kontrolera lotu informację z jaką prędkością obraca się każdy silnik. Dzięki temu Betaflight filtruje tylko te częstotliwości, które generują hałas z silników, oszczędzając czas procesora.")

    elif st.session_state.flow_state == 'upload':
        st.markdown(f"<h2>SEKWENCJA ANALIZY: <span style='color: {ACCENT_LIGHT};'>{st.session_state.industry_select.upper()}</span></h2>", unsafe_allow_html=True)
        if st.button("← Wróć do menu głównego"): 
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
            u_log = st.file_uploader("Upuść plik telemetrii w tym miejscu (.bbl lub .csv)", type=['bbl', 'csv'], label_visibility="collapsed")
            
            if u_log:
                st.markdown("<div class='cta-btn'>", unsafe_allow_html=True)
                if st.button(f"ROZPOCZNIJ PRZETWARZANIE (-{cost} TOKENÓW)"):
                    if user_data.get('tokeny', 0) >= cost:
                        with st.status("Trwa analizowanie fizyki lotu...", expanded=True) as status:
                            dec = get_decoder()
                            with open("/tmp/u.bbl", "wb") as f: f.write(u_log.getbuffer())
                            subprocess.run([dec, "/tmp/u.bbl"], stdout=subprocess.DEVNULL)
                            csvs = sorted(glob.glob("/tmp/u*.csv"))
                            
                            if csvs:
                                df = pd.read_csv(csvs[0])
                                stats = render_terminal_hud(df, mode=st.session_state.env_select, premium=(cost==2))
                                
                                if init_ai():
                                    prompt = f"Instruktor FPV. Pilot: {user_data['imie']}, Poziom: {st.session_state.skill_select}, Styl: {st.session_state.industry_select}. Płynność Roll: {stats['jr']:.2f}, Max G: {stats['max_g']:.1f}G. Wygeneruj czysty JSON: {{\"ocena\": 8, \"diagnoza\": \"...\", \"zadanie\": \"...\"}}"
                                    raw_ai = generate_intel(prompt)
                                    try:
                                        js = json.loads(raw_ai.replace("```json","").replace("```","").strip())
                                        tag = "ANALIZA PREMIUM" if cost == 2 else "ANALIZA STANDARDOWA"
                                        txt = f"### {tag}\n**SKUTECZNOŚĆ OPERACYJNA:** {js['ocena']}/10\n\n**DIAGNOZA SYSTEMOWA:**\n{js['diagnoza']}\n\n**CEL TRENINGOWY:**\n{js['zadanie']}"
                                        
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
                                        st.session_state.flow_state = 'launchpad' 
                                        st.rerun()
                                    except: st.error("Wystąpił problem z systemem AI.")
                    else: st.error("Niewystarczająca liczba tokenów na koncie.")
                st.markdown("</div>", unsafe_allow_html=True)
