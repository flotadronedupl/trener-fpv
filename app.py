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

st.set_page_config(page_title="Trener FPV Pro", page_icon="🚁", layout="wide")

# ==========================================
# KONFIGURACJA API I INTELIGENTNE AI (AUTO-DISCOVERY)
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def get_ai_analysis(prompt):
    """
    Automatycznie wykrywa dostępne modele i wybiera najlepszy.
    Eliminuje błąd 404 (NotFound).
    """
    try:
        # Pobieramy listę wszystkich modeli dostępnych dla Twojego klucza
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Szukamy najlepszego kandydata (Flash 1.5 -> Pro -> cokolwiek)
        best_model = None
        for m in available_models:
            if '1.5-flash' in m:
                best_model = m
                break
        if not best_model:
            for m in available_models:
                if 'pro' in m:
                    best_model = m
                    break
        if not best_model and available_models:
            best_model = available_models[0]
            
        if best_model:
            model = genai.GenerativeModel(best_model)
            response = model.generate_content(prompt)
            return response.text
    except Exception as e:
        return f'{{"ocena": 0, "diagnoza": "Błąd API: {str(e)}", "zadanie": "Sprawdź połączenie"}}'
    
    return '{"ocena": 0, "diagnoza": "Nie znaleziono modeli AI", "zadanie": "Sprawdź klucz API"}'

if 'raport_draft' not in st.session_state:
    st.session_state.raport_draft = None
if 'raport_meta' not in st.session_state:
    st.session_state.raport_meta = {}

# ==========================================
# DEKODER BBL -> CSV
# ==========================================
@st.cache_resource
def get_decoder_path():
    extract_dir = "/tmp/bbt_source"
    executable = f"{extract_dir}/blackbox-tools-master/obj/blackbox_decode"
    if not os.path.exists(executable):
        os.makedirs(extract_dir, exist_ok=True)
        url = "https://github.com/betaflight/blackbox-tools/archive/refs/heads/master.zip"
        zip_path = "/tmp/bbt_src.zip"
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        subprocess.run(["make", "obj/blackbox_decode"], cwd=f"{extract_dir}/blackbox-tools-master", check=True)
    os.chmod(executable, 0o755)
    return executable

supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# ==========================================
# SILNIK ANALITYCZNY (DASHBOARD)
# ==========================================
def render_pro_dashboard(df, show_charts=True):
    # Dynamiczna detekcja kolumn (odporna na wersje Betaflight)
    thr = [c for c in df.columns if 'rcCommand[3]' in c or ('rcCommand' in c and '3' in c)][0]
    roll = [c for c in df.columns if 'rcCommand[0]' in c or ('rcCommand' in c and '0' in c)][0]
    pitch = [c for c in df.columns if 'rcCommand[1]' in c or ('rcCommand' in c and '1' in c)][0]
    
    j_r = df[roll].diff().abs().mean()
    j_p = df[pitch].diff().abs().mean()
    avg_t = df[thr].mean()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Średni Gaz", f"{avg_t:.0f}")
    m2.metric("Płynność Roll", f"{j_r:.2f}")
    m3.metric("Płynność Pitch", f"{j_p:.2f}")
    
    if show_charts:
        krok = max(1, len(df)//5000)
        pdf = df.iloc[::krok]
        tab1, tab2, tab3 = st.tabs(["📈 Wykres 2D", "🪐 Tunel 3D", "🔋 Battery Sag"])
        
        with tab1:
            f2d = go.Figure()
            f2d.add_trace(go.Scatter(y=pdf[thr], name="Throttle", line=dict(color='orange', width=2)))
            f2d.add_trace(go.Scatter(y=pdf[roll], name="Roll", line=dict(color='cyan', width=1), opacity=0.6))
            f2d.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=20,b=0))
            st.plotly_chart(f2d, use_container_width=True)
            
        with tab2:
            x, y, z = pdf[roll].cumsum()/500, pdf[pitch].cumsum()/500, np.arange(len(pdf))
            f3d = go.Figure(data=[go.Scatter3d(x=x, y=y, z=z, mode='lines', line=dict(color=pdf[thr], colorscale='Jet', width=5))])
            f3d.update_layout(template="plotly_dark", height=500, margin=dict(l=0,r=0,t=0,b=0))
            st.plotly_chart(f3d, use_container_width=True)
            
        with tab3:
            v_col = [c for c in df.columns if 'vbat' in c.lower()]
            if v_col:
                f_bat = make_subplots(specs=[[{"secondary_y": True}]])
                f_bat.add_trace(go.Scatter(y=pdf[v_col[0]]/100, name="Napięcie (V)", line=dict(color='cyan')), secondary_y=False)
                f_bat.add_trace(go.Scatter(y=pdf[thr], name="Gaz", fill='tozeroy', opacity=0.2, line=dict(color='orange')), secondary_y=True)
                f_bat.update_layout(template="plotly_dark", height=350)
                st.plotly_chart(f_bat, use_container_width=True)
    
    return {"j_r": float(j_r), "j_p": float(j_p), "avg_t": float(avg_t)}

# ==========================================
# GŁÓWNA APLIKACJA
# ==========================================
if st.session_state.get('zalogowany_uzytkownik') is None:
    st.title("🚁 Akademia FPV Pro")
    t1, t2 = st.tabs(["🔐 Logowanie", "📝 Rejestracja"])
    with t1:
        em = st.text_input("Email")
        pw = st.text_input("Hasło", type="password")
        if st.button("🔓 Wejdź"):
            res = supabase.table('konta').select('*').eq('email', em).execute()
            if res.data and res.data[0]['haslo'] == pw:
                st.session_state.zalogowany_uzytkownik = em
                st.rerun()
    with t2:
        rem, rpw, rnm = st.text_input("Nowy Email"), st.text_input("Nowe Hasło", type="password"), st.text_input("Imię")
        if st.button("📝 Załóż konto"):
            supabase.table('konta').insert({'email': rem, 'haslo': rpw, 'imie': rnm, 'rola': 'Kursant', 'tokeny': 5, 'zadania': []}).execute()
            st.success("Konto gotowe!")
    st.stop()

user_data = supabase.table('konta').select('*').eq('email', st.session_state.zalogowany_uzytkownik).execute().data[0]

with st.sidebar:
    st.title(f"Witaj {user_data['imie']}")
    if st.button("🚪 Wyloguj"):
        st.session_state.zalogowany_uzytkownik = None
        st.rerun()

# --- WIDOK INSTRUKTORA ---
if user_data['rola'] == "Instruktor":
    st.header("👨‍🏫 Panel Instruktorski Master")
    kursanci = supabase.table('konta').select('*').eq('rola', 'Kursant').execute().data
    wybrany_em = st.selectbox("Kursant:", [k['email'] for k in kursanci])
    k_data = next(k for k in kursanci if k['email'] == wybrany_em)

    col_l, col_v = st.columns(2)
    with col_l: log = st.file_uploader("Wgraj log (.bbl/.csv)", type=['bbl', 'csv'])
    with col_v: v_url = st.text_input("Link do wideo:")
    
    df = None
    if log:
        if log.name.endswith('.csv'): df = pd.read_csv(log)
        else:
            dec = get_decoder_path()
            with open("/tmp/i.bbl", "wb") as f: f.write(log.getbuffer())
            subprocess.run([dec, "/tmp/i.bbl"])
            csvs = sorted(glob.glob("/tmp/i*.csv"))
            if csvs: df = pd.read_csv(csvs[0])

    if df is not None:
        stats = render_pro_dashboard(df, show_charts=True)
        if st.button("🤖 Generuj Draft Raportu"):
            prompt = f"Analiza drona FPV. Roll Jerk: {stats['j_r']:.2f}. Zwróć JSON: {{'ocena': 1-10, 'diagnoza': '...', 'zadanie': '...'}}"
            ai_text = get_ai_analysis(prompt)
            try:
                js = json.loads(ai_text.replace("```json","").replace("```","").strip())
                st.session_state.raport_draft = f"### Ocena Systemu: {js['ocena']}/10\n\n**🩺 Diagnoza:**\n{js['diagnoza']}\n\n**🏁 Zadanie:**\n{js['zadanie']}"
                st.session_state.raport_meta = {"ocena": js['ocena'], "j_r": stats['j_r']}
            except: st.error(f"AI zwróciło nieoczekiwany format: {ai_text[:100]}")

    if st.session_state.raport_draft:
        final = st.text_area("Edytuj raport:", value=st.session_state.raport_draft, height=200)
        if st.button("🚀 WYŚLIJ JAKO PREMIUM"):
            match = re.search(r"Ocena Systemu: (\d+)/10", final)
            ocena = int(match.group(1)) if match else 0
            wpis = {"data": datetime.now().strftime("%Y-%m-%d %H:%M"), "ocena": ocena, "raport": final, "wideo": v_url, "premium": True}
            aktualne = k_data['zadania']
            aktualne.append(wpis)
            supabase.table('konta').update({"zadania": aktualne}).eq('email', wybrany_em).execute()
            st.session_state.raport_draft = None
            st.success("Wysłano raport!")
            time.sleep(1)
            st.rerun()

# --- WIDOK KURSANTA ---
else:
    st.header(f"🎓 Twój Panel: {user_data['imie']}")
    zads = user_data.get('zadania', [])
    if len(zads) > 1:
        oceny = [z['ocena'] for z in zads if isinstance(z, dict) and 'ocena' in z]
        st.plotly_chart(go.Figure(go.Scatter(y=oceny, mode='lines+markers', name="Ocena", line=dict(color='gold', width=3))).update_layout(template="plotly_dark", height=200, margin=dict(l=0,r=0,t=0,b=0)), use_container_width=True)

    st.divider()
    col_t1, col_t2 = st.columns([1, 2])
    with col_t1:
        st.metric("Twoje Tokeny 🎟️", user_data['tokeny'])
        pakiet = st.radio("Usługa:", ["📄 Analiza Basic (1 Token)", "💎 Analiza Premium (2 Tokeny)"])
    
    with col_t2:
        u_log = st.file_uploader("Wgraj log .bbl", type=['bbl'])
        koszt = 1 if "Basic" in pakiet else 2
        if u_log and st.button(f"🚀 Uruchom {pakiet}"):
            if user_data['tokeny'] >= koszt:
                with st.spinner("Analiza w toku..."):
                    dec = get_decoder_path()
                    with open("/tmp/u.bbl", "wb") as f: f.write(u_log.getbuffer())
                    subprocess.run([dec, "/tmp/u.bbl"])
                    csvs = sorted(glob.glob("/tmp/u*.csv"))
                    if csvs:
                        df = pd.read_csv(csvs[0])
                        stats = render_pro_dashboard(df, show_charts=(koszt == 2))
                        ai_text = get_ai_analysis(f"Analiza FPV. Jerk: {stats['j_r']:.2f}. Podaj JSON z oceną i diagnozą.")
                        try:
                            js = json.loads(ai_text.replace("```json","").replace("```","").strip())
                            tag = "💎 PREMIUM" if koszt == 2 else "📄 BASIC"
                            txt = f"### {tag} RAPORT AI\n\n**Ocena:** {js['ocena']}/10\n\n**Analiza:** {js['diagnoza']}\n\n**Zadanie:** {js['zadanie']}"
                            zads.append({"data": datetime.now().strftime("%Y-%m-%d"), "ocena": js['ocena'], "raport": txt, "premium": (koszt==2)})
                            supabase.table('konta').update({"zadania": zads, "tokeny": user_data['tokeny'] - koszt}).eq('email', st.session_state.zalogowany_uzytkownik).execute()
                            st.rerun()
                        except: st.error("Błąd AI")
            else: st.error("Brak tokenów!")

    st.subheader("📋 Historia Twoich Analiz")
    for z in reversed(zads):
        if isinstance(z, dict):
            ico = "💎" if z.get('premium') else "📄"
            with st.expander(f"{ico} {z.get('data')} | Ocena: {z.get('ocena')}/10"):
                st.markdown(z.get('raport'))
                if z.get('wideo'): st.video(z.get('wideo'))
