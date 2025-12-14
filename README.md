# AI Web Builder

Create production-ready landing pages, portfolios, and marketing sites in minutes. AI Web Builder turns natural language briefs into polished HTML/CSS, complete with variant testing guidance so you can validate pages before launch.

![AI Web Builder screenshot](docs/app-preview.png) <!-- optional image, update/remove if unavailable -->

## Table of Contents

1. [Highlights](#highlights)
2. [System Requirements](#system-requirements)
3. [Quick Start](#quick-start)
4. [Environment Configuration](#environment-configuration)
5. [Running the App](#running-the-app)
6. [Product Workflow](#product-workflow)
7. [Image Generation Pipeline](#image-generation-pipeline)
8. [Deploying / Hosting](#deploying--hosting)
9. [Publishing to GitHub](#publishing-to-github)
10. [Contributing](#contributing)

---

## Highlights

- **Multi-provider LLM orchestration** – Gemini, OpenAI, Anthropic (Claude), Groq, and Ollama are all supported with automatic failover. Toggle providers via `LLM_PROVIDER` without redeploying.
- **Design intelligence baked in** – Users pick from curated style presets (palette, typography, tone) and a component library (hero, pricing, timeline, testimonials) before writing a single prompt.
- **Interactive enhancements (Feature #6)** – Layer in animated counters, magnetic CTAs, testimonial carousels, parallax timelines, lightweight 3D embeds, and more. Each choice includes an implementation brief so the LLM explains where and why to use it.
- **Rich asset ingestion** – Upload profile shots, drop reference files/URLs, or auto-fetch imagery via Hugging Face FLUX / SD 3.5 with Unsplash fallbacks.
- **Live preview + download** – Generated HTML is streamed into an iframe for instant QA. Export the final artifact as a standalone file with one click.
- **Modernization ready** – The project ships with a modernization plan (`modernization-plan.md`) outlining upcoming work (accessibility audits, collaboration, versioning, deployment hooks, etc.).

## System Requirements

| Requirement | Details |
|-------------|---------|
| Python      | 3.10 (recommended) |
| pip / venv  | Standard Python packaging tools |
| Node / Playwright | *Optional.* Needed only if you want automated screenshots |
| Ollama      | *Optional.* Install when using local models (`LLM_PROVIDER=ollama`) |
| GPU access  | *Optional.* Required only for self-hosted Hugging Face image models |

## Quick Start

```bash
git clone https://github.com/<your-org>/ai-web-builder.git
cd ai-web-builder
python -m venv env
source env/bin/activate             # Windows: env\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env                 # create your config (see next section)
```

## Environment Configuration

Create a `.env` file in the project root. The app reads the following keys:

| Variable | Description |
|----------|-------------|
| `LLM_PROVIDER` | `openai`, `gemini`, `claude`, `groq`, or `ollama`. Determines the first provider to try. |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | Required when `LLM_PROVIDER=openai`. Example model: `gpt-4o-mini`. |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | Enable Claude (`claude-3-5-sonnet-20241022`, etc.). |
| `GOOGLE_API_KEY`, `GEMINI_MODEL` | Access Gemini 2.5 (text + vision). |
| `GROQ_API_KEY`, `GROQ_MODEL` | Optional Groq inference (`llama-3.3-70b-versatile`). |
| `OLLAMA_MODEL` | Local model name, e.g. `qwen2.5-coder:14b`. Requires Ollama running locally. |
| `UNSPLASH_ACCESS_KEY` | Free fallback for stock photography. |
| `HF_TOKEN`, `HF_MODEL` | Optional Hugging Face credentials for FLUX.1-dev or SD 3.5. |
| `PLAYWRIGHT_BROWSERS_PATH` | (Optional) Location of browsers for screenshot capture. |

Any missing provider key simply disables that backend; the app logs a warning but continues with available fallbacks.

## Running the App

```bash
python app.py
# visit http://127.0.0.1:5000/
```

Hot reloading is enabled via Flask’s debug server, so UI edits refresh automatically. For production, run behind a WSGI server (see [Deploying / Hosting](#deploying--hosting)).

## Product Workflow

1. **Pick a template** – Business agency, SaaS landing, or personal portfolio structure.
2. **Lock a style preset** – e.g., Editorial Luxe, Neo-morphism Glow, High-Contrast Minimal.
3. **Curate sections** – Toggle hero/testimonials/pricing/timeline variants from `component_library.json`.
4. **Add interactive enhancements** – Check animated counters, parallax timelines, magnetic CTAs, etc. The prompt blueprint explains how to build and justify each effect.
5. **Attach references** – Upload PDFs, text briefs, or drop a reference URL. Add a profile image or brand assets.
6. **Describe your site** – Use the chat composer; first prompt generates a full build, subsequent prompts restyle/rewrite existing HTML.
7. **Preview & export** – View the result in the live iframe, then download the generated HTML or open it in a new tab for closer inspection.

## Image Generation Pipeline

1. FLUX.1-dev via Hugging Face (if token + credits available)
2. Stable Diffusion 3.5 Large
3. Unsplash API (semantic search with automatic prompt rewriting)

If none are configured, the builder still works—image placeholders remain untouched so you can manually swap assets later.

## Deploying / Hosting

For a simple production deploy:

```bash
export FLASK_ENV=production
gunicorn --bind 0.0.0.0:8080 app:app
```

Behind a reverse proxy (nginx, Caddy, etc.), remember to pass the required environment variables and ensure the `env` virtual environment is installed on the server/runner.

## Publishing to GitHub

Use these commands once you are satisfied locally:

```bash
git init
git add .
git commit -m "Initial public release"
git branch -M main
git remote add origin git@github.com:<your-org>/ai-web-builder.git
git push -u origin main
```

After pushing:

1. Configure repository secrets (API keys, HF tokens) in GitHub Actions if you plan to automate deployments.
2. Enable Dependabot/security alerts for the `requirements.txt`.
3. Use Issues/Projects boards to track modernization milestones outlined in `modernization-plan.md`.

## Contributing

Contributions are welcome! Please open an issue describing the improvement or bug, submit a PR with a clear description, and include screenshots/GIFs for UI changes. For larger roadmap items (accessibility audits, collaboration tooling, deployment integrations), reference the modernization plan to avoid duplicating ongoing work.

---

Questions or ideas? Open an issue or start a discussion once the repo is public. Happy building! 🚀
