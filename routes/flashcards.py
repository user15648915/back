from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import date
from extensions import db
# ❗ Важные изменения: импортируем RepetitionSchedule и date
from models import Flashcard, Category, RepetitionSchedule

flashcards_bp = Blueprint("flashcards", __name__)

# 📌 Получить все карточки пользователя
@flashcards_bp.route("", methods=["GET"]) # ИСПРАВЛЕНИЕ 1: удален завершающий слэш
@jwt_required()
def get_flashcards():
    user_id = int(get_jwt_identity())
    # Если вы используете relationship в SQLAlchemy, используйте .options(joinedload(Flashcard.category))
    # Для простоты пока используем .all()
    cards = Flashcard.query.filter_by(user_id=user_id).all()
    
    return jsonify([
        {
            "id": card.id,
            "front": card.front,
            "back": card.back,
            # УЛУЧШЕНИЕ API: отправляем имя категории, если оно есть
            "category_name": card.category.name if card.category else "Без категории",
            "category_id": card.category_id
        }
        for card in cards
    ]), 200


# 📌 Создать карточку
@flashcards_bp.route("", methods=["POST"]) # ИСПРАВЛЕНИЕ 1: удален завершающий слэш
@jwt_required()
def create_flashcard():
    data = request.json
    front = data.get("front")
    back = data.get("back")
    category_name = data.get("category") # Фронтенд шлет 'category'

    if not front or not back:
        return jsonify({"error": "front и back обязательны"}), 400

    user_id = int(get_jwt_identity())
    final_category_id = None

    # ЛОГИКА ОБРАБОТКИ КАТЕГОРИИ
    if category_name:
        category = Category.query.filter_by(
            name=category_name, 
            user_id=user_id
        ).first()

        if not category:
            new_category = Category(name=category_name, user_id=user_id)
            db.session.add(new_category)
            db.session.commit()
            final_category_id = new_category.id
        else:
            final_category_id = category.id

    # СОЗДАНИЕ КАРТОЧКИ
    new_card = Flashcard(
        front=front,
        back=back,
        category_id=final_category_id,
        user_id=user_id
    )
    db.session.add(new_card)
    db.session.commit() # ❗ Коммит, чтобы получить new_card.id

    # --- ИСПРАВЛЕНИЕ 2: Создаем расписание повторения для новой карточки ---
    initial_schedule = RepetitionSchedule(
        flashcard_id=new_card.id,
        user_id=user_id,
        next_review_date=date.today(), # Ставим на повторение СЕГОДНЯ
        repetitions=0,
        efactor=2.5,
        interval=1
    )
    db.session.add(initial_schedule)
    db.session.commit()
    # ---------------------------------------------------------------------

    return jsonify({"message": "Карточка создана", "id": new_card.id}), 201


# 📌 Удалить карточку
@flashcards_bp.route("/<int:card_id>", methods=["DELETE"])
@jwt_required()
def delete_flashcard(card_id):
    user_id = int(get_jwt_identity())
    
    # Ищем карточку
    card = Flashcard.query.filter_by(id=card_id, user_id=user_id).first()
    if not card:
        return jsonify({"error": "Карточка не найдена"}), 404

    # Ищем расписание и удаляем его перед удалением карточки
    schedule = RepetitionSchedule.query.filter_by(flashcard_id=card_id).first()
    if schedule:
        db.session.delete(schedule)

    db.session.delete(card)
    db.session.commit()

    return jsonify({"message": "Карточка удалена"}), 200
