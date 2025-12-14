# Modernization Roadmap

## 1. AI-Driven Styling
- Build “style presets” (Brutalist, Editorial, Neo-morphism, etc.) and let users generate or pick them before site creation.
- Send palette/typography/mood context to the LLM so every page feels intentionally designed.
### AI-Driven Styling – Detailed Implementation Plan

#### Style Preset System
- Curate 6–8 distinct presets (e.g., Brutalist, Editorial, Neo-morphism, Vaporwave, High-Contrast Minimal, Warm Artisan).
- For each preset define:
  - Color palette (primary/secondary/background, gradient tokens)
  - Typography pairing (heading + body fonts)
  - Mood descriptors (3–4 adjectives)
  - UI accents (corner radius, shadow style, patterns)
- Store presets as structured JSON so both frontend (preview chips) and backend (prompt injection) can use the same source of truth.

#### Frontend UX
- Add a “Design Style” selector (chips or carousel) with live color chips and font previews.
- Show short descriptions + example tags for each preset; allow “Surprise me” randomizer.
- Persist the selected preset when users enter the conversational update flow so style preferences survive iterations.

#### Backend Prompt Enhancements
- When a preset is selected, append a prompt block such as:
  ```
  Design style: Brutalist
  Palette: #000000 / #f4f4f4 / #ff0054
  Typography: Heading – Space Grotesk bold, Body – Inter regular
  Mood: bold, architectural, minimal
  UI Accents: thick borders, stark boxes, asymmetric layout
  Instructions: keep surfaces flat, emphasize large typography, limit gradients
  ```
- Ensure both `/generate` and `/update` endpoints include the style context so updates preserve the chosen design language.
- Extend `fill_images` fallback prompts to respect the preset (e.g., “photograph matching Brutalist palette”).

#### Preview & Validation
- After generation, render a quick screenshot thumbnail (Playwright) so users can see how the preset manifested.
- Add a “regenerate with same content, new style” button to encourage experimentation.
- Log which presets are selected vs. accepted to fine-tune preset definitions.

#### QA & Validation Checklist
- **Frontend**: Confirm selector looks correct on desktop, tablet, and mobile breakpoints; verify default style is pre-selected; ensure cards toggle selection state and re-open with correct state after “New Prompt”.
- **Form submission**: Inspect DevTools network calls to confirm `style_preset` is attached to `/generate` and `/update` payloads.
- **Generation flow**: Run at least one prompt per preset to verify the resulting HTML references the requested aesthetic (color tokens, typography hints in CSS) and that placeholder text acknowledges the style.
- **Image pipeline**: Trigger fallback image generation (no uploads) and confirm `style_image_hint` influences logs/output (e.g., FLUX prompt includes preset context).
- **Regression checks**: Repeat existing generation without selecting a style to ensure defaults still work; confirm profile image logic and template loading remain unaffected.
- **Error handling**: Simulate missing/unknown preset key (manually edit request) and ensure backend safely ignores it without crashing.

#### Extensibility & Future Work
- Allow advanced users to tweak base presets (upload palette JSON, swap fonts).
- Expose API hook to accept custom style tokens from design tools (e.g., Figma exports).
- Introduce seasonal or trending presets (e.g., “Holiday Glow”) to keep the experience fresh.

## 2. Component Library with Variations
- Curate a library of high-quality sections (hero, testimonials, pricing, timelines) with multiple visual variants.
- Allow AI to assemble sites from these blocks for consistency and polish.

## 3. Visual Feedback Loop
- Capture quick screenshots (Playwright) after generation and show thumbnails so users can pick or compare.
- Add annotation/markup on previews that translates into update prompts.

## 4. Rich Asset Handling
- Accept logos, favicons, background textures, videos, and auto-generate subtle patterns/gradients.
- Expand beyond profile images so brand assets are reflected across the layout.

## 5. Structured Resume/Portfolio Mode
- Offer structured input (experience, skills, certifications) that feeds the prompt for consistent resume layouts.
- Output both responsive HTML and PDF/ATS-friendly formats.

## 6. Interactive Enhancements
- Include optional micro-interactions (animated counters, parallax timelines, carousels, lightweight 3D embeds).
- Have the AI explain where/why to place these for a premium feel.

## 7. Brand Voice Personalization
- Provide tone presets (bold startup, luxury studio, warm personal) and auto-rewrite copy accordingly.
- Support multilingual output with localized typography and layout tweaks.

## 8. Accessibility & QA
- Run automated checks for color contrast, heading hierarchy, semantic tags, and ARIA usage.
- Offer an “improve accessibility” toggle that enforces best practices before delivery.

## 9. Collaboration & Versioning
- Track every conversational update, show diffs, and allow rollbacks.
- Share preview links with comment threads for stakeholder feedback.

## 10. Deployment & Integrations
- One-click deploy to Netlify/Vercel plus CMS export options.
- Provide API/webhook hooks for dynamic data (GitHub stats, RSS feeds) that AI can wire into sections.