import os
from datetime import timedelta
from dotenv import load_dotenv

# загружаем .env файл
load_dotenv("b.env")

class Config:
    # 🔑 Flask secret key (для сессий, CSRF и пр.)
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")

    # 🔌 Подключение к базе данных PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or 'postgresql://user:password@localhost/flashcards_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 🔐 Настройки JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwtsecretkey")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)  # срок жизни токена (30 дней)

    # 🔧 Дополнительно (можно включить при необходимости)
    # PROPAGATE_EXCEPTIONS = True

