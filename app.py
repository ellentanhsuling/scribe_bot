import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import speech_recognition as sr
import datetime
import numpy as np
import queue
import threading
import av

# Initialize queues for audio processing
audio_queue = queue.Queue()
result_queue = queue.Queue()

# Risk keywords for escalation
RISK_KEYWORDS = [
    "suicide", "kill", "hurt", "harm", "die", "end my life",
    "self harm", "cut myself", "overdose", "pills"
]

def initialize_session_state():
    if 'conversations' not in st.session_state:
        st.session_state.conversations = []
    if 'speaker_count' not in st.session_state:
        st.session_state.speaker_count = 0
    if 'risk_level' not in st.session_state:
        st.session_state.risk_level = "Normal"
    if 'current_text' not in st.session_state:
        st.session_state.current_text = ""

def detect_risk_level(text):
    text = text.lower()
    for keyword in RISK_KEYWORDS:
        if keyword in text:
            return "High"
    return "Normal"

def save_conversation(conversations):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"conversation_{timestamp}.txt"
    
    with open(filename, "w") as f:
        for conv in conversations:
            f.write(f"{conv['timestamp']} - {conv['speaker']}: {conv['text']}\n")
            f.write(f"Risk Level: {conv['risk_level']}\n\n")
    return filename

def process_audio(frame):
    sound = frame.to_ndarray()
    audio_queue.put(sound)
    return av.AudioFrame.from_ndarray(sound, layout='mono')

def audio_frame_callback(frame):
    try:
        recognizer = sr.Recognizer()
        audio_data = frame.to_ndarray().tobytes()
        audio = sr.AudioData(audio_data, sample_rate=16000, sample_width=2)
        text = recognizer.recognize_google(audio)
        if text:
            st.session_state.current_text = text
            return text
    except Exception as e:
        return None

def main():
    st.title("Conversation Transcription & Risk Monitor")
    
    # User Instructions
    st.markdown("""
    ### How to Use This App
    1. **Add Speakers**: Use the 'Add New Speaker' button in the sidebar
    2. **Start Audio**: Click the 'START' button in the audio widget
    3. **Select Speaker**: Choose the current speaker when text appears
    4. **Monitor Risk**: Automatic risk level detection
    5. **Save**: Store the conversation when finished
    
    ### Important Notes
    - Allow microphone access when prompted
    - Speak clearly for better recognition
    - Risk levels are monitored in real-time
    """)
    
    initialize_session_state()

    # Sidebar controls
    st.sidebar.header("Controls")
    if st.sidebar.button("Add New Speaker"):
        st.session_state.speaker_count += 1
        st.sidebar.success(f"Added Person{st.session_state.speaker_count}")

    # WebRTC Audio Streamer
    webrtc_ctx = webrtc_streamer(
        key="speech-to-text",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"video": False, "audio": True},
    )

    if webrtc_ctx.audio_receiver:
        if webrtc_ctx.state.playing:
            try:
                audio_frames = webrtc_ctx.audio_receiver.get_frames(timeout=1)
                for audio_frame in audio_frames:
                    text = audio_frame_callback(audio_frame)
                    if text:
                        speaker = st.selectbox(
                            "Who is speaking?",
                            [f"Person{i+1}" for i in range(st.session_state.speaker_count)]
                        )
                        
                        risk_level = detect_risk_level(text)
                        
                        conversation_entry = {
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "speaker": speaker,
                            "text": text,
                            "risk_level": risk_level
                        }
                        
                        st.session_state.conversations.append(conversation_entry)
                        
                        if risk_level == "High":
                            st.error("⚠️ High Risk Detected - Immediate Action Required")
                            if st.button("Contact Psychologist"):
                                st.info("Connecting to emergency response system...")
                        else:
                            st.success("✓ Normal Risk Level")
                            if st.button("Contact Parents"):
                                st.info("Preparing parent notification...")
            except queue.Empty:
                pass

    # Display conversation history
    if st.session_state.conversations:
        st.markdown("### Conversation History")
        for conv in st.session_state.conversations:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{conv['speaker']}** ({conv['timestamp']}): {conv['text']}")
            with col2:
                if conv['risk_level'] == "High":
                    st.error(f"Risk: {conv['risk_level']}")
                else:
                    st.success(f"Risk: {conv['risk_level']}")

    # Save conversation
    if st.button("Save Conversation"):
        if st.session_state.conversations:
            filename = save_conversation(st.session_state.conversations)
            st.success(f"✅ Conversation saved to {filename}")
        else:
            st.warning("No conversation to save yet")

if __name__ == "__main__":
    main()
