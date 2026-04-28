import os
import json
from http.server import BaseHTTPRequestHandler
from apify_client import ApifyClient
from supabase import create_client, Client
import urllib.parse

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_response(400, {"error": "El cuerpo de la petición está vacío"})
                return
                
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data)
            urls = body.get("urls", [])
            urls = [u.strip() for u in urls if u.strip()]
            
            if not urls:
                self._send_response(400, {"error": "No se proporcionaron URLs"})
                return

            # Vercel Environment Variables
            APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN")
            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
            
            if not APIFY_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
                self._send_response(500, {"error": "Faltan credenciales en las Environment Variables de Vercel"})
                return

            apify = ApifyClient(APIFY_TOKEN)
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            ACTOR_ID = "pintostudio/youtube-transcript-scraper"
            
            # Buscar el ID del canal Starter Story (por defecto)
            channel_resp = supabase.table("channels").select("id").eq("channel_id", "UCp6993wxpWPMfTso0IjxOaQ").execute()
            if not channel_resp.data:
                self._send_response(500, {"error": "Canal Starter Story no encontrado en la Base de Datos. Ejecuta la migracion 001."})
                return
            CHANNEL_UUID = channel_resp.data[0]["id"]

            # Iniciar registro en scraper_runs
            run_entry = supabase.table("scraper_runs").insert({
                "channel_id": CHANNEL_UUID, "status": "running", "videos_found": len(urls), "videos_new": 0, "videos_updated": 0
            }).execute()
            run_id = run_entry.data[0]["id"]

            results = []
            count_new = 0
            count_skipped = 0

            # Procesar cada URL
            for url in urls:
                try:
                    # Extraer ID
                    yt_video_id = url.split("v=")[1].split("&")[0] if "v=" in url else url.split("/")[-1].split("?")[0]
                    
                    # Chequear incremental
                    existing = supabase.table("videos").select("id").eq("video_id", yt_video_id).execute()
                    if existing.data:
                        results.append({"url": url, "status": "skipped", "message": "El video ya existía en la base de datos", "title": f"Video {yt_video_id}"})
                        count_skipped += 1
                        continue
                        
                    # Extraer de Apify
                    run = apify.actor(ACTOR_ID).call(run_input={"videoUrl": url})
                    items = list(apify.dataset(run["defaultDatasetId"]).iterate_items())
                    
                    if not items:
                        results.append({"url": url, "status": "error", "message": "Apify no devolvió transcripciones (probablemente no tiene subtítulos)", "title": yt_video_id})
                        continue
                        
                    raw_data = items[0]
                    title = raw_data.get("title", f"Video {yt_video_id}")
                    
                    # Parsear transcripción a full text
                    transcript_data = raw_data.get("data", raw_data.get("transcript", []))
                    if isinstance(transcript_data, list):
                        segments = [{"start": s.get("start", s.get("offset", 0)), "duration": s.get("duration", s.get("dur", 0)), "text": s.get("text", "")} for s in transcript_data if isinstance(s, dict)]
                        full_text = " ".join([s["text"] for s in segments])
                    elif isinstance(transcript_data, str):
                        full_text = transcript_data
                        segments = []
                    else:
                        full_text = str(transcript_data)
                        segments = []
                        
                    # Insertar Video
                    video_insert = supabase.table("videos").insert({
                        "channel_id": CHANNEL_UUID, "video_id": yt_video_id, "title": title,
                        "description": raw_data.get("description", ""), "url": url,
                        "published_at": raw_data.get("publishedAt", raw_data.get("published_at")),
                        "duration_seconds": raw_data.get("duration"),
                        "thumbnail_url": raw_data.get("thumbnail", raw_data.get("thumbnailUrl")),
                        "language": raw_data.get("language", raw_data.get("lang", "en")),
                    }).execute()
                    
                    video_uuid = video_insert.data[0]["id"]
                    
                    # Insertar Transcripción
                    supabase.table("transcriptions").insert({
                        "video_id": video_uuid, "language": raw_data.get("language", raw_data.get("lang", "en")),
                        "full_text": full_text, "segments": segments, "source": "apify_pinto_studio",
                    }).execute()
                    
                    results.append({"url": url, "status": "success", "title": title, "message": "Persistido en Supabase correctamente"})
                    count_new += 1
                except Exception as inner_e:
                    results.append({"url": url, "status": "error", "message": str(inner_e), "title": "Error en el pipeline"})

            # Actualizar estado final del scraper_run
            supabase.table("scraper_runs").update({
                "status": "completed", "videos_new": count_new, "videos_updated": count_skipped
            }).eq("id", run_id).execute()

            self._send_response(200, {"message": "Scraping finalizado", "results": results})

        except Exception as e:
            self._send_response(500, {"error": f"Error interno en Vercel: {str(e)}"})

    def _send_response(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
