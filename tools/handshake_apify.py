import os
from dotenv import load_dotenv
from apify_client import ApifyClient

# Load environment variables
load_dotenv()

apify_token = os.environ.get("APIFY_API_TOKEN")

if not apify_token:
    print("❌ ERROR: Falta APIFY_API_TOKEN en el archivo .env")
    exit(1)

try:
    # Initialize the ApifyClient with your API token
    client = ApifyClient(apify_token)
    
    # Verify by getting the user's account info
    user = client.user().get()
    
    print(f"✅ Handshake exitoso con Apify. Autenticado como usuario ID: {user['id']}")

except Exception as e:
    print(f"❌ Error al conectar con Apify: {str(e)}")
