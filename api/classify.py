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
        try:
            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
            OPENROUTER_API_KEY = os.environ.get("DEEPSEEK_KEY")

            if not SUPABASE_URL or not SUPABASE_KEY or not OPENROUTER_API_KEY:
                self._send(500, {"error": "Faltan credenciales (Supabase o DEEPSEEK_KEY) en Vercel"})
                return

            sb = create_client(SUPABASE_URL, SUPABASE_KEY)

            # Paso 1: Obtener IDs ya clasificados
            cls_resp = sb.table("video_classifications").select("video_id").execute()
            classified_ids = [c["video_id"] for c in cls_resp.data] if cls_resp.data else []

            # Paso 2: Obtener transcripciones (sin límite tan restrictivo)
            query = sb.table("transcriptions").select("video_id, full_text").limit(500).execute()
            unclassified = None
            for t in query.data:
                if t["video_id"] not in classified_ids:
                    unclassified = t
                    break

            if not unclassified:
                self._send(200, {"message": "No hay videos pendientes de clasificacion", "status": "completed"})
                return

            transcript_text = unclassified["full_text"]
            video_id = unclassified["video_id"]
            
            # Recortar si es muy largo por velocidad y costos
            if len(transcript_text) > 15000:
                transcript_text = transcript_text[:15000]

            system_prompt = "Eres un analista experto en modelos de negocio digitales. Tu tarea es analizar transcripciones de videos de emprendedores y extraer información estructurada de forma precisa, concreta y verificable.\n\nDebes responder EXCLUSIVAMENTE en JSON válido. No agregues texto adicional."
            
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
- No uses lenguaje ambiguo
- IMPORTANTE: Toda la respuesta (valores del JSON, descripciones y pain points) DEBE estar redactada estrictamente en ESPAÑOL.

FORMATO DE RESPUESTA:
{{
  "business_model": {{ "type": "string o null", "description": "string o null" }},
  "revenue_stream": {{ "type": "string o null", "description": "string o null" }},
  "target_customer": {{ "type": "string o null", "description": "string o null" }},
  "latam_pain_points": [
    {{
      "pain_point": "Breve descripción del problema original",
      "latam_context_adaptation": "Justificación concreta de cómo y por qué este dolor aplica o se acentúa en el contexto de Latinoamérica"
    }}
  ],
  "confidence_score": 90
}}

VALIDACIÓN INTERNA (OBLIGATORIA):
Antes de responder: Verifica que cada campo tenga sentido lógico y no contradiga la transcripción. Si hay dudas baja el confidence_score.
Si la transcripción es irrelevante o incompleta, devuelve:
{{
  "business_model": null,
  "revenue_stream": null,
  "target_customer": null,
  "latam_pain_points": [],
  "confidence_score": 0
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

            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            if response.status_code != 200:
                self._send(500, {"error": f"Error de OpenRouter: {response.text}"})
                return
                
            result_data = response.json()
            content = result_data["choices"][0]["message"]["content"]
            
            # Limpiar posible markdown
            content = content.replace("```json", "").replace("```", "").strip()
            
            try:
                extracted = json.loads(content)
            except Exception as e:
                self._send(500, {"error": "El LLM no devolvio un JSON valido", "raw_content": content})
                return

            b_model_type = None
            if extracted.get("business_model") and isinstance(extracted["business_model"], dict):
                b_model_type = extracted["business_model"].get("type")
            elif isinstance(extracted.get("business_model"), str):
                b_model_type = extracted.get("business_model")

            # Guardamos en base de datos.
            sb.table("video_classifications").insert({
                "video_id": video_id,
                "business_model": b_model_type,
                "key_insights": extracted,
                "model_used": payload["model"],
                "prompt_version": "v1_hu_06"
            }).execute()

            # Insertamos explícitamente los Pain Points en su propia tabla para el Dashboard
            pain_points_array = extracted.get("latam_pain_points", [])
            if isinstance(pain_points_array, list):
                for pp in pain_points_array:
                    if isinstance(pp, dict) and pp.get("pain_point"):
                        sb.table("latam_pain_points").insert({
                            "description": pp.get("pain_point"),
                            "impact_level": "Medium",
                            "evidence": pp.get("latam_context_adaptation"),
                            "source_video_id": video_id
                        }).execute()

            self._send(200, {
                "message": "Clasificacion exitosa",
                "video_id": video_id,
                "extracted": extracted,
                "status": "success"
            })

        except Exception as e:
            self._send(500, {"error": str(e)})

    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
