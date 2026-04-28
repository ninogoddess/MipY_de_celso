# Branding Guidelines

## Core Palette
- **Primary:** #1ED760
- **Secondary:** #9D968E
- **Accent:** #1ED760
- **Background:** #121212
- **Text Primary:** #FFFFFF
- **Link:** #0000EE

## Severity Colors
- **Critical:** #E91429 (Mapped to `--danger`)
- **High:** #FFA42B (Mapped to `--warning`)
- **Medium:** #F3D32A (Mapped to `--accent`)
- **Low:** #3388FF (Mapped to `--info`)

## Fonts & Typography
- CircularSp-Arab (body, primary, heading)
- CircularSp-Hebr (body)
- CircularSp-Cyrl (body)
- CircularSp-Grek (body)
- Helvetica Neue (body)

**Hierarchy:**
- **h1:** 16px
- **h2:** 24px
- **body:** 14px

## Component Styles
- **Spacing (Base Unit):** 4
- **Border Radius:** 0px
- **Shadows:** Flat and subtle contrast borders.

## Personality
- **Tone:** modern
- **Energy:** high
- **Audience:** music enthusiasts and general public

## Implementation Rules
**1. Centralized CSS Variables:** All colors **must** come from central CSS variables defined in `index.css`. Hardcoded colors in JSX or CSS are strictly prohibited.
