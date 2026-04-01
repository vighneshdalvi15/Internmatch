from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from backend.db import get_db
from backend.utils.mongo import oid, serialize_doc


applications_bp = Blueprint("applications", __name__)


@applications_bp.post("")
@jwt_required()
def apply():
    claims = get_jwt()
    if claims.get("role") != "student":
        return jsonify({"error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    job_id = payload.get("job_id")
    if not job_id:
        return jsonify({"error": "missing_fields", "fields": ["job_id"]}), 400

    db = get_db(current_app)
    student_id = oid(get_jwt_identity())
    job = db.jobs.find_one({"_id": oid(job_id)})
    if not job or job.get("status") != "open":
        return jsonify({"error": "job_not_available"}), 400

    now = datetime.now(timezone.utc)
    doc = {
        "job_id": job["_id"],
        "company_id": job["company_id"],
        "student_id": student_id,
        "status": "submitted",
        "cover_note": str(payload.get("cover_note", "")).strip(),
        "created_at": now,
        "updated_at": now,
    }

    try:
        res = db.applications.insert_one(doc)
    except Exception:
        return jsonify({"error": "already_applied"}), 409

    app_doc = db.applications.find_one({"_id": res.inserted_id})
    return jsonify({"application": serialize_doc(app_doc)}), 201


@applications_bp.get("/mine")
@jwt_required()
def mine():
    claims = get_jwt()
    db = get_db(current_app)
    user_id = oid(get_jwt_identity())

    if claims.get("role") == "student":
        items = [serialize_doc(d) for d in db.applications.find({"student_id": user_id}).sort("created_at", -1).limit(200)]
        return jsonify({"items": items})

    if claims.get("role") == "company":
        items = [serialize_doc(d) for d in db.applications.find({"company_id": user_id}).sort("created_at", -1).limit(200)]
        return jsonify({"items": items})

    return jsonify({"error": "forbidden"}), 403


@applications_bp.put("/<app_id>")
@jwt_required()
def update_status(app_id: str):
    claims = get_jwt()
    if claims.get("role") != "company":
        return jsonify({"error": "forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    if status not in ("submitted", "under_review", "shortlisted", "rejected", "selected"):
        return jsonify({"error": "invalid_status"}), 400

    db = get_db(current_app)
    company_id = oid(get_jwt_identity())
    existing = db.applications.find_one({"_id": oid(app_id)})
    if not existing:
        return jsonify({"error": "not_found"}), 404
    if existing.get("company_id") != company_id:
        return jsonify({"error": "forbidden"}), 403

    now = datetime.now(timezone.utc)
    db.applications.update_one({"_id": existing["_id"]}, {"$set": {"status": status, "updated_at": now}})
    updated = db.applications.find_one({"_id": existing["_id"]})
    return jsonify({"application": serialize_doc(updated)})

