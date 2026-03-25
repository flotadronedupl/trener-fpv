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

st.set_page_config(page_title="Trener FPV", page_icon="🚁", layout="wide")

# ==========================================
# KONFIGURACJA API GEMINI
# ==========================================
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except KeyError:
    st.error("🚨 Brak klucza API Gemini w Secrets!")
    st.stop()

if 'raport_draft' not in st.session_state:
    st.session_state.raport_draft = None
if 'raport_meta' not in st.session_state:
    st.session_state.raport_meta = {}

# ==========================================
# NARZĘDZIA DEKODERA
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

@st.cache_resource
def get_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = get_supabase()

if 'zalogowany_uzytkownik' not in st.session_state:
    st.session_state.zalogowany_uzytkownik = None

# ==========================================
# LOGOWANIE
# ==========================================
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
        st.info("Rejestracja Kursanta")
        rem = st.text_input("Nowy E-mail")
        rpw = st.text_input("Nowe Hasło", type="password")
        rnm = st.text_input("Imię")
        if st.button("📝 Stwórz konto"):
            supabase.table('konta').insert({'email': rem, 'haslo': rpw, 'imie': rnm, 'rola': 'Kursant', 'tokeny': 5, 'zadania': []}).execute()
            st.success("Gotowe!")
    st.stop()

user_data = supabase.table('konta').select('*').eq('email', st.session_state.zalogowany_uzyv_data := st.session_state.zalogowany_uzytkownik).execute().data[0]

with st.sidebar:
    st.title(f"Witaj {user_data['imie']}")
    if st.button("🚪 Wyloguj"):
        st.session_state.zalogowany_uzytkownik = None
        st.rerun()

# ==========================================
# WIDOK INSTRUKTORA
# ==========================================
if user_data['rola'] == "Instruktor":
    st.header("👨‍🏫 Panel Zarządzania")
    kursanci = supabase.table('konta').select('*').eq('rola', 'Kursant').execute().data
    wybrany_em = st.selectbox("Kursant:", [k['email'] for k in kursanci])
    k_data = next(k for k in kursanci if k['email'] == wybrany_em)

    with st.expander("📜 Historia zadań"):
        for z in reversed(k_data['zadania']):
            if isinstance(z, dict):
                st.write(f"**{z.get('data')} | Ocena: {z.get('ocena')}/10**")
                st.write(z.get('raport'))
            else: st.write(z)
            st.divider()

    col1, col2 = st.columns(2)
    with col1:
        log = st.file_uploader("Log (.bbl / .csv)", type=['bbl', 'csv'])
        v_url = st.text_input("Link do wideo:")
        
    df = None
    if log:
        if log.name.endswith('.csv'): df = pd.read_csv(log)
        else:
            dec = get_decoder_path()
            with open("/tmp/t.bbl", "wb") as f: f.write(log.getbuffer())
            subprocess.run([dec, "/tmp/t.bbl"])
            csvs = glob.glob("/tmp/t*.csv")
            if csvs: df = pd.read_csv(csvs[0])

    if df is not None:
        # Analiza
        thr = [c for c in df.columns if 'rcCommand[3]' in c or 'rcCommand' in c and '3' in c][0]
        roll = [c for c in df.columns if 'rcCommand[0]' in c or 'rcCommand' in c and '0' in c][0]
        pitch = [c for c in df.columns if 'rcCommand[1]' in c or 'rcCommand' in c and '1' in c][0]
        
        j_r = df[roll].diff().abs().mean()
        j_p = df[pitch].diff().abs().mean()
        
        # Wykresy (Skrócone dla czytelności)
        krok = max(1, len(df)//5000)
        pdf = df.iloc[::krok]
        
        t1, t2 = st.tabs(["📊 Wykresy", "🪐 3D"])
        with t1:
            f2d = go.Figure()
            f2d.add_trace(go.Scatter(y=pdf[thr], name="Gaz", line=dict(color='orange')))
            f2d.update_layout(template="plotly_dark", height=300)
            st.plotly_chart(f2d, use_container_width=True)
        with t2:
            f3d = go.Figure(data=[go.Scatter3d(x=pdf[roll].cumsum()/500, y=pdf[pitch].cumsum()/500, z=np.arange(len(pdf)), mode='lines', line=dict(color=pdf[thr], colorscale='Jet'))])
            f3d.update_layout(template="plotly_dark", height=400)
            st.plotly_chart(f3d, use_container_width=True)

        if st.button("🤖 Generuj Draft AI"):
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"Oceń lot FPV. Szarpanie Roll: {j_r:.2f}, Pitch: {j_p:.2f}. Zwróć JSON: {{'ocena': 1-10, 'diagnoza': '...', 'zadanie': '...'}}"
            res = model.generate_content(prompt)
            try:
                js = json.loads(res.text.replace("```json","").replace("```","").strip())
                st.session_state.raport_draft = f"### Ocena Systemu: {js['ocena']}/10\n\n**Diagnoza:** {js['diagnoza']}\n\n**Zadanie:** {js['zadanie']}"
                st.session_state.raport_meta = {"j_r": float(j_r), "j_p": float(j_p)}
            except: st.error("AI miało gorszy dzień. Spróbuj ponownie.")

    if st.session_state.raport_draft:
        final_rep = st.text_area("Edytuj raport:", value=st.session_state.raport_draft, height=200)
        if st.button("🚀 WYŚLIJ DO KURSANTA"):
            # KLUCZOWA POPRAWKA: Wyciągamy ocenę z tekstu edytora!
            ocena_match = re.search(r"Ocena Systemu: (\d+)/10", final_rep)
            ocena_final = int(ocena_match.group(1)) if ocena_match else 0
            
            nowy_wpis = {
                "data": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "ocena": ocena_final,
                "j_r": st.session_state.raport_meta.get("j_r", 0),
                "raport": final_rep,
                "wideo": v_url
            }
            aktualne = k_data['zadania']
            aktualne.append(nowy_wpis)
            supabase.table('konta').update({"zadania": aktualne}).eq('email', wybrany_em).execute()
            st.session_state.raport_draft = None
            st.success("Wysłano!")
            time.sleep(1)
            st.rerun()

# ==========================================
# WIDOK KURSANTA
# ==========================================
else:
    st.header(f"🎓 Panel Kursanta: {user_data['imie']}")
    zadania = user_data['zadania']
    
    # Wykres postępów
    if zadania and isinstance(zadania[0], dict):
        oceny = [z['ocena'] for z in zadania if isinstance(z, dict) and 'ocena' in z]
        if oceny:
            figp = go.Figure(go.Scatter(y=oceny, mode='lines+markers', name="Twoja Forma", line=dict(color='gold')))
            figp.update_layout(title="Twój Rozwój", template="plotly_dark", height=250)
            st.plotly_chart(figp, use_container_width=True)

    st.subheader("📥 Twoje Raporty")
    if not zadania: st.info("Czekamy na Twój pierwszy lot!")
    for z in reversed(zadania):
        if isinstance(z, dict):
            with st.expander(f"Lot z dnia {z.get('data')} | Ocena: {z.get('ocena')}/10"):
                st.markdown(z.get('raport'))
                if z.get('wideo'): st.video(z.get('wideo'))
        else:
            with st.expander("Stary raport"): st.write(z)
