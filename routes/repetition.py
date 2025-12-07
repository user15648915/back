from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import date, timedelta, datetime
from extensions import db
# ❗ ИМПОРТИРУЕМ QuizResult для записи статистики
from models import Flashcard, RepetitionSchedule, QuizResult, User
from utils.sm2 import sm2_update

# создаём blueprint
repetition_bp = Blueprint("repetition", __name__)

# получить карточки на сегодня
@repetition_bp.route("/today", methods=["GET"])
@jwt_required()
def get_today_cards():
    user_id = int(get_jwt_identity())
    category_id = request.args.get('category_id', type=int) 
    
    today = date.today()

    # 1. Запрос карточек ДЛЯ КОНКРЕТНОЙ КАТЕГОРИИ
    if category_id is not None:
        # Мы ищем все карточки, которые принадлежат этой категории и пользователю.
        # Фильтр по дате повторения (next_review_date <= today) ИГНОРИРУЕТСЯ, 
        # чтобы пользователь мог учить категорию в любое время.
        
        # Получаем Flashcards, которые имеют RepetitionSchedule
        query = RepetitionSchedule.query.join(Flashcard).filter(
            RepetitionSchedule.user_id == user_id,
            Flashcard.category_id == category_id
        ).order_by(
            RepetitionSchedule.next_review_date.asc() # Можно оставить сортировку
        )
        
        # Устанавливаем лимит, например, 50 карточек
        schedules = query.all()
        
    # 2. Запрос карточек ПО ОБЩЕМУ РАСПИСАНИЮ (Стандартный режим)
    else:
        # Стандартная логика: только карточки, которые пора повторять
        query = RepetitionSchedule.query.join(Flashcard).filter(
            RepetitionSchedule.user_id == user_id,
            RepetitionSchedule.next_review_date <= today,
        ).order_by(
            RepetitionSchedule.next_review_date.asc()
        )
        schedules = query.limit(200).all()


    # 3. Форматирование результата (Общее для обоих случаев)
    cards = []
    for schedule in schedules:
        card = schedule.flashcard
        cards.append({
            "id": card.id,
            "front": card.front,
            "back": card.back,
            "category_id": card.category_id,
            "schedule_id": schedule.id, 
        })

    return jsonify(cards), 200


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
        
        user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    # Статус до обновления
    was_mastered = (schedule.repetitions > 0 and schedule.efactor > 1.3)
    
    # ПРИМЕНЯЕМ SM2 (это обновит schedule)
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

    # Статус после обновления
    is_mastered = (reps > 0 and ef > 1.3) # Критерий "Изучено" (Mastered)
    
    # 1. Логика для "Изучаю" (studying_count)
    # Срабатывает, если:
    #   A) Карточка оценивается как "Не знаю" (quality=0) или "Трудно" (quality < 3)
    #   B) И это *первое* взаимодействие с карточкой (было repetitions=0)
    #   C) И она еще не была "Изучаю" (studying_count)
    # 
    # Мы упрощаем: если repetitions > 0, считаем, что она уже в "Изучаю" или "Изучено".
    # Для целей этого счетчика, мы увеличиваем "Изучаю", если repetitions было 0,
    # и пользователь дал ЛЮБУЮ оценку, КРОМЕ "Знаю" с первой попытки.
    
    if schedule.repetitions == 0 and quality < 4:
        # Это первая попытка и она не "Знаю" -> Переходит в "Изучаю"
        user.studying_count += 1
        # Важно: устанавливаем repetitions = 1 после sm2_update
        
    # 2. Логика для "Изучено" (learned_count)
    # Срабатывает, если:
    #   A) Карточка стала "Изучена" (is_mastered = True)
    #   B) И она *НЕ* была "Изучена" до этого (was_mastered = False)
    #   C) Она должна быть удалена из "Изучаю", если она там была.
    
    if is_mastered and not was_mastered:
        # Карточка только что освоена
        user.learned_count += 1
        # Если карточка была в "Изучаю" (то есть reps = 1-5, но efactor < 1.3), 
        # уменьшаем studying_count. 
        if user.studying_count > 0:
             user.studying_count -= 1
    
    # Если была "Изучено" и стала "Не знаю" (quality < 3)
    # Сбрасываем ее в "Изучаю"
    if was_mastered and not is_mastered and quality < 3:
        user.learned_count = max(0, user.learned_count - 1)
        user.studying_count += 1

    # ... (старая логика QuizResult)
    # ----------------------------------------------------------
    
    # Один финальный коммит для всех изменений (Schedule + QuizResult + User)
    db.session.commit()

    return jsonify({
        "message": "updated",
        "flashcard_id": flashcard_id,
        "next_review_date": str(schedule.next_review_date)
    }), 200

@repetition_bp.route("/next", methods=["GET"])
@jwt_required()
def get_next_cards():
    user_id = int(get_jwt_identity())
    category_id = request.args.get('category_id')
    
    print(f"--- DEBUG: Запрос карточек для User {user_id}. Категория: {category_id} ---")

    query = RepetitionSchedule.query.filter(
        RepetitionSchedule.user_id == user_id,
        RepetitionSchedule.next_review_date <= date.today()
    )

    # Присоединяем карточки
    query = query.join(Flashcard) 

    if category_id and category_id.isdigit(): 
        query = query.filter(Flashcard.category_id == int(category_id))
        
    schedules = query.order_by(RepetitionSchedule.next_review_date).limit(20).all()
    
    print(f"--- DEBUG: Найдено карточек: {len(schedules)} ---")

    cards_data = []
    for schedule in schedules:
        card = schedule.flashcard 
        cards_data.append({
            "id": card.id,
            "front": card.front,
            "back": card.back,
            "schedule_id": schedule.id,
            "category_id": card.category_id
        })

    return jsonify(cards_data), 200


# Маршрут для оценки (восстановлен стандартный код SuperMemo)
@repetition_bp.route("/grade", methods=["POST"])
@jwt_required()
def grade_card():
    user_id = int(get_jwt_identity())
    data = request.json
    card_id = data.get("card_id")
    quality = data.get("quality") # 0-5

    schedule = RepetitionSchedule.query.filter_by(flashcard_id=card_id, user_id=user_id).first()
    if not schedule:
        return jsonify({"error": "Schedule not found"}), 404

    # Логика SuperMemo-2
    if quality >= 3:
        # Успешное повторение
        if schedule.repetitions == 0:
            schedule.interval = 1
        elif schedule.repetitions == 1:
            schedule.interval = 6
        else:
            schedule.interval = int(schedule.interval * schedule.efactor)
        
        schedule.repetitions += 1
        # Обновляем E-Factor (стандартная формула)
        schedule.efactor = max(1.3, schedule.efactor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        
        # Планируем следующее повторение в будущем
        schedule.next_review_date = date.today() + timedelta(days=schedule.interval)

    else: # quality < 3 (Не знаю / Тяжело)
        # Неуспешное повторение: сброс, но оставляем доступной СЕГОДНЯ
        schedule.repetitions = 1 # ❗ Не сбрасываем в 0, чтобы не терять статус "Изучаю"
        schedule.interval = 1
        schedule.efactor = max(1.3, schedule.efactor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        # ❗ Карточка доступна сразу
        schedule.next_review_date = date.today()

    # Проверяем, была ли уже активность сегодня (чтобы не дублировать)
    today_result = QuizResult.query.filter(
        QuizResult.user_id == user_id,
        db.func.date(QuizResult.date) == date.today()
    ).first()

    if today_result:
        # Если запись есть, просто обновляем счетчик очков
        today_result.score += 1 
    else:
        # Если записи нет, создаем новую
        new_result = QuizResult(user_id=user_id, score=1, date=datetime.utcnow())
        db.session.add(new_result)
    
    db.session.commit()
    return jsonify({"message": "Оценка сохранена", "next_date": schedule.next_review_date}), 200