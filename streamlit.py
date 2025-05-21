import streamlit as st
import requests
import uuid
import json
from datetime import datetime
import os
import speech_recognition as sr
import pyttsx3
import matplotlib.pyplot as plt

# Flask Backend URL
FLASK_BACKEND_URL = "http://127.0.0.1:5000"

# Load or initialize user data
USER_DATA_FILE = "user_data.json"
def load_user_data():
    if not os.path.exists(USER_DATA_FILE):
        return {}
    try:
        with open(USER_DATA_FILE, "r") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)

# Initialize session state
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())
    st.session_state.name = ""

user_data = load_user_data()
user_id = st.session_state.user_id
if user_id not in user_data:
    user_data[user_id] = {"name": "", "mood": [], "topics": [], "chat_history": []}

# Streamlit UI Settings
st.set_page_config(page_title="Sarah - AI Psychologist", page_icon="💙", layout="wide")
st.markdown("""
    <style>
        .main-title { color: #2E86C1; text-align: center; font-size: 40px; font-weight: bold; }
        .sidebar-title { color: #E74C3C; }
        .chat-container { background-color: #F7F9F9; padding: 15px; border-radius: 10px; }
        .user-msg { background-color: #AED6F1; padding: 10px; border-radius: 10px; margin-bottom: 5px; }
        .bot-msg { background-color: #D5DBDB; padding: 10px; border-radius: 10px; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>Sarah - Your AI Psychologist</h1>", unsafe_allow_html=True)
st.sidebar.image("https://source.unsplash.com/400x200/?therapy", use_container_width=True)
st.sidebar.markdown("<h2 class='sidebar-title'>Navigation</h2>", unsafe_allow_html=True)
page = st.sidebar.radio("Go to", ["Chat", "Dashboard", "Mood Analytics"])

name = st.sidebar.text_input("Enter your name:", value=user_data[user_id]["name"])
st.sidebar.write(f"**User ID:** {user_id[:8]}")
st.sidebar.write(f"**Recent Moods:** {', '.join(user_data[user_id]['mood'][-3:])}")
st.sidebar.write(f"**Frequent Topics:** {', '.join(user_data[user_id]['topics'][-5:])}")

if name and name != user_data[user_id]["name"]:
    user_data[user_id]["name"] = name
    save_user_data(user_data)

# Voice Input Function
def get_voice_input():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening...")
        try:
            audio = recognizer.listen(source, timeout=5)
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            return "Could not understand audio. Try again."
        except sr.RequestError:
            return "Error with the speech recognition service."

# Text-to-Speech Function
def speak_text(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

# Chat Page
if page == "Chat":
    st.subheader("💬 Chat with Sarah")
    chat_container = st.container()
    with chat_container:
        for msg in user_data[user_id]["chat_history"][-10:]:
            role = "👤 You:" if msg["role"] == "user" else "🤖 Sarah:"
            color_class = "user-msg" if msg["role"] == "user" else "bot-msg"
            st.markdown(f"<div class='{color_class}'><b>{role}</b> {msg['content']}</div>", unsafe_allow_html=True)
    
    user_input = st.text_input("Type your message:", "", key="user_input")
    if st.button("🎤 Speak"):
        user_input = get_voice_input()
        st.write(f"You said: {user_input}")
    
    if st.button("Send") and user_input:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_data[user_id]["chat_history"].append({"role": "user", "content": user_input, "timestamp": timestamp})
        save_user_data(user_data)
        
        response = requests.post(f"{FLASK_BACKEND_URL}/chat", json={"message": user_input, "name": name})
        chatbot_reply = response.json().get("response", "I'm facing some issues responding right now. Please try again later.")
        
        user_data[user_id]["chat_history"].append({"role": "assistant", "content": chatbot_reply, "timestamp": timestamp})
        save_user_data(user_data)
        speak_text(chatbot_reply)
        st.rerun()

# Dashboard Page
elif page == "Dashboard":
    st.subheader("📊 Dashboard")
    st.write("Welcome to your personal mental health dashboard.")
    st.write(f"**Total Chats:** {len(user_data[user_id]['chat_history'])}")
    st.write(f"**Mood History:** {', '.join(user_data[user_id]['mood'])}")
    
    if len(user_data[user_id]['chat_history']) > 0:
        last_msg = user_data[user_id]['chat_history'][-1]["content"]
        st.write(f"**Last Message:** {last_msg}")

# Mood Analytics Page
elif page == "Mood Analytics":
    st.subheader("📈 Mood Analytics")
    if len(user_data[user_id]['mood']) > 0:
        mood_counts = {mood: user_data[user_id]['mood'].count(mood) for mood in set(user_data[user_id]['mood'])}
        
        fig, ax = plt.subplots()
        ax.bar(mood_counts.keys(), mood_counts.values(), color=['#FF5733', '#33FF57', '#3357FF', '#F4D03F', '#8E44AD'])
        plt.xticks(rotation=45)
        plt.xlabel("Mood")
        plt.ylabel("Frequency")
        plt.title("Mood Trends Over Time")
        st.pyplot(fig)
    else:
        st.write("No mood data available.")