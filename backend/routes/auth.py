from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token

from backend.db import get_db
from backend.utils.mongo import serialize_doc
from backend.utils.security import Role, hash_password, verify_password
from backend.utils.validation import is_valid_email, require_fields


auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/signup")
def signup():
    payload = request.get_json(silent=True) or {}
    missing = require_fields(payload, ["role", "email", "password"])
    if missing:
        return jsonify({"error": "missing_fields", "fields": missing}), 400

    role: Role = payload.get("role")
    if role not in ("student", "company"):
        return jsonify({"error": "invalid_role"}), 400

    email = str(payload.get("email", "")).strip().lower()
    if not is_valid_email(email):
        return jsonify({"error": "invalid_email"}), 400

    password = str(payload.get("password", ""))
    if len(password) < 6:
        return jsonify({"error": "weak_password", "min_length": 6}), 400

    db = get_db(current_app)
    now = datetime.now(timezone.utc)

    user_doc = {
        "role": role,
        "email": email,
        "password_hash": hash_password(password),
        "created_at": now,
        "updated_at": now,
        "last_login_at": None,
    }

    try:
        res = db.users.insert_one(user_doc)
    except Exception:
        return jsonify({"error": "email_already_exists"}), 409

    user_doc["_id"] = res.inserted_id
    token = create_access_token(identity=str(res.inserted_id), additional_claims={"role": role})
    return jsonify({"access_token": token, "user": serialize_doc({k: v for k, v in user_doc.items() if k != "password_hash"})})


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    missing = require_fields(payload, ["email", "password"])
    if missing:
        return jsonify({"error": "missing_fields", "fields": missing}), 400

    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))

    db = get_db(current_app)
    user = db.users.find_one({"email": email})
    if not user:
        return jsonify({"error": "invalid_credentials"}), 401

    if not verify_password(password, user.get("password_hash", "")):
        return jsonify({"error": "invalid_credentials"}), 401

    now = datetime.now(timezone.utc)
    db.users.update_one({"_id": user["_id"]}, {"$set": {"last_login_at": now, "updated_at": now}})

    role = user.get("role")
    token = create_access_token(identity=str(user["_id"]), additional_claims={"role": role})
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    return jsonify({"access_token": token, "user": serialize_doc(safe_user)})

