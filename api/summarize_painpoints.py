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

            if not SUPABASE_URL or not SUPABASE_KEY:
                self._send(500, {"error": "Faltan credenciales de Supabase"})
                return

            sb = create_client(SUPABASE_URL, SUPABASE_KEY)

            # Extraer todos los pain points
            pp_resp = sb.table("latam_pain_points").select("description, evidence").execute()
            if not pp_resp.data:
                self._send(200, {"message": "No hay pain points para resumir."})
                return

            # Preparar el texto para el LLM
            pain_points_text = ""
            for i, pp in enumerate(pp_resp.data):
                pain_points_text += f"{i+1}. Problema: {pp['description']}\n   Evidencia LATAM: {pp['evidence']}\n\n"

            system_prompt = "Eres un estratega de negocios experto en LATAM. Tu tarea es analizar una lista cruda de pain points extraídos de casos de éxito y consolidarlos en un único resumen estructurado y estratégico del mercado. Identifica patrones, categoriza las oportunidades principales y explica brevemente por qué el mercado latinoamericano es vulnerable o propicio para estas soluciones."
            
            user_prompt = f"Aquí tienes los pain points extraídos:\n\n{pain_points_text[:15000]}\n\nPor favor, genera un resumen estratégico del mercado. (Solo texto en formato Markdown, estructurado con títulos)."

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
            
            # Lógica de Fallback a OpenAI si falla OpenRouter o hay límite 429
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
            summary_content = result_data["choices"][0]["message"]["content"]

            # Borrar resumen anterior si existe
            sb.table("latam_market_summary").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

            # Insertar nuevo resumen
            sb.table("latam_market_summary").insert({
                "summary_text": summary_content
            }).execute()

            self._send(200, {
                "message": "Resumen actualizado exitosamente.",
                "summary": summary_content
            })

        except Exception as e:
            self._send(500, {"error": str(e)})

    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
