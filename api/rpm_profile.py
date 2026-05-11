import os
import json
from http.server import BaseHTTPRequestHandler
from supabase import create_client

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, PUT, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Returns the active RPM profile if one exists."""
        try:
            sb = self._get_sb()
            if not sb:
                return

            resp = sb.table("rpm_profiles").select("*").eq("is_active", True).order("created_at", desc=True).limit(1).execute()
            if not resp.data:
                self._send(200, {"profile": None, "message": "No hay perfil RPM activo."})
                return

            profile = resp.data[0]
            self._send(200, {"profile": profile})

        except Exception as e:
            self._send(500, {"error": str(e)})

    def do_PUT(self):
        """Updates the active RPM profile with edited data."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))

            sb = self._get_sb()
            if not sb:
                return

            profile_id = body.get("id")
            if not profile_id:
                self._send(400, {"error": "Falta el ID del perfil."})
                return

            update_data = {}
            if "resources" in body:
                update_data["resources"] = body["resources"]
            if "process" in body:
                update_data["process"] = body["process"]
            if "market" in body:
                update_data["market"] = body["market"]
            if "raw_answers" in body:
                update_data["raw_answers"] = body["raw_answers"]
            if "ai_interpretation" in body:
                update_data["ai_interpretation"] = body["ai_interpretation"]

            if not update_data:
                self._send(400, {"error": "No hay datos para actualizar."})
                return

            sb.table("rpm_profiles").update(update_data).eq("id", profile_id).execute()
            self._send(200, {"message": "Perfil RPM actualizado exitosamente."})

        except Exception as e:
            self._send(500, {"error": str(e)})

    def _get_sb(self):
        SUPABASE_URL = os.environ.get("SUPABASE_URL")
        SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
        if not SUPABASE_URL or not SUPABASE_KEY:
            self._send(500, {"error": "Faltan credenciales de Supabase"})
            return None
        return create_client(SUPABASE_URL, SUPABASE_KEY)

    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
