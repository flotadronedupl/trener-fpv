import streamlit as st
import pandas as pd
import numpy as np
import time
import google.generativeai as genai # Prawdziwe AI!

st.set_page_config(page_title="Trener FPV", page_icon="🚁", layout="wide")

# --- PANEL BOCZNY (Sekrety) ---
with st.sidebar:
    st.header("⚙️ Ustawienia Systemu")
    api_key = st.text_input("Wklej klucz API Gemini:", type="password")
    if api_key:
        genai.configure(api_key=api_key)
        st.success("Klucz API podłączony!")
    else:
        st.warning("Podaj klucz API, aby uruchomić Trenera AI.")

st.title("🚁 Platforma Treningowa FPV - Wersja Działająca")
st.markdown("Wgraj dane z lotu i pozwól Sztucznej Inteligencji wyciągnąć wnioski.")

st.divider()

# Utrzymujemy opcję Demo na wypadek braku pliku .csv
if 'demo_loaded' not in st.session_state:
    st.session_state.demo_loaded = False

if st.button("🧪 Załaduj Lot Janka (Brak własnego pliku)"):
    st.session_state.demo_loaded = True

col1, col2 = st.columns(2)
df = None # Pusta zmienna na nasze dane

with col1:
    st.header("1. Telemetria (Drążki)")
    blackbox_file = st.file_uploader("Przeciągnij plik Blackbox (.csv)", type=['csv'])
    
    if st.session_state.demo_loaded or blackbox_file is not None:
        if st.session_state.demo_loaded:
            czas = np.linspace(0, 10, 500)
            throttle = 30 + 20 * np.sin(czas) + np.random.normal(0, 5, 500) # Celowe szarpanie gazem
            roll = 50 * np.sin(czas * 2)
            df = pd.DataFrame({'Czas': czas, 'Throttle': throttle, 'Roll': roll})
            st.info("⚠️ Użyto danych testowych.")
        else:
            df = pd.read_csv(blackbox_file)

        st.line_chart(df.set_index(df.columns[0])) # Rysuje wykres bez względu na nazwy kolumn

with col2:
    st.header("2. Wideo (Opcjonalnie)")
    video_file = st.file_uploader("Przeciągnij plik wideo (.mp4)", type=['mp4'])
    if video_file:
        st.video(video_file)

st.divider()

# --- PRAWDZIWY MODUŁ AI ---
st.header("🧠 Panel Trenera AI")

if st.button("🚀 Wygeneruj Raport"):
    if not api_key:
        st.error("Wklej klucz API w lewym panelu!")
    elif df is not None:
        with st.spinner('AI analizuje parametry lotu...'):
            try:
                # 1. Obliczamy statystyki z lotu, żeby wysłać je do AI
                throttle_col = [c for c in df.columns if 'Throttle' in c or 'throttle' in c.lower()]
                
                if throttle_col:
                    sredni_gaz = df[throttle_col[0]].mean()
                    wariancja_gazu = df[throttle_col[0]].var() # Im wyższa wariancja, tym mocniejsze szarpanie
                else:
                    sredni_gaz = "Brak danych"
                    wariancja_gazu = "Brak danych"

                # 2. Tworzymy System Prompt (Instrukcję dla AI)
                prompt = f"""
                Jesteś profesjonalnym instruktorem dronów wyścigowych FPV. 
                Oto suche dane z analizy ruchów drążków kursanta (z czarnej skrzynki):
                - Średnie wychylenie przepustnicy (Throttle): {sredni_gaz}
                - Wariancja (szarpanie) na przepustnicy: {wariancja_gazu}
                
                Zasada: Jeśli wariancja jest wyższa niż 15, oznacza to, że kursant dramatycznie "pompuje" gazem w zakrętach i gubi płynność.
                
                Zadanie:
                1. Napisz 2-zdaniową, bezpośrednią i profesjonalną diagnozę błędu. Zwracaj się bezpośrednio do kursanta (np. "Cześć Janek...").
                2. Wygeneruj dla niego 1 konkretne zadanie poprawkowe do wykonania na łące lub w symulatorze.
                Formatuj odpowiedź używając pogrubień i list.
                """

                # 3. Automatyczne wykrywanie najlepszego modelu
                dostepne_modele = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                
                if not dostepne_modele:
                    st.error("Twój klucz API nie ma przypisanych żadnych modeli! Wygeneruj nowy klucz w Google AI Studio.")
                    st.stop()
                    
                # Szuka szybkiego modelu 'flash', a jak go nie znajdzie - bierze pierwszy dostępny
                wybrany_model = next((m for m in dostepne_modele if 'flash' in m.lower()), dostepne_modele[0])
                
                model = genai.GenerativeModel(wybrany_model)
                response = model.generate_content(prompt)
              
                # 4. Wyświetlamy wynik!
                st.success("Raport wygenerowany pomyślnie!")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"Wystąpił błąd podczas połączenia z AI: {e}")
    else:
        st.error("Najpierw wgraj plik z kontrolera lotu lub załaduj lot testowy!")
