"""
Handshake Supabase - Verifica conexion, lectura y escritura.
Prueba contra las tablas reales del schema 001.
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

print("=" * 50)
print("HANDSHAKE SUPABASE - Scrapscrap_celso")
print("=" * 50)

# 1. Verificar que las credenciales existen
if not url or not key:
    print("[FAIL] Faltan credenciales en .env (SUPABASE_URL o SUPABASE_KEY)")
    sys.exit(1)

print(f"[OK] SUPABASE_URL detectada: {url[:40]}...")
print(f"[OK] SUPABASE_KEY detectada: {key[:20]}...")

# 2. Crear cliente
try:
    supabase: Client = create_client(url, key)
    print("[OK] Cliente Supabase creado exitosamente")
except Exception as e:
    print(f"[FAIL] Error al crear cliente: {e}")
    sys.exit(1)

# 3. TEST DE LECTURA - Leer el canal seed (Starter Story)
print("\n--- TEST DE LECTURA ---")
try:
    response = supabase.table("channels").select("*").execute()
    rows = response.data
    print(f"[OK] Lectura exitosa en tabla 'channels'. Filas encontradas: {len(rows)}")
    if rows:
        for row in rows:
            print(f"     Canal: {row.get('name', 'N/A')} | ID: {row.get('channel_id', 'N/A')} | Activo: {row.get('is_active', 'N/A')}")
    else:
        print("     (Sin datos seed - la tabla existe pero esta vacia)")
except Exception as e:
    print(f"[FAIL] Error al leer 'channels': {e}")
    sys.exit(1)

# 4. TEST DE ESCRITURA - Insertar y luego borrar un registro de prueba en scraper_runs
print("\n--- TEST DE ESCRITURA ---")
try:
    # Necesitamos un channel_id valido para el FK
    if rows:
        test_channel_id = rows[0]["id"]
    else:
        # Si no hay seed, insertar un canal temporal
        ch_resp = supabase.table("channels").insert({
            "channel_id": "__test_handshake__",
            "name": "Test Channel (Handshake)",
            "is_active": False
        }).execute()
        test_channel_id = ch_resp.data[0]["id"]
        print(f"[OK] Canal temporal creado para test: {test_channel_id}")

    # Insertar un scraper_run de prueba
    insert_resp = supabase.table("scraper_runs").insert({
        "channel_id": test_channel_id,
        "status": "completed",
        "videos_found": 0,
        "videos_new": 0,
        "videos_updated": 0,
        "errors": {"test": "handshake verification"}
    }).execute()
    test_run_id = insert_resp.data[0]["id"]
    print(f"[OK] Escritura exitosa. scraper_run de prueba creado con ID: {test_run_id}")

    # Limpiar: borrar el registro de prueba
    supabase.table("scraper_runs").delete().eq("id", test_run_id).execute()
    print(f"[OK] Limpieza exitosa. Registro de prueba eliminado.")

    # Si creamos un canal temporal, borrarlo tambien
    if not rows:
        supabase.table("channels").delete().eq("channel_id", "__test_handshake__").execute()
        print(f"[OK] Canal temporal eliminado.")

except Exception as e:
    print(f"[FAIL] Error en test de escritura: {e}")
    sys.exit(1)

# 5. TEST DE TABLAS - Verificar que todas las tablas existen
print("\n--- VERIFICACION DE TABLAS ---")
expected_tables = [
    "channels", "videos", "video_snapshots", "transcriptions", "scraper_runs",
    "video_classifications", "latam_pain_points",
    "user_profiles", "rpm_profiles", "solutions", "solution_source_videos",
    "mvt_validations", "mvt_evidence"
]

all_ok = True
for table_name in expected_tables:
    try:
        resp = supabase.table(table_name).select("*").limit(1).execute()
        print(f"  [OK] {table_name}")
    except Exception as e:
        print(f"  [FAIL] {table_name}: {e}")
        all_ok = False

# 6. Resultado final
print("\n" + "=" * 50)
if all_ok:
    print("RESULTADO: HANDSHAKE EXITOSO")
    print("Conexion, lectura, escritura y 13 tablas verificadas.")
    print("Supabase esta listo para produccion.")
else:
    print("RESULTADO: HANDSHAKE PARCIAL")
    print("Algunas tablas no pudieron verificarse. Revisa los errores arriba.")
print("=" * 50)
