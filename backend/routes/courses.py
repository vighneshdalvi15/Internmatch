from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
from flask_jwt_extended import get_jwt_identity

from backend.db import get_db
from backend.utils.mongo import oid, serialize_doc
from backend.utils.validation import require_fields, split_skills


courses_bp = Blueprint("courses", __name__)


def _seed_if_needed() -> None:
    db = get_db(current_app)
    if db.courses.count_documents({}) > 0:
        return

    now = datetime.now(timezone.utc)

    # User-provided YouTube videos
    seed = [
        {
            "youtube_id": "7wnove7K-ZQ",
            "title": "Python Full Course (Beginner to Intermediate)",
            "url": "https://youtu.be/7wnove7K-ZQ",
            "skills": split_skills(["python", "programming", "problem solving"]),
        },
        {
            "youtube_id": "yRpLlJmRo2w",
            "title": "MongoDB Full Course",
            "url": "https://youtu.be/yRpLlJmRo2w",
            "skills": split_skills(["mongodb", "database", "nosql"]),
        },
        {
            "youtube_id": "gxHXPmePnvo",
            "title": "React JS Full Course",
            "url": "https://youtu.be/gxHXPmePnvo",
            "skills": split_skills(["react", "javascript", "frontend", "web development"]),
        },
        {
            "youtube_id": "tVzUXW6siu0",
            "title": "Node.js Full Course",
            "url": "https://youtu.be/tVzUXW6siu0",
            "skills": split_skills(["node.js", "javascript", "backend", "api"]),
        },
        {
            "youtube_id": "8mAITcNt710",
            "title": "SQL Tutorial - Full Database Course for Beginners",
            "url": "https://youtu.be/8mAITcNt710",
            "skills": split_skills(["sql", "database", "data analysis"]),
        },
        {
            "youtube_id": "rfscVS0vtbw",
            "title": "Learn Python - Full Course for Beginners (freeCodeCamp)",
            "url": "https://youtu.be/rfscVS0vtbw",
            "skills": split_skills(["python", "programming", "dsa"]),
        },
        {
            "youtube_id": "ZSPZob_1TOk",
            "title": "Git and GitHub for Beginners - Crash Course",
            "url": "https://youtu.be/ZSPZob_1TOk",
            "skills": split_skills(["git", "github", "version control"]),
        },
        {
            "youtube_id": "zJSY8tbf_ys",
            "title": "Data Structures Easy to Advanced (Full Course)",
            "url": "https://youtu.be/zJSY8tbf_ys",
            "skills": split_skills(["dsa", "problem solving", "programming"]),
        },
        {
            "youtube_id": "c9Wg6Cb_YlU",
            "title": "UI/UX Design Full Course",
            "url": "https://youtu.be/c9Wg6Cb_YlU",
            "skills": split_skills(["ui/ux", "figma", "design systems"]),
        },
        {
            "youtube_id": "G8uL0lFFoN0",
            "title": "Aptitude for Placements (Basics + Practice)",
            "url": "https://youtu.be/G8uL0lFFoN0",
            "skills": split_skills(["aptitude", "problem solving", "communication"]),
        },
    ]

    for c in seed:
        c["created_at"] = now
        c["updated_at"] = now
        c["provider"] = "YouTube"
        c["type"] = "youtube"
        c["thumbnail_url"] = f"https://img.youtube.com/vi/{c['youtube_id']}/hqdefault.jpg"

    db.courses.insert_many(seed)


@courses_bp.before_app_request
def ensure_seeded():
    # seed once per process (safe: only inserts if empty)
    if current_app.extensions.get("_seeded_courses"):
        return
    try:
        _seed_if_needed()
        current_app.extensions["_seeded_courses"] = True
    except Exception:
        # Don't break app boot if DB isn't available yet.
        pass


@courses_bp.get("")
def list_courses():
    db = get_db(current_app)
    items = [serialize_doc(d) for d in db.courses.find({}).sort("created_at", -1).limit(200)]
    return jsonify({"items": items})


@courses_bp.get("/<course_id>")
def get_course(course_id: str):
    db = get_db(current_app)
    doc = db.courses.find_one({"_id": oid(course_id)})
    if not doc:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"course": serialize_doc(doc)})


@courses_bp.post("")
@jwt_required()
def create_course():
    claims = get_jwt()
    if claims.get("role") not in ("company", "admin"):
        return jsonify({"error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    missing = require_fields(payload, ["title", "url"])
    if missing:
        return jsonify({"error": "missing_fields", "fields": missing}), 400

    now = datetime.now(timezone.utc)
    doc = {
        "title": str(payload.get("title", "")).strip(),
        "url": str(payload.get("url", "")).strip(),
        "provider": str(payload.get("provider", "InternMatch")).strip(),
        "type": str(payload.get("type", "link")).strip(),
        "skills": split_skills(payload.get("skills")),
        "thumbnail_url": str(payload.get("thumbnail_url", "")).strip(),
        "youtube_id": str(payload.get("youtube_id", "")).strip(),
        "created_at": now,
        "updated_at": now,
    }

    db = get_db(current_app)
    res = db.courses.insert_one(doc)
    created = db.courses.find_one({"_id": res.inserted_id})
    return jsonify({"course": serialize_doc(created)}), 201


@courses_bp.put("/<course_id>")
@jwt_required()
def update_course(course_id: str):
    claims = get_jwt()
    if claims.get("role") not in ("company", "admin"):
        return jsonify({"error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    db = get_db(current_app)
    existing = db.courses.find_one({"_id": oid(course_id)})
    if not existing:
        return jsonify({"error": "not_found"}), 404

    now = datetime.now(timezone.utc)
    update: dict = {"updated_at": now}
    for k in ["title", "url", "provider", "type", "thumbnail_url", "youtube_id"]:
        if k in payload:
            update[k] = payload.get(k)
    if "skills" in payload:
        update["skills"] = split_skills(payload.get("skills"))

    db.courses.update_one({"_id": existing["_id"]}, {"$set": update})
    updated = db.courses.find_one({"_id": existing["_id"]})
    return jsonify({"course": serialize_doc(updated)})


@courses_bp.delete("/<course_id>")
@jwt_required()
def delete_course(course_id: str):
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "forbidden"}), 403
    db = get_db(current_app)
    res = db.courses.delete_one({"_id": oid(course_id)})
    if res.deleted_count == 0:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"ok": True})


@courses_bp.post("/<course_id>/watch")
@jwt_required()
def mark_watched(course_id: str):
    claims = get_jwt()
    if claims.get("role") != "student":
        return jsonify({"error": "forbidden"}), 403

    db = get_db(current_app)
    course = db.courses.find_one({"_id": oid(course_id)})
    if not course:
        return jsonify({"error": "not_found"}), 404

    user_id = oid(get_jwt_identity())
    now = datetime.now(timezone.utc)
    db.student_profiles.update_one(
        {"user_id": user_id},
        {
            "$setOnInsert": {"user_id": user_id, "created_at": now},
            "$set": {"updated_at": now},
            "$addToSet": {"courses_watched": oid(course_id)},
        },
        upsert=True,
    )
    return jsonify({"ok": True})

