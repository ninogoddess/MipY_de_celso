# SOP 002: LLM Extraction (HU 06)

## Objetivo
Definir el Standard Operating Procedure (SOP) para la extracción semántica mediante IA (LLM). Este documento establece el *prompt* y la estructura de datos obligatoria para extraer el modelo de negocio, la fuente de ingresos y el cliente objetivo desde las transcripciones de los videos.

## Contexto
Los datos brutos obtenidos en la Fase 1 (Scraping) son extensos y sin estructura. El objetivo es procesar la transcripción de cada video en la tabla `videos` y `transcriptions` para rellenar la tabla `video_classifications` u otras estructuras con información clave estandarizada.

---

## 1. Prompt de Extracción

El siguiente prompt debe ser utilizado como `system_prompt` y `user_prompt` cuando se envíe la solicitud al LLM.

### System Prompt
```text
Eres un analista experto en modelos de negocio digitales. Tu tarea es analizar transcripciones de videos de emprendedores y extraer información estructurada de forma precisa, concreta y verificable.

Debes responder EXCLUSIVAMENTE en JSON válido. No agregues texto adicional.
```

### User Prompt
```text
Analiza la siguiente transcripción de un video de emprendimiento y extrae la información solicitada.

TRANSCRIPCIÓN:
{{transcript}}

INSTRUCCIONES:

1. Identifica el modelo de negocio principal
2. Identifica la fuente de ingresos (cómo gana dinero)
3. Identifica el cliente objetivo
4. EXTRAPOLACIÓN LATAM: Identifica los problemas (pain points) principales que resuelve este modelo y extrapólalos a la realidad y contexto del mercado latinoamericano. Explica cómo o por qué esta necesidad existe o se adapta en LATAM.

REGLAS IMPORTANTES:
- No inventes información
- Si no está claro, usa null
- Sé específico (no generalices)
- Máximo 2-3 frases por campo
- No uses lenguaje ambiguo
- IMPORTANTE: Toda la respuesta (valores del JSON, descripciones y pain points) DEBE estar redactada estrictamente en ESPAÑOL.

FORMATO DE RESPUESTA:
{
  "business_model": {
    "type": string | null,
    "description": string | null
  },
  "revenue_stream": {
    "type": string | null,
    "description": string | null
  },
  "target_customer": {
    "type": string | null,
    "description": string | null
  },
  "latam_pain_points": [
    {
      "pain_point": "Breve descripción del problema original",
      "latam_context_adaptation": "Justificación concreta de cómo y por qué este dolor aplica o se acentúa en el contexto de Latinoamérica"
    }
  ],
  "confidence_score": number (0-100)
}

VALIDACIÓN INTERNA (OBLIGATORIA):
Antes de responder:
- Verifica que cada campo tenga sentido lógico
- Verifica que no contradiga la transcripción
- Si hay dudas → baja el confidence_score

Si la transcripción es irrelevante o incompleta, devuelve:
{
  "business_model": null,
  "revenue_stream": null,
  "target_customer": null,
  "latam_pain_points": [],
  "confidence_score": 0
}
```

---

## 2. Recomendación Tecnológica (Motor LLM)
Para mantener un enfoque de costo $0 o mínimo durante la fase académica/MVP, se recomienda utilizar la API de **OpenRouter**.

- **Modelo recomendado:** `deepseek/deepseek-chat:free` (DeepSeek V3) o `deepseek/deepseek-r1:free`.
- **Por qué:** DeepSeek ha demostrado capacidades de razonamiento (`R1`) y seguimiento de formato JSON de nivel GPT-4, siendo ofrecido de forma gratuita o ultra-accesible en OpenRouter.
- **Fallback:** En OpenRouter, establecer el parámetro `model: "openrouter/free"` permite delegar al modelo gratuito con mejor disponibilidad en el momento.

## 3. Manejo de Errores
- **Fallo de Parseo JSON:** El pipeline (Python/Serverless) debe capturar la respuesta y usar validación `json.loads`. Si falla, intentar un re-intento estructurado o asignar un error logeado en base de datos (`status: error`).
- **Confidence Score Bajo (<50):** Los registros deben marcarse en BD para revisión humana y no tomarse como fuentes de "alta confianza" para la generación del *Motor de Soluciones*.
