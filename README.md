# InternMatch (Full-Stack)

Flask + MongoDB internship platform with a Tailwind SPA frontend.

## Prerequisites
- Python 3.10+
- MongoDB running locally (or a MongoDB URI)

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set `MONGODB_URI`, `SECRET_KEY`, `JWT_SECRET_KEY`.

## Run

```bash
python run.py
```

Open `http://127.0.0.1:5000`.

## Default behavior
- **Student** and **Company** can sign up and log in
- **Company** can post jobs/internships
- **Student** can browse and apply
- **AI Match** computes match % + missing skills and recommends courses/resources

