"""
scrape_and_store.py — Scraper + Supabase integration test.
Extrae transcripciones de 2 videos de Starter Story via Apify
y los persiste en Supabase (videos + transcriptions + scraper_runs).
"""
import os
import sys
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from apify_client import ApifyClient
from supabase import create_client, Client

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

# --- Config ---
APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

ACTOR_ID = "pintostudio/youtube-transcript-scraper"

# 2 videos reales de Starter Story para el test
TEST_VIDEOS = [
    "https://www.youtube.com/watch?v=D4fkiQfzw_I",
    "https://www.youtube.com/watch?v=iVy5J7iE-3Q",
    "https://www.youtube.com/watch?v=bq3-qH-CpYQ",
]

# --- Init clients ---
print("=" * 60)
print("SCRAPE & STORE TEST - Starter Story -> Supabase")
print("=" * 60)

if not all([APIFY_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    print("[FAIL] Faltan credenciales en .env")
    sys.exit(1)

apify = ApifyClient(APIFY_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Get channel UUID from Supabase ---
channel_resp = supabase.table("channels").select("id").eq("channel_id", "UCp6993wxpWPMfTso0IjxOaQ").execute()
if not channel_resp.data:
    print("[FAIL] Canal Starter Story no encontrado en la BD. Ejecuta primero el SQL de migracion.")
    sys.exit(1)

CHANNEL_UUID = channel_resp.data[0]["id"]
print(f"[OK] Canal Starter Story encontrado: {CHANNEL_UUID}")

# --- Create scraper_run entry ---
run_entry = supabase.table("scraper_runs").insert({
    "channel_id": CHANNEL_UUID,
    "status": "running",
    "videos_found": len(TEST_VIDEOS),
    "videos_new": 0,
    "videos_updated": 0,
}).execute()
scraper_run_id = run_entry.data[0]["id"]
print(f"[OK] Scraper run registrado: {scraper_run_id}")

videos_new = 0
videos_updated = 0
errors = []

for i, video_url in enumerate(TEST_VIDEOS, 1):
    print(f"\n--- Video {i}/{len(TEST_VIDEOS)}: {video_url} ---")
    
    # 1. Extraer video_id de la URL
    if "v=" in video_url:
        yt_video_id = video_url.split("v=")[1].split("&")[0]
    else:
        yt_video_id = video_url.split("/")[-1]
    
    # 2. Check if video already exists in DB (incremental)
    existing = supabase.table("videos").select("id").eq("video_id", yt_video_id).execute()
    if existing.data:
        print(f"  [SKIP] Video {yt_video_id} ya existe en la BD. Saltando.")
        videos_updated += 1
        continue
    
    # 3. Call Apify Pinto Studio
    print(f"  [APIFY] Llamando a {ACTOR_ID}...")
    try:
        run = apify.actor(ACTOR_ID).call(run_input={"videoUrl": video_url})
        items = list(apify.dataset(run["defaultDatasetId"]).iterate_items())
    except Exception as e:
        error_msg = f"Error Apify para {yt_video_id}: {str(e)}"
        print(f"  [FAIL] {error_msg}")
        errors.append(error_msg)
        continue
    
    if not items:
        error_msg = f"Apify no devolvio datos para {yt_video_id}"
        print(f"  [WARN] {error_msg}")
        errors.append(error_msg)
        continue
    
    raw_data = items[0]
    print(f"  [OK] Datos recibidos de Apify. Keys: {list(raw_data.keys())}")
    
    # 4. Parse data from Pinto Studio response
    title = raw_data.get("title", f"Video {yt_video_id}")
    
    # Build full_text from transcript data
    transcript_data = raw_data.get("data", raw_data.get("transcript", []))
    
    if isinstance(transcript_data, list):
        segments = []
        text_parts = []
        for seg in transcript_data:
            if isinstance(seg, dict):
                segments.append({
                    "start": seg.get("start", seg.get("offset", 0)),
                    "duration": seg.get("duration", seg.get("dur", 0)),
                    "text": seg.get("text", "")
                })
                text_parts.append(seg.get("text", ""))
        full_text = " ".join(text_parts)
    elif isinstance(transcript_data, str):
        full_text = transcript_data
        segments = []
    else:
        full_text = str(transcript_data)
        segments = []
    
    print(f"  [OK] Transcripcion parseada: {len(segments)} segmentos, {len(full_text)} caracteres")
    
    # 5. Insert into videos table
    try:
        video_insert = supabase.table("videos").insert({
            "channel_id": CHANNEL_UUID,
            "video_id": yt_video_id,
            "title": title,
            "description": raw_data.get("description", ""),
            "url": video_url,
            "published_at": raw_data.get("publishedAt", raw_data.get("published_at", None)),
            "duration_seconds": raw_data.get("duration", None),
            "thumbnail_url": raw_data.get("thumbnail", raw_data.get("thumbnailUrl", None)),
            "language": raw_data.get("language", raw_data.get("lang", "en")),
        }).execute()
        
        video_uuid = video_insert.data[0]["id"]
        print(f"  [OK] Video insertado en BD: {video_uuid}")
        videos_new += 1
    except Exception as e:
        error_msg = f"Error al insertar video {yt_video_id}: {str(e)}"
        print(f"  [FAIL] {error_msg}")
        errors.append(error_msg)
        continue
    
    # 6. Insert into transcriptions table
    try:
        trans_insert = supabase.table("transcriptions").insert({
            "video_id": video_uuid,
            "language": raw_data.get("language", raw_data.get("lang", "en")),
            "full_text": full_text,
            "segments": segments,
            "source": "apify_pinto_studio",
        }).execute()
        
        trans_uuid = trans_insert.data[0]["id"]
        print(f"  [OK] Transcripcion insertada en BD: {trans_uuid}")
    except Exception as e:
        error_msg = f"Error al insertar transcripcion para {yt_video_id}: {str(e)}"
        print(f"  [FAIL] {error_msg}")
        errors.append(error_msg)

# --- Update scraper_run with results ---
supabase.table("scraper_runs").update({
    "status": "completed" if not errors else "completed",
    "videos_new": videos_new,
    "videos_updated": videos_updated,
    "errors": errors if errors else None,
    "completed_at": datetime.now(timezone.utc).isoformat(),
}).eq("id", scraper_run_id).execute()

# --- Final verification ---
print("\n" + "=" * 60)
print("VERIFICACION FINAL")
print("=" * 60)

v_count = supabase.table("videos").select("id", count="exact").execute()
t_count = supabase.table("transcriptions").select("id", count="exact").execute()
r_count = supabase.table("scraper_runs").select("id", count="exact").execute()

print(f"  Videos en BD:          {v_count.count}")
print(f"  Transcripciones en BD: {t_count.count}")
print(f"  Scraper runs en BD:    {r_count.count}")
print(f"  Videos nuevos hoy:     {videos_new}")
print(f"  Errores:               {len(errors)}")

if errors:
    print("\n  Detalle de errores:")
    for err in errors:
        print(f"    - {err}")

print("\n" + "=" * 60)
if videos_new > 0:
    print("RESULTADO: TEST EXITOSO")
    print(f"{videos_new} videos scrapeados y persistidos en Supabase.")
else:
    print("RESULTADO: SIN NUEVOS VIDEOS (ya existian o hubo errores)")
print("=" * 60)
