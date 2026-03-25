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

st.set_page_config(page_title="Trener FPV", page_icon="🚁", layout="wide")

# ==========================================
# KONFIGURACJA I NARZĘDZIA
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

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

def render_charts(df):
    """Funkcja rysująca wykresy dla opcji Premium"""
    thr = [c for c in df.columns if 'rcCommand[3]' in c or ('rcCommand' in c and '3' in c)][0]
    roll = [c for c in df.columns if 'rcCommand[0]' in c or ('rcCommand' in c and '0' in c)][0]
    pitch = [c for c in df.columns if 'rcCommand[1]' in c or ('rcCommand' in c and '1' in c)][0]
    krok = max(1, len(df)//5000)
    pdf = df.iloc[::krok]
    
    t1, t2 = st.tabs(["📊 Wykres 2D", "🪐 Tunel 3D"])
    with t1:
        f2d = go.Figure()
        f2d.add_trace(go.Scatter(y=pdf[thr], name="Gaz", line=dict(color='orange')))
        f2d.update_layout(template="plotly_dark", height=300)
        st.plotly_chart(f2d, use_container_width=True)
    with t2:
        f3d = go.Figure(data=[go.Scatter3d(x=pdf[roll].cumsum()/500, y=pdf[pitch].cumsum()/500, z=np.arange(len(pdf)), mode='lines', line=dict(color=pdf[thr], colorscale='Jet', width=4))])
        f3d.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(f3d, use_container_width=True)

# ==========================================
# SYSTEM LOGOWANIA
# ==========================================
if 'zalogowany_uzytkownik' not in st.session_state:
    st.session_state.zalogowany_uzytkownik = None

if st.session_state.zalogowany_uzytkownik is None:
    st.title("🚁 Akademia FPV")
    t1, t2 = st.tabs(["🔐 Zaloguj", "📝 Rejestracja"])
    with t1:
        em = st.text_input("E-mail")
        pw = st.text_input("Hasło", type="password")
        if st.button("🔓 Zaloguj"):
            res = supabase.table('konta').select('*').eq('email', em).execute()
            if res.data and res.data[0]['haslo'] == pw:
                st.session_state.zalogowany_uzytkownik = em
                st.rerun()
    with t2:
        rem = st.text_input("E-mail")
        rpw = st.text_input("Hasło", type="password")
        rnm = st.text_input("Imię")
        if st.button("📝 Zarejestruj"):
            supabase.table('konta').insert({'email': rem, 'haslo': rpw, 'imie': rnm, 'rola': 'Kursant', 'tokeny': 5, 'zadania': []}).execute()
            st.success("Konto utworzone!")
    st.stop()

user_data = supabase.table('konta').select('*').eq('email', st.session_state.zalogowany_uzytkownik).execute().data[0]

with st.sidebar:
    st.title(f"Witaj {user_data['imie']}")
    if st.button("🚪 Wyloguj"):
        st.session_state.zalogowany_uzytkownik = None
        st.rerun()

# ==========================================
# WIDOK INSTRUKTORA
# ==========================================
if user_data['rola'] == "Instruktor":
    st.header("👨‍🏫 Panel Instruktora")
    kursanci = supabase.table('konta').select('*').eq('rola', 'Kursant').execute().data
    wybrany_em = st.selectbox("Wybierz kursanta:", [k['email'] for k in kursanci])
    k_data = next(k for k in kursanci if k['email'] == wybrany_em)

    log = st.file_uploader("Wgraj log lotu", type=['bbl', 'csv'])
    v_url = st.text_input("Link do wideo:")
    
    if log:
        df = pd.read_csv(log) if log.name.endswith('.csv') else None
        if not df:
            with st.spinner("Dekodowanie..."):
                dec = get_decoder_path()
                with open("/tmp/inst.bbl", "wb") as f: f.write(log.getbuffer())
                subprocess.run([dec, "/tmp/inst.bbl"])
                csvs = sorted(glob.glob("/tmp/inst*.csv"))
                if csvs: df = pd.read_csv(csvs[0])
        
        if df is not None:
            # Instruktor zawsze widzi wykresy (Premium)
            roll_col = [c for c in df.columns if 'rcCommand[0]' in c or ('rcCommand' in c and '0' in c)][0]
            pitch_col = [c for c in df.columns if 'rcCommand[1]' in c or ('rcCommand' in c and '1' in c)][0]
            jr, jp = df[roll_col].diff().abs().mean(), df[pitch_col].diff().abs().mean()
            
            render_charts(df)
            
            if st.button("🤖 Generuj Analizę dla Ucznia"):
                model = genai.GenerativeModel('gemini-1.5-flash')
                res = model.generate_content(f"Jako Instruktor FPV oceń lot. Roll Jerk: {jr:.2f}, Pitch Jerk: {jp:.2f}. Napisz raport JSON z oceną 1-10 i zadaniami.")
                try:
                    js = json.loads(res.text.replace("```json","").replace("```","").strip())
                    st.session_state.draft = f"### 🏆 Raport Premium od Instruktora\n\n**Ocena:** {js['ocena']}/10\n\n**Diagnoza:** {js['diagnoza']}\n\n**Zadanie:** {js['zadanie']}"
                    st.session_state.meta = {"ocena": js['ocena'], "premium": True}
                except: st.error("AI błąd")

    if 'draft' in st.session_state and st.session_state.draft:
        final = st.text_area("Finalna edycja:", value=st.session_state.draft, height=200)
        if st.button("🚀 Wyślij jako Raport Premium"):
            wpis = {"data": datetime.now().strftime("%Y-%m-%d"), "ocena": st.session_state.meta['ocena'], "raport": final, "wideo": v_url, "premium": True}
            zads = k_data['zadania']
            zads.append(wpis)
            supabase.table('konta').update({"zadania": zads}).eq('email', wybrany_em).execute()
            st.session_state.draft = None
            st.success("Wysłano raport Premium!")

# ==========================================
# WIDOK KURSANTA
# ==========================================
else:
    st.header(f"🎓 Twój Panel: {user_data['imie']}")
    st.metric("Twoje Tokeny 🎟️", user_data['tokeny'])
    
    st.divider()
    st.subheader("📤 Nowa Analiza")
    tryb = st.radio("Wybierz pakiet:", ["📄 Opis AI (1 Token)", "💎 Pełny Raport + Wykresy (2 Tokeny)"])
    koszt = 1 if "1 Token" in tryb else 2
    
    u_log = st.file_uploader("Wgraj log .bbl", type=['bbl'])
    
    if u_log and st.button(f"Uruchom analizę ({koszt} Tokeny)"):
        if user_data['tokeny'] >= koszt:
            with st.spinner("Przetwarzanie danych..."):
                dec = get_decoder_path()
                with open("/tmp/kurs.bbl", "wb") as f: f.write(u_log.getbuffer())
                subprocess.run([dec, "/tmp/kurs.bbl"])
                csvs = sorted(glob.glob("/tmp/kurs*.csv"))
                if csvs:
                    df = pd.read_csv(csvs[0])
                    roll_c = [c for c in df.columns if 'rcCommand[0]' in c or ('rcCommand' in c and '0' in c)][0]
                    pitch_c = [c for c in df.columns if 'rcCommand[1]' in c or ('rcCommand' in c and '1' in c)][0]
                    jr, jp = df[roll_c].diff().abs().mean(), df[pitch_c].diff().abs().mean()
                    
                    if koszt == 2: render_charts(df) # Wykresy tylko w Premium
                    
                    # Generowanie tekstu AI
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    res = model.generate_content(f"Analiza FPV. Roll Jerk: {jr:.2f}, Pitch Jerk: {jp:.2f}. Podaj JSON z oceną 1-10 i diagnozą.")
                    js = json.loads(res.text.replace("```json","").replace("```","").strip())
                    
                    pre_txt = "💎 RAPORT PREMIUM" if koszt == 2 else "📄 RAPORT PODSTAWOWY"
                    raport_txt = f"### {pre_txt}\n\n**Ocena:** {js['ocena']}/10\n\n**Analiza AI:** {js['diagnoza']}\n\n**Zadanie:** {js['zadanie']}"
                    
                    # Zapis
                    nowy_wpis = {
                        "data": datetime.now().strftime("%Y-%m-%d"),
                        "ocena": js['ocena'],
                        "raport": raport_txt,
                        "premium": (koszt == 2) # Flaga czy raport ma wykresy
                    }
                    zadania = user_data['zadania']
                    zadania.append(nowy_wpis)
                    supabase.table('konta').update({"zadania": zadania, "tokeny": user_data['tokeny'] - koszt}).eq('email', st.session_state.zalogowany_uzytkownik).execute()
                    st.rerun()
        else:
            st.error("Brak tokenów!")

    st.divider()
    st.subheader("📋 Historia Twoich Lotów")
    for z in reversed(user_data['zadania']):
        if isinstance(z, dict):
            status = "💎 Premium" if z.get('premium') else "📄 Basic"
            with st.expander(f"{z.get('data')} | {status} | Ocena: {z.get('ocena')}/10"):
                st.markdown(z.get('raport'))
                if z.get('wideo'): st.video(z.get('wideo'))
                # Jeśli raport jest Premium, a kursant go przegląda - nie rysujemy wykresów na żywo, 
                # ale informujemy, że w wersji Premium ma pełen opis. 
                # (Dla uproszczenia darmowego serwera, wykresy rysujemy tylko w momencie generowania)
