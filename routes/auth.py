from flask import Blueprint, request, jsonify
from extensions import db, bcrypt
from models import User
from flask_jwt_extended import create_access_token
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import jsonify
from models import User

# 👇 это должно быть в самом верху!
auth_bp = Blueprint("auth", __name__)

# регистрация
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.json
    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email и пароль обязательны"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Пользователь уже существует"}), 400

    hashed_pw = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    user = User(email=data["email"], password=hashed_pw)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Регистрация успешна"}), 201

# логин
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email и пароль обязательны"}), 400

    user = User.query.filter_by(email=data["email"]).first()
    if not user or not bcrypt.check_password_hash(user.password, data["password"]):
        return jsonify({"error": "Неверный email или пароль"}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({"access_token": token}), 200

#профиль
@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def profile():
    """Возвращает данные текущего пользователя"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user.id,
        "name": getattr(user, "name", None),
        "email": user.email
    }), 200