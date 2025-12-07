from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import date
from extensions import db
from models import Flashcard, Category, RepetitionSchedule

flashcards_bp = Blueprint("flashcards", __name__)

# ===================================================
# 📌 МАРШРУТЫ КАРТОЧЕК
# ===================================================

# 1. Получить все карточки (ИСПРАВЛЕННЫЙ КОД)
@flashcards_bp.route("", methods=["GET"])
@jwt_required()
def get_flashcards():
    user_id = int(get_jwt_identity())
    
    # Запрашиваем все карточки пользователя, объединяя их с Category
    # Используем db.session.query и outerjoin, чтобы получить название категории 
    # в один запрос и избежать ошибки N+1.
    flashcards_with_categories = db.session.query(Flashcard, Category).outerjoin(
        Category, Flashcard.category_id == Category.id
    ).filter(
        Flashcard.user_id == user_id
    ).all()

    result = []
    for card, category in flashcards_with_categories:
        result.append({
            "id": card.id,
            "front": card.front,
            "back": card.back,
            # category.name будет именем, если категория есть, иначе "Без категории"
            "category_name": category.name if category else "Без категории", 
            "category_id": card.category_id
        })

    return jsonify(result), 200

# routes/flashcards.py

# 2. Создать карточку (ФИНАЛЬНАЯ ИСПРАВЛЕННАЯ ВЕРСИЯ)
@flashcards_bp.route("", methods=["POST"])
@jwt_required()
def create_flashcard():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) 
    
    if data is None:
        return jsonify({"error": "Пустой JSON"}), 400

    front = data.get('front', "").strip()
    back = data.get('back', "").strip()
    category_name = data.get('category', "").strip()

    if not front or not back:
        return jsonify({"error": "Заполните обе стороны"}), 400

    final_category_id = None

    if category_name:
        category = Category.query.filter_by(user_id=user_id, name=category_name).first()

        if not category:
            category = Category(
                user_id=user_id,
                name=category_name,
                level='USER' 
            )
            db.session.add(category)
            db.session.flush() # Получаем ID новой категории
        final_category_id = category.id
    
    # 1. Создание карточки
    new_card = Flashcard(
        front=front,
        back=back,
        category_id=final_category_id,
        user_id=user_id
    )
    db.session.add(new_card)
    
    # 💥 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: db.session.flush()
    # Получает new_card.id для RepetitionSchedule.
    db.session.flush() 
    print(f"--- DEBUG: ID созданной карточки: {new_card.id} ---")
    print(f"--- DEBUG: Next review date: {date.today()} ---")
    # 2. Создание расписания (с ID только что созданной карточки)
    initial_schedule = RepetitionSchedule(
        flashcard_id=new_card.id,
        user_id=user_id,
        next_review_date=date.today(), 
        repetitions=0,
        efactor=2.5,
        interval=1
    )
    db.session.add(initial_schedule)
    
    # 3. Единый commit() для сохранения карточки и расписания
    db.session.commit()

    return jsonify({"message": "Карточка создана", "id": new_card.id}), 201

# 3. Удалить карточку
@flashcards_bp.route("/<int:card_id>", methods=["DELETE"])
@jwt_required()
def delete_flashcard(card_id):
    user_id = int(get_jwt_identity())
    card = Flashcard.query.filter_by(id=card_id, user_id=user_id).first()
    if not card: return jsonify({"error": "Не найдено"}), 404

    schedule = RepetitionSchedule.query.filter_by(flashcard_id=card_id).first()
    if schedule: db.session.delete(schedule)

    db.session.delete(card)
    db.session.commit()
    return jsonify({"message": "Удалено"}), 200


# ===================================================
# 📌 МАРШРУТЫ КАТЕГОРИЙ
# ===================================================

# 4. Создать категорию вручную
@flashcards_bp.route("/category", methods=["POST"])
@jwt_required()
def add_category():
    user_id = int(get_jwt_identity())
    data = request.json
    name = data.get("name")
    level = data.get("level", "USER") 
    
    if not name: return jsonify({"error": "Имя обязательно"}), 400

    if Category.query.filter_by(user_id=user_id, name=name).first():
        return jsonify({"error": "Уже существует"}), 400

    new_category = Category(user_id=user_id, name=name, level=level) 
    db.session.add(new_category)
    db.session.commit()
    return jsonify({"message": "Создано"}), 201


# 💥 5. ПОЛУЧИТЬ КАТЕГОРИИ (ИСПРАВЛЕНО: ДОБАВЛЕН CARD_COUNT) 💥
@flashcards_bp.route("/categories", methods=["GET"])
@jwt_required()
def get_categories():
    user_id = int(get_jwt_identity())
    categories = Category.query.filter_by(user_id=user_id).order_by(Category.name).all()

    return jsonify([
        {
            "id": c.id, 
            "name": c.name,
            "level": c.level,
            # 👇 ВОТ ЭТОЙ СТРОКИ НЕ ХВАТАЛО 👇
            "card_count": Flashcard.query.filter_by(category_id=c.id).count()
        } 
        for c in categories
    ]), 200


# 6. Получить публичные
@flashcards_bp.route("/public_categories", methods=["GET"])
@jwt_required()
def get_public_categories():
    ADMIN_USER_ID = 0 
    categories = Category.query.filter_by(user_id=ADMIN_USER_ID).order_by(Category.level, Category.name).all()
    
    result = []
    for c in categories:
        result.append({
            "id": c.id, 
            "name": c.name,
            "level": c.level,
            "card_count": Flashcard.query.filter_by(category_id=c.id).count() 
        })
    return jsonify(result), 200

# 7. Добавить публичный набор
@flashcards_bp.route("/add_public_set", methods=["POST"])
@jwt_required()
def add_public_set_to_user():
    user_id = int(get_jwt_identity())
    data = request.json
    category_id = data.get("category_id")
    
    public_category = Category.query.get(category_id)
    if not public_category or public_category.user_id != 0: 
        return jsonify({"error": "Набор не найден"}), 404
    
    existing_category=Category.query.filter_by(user_id=user_id, name=public_category.name).first()
    if existing_category:
        return jsonify({
            "message": "Уже добавлено, переходим к изучению", 
            "category_id": existing_category.id 
        }), 200

    new_category = Category(user_id=user_id, name=public_category.name, level=public_category.level)
    db.session.add(new_category)
    db.session.flush()

    public_flashcards = Flashcard.query.filter_by(category_id=public_category.id).all()
    for public_card in public_flashcards:
        new_flashcard = Flashcard(
            category_id=new_category.id, front=public_card.front, back=public_card.back, user_id=user_id 
        )
        db.session.add(new_flashcard)
        db.session.flush()
        initial_schedule = RepetitionSchedule(
            flashcard_id=new_flashcard.id, user_id=user_id, next_review_date=date.today()
        )
        db.session.add(initial_schedule)
        
    db.session.commit()
    return jsonify({"message": "Добавлено"}), 201

# 8. Удалить категорию
@flashcards_bp.route("/category/<int:category_id>", methods=["DELETE"])
@jwt_required()
def delete_category(category_id):
    user_id = int(get_jwt_identity())
    category = Category.query.filter_by(id=category_id, user_id=user_id).first()
    
    if not category: return jsonify({"error": "Не найдено"}), 404

    # Отвязываем карточки (делаем их без категории)
    cards = Flashcard.query.filter_by(category_id=category_id).all()
    for card in cards:
        card.category_id = None
    
    db.session.delete(category)
    db.session.commit()
    return jsonify({"message": "Удалено"}), 200

# 9. Получить одну карточку по ID (НОВЫЙ МАРШРУТ)
@flashcards_bp.route("/<int:card_id>", methods=["GET"])
@jwt_required()
def get_flashcard(card_id):
    from models import RepetitionSchedule, Flashcard # Импорты должны быть доступны
    
    user_id = int(get_jwt_identity())
    
    # Ищем карточку, принадлежащую пользователю
    card = Flashcard.query.filter_by(id=card_id, user_id=user_id).first()

    if not card:
        return jsonify({"error": "Карточка не найдена"}), 404

    # Находим расписание повторения (нужно для оценки, чтобы сохранить прогресс)
    schedule = RepetitionSchedule.query.filter_by(flashcard_id=card_id, user_id=user_id).first()

    return jsonify({
        "id": card.id,
        "front": card.front,
        "back": card.back,
        "category_id": card.category_id,
        "schedule_id": schedule.id if schedule else None 
    }), 200