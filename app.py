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
import plotly.graph_objects as go

st.set_page_config(page_title="Trener FPV", page_icon="🚁", layout="wide")

# ==========================================
# AUTO-INSTALATOR DEKODERA BETAFLIGHT (Działa w tle na serwerze)
# ==========================================
@st.cache_resource
def get_decoder_path():
    extract_dir = "/tmp/bbt_source"
    zip_path = "/tmp/bbt_src.zip"
    executable = f"{extract_dir}/blackbox-tools-master/obj/blackbox_decode"
    
    if not os.path.exists(executable):
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        os.makedirs(extract_dir, exist_ok=True)
        
        url = "https://github.com/betaflight/blackbox-tools/archive/refs/heads/master.zip"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        
        try:
            with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                out_file.write(response.read())
                
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                
            source_dir = f"{extract_dir}/blackbox-tools-master"
            subprocess.run(["make", "obj/blackbox_decode"], cwd=source_dir, check=True, capture_output=True)
            
        except Exception as e:
            st.cache_resource.clear()
            raise RuntimeError(f"Serwer nie poradził sobie z kompilacją kodu: {e}")
            
    if os.path.exists(executable):
        os.chmod(executable, 0o755)
        return executable
        
    st.cache_resource.clear()
    return None

# ==========================================
# POŁĄCZENIE Z BAZĄ SUPABASE
# ==========================================
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = get_supabase()

if 'zalogowany_uzytkownik' not in st.session_state:
    st.session_state.zalogowany_uzytkownik = None

# ==========================================
# EKRAN LOGOWANIA I REJESTRACJI
# ==========================================
if st.session_state.zalogowany_uzytkownik is None:
    st.title("🚁 Akademia FPV")
    st.markdown("Zaloguj się, aby uzyskać dostęp do panelu treningowego.")

    tab_logowanie, tab_rejestracja = st.tabs(["🔐 Zaloguj się", "📝 Zarejestruj nowe konto"])

    with tab_logowanie:
        login_email = st.text_input("Adres E-mail")
        login_haslo = st.
