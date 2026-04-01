from __future__ import annotations

import os
import time

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required
from werkzeug.utils import secure_filename


uploads_bp = Blueprint("uploads", __name__)

ALLOWED_EXT = {"pdf", "doc", "docx"}


def _ext(filename: str) -> str:
    return (filename.rsplit(".", 1)[-1] if "." in filename else "").lower()


@uploads_bp.post("/resume")
@jwt_required()
def upload_resume():
    claims = get_jwt()
    if claims.get("role") != "student":
        return jsonify({"error": "forbidden"}), 403

    if "file" not in request.files:
        return jsonify({"error": "missing_file"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "missing_file"}), 400

    ext = _ext(f.filename)
    if ext not in ALLOWED_EXT:
        return jsonify({"error": "invalid_file_type", "allowed": sorted(ALLOWED_EXT)}), 400

    upload_dir = current_app.config["UPLOAD_DIR"]
    safe = secure_filename(f.filename)
    name = f"{int(time.time())}_{safe}"
    path = os.path.join(upload_dir, name)
    f.save(path)

    return jsonify({"url": f"/uploads/{name}"})

