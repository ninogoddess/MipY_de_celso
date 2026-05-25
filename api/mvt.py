import os
import json
from http.server import BaseHTTPRequestHandler
from supabase import create_client

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Fetches the current active MVT Validation and its evidence."""
        try:
            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

            if not SUPABASE_URL or not SUPABASE_KEY:
                self._send(500, {"error": "Faltan credenciales de Supabase"})
                return

            sb = create_client(SUPABASE_URL, SUPABASE_KEY)

            # 1. Obtener perfil activo del usuario (para asegurar permisos básicos o contexto)
            rpm_resp = sb.table("rpm_profiles").select("user_id").eq("is_active", True).execute()
            if not rpm_resp.data:
                self._send(400, {"error": "No hay un perfil RPM activo."})
                return
            
            user_id = rpm_resp.data[0]["user_id"]

            # 2. Buscar si hay un MVT activo. 
            # Como mvt_validations no tiene user_id directo, buscamos a través de solutions
            # Buscaremos la validación más reciente
            val_resp = sb.table("mvt_validations").select("*, solutions!inner(user_id, title, description, justification)").eq("solutions.user_id", user_id).order("created_at", desc=True).limit(1).execute()
            
            if not val_resp.data:
                self._send(200, {"validation": None})
                return
                
            validation = val_resp.data[0]
            
            # 3. Obtener evidencia
            ev_resp = sb.table("mvt_evidence").select("*").eq("validation_id", validation["id"]).order("created_at", desc=True).execute()
            
            self._send(200, {
                "validation": validation,
                "evidence": ev_resp.data
            })

        except Exception as e:
            self._send(500, {"error": str(e)})

    def do_POST(self):
        """Handles starting MVT, adding evidence, and making decisions."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))

            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
            sb = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            action = body.get("action")

            if action == "start":
                solution_id = body.get("solution_id")
                if not solution_id:
                    self._send(400, {"error": "Se requiere solution_id"})
                    return
                
                # Check if validation already exists
                check_resp = sb.table("mvt_validations").select("id").eq("solution_id", solution_id).execute()
                if check_resp.data:
                    self._send(200, {"message": "Ya existe", "validation_id": check_resp.data[0]["id"]})
                    return

                # Create validation
                insert_resp = sb.table("mvt_validations").insert({
                    "solution_id": solution_id,
                    "total_conversations": 0,
                    "total_tests": 0,
                    "conversion_rate": 0,
                    "engagement_score": 0
                }).execute()
                
                # Update solution status
                sb.table("solutions").update({"status": "validating"}).eq("id", solution_id).execute()

                self._send(200, {"message": "MVT Iniciado", "validation_id": insert_resp.data[0]["id"]})

            elif action == "add_evidence":
                validation_id = body.get("validation_id")
                evidence_type = body.get("evidence_type", "note")
                content = body.get("content", "")
                source = body.get("source", "")
                outcome = body.get("outcome", "neutral")
                evidence_url = body.get("evidence_url", "")
                
                if not validation_id or not content:
                    self._send(400, {"error": "validation_id y content requeridos"})
                    return
                    
                sb.table("mvt_evidence").insert({
                    "validation_id": validation_id,
                    "evidence_type": evidence_type,
                    "content": content,
                    "source": source,
                    "outcome": outcome,
                    "evidence_url": evidence_url
                }).execute()
                
                # Update counters (simple simulation)
                val = sb.table("mvt_validations").select("*").eq("id", validation_id).execute()
                if val.data:
                    v = val.data[0]
                    updates = {}
                    if evidence_type == 'conversation':
                        updates["total_conversations"] = (v.get("total_conversations") or 0) + 1
                    elif evidence_type == 'test' or evidence_type == 'landing_page':
                        updates["total_tests"] = (v.get("total_tests") or 0) + 1
                    
                    if updates:
                        sb.table("mvt_validations").update(updates).eq("id", validation_id).execute()

                self._send(200, {"message": "Evidencia guardada exitosamente"})

            elif action == "decide":
                validation_id = body.get("validation_id")
                decision = body.get("decision") # Pivot, Proceed, Kill
                
                if not validation_id or not decision:
                    self._send(400, {"error": "Faltan parámetros"})
                    return
                    
                sb.table("mvt_validations").update({"decision": decision}).eq("id", validation_id).execute()
                
                # We could also update the solution status to 'validated', 'rejected' etc.
                status_map = {
                    "Proceed": "validated",
                    "Pivot": "reviewing",
                    "Kill": "rejected"
                }
                
                val = sb.table("mvt_validations").select("solution_id").eq("id", validation_id).execute()
                if val.data:
                    sol_id = val.data[0]["solution_id"]
                    sb.table("solutions").update({"status": status_map.get(decision, "validating")}).eq("id", sol_id).execute()

                self._send(200, {"message": f"Decisión {decision} registrada."})

            else:
                self._send(400, {"error": "Acción no válida"})

        except Exception as e:
            self._send(500, {"error": str(e)})

    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
