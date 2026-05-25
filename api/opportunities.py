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
            vid_resp = sb.table("video_classifications").select("*, videos(title, url, thumbnail_url)").order("latam_relevance_score", desc=True).limit(30).execute()
            if not vid_resp.data:
                self._send(400, {"error": "No hay videos clasificados aún. Por favor reclasifica algunos videos primero."})
                return

            # Preparar contexto de videos
            videos_context = ""
            for v in vid_resp.data:
                score = v.get("latam_relevance_score", 0)
                if score < 5:
                    continue
                v_title = v.get("videos", {}).get("title", "Desconocido")
                v_url = v.get("videos", {}).get("url", "")
                v_thumb = v.get("videos", {}).get("thumbnail_url", "")
                insights = json.dumps(v.get("key_insights", {}), ensure_ascii=False)
                videos_context += f"--- VIDEO ID: {v['video_id']} ---\n"
                videos_context += f"TÍTULO: {v_title}\n"
                videos_context += f"URL: {v_url}\n"
                videos_context += f"THUMBNAIL: {v_thumb}\n"
                videos_context += f"SCORE LATAM: {score}%\n"
                videos_context += f"INSIGHTS: {insights}\n\n"

            # 3. Obtener Pain Points
            pp_resp = sb.table("latam_pain_points").select("*").limit(20).execute()
            pp_context = ""
            if pp_resp.data:
                for pp in pp_resp.data:
                    pp_context += f"- [{pp['impact_level']}] {pp['category']}: {pp.get('name', '')} - {pp['description']}\n"

            system_prompt = """Eres el 'Opportunity Matching Engine', un avanzado Principal AI Engineer + Product Strategist + Recommendation System Architect.
Tu objetivo es cruzar el Perfil RPM del usuario (sus metas, recursos, habilidades y riesgos) con una lista de Videos Clasificados de negocios reales y los Pain Points de LATAM.

DEBES GENERAR EXACTAMENTE 4 PROPUESTAS DE NEGOCIO DISTINTAS Y DINÁMICAS.
NO uses plantillas rígidas ni repitas la misma idea.
Si el RPM indica poco dinero, sugiere SaaS/Servicios. Si indica capital, sugiere operaciones o supply chain. Las 4 ideas deben atacar distintos ángulos.

RESPONDE EXCLUSIVAMENTE en JSON válido con la siguiente estructura (NO AGREGUES TEXTO FUERA DEL JSON):
{
  "solutions": [
    {
      "title": "Nombre corto y atractivo",
      "summary": "Descripción clara de la solución y por qué hace match con este RPM",
      "latam_pain_point": "Descripción breve del pain point resuelto",
      "pain_point_category": "Categoría (ej: Logística, Pagos, SaaS)",
      "regional_context": "Adaptación específica a LATAM",
      "why_now": "Por qué es el momento en LATAM",
      "business_model": "Modelo de monetización",
      "target_customer": "Cliente objetivo",
      "difficulty_score": 50,
      "rpm_fit_score": 95,
      "market_opportunity_score": 85,
      "execution_complexity": "Alta/Media/Baja",
      "required_skills": ["skill 1", "skill 2"],
      "estimated_startup_cost": "Bajo/Medio/Alto o cifra estimada",
      "time_to_validate": "Tiempo estimado (ej: 2 semanas)",
      "recommended_validation_method": "Método exacto MVT (Minimum Viable Test)",
      "related_videos": [
        {"id": "VIDEO_ID_EXACTO", "title": "TÍTULO DEL VIDEO", "url": "URL_DEL_VIDEO", "thumbnail": "URL_THUMBNAIL", "relevance": "Por qué inspiró esto"}
      ],
      "reasoning": "Por qué la IA conectó este modelo con este RPM específicamente",
      "main_risks": ["riesgo 1"],
      "competitive_advantages": ["ventaja 1"],
      "recommended_first_steps": ["paso 1", "paso 2", "paso 3"]
    }
  ]
}

REGLAS CRÍTICAS:
- GENERAR EXACTAMENTE 4 PROPUESTAS DIFERENTES.
- `related_videos` DEBE usar la información proporcionada en el contexto. El `id` debe ser el VIDEO_ID real.
- Todos los scores deben ser enteros entre 0 y 100.
"""

            user_prompt = f"""PERFIL DEL USUARIO (RPM):
{json.dumps(ai_interpretation, ensure_ascii=False, indent=2)}

PAIN POINTS LATAM DISPONIBLES:
{pp_context}

VIDEOS DISPONIBLES (NEGOCIOS INSPIRACIÓN):
{videos_context}

Genera las 4 mejores soluciones de negocio para este usuario en base a su RPM."""

            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            models_to_try = [
                "google/gemini-2.5-pro-exp:free",
                "meta-llama/llama-3.3-70b-instruct:free",
                "deepseek/deepseek-r1:free",
                "deepseek/deepseek-chat:free",
                "openrouter/auto"
            ]
            
            response = None
            for model_name in models_to_try:
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "response_format": { "type": "json_object" }
                }
                response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                if response.status_code == 200:
                    break
                    
            if not response or response.status_code != 200:
                self._send(500, {"error": f"Error de OpenRouter tras intentar varios modelos. Último error: {response.text}"})
                return

            result_data = response.json()
            reply_text = result_data["choices"][0]["message"]["content"]

            try:
                reply_text_clean = reply_text.replace("```json", "").replace("```", "").strip()
                solutions_json = json.loads(reply_text_clean)
                generated_solutions = solutions_json.get("solutions", [])
            except Exception as e:
                # Fallback if json parsing fails
                self._send(500, {"error": "El LLM no devolvió un JSON válido. Reintenta.", "details": str(e), "raw": reply_text})
                return

            # Insertar en base de datos
            inserted_solutions = []
            
            # Limpiar soluciones anteriores de este perfil para mantener limpieza (opcional)
            # sb.table("solutions").update({"status": "archived"}).eq("rpm_profile_id", rpm_profile["id"]).execute()

            for sol in generated_solutions:
                # Guardamos el payload COMPLETO como json en 'justification'
                # Y extraemos campos primarios para la tabla
                sol_insert = sb.table("solutions").insert({
                    "user_id": user_id,
                    "rpm_profile_id": rpm_profile["id"],
                    "title": sol.get("title", "Solución sin título"),
                    "description": sol.get("summary", ""),
                    "latam_adaptation": sol.get("latam_pain_point", ""),
                    "rpm_fit_score": sol.get("rpm_fit_score", 0),
                    "difficulty": str(sol.get("difficulty_score", 50)),
                    "justification": json.dumps(sol, ensure_ascii=False),
                    "status": "generated"
                }).execute()
                
                new_sol_id = sol_insert.data[0]["id"]
                sol["id"] = new_sol_id  # Inyectar id para el frontend
                inserted_solutions.append(sol)

                # Mapear source videos
                for vid in sol.get("related_videos", []):
                    try:
                        vid_id = vid.get("id")
                        if vid_id:
                            sb.table("solution_source_videos").insert({
                                "solution_id": new_sol_id,
                                "video_id": vid_id,
                                "relevance_note": vid.get("relevance", "Match IA")
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
