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
        """Unified Wizard Engine: validation, chat, profile processing."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))

            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
            OPENROUTER_API_KEY = os.environ.get("DEEPSEEK_KEY")
            sb = create_client(SUPABASE_URL, SUPABASE_KEY)

            path = self.path.split('?')[0]

            if "validate" in path:
                self._handle_validate(body, OPENROUTER_API_KEY)
            elif "chat" in path:
                self._handle_chat(body, sb, OPENROUTER_API_KEY)
            elif "process" in path:
                self._handle_process(body, sb, OPENROUTER_API_KEY)
            else:
                self._send(404, {"error": "Endpoint no encontrado en Wizard Engine"})

        except Exception as e:
            self._send(500, {"error": str(e)})

    # ------------------------------------------------------------------
    # /api/wizard_validate
    # ------------------------------------------------------------------
    def _handle_validate(self, body, api_key):
        user_input = body.get("user_input", "")

        system_prompt = (
            "Eres un 'Validator' del Wizard RPM. Analiza la respuesta del usuario.\n"
            "Si la respuesta es muy corta o vacia (ej: 'quiero dinero', 'no se'), responde:\n"
            '{"valid": false, "feedback": "explicacion breve y peticion de mas detalle"}\n'
            "Si la respuesta es buena responde:\n"
            '{"valid": true, "feedback": ""}'
        )

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "openrouter/free",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Respuesta del usuario: {user_input}"}
            ],
            "response_format": {"type": "json_object"}
        }
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload, timeout=30
        )
        self._send(200, response.json()["choices"][0]["message"]["content"])

    # ------------------------------------------------------------------
    # /api/wizard_process — generate the structured RPM profile
    # ------------------------------------------------------------------
    def _handle_process(self, body, sb, api_key):
        # Accept both 'answers' (frontend) and 'responses' (legacy)
        answers = body.get("answers") or body.get("responses") or {}

        if not answers:
            self._send(400, {"error": "No se recibieron respuestas del wizard"})
            return

        # Pull current pain points so the LLM can do a real market match
        pain_points_context = []
        try:
            pp_resp = sb.table("latam_pain_points").select(
                "description, category, impact_level"
            ).limit(25).execute()
            for pp in pp_resp.data or []:
                pain_points_context.append({
                    "name": pp.get("description", ""),
                    "category": pp.get("category", ""),
                    "impact": pp.get("impact_level", "")
                })
        except Exception:
            pass  # Pain points are optional context

        system_prompt = (
            "Eres el 'RPM Profile Architect' especializado en el mercado LATAM. "
            "Tu trabajo es analizar las respuestas del wizard y producir un perfil "
            "RPM (Resultados-Proposito-Mercado) ESTRUCTURADO y completo.\n\n"
            "REGLAS CRITICAS:\n"
            "1. Responde EXCLUSIVAMENTE con un JSON valido (sin texto extra, sin markdown).\n"
            "2. NO dejes campos vacios. Si una respuesta es ambigua, infiere lo mas razonable.\n"
            "3. Todos los strings en espanol y concisos.\n"
            "4. Los arrays deben tener entre 3 y 6 elementos cortos (1-4 palabras cada uno).\n"
            "5. Para market_match, usa SOLO los pain points proporcionados en el contexto.\n\n"
            "ESQUEMA EXACTO requerido:\n"
            "{\n"
            '  "profile_summary": "Resumen ejecutivo en 2-3 oraciones del perfil del usuario",\n'
            '  "rpm_profile": {\n'
            '    "goal_type": "Tipo de meta concisa, ej: SaaS B2B, E-commerce, Consultoria",\n'
            '    "financial_goal": "Meta financiera concreta, ej: $3,000 USD/mes en 12 meses",\n'
            '    "time_commitment": "Tiempo disponible, ej: 20 hrs/semana",\n'
            '    "core_purpose": "El WHY del usuario en una oracion",\n'
            '    "skills": ["habilidad1", "habilidad2", "habilidad3"],\n'
            '    "business_preferences": ["preferencia1", "preferencia2", "preferencia3"],\n'
            '    "constraints": ["restriccion o recurso 1", "restriccion 2", "recurso 3"]\n'
            "  },\n"
            '  "ai_interpretation": {\n'
            '    "risk_profile": "Bajo | Medio | Alto",\n'
            '    "market_fit": "Analisis del encaje del perfil con el mercado LATAM en 2 oraciones"\n'
            "  },\n"
            '  "market_match": [\n'
            '    {"pain_point": "nombre exacto del pain point", "relevance": "High | Medium | Low", "reasoning": "por que encaja en una oracion"}\n'
            "  ],\n"
            '  "massive_action_plan": {\n'
            '    "recommended_model": "Modelo de negocio recomendado, ej: SaaS Suscripcion",\n'
            '    "steps": ["paso 1 concreto y accionable", "paso 2", "paso 3", "paso 4", "paso 5"]\n'
            "  }\n"
            "}"
        )

        user_content = (
            "RESPUESTAS DEL USUARIO (Wizard RPM):\n"
            f"{json.dumps(answers, ensure_ascii=False, indent=2)}\n\n"
            "PAIN POINTS LATAM DISPONIBLES (usa solo estos para market_match):\n"
            f"{json.dumps(pain_points_context, ensure_ascii=False, indent=2)}"
        )

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "openrouter/free",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.4
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers, json=payload, timeout=90
        )

        if response.status_code != 200:
            raise Exception(f"Error de LLM (OpenRouter): {response.text}")

        raw_content = response.json()["choices"][0]["message"]["content"]

        # Robust JSON parsing
        try:
            profile_data = json.loads(raw_content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown fences if present
            cleaned = raw_content.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
                cleaned = cleaned.strip()
            profile_data = json.loads(cleaned)

        # Ensure all expected keys exist with safe defaults
        profile_data = self._ensure_complete_profile(profile_data, answers)

        # Get or create user
        u_resp = sb.table("user_profiles").select("id").limit(1).execute()
        if u_resp.data:
            user_id = u_resp.data[0]["id"]
        else:
            u_insert = sb.table("user_profiles").insert({
                "email": "demo@mipylatam.com",
                "display_name": "Emprendedor Demo"
            }).execute()
            user_id = u_insert.data[0]["id"]

        # Deactivate previous profiles
        sb.table("rpm_profiles").update({"is_active": False}).eq("user_id", user_id).execute()

        rpm_core = profile_data.get("rpm_profile", {})

        # Insert new profile with raw_answers preserved
        sb.table("rpm_profiles").insert({
            "user_id": user_id,
            "resources": rpm_core.get("constraints", []),
            "process": profile_data.get("massive_action_plan", {}),
            "market": rpm_core.get("skills", []),
            "raw_answers": answers,
            "ai_interpretation": profile_data,
            "is_active": True
        }).execute()

        self._send(200, profile_data)

    # ------------------------------------------------------------------
    # Ensure all keys required by the frontend exist
    # ------------------------------------------------------------------
    def _ensure_complete_profile(self, data, answers):
        if not isinstance(data, dict):
            data = {}

        # rpm_profile
        rpm = data.get("rpm_profile") or {}
        rpm.setdefault("goal_type", answers.get("results_business_type", "Por definir"))
        rpm.setdefault("financial_goal", answers.get("results_income", "Por definir"))
        rpm.setdefault("time_commitment", answers.get("market_time", "Por definir"))
        rpm.setdefault("core_purpose", answers.get("purpose_motivation", "Por definir"))

        if not isinstance(rpm.get("skills"), list) or not rpm.get("skills"):
            raw_skills = answers.get("market_skills", "")
            rpm["skills"] = [s.strip() for s in raw_skills.split(",") if s.strip()] or ["Por definir"]

        if not isinstance(rpm.get("business_preferences"), list) or not rpm.get("business_preferences"):
            raw_pref = answers.get("results_business_type", "")
            rpm["business_preferences"] = [s.strip() for s in raw_pref.split(",") if s.strip()] or ["Por definir"]

        if not isinstance(rpm.get("constraints"), list) or not rpm.get("constraints"):
            raw_res = answers.get("market_resources", "")
            rpm["constraints"] = [s.strip() for s in raw_res.split(",") if s.strip()] or ["Por definir"]

        data["rpm_profile"] = rpm

        # ai_interpretation
        ai = data.get("ai_interpretation") or {}
        ai.setdefault("risk_profile", "Medio")
        ai.setdefault("market_fit", "Perfil con potencial en el mercado LATAM.")
        data["ai_interpretation"] = ai

        # profile_summary
        if not data.get("profile_summary"):
            data["profile_summary"] = (
                f"Emprendedor con perfil orientado a {rpm['goal_type']}, "
                f"meta financiera de {rpm['financial_goal']}, "
                f"y enfoque en {', '.join(rpm['skills'][:3])}."
            )

        # market_match
        if not isinstance(data.get("market_match"), list):
            data["market_match"] = []

        # massive_action_plan
        plan = data.get("massive_action_plan")
        if isinstance(plan, list):
            # Legacy array format - upgrade to object
            data["massive_action_plan"] = {
                "recommended_model": rpm["goal_type"],
                "steps": [str(s) for s in plan if s]
            }
        elif isinstance(plan, dict):
            plan.setdefault("recommended_model", rpm["goal_type"])
            if not isinstance(plan.get("steps"), list) or not plan.get("steps"):
                plan["steps"] = [
                    "Validar el problema con 10 entrevistas a clientes potenciales",
                    "Construir un MVP minimo en 4 semanas",
                    "Lanzar landing page para captar leads",
                    "Iterar segun feedback de primeros usuarios",
                    "Definir modelo de monetizacion y precios"
                ]
            data["massive_action_plan"] = plan
        else:
            data["massive_action_plan"] = {
                "recommended_model": rpm["goal_type"],
                "steps": [
                    "Validar el problema con 10 entrevistas",
                    "Construir un MVP minimo",
                    "Lanzar landing page",
                    "Iterar con feedback real",
                    "Definir monetizacion"
                ]
            }

        return data

    # ------------------------------------------------------------------
    def _handle_chat(self, body, sb, api_key):
        self._send(200, {"message": "Chat endpoint unified"})

    # ------------------------------------------------------------------
    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        if isinstance(data, str):
            self.wfile.write(data.encode('utf-8'))
        else:
            self.wfile.write(json.dumps(data).encode('utf-8'))
