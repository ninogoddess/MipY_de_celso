import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: No se encontraron las credenciales de Supabase en el .env")
    exit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    print("Iniciando borrado de todas las clasificaciones en video_classifications...")
    # Truco para borrar todos los registros en Supabase: .neq("id", un uuid nulo) o usar el endpoint REST puro.
    # En la tabla video_classifications la primary key es el video_id (generalmente un string).
    # Así que podemos hacer .neq("video_id", "algo_imposible")
    res = sb.table("video_classifications").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    
    print(f"Borrado exitoso. Registros eliminados.")
except Exception as e:
    print(f"Error al borrar las clasificaciones: {e}")
