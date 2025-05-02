import os
from dotenv import load_dotenv
from fastapi import FastAPI, Form
from pydantic import BaseModel
import json
import google.generativeai as genai
# Load environment variables from .env file
load_dotenv()

# Use the environment variable for the Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = '''Okay, I understand. Based on the negative feedback keywords: "Poor service," "failed delivery," and "totally unprofessional," I will generate 15 survey questions, including Yes/No, rating scale, Good/Bad choice, and short answer questions, tailored to investigate the issues mentioned. Here's the JSON output:'''

# Load example.json file into the example variable
with open("example.json", "r") as file:
    example = json.load(file)

app = FastAPI()

# Define Gemini function globally
def generate_survey_questions(prompt: str):
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=generation_config,
        system_instruction="You are a system to generate survey-related questions and relevant answers",
    )

    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [
                    "Give me 15 survey-related questions, including Yes/No questions, rating scale questions, Good/Bad choice questions, and short answer questions. refer {example} for more and don't give {bot} in answer",
                ],
            },
            {
                "role": "model",
                "parts": [
                    "Okay, I'm ready. Please provide me the {prompt} that need to generate 15 survey-related questions and just output question in json format. Also avoid response like {bot} and align with the {example} provided.",
                ],
            },
        ]
    )

    response = chat_session.send_message({prompt})

    return response.text

class Item(BaseModel):
    prompt: str

# JSON response
# @app.post("/generate_survey/")
# async def create_item(prompt: str = Form(...)):
#     # Call the global Gemini function
#     survey_questions = generate_survey_questions(prompt)
#     return {"survey_questions": survey_questions}

# Formatted JSON response
@app.post("/generate_survey/")
async def create_item(prompt: str = Form(...)):
    # Call the global Gemini function
    survey_questions = generate_survey_questions(prompt)
    
    # Parse the JSON string to make it readable
    try:
        # Extract the JSON content from the response
        parsed_questions = json.loads(survey_questions.strip("```json").strip("```"))
    except json.JSONDecodeError:
        return {"error": "Failed to parse survey questions JSON"}

    return {"survey_questions": parsed_questions}