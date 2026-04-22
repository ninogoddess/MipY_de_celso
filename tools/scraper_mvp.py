import streamlit as st
import os
from dotenv import load_dotenv
from apify_client import ApifyClient
import pandas as pd

# Cargar variables de entorno
load_dotenv()

# Configuración de página MVP
st.set_page_config(page_title="Scrapscrap MVP", page_icon="📝", layout="wide")
st.title("YouTube Transcript Scraper - MVP")
st.markdown("Usando Apify Actor: `pintostudio/youtube-transcript-scraper`")

# Verificar API Key
apify_token = os.environ.get("APIFY_API_TOKEN")

if not apify_token:
    st.error("❌ No se encontró APIFY_API_TOKEN. Guarda tu token en el archivo `.env` antes de ejecutar.")
    st.info("Formato en .env:\n\nAPIFY_API_TOKEN=apify_api_TuTokenSecreto")
    st.stop()
else:
    st.success("✅ APIFY_API_TOKEN cargado correctamente.")

# Cliente de Apify
client = ApifyClient(apify_token)

# Input UI para la URL del video
video_url = st.text_input("Ingresa la URL del video de YouTube (ej. Starter Story):", "https://www.youtube.com/watch?v=kYxCRzMAyG4")

if st.button("Extraer Transcripción", type="primary"):
    with st.spinner("Conectando con Apify y scrapeando... (puede tardar unos 30-60 segundos)"):
        try:
            # Preparar el input para el actor de Pinto Studio
            run_input = {
                "videoUrl": video_url,
                "language": "es" # Intentar Español por defecto, si no, traer original (esto depende de config de pinto, sino quitar param language)
            }

            # Llamar al Actor
            # pintostudio/youtube-transcript-scraper
            run = client.actor("pintostudio/youtube-transcript-scraper").call(run_input=run_input)
            
            # Obtener los items del dataset asociado a la ejecución
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            
            if not items:
                st.warning("⚠️ El actor se ejecutó pero no devolvió items. Es posible que el video no tenga subtítulos.")
            else:
                st.success("✅ Transcripción extraída con éxito!")
                
                # Pinto studio devuelve un JSON, vamos a formatearlo visualmente
                # Usualmente devuelve "text" o un array de captions
                
                # Asumimos que los items tienen formato de transcripción
                first_item = items[0]
                
                # Mostrar el JSON crudo en un expander
                with st.expander("Ver JSON Crudo (Data Schema Base)"):
                    st.json(first_item)
                
                # Procesar a texto legible si es posible
                if 'transcript' in first_item or 'captions' in first_item or 'text' in first_item:
                    st.subheader("Transcripción Procesada")
                    
                    if 'transcript' in first_item and isinstance(first_item['transcript'], list):
                        # Convertir a dataframe para tabla
                        df = pd.DataFrame(first_item['transcript'])
                        if not df.empty:
                            st.dataframe(df, use_container_width=True)
                            
                            # Mostrar todo el texto concatenado
                            full_text = " ".join([item.get('text', '') for item in first_item['transcript']])
                            st.text_area("Texto Completo (Para LLM):", full_text, height=300)
                    elif 'text' in first_item: # Si pintostudio devuelve un campo text grande
                        st.text_area("Texto Completo:", first_item['text'], height=300)
                    else:
                        st.write("Estructura de transcripción no estándar para tabla.")
                
        except Exception as e:
            st.error(f"❌ Error al ejecutar el scraper: {str(e)}")
