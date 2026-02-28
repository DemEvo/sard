from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    current_state = db.Column(db.String(100), nullable=False, default='BUSINESS_TASK_ANALYSIS')
    
    blocks = db.relationship('ApprovedBlock', backref='project', lazy=True)
    chats = db.relationship('ChatHistory', backref='project', lazy=True)
    files = db.relationship('ProjectFile', backref='project', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'current_state': self.current_state
        }

class ApprovedBlock(db.Model):
    __tablename__ = 'approved_blocks'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    state_id = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='draft') # draft, approved, outdated

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'state_id': self.state_id,
            'content': self.content,
            'status': self.status
        }

class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    state_id = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'user', 'model'
    content = db.Column(db.Text, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content
        }

class ProjectFile(db.Model):
    __tablename__ = 'project_files'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    raw_text = db.Column(db.Text, nullable=False)
    distilled_context = db.Column(db.Text, nullable=False) # JSON as string

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'distilled_context': self.distilled_context
        }
