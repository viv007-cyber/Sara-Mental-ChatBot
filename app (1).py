from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import torch
from transformers import pipeline
import google.generativeai as genai
import json
import os
import uuid
from datetime import datetime

# Load Hugging Face Sentiment Analysis Model using PyTorch
sentiment_analyzer = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment", framework="pt")

# Configure Gemini API
API_KEY = "AIzaSyBxnufV01q5IVlAHJ1OCDdg3H2DI8LJzl8"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# File to store user data
USER_DATA_FILE = "user_data.json"

app = Flask(__name__)
CORS(app)  # Enable CORS to allow cross-origin requests
app.secret_key = os.urandom(24)

FLASK_BACKEND_URL = "http://127.0.0.1:5000"

def load_user_data():
    """Loads user data from a JSON file, ensuring JSON integrity."""
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, "r") as file:
                data = json.load(file)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, ValueError):
            print("Warning: user_data.json is corrupted. Resetting data.")
    return {}

def save_user_data(data):
    """Safely writes user data to a JSON file."""
    temp_file = f"{USER_DATA_FILE}.tmp"
    with open(temp_file, "w") as file:
        json.dump(data, file, indent=4)
    os.replace(temp_file, USER_DATA_FILE)  # Atomic write

def analyze_sentiment(text):
    """Returns sentiment category based on analysis."""
    sentiment_result = sentiment_analyzer(text)[0]
    label = sentiment_result["label"]
    if "1 star" in label or "2 star" in label:
        return "negative"
    elif "4 star" in label or "5 star" in label:
        return "positive"
    else:
        return "neutral"

def update_user_profile(user_id, user_input, sentiment, user_data):
    """Updates user mood, chat topics, and history."""
    if user_id not in user_data:
        user_data[user_id] = {"name": "", "mood": [], "topics": [], "chat_history": []}
    
    user_data[user_id]["mood"].append(sentiment)

    words = [word for word in user_input.lower().split() if len(word) > 3 and word.isalpha()]
    current_topics = user_data[user_id]["topics"]
    
    for word in words:
        if word not in current_topics:
            current_topics.append(word)
    
    user_data[user_id]["topics"] = current_topics[-10:]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_data[user_id]["chat_history"].append({"role": "user", "content": user_input, "timestamp": timestamp})
    save_user_data(user_data)

def chatbot_response(user_id, user_input, user_data):
    """Generates a response using Gemini API while considering sentiment and context."""
    sentiment = analyze_sentiment(user_input)
    update_user_profile(user_id, user_input, sentiment, user_data)

    recent_history = user_data[user_id]["chat_history"][-10:]
    context = "\n".join([f"{'User' if msg['role'] == 'user' else 'Sarah'}: {msg['content']}" for msg in recent_history])

    prompt = (
        f"""You are Sarah, an empathic and compassionate Female Psychologist or Psychiatrist, conducting a clinical interview in english. 
        A highly experienced and dedicated Clinical Psychologist with over 30 years of experience in clinical practice and research.
        Specializing in trauma, anxiety disorders, and family therapy, Sarah has a proven track record of successfully treating a wide range of psychological conditions.
        Her deep commitment to patient care and mental health advocacy has driven her to develop innovative therapeutic approaches and lead community mental health initiatives.
        Sarah's extensive career is marked by her unwavering dedication to giving back to the community. 
        She has been actively involved in various community service efforts, including several years of work with children with disabilities and autistic children.
        Her compassionate approach and ability to connect with patients of all ages have made her a respected figure in the field of psychology.
        Sarah is not only a skilled clinician but also a passionate advocate for mental health, continuously striving to improve the lives of those she serves. \n"""
        f"""Don't include your expressions in the response in brackets."""
        f"User's name: {user_data[user_id]['name']}\n"
        f"Recent mood: {user_data[user_id]['mood'][-3:]}\n"
        f"Frequent topics: {', '.join(user_data[user_id]['topics'][-5:])}\n"
        f"Previous conversation:\n{context}\n"
        f"User: {user_input}\nChatbot: """
    )

    try:
        response = model.generate_content(prompt)
        chatbot_reply = response.candidates[0].content.parts[0].text.strip() if response.candidates else "I'm here for you. Let's talk more."
    except Exception as e:
        print(f"API Error: {str(e)}")
        chatbot_reply = "I'm here for you. Let's talk more."

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_data[user_id]["chat_history"].append({"role": "assistant", "content": chatbot_reply, "timestamp": timestamp})
    save_user_data(user_data)

    return chatbot_reply

@app.route('/')
def index():
    """Renders the index page and assigns a session ID."""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handles user messages and returns chatbot responses."""
    data = request.json
    user_input = data.get('message', '').strip()
    user_name = data.get('name', '').strip()
    
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    user_id = session['user_id']
    user_data = load_user_data()

    if user_id not in user_data:
        user_data[user_id] = {"name": "", "mood": [], "topics": [], "chat_history": []}

    if user_name:
        user_data[user_id]['name'] = user_name
        save_user_data(user_data)

    if not user_input:
        return jsonify({'response': "Please enter a message."})

    response = chatbot_response(user_id, user_input, user_data)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
