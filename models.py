from datetime import datetime, date
from extensions import db

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    studying_count = db.Column(db.Integer, default=0, nullable=False) 
    learned_count = db.Column(db.Integer, default=0, nullable=False)

class Category(db.Model):
    __tablename__ = "categories" # Добавлено для консистентности
    id = db.Column(db.Integer, primary_key=True)
    # 💥 ИСПРАВЛЕНИЕ 1: Ссылка на 'users.id'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) 
    name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.String(5), nullable=False, default='USER') 
    
    # 💥 Отношение определено ОДИН раз. Оно создаст Category.flashcards И Flashcard.category
    flashcards = db.relationship('Flashcard', backref='category', lazy=True)


class Flashcard(db.Model):
    __tablename__ = "flashcards"
    id = db.Column(db.Integer, primary_key=True)
    front = db.Column(db.String(255), nullable=False)
    back = db.Column(db.String(255), nullable=False)
    # Ссылки на категории и пользователей
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    
    # 💥 ИСПРАВЛЕНИЕ 2: Удалено конфликтное определение db.relationship
    # Свойство 'category' теперь создается автоматически через backref в Category.
    # Если бы вы хотели определить его здесь, вы бы использовали back_populates.


class QuizResult(db.Model):
    __tablename__ = "quiz_results"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    score = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class RepetitionSchedule(db.Model):
    __tablename__ = "repetition_schedule"
    id = db.Column(db.Integer, primary_key=True)
    flashcard_id = db.Column(db.Integer, db.ForeignKey("flashcards.id"), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    next_review_date = db.Column(db.Date, nullable=False)
    repetitions = db.Column(db.Integer, default=0)
    efactor = db.Column(db.Float, default=2.5)
    interval = db.Column(db.Integer, default=1)
    flashcard = db.relationship('Flashcard', backref='schedules', lazy=True)
    flashcard = db.relationship("Flashcard", backref="schedule")