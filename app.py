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
# KONFIGURACJA API I SESJI
# ==========================================
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

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
    # Detekcja kolumn
    thr = [c for c in df.columns if 'rcCommand[3]' in c or ('rcCommand' in c and '3' in c)][0]
    roll = [c for c in df.columns if 'rcCommand[0]' in c or ('rcCommand' in c and '0' in c)][0]
    pitch = [c for c in df.columns if 'rcCommand[1]' in c or ('rcCommand' in c and '1' in c)][0]
    
    # Matematyka
    j_r = df[roll].diff().abs().mean()
    j_p = df[pitch].diff().abs().mean()
    avg_t = df[thr].mean()
    
    # Kafelki Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Średni Gaz", f"{avg_t:.0f}")
    m2.metric("Płynność Roll (Jerk)", f"{j_r:.2f}")
    m3.metric("Płynność Pitch (Jerk)", f"{j_p:.2f}")
    
    if show_charts:
        krok = max(1, len(df)//5000)
        pdf = df.iloc[::krok]
        
        tab1, tab2, tab3 = st.tabs(["📈 Drążki 2D", "🪐 Tunel 3D", "🔋 Battery Sag"])
        
        with tab1:
            f2d = go.Figure()
            f2d.add_trace(go.Scatter(y=pdf[thr], name="Throttle", line=dict(color='orange', width=2)))
            f2d.add_trace(go.Scatter(y=pdf[roll], name="Roll", line=dict(color='cyan', width=1), opacity=0.6))
            f2d.add_trace(go.Scatter(y=pdf[pitch], name="Pitch", line=dict(color='magenta', width=1), opacity=0.6))
            f2d.update_layout(template="plotly_dark", height=350, margin=dict(l=0,r=0,t=20,b=0))
            st.plotly_chart(f2d, use_container_width=True)
            
        with tab2:
            x = pdf[roll].cumsum()/500
            y = pdf[pitch].cumsum()/500
            z = np.arange(len(pdf))
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
            else:
                st.info("Brak danych o napięciu baterii.")
    
    return {"j_r": float(j_r), "j_p": float(j_p), "avg_t": float(avg_t)}

# ==========================================
# LOGOWANIE
# ==========================================
if st.session_state.zalogowany_uzytkownik is None:
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
        rem = st.text_input("Nowy Email")
        rpw = st.text_input("Nowe Hasło", type="password")
        rnm = st.text_input("Imię")
        if st.button("📝 Załóż konto Kursanta"):
            supabase.table('konta').insert({'email': rem, 'haslo': rpw, 'imie': rnm, 'rola': 'Kursant', 'tokeny': 5, 'zadania': []}).execute()
            st.success("Konto gotowe!")
    st.stop()

# Pobranie danych usera
user_res = supabase.table('konta').select('*').eq('email', st.session_state.zalogowany_uzytkownik).execute()
user_data = user_res.data[0]

with st.sidebar:
    st.title(f"Profil: {user_data['imie']}")
    st.write(f"Rola: **{user_data['rola']}**")
    if st.button("🚪 Wyloguj"):
        st.session_state.zalogowany_uzytkownik = None
        st.rerun()

# ==========================================
# WIDOK INSTRUKTORA (Zawsze Pro/Premium)
# ==========================================
if user_data['rola'] == "Instruktor":
    st.header("👨‍🏫 Panel Instruktorski Master")
    kursanci = supabase.table('konta').select('*').eq('rola', 'Kursant').execute().data
    wybrany_em = st.selectbox("Wybierz kursanta:", [k['email'] for k in kursanci])
    k_data = next(k for k in kursanci if k['email'] == wybrany_em)

    with st.expander("📜 Historia postępów ucznia"):
        for z in reversed(k_data['zadania']):
            if isinstance(z, dict):
                st.write(f"**{z.get('data')} | Ocena: {z.get('ocena')}/10**")
                st.markdown(z.get('raport'))
            else: st.write(z)
            st.divider()

    col_l, col_v = st.columns(2)
    with col_l: log = st.file_uploader("Wgraj log (.bbl/.csv)", type=['bbl', 'csv'])
    with col_v: v_url = st.text_input("Link do wideo (YouTube/Drive):")
    
    df = None
    if log:
        if log.name.endswith('.csv'): df = pd.read_csv(log)
        else:
            with st.spinner("Dekodowanie BBL..."):
                dec = get_decoder_path()
                with open("/tmp/i.bbl", "wb") as f: f.write(log.getbuffer())
                subprocess.run([dec, "/tmp/i.bbl"])
                csvs = sorted(glob.glob("/tmp/i*.csv"))
                if csvs: df = pd.read_csv(csvs[0])

    if df is not None:
        stats = render_pro_dashboard(df, show_charts=True)
        
        if st.button("🤖 Generuj Draft Raportu (JSON AI)"):
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = f"Analiza FPV. Roll Jerk: {stats['j_r']:.2f}, Pitch Jerk: {stats['j_p']:.2f}. Zwróć JSON: {{'ocena': 1-10, 'diagnoza': '...', 'zadanie': '...'}}"
            res = model.generate_content(prompt)
            try:
                js = json.loads(res.text.replace("```json","").replace("```","").strip())
                st.session_state.raport_draft = f"### Ocena Systemu: {js['ocena']}/10\n\n**🩺 Diagnoza:**\n{js['diagnoza']}\n\n**🏁 Zadanie:**\n{js['zadanie']}"
                st.session_state.raport_meta = {"ocena": js['ocena'], "j_r": stats['j_r']}
            except: st.error("AI Error. Spróbuj ponownie.")

    if st.session_state.raport_draft:
        final = st.text_area("Edytuj raport przed wysłaniem:", value=st.session_state.raport_draft, height=200)
        if st.button("🚀 WYŚLIJ JAKO PREMIUM"):
            match = re.search(r"Ocena Systemu: (\d+)/10", final)
            ocena = int(match.group(1)) if match else 0
            nowy = {"data": datetime.now().strftime("%Y-%m-%d %H:%M"), "ocena": ocena, "raport": final, "wideo": v_url, "jerk": st.session_state.raport_meta.get('j_r',0), "premium": True}
            aktualne = k_data['zadania']
            aktualne.append(nowy)
            supabase.table('konta').update({"zadania": aktualne}).eq('email', wybrany_em).execute()
            st.session_state.raport_draft = None
            st.success("Wysłano!")
            time.sleep(1)
            st.rerun()

# ==========================================
# WIDOK KURSANTA (Model 1 vs 2 Tokeny)
# ==========================================
else:
    st.header(f"🎓 Panel Kursanta: {user_data['imie']}")
    
    # Wykres Postępów (Grywalizacja)
    zads = user_data.get('zadania', [])
    if len(zads) > 1:
        oceny = [z['ocena'] for z in zads if isinstance(z, dict) and 'ocena' in z]
        st.subheader("📈 Twoja Krzywa Uczenia")
        figp = go.Figure(go.Scatter(y=oceny, mode='lines+markers', name="Ocena", line=dict(color='gold', width=3)))
        figp.update_layout(template="plotly_dark", height=250, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(figp, use_container_width=True)

    st.divider()
    col_t1, col_t2 = st.columns([1, 2])
    with col_t1:
        st.metric("Twoje Tokeny 🎟️", user_data['tokeny'])
        pakiet = st.radio("Wybierz usługę:", ["📄 Analiza Basic (1 Token)", "💎 Analiza Premium (2 Tokeny)"])
    
    with col_t2:
        u_log = st.file_uploader("Wgraj czarną skrzynkę .bbl", type=['bbl'])
        koszt = 1 if "Basic" in pakiet else 2
        
        if u_log and st.button(f"🚀 Uruchom {pakiet}"):
            if user_data['tokeny'] >= koszt:
                with st.spinner("Przetwarzanie danych..."):
                    dec = get_decoder_path()
                    with open("/tmp/u.bbl", "wb") as f: f.write(u_log.getbuffer())
                    subprocess.run([dec, "/tmp/u.bbl"])
                    csvs = sorted(glob.glob("/tmp/u*.csv"))
                    if csvs:
                        df = pd.read_csv(csvs[0])
                        # Dashboard Premium tylko dla 2 tokenów
                        stats = render_pro_dashboard(df, show_charts=(koszt == 2))
                        
                        # AI Raport
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        res = model.generate_content(f"Analiza FPV. Jerk: {stats['j_r']:.2f}. Podaj JSON z oceną 1-10 i diagnozą.")
                        try:
                            js = json.loads(res.text.replace("```json","").replace("```","").strip())
                            tag = "💎 PREMIUM" if koszt == 2 else "📄 BASIC"
                            txt = f"### {tag} RAPORT AI\n\n**Ocena:** {js['ocena']}/10\n\n**Analiza:** {js['diagnoza']}\n\n**Zadanie:** {js['zadanie']}"
                            
                            nowy_wpis = {"data": datetime.now().strftime("%Y-%m-%d"), "ocena": js['ocena'], "raport": txt, "premium": (koszt==2), "jerk": stats['j_r']}
                            zads.append(nowy_wpis)
                            supabase.table('konta').update({"zadania": zads, "tokeny": user_data['tokeny'] - koszt}).eq('email', st.session_state.zalogowany_uzytkownik).execute()
                            st.balloons()
                            time.sleep(2)
                            st.rerun()
                        except: st.error("AI Error")
            else: st.error("Brak tokenów!")

    st.subheader("📋 Historia Twoich Analiz")
    for z in reversed(zads):
        if isinstance(z, dict):
            status = "💎" if z.get('premium') else "📄"
            with st.expander(f"{status} Analiza {z.get('data')} | Ocena: {z.get('ocena')}/10"):
                st.markdown(z.get('raport'))
                if z.get('wideo'): st.video(z.get('wideo'))
