from datetime import datetime
from app import db
from flask_login import UserMixin
from sqlalchemy import func


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='contestant')  # admin, judge, contestant, visitor
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    submissions = db.relationship('Submission', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_judge(self):
        return self.role in ['admin', 'judge']
    
    def can_submit(self):
        return self.role in ['admin', 'judge', 'contestant']


class Contest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    problems = db.relationship('Problem', backref='contest', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Contest {self.name}>'
    
    def is_running(self):
        now = datetime.utcnow()
        return self.start_time <= now <= self.end_time
    
    def has_started(self):
        return datetime.utcnow() >= self.start_time
    
    def has_ended(self):
        return datetime.utcnow() > self.end_time


class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), nullable=False)  # Short identifier like A, B, C
    statement = db.Column(db.Text, nullable=False)
    input_format = db.Column(db.Text)
    output_format = db.Column(db.Text)
    constraints = db.Column(db.Text)
    sample_input = db.Column(db.Text)
    sample_output = db.Column(db.Text)
    time_limit = db.Column(db.Integer, default=1000)  # milliseconds
    memory_limit = db.Column(db.Integer, default=256)  # MB
    difficulty = db.Column(db.String(20), default='easy')
    points = db.Column(db.Integer, default=100)
    contest_id = db.Column(db.Integer, db.ForeignKey('contest.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    test_cases = db.relationship('TestCase', backref='problem', lazy=True, cascade='all, delete-orphan')
    submissions = db.relationship('Submission', backref='problem', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Problem {self.code}: {self.title}>'


class TestCase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'), nullable=False)
    input_data = db.Column(db.Text, nullable=False)
    output_data = db.Column(db.Text, nullable=False)
    is_sample = db.Column(db.Boolean, default=False)
    points = db.Column(db.Integer, default=10)
    
    def __repr__(self):
        return f'<TestCase {self.id} for Problem {self.problem_id}>'


class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    problem_id = db.Column(db.Integer, db.ForeignKey('problem.id'), nullable=False)
    language = db.Column(db.String(20), nullable=False)
    code = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, judging, accepted, wrong_answer, time_limit, memory_limit, runtime_error, compile_error
    score = db.Column(db.Integer, default=0)
    execution_time = db.Column(db.Integer)  # milliseconds
    memory_used = db.Column(db.Integer)  # KB
    judge_message = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    judged_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Submission {self.id} by {self.user.username} for {self.problem.code}>'
    
    def get_status_class(self):
        status_classes = {
            'pending': 'warning',
            'judging': 'info',
            'accepted': 'success',
            'wrong_answer': 'danger',
            'time_limit': 'warning',
            'memory_limit': 'warning',
            'runtime_error': 'danger',
            'compile_error': 'danger'
        }
        return status_classes.get(self.status, 'secondary')


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_important = db.Column(db.Boolean, default=False)
    
    # Relationships
    author = db.relationship('User', backref='announcements')
    
    def __repr__(self):
        return f'<Announcement {self.title}>'
