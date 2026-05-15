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
        """Unified Wizard Engine to handle Chat, Validation, and Profile Processing."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))
            
            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
            OPENROUTER_API_KEY = os.environ.get("DEEPSEEK_KEY")
            sb = create_client(SUPABASE_URL, SUPABASE_KEY)

            path = self.path.split('?')[0]

            # --- /api/wizard_validate ---
            if "validate" in path:
                messages = body.get("messages", [])
                user_input = body.get("user_input", "")
                
                system_prompt = """Eres un 'Validator' del Wizard RPM. Tu tarea es analizar la respuesta del usuario para ver si tiene profundidad suficiente.
Si la respuesta es muy corta (ej: 'quiero dinero', 'no se') o vacia, debes responder con un JSON: {"valid": false, "feedback": "Una breve explicacion de por que no es valida y pedir mas detalle"}.
Si la respuesta es buena, responde: {"valid": true, "feedback": ""}."""

                headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
                payload = {
                    "model": "openrouter/free",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Respuesta del usuario: {user_input}"}
                    ],
                    "response_format": { "type": "json_object" }
                }
                response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                self._send(200, response.json()["choices"][0]["message"]["content"])

            # --- /api/wizard_chat (Legacy or future chat logic) ---
            elif "chat" in path:
                # Logic from wizard_chat.py
                self._handle_chat(body, sb, OPENROUTER_API_KEY)

            # --- /api/wizard_process (Phase 5) ---
            elif "process" in path:
                self._handle_process(body, sb, OPENROUTER_API_KEY)

            else:
                self._send(404, {"error": "Endpoint no encontrado en Wizard Engine"})

        except Exception as e:
            self._send(500, {"error": str(e)})

    def _handle_process(self, body, sb, api_key):
        responses = body.get("responses", {})
        
        system_prompt = """Eres el 'RPM Profile Architect'. Tu objetivo es procesar las respuestas del usuario y generar un Perfil RPM ESTRUCTURADO.
Responde EXCLUSIVAMENTE con un JSON que contenga:
{
  "rpm_profile": {
    "goal_type": "string",
    "financial_goal": "string",
    "core_purpose": "string",
    "constraints": ["string"],
    "skills": ["string"]
  },
  "massive_action_plan": ["paso 1", "paso 2", ...],
  "ai_interpretation": { "risk_profile": "string", "market_fit": "string" }
}"""

        user_content = f"RESPUESTAS DEL USUARIO:\n{json.dumps(responses, ensure_ascii=False, indent=2)}"
        
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "openrouter/free",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "response_format": { "type": "json_object" }
        }
        
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        result = response.json()["choices"][0]["message"]["content"]
        
        # Guardar en DB
        profile_data = json.loads(result)
        
        # Obtener user_id
        u_resp = sb.table("user_profiles").select("id").limit(1).execute()
        user_id = u_resp.data[0]["id"] if u_resp.data else None
        
        # Desactivar perfiles anteriores
        sb.table("rpm_profiles").update({"is_active": False}).eq("user_id", user_id).execute()

        # Insertar nuevo
        sb.table("rpm_profiles").insert({
            "user_id": user_id,
            "resources": profile_data.get("rpm_profile", {}).get("constraints", []),
            "process": profile_data.get("massive_action_plan", []),
            "market": profile_data.get("rpm_profile", {}).get("skills", []),
            "ai_interpretation": profile_data,
            "is_active": True
        }).execute()

        self._send(200, profile_data)

    def _handle_chat(self, body, sb, api_key):
        # Implementation of chat logic if needed, otherwise just proxy
        self._send(200, {"message": "Chat endpoint unified"})

    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        if isinstance(data, str):
            self.wfile.write(data.encode('utf-8'))
        else:
            self.wfile.write(json.dumps(data).encode('utf-8'))
