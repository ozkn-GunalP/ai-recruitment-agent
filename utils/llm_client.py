import json
import streamlit as st
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Ücretsiz model fallback zinciri — ilki başarısız olursa sıradakine geçer
FREE_MODELS = [
    "meta-llama/llama-4-maverick:free",
    "google/gemini-2.5-flash-preview:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]

MAX_RESUME_CHARS = 3000  # CV başına karakter üst sınırı (1000'den yükseltildi)


def _get_client() -> OpenAI:
    api_key = st.secrets.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY tanımlı değil. "
            ".streamlit/secrets.toml dosyasını kontrol et."
        )
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


def _build_prompt(job_description: str, candidates: list[dict]) -> str:
    """Yapılandırılmış JSON çıktısı isteyen prompt oluşturur."""

    candidates_text = ""
    for i, c in enumerate(candidates, 1):
        # CV metnini makul bir üst sınırla kırp
        text = c["text"][:MAX_RESUME_CHARS]
        candidates_text += f"\n--- Candidate {i}: {c['name']} ---\n{text}\n"

    return f"""You are a senior HR recruitment specialist.

Analyze the candidates below against the job description.

IMPORTANT: Respond ONLY with valid JSON matching this exact schema — no markdown, no extra text:

{{
  "job_summary": "2-3 sentence summary of the role requirements",
  "candidates": [
    {{
      "rank": 1,
      "file": "filename",
      "match_score": 85,
      "matching_skills": ["skill1", "skill2"],
      "experience_match": "Brief assessment",
      "strengths": ["strength1", "strength2"],
      "weaknesses": ["weakness1"],
      "evidence": "Direct quote or reference from the CV that supports the ranking"
    }}
  ],
  "recommendation": "Final hiring recommendation in 2-3 sentences"
}}

Rules:
- match_score is 0-100 based on how well the candidate fits the job description.
- evidence must reference actual content from the candidate's CV, not assumptions.
- Rank all candidates from best to worst fit.
- Be critical and objective.

Job Description:
{job_description}

Candidates:
{candidates_text}"""


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(min=2, max=10),
    retry=retry_if_exception_type((Exception,)),
    reraise=True,
)
def _call_model(client: OpenAI, model: str, prompt: str) -> str:
    """Tek bir modeli çağırır, retry ile."""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        timeout=60,
    )
    return response.choices[0].message.content


def analyze_candidates(job_description: str, candidates: list[dict]) -> dict:
    """Adayları analiz eder. Fallback zinciriyle çalışır.

    candidates: [{"name": "dosya_adi.pdf", "text": "cv metni"}, ...]
    Dönen: parsed JSON dict veya hata durumunda {"error": "mesaj"}
    """
    client = _get_client()
    prompt = _build_prompt(job_description, candidates)

    last_error = None
    used_model = None

    for model in FREE_MODELS:
        try:
            raw = _call_model(client, model, prompt)
            used_model = model

            # JSON çıkarma — bazen model ```json ... ``` ile sarar
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                # İlk ve son ``` satırlarını kaldır
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned

            result = json.loads(cleaned)
            result["_model_used"] = used_model
            return result

        except json.JSONDecodeError:
            # Model geçerli JSON üretmedi — ham metni fallback olarak dön
            return {
                "error": None,
                "raw_text": raw,
                "_model_used": used_model,
                "_parse_failed": True,
            }
        except Exception as e:
            last_error = e
            continue  # Sonraki modele geç

    return {"error": f"Tüm modeller başarısız oldu. Son hata: {last_error}"}
