import os
import json
from dotenv import load_dotenv
from supabase import create_client

# Load env vars
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Credenciales de Supabase no encontradas.")
    exit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

PAIN_POINTS = [
    {
        "name": "Brecha de Financiación PyME (Credit Gap)",
        "description": "Las pequeñas y medianas empresas en LATAM enfrentan barreras severas para acceder a crédito formal debido a historiales crediticios inexistentes, altas tasas de interés y requisitos colaterales inflexibles.",
        "category": "Fintech",
        "impact_level": "Critical",
        "evidence": "Según el Banco Mundial y la Corporación Financiera Internacional (IFC), la brecha de financiamiento para las PYMES en América Latina y el Caribe se estima en más de 1 billón de USD.",
        "keywords": ["crédito", "pymes", "fintech", "bancarización", "préstamos", "b2b"],
        "sources": "Banco Mundial (SME Finance Forum), IFC",
        "semantic_metadata": {"market_size_usd": "1T+", "urgency": "high", "target_audience": "B2B SME"}
    },
    {
        "name": "Fricción en Logística de Última Milla",
        "description": "Costos desproporcionados y retrasos en las entregas de última milla provocados por infraestructura vial deficiente, falta de trazabilidad, zonas rojas (inseguridad) y direcciones no estandarizadas.",
        "category": "Logistics",
        "impact_level": "High",
        "evidence": "La CEPAL indica que los costos logísticos en LATAM representan entre el 18% y 35% del valor del producto, en contraste con el 8% en países de la OCDE.",
        "keywords": ["logística", "última milla", "delivery", "ecommerce", "rutas", "costos"],
        "sources": "CEPAL, Banco Interamericano de Desarrollo (BID)",
        "semantic_metadata": {"market_trend": "growing ecommerce", "bottleneck": "infrastructure", "target_audience": "B2B/B2C Retail"}
    },
    {
        "name": "Déficit de Talento Tecnológico (Skills Gap)",
        "description": "Las empresas luchan por contratar y retener talento técnico calificado (desarrolladores, analistas de datos, ciberseguridad) frente a una demanda creciente que los sistemas educativos tradicionales no logran cubrir.",
        "category": "Education",
        "impact_level": "High",
        "evidence": "PageGroup y el BID reportan un déficit de más de 1.2 millones de programadores en LATAM para 2025, frenando la transformación digital corporativa.",
        "keywords": ["talento", "tecnología", "educación", "bootcamp", "habilidades", "reclutamiento"],
        "sources": "BID, PageGroup, Korn Ferry",
        "semantic_metadata": {"opportunity": "EdTech, Upskilling B2B", "urgency": "high", "target_audience": "B2B HR, B2C Professionals"}
    },
    {
        "name": "Saturación y Fragmentación del Sistema de Salud",
        "description": "Largos tiempos de espera, historias clínicas no unificadas y acceso limitado a especialistas, especialmente en zonas no metropolitanas, derivado de sistemas de salud públicos colapsados y privados costosos.",
        "category": "Health",
        "impact_level": "Critical",
        "evidence": "La Organización Panamericana de la Salud (OPS) subraya que el gasto de bolsillo en salud en LATAM promedia el 34%, afectando financieramente a millones de familias ante ineficiencias del sector.",
        "keywords": ["salud", "telemedicina", "historias clínicas", "seguros", "bienestar"],
        "sources": "OPS/OMS, OCDE Health Statistics",
        "semantic_metadata": {"trend": "telehealth adoption", "bottleneck": "data silos", "target_audience": "B2C Patients, B2B Clinics"}
    },
    {
        "name": "Baja Productividad Agrícola (AgTech Lag)",
        "description": "Los pequeños y medianos productores enfrentan mermas en sus cosechas e ingresos debido a la falta de tecnificación, acceso a datos climáticos, intermediarios abusivos y poco financiamiento agrario.",
        "category": "Agro",
        "impact_level": "Medium",
        "evidence": "El IICA y la FAO destacan que aunque LATAM es una despensa global, la brecha de productividad de los pequeños agricultores reduce la rentabilidad regional en un 40%.",
        "keywords": ["agro", "rendimiento", "clima", "intermediarios", "agtech", "exportación"],
        "sources": "IICA, FAO",
        "semantic_metadata": {"trend": "climate tech", "bottleneck": "supply chain transparency", "target_audience": "B2B Farmers"}
    },
    {
        "name": "Desconfianza y Fraude en E-commerce",
        "description": "Tasas de abandono de carrito elevadas originadas por el miedo al fraude, la clonación de tarjetas y contracargos excesivos que castigan tanto al consumidor como al comercio.",
        "category": "E-commerce",
        "impact_level": "High",
        "evidence": "Mastercard y Statista reportan que LATAM tiene una de las tasas de fraude online más altas del mundo (20% de transacciones rechazadas), generando pérdidas billonarias a retailers.",
        "keywords": ["fraude", "pagos", "ecommerce", "ciberseguridad", "confianza", "contracargos"],
        "sources": "Mastercard, Statista, MRC",
        "semantic_metadata": {"trend": "digital wallets", "bottleneck": "security vs UX", "target_audience": "B2B Merchants"}
    },
    {
        "name": "Alta Informalidad Laboral y Comercial",
        "description": "Más de la mitad de los trabajadores y microempresas operan en la informalidad, impidiéndoles acceder a software de gestión, seguridad social, beneficios crediticios y escalar sus negocios.",
        "category": "Employment",
        "impact_level": "Critical",
        "evidence": "La OIT (Organización Internacional del Trabajo) estima que el 53.7% del empleo en América Latina es informal, limitando la adopción de herramientas B2B formales.",
        "keywords": ["informalidad", "empleo", "microempresas", "impuestos", "inclusión"],
        "sources": "OIT (ILO), CEPAL",
        "semantic_metadata": {"trend": "gig economy", "bottleneck": "regulatory overhead", "target_audience": "B2B Micro, B2C Workers"}
    },
    {
        "name": "Rezago en Digitalización de Procesos B2B (SaaS)",
        "description": "Millones de pymes aún gestionan inventarios, contabilidad y nóminas en papel o Excel, generando pérdida de datos, errores humanos y estancamiento competitivo.",
        "category": "SaaS",
        "impact_level": "High",
        "evidence": "McKinsey estima que la digitalización profunda de pymes en LATAM podría aumentar el PIB regional, dado que actualmente menos del 30% utiliza software en la nube para procesos core.",
        "keywords": ["pymes", "excel", "software", "nube", "automatización", "SaaS", "erp"],
        "sources": "McKinsey & Company, BID",
        "semantic_metadata": {"trend": "cloud migration", "bottleneck": "tech literacy", "target_audience": "B2B SME"}
    },
    {
        "name": "Carga Burocrática y Regulatoria Excesiva",
        "description": "Abrir, operar o cerrar una empresa requiere decenas de trámites presenciales, pago de sellos y meses de espera, ahogando a los emprendedores en papeleo.",
        "category": "Government",
        "impact_level": "High",
        "evidence": "El último reporte 'Doing Business' del Banco Mundial ubicó a la mayoría de los países de LATAM en el tercio inferior global por la dificultad y lentitud de los trámites para abrir empresas.",
        "keywords": ["burocracia", "trámites", "legaltech", "gobierno", "impuestos"],
        "sources": "Banco Mundial (Doing Business), OCDE",
        "semantic_metadata": {"trend": "govtech", "bottleneck": "paperwork", "target_audience": "B2B Startups, B2B SME"}
    },
    {
        "name": "Vulnerabilidad Cibernética en PyMES",
        "description": "Con la migración forzada a digital post-pandemia, las empresas pequeñas carecen de escudos cibernéticos, siendo víctimas fáciles de ransomware, phishing y robo de datos corporativos.",
        "category": "Cybersecurity",
        "impact_level": "Medium",
        "evidence": "Fortinet reportó más de 360 mil millones de intentos de ciberataques en LATAM en 2022, destacando que las PYMES son el blanco con menor preparación defensiva.",
        "keywords": ["ciberseguridad", "ransomware", "datos", "protección", "pymes"],
        "sources": "Fortinet Threat Intelligence, BID",
        "semantic_metadata": {"trend": "data privacy", "bottleneck": "budget constraints", "target_audience": "B2B Mid-Market"}
    }
]

def run_seed():
    print("Iniciando Seed de Pain Points LATAM...")
    
    # Intentar limpiar la tabla primero (puede fallar si no se ha aplicado el migration 002)
    try:
        # Solo limpia registros anteriores insertados por los LLMs que no tienen 'name'
        # o borra todos (ya que queremos que sea ground truth).
        sb.table("latam_pain_points").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        print("✓ Tabla anterior vaciada.")
    except Exception as e:
        print(f"Nota al vaciar: {e}")

    # Insertar los 10 Pain Points Golden Data
    success_count = 0
    for pp in PAIN_POINTS:
        try:
            # Quitamos keys que podrían fallar si el schema SQL no ha sido ejecutado aún.
            # OJO: Asumimos que la migración SQL 002_update_painpoints.sql YA se ejecutó.
            sb.table("latam_pain_points").insert(pp).execute()
            success_count += 1
            print(f"  + Insertado: {pp['name']}")
        except Exception as e:
            print(f"Error insertando {pp.get('name')}: {e}")
            print("¿Ejecutaste el script SQL de migración en Supabase primero?")
            break

    print(f"\nFinalizado. {success_count}/{len(PAIN_POINTS)} pain points insertados.")

if __name__ == "__main__":
    run_seed()
