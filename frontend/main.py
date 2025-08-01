import streamlit as st
import requests
import os
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk
# import streamlit_audiorec  # Removed since we no longer handle is_cloud=True

load_dotenv()

speech_key = os.getenv('SPEECH_KEY')
service_region = os.getenv('SPEECHSERVICE_REGION')
agentic_backend = os.getenv('AGENTIC_BACKEND')
speech_lang = os.getenv('SPEECH_LANG', 'en-US')
is_cloud = os.getenv('IS_CLOUD', 'False').lower() == 'true'  # add this env in Azure config

speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_config.speech_recognition_language = speech_lang

st.set_page_config(page_title="Agentic System Voicebot", page_icon="🤖🗣️")
st.title("Agentic System Voicebot")

def send_to_backend(message, thread_id=None):
    url = agentic_backend
    payload = {"message": message}
    if thread_id:
        payload["thread_id"] = thread_id
    try:
        resp = requests.post(url, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        return data["response"], data.get("thread_id")
    except Exception as e:
        return f"Error: {e}", None


if "messages" not in st.session_state or "thread_id" not in st.session_state:
    st.session_state.messages = []
    st.session_state.thread_id = None


def transcribe_audio_from_wav(wav_bytes):
    """Use Azure Speech SDK to transcribe from wav audio bytes"""
    audio_config = speechsdk.audio.AudioConfig(stream=speechsdk.AudioDataStream(wav_bytes))
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    result = speech_recognizer.recognize_once()
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        return result.text
    else:
        return None


if not is_cloud:
    # Local mic recog (existing approach)
    def transcribe_speech(status_placeholder):
        try:
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
            speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        except Exception as e:
            return "NO_MIC", f"Microphone error: {e}"

        status_placeholder.info("Listening... Speak now")
        try:
            result = speech_recognizer.recognize_once_async().get()
        except Exception as e:
            status_placeholder.error(f"Speech recognition error: {e}")
            return None
        status_placeholder.empty()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text
        elif result.reason == speechsdk.ResultReason.NoMatch:
            status_placeholder.error("No speech could be recognized. Please try again.")
        elif result.reason == speechsdk.ResultReason.Canceled:
            cd = result.cancellation_details
            status_placeholder.error(f"Speech Recognition canceled: {cd.reason}")
            if cd.reason == speechsdk.CancellationReason.Error:
                status_placeholder.error(f"Error details: {cd.error_details}")
        else:
            status_placeholder.error("Unknown speech recognition error.")
        return None


# Chat history container
chat_history_container = st.container()
with chat_history_container:
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).markdown(msg["content"])
st.divider()

control_cols = st.columns([1, 6, 1])
status_placeholder = st.empty()

with control_cols[0]:
    if st.button("New Chat"):
        st.session_state.thread_id = None
        st.session_state.messages = []
        st.rerun()

with control_cols[1]:
    user_input = st.chat_input("Your message...")

with control_cols[2]:
    # Disable the Speak button if is_cloud is True
    speak_btn = st.button("Speak", disabled=is_cloud)
    if speak_btn:
        # Since is_cloud=True case removed, this runs only local mic recog logic
        speech_result = transcribe_speech(status_placeholder)
        if isinstance(speech_result, tuple) and speech_result[0] == "NO_MIC":
            status_placeholder.error("No microphone detected. Please connect a microphone and try again.")
        elif speech_result:
            st.session_state.messages.append({"role": "user", "content": speech_result})
            with chat_history_container:
                st.chat_message("user").markdown(speech_result)

            status_placeholder.info("Waiting for server response...")
            response, thread_id = send_to_backend(speech_result, st.session_state.thread_id)
            if response.startswith("Error:"):
                status_placeholder.error(response)
            else:
                status_placeholder.empty()

            st.session_state.messages.append({"role": "assistant", "content": response})
            with chat_history_container:
                st.chat_message("assistant").markdown(response)

            if thread_id:
                st.session_state.thread_id = thread_id


# Handle user input send event
if 'user_input' in locals() and user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with chat_history_container:
        st.chat_message("user").markdown(user_input)

    status_placeholder.info("Waiting for server response...")
    response, thread_id = send_to_backend(user_input, st.session_state.thread_id)
    if response.startswith("Error:"):
        status_placeholder.error(response)
    else:
        status_placeholder.empty()

    st.session_state.messages.append({"role": "assistant", "content": response})
    with chat_history_container:
        st.chat_message("assistant").markdown(response)

    if thread_id:
        st.session_state.thread_id = thread_id


# Optional CSS for styling …
st.markdown("""
    <style>
    div[data-testid="stMarkdownContainer"] > div { min-width: 400px; max-width: 800px; }
    .stButton > button { height: 50px; font-size: 13px; width: 100%; }
    </style>
    """, unsafe_allow_html=True)
