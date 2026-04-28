import os
import json
from http.server import BaseHTTPRequestHandler
from supabase import create_client

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

            if not SUPABASE_URL or not SUPABASE_KEY:
                self._send(500, {"error": "Faltan credenciales de Supabase"})
                return

            sb = create_client(SUPABASE_URL, SUPABASE_KEY)

            videos = sb.table("videos").select("id", count="exact").execute()
            classifications = sb.table("video_classifications").select("id", count="exact").execute()
            pain_points = sb.table("latam_pain_points").select("id", count="exact").execute()
            solutions = sb.table("solutions").select("id", count="exact").execute()
            rpm = sb.table("rpm_profiles").select("id").eq("is_active", True).limit(1).execute()

            last_run_resp = sb.table("scraper_runs").select("*").order("started_at", desc=True).limit(1).execute()
            last_run = None
            if last_run_resp.data:
                r = last_run_resp.data[0]
                last_run = {
                    "status": r.get("status"),
                    "videos_found": r.get("videos_found", 0),
                    "videos_new": r.get("videos_new", 0),
                    "videos_updated": r.get("videos_updated", 0),
                    "completed_at": r.get("completed_at", "")
                }

            self._send(200, {
                "videos": videos.count or 0,
                "analyzed": classifications.count or 0,
                "pain_points": pain_points.count or 0,
                "solutions": solutions.count or 0,
                "rpm_completed": len(rpm.data) > 0,
                "last_run": last_run
            })
        except Exception as e:
            self._send(500, {"error": str(e)})

    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
