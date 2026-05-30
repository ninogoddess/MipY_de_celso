import os
import json
from http.server import BaseHTTPRequestHandler
from apify_client import ApifyClient
from supabase import create_client, Client


class handler(BaseHTTPRequestHandler):
    """
    CRON Endpoint — Automated weekly scraping of new Starter Story videos.
    
    This endpoint is called automatically by Vercel Cron Jobs (configured in vercel.json).
    It uses Apify's YouTube Channel Scraper to discover new videos from the channel,
    then processes only the ones not already in the database (incremental).
    
    Can also be triggered manually via GET request from the Settings page.
    """

    def do_GET(self):
        """Handles both Vercel Cron invocations and manual triggers from the UI."""
        try:
            APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN")
            SUPABASE_URL = os.environ.get("SUPABASE_URL")
            SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

            if not APIFY_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
                self._send(500, {"error": "Faltan credenciales (APIFY_API_TOKEN, SUPABASE_URL, SUPABASE_KEY)"})
                return

            apify = ApifyClient(APIFY_TOKEN)
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

            # 1. Get the Starter Story channel from DB
            channel_resp = supabase.table("channels").select("id, channel_id").eq("channel_id", "UCp6993wxpWPMfTso0IjxOaQ").execute()
            if not channel_resp.data:
                self._send(500, {"error": "Canal Starter Story no encontrado en la BD."})
                return

            CHANNEL_UUID = channel_resp.data[0]["id"]
            YT_CHANNEL_ID = channel_resp.data[0]["channel_id"]

            # 2. Get existing video_ids to skip (incremental)
            existing_resp = supabase.table("videos").select("video_id").eq("channel_id", CHANNEL_UUID).execute()
            existing_ids = set(v["video_id"] for v in existing_resp.data) if existing_resp.data else set()

            # 3. Use Apify to get the latest videos from the channel
            # We use the "bernardo/youtube-channel-scraper" or similar actor to list videos
            # Alternatively, use YouTube's RSS feed which is free and doesn't need Apify
            CHANNEL_RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={YT_CHANNEL_ID}"

            # Fetch RSS feed (free, no API key needed, gives last ~15 videos)
            import urllib.request
            import xml.etree.ElementTree as ET

            req = urllib.request.Request(CHANNEL_RSS_URL, headers={"User-Agent": "Mozilla/5.0"})
            response = urllib.request.urlopen(req, timeout=15)
            xml_content = response.read().decode("utf-8")

            # Parse RSS/Atom feed
            root = ET.fromstring(xml_content)
            ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015", "media": "http://search.yahoo.com/mrss/"}

            new_video_urls = []
            for entry in root.findall("atom:entry", ns):
                video_id_el = entry.find("yt:videoId", ns)
                if video_id_el is not None:
                    vid_id = video_id_el.text
                    if vid_id not in existing_ids:
                        new_video_urls.append(f"https://www.youtube.com/watch?v={vid_id}")

            if not new_video_urls:
                # Register a "no new videos" run
                supabase.table("scraper_runs").insert({
                    "channel_id": CHANNEL_UUID,
                    "status": "completed",
                    "videos_found": 0,
                    "videos_new": 0,
                    "videos_updated": 0
                }).execute()
                self._send(200, {
                    "message": "CRON ejecutado. No hay videos nuevos en el canal.",
                    "new_videos": 0,
                    "checked": len(existing_ids)
                })
                return

            # 4. Limit to max 5 per cron run (to stay within Vercel 60s timeout)
            urls_to_process = new_video_urls[:5]

            # 5. Register scraper run
            run_entry = supabase.table("scraper_runs").insert({
                "channel_id": CHANNEL_UUID,
                "status": "running",
                "videos_found": len(new_video_urls),
                "videos_new": 0,
                "videos_updated": 0
            }).execute()
            run_id = run_entry.data[0]["id"]

            # 6. Process each new video via Apify transcript scraper
            ACTOR_ID = "pintostudio/youtube-transcript-scraper"
            count_new = 0
            errors = []

            for url in urls_to_process:
                try:
                    yt_video_id = url.split("v=")[1].split("&")[0]

                    # Double-check incremental (race condition safety)
                    check = supabase.table("videos").select("id").eq("video_id", yt_video_id).execute()
                    if check.data:
                        continue

                    # Call Apify
                    run = apify.actor(ACTOR_ID).call(run_input={"videoUrl": url})
                    items = list(apify.dataset(run["defaultDatasetId"]).iterate_items())

                    if not items:
                        errors.append(f"No transcript for {yt_video_id}")
                        continue

                    raw_data = items[0]
                    title = raw_data.get("title", f"Video {yt_video_id}")

                    # Parse transcript
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

                    # Insert video
                    video_insert = supabase.table("videos").insert({
                        "channel_id": CHANNEL_UUID,
                        "video_id": yt_video_id,
                        "title": title,
                        "description": raw_data.get("description", ""),
                        "url": url,
                        "published_at": raw_data.get("publishedAt", raw_data.get("published_at")),
                        "duration_seconds": raw_data.get("duration"),
                        "thumbnail_url": raw_data.get("thumbnail", raw_data.get("thumbnailUrl")),
                        "language": raw_data.get("language", raw_data.get("lang", "en")),
                    }).execute()

                    video_uuid = video_insert.data[0]["id"]

                    # Insert transcription
                    supabase.table("transcriptions").insert({
                        "video_id": video_uuid,
                        "language": raw_data.get("language", raw_data.get("lang", "en")),
                        "full_text": full_text,
                        "segments": segments,
                        "source": "apify_pinto_studio",
                    }).execute()

                    count_new += 1

                except Exception as e:
                    errors.append(f"{url}: {str(e)}")

            # 7. Update run status
            supabase.table("scraper_runs").update({
                "status": "completed",
                "videos_new": count_new,
                "videos_updated": len(urls_to_process) - count_new,
                "errors": errors[:10] if errors else None
            }).eq("id", run_id).execute()

            self._send(200, {
                "message": f"CRON completado. {count_new} videos nuevos procesados.",
                "new_videos": count_new,
                "total_found_in_feed": len(new_video_urls),
                "processed_this_run": len(urls_to_process),
                "errors": errors[:5]
            })

        except Exception as e:
            self._send(500, {"error": f"Error en CRON: {str(e)}"})

    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
