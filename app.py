import os
import json
from flask import Flask, request, jsonify, render_template
from google import genai
from google.genai import types
from models import db, Project, ApprovedBlock, ChatHistory, ProjectFile
from dotenv import load_dotenv
import logging
from logging import StreamHandler, Formatter
import glob  # Добавь в импорты

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sard.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

sard_logger = logging.getLogger('sard_logger')
sard_logger.setLevel(logging.DEBUG if os.getenv('FLASK_ENV', 'development') == 'development' else logging.INFO)
handler = StreamHandler()
handler.setFormatter(Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s'))
sard_logger.addHandler(handler)

# Ensure the database is created
with app.app_context():
    db.create_all()

# Setup GenAI
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

STATES = [
    'BUSINESS_TASK_ANALYSIS',
    'PROJECT_CONTEXT_MODELING',
    'FUNCTIONAL_REQUIREMENTS_DEVELOPMENT',
    'NFR_FORMALIZATION',
    'SRS_ASSEMBLY_AND_AUDIT'
]


def load_prompt(state_id):
    # Используем glob для поиска файла с любым суффиксом
    files = glob.glob(os.path.join('Prompts', f"{state_id}*.md"))
    if files:
        with open(files[0], 'r', encoding='utf-8') as f:
            return f.read()
    return f"Return response in JSON format for {state_id}"


def get_project_context(project_id):
    # Собираем все утвержденные блоки ТЗ
    blocks = ApprovedBlock.query.filter_by(project_id=project_id, status='approved').all()
    context_parts = []
    for b in blocks:
        context_parts.append(f"### Раздел: {b.state_id}\n{b.content}")

    # Можно также добавить дистиллированные данные из файлов
    files = ProjectFile.query.filter_by(project_id=project_id).all()
    for f in files:
        context_parts.append(f"### Данные из файла {f.filename}:\n{f.distilled_context}")

    return "\n\n".join(context_parts)

def get_compressed_history(project_id, state_id, current_msg_id):
    # Достаем все сообщения текущего этапа ДО текущего запроса
    past_chats = ChatHistory.query.filter(
        ChatHistory.project_id == project_id,
        ChatHistory.state_id == state_id,
        ChatHistory.id < current_msg_id
    ).order_by(ChatHistory.id).all()

    if not past_chats:
        return "Диалог только начат."

    compressed_log = []
    for c in past_chats:
        if c.role == 'user':
            compressed_log.append(f"ПОЛЬЗОВАТЕЛЬ: {c.content}")
        elif c.role == 'model':
            try:
                # Пытаемся вытащить только сухую выжимку фасилитатора
                parsed = json.loads(c.content)
                summary = parsed.get("facilitator_summary", "")
                if summary:
                    compressed_log.append(f"ИИ-ФАСИЛИТАТОР: {summary}")
            except:
                pass # Игнорируем невалидные ответы

    return "\n\n".join(compressed_log)

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
        sard_logger.info(f"Initialized new project (state_id={project.current_state})")
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

    # Сохраняем сообщение пользователя в БД
    user_chat = ChatHistory(project_id=project.id, state_id=project.current_state, role='user', content=message)
    db.session.add(user_chat)
    db.session.commit()

    # --- СЦЕНАРИЙ 1: ДИСПЕТЧЕР (Gemini 2.5 Flash) ---
    chat_history_length = ChatHistory.query.filter_by(project_id=project.id).count()
    if project.current_state == 'BUSINESS_TASK_ANALYSIS' and chat_history_length == 1:
        sard_logger.info("Running Dispatcher on Gemini 2.5 Flash...")
        dispatcher_prompt = load_prompt("SYS_DISPATCHER_m1")

        model_id = 'gemini-2.5-flash'
        response = client.models.generate_content(
            model=model_id,
            contents=f"{dispatcher_prompt}\n\nUSER BRIEF:\n{message}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        # Парсим результат и создаем черновики (логика из твоего исходника)
        try:
            parsed_res = json.loads(response.text)
            extracted = parsed_res.get('extracted_data', {})
            mapping = {
                'PROJECT_CONTEXT_MODELING': extracted.get('bucket_2_roles', []),
                'FUNCTIONAL_REQUIREMENTS_DEVELOPMENT': extracted.get('bucket_3_functions', []),
                'NFR_FORMALIZATION': extracted.get('bucket_4_nfr', [])
            }
            for state_id, items in mapping.items():
                if items:
                    content = "\n".join(f"- {item}" for item in items)
                    db.session.add(
                        ApprovedBlock(project_id=project.id, state_id=state_id, content=content, status='draft'))

            # Формируем ответ от ИИ
            reply_content = json.dumps({
                "agents_dialogue": [
                    {"agent": "System Dispatcher", "message": "Бриф проанализирован. Черновики созданы."}],
                "facilitator_summary": "Я разложил ваш запрос по полочкам. Давайте начнем с уточнения бизнес-целей."
            }, ensure_ascii=False)

            model_chat = ChatHistory(project_id=project.id, state_id=project.current_state, role='model',
                                     content=reply_content)
            db.session.add(model_chat)
            db.session.commit()
            return jsonify(model_chat.to_dict())
        except Exception as e:
            sard_logger.error(f"Dispatcher failed: {e}")

    # --- СЦЕНАРИЙ 2: ГЛУБОКАЯ АНАЛИТИКА (Gemini 3.1 Pro Preview) ---
    sard_logger.info(f"Running Analysis on Gemini 3.1 Pro for state: {project.current_state}")

    try:
        # 1. Инструкции этапа
        system_prompt = load_prompt(project.current_state)
        # 2. Долгосрочная память (фундамент)
        past_context = get_project_context(project.id)
        # 3. Краткосрочная память (история чата)
        compressed_history = get_compressed_history(project.id, project.current_state, user_chat.id)

        full_query = (
            f"ИНСТРУКЦИЯ СИСТЕМЫ:\n{system_prompt}\n\n"
            f"УТВЕРЖДЕННЫЙ КОНТЕКСТ ПРОЕКТА (ФУНДАМЕНТ):\n{past_context}\n\n"
            f"ИСТОРИЯ ТЕКУЩЕГО ОБСУЖДЕНИЯ:\n{compressed_history}\n\n"
            f"ВАЖНО: Отвечай строго в формате JSON, без обертки ```json."
        )

        model_id = 'gemini-3.1-pro-preview'
        # Используем словарь для конфига, без temperature
        response = client.models.generate_content(
            model=model_id,
            contents=full_query
        )

        # Сохраняем реальный ответ нейронки
        model_chat = ChatHistory(
            project_id=project.id,
            state_id=project.current_state,
            role='model',
            content=response.text
        )

        db.session.add(model_chat)
        db.session.commit()
        return jsonify(model_chat.to_dict())

    except Exception as e:
        sard_logger.error(f"Critical API Error: {e}")
        return jsonify({"error": "Model 3.1 Pro unavailable or failed", "details": str(e)}), 500


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
        for subsequent_state in STATES[idx + 1: STATES.index(project.current_state) + 1]:
            b = ApprovedBlock.query.filter_by(project_id=project.id, state_id=subsequent_state).first()
            if b:
                b.status = 'outdated'
        project.current_state = state_id  # Soft rollback
        sard_logger.info(f"Project state changed (Soft Rollback): state_id={project.current_state}")
    elif state_id == project.current_state:
        # Advance current state if possible
        idx = STATES.index(project.current_state)
        if idx < len(STATES) - 1:
            project.current_state = STATES[idx + 1]
            sard_logger.info(f"Project state changed (Advanced): state_id={project.current_state}")

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

    raw_text = file.read().decode('utf-8', errors='ignore')

    sard_logger.info(f"Starting AI-Distillation for {file.filename} via gemini-2.5-flash")

    try:
        distiller_prompt = load_prompt("FILE_PREPROCESSOR_m1")  # Убедись, что имя файла промпта верное

        # Вызываем 2.5 Flash для быстрого извлечения фактов
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{distiller_prompt}\n\nDOCUMENT TEXT:\n{raw_text}"
        )
        distilled_context = response.text
        sard_logger.info("Distillation successful")
    except Exception as e:
        sard_logger.error(f"Distillation failed: {e}")
        distilled_context = json.dumps({"error": "Failed to process file", "details": str(e)})

    new_file = ProjectFile(project_id=project.id, filename=file.filename, raw_text=raw_text,
                           distilled_context=distilled_context)
    db.session.add(new_file)
    db.session.commit()

    return jsonify(new_file.to_dict())


if __name__ == '__main__':
    app.run(debug=True, port=5000)
