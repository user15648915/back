from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import date
from extensions import db
from models import RepetitionSchedule
from utils.sm2 import sm2_update

# создаём blueprint
repetition_bp = Blueprint("repetition", __name__)

# получить карточки на сегодня
@repetition_bp.route("/today", methods=["GET"])
@jwt_required()
def get_today_cards():
    user_id = int(get_jwt_identity())
    schedules = RepetitionSchedule.query.filter(
        RepetitionSchedule.user_id == user_id,
        RepetitionSchedule.next_review_date <= date.today()
    ).all()

    return jsonify([
        {
            "id": s.flashcard.id,
            "front": s.flashcard.front,
            "back": s.flashcard.back,
            "next_review_date": str(s.next_review_date)
        }
        for s in schedules
    ]), 200


# обновить результат по карточке
@repetition_bp.route("/result", methods=["POST"])
@jwt_required()
def update_result():
    data = request.json
    if not data or "flashcard_id" not in data or "quality" not in data:
        return jsonify({"error": "flashcard_id и quality обязательны"}), 400

    user_id = int(get_jwt_identity())
    flashcard_id = data["flashcard_id"]
    quality = int(data["quality"])

    schedule = RepetitionSchedule.query.filter_by(
        user_id=user_id, flashcard_id=flashcard_id
    ).first()

    if not schedule:
        # если карточки ещё нет в расписании → создаём её с начальным состоянием
        schedule = RepetitionSchedule(
            flashcard_id=flashcard_id,
            user_id=user_id,
            next_review_date=date.today(),
            repetitions=0,
            efactor=2.5,
            interval=1
        )
        db.session.add(schedule)
        db.session.commit()

    # применяем SM2
    reps, ef, interval, next_date = sm2_update(
        schedule.repetitions,
        schedule.efactor,
        schedule.interval,
        quality
    )

    schedule.repetitions = reps
    schedule.efactor = ef
    schedule.interval = interval
    schedule.next_review_date = next_date

    db.session.commit()

    return jsonify({
        "message": "updated",
        "flashcard_id": flashcard_id,
        "next_review_date": str(schedule.next_review_date),
        "repetitions": schedule.repetitions,
        "efactor": schedule.efactor,
        "interval": schedule.interval
    }), 200
