import os
import json
import requests
import re
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
        """Process the wizard form answers through LLM and save structured RPM profile."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))

            raw_answers = body.get("answers", {})

            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
            OPENROUTER_API_KEY = os.environ.get("DEEPSEEK_KEY")

            if not SUPABASE_URL or not SUPABASE_KEY:
                self._send(500, {"error": "Faltan credenciales de Supabase"})
                return

            sb = create_client(SUPABASE_URL, SUPABASE_KEY)

            # Get market summary for context
            market_summary = ""
            try:
                ms_resp = sb.table("latam_market_summary").select("summary_text").execute()
                if ms_resp.data:
                    market_summary = ms_resp.data[0]["summary_text"][:3000]
            except:
                pass

            # Get pain points for matching
            pain_points_text = ""
            try:
                pp_resp = sb.table("latam_pain_points").select("description, evidence, category, impact_level").limit(50).execute()
                if pp_resp.data:
                    for i, pp in enumerate(pp_resp.data):
                        pain_points_text += f"{i+1}. [{pp.get('category','General')}] {pp['description']} (Impacto: {pp.get('impact_level','Medium')})\n"
            except:
                pass

            system_prompt = """Eres un estratega de negocios experto en LATAM. Recibirás las respuestas de un emprendedor que completó un formulario RPM (Rapid Planning Method).

Tu tarea es:
1. Analizar y estructurar sus respuestas en un perfil RPM profesional
2. Cruzar su perfil con los pain points LATAM disponibles
3. Generar un Massive Action Plan (MAP) personalizado

RESPONDE EXCLUSIVAMENTE en JSON válido con esta estructura:
{
  "rpm_profile": {
    "results": {
      "goal": "Meta principal sintetizada",
      "timeline": "Línea temporal",
      "income_target": "Meta de ingresos",
      "business_type": "Tipo de negocio que busca",
      "commitment_level": "Nivel de compromiso"
    },
    "purpose": {
      "core_motivation": "Motivación central",
      "emotional_drivers": ["Lista de drivers emocionales"],
      "fear_if_not_achieved": "Miedo principal",
      "beneficiaries": ["Quiénes se benefician"]
    },
    "constraints": {
      "time_per_week": "Horas disponibles",
      "skills": ["Habilidades identificadas"],
      "resources": ["Recursos disponibles"],
      "risk_tolerance": "Tolerancia al riesgo",
      "experience_level": "Nivel de experiencia"
    }
  },
  "pain_point_match": [
    {
      "category": "Categoría",
      "problem": "Problema del mercado",
      "relevance_score": "High/Medium/Low",
      "reasoning": "Por qué encaja con este perfil"
    }
  ],
  "massive_action_plan": {
    "opportunity": "Oportunidad principal identificada",
    "business_model": "Modelo de negocio recomendado",
    "steps": ["Paso 1", "Paso 2", "..."],
    "priorities": ["Prioridad 1", "Prioridad 2"],
    "weekly_execution": "Plan semanal sugerido",
    "learning_path": ["Qué aprender primero"],
    "mvp_definition": "Definición del MVP/MVT"
  },
  "profile_summary": "Resumen ejecutivo de 2-3 párrafos del perfil completo"
}

IMPORTANTE: Responde en español. No inventes datos que no estén en las respuestas."""

            user_prompt = f"""RESPUESTAS DEL USUARIO AL WIZARD RPM:

--- PASO 1: RESULTADOS (R) ---
Metas: {raw_answers.get('results_goals', 'No respondido')}
Ingresos objetivo: {raw_answers.get('results_income', 'No respondido')}
Línea temporal: {raw_answers.get('results_timeline', 'No respondido')}
Tipo de negocio: {raw_answers.get('results_business_type', 'No respondido')}

--- PASO 2: PROPÓSITO (P) ---
Motivación principal: {raw_answers.get('purpose_motivation', 'No respondido')}
¿Qué pasa si no lo logras?: {raw_answers.get('purpose_fear', 'No respondido')}
¿A quién más impacta?: {raw_answers.get('purpose_beneficiaries', 'No respondido')}

--- PASO 3: MERCADO Y RECURSOS (M) ---
Habilidades: {raw_answers.get('market_skills', 'No respondido')}
Tiempo disponible por semana: {raw_answers.get('market_time', 'No respondido')}
Recursos (dinero, herramientas, contactos): {raw_answers.get('market_resources', 'No respondido')}
Experiencia previa: {raw_answers.get('market_experience', 'No respondido')}
Tolerancia al riesgo: {raw_answers.get('market_risk', 'No respondido')}

--- CONTEXTO DE MERCADO (PAIN POINTS LATAM DISPONIBLES) ---
{pain_points_text if pain_points_text else 'No hay pain points disponibles aún.'}

--- RESUMEN ESTRATÉGICO DEL MERCADO ---
{market_summary if market_summary else 'No disponible.'}

Procesa estas respuestas y genera el perfil RPM estructurado completo."""

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
                OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
                if response.status_code == 429 and OPENAI_API_KEY:
                    headers_oai = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
                    payload["model"] = "gpt-4o-mini"
                    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers_oai, json=payload)
                    if response.status_code != 200:
                        self._send(500, {"error": f"Fallo OpenRouter y OpenAI: {response.text}"})
                        return
                else:
                    self._send(500, {"error": f"Error de OpenRouter: {response.text}"})
                    return

            result_data = response.json()
            reply_text = result_data["choices"][0]["message"]["content"]

            # Parse JSON from response
            reply_text_clean = reply_text.replace("```json", "").replace("```", "").strip()
            try:
                profile_json = json.loads(reply_text_clean)
            except:
                # Try to find JSON in the text
                json_match = re.search(r'\{.*\}', reply_text_clean, re.DOTALL)
                if json_match:
                    profile_json = json.loads(json_match.group(0))
                else:
                    self._send(500, {"error": "El LLM no devolvió un JSON válido", "raw": reply_text[:500]})
                    return

            # Get or create user profile
            u_resp = sb.table("user_profiles").select("id").limit(1).execute()
            user_id = None
            if u_resp.data:
                user_id = u_resp.data[0]["id"]
            else:
                u_insert = sb.table("user_profiles").insert({"email": "demo@mipylatam.com", "display_name": "Emprendedor"}).execute()
                user_id = u_insert.data[0]["id"]

            # Deactivate previous profiles
            sb.table("rpm_profiles").update({"is_active": False}).eq("user_id", user_id).eq("is_active", True).execute()

            # Save new profile
            sb.table("rpm_profiles").insert({
                "user_id": user_id,
                "resources": profile_json.get("rpm_profile", {}).get("constraints", {}),
                "process": profile_json.get("massive_action_plan", {}),
                "market": profile_json.get("pain_point_match", []),
                "raw_answers": raw_answers,
                "ai_interpretation": profile_json,
                "is_active": True
            }).execute()

            self._send(200, {
                "message": "Perfil RPM procesado y guardado exitosamente.",
                "profile": profile_json
            })

        except Exception as e:
            self._send(500, {"error": str(e)})

    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
