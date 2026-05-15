import os
import json
import requests
from http.server import BaseHTTPRequestHandler
from supabase import create_client
import uuid

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        """Generates Business Solutions by matching the RPM Profile with the best Classified Videos."""
        try:
            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
            OPENROUTER_API_KEY = os.environ.get("DEEPSEEK_KEY")

            if not SUPABASE_URL or not SUPABASE_KEY or not OPENROUTER_API_KEY:
                self._send(500, {"error": "Faltan credenciales"})
                return

            sb = create_client(SUPABASE_URL, SUPABASE_KEY)

            # 1. Obtener perfil activo
            rpm_resp = sb.table("rpm_profiles").select("*, user_profiles(id)").eq("is_active", True).execute()
            if not rpm_resp.data:
                self._send(400, {"error": "No tienes un perfil RPM activo. Por favor completa el Wizard RPM primero."})
                return
            
            rpm_profile = rpm_resp.data[0]
            user_id = rpm_profile["user_id"]
            ai_interpretation = rpm_profile.get("ai_interpretation", {})

            # 2. Obtener mejores videos clasificados
            # Traer los de mayor score
            vid_resp = sb.table("video_classifications").select("*, videos(title, url)").order("latam_relevance_score", desc=True).limit(20).execute()
            
            if not vid_resp.data:
                self._send(400, {"error": "No hay videos clasificados aún. Por favor reclasifica algunos videos primero."})
                return

            # Preparar contexto de videos
            videos_context = ""
            for v in vid_resp.data:
                score = v.get("latam_relevance_score", 0)
                if score < 10:
                    continue
                v_title = v.get("videos", {}).get("title", "Desconocido")
                v_url = v.get("videos", {}).get("url", "")
                insights = json.dumps(v.get("key_insights", {}), ensure_ascii=False)
                videos_context += f"--- VIDEO ID: {v['video_id']} ---\n"
                videos_context += f"TÍTULO: {v_title}\n"
                videos_context += f"SCORE LATAM: {score}%\n"
                videos_context += f"INSIGHTS: {insights}\n\n"

            if not videos_context:
                self._send(400, {"error": "Los videos clasificados actuales tienen un score muy bajo. Reclasifica más videos."})
                return

            system_prompt = """Eres el 'Opportunity Matching Engine', un avanzado sistema de IA para emprendedores.
Tu objetivo es analizar el Perfil RPM del usuario (sus metas, recursos, habilidades y perfil de riesgo) y compararlo contra una lista de Videos Clasificados de negocios exitosos.

Debes seleccionar los 3 MEJORES negocios (basados en los videos) que hagan match perfecto con el perfil del usuario.
Para cada uno, debes generar una 'Business Solution' detallada que explique exactamente cómo el usuario debería implementar este negocio en LATAM.

RESPONDE EXCLUSIVAMENTE en JSON válido con la siguiente estructura:
{
  "solutions": [
    {
      "title": "Nombre atractivo para la oportunidad",
      "description": "Descripción clara del modelo adaptado al usuario",
      "source_videos": ["VIDEO_ID_DEL_CUAL_TE_INSPIRASTE"],
      "latam_adaptation": "Cómo se adapta exactamente a las condiciones de LATAM y a las restricciones del usuario",
      "rpm_fit_score": 95,
      "difficulty": "Low/Medium/High",
      "justification": "Por qué es el match perfecto para este usuario basándote en sus habilidades y recursos concretos."
    }
  ]
}

REGLAS IMPORTANTES:
- Selecciona exactamente 3 soluciones.
- El campo source_videos DEBE contener el ID exacto del video listado en el contexto.
- El rpm_fit_score debe ser un número entero entre 0 y 100.
- Todo debe estar en ESPAÑOL.
"""

            user_prompt = f"""PERFIL DEL USUARIO (RPM):
{json.dumps(ai_interpretation, ensure_ascii=False, indent=2)}

VIDEOS DISPONIBLES (NEGOCIOS DE REFERENCIA):
{videos_context}

Genera las 3 mejores soluciones de negocio para este usuario."""

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
            reply_text = result_data["choices"][0]["message"]["content"]

            reply_text_clean = reply_text.replace("```json", "").replace("```", "").strip()
            solutions_json = json.loads(reply_text_clean)
            generated_solutions = solutions_json.get("solutions", [])

            # Insertar en base de datos
            inserted_solutions = []
            for sol in generated_solutions:
                sol_insert = sb.table("solutions").insert({
                    "user_id": user_id,
                    "rpm_profile_id": rpm_profile["id"],
                    "title": sol.get("title", ""),
                    "description": sol.get("description", ""),
                    "latam_adaptation": sol.get("latam_adaptation", ""),
                    "rpm_fit_score": sol.get("rpm_fit_score", 0),
                    "difficulty": sol.get("difficulty", "Medium"),
                    "justification": sol.get("justification", ""),
                    "status": "generated"
                }).execute()
                
                new_sol_id = sol_insert.data[0]["id"]
                inserted_solutions.append(sol_insert.data[0])

                # Mapear source videos
                for vid in sol.get("source_videos", []):
                    try:
                        sb.table("solution_source_videos").insert({
                            "solution_id": new_sol_id,
                            "video_id": vid,
                            "relevance_note": "Match automático del motor IA"
                        }).execute()
                    except:
                        pass # Ignorar si el video_id no existe en la BD

            self._send(200, {
                "message": "Soluciones generadas exitosamente",
                "solutions": inserted_solutions
            })

        except Exception as e:
            self._send(500, {"error": str(e)})

    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
