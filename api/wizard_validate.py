import os
import json
import requests
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        """Validates a step of the RPM wizard to ensure semantic depth."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            step = data.get("step") # 'R', 'P', or 'M'
            answer = data.get("answer", "").strip()

            if not step or not answer:
                self._send(400, {"error": "Faltan datos (step o answer)"})
                return

            OPENROUTER_API_KEY = os.environ.get("DEEPSEEK_KEY")
            if not OPENROUTER_API_KEY:
                self._send(500, {"error": "Falta DEEPSEEK_KEY"})
                return

            # Definimos el contexto según el paso
            step_context = ""
            if step == 'R':
                step_context = "Resultados (R): Buscamos objetivos financieros concretos, horizonte de tiempo, tipo de negocio y dedicación."
            elif step == 'P':
                step_context = "Propósito (P): Buscamos motivaciones emocionales profundas, urgencia, por qué importa, y el dolor personal que resuelve."
            elif step == 'M':
                step_context = "Massive Action Plan (M): Buscamos capital real disponible, tiempo semanal, habilidades técnicas o blandas, y nivel de aversión al riesgo."

            system_prompt = f"""Eres un Coach Estricto de Negocios. Tu trabajo es evaluar la respuesta de un emprendedor para la etapa '{step_context}' del framework RPM.
Debes determinar si la respuesta es lo suficientemente detallada, concreta y accionable.
Si la respuesta es muy corta, ambigua o irreal (ej: "quiero ganar dinero", "ser feliz", "mucho éxito"), debes RECHAZARLA y proporcionar una pregunta o feedback corto y directo para que profundice.
Si la respuesta es detallada y útil, debes ACEPTARLA.

Responde ÚNICAMENTE en este formato JSON estricto:
{{
  "is_valid": true o false,
  "feedback": "Tu mensaje explicativo o pregunta si is_valid es false. Si es true, pon null o 'Perfecto'."
}}"""

            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "openrouter/free",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Respuesta del usuario:\n{answer}"}
                ]
            }

            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            
            # Fallback a OpenAI si falla
            if response.status_code != 200:
                OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
                if response.status_code == 429 and OPENAI_API_KEY:
                    headers_oai = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
                    payload["model"] = "gpt-4o-mini"
                    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers_oai, json=payload)
                    if response.status_code != 200:
                        self._send(500, {"error": "Error en LLM (Fallback failed)"})
                        return
                else:
                    self._send(500, {"error": "Error en API OpenRouter"})
                    return
                
            result_data = response.json()
            content = result_data["choices"][0]["message"]["content"]
            content = content.replace("```json", "").replace("```", "").strip()
            
            try:
                validation = json.loads(content)
            except:
                # Si el LLM falla al parsear, aceptamos por defecto para no bloquear la UX.
                validation = {"is_valid": True, "feedback": None}

            self._send(200, validation)

        except Exception as e:
            self._send(500, {"error": str(e)})

    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
