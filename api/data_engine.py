import os
import json
from http.server import BaseHTTPRequestHandler
from supabase import create_client

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Unified Data Engine to handle multiple informational endpoints and save Serverless Functions."""
        try:
            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
            if not SUPABASE_URL or not SUPABASE_KEY:
                self._send(500, {"error": "Faltan credenciales"})
                return

            sb = create_client(SUPABASE_URL, SUPABASE_KEY)
            
            # Simple routing based on path
            path = self.path.split('?')[0]
            
            # --- /api/stats ---
            if "stats" in path:
                videos = sb.table("videos").select("id", count="exact").execute()
                classifications = sb.table("video_classifications").select("id", count="exact").execute()
                pain_points = sb.table("latam_pain_points").select("id", count="exact").execute()
                solutions = sb.table("solutions").select("id", count="exact").execute()
                rpm = sb.table("rpm_profiles").select("id").eq("is_active", True).limit(1).execute()
                last_run_resp = sb.table("scraper_runs").select("*").order("started_at", desc=True).limit(10).execute()
                
                all_runs = []
                last_run = None
                if last_run_resp.data:
                    for r in last_run_resp.data:
                        all_runs.append({
                            "status": r.get("status"),
                            "videos_found": r.get("videos_found", 0),
                            "videos_new": r.get("videos_new", 0),
                            "videos_updated": r.get("videos_updated", 0),
                            "started_at": r.get("started_at", ""),
                            "completed_at": r.get("completed_at", "")
                        })
                    last_run = all_runs[0]

                self._send(200, {
                    "videos": videos.count or 0,
                    "analyzed": classifications.count or 0,
                    "pain_points": pain_points.count or 0,
                    "solutions": solutions.count or 0,
                    "rpm_completed": len(rpm.data) > 0,
                    "last_run": last_run,
                    "all_runs": all_runs
                })

            # --- /api/videos ---
            elif "videos" in path:
                videos_resp = sb.table("videos").select("*").order("created_at", desc=True).limit(50).execute()
                self._send(200, {"videos": videos_resp.data})

            # --- /api/classifications ---
            elif "classifications" in path:
                resp = sb.table("video_classifications").select("*, videos(title, url, video_id)").order("classified_at", desc=True).limit(50).execute()
                self._send(200, {"classifications": resp.data})

            # --- /api/painpoints ---
            elif "painpoints" in path:
                # Get pain points
                pp_resp = sb.table("latam_pain_points").select("*").order("name").execute()
                # Also get counts by category
                stats_resp = sb.table("latam_pain_points").select("category").execute()
                stats = {}
                for item in stats_resp.data:
                    cat = item["category"]
                    stats[cat] = stats.get(cat, 0) + 1
                
                self._send(200, {
                    "pain_points": pp_resp.data,
                    "stats": stats
                })

            # --- /api/rpm_profile ---
            elif "rpm_profile" in path:
                # Get the active RPM profile
                resp = sb.table("rpm_profiles").select("*").eq("is_active", True).order("created_at", desc=True).limit(1).execute()
                if resp.data:
                    self._send(200, {"profile": resp.data[0]})
                else:
                    self._send(404, {"error": "No hay perfil activo"})

            else:
                self._send(404, {"error": "Endpoint no encontrado en Data Engine"})

        except Exception as e:
            self._send(500, {"error": str(e)})

    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
