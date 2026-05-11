import os
import json
import requests
from http.server import BaseHTTPRequestHandler
from supabase import create_client

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        """Re-classifies ALL videos by clearing existing classifications and re-running LLM."""
        try:
            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
            OPENROUTER_API_KEY = os.environ.get("DEEPSEEK_KEY")

            if not SUPABASE_URL or not SUPABASE_KEY or not OPENROUTER_API_KEY:
                self._send(500, {"error": "Faltan credenciales"})
                return

            sb = create_client(SUPABASE_URL, SUPABASE_KEY)

            # Step 1: Wipe existing classifications and pain points
            sb.table("latam_pain_points").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            sb.table("video_classifications").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

            # Step 2: Get all transcriptions
            transcriptions = sb.table("transcriptions").select("video_id, full_text").limit(500).execute()
            if not transcriptions.data:
                self._send(200, {"message": "No hay transcripciones para re-clasificar.", "reclassified": 0})
                return

            system_prompt = "Eres un analista experto en modelos de negocio digitales. Tu tarea es analizar transcripciones de videos de emprendedores y extraer información estructurada de forma precisa, concreta y verificable.\n\nDebes responder EXCLUSIVAMENTE en JSON válido. No agregues texto adicional."

            reclassified = 0
            errors = []

            for t in transcriptions.data:
                video_id = t["video_id"]
                transcript_text = t["full_text"][:15000]

                user_prompt = f"""Analiza la siguiente transcripción de un video de emprendimiento y extrae la información solicitada.

TRANSCRIPCIÓN:
{transcript_text}

INSTRUCCIONES:
1. Identifica el modelo de negocio principal
2. Identifica la fuente de ingresos (cómo gana dinero)
3. Identifica el cliente objetivo
4. EXTRAPOLACIÓN LATAM: Identifica los problemas (pain points) principales que resuelve este modelo y extrapólalos a la realidad y contexto del mercado latinoamericano. Explica cómo o por qué esta necesidad existe o se adapta en LATAM.

REGLAS IMPORTANTES:
- No inventes información. Si no está claro, usa null
- Sé específico (no generalices)
- Máximo 2-3 frases por campo
- IMPORTANTE: Toda la respuesta DEBE estar en ESPAÑOL.

FORMATO DE RESPUESTA:
{{
  "business_model": {{ "type": "string o null", "description": "string o null" }},
  "revenue_stream": {{ "type": "string o null", "description": "string o null" }},
  "target_customer": {{ "type": "string o null", "description": "string o null" }},
  "latam_pain_points": [
    {{
      "pain_point": "Breve descripción del problema original",
      "latam_context_adaptation": "Justificación de cómo y por qué este dolor aplica en LATAM",
      "category": "Categoría del pain point (ej: Fintech, Logistics, Education, Health, E-commerce, SaaS, etc.)",
      "relevance_level": "High | Medium | Low"
    }}
  ],
  "confidence_score": 90
}}"""

                headers = {
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "openrouter/free",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                }

                try:
                    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                    
                    if response.status_code != 200:
                        OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
                        if response.status_code == 429 and OPENAI_API_KEY:
                            headers_oai = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
                            payload["model"] = "gpt-4o-mini"
                            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers_oai, json=payload)
                            if response.status_code != 200:
                                errors.append({"video_id": video_id, "error": "Fallback failed"})
                                continue
                        else:
                            errors.append({"video_id": video_id, "error": f"Status {response.status_code}"})
                            continue

                    result_data = response.json()
                    content = result_data["choices"][0]["message"]["content"]
                    content = content.replace("```json", "").replace("```", "").strip()
                    extracted = json.loads(content)

                    b_model_type = None
                    if extracted.get("business_model") and isinstance(extracted["business_model"], dict):
                        b_model_type = extracted["business_model"].get("type")
                    elif isinstance(extracted.get("business_model"), str):
                        b_model_type = extracted.get("business_model")

                    sb.table("video_classifications").insert({
                        "video_id": video_id,
                        "business_model": b_model_type,
                        "key_insights": extracted,
                        "model_used": payload["model"],
                        "prompt_version": "v2_reclass"
                    }).execute()

                    pain_points_array = extracted.get("latam_pain_points", [])
                    if isinstance(pain_points_array, list):
                        for pp in pain_points_array:
                            if isinstance(pp, dict) and pp.get("pain_point"):
                                impact = pp.get("relevance_level", "Medium")
                                if impact not in ("Low", "Medium", "High", "Critical"):
                                    impact = "Medium"
                                sb.table("latam_pain_points").insert({
                                    "description": pp.get("pain_point"),
                                    "impact_level": impact,
                                    "category": pp.get("category", "General"),
                                    "evidence": pp.get("latam_context_adaptation"),
                                    "source_video_id": video_id
                                }).execute()

                    reclassified += 1
                except Exception as inner_e:
                    errors.append({"video_id": video_id, "error": str(inner_e)})

            self._send(200, {
                "message": f"Re-clasificación completada: {reclassified} videos procesados.",
                "reclassified": reclassified,
                "errors": errors[:5]
            })

        except Exception as e:
            self._send(500, {"error": str(e)})

    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
