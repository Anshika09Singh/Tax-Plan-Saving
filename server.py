from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory, session, redirect, url_for
from dotenv import load_dotenv
import storage

from ai_advisor import generate_ai_insights
from tax_engine import DeductionInput, IncomeInput, build_summary, calculate_tax_plan, generate_recommendations

load_dotenv()
storage.init_db()

ROOT = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(ROOT), static_url_path="")
app.secret_key = "tax_saving_assistant_secret_key" # In production, use a secure random key


def number(payload: dict[str, Any], key: str) -> float:
    try:
        return max(float(payload.get(key, 0) or 0), 0.0)
    except (TypeError, ValueError):
        return 0.0


def to_inputs(payload: dict[str, Any]) -> tuple[IncomeInput, DeductionInput]:
    income = IncomeInput(
        salary=number(payload, "salary"),
        freelance=number(payload, "freelance"),
        business=number(payload, "business"),
        other=number(payload, "other"),
    )
    deductions = DeductionInput(
        section_80c=number(payload, "section80c"),
        nps=number(payload, "nps"),
        medical_insurance=number(payload, "medical"),
        home_loan_interest=number(payload, "homeLoan"),
        education_loan_interest=number(payload, "educationLoan"),
        donations=number(payload, "donations"),
    )
    return income, deductions


def serialize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "gross_income": summary["gross_income"],
        "eligible_deductions": summary["eligible_deductions"],
        "deduction_breakup": summary["deduction_breakup"],
        "old_regime": asdict(summary["old_regime"]),
        "new_regime": asdict(summary["new_regime"]),
        "best_regime": summary["best_regime"],
        "best_tax": summary["best_tax"],
        "tax_savings": summary["tax_savings"],
    }


def analyze(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str], str]:
    income, deductions = to_inputs(payload)
    summary = calculate_tax_plan(income, deductions)
    recommendations = generate_recommendations(income, deductions, summary)
    report = build_summary(summary)
    return serialize_summary(summary), recommendations, report


@app.route("/login")
def login_page():
    return send_from_directory(ROOT, "login.html")

@app.post("/api/register")
def register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
        
    if storage.register_user(username, password, full_name):
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Username already exists"}), 409

@app.post("/api/login")
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    
    full_name = storage.verify_user(username, password)
    if full_name:
        session["user"] = username
        session["full_name"] = full_name
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"success": True})

@app.get("/api/user")
def get_user():
    if "user" not in session:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify({"username": session["user"], "full_name": session["full_name"]})

@app.get("/")
def index() -> Any:
    return send_from_directory(ROOT, "index.html")

@app.get("/dashboard")
def dashboard() -> Any:
    if "user" not in session:
        return redirect(url_for("login_page"))
    return send_from_directory(ROOT, "dashboard.html")


@app.get("/api/status")
def status() -> Any:
    return jsonify(
        {
            "groqConfigured": bool(os.getenv("GROQ_API_KEY")),
            "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        }
    )


@app.post("/api/calculate")
def calculate() -> Any:
    payload = request.get_json(silent=True) or {}
    summary, recommendations, report = analyze(payload)
    return jsonify({"summary": summary, "recommendations": recommendations, "report": report})


@app.post("/api/ai-insights")
def ai_insights() -> Any:
    payload = request.get_json(silent=True) or {}
    summary, recommendations, _ = analyze(payload)
    if not os.getenv("GROQ_API_KEY"):
        return (
            jsonify(
                {
                    "error": "GROQ_API_KEY is not configured on the server.",
                    "insights": "Add your Groq API key in the terminal before starting the server to enable live AI insights.",
                }
            ),
            503,
        )

    try:
        insights = generate_ai_insights(summary, recommendations)
    except Exception as exc:  # Groq/network failures should not break the dashboard.
        return jsonify({"error": str(exc), "insights": "Groq could not generate insights for this request."}), 502
    return jsonify({"insights": insights})


@app.post("/api/chat")
def chat() -> Any:
    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    summary, recommendations, report = analyze(payload)
    if not question:
        return jsonify({"error": "Please enter a question."}), 400
    if not os.getenv("GROQ_API_KEY"):
        return jsonify({"error": "GROQ_API_KEY is not configured on the server."}), 503

    try:
        from groq import Groq

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        completion = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an Indian tax planning assistant. Be practical, concise, and educational. "
                        "Use the provided calculation context. Do not claim to file taxes or provide legal certification. "
                        "Mention when the user should consult a qualified tax professional."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": question,
                            "summary": summary,
                            "recommendations": recommendations,
                            "report": report,
                        },
                        indent=2,
                    ),
                },
            ],
            temperature=0.25,
            max_completion_tokens=550,
        )
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify({"answer": completion.choices[0].message.content or "No answer generated."})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8503, debug=True)
