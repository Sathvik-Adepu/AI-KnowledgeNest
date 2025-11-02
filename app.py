import os
import uuid
import re
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
from pymongo import MongoClient
from utils.file_extractors import extract_text_from_file
from utils.perplexity_api import call_perplexity_api_with_context, call_perplexity_api_with_messages
from utils.quiz_feedback import get_quiz_feedback

app = Flask(__name__)
CORS(app,
     supports_credentials=True,
     origins=["http://localhost:5173", "https://ai-knowledgenest.vercel.app"],  # frontend URLs
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"])
app.secret_key = os.getenv("FLASK_SECRET_KEY", "your_secret_key_here")

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client['test']

def get_user_id():
    return 'ai-knowledge-bot'

def store_uploaded_notes(user_id, notes_dict):
    db.notes.update_one({'user_id': user_id}, {'$set': {'notes': notes_dict}}, upsert=True)

def get_uploaded_notes(user_id):
    doc = db.notes.find_one({'user_id': user_id})
    return doc['notes'] if doc and 'notes' in doc else {}

def store_file_summaries(user_id, summaries_dict):
    db.summaries.update_one({'user_id': user_id}, {'$set': {'summaries': summaries_dict}}, upsert=True)

def get_file_summaries(user_id):
    doc = db.summaries.find_one({'user_id': user_id})
    return doc['summaries'] if doc and 'summaries' in doc else {}

def store_conversation(user_id, conversation):
    db.conversations.update_one({'user_id': user_id}, {'$set': {'conversation': conversation}}, upsert=True)

def get_conversation(user_id):
    doc = db.conversations.find_one({'user_id': user_id})
    return doc['conversation'] if doc and 'conversation' in doc else []

def store_quiz(user_id, quiz):
    db.quizzes.update_one({'user_id': user_id}, {'$set': {'quiz': quiz}}, upsert=True)

def get_quiz(user_id):
    doc = db.quizzes.find_one({'user_id': user_id})
    return doc['quiz'] if doc and 'quiz' in doc else []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    user_id = get_user_id()
    files = request.files.getlist('files')
    uploaded_notes = {}
    file_summaries = {}

    for file in files:
        text = extract_text_from_file(file)
        uploaded_notes[file.filename] = text
        if text.strip():
            summary = call_perplexity_api_with_context(text, "Please provide a concise summary of this document.")
        else:
            summary = "No content found."
        file_summaries[file.filename] = summary

    store_uploaded_notes(user_id, uploaded_notes)
    store_file_summaries(user_id, file_summaries)
    store_conversation(user_id, [])  # Reset
    store_quiz(user_id, [])
    return jsonify({"message": "Files uploaded and summarized.", "summaries": file_summaries})

@app.route('/followup', methods=['POST'])
def follow_up():
    user_id = get_user_id()
    data = request.json
    follow_up_query = data.get("query", "").strip()
    if not follow_up_query:
        return jsonify({"response": "Please enter a valid follow-up question."})

    conversation = [qa for qa in get_conversation(user_id)
                    if 'API error' not in qa.get('answer', '')]
    uploaded_notes = get_uploaded_notes(user_id)
    context = "\n".join(uploaded_notes.values())

    # New, helpful system message
    system_msg = (
        "You are a helpful assistant. Use only the uploaded notes below to answer the user's question. "
        "If you find an answer in the notes, quote or summarize it directly. "
        "If nothing relevant is found, reply exactly: 'Not found in uploaded notes/resources.'"
    )

    messages = [{"role": "system", "content": system_msg}]
    messages.append({"role": "user", "content": f"Uploaded notes:\n{context}"})
    messages.append({"role": "assistant", "content": f"Uploaded notes:\n{context}"})
    for qa in conversation:
        messages.append({"role": "user", "content": qa['question']})
        messages.append({"role": "assistant", "content": qa['answer']})
    messages.append({"role": "user", "content": follow_up_query})

    response = call_perplexity_api_with_messages(messages)
    if not response or "API error" in response or not response.strip():
        return jsonify({"response": "Not found in uploaded notes/resources."})

    conversation.append({"question": follow_up_query, "answer": response})
    store_conversation(user_id, conversation)
    return jsonify({"response": response})



# @app.route('/generate_quiz', methods=['POST'])
# def generate_quiz():
#     user_id = get_user_id()
#     data = request.json
#     num_questions = int(data.get("num_questions", 1))
#     uploaded_notes = get_uploaded_notes(user_id)
#     context = "\n".join(uploaded_notes.values()).strip()
#     if not context:
#         return jsonify({
#             "quiz": [],
#             "message": "No notes uploaded for quiz generation."
#         })

#     prompt = (
#         f"Generate {num_questions} multiple choice questions (MCQs) ONLY from the uploaded notes. "
#         f"Each question should have four answer options. If not possible, reply: "
#         f"'Cannot generate {num_questions} questions from uploaded content.'\n\nNotes:\n{context}\n"
#         f"Format:\nQ: <question>\nA. <option 1>\nB. <option 2>\nC. <option 3>\nD. <option 4>\n"
#     )
#     messages = [
#         {"role": "system", "content": "You are a quiz generator assistant. Only use info from uploaded notes."},
#         {"role": "user", "content": prompt}
#     ]
#     response = call_perplexity_api_with_messages(messages)
#     if "cannot generate" in response.lower() or not response.strip():
#         return jsonify({
#             "quiz": [],
#             "message": f"Cannot generate {num_questions} MCQs from uploaded content."
#         })
#     import re
#     mcq_blocks = re.split(r"\nQ: ", "\n" + response)
#     quiz = []
#     for block in mcq_blocks[1:]:
#         lines = block.strip().split("\n")
#         q_text = lines[0].strip()
#         options = []
#         for line in lines[1:]:
#             m = re.match(r"([A-D])\. (.+)", line)
#             if m:
#                 options.append(m.group(2).strip())
#         if q_text and len(options) == 4:
#             quiz.append({'question': q_text, 'options': options})
#         if len(quiz) >= num_questions:
#             break
#     if len(quiz) < num_questions:
#         return jsonify({
#             "quiz": [],
#             "message": f"Cannot generate {num_questions} MCQs from uploaded content."
#         })
#     store_quiz(user_id, quiz)
#     return jsonify({"quiz": quiz, "message": "Quiz generated successfully."})

@app.route('/quiz_feedback', methods=['POST'])
def quiz_feedback():
    data = request.json
    quiz_results = data.get("quiz_results", [])
    if not quiz_results:
        return jsonify({"feedback": "No quiz results submitted."})
    prompt_text = "Provide detailed feedback for this quiz result:\n"
    for entry in quiz_results:
        prompt_text += f"Question: {entry['question']}\n"
        prompt_text += f"Chosen answer: {entry['chosen_answer']}\n"
        prompt_text += f"Correct answer: {entry['correct_answer']}\n\n"
    messages = [
        {"role": "system", "content": "You are a helpful assistant providing quiz feedback."},
        {"role": "user", "content": prompt_text}
    ]
    response = call_perplexity_api_with_messages(messages)
    if not response or not response.strip():
        response = "No feedback generated."
    return jsonify({"feedback": response})

def save_question(question_doc):
    result = db.questions.insert_one(question_doc)
    return result.inserted_id

# Helper to save a quiz and return the inserted document
def save_quiz(quiz_doc):
    result = db.quizzes.insert_one(quiz_doc)
    quiz_doc['_id'] = result.inserted_id
    return quiz_doc

@app.route('/generate_quiz', methods=['POST'])
def generate_quiz():
    user_id = get_user_id()  # your function to get current user
    data = request.json
    num_questions = int(data.get("num_questions", 1))
    uploaded_notes = get_uploaded_notes(user_id)  # your note fetch function
    context = "\n".join(uploaded_notes.values()).strip()
    
    if not context:
        return jsonify({
            "quiz": [],
            "message": "No notes uploaded for quiz generation."
        })
    
    prompt = (
        f"Generate {num_questions} multiple choice questions (MCQs) ONLY from the uploaded notes. "
        f"Each question should have four answer options and indicate the correct option explicitly, for example:\n\n"
        f"Q: <question_text>\nA. <option 1>\nB. <option 2>\nC. <option 3>\nD. <option 4>\nCorrect: <correct_option_letter>\n\n"
        f"If not possible, reply:\n"
        f"'Cannot generate {num_questions} questions from uploaded content.'\n\n"
        f"Notes:\n{context}\n"
    )
    messages = [
        {"role": "system", "content": "You are a quiz generator assistant. Only use info from uploaded notes."},
        {"role": "user", "content": prompt}
    ]
    
    response = call_perplexity_api_with_messages(messages)
    
    if "cannot generate" in response.lower() or not response.strip():
        return jsonify({
            "quiz": [],
            "message": f"Cannot generate {num_questions} MCQs from uploaded content."
        })
    
    # Parse the response into question blocks with options and correct option
    mcq_blocks = re.split(r"\nQ: ", "\n" + response)
    questions_to_save = []
    
    for block in mcq_blocks[1:]:
        lines = block.strip().split("\n")
        q_text = lines[0].strip()
        options = []
        correct_letter = None
        
        # Parse options and correct answer
        for line in lines[1:]:
            m_opt = re.match(r"([A-D])\. (.+)", line)
            m_corr = re.match(r"Correct:\s*([A-D])", line, re.I)
            if m_opt:
                options.append({'letter': m_opt.group(1), 'text': m_opt.group(2).strip()})
            elif m_corr:
                correct_letter = m_corr.group(1)
        
        if q_text and len(options) == 4 and correct_letter:
            # Build options list with isCorrect
            opts = []
            for opt in options:
                opts.append({
                    'text': opt['text'],
                    'isCorrect': (opt['letter'] == correct_letter)
                })
            
            question_doc = {
                'quiz': None,  # will update later
                'questionText': q_text,
                'questionType': 'multiple-choice',
                'options': opts,
                'points': 1,
                'explanation': '',
                'difficulty': 'medium',
                'tags': [],
                'createdBy': user_id,
                'isAIGenerated': True
            }
            questions_to_save.append(question_doc)
        
        if len(questions_to_save) >= num_questions:
            break
    
    if len(questions_to_save) < num_questions:
        return jsonify({
            "quiz": [],
            "message": f"Cannot generate {num_questions} MCQs from uploaded content."
        })
    
    # Save questions and collect IDs
    question_ids = []
    for q in questions_to_save:
        inserted_id = save_question(q)
        question_ids.append(inserted_id)
    
    # Create quiz document referencing question IDs
    quiz_doc = {
        'title': data.get('title', 'Generated Quiz'),
        'description': data.get('description', 'Quiz generated from uploaded notes'),
        'group': "ObjectId('69060c604e7e2bcf84acf0d8')",  # example group ID or dynamic
        'questions': question_ids,
        'difficulty': 'easy',
        'timeLimit': 60,
        'createdBy': user_id,
        'isAIGenerated': True,
        'isScheduled': False,
        'maxAttempts': None,
        'shuffleQuestions': False,
        'shuffleOptions': False,
        'showResults': 'immediately',
        'passingScore': 60,
        'isPublished': True,
        'isActive': True,
        'totalAttempts': 0,
        'averageScore': 0
    }
    
    saved_quiz = save_quiz(quiz_doc)
    # iterate to update each question with quiz ID
    for q_id in question_ids:
        db.questions.update_one({'_id': q_id}, {'$set': {'quiz': saved_quiz['_id']}})
    return jsonify({
        "quiz": {
            "quizId": str(saved_quiz['_id']),
            "title": saved_quiz['title'],
            "description": saved_quiz['description'],
            "questionsCount": len(question_ids)
        },
        "message": "Quiz generated and saved successfully."
    })

if __name__ == '__main__':
    # Bind to PORT provided by the environment (Render sets $PORT)
    # and allow FLASK_DEBUG to toggle debug mode.
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug)
