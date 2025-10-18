from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Category

categories_bp = Blueprint("categories", __name__)

@categories_bp.route("", methods=["GET"])
@jwt_required()
def list_categories():
    user_id = int(get_jwt_identity())
    cats = Category.query.filter_by(user_id=user_id).all()
    return jsonify([{"id": c.id, "name": c.name} for c in cats]), 200

@categories_bp.route("", methods=["POST"])
@jwt_required()
def create_category():
    data = request.json
    if not data.get("name"):
        return jsonify({"error": "name required"}), 400
    user_id = int(get_jwt_identity())
    c = Category(name=data["name"], user_id=user_id)
    db.session.add(c)
    db.session.commit()
    return jsonify({"id": c.id, "name": c.name}), 201

@categories_bp.route("/<int:cat_id>", methods=["DELETE"])
@jwt_required()
def delete_category(cat_id):
    user_id = int(get_jwt_identity())
    cat = Category.query.filter_by(id=cat_id, user_id=user_id).first()
    if not cat:
        return jsonify({"error": "not found"}), 404
    db.session.delete(cat)
    db.session.commit()
    return jsonify({"message": "deleted"}), 200
