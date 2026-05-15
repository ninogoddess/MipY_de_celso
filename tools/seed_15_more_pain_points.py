import os
import uuid
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: No se encontraron las credenciales de Supabase en el .env")
    exit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

additional_pain_points = [
    {
        "id": str(uuid.uuid4()),
        "name": "Alta inflación y devaluación monetaria",
        "description": "Las pymes y emprendedores enfrentan pérdida de poder adquisitivo y riesgo cambiario, lo que dificulta la planificación a largo plazo y la importación de bienes.",
        "category": "Económico",
        "impact_level": "High"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Altos costos logísticos y de última milla",
        "description": "Infraestructura vial deficiente y geografía compleja que encarecen significativamente los envíos de e-commerce y distribución de productos físicos.",
        "category": "Operativo",
        "impact_level": "High"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Gran porcentaje de población no bancarizada",
        "description": "Dificultad para negocios digitales de cobrar suscripciones o pagos online debido a la baja penetración de tarjetas de crédito tradicionales.",
        "category": "Financiero",
        "impact_level": "High"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Economía altamente informal",
        "description": "Competencia desleal y dificultad para formalizar empleados y ventas. Muchos negocios B2B luchan por vender a pymes que operan en efectivo y sin facturas.",
        "category": "Estructural",
        "impact_level": "High"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Burocracia y complejidad regulatoria",
        "description": "Exceso de trámites y altos impuestos que ralentizan la creación de empresas y encarecen la legalización de startups.",
        "category": "Legal",
        "impact_level": "Medium"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Déficit de talento tecnológico especializado",
        "description": "Las empresas luchan por contratar desarrolladores, analistas de datos y expertos en ciberseguridad a precios accesibles debido a la fuga de cerebros.",
        "category": "Recursos Humanos",
        "impact_level": "Medium"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Inseguridad y robo de mercancías",
        "description": "Altos índices de robos en carreteras y asaltos a repartidores de última milla, lo que obliga a gastar fuertemente en seguros y escoltas.",
        "category": "Operativo",
        "impact_level": "High"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Resistencia cultural a la digitalización y SaaS",
        "description": "Dueños de negocios tradicionales que prefieren el papel y lápiz o Excel antes que pagar una suscripción mensual por software en la nube.",
        "category": "Adopción de Mercado",
        "impact_level": "High"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Bajo nivel de inglés técnico",
        "description": "Dificultad para expandirse globalmente o utilizar herramientas modernas de IA y software que no están traducidas ni localizadas.",
        "category": "Recursos Humanos",
        "impact_level": "Medium"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Falta de acceso a crédito para pymes",
        "description": "Los bancos tradicionales exigen demasiados requisitos e imponen tasas de interés altísimas, frenando el crecimiento de pequeños negocios.",
        "category": "Financiero",
        "impact_level": "High"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Desconfianza generalizada en pagos digitales",
        "description": "Miedo al fraude electrónico que lleva a altas tasas de carritos abandonados o preferencia por el pago contra entrega (Cash on Delivery).",
        "category": "Comportamiento del Consumidor",
        "impact_level": "High"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Atención al cliente y post-venta deficiente",
        "description": "Expectativas muy bajas en el mercado sobre el soporte técnico, lo que representa una oportunidad para negocios centrados en Customer Success.",
        "category": "Cultural",
        "impact_level": "Low"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Desigualdad en conexión a internet (Brecha digital)",
        "description": "Mientras las ciudades tienen 5G, las zonas rurales y periurbanas sufren de conexiones inestables, limitando aplicaciones pesadas o EdTech.",
        "category": "Tecnológico",
        "impact_level": "Medium"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Saturación publicitaria y alto CAC",
        "description": "El costo de adquisición de clientes en Meta y Google Ads se ha disparado, haciendo insostenibles los negocios sin crecimiento orgánico.",
        "category": "Marketing",
        "impact_level": "Medium"
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Fricciones en el comercio transfronterizo (Cross-border)",
        "description": "Aduanas lentas, aranceles cambiantes y problemas para enviar productos o recibir pagos entre países vecinos de Latinoamérica.",
        "category": "Comercio Internacional",
        "impact_level": "High"
    }
]

print("Inyectando 15 nuevos Pain Points en la base de datos...")

try:
    for pp in additional_pain_points:
        sb.table("latam_pain_points").upsert(pp).execute()
    print("¡15 Pain Points agregados exitosamente!")
except Exception as e:
    print(f"Error insertando datos: {e}")
