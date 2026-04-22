import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ ERROR: Faltan credenciales de Supabase en el archivo .env")
    exit(1)

try:
    # Initialize the client
    supabase: Client = create_client(url, key)
    
    # Try a simple operation to verify connection
    # Assuming there's no table yet, we can't easily query. 
    # But just creating the client verifies the URL structure.
    # We can try to list tables in the public schema by querying 'pg_catalog' or a dummy table
    try:
        # A simple query that will fail if the connection/auth is completely broken
        # We query a non-existent table just to see if we reach the DB and get a proper PostgREST error
        response = supabase.table('non_existent_table_for_handshake').select('*').limit(1).execute()
    except Exception as e:
        if "relation \"public.non_existent_table_for_handshake\" does not exist" in str(e):
            print("✅ Handshake exitoso con Supabase. Conexión y autenticación verificadas.")
        else:
            print("✅ Supabase client initialized, pero ocurrió un error inesperado al probar queries:", str(e))

except Exception as e:
    print(f"❌ Error al conectar con Supabase: {str(e)}")
