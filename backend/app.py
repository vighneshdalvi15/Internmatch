"""
Flask application factory for InternMatch.

Creates the Flask app, loads environment configuration, initializes MongoDB,
registers API blueprints, and serves the single-page frontend.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from backend.db import get_db, init_db
from backend.routes.auth import auth_bp
from backend.routes.students import students_bp
from backend.routes.companies import companies_bp
from backend.routes.jobs import jobs_bp
from backend.routes.applications import applications_bp
from backend.routes.matching import matching_bp
from backend.routes.courses import courses_bp
from backend.routes.tests import tests_bp
from backend.routes.uploads import uploads_bp


def create_app() -> Flask:
    load_dotenv()

    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret")
    app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "0") == "1"

    # Use IPv4 localhost by default (some Windows setups don't bind ::1 for MongoDB).
    app.config["MONGODB_URI"] = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
    app.config["MONGODB_DB"] = os.getenv("MONGODB_DB", "internmatch")

    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
    os.makedirs(upload_dir, exist_ok=True)
    app.config["UPLOAD_DIR"] = upload_dir
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    JWTManager(app)

    init_db(app)

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(students_bp, url_prefix="/api/students")
    app.register_blueprint(companies_bp, url_prefix="/api/companies")
    app.register_blueprint(jobs_bp, url_prefix="/api/jobs")
    app.register_blueprint(applications_bp, url_prefix="/api/applications")
    app.register_blueprint(matching_bp, url_prefix="/api/match")
    app.register_blueprint(courses_bp, url_prefix="/api/courses")
    app.register_blueprint(tests_bp, url_prefix="/api/tests")
    app.register_blueprint(uploads_bp, url_prefix="/api/uploads")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/uploads/<path:filename>")
    def serve_upload(filename: str):
        return send_from_directory(app.config["UPLOAD_DIR"], filename)

    @app.get("/api/health")
    def health():
        # Dynamic check (prevents stale db_error after MongoDB starts).
        try:
            db = get_db(app)
            db.client.admin.command("ping")
            app.extensions.pop("db_error", None)
            return jsonify({"ok": True, "db": "connected"})
        except Exception as e:
            app.extensions["db_error"] = str(e)
            return jsonify({"ok": False, "db": "disconnected", "error": str(e)}), 503

    return app

