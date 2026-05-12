from __future__ import annotations

import os


def generate_ai_insights(summary: dict, recommendations: list[str]) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Set GROQ_API_KEY to enable AI-generated planning insights."

    try:
        from groq import Groq
    except ImportError:
        return "Install the groq package to enable AI-generated planning insights."

    client = Groq(api_key=api_key)
    prompt = (
        "You are a tax planning assistant for an Indian taxpayer. Provide concise, "
        "educational suggestions. Avoid legal guarantees and advise consulting a tax professional. "
        "Return clear bullet points with practical next steps.\n\n"
        f"Summary: {summary}\n"
        f"Rule-based recommendations: {recommendations}"
    )
    completion = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=[
            {"role": "system", "content": "You explain tax planning in simple, careful language."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_completion_tokens=450,
    )
    return completion.choices[0].message.content or "No AI insight was generated."
