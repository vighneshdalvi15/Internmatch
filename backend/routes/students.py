from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from backend.db import get_db
from backend.utils.mongo import oid, serialize_doc
from backend.utils.validation import split_skills


students_bp = Blueprint("students", __name__)


def _require_student():
    claims = get_jwt()
    if claims.get("role") != "student":
        return jsonify({"error": "forbidden"}), 403
    return None


@students_bp.get("/me")
@jwt_required()
def get_me():
    denied = _require_student()
    if denied:
        return denied

    db = get_db(current_app)
    user_id = oid(get_jwt_identity())
    prof = db.student_profiles.find_one({"user_id": user_id}) or {"user_id": user_id}
    return jsonify({"profile": serialize_doc(prof)})


@students_bp.put("/me")
@jwt_required()
def upsert_me():
    denied = _require_student()
    if denied:
        return denied

    payload = request.get_json(silent=True) or {}
    db = get_db(current_app)
    user_id = oid(get_jwt_identity())
    now = datetime.now(timezone.utc)

    doc = {
        "full_name": payload.get("full_name", ""),
        "phone": payload.get("phone", ""),
        "education": payload.get("education", {}),
        "skills": split_skills(payload.get("skills")),
        "projects": payload.get("projects", []),
        "experience": payload.get("experience", ""),
        "preferences": payload.get("preferences", {}),
        "links": payload.get("links", {}),
        "resume_url": payload.get("resume_url", ""),
        "updated_at": now,
    }

    existing = db.student_profiles.find_one({"user_id": user_id})
    if existing:
        db.student_profiles.update_one({"_id": existing["_id"]}, {"$set": doc})
        prof = db.student_profiles.find_one({"_id": existing["_id"]})
    else:
        doc["user_id"] = user_id
        doc["created_at"] = now
        res = db.student_profiles.insert_one(doc)
        prof = db.student_profiles.find_one({"_id": res.inserted_id})

    return jsonify({"profile": serialize_doc(prof)})


@students_bp.get("/me/dashboard")
@jwt_required()
def dashboard():
    denied = _require_student()
    if denied:
        return denied

    db = get_db(current_app)
    user_id = oid(get_jwt_identity())

    prof = db.student_profiles.find_one({"user_id": user_id}) or {}
    skills_known = len(prof.get("skills") or [])
    courses_watched = len(prof.get("courses_watched") or [])

    tests_given = db.test_attempts.count_documents({"user_id": user_id})
    internships_applied = db.applications.count_documents({"student_id": user_id})
    internships_completed = db.applications.count_documents({"student_id": user_id, "status": "selected"})

    return jsonify(
        {
            "stats": {
                "tests_given": tests_given,
                "internships_applied": internships_applied,
                "internships_completed": internships_completed,
                "courses_watched": courses_watched,
                "skills_known": skills_known,
            }
        }
    )

