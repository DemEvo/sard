import os
import json
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from models import db, Project, ApprovedBlock, ChatHistory, ProjectFile
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Ensure the database is created
with app.app_context():
    db.create_all()

# Setup GenAI
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "DUMMY_KEY"))

STATES = [
    'BUSINESS_TASK_ANALYSIS',
    'PROJECT_CONTEXT_MODELING',
    'FUNCTIONAL_REQUIREMENTS_DEVELOPMENT',
    'NFR_FORMALIZATION',
    'SRS_ASSEMBLY_AND_AUDIT'
]

def load_prompt(state_id):
    prompt_path = os.path.join('Prompts', f"{state_id}.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    return f"System prompt for {state_id}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/projects', methods=['GET', 'POST'])
def handle_projects():
    if request.method == 'POST':
        data = request.json
        title = data.get('title', 'New Project')
        project = Project(title=title)
        db.session.add(project)
        db.session.commit()
        return jsonify(project.to_dict()), 201
    else:
        projects = Project.query.all()
        return jsonify([p.to_dict() for p in projects])

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = Project.query.get_or_404(project_id)
    blocks = ApprovedBlock.query.filter_by(project_id=project_id).all()
    chats = ChatHistory.query.filter_by(project_id=project_id).all()
    files = ProjectFile.query.filter_by(project_id=project_id).all()

    return jsonify({
        'project': project.to_dict(),
        'blocks': [b.to_dict() for b in blocks],
        'chats': [c.to_dict() for c in chats],
        'files': [f.to_dict() for f in files]
    })

@app.route('/api/projects/<int:project_id>/chat', methods=['POST'])
def chat(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.json
    message = data.get('message', '')
    
    # Save user message
    user_chat = ChatHistory(project_id=project.id, state_id=project.current_state, role='user', content=message)
    db.session.add(user_chat)
    db.session.commit()

    # FR-0 / FR-2 Trigger
    # In a fully implemented logic, we call the Gemini API here.
    # We simulate the API call for MVP purposes.
    
    # We would use gemini-3.1-pro-preview
    # model = genai.GenerativeModel('gemini-3.1-pro-preview')
    # Use Structured outputs (JSON)
    # prompt = build_prompt(project)
    # response = model.generate_content(prompt)
    
    # Mocking cognitive simulation response
    response_json = {
        "agents_dialogue": [
            {"agent": "Architect", "message": f"User says: {message}. We need more context on {project.current_state}."},
            {"agent": "DevOps", "message": "I agree. Let's ask for the scaling requirements."}
        ],
        "facilitator_summary": f"Please clarify the requirements for {project.current_state}."
    }
    
    model_chat = ChatHistory(project_id=project.id, state_id=project.current_state, role='model', content=json.dumps(response_json))
    db.session.add(model_chat)
    db.session.commit()

    return jsonify(model_chat.to_dict())

@app.route('/api/projects/<int:project_id>/block', methods=['POST'])
def save_block(project_id):
    # FR-3: Block Fixation
    project = Project.query.get_or_404(project_id)
    data = request.json
    content = data.get('content', '')
    state_id = data.get('state_id', project.current_state)
    
    block = ApprovedBlock.query.filter_by(project_id=project.id, state_id=state_id).first()
    if block:
        block.content = content
        block.status = 'approved'
    else:
        block = ApprovedBlock(project_id=project.id, state_id=state_id, content=content, status='approved')
        db.session.add(block)
    
    # FR-4 Logic: Soft rollback invalidation if saving previous step
    if STATES.index(state_id) < STATES.index(project.current_state):
        idx = STATES.index(state_id)
        for subsequent_state in STATES[idx+1: STATES.index(project.current_state)+1]:
            b = ApprovedBlock.query.filter_by(project_id=project.id, state_id=subsequent_state).first()
            if b:
                b.status = 'outdated'
        project.current_state = state_id # Soft rollback
    elif state_id == project.current_state:
        # Advance current state if possible
        idx = STATES.index(project.current_state)
        if idx < len(STATES) - 1:
            project.current_state = STATES[idx + 1]
    
    # Cleanup chat for current state
    ChatHistory.query.filter_by(project_id=project.id, state_id=state_id).delete()
    
    db.session.commit()
    return jsonify({'status': 'success', 'project': project.to_dict()})

@app.route('/api/projects/<int:project_id>/upload', methods=['POST'])
def upload_file(project_id):
    # FR-5: AI-Distillation of Artifacts
    project = Project.query.get_or_404(project_id)
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # In a real impl, decode PDF/TXT, send to gemini-2.5-flash
    raw_text = file.read().decode('utf-8', errors='ignore')
    
    # Mock distillation
    distilled_context = json.dumps({"facts": ["Extracted facts from file"]})
    
    new_file = ProjectFile(project_id=project.id, filename=file.filename, raw_text=raw_text, distilled_context=distilled_context)
    db.session.add(new_file)
    db.session.commit()
    
    return jsonify(new_file.to_dict())

if __name__ == '__main__':
    app.run(debug=True, port=5000)
