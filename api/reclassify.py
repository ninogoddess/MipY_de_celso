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

            # Step 1: Wipe existing classifications ONLY. DO NOT WIPE latam_pain_points!
            sb.table("video_classifications").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

            # Step 2: Get all transcriptions
            transcriptions = sb.table("transcriptions").select("video_id, full_text").limit(500).execute()
            if not transcriptions.data:
                self._send(200, {"message": "No hay transcripciones para re-clasificar.", "reclassified": 0})
                return

            # Fetch Ground Truth LATAM pain points
            pp_resp = sb.table("latam_pain_points").select("id, name, description, category").execute()
            ground_truth_pps = pp_resp.data if pp_resp.data else []
            
            pp_context = ""
            for pp in ground_truth_pps:
                pp_context += f"- ID: {pp['id']} | Nombre: {pp['name']} | Categoría: {pp['category']}\n  Descripción: {pp['description']}\n\n"

            system_prompt = "Eres un analista experto en modelos de negocio digitales. Tu tarea es clasificar la transcripción de un video contra una lista ESTÁTICA de problemas (Pain Points) del mercado latinoamericano.\n\nDebes responder EXCLUSIVAMENTE en JSON válido. No agregues texto adicional."

            reclassified = 0
            errors = []

            for t in transcriptions.data:
                video_id = t["video_id"]
                transcript_text = t["full_text"][:15000]

                user_prompt = f"""Analiza la siguiente transcripción de un video de emprendimiento y extrae la información solicitada haciendo MATCH con los Pain Points proporcionados.

TRANSCRIPCIÓN:
{transcript_text}

PAIN POINTS DISPONIBLES (GROUND TRUTH):
{pp_context}

INSTRUCCIONES:
1. Identifica el modelo de negocio principal y fuente de ingresos.
2. Identifica el cliente objetivo.
3. CLASIFICACIÓN MULTI-LABEL: Selecciona cuáles de los "Pain Points Disponibles" ayuda a resolver o aborda este modelo de negocio.
4. Para cada Pain Point seleccionado, asigna un porcentaje de relevancia (0-100) y una breve justificación (reasoning) de por qué hace match.

REGLAS IMPORTANTES:
- Usa EXACTAMENTE los IDs de los Pain Points proporcionados. No inventes problemas nuevos.
- Si el video no aborda ninguno de los problemas, deja la lista de "latam_pain_points" vacía [].
- Toda la respuesta DEBE estar en ESPAÑOL.

FORMATO DE RESPUESTA:
{{
  "business_model": {{ "type": "string o null", "description": "string o null" }},
  "revenue_stream": {{ "type": "string o null", "description": "string o null" }},
  "target_customer": {{ "type": "string o null", "description": "string o null" }},
  "latam_pain_points": [
    {{
      "pain_point_id": "uuid del pain point",
      "pain_point_name": "Nombre del pain point",
      "relevance_score": 85,
      "reasoning": "Justificación concreta de por qué este negocio resuelve este dolor específico basado en la transcripción."
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

                    pps = extracted.get("latam_pain_points", [])
                    avg_relevance = 0
                    if pps and isinstance(pps, list) and len(pps) > 0:
                        total_score = sum(pp.get("relevance_score", 0) for pp in pps if isinstance(pp, dict))
                        avg_relevance = int(total_score / len(pps))

                    sb.table("video_classifications").insert({
                        "video_id": video_id,
                        "business_model": b_model_type,
                        "key_insights": extracted,
                        "latam_relevance_score": avg_relevance,
                        "model_used": payload["model"],
                        "prompt_version": "v2_multilabel"
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
