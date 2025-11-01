import os
import requests
from dotenv import load_dotenv

load_dotenv()
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

def format_quiz_results(quiz_results):
    prompt = "Provide detailed feedback for this quiz result:\n"
    for entry in quiz_results:
        prompt += f"Question: {entry['question']}\n"
        prompt += f"Chosen answer: {entry['chosen_answer']}\n"
        prompt += f"Correct answer: {entry['correct_answer']}\n\n"
    return prompt

def get_quiz_feedback(quiz_results):
    prompt_text = format_quiz_results(quiz_results)
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant providing quiz feedback."},
            {"role": "user", "content": prompt_text}
        ]
    }
    response = requests.post(PERPLEXITY_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"API error: {response.status_code} - {response.text}"

