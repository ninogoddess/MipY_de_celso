# 📜 Project Constitution — Scrapscrap_celso

> Este documento es **LEY**. Solo se modifica cuando cambia un schema, se añade una regla, o se modifica la arquitectura.

---

## Data Schemas

### Input Schema (Raw & Intermedio)
```json
{
  "youtube_metadata": {
    "video_id": "string",
    "title": "string",
    "description": "string",
    "views": "integer",
    "published_at": "datetime",
    "url": "string"
  },
  "transcription": [
    {
      "start": "float",
      "duration": "float",
      "text": "string"
    }
  ],
  "user_rpm_profile": {
    "user_id": "uuid",
    "resources": ["string"],
    "process": ["string"],
    "market": ["string"]
  },
  "latam_pain_points": [
    {
      "id": "uuid",
      "description": "string",
      "impact_level": "string",
      "evidence": "string"
    }
  ],
  "mvt_validation": {
    "solution_id": "uuid",
    "conversations": ["string"],
    "metrics": {
      "conversion_rate": "float",
      "engagement": "float"
    },
    "decision": "string (Pivot/Proceed/Kill)"
  }
}
```

### Output Schema (Delivery Payload)
```json
{
  "business_solution": {
    "solution_id": "uuid",
    "title": "string",
    "description": "string",
    "source_videos": ["video_id"],
    "latam_adaptation": "string",
    "rpm_fit_score": "integer",
    "difficulty": "string (Low/Medium/High)",
    "justification": "string",
    "created_at": "datetime"
  }
}
```

---

## Behavioral Rules

1. **Data-First:** No se escribe código sin schema definido y confirmado.
2. **Determinismo:** La lógica de negocio es determinística. Los LLMs no deciden reglas de negocio, solo clasifican/generan texto basado en reglas.
3. **Self-Annealing:** Cada error se analiza, se parchea, se testea y se documenta en `architecture/`.
4. **Separación de capas:** Architecture (SOPs) → Navigation (Routing) → Tools (Ejecución).
5. **Intermedios vs. Entregables:** `.tmp/` es efímero; los datos crudos y procesados persisten en Supabase. El payload se entrega en la web app Vercel.
6. **No Fake Data:** Prohibido el uso de contenido IA genérico sin justificación o data simulada en las validaciones MVT.

---

## Architectural Invariants

- `tools/` contiene scripts Python atómicos y testeables.
- `architecture/` contiene SOPs en Markdown.
- `.env` almacena credenciales y tokens.
- `.tmp/` para archivos intermedios (efímeros).
- Ningún script se escribe hasta que el Blueprint esté aprobado.

---

## Change Log

| Fecha | Cambio | Autor |
|-------|--------|-------|
| 2026-04-21 | Inicialización del documento | System Pilot |
| 2026-04-21 | Adición de Input y Output Schemas | System Pilot |
| 2026-04-27 | Diseño DB: 14 tablas, 3 capas, SQL migration 001 | System Pilot |

---

> Última actualización: 2026-04-27
