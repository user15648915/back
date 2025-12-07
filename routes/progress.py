from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import date, timedelta
from extensions import db
# ❗ ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ: Импортируем QuizResult для статистики и стрейков
from models import Flashcard, RepetitionSchedule, QuizResult 
from sqlalchemy import func

# создаём blueprint
progress_bp = Blueprint("progress", __name__)

# --- 1. Статистика по прогрессу (/progress/stats) ---
@progress_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_progress_stats():
    user_id = int(get_jwt_identity())
    today = date.today()

    # общее количество карточек пользователя
    total_cards = Flashcard.query.filter_by(user_id=user_id).count()

    # 2. Количество "Изучено" (Mastered): efactor > 2.6 и >= 1 повторение
    mastered_cards = RepetitionSchedule.query.filter(
        RepetitionSchedule.user_id == user_id,
        RepetitionSchedule.efactor > 2.6,
        RepetitionSchedule.repetitions >= 1
    ).count()

    # 3. Количество "Изучаю" (Studying): повторена >= 1 раз, НО efactor <= 2.6
    studying_cards = RepetitionSchedule.query.filter(
        RepetitionSchedule.user_id == user_id,
        RepetitionSchedule.repetitions >= 1, 
        RepetitionSchedule.efactor <= 2.6 # Еще не достигла "mastered"
    ).count()

    # ❗ ИСПРАВЛЕНИЕ: Расчет Серии (Streak)
    streak = 0
    
    # 1. Считаем непрерывную серию ЗАВЕРШЕННЫХ дней (начиная со вчерашнего дня)
    # Начинаем с i=1 (Вчера), i=2 (Позавчера) и т.д.
    for i in range(1, 31): 
        check_day = today - timedelta(days=i) 
        
        # Проверяем, была ли хоть одна запись в QuizResult за этот день
        review_exists = QuizResult.query.filter(
            QuizResult.user_id == user_id,
            db.func.date(QuizResult.date) == check_day
        ).first()

        if review_exists:
            streak += 1 # Если активность есть, прибавляем к серии
        else:
            # Если нет активности, цепочка прерывается
            break
            
    # 2. Проверяем, была ли активность СЕГОДНЯ
    today_active = QuizResult.query.filter(
        QuizResult.user_id == user_id,
        db.func.date(QuizResult.date) == today
    ).first()
    
    # Если сегодня была активность, добавляем +1 к серии
    if today_active:
        streak += 1

    # уровень владения (процент выученных карт)
    proficiency = 0
    if total_cards > 0:
        proficiency = int((studying_cards / total_cards) * 100)

    # ❗ ФИНАЛЬНЫЙ JSON-ОТВЕТ
    stats = {
        "total_cards": total_cards,
        "studying_words": studying_cards, # <-- Идет в счетчик "Изучаю"
        "mastered_words": mastered_cards, # <-- Идет в счетчик "Изучено"
        "streak": streak,
        "level": f"{proficiency}%"
    }

    return jsonify(stats), 200

# --- 2. Новый роут для данных графика (/progress/chart_data) ---
@progress_bp.route("/chart_data", methods=["GET"])
@jwt_required()
def get_chart_data():
    user_id = int(get_jwt_identity())
    
    # Данные за последние 30 дней для хорошей визуализации
    thirty_days_ago = date.today() - timedelta(days=30)
    
    # Получаем дневные результаты (количество очков в день)
    daily_results = db.session.query(
        func.date(QuizResult.date).label('day'),
        func.sum(QuizResult.score).label('total_score')
    ).filter(
        QuizResult.user_id == user_id,
        QuizResult.date >= thirty_days_ago
    ).group_by('day').order_by('day').all()
    
    # Форматирование для Chart.js (кумулятивный прогресс)
    date_series = [thirty_days_ago + timedelta(days=i) for i in range(31)]
    results_map = {str(r.day): r.total_score for r in daily_results}
    
    labels = [d.strftime("%d.%m") for d in date_series] # Формат даты: ДД.ММ
    data_points = []
    
    # 1. Рассчитываем начальный кумулятивный счет (до 30 дней)
    initial_learned_count = db.session.query(func.sum(QuizResult.score)).filter(
        QuizResult.user_id == user_id,
        QuizResult.date < thirty_days_ago
    ).scalar() or 0
    
    cumulative_score = initial_learned_count
    
    # 2. Добавляем ежедневный прогресс
    for d in date_series:
        day_str = str(d)
        daily_score = results_map.get(day_str, 0)
        cumulative_score += daily_score
        data_points.append(cumulative_score) # Добавляем накопленный счет
        
    return jsonify({
        "labels": labels,
        "data": data_points
    }), 200

# --- 2. История активности (для графиков) ---
@progress_bp.route("/history", methods=["GET"])
@jwt_required()
def get_progress_history():
    user_id = int(get_jwt_identity())
    today = date.today()
    history = []

    # последние 14 дней
    for i in range(14):
        check_day = today - timedelta(days=i)

        # Мой исправленный код (для /history)
# -------------------------------------------------------------------
# ❗ ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ 4: Получаем реальный СЧЕТ (score) из QuizResult
        result = QuizResult.query.filter( # <-- ИСПОЛЬЗУЕТ QuizResult
            QuizResult.user_id == user_id,
            db.func.date(QuizResult.date) == check_day
        ).first()

# Значение для графика: 0, если активности не было, или score
        learned_count = result.score if result else 0 
# ...
        
        # Добавляем данные
        history.append({
            "date": str(check_day),
            "learned": learned_count # progress.html ждет поле 'learned'
        })
    
    # Инвертируем список, чтобы график шёл от старых дат к новым
    return jsonify(history[::-1]), 200