### Survey Generator Streamlit App with Firebase Integration ###


import streamlit as st
import requests
import json
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Streamlit app configuration
st.set_page_config(page_title="Survey Generator", layout="wide")

# Title and description
st.title("Survey Generator")
st.write("Define your survey goal and select topics to generate a comprehensive survey.")

# Predefined topics
available_topics = [
    'Customer Satisfaction',
    'Product Feedback',
    'Market Research',
    'Employee Engagement',
    'Event Feedback',
    'User Experience',
    'Brand Awareness',
]

# Initialize session state
if 'selected_topics' not in st.session_state:
    st.session_state.selected_topics = []
if 'survey_generated' not in st.session_state:
    st.session_state.survey_generated = False
if 'survey_data' not in st.session_state:
    st.session_state.survey_data = None
if 'survey_goal' not in st.session_state:
    st.session_state.survey_goal = ""
if 'custom_topics' not in st.session_state:
    st.session_state.custom_topics = []

# Combine predefined and custom topics
all_topics = available_topics + st.session_state.custom_topics

# Firebase Firestore setup
try:
    # Load credentials
    firebase_creds = {
    "type": st.secrets["firebase"]["type"],
    "project_id": st.secrets["firebase"]["project_id"],
    "private_key_id": st.secrets["firebase"]["private_key_id"],
    "private_key": st.secrets["firebase"]["private_key"],
    "client_email": st.secrets["firebase"]["client_email"],
    "client_id": st.secrets["firebase"]["client_id"],
    "auth_uri": st.secrets["firebase"]["auth_uri"],
    "token_uri": st.secrets["firebase"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
    }

    cred = credentials.Certificate(firebase_creds)
    # Initialize Firebase app if not already initialized
    try:
        firebase_admin.initialize_app(cred)
    except ValueError:
        # Ignore if app is already initialized (handles Streamlit hot-reloading)
        pass
except Exception as e:
    st.error(f"Failed to load Firebase credentials: {str(e)}. Please ensure 'firebase-credentials.json' exists and is valid.")
    st.stop()

try:
    db = firestore.client()
    collection = db.collection('survey_data')
except Exception as e:
    st.error(f"Failed to connect to Firebase Firestore: {str(e)}")
    st.stop()

# Survey goal input
survey_goal = st.text_area("Survey Goal", placeholder="e.g., To collect customer opinions on food quality, service, and ambiance at [Restaurant Name] ", height=100)

# Topic selection
st.subheader("Select Topics")
cols = st.columns(3)
for i, topic in enumerate(all_topics):
    col = cols[i % 3]
    if col.checkbox(topic, key=f"topic_{topic}", value=topic in st.session_state.selected_topics):
        if topic not in st.session_state.selected_topics:
            st.session_state.selected_topics.append(topic)
    else:
        if topic in st.session_state.selected_topics:
            st.session_state.selected_topics.remove(topic)

# Custom topic input (placed below topic selection)
st.subheader("Add a topic if it’s unavailable")
custom_topic = st.text_input("Enter a custom topic (optional)", placeholder="e.g., Website Usability", key="custom_topic_input")
if st.button("Add Custom Topic"):
    if custom_topic.strip() and custom_topic.strip() not in all_topics:
        st.session_state.custom_topics.append(custom_topic.strip())
        st.session_state.selected_topics.append(custom_topic.strip())  # Auto-select the custom topic
        st.success(f"Added custom topic: {custom_topic.strip()}")
    elif not custom_topic.strip():
        st.error("Please enter a valid topic name")
    else:
        st.error("This topic already exists")

# Generate survey button
if st.button("Generate Survey"):
    if not survey_goal.strip():
        st.error("Please define your survey goal")
    elif not st.session_state.selected_topics:
        st.error("Please select at least one topic")
    else:
        # Store survey goal in session state
        st.session_state.survey_goal = survey_goal.strip()

        # Create the prompt
        prompt = f"""
Create a comprehensive survey for {survey_goal.strip()} 
focusing on the following topics: {', '.join(st.session_state.selected_topics)}.
Include a diverse mix of question types including multiple choice, Yes/No, Rating Scales (1-5), 
and open-ended questions. For multiple choice questions, provide 3-5 relevant options.
Title: Survey for {survey_goal.strip()}
Description: This survey aims to gather insights on {survey_goal.strip()}.

Format each question as:
{{
  "text": "Question text here",
  "type": "multiple choice OR rating scale OR open-ended OR yes/no",
  "options": ["Option 1", "Option 2", "Option 3"] // Include for multiple choice and yes/no; omit or empty for open-ended
}}
"""

        # Send request to FastAPI endpoint
        try:
            response = requests.post(
                "https://civil-nertie-udula-g-423ec937.koyeb.app/generate_survey/",
                data={"prompt": prompt}
            )
            response.raise_for_status()
            survey_data = response.json()

            # Display the survey questions
            st.subheader("Generated Survey Questions")
            if "survey_questions" in survey_data:
                st.session_state.survey_data = survey_data["survey_questions"]
                st.session_state.survey_generated = True
                for i, question in enumerate(survey_data["survey_questions"], 1):
                    st.markdown(f"**Question {i}:** {question['text']}")
                    # Display options for multiple choice, yes/no, and rating scale questions
                    if "options" in question and question["options"] and question["type"] != "open-ended":
                        for j, option in enumerate(question["options"], 1):
                            st.markdown(f"- {option}")
                    elif question["type"] == "rating scale" and not question.get("options"):
                        # Default options for rating scale if none provided
                        st.markdown("- 1 (Poor) to 5 (Excellent)")
                    st.markdown("---")
            else:
                st.error(survey_data.get("error", "Failed to generate survey questions"))
                st.session_state.survey_generated = False
        except requests.exceptions.RequestException as e:
            st.error(f"Failed to connect to the FastAPI server: {str(e)}")
            st.session_state.survey_generated = False

# Feedback section (displayed only after survey is generated)
if st.session_state.survey_generated and st.session_state.survey_data:
    st.subheader("Survey Feedback")
    star_rating = st.radio(
        "Rate the survey",
        options=["1 ⭐", "2 ⭐", "3 ⭐", "4 ⭐", "5 ⭐"],
        index=2,  # Default to 3 stars
        horizontal=True
    )
    feedback = st.text_area("Optional Feedback", placeholder="Share your thoughts about the survey (optional)", height=100)
    if st.button("Submit Feedback"):
        # Convert star rating to numeric value
        rating_value = int(star_rating[0])
        # Save to Firebase Firestore
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        survey_doc = {
            'timestamp': timestamp,
            'survey_goal': st.session_state.survey_goal,
            'selected_topics': ', '.join(st.session_state.selected_topics),
            'survey_questions': json.dumps(st.session_state.survey_data),
            'star_rating': rating_value,
            'feedback': feedback.strip() if feedback.strip() else ""
        }
        try:
            collection.add(survey_doc)
            st.success("Thank you for your feedback!")
            # Reset survey state to allow generating a new survey
            st.session_state.survey_generated = False
            st.session_state.survey_data = None
        except Exception as e:
            st.error(f"Failed to save feedback to Firebase: {str(e)}")
