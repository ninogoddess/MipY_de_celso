# 🔍 Findings — Scrapscrap_celso

> Registro de investigación, descubrimientos y restricciones del proyecto.

---

## Descubrimientos

1. **North Star:** Aplicación web en Vercel para transformar contenido de *Starter Story* en oportunidades de negocio reales y validadas para LATAM, personalizadas según el perfil RPM (Resources, Process, Market) del usuario.
2. **Integraciones requeridas:** 
   - **Apify / YouTube API** para transcripciones estables, escalables y en free-tier.
   - **Supabase** para persistencia real de datos (videos, transcripciones, datos procesados).
   - **LLM/IA** para clasificación, análisis y generación de soluciones.
   - **Vercel Cron / Scheduler** para automatización de rescraping.
3. **Delivery:** Web app (Next.js/Vercel) con módulos interactivos: Dashboard de Scraping (logs, status), Wizard RPM, Motor de Soluciones, y Módulo de Validación MVT.

## Restricciones

1. **Prohibiciones Absolutas:** Cero ideas genéricas de IA; el output debe derivar estrictamente de casos reales de éxito. Cero simulaciones en MVT; deben usarse datos e interacciones reales. Nada hardcodeado.
2. **Arquitectura:** Debe separar claramente datos crudos de datos procesados. El scraper debe ser incremental para evitar rate limits. 

## Recursos Útiles

- Documentación de Apify YouTube Extractors.
- Supabase Docs & Next.js Auth/Database setup.
- Vercel Cron Jobs documentation.

---

> Última actualización: 2026-04-21
