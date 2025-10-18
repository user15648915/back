from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import date, timedelta
from extensions import db
from models import Flashcard, RepetitionSchedule

# создаём blueprint
progress_bp = Blueprint("progress", __name__)

# --- 1. Статистика по прогрессу ---
@progress_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_progress_stats():
    user_id = int(get_jwt_identity())

    # общее количество карточек пользователя
    total_cards = Flashcard.query.filter_by(user_id=user_id).count()

    # количество "выученных" карточек (например, >3 повторений и eFactor > 2.6)
    learned_cards = RepetitionSchedule.query.filter(
        RepetitionSchedule.user_id == user_id,
        RepetitionSchedule.efactor > 2.6,
        RepetitionSchedule.repetitions >= 3
    ).count()

    # серия обучения (сколько подряд дней пользователь занимался)
    today = date.today()
    streak = 0
    for i in range(30):  # проверим последние 30 дней
        check_day = today - timedelta(days=i)
        activity = RepetitionSchedule.query.filter(
            RepetitionSchedule.user_id == user_id,
            RepetitionSchedule.next_review_date == check_day
        ).first()
        if activity:
            streak += 1
        else:
            break  # если день пропущен → серия заканчивается

    # уровень владения (процент выученных карт)
    proficiency = 0
    if total_cards > 0:
        proficiency = round((learned_cards / total_cards) * 100, 2)

    stats = {
        "total_cards": total_cards,
        "learned_cards": learned_cards,
        "learning_streak": streak,
        "proficiency": f"{proficiency}%"
    }

    return jsonify(stats), 200


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

        # сколько карточек в этот день были "назначены на повторение"
        reviews = RepetitionSchedule.query.filter(
            RepetitionSchedule.user_id == user_id,
            RepetitionSchedule.next_review_date == check_day
        ).count()

        history.append({
            "date": str(check_day),
            "reviews": reviews
        })

    # разворачиваем (от старых к новым)
    history.reverse()

    return jsonify(history), 200
