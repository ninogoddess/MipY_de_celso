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
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))
            
            messages = body.get("messages", [])

            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
            OPENROUTER_API_KEY = os.environ.get("DEEPSEEK_KEY")

            if not SUPABASE_URL or not SUPABASE_KEY:
                self._send(500, {"error": "Faltan credenciales de Supabase"})
                return

            sb = create_client(SUPABASE_URL, SUPABASE_KEY)

            # Obtener resumen de mercado (Pain points)
            market_summary = ""
            try:
                ms_resp = sb.table("latam_market_summary").select("summary_text").execute()
                if ms_resp.data:
                    market_summary = ms_resp.data[0]["summary_text"]
            except Exception:
                pass # Si la tabla aun no existe o falla, ignorar

            # System Prompt maestro
            system_prompt = f"""You are an AI system embedded in a product that helps users discover and build digital business opportunities in LATAM.

Your role is to construct a dynamic user profile using the RPM (Rapid Planning Method) framework by Tony Robbins, through a natural, conversational chat.

CORE OBJECTIVE: Extract R (Results) and P (Purpose). Then, using those + a database of LATAM pain points, generate M (Massive Action Plan) yourself using reasoning.

IMPORTANT CONSTRAINT: DO NOT ask the user explicitly for “Massive Action Plan” at the beginning. Extract R and P.
IMPORTANT: Speak in Spanish naturally. Ask ONE question at a time. Adapt based on user responses. Push for clarity.

CURRENT LATAM MARKET PAIN POINTS (Use this for Contextual Enrichment and Phase 4/5):
{market_summary[:3000] if market_summary else "No hay contexto de mercado disponible aun."}

FINAL OUTPUT FORMAT: When you have gathered enough information, output the final structured JSON EXACTLY as requested in the instructions, wrapped in ```json ... ``` tags. NEVER output JSON until enough information is gathered."""

            # Preparar payload
            api_messages = [{"role": "system", "content": system_prompt}] + messages
            
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "openrouter/free",
                "messages": api_messages
            }

            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            
            # Fallback OpenAI
            if response.status_code != 200:
                OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
                if response.status_code == 429 and OPENAI_API_KEY:
                    headers_oai = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
                    payload["model"] = "gpt-4o-mini"
                    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers_oai, json=payload)
                    if response.status_code != 200:
                        self._send(500, {"error": f"Fallo OpenRouter y OpenAI Fallback: {response.text}"})
                        return
                else:
                    self._send(500, {"error": f"Error de OpenRouter: {response.text}"})
                    return
                
            result_data = response.json()
            reply_text = result_data["choices"][0]["message"]["content"]

            # Intentar detectar JSON final
            json_match = re.search(r'```json(.*?)```', reply_text, re.DOTALL)
            is_final = False
            profile_json = None
            if json_match:
                try:
                    profile_json = json.loads(json_match.group(1).strip())
                    if "rpm_profile" in profile_json:
                        is_final = True
                        
                        # Obtener o crear user_profile dummy
                        u_resp = sb.table("user_profiles").select("id").limit(1).execute()
                        user_id = None
                        if u_resp.data:
                            user_id = u_resp.data[0]["id"]
                        else:
                            u_insert = sb.table("user_profiles").insert({"email": "demo@mipylatam.com", "name": "Emprendedor"}).execute()
                            user_id = u_insert.data[0]["id"]
                            
                        # Guardar en DB
                        sb.table("rpm_profiles").insert({
                            "user_id": user_id,
                            "resources": profile_json.get("rpm_profile", {}).get("constraints", {}),
                            "process": profile_json.get("massive_action_plan", {}),
                            "market": profile_json.get("pain_point_match", []),
                            "is_active": True
                        }).execute()
                except Exception as e:
                    print("Error parsing final JSON", e)

            self._send(200, {
                "reply": reply_text.replace(json_match.group(0), "") if is_final and json_match else reply_text,
                "is_final": is_final,
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
