import os
from flask import Flask, render_template, request, jsonify
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import json
import tempfile
import webbrowser
import re, urllib.parse
from pathlib import Path
import base64
from werkzeug.utils import secure_filename

# Import Hugging Face for FLUX.1-dev
try:
    from huggingface_hub import InferenceApi
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("Warning: huggingface_hub not available, falling back to Unsplash")

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright not installed; thumbnail generation disabled.")

try:
    from langchain_groq import ChatGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("langchain-groq not installed; Groq provider disabled.")

try:
    from langchain_openai import ChatOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("langchain-openai not installed; OpenAI provider disabled.")

try:
    from langchain_anthropic import ChatAnthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    print("langchain-anthropic not installed; Claude provider disabled.")

# Load environment variables
load_dotenv()

app = Flask(__name__)

def get_llm():
    """Return an LLM instance with provider preference and fallbacks."""
    provider_pref = os.getenv("LLM_PROVIDER", "").strip().lower()
    google_api_key = os.getenv("GOOGLE_API_KEY")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    groq_api_key = os.getenv("GROQ_API_KEY")
    groq_model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    ollama_model = os.getenv("OLLAMA_MODEL", "mistral")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    def init_gemini():
        if not google_api_key:
            return None
        try:
            # Ensure each Flask worker thread has its own event loop
            import asyncio
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.set_event_loop(asyncio.new_event_loop())
            print("INFO: Using Google Gemini provider.")
            return ChatGoogleGenerativeAI(model=gemini_model, temperature=0.7, max_output_tokens=16384)
        except Exception as e:
            print(f"Error initializing Gemini LLM: {e}")
            return None

    def init_groq():
        if not groq_api_key:
            return None
        if not GROQ_AVAILABLE:
            print("Groq requested but langchain-groq package is missing.")
            return None
        try:
            print("INFO: Using Groq provider.")
            return ChatGroq(
                groq_api_key=groq_api_key,
                model_name=groq_model,
                temperature=float(os.getenv("GROQ_TEMPERATURE", 0.7)),
                max_tokens=int(os.getenv("GROQ_MAX_TOKENS", 4096)),
            )
        except Exception as e:
            print(f"Error initializing Groq LLM: {e}")
            return None

    def init_ollama():
        try:
            print("INFO: Using Ollama provider.")
            return Ollama(model=ollama_model)
        except Exception as e:
            print(f"Error initializing Ollama: {e}")
            return None

    def init_openai():
        if not openai_api_key or not OPENAI_AVAILABLE:
            if not openai_api_key:
                print("OpenAI requested but OPENAI_API_KEY missing.")
            else:
                print("OpenAI requested but langchain-openai not installed.")
            return None
        try:
            print("INFO: Using OpenAI provider.")
            return ChatOpenAI(
                model=openai_model,
                api_key=openai_api_key,
                temperature=float(os.getenv("OPENAI_TEMPERATURE", 0.6)),
                max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", 4096)),
            )
        except Exception as e:
            print(f"Error initializing OpenAI LLM: {e}")
            return None

    def init_claude():
        if not anthropic_api_key or not CLAUDE_AVAILABLE:
            if not anthropic_api_key:
                print("Claude requested but ANTHROPIC_API_KEY missing.")
            else:
                print("Claude requested but langchain-anthropic not installed.")
            return None
        try:
            print("INFO: Using Claude provider.")
            return ChatAnthropic(
                model=anthropic_model,
                api_key=anthropic_api_key,
                temperature=float(os.getenv("ANTHROPIC_TEMPERATURE", 0.6)),
                max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", 4096)),
            )
        except Exception as e:
            print(f"Error initializing Claude LLM: {e}")
            return None

    provider_sequence = []
    if provider_pref == "groq":
        provider_sequence = [init_groq, init_openai, init_claude, init_gemini, init_ollama]
    elif provider_pref == "ollama":
        provider_sequence = [init_ollama, init_groq, init_openai, init_claude, init_gemini]
    elif provider_pref == "gemini":
        provider_sequence = [init_gemini, init_openai, init_claude, init_groq, init_ollama]
    elif provider_pref == "openai":
        provider_sequence = [init_openai, init_gemini, init_claude, init_groq, init_ollama]
    elif provider_pref in ["claude", "anthropic"]:
        provider_sequence = [init_claude, init_openai, init_gemini, init_groq, init_ollama]
    else:
        # Default preference prioritizes hosted coding-tuned models first
        provider_sequence = [init_gemini, init_openai, init_claude, init_groq, init_ollama]

    for init in provider_sequence:
        llm = init()
        if llm:
            return llm

    print("ERROR: Failed to initialize any LLM provider.")
    return None

STYLE_PRESETS_PATH = Path(__file__).resolve().parent / "style_presets.json"
COMPONENT_LIBRARY_PATH = Path(__file__).resolve().parent / "component_library.json"

DEFAULT_STYLE_PRESETS = {
    "brutalist": {
        "label": "Brutalist Bold",
        "palette": ["#000000", "#f4f4f4", "#ff0054"],
        "fonts": ["Space Grotesk", "Inter"],
        "mood": ["bold", "architectural", "minimal"],
        "ui_accents": "thick borders, stark boxes, asymmetric layout",
        "instructions": "Use high-contrast surfaces, unapologetically large typography, and minimal gradients.",
        "image_prompt": "brutalist aesthetic, bold high-contrast colors, punchy geometric composition"
    },
    "editorial": {
        "label": "Editorial Luxe",
        "palette": ["#0f172a", "#f8fafc", "#eab308"],
        "fonts": ["Playfair Display", "Source Sans Pro"],
        "mood": ["refined", "magazine-like", "balanced"],
        "ui_accents": "generous whitespace, split layouts, elegant rules and captions",
        "instructions": "Emphasize large serif headlines, supporting sans-serif body copy, and balanced columns.",
        "image_prompt": "editorial magazine photography, soft lighting, high-end typography overlays"
    },
    "neomorphism": {
        "label": "Neo-morphism Soft Glow",
        "palette": ["#ecf0f3", "#cfd8dc", "#5c6ac4"],
        "fonts": ["Poppins", "Nunito"],
        "mood": ["soft", "tactile", "futuristic"],
        "ui_accents": "subtle shadows, pill buttons, frosted cards, glowing highlights",
        "instructions": "Use layered cards with soft drop shadows, rounded corners, and gentle gradients.",
        "image_prompt": "soft lit 3D renders, neumorphic interface visuals, gentle glow"
    },
    "artisan": {
        "label": "Warm Artisan",
        "palette": ["#2c1810", "#f7ede2", "#f28482"],
        "fonts": ["Cormorant Garamond", "Work Sans"],
        "mood": ["warm", "craft-focused", "story-driven"],
        "ui_accents": "textured backgrounds, hand-drawn dividers, layered cards",
        "instructions": "Incorporate organic shapes, textured backgrounds, and storytelling callouts.",
        "image_prompt": "artisan lifestyle photography, warm film tones, handcrafted details"
    }
}


def load_style_presets():
    """Load shared style presets from JSON so frontend/backend share the same source."""
    try:
        with open(STYLE_PRESETS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and data:
                return data
    except FileNotFoundError:
        print("style_presets.json not found. Falling back to default presets.")
    except Exception as exc:
        print(f"Error loading style presets: {exc}. Falling back to defaults.")
    return DEFAULT_STYLE_PRESETS


STYLE_PRESETS = load_style_presets()


INTERACTIVE_ENHANCEMENTS_LIBRARY = {
    "animated_counters": {
        "label": "Animated Counters",
        "purpose": "Highlight key metrics with numbers that ease upward when scrolled into view.",
        "placement": "Impact stats in hero sections, success metrics, or social proof bands.",
        "implementation": "Use data attributes for target values and trigger the animation when the element enters the viewport."
    },
    "parallax_timeline": {
        "label": "Parallax Timeline",
        "purpose": "Tell a story with milestones that move at different speeds for depth.",
        "placement": "Roadmaps, brand history, or process sections spanning full width.",
        "implementation": "Use layered backgrounds with translateY offsets and subtle scroll speed differences."
    },
    "testimonial_carousel": {
        "label": "Testimonial Carousel",
        "purpose": "Cycle through quotes automatically while allowing manual control.",
        "placement": "Trust band or social proof sections near CTAs.",
        "implementation": "Use a lightweight slider (CSS scroll snap or minimal JS) with play/pause on hover."
    },
    "hover_reveal_cards": {
        "label": "Hover Reveal Cards",
        "purpose": "Show additional context or imagery when hovering/focusing on service cards.",
        "placement": "Services/features grids or portfolio cards.",
        "implementation": "Flip or fade in extended copy via transform and opacity transitions; ensure keyboard focus support."
    },
    "micro_interaction_cta": {
        "label": "Magnetic CTA",
        "purpose": "Primary CTA button subtly follows cursor or pulses to draw attention.",
        "placement": "Hero or pricing sections.",
        "implementation": "Use small translate transforms tied to mouse position plus glow animation."
    },
    "lightweight_3d_embed": {
        "label": "Lightweight 3D Embed",
        "purpose": "Embed a small WebGL/Spline scene for a premium hero visual.",
        "placement": "Hero right column or a spotlight section.",
        "implementation": "Use an iframe/container with gentle rotation and provide fallback image."
    }
}


def build_interactive_context(selected_enhancements):
    """Return textual guidance for interactive enhancements."""
    if not selected_enhancements:
        return ""
    
    # normalize to list of ids
    normalized_ids = []
    for item in selected_enhancements:
        if isinstance(item, dict):
            item_id = item.get("id")
        else:
            item_id = item
        if item_id:
            normalized_ids.append(item_id)
    
    lines = []
    for enh_id in normalized_ids:
        spec = INTERACTIVE_ENHANCEMENTS_LIBRARY.get(enh_id)
        if not spec:
            continue
        lines.append(
            f"- {spec['label']}: {spec['purpose']} Place it in {spec['placement']}. Implementation notes: {spec['implementation']}. "
            "Include a short caption or subheading that explains the effect's benefit so users understand the premium feel."
        )
    
    if not lines:
        return ""
    
    header = (
        "INTERACTIVE ENHANCEMENT BLUEPRINT:\n"
        "Integrate the following micro-interactions. Each chosen effect must be implemented in HTML/CSS (with minimal JS if required), "
        "kept lightweight, and paired with a brief on-page explanation of why it matters.\n"
    )
    footer = "\nEnsure animations respect prefers-reduced-motion by providing graceful fallbacks."
    return header + "\n".join(lines) + footer


def build_style_context(style_key: str):
    """Return textual context and image hint for a given style preset."""
    preset = STYLE_PRESETS.get(style_key)
    if not preset:
        return "", ""
    
    palette = " / ".join(preset.get("palette", []))
    fonts = preset.get("fonts", [])
    heading_font = fonts[0] if fonts else "sans-serif"
    body_font = fonts[1] if len(fonts) > 1 else "sans-serif"
    mood = ", ".join(preset.get("mood", []))
    ui_accents = preset.get("ui_accents", "")
    instructions = preset.get("instructions", "")
    
    context = f"""
DESIGN STYLE GUIDANCE:
- Style Name: {preset.get('label', style_key.title())}
- Palette: {palette}
- Typography: Heading – {heading_font}, Body – {body_font}
- Mood: {mood}
- UI Accents: {ui_accents}
- Additional Instructions: {instructions}
Ensure every section, color choice, component spacing, and interaction embodies this style consistently.
"""
    image_hint = preset.get("image_prompt", "")
    return context, image_hint


DEFAULT_COMPONENT_LIBRARY = {
    "hero": {
        "label": "Hero Sections",
        "description": "Above-the-fold intros that mix bold headlines, supporting copy, CTAs, and imagery.",
        "variants": [
            {
                "id": "hero_split_image",
                "name": "Split Layout",
                "layout": "Two-column grid with text on the left and layered imagery on the right.",
                "content_focus": ["Headline", "Value bullets", "Primary CTA"],
                "visual_notes": "Use gradient accent behind the image and floating stat cards.",
                "best_for": ["saas", "agency", "product", "general"],
                "css_primitives": ["grid", "gradient-background", "rounded-3xl", "shadow-2xl"]
            }
        ]
    },
    "testimonials": {
        "label": "Testimonials",
        "description": "Social proof layouts to build trust.",
        "variants": [
            {
                "id": "testimonials_cards",
                "name": "Card Grid",
                "layout": "Responsive grid of testimonial cards with star ratings.",
                "content_focus": ["Quote", "Star rating", "Avatar"],
                "visual_notes": "Alternate background tints and include quotation marks.",
                "best_for": ["saas", "agency", "services", "general"],
                "css_primitives": ["grid", "rounded-2xl", "shadow-md", "accent-border"]
            }
        ]
    },
    "pricing": {
        "label": "Pricing Tables",
        "description": "Package comparisons with highlighted plan.",
        "variants": [
            {
                "id": "pricing_three_tiers",
                "name": "Three Tiers",
                "layout": "Three-column cards with middle plan elevated.",
                "content_focus": ["Plan name", "Price", "Feature list", "CTA"],
                "visual_notes": "Scale featured card and add badge chip.",
                "best_for": ["saas", "platforms", "services", "general"],
                "css_primitives": ["grid-cols-3", "featured-scale", "badge-chip", "icon-list"]
            }
        ]
    },
    "timeline": {
        "label": "Timeline / Process",
        "description": "Steps or milestones to explain journey or roadmap.",
        "variants": [
            {
                "id": "timeline_vertical_cards",
                "name": "Vertical Cards",
                "layout": "Stacked cards along a vertical line with alternating alignment.",
                "content_focus": ["Date", "Title", "Description"],
                "visual_notes": "Alternate alignment, add soft shadows, include connectors.",
                "best_for": ["agency", "case-study", "education", "general"],
                "css_primitives": ["timeline", "shadow-lg", "connector-line", "accent-dot"]
            }
        ]
    }
}


def load_component_library():
    """Load the component library definition shared across the stack."""
    try:
        with open(COMPONENT_LIBRARY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and data:
                return data
    except FileNotFoundError:
        print("component_library.json not found. Using default component snippets.")
    except Exception as exc:
        print(f"Error loading component library: {exc}. Using defaults.")
    return DEFAULT_COMPONENT_LIBRARY


COMPONENT_LIBRARY = load_component_library()

BUSINESS_TYPE_KEYWORDS = {
    "saas": ["saas", "software", "platform", "startup", "app", "tech"],
    "agency": ["agency", "studio", "consult", "freelance", "creative"],
    "services": ["service", "salon", "spa", "therapy", "coaching"],
    "product": ["product", "ecommerce", "shop", "store", "retail"],
    "portfolio": ["portfolio", "photography", "designer", "artist"],
    "education": ["school", "academy", "bootcamp", "education", "course"],
    "case-study": ["case study", "success story"],
    "general": []
}


def infer_project_tags(text: str, template_name: str = "") -> set:
    """Infer high-level project tags from the user prompt and template name."""
    tags = set()
    haystack = f"{text or ''} {template_name or ''}".lower()
    for tag, keywords in BUSINESS_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword and keyword in haystack:
                tags.add(tag)
                break
    if not tags:
        tags.add("general")
    return tags


def select_component_variants(tags: set) -> dict:
    """Select the best variant per section based on inferred tags."""
    selections = {}
    for section_key, section_data in COMPONENT_LIBRARY.items():
        variants = section_data.get("variants", [])
        chosen = None
        for variant in variants:
            variant_tags = set(variant.get("best_for", []))
            if variant_tags.intersection(tags):
                chosen = variant
                break
        if not chosen and variants:
            chosen = variants[0]
        if chosen:
            selections[section_key] = {
                "section_label": section_data.get("label", section_key.title()),
                "section_description": section_data.get("description", ""),
                "variant": chosen
            }
    return selections


def build_component_context(user_prompt: str, template_name: str = "", preferred_sections: dict = None):
    """Return selected component variants (respecting user preferences) and blueprint text."""
    tags = infer_project_tags(user_prompt, template_name)
    selections = select_component_variants(tags)
    
    if preferred_sections:
        for section_key, prefs in preferred_sections.items():
            section_data = COMPONENT_LIBRARY.get(section_key)
            if not section_data:
                continue
            include_section = prefs.get("include", True)
            if not include_section:
                selections.pop(section_key, None)
                continue
            desired_variant_id = prefs.get("variant")
            variant = None
            if desired_variant_id:
                variant = next(
                    (v for v in section_data.get("variants", []) if v.get("id") == desired_variant_id),
                    None
                )
            if not variant and section_data.get("variants"):
                variant = section_data["variants"][0]
            if variant:
                selections[section_key] = {
                    "section_label": section_data.get("label", section_key.title()),
                    "section_description": section_data.get("description", ""),
                    "variant": variant
                }

    if not selections:
        return {}, ""
    lines = [
        "COMPONENT BLUEPRINT:",
        "Assemble the page using these curated section patterns for consistency."
    ]
    for section_key, data in selections.items():
        variant = data["variant"]
        content_focus = ", ".join(variant.get("content_focus", []))
        css_primitives = ", ".join(variant.get("css_primitives", []))
        lines.append(f"- {data['section_label']} → {variant.get('name')}: {variant.get('layout', '')}")
        if content_focus:
            lines.append(f"  Content focus: {content_focus}")
        if variant.get("visual_notes"):
            lines.append(f"  Visual notes: {variant['visual_notes']}")
        if css_primitives:
            lines.append(f"  CSS primitives: {css_primitives}")
    return selections, "\n".join(lines)


# Define the prompt template for website generation
website_prompt_template = """
Create a single HTML page based on this description: {user_prompt}

{template_context}

CONTEXT-AWARE DESIGN GUIDANCE:
Analyze the request and apply appropriate design:

FOR PROFESSIONAL/RESUME WEBSITES:
- Clean, minimal design with professional colors (navy, gray, white)
- Sans-serif fonts (Roboto, Inter, Open Sans)
- If a profile photo is uploaded: Use it prominently in hero or sidebar
- Include sections: About, Skills, Experience, Education, Contact
- Use {{image: profile}} for the uploaded profile photo
- Use {{image: hero-background}} for professional backgrounds

FOR RESTAURANT/FOOD BUSINESSES:
- Warm, inviting colors (orange, brown, cream, gold)
- If a menu image/PDF is uploaded: Reference it for food styling
- If restaurant photos are uploaded: Use them in gallery sections
- Use {{image: hero-banner}}, {{image: food-dish}}, {{image: interior}}, {{image: ambiance}}
- Do NOT use profile photos - use food/restaurant imagery instead

FOR E-COMMERCE/PRODUCT WEBSITES:
- If product images are uploaded: Use {{image: product}} prominently
- If logo is uploaded: Use {{image: logo}} in header
- Product-focused layouts with clear CTAs
- Use {{image: product-showcase}}, {{image: product-detail}}, {{image: feature}}

FOR CREATIVE PORTFOLIOS:
- Bold, modern design with vibrant colors
- If portfolio images/work samples are uploaded: Use them in showcase sections
- Use {{image: portfolio-item-1}}, {{image: portfolio-item-2}}, etc.
- Do NOT use profile photos unless specifically for "About" section

FOR SERVICE BUSINESSES (Salon, Barber, Spa, etc.):
- If service images are uploaded: Use them to showcase services
- If before/after images: Use {{image: before-after}}
- If team photos: Use {{image: team}}, {{image: staff}}
- Use {{image: service-1}}, {{image: service-2}}, {{image: interior}}

INTELLIGENT IMAGE HANDLING - CRITICAL:
1. IMAGE LABELS MUST MATCH CONTEXT:
   - For FARM SHOP: Use labels like {{image: farm-produce}}, {{image: fresh-vegetables}}, {{image: farm-stand}}, {{image: organic-products}}, {{image: farmers-market}}
   - For RESTAURANT: Use {{image: food-dish}}, {{image: restaurant-interior}}, {{image: chef}}, {{image: dining-ambiance}}
   - For SALON: Use {{image: salon-interior}}, {{image: haircut-style}}, {{image: beauty-treatment}}, {{image: salon-chair}}
   - For RETAIL: Use {{image: store-front}}, {{image: product-display}}, {{image: shopping-experience}}
   - For PROFESSIONAL: Use {{image: profile}}, {{image: office}}, {{image: team}}, {{image: workspace}}

2. UPLOADED IMAGES:
   - First uploaded image is available as {{image: profile}}
   - Additional images available as {{image: image-2}}, {{image: image-3}}, etc.
   - ALWAYS use uploaded images when available
   - Use uploaded images by their labels - they will be embedded directly

3. IMAGE PLACEHOLDER NAMING RULES:
   - {{image: profile}} - For personal/professional headshots (FIRST UPLOADED IMAGE)
   - {{image: product}} - For product/e-commerce items
   - {{image: hero-banner}} - For main hero sections
   - {{image: food-dish}}, {{image: restaurant-interior}} - For food businesses
   - {{image: portfolio-item-N}} - For portfolio showcases
   - {{image: service-1}}, {{image: service-2}} - For service businesses
   - {{image: image-2}}, {{image: image-3}} - For additional uploaded images
   - **Use SPECIFIC, CONTEXT-RELEVANT labels that match the business type**
   - **NEVER use generic labels like "nature" or "landscape" - be specific to the business**

IMPORTANT - USE PROVIDED DATA:
- If a resume/document was uploaded, MUST use the actual data provided
- Do NOT make up or hallucinate contact information, experience, or details
- Use ONLY the information from the uploaded files
- If specific details are missing, leave them blank or use placeholder text

CRITICAL RULES - MUST FOLLOW EXACTLY:
1. Output ONLY valid HTML (no explanations or markdown).
2. Include CSS in <style> tags and minimal JavaScript in <script> tags.
3. **NEVER use <img src="..."> with actual URLs**
4. **For EVERY image, use EXACTLY this format: {{image: descriptive-label}}**
   - Example: {{image: profile}}, {{image: hero-banner}}, {{image: food-dish}}
   - Replace the entire <img> tag with just the placeholder
   - WRONG: <img src="https://...">
   - CORRECT: {{image: profile}}
5. **IMAGE LABELS MUST BE CONTEXT-SPECIFIC:**
   - Read the user description carefully
   - If it mentions "farm shop" → use {{image: farm-produce}}, {{image: fresh-vegetables}}, etc.
   - If it mentions "restaurant" → use {{image: food-dish}}, {{image: restaurant-interior}}, etc.
   - If it mentions "salon" → use {{image: salon-interior}}, {{image: haircut-style}}, etc.
   - **NEVER use vague labels like "nature", "landscape", "road", "lights"**
   - **Always match image labels to the specific business type mentioned**
6. Keep CSS concise. Use flexbox/grid for layout.
7. Make it responsive and visually appealing.
8. Ensure the page is complete and ready to save as .html.
9. Do NOT generate any URLs or fetch images - only use {{image: label}} placeholders.
"""

# --------------------------------------------------
# Helper: replace {{image: label}} with Unsplash URLs
# --------------------------------------------------

import requests, random
from urllib.parse import urljoin

def fetch_unsplash(query: str) -> str:
    """Fetch a random photo from Unsplash based on query."""
    print(f"DEBUG: Unsplash - Original query: '{query}'")
    
    if not os.getenv("UNSPLASH_ACCESS_KEY"):
        print("DEBUG: Unsplash - No access key configured")
        return ""
    
    # Improve query for better food images with context
    improved_query = query
    if "biriyani" in query.lower() or "biryani" in query.lower():
        improved_query = "biryani rice dish indian food"
    elif "lamb" in query.lower() and any(word in query.lower() for word in ["rogan", "josh", "food", "dish", "curry"]):
        improved_query = "lamb rogan josh kashmiri curry indian food"
    elif "lamb" in query.lower() and "food" in query.lower():
        improved_query = "lamb meat dish food"
    elif "food" in query.lower() or "dish" in query.lower():
        improved_query = f"{query} food cuisine dish"
    elif "cleaning" in query.lower():
        improved_query = "professional cleaning service"
    elif "portfolio" in query.lower():
        improved_query = "professional portfolio work"
    
    print(f"DEBUG: Unsplash - Improved query: '{improved_query}'")
    
    url = 'https://api.unsplash.com/photos/random'
    params = {'query': improved_query, 'orientation': 'landscape'}
    headers = {'Authorization': f'Client-ID {os.getenv("UNSPLASH_ACCESS_KEY")}'}
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.ok:
            result_url = r.json()["urls"]["regular"]
            print(f"DEBUG: Unsplash - Successfully fetched image for '{query}': {result_url[:50]}...")
            return result_url
        else:
            print(f"DEBUG: Unsplash - API error: {r.status_code}")
    except Exception as e:
        print(f"DEBUG: Unsplash - API error: {e}")
    return ""

def generate_flux_image(prompt: str) -> str:
    """Generate an image using FLUX.1-dev via Hugging Face API."""
    print(f"DEBUG: FLUX.1-dev - Original prompt: '{prompt}'")
    
    if not HF_AVAILABLE or not os.getenv("HF_TOKEN"):
        print("FLUX.1-dev not available, trying Stable Diffusion 3.5")
        return generate_stable_diffusion_image(prompt)
    
    try:
        # Initialize the FLUX.1-dev model
        client = InferenceApi(
            repo_id="black-forest-labs/FLUX.1-dev",
            token=os.getenv("HF_TOKEN")
        )
        
        # Improve prompt for better results with context
        improved_prompt = prompt
        if "biriyani" in prompt.lower() or "biryani" in prompt.lower():
            improved_prompt = "delicious biryani rice dish, indian cuisine, food photography, high quality"
        elif "lamb" in prompt.lower() and any(word in prompt.lower() for word in ["rogan", "josh", "food", "dish", "curry"]):
            improved_prompt = "lamb rogan josh, kashmiri curry, indian dish, food photography, delicious meal, high quality"
        elif "lamb" in prompt.lower() and "food" in prompt.lower():
            improved_prompt = "lamb meat dish, food photography, delicious meal, high quality"
        elif "food" in prompt.lower() or "dish" in prompt.lower():
            improved_prompt = f"{prompt}, food photography, delicious meal, high quality, professional"
        elif "cleaning" in prompt.lower():
            improved_prompt = "professional cleaning service, clean, modern, high quality"
        elif "portfolio" in prompt.lower():
            improved_prompt = "professional portfolio work, modern design, high quality"
        
        print(f"DEBUG: FLUX.1-dev - Improved prompt: '{improved_prompt}'")
        
        # Generate image
        response = client(
            inputs=improved_prompt,
            parameters={
                "num_inference_steps": 28,
                "guidance_scale": 3.5,
                "width": 1024,
                "height": 768
            }
        )
        
        # Convert response to base64 image URL
        if isinstance(response, bytes):
            import base64
            image_b64 = base64.b64encode(response).decode()
            print(f"DEBUG: FLUX.1-dev - Successfully generated image for '{prompt}'")
            return f"data:image/png;base64,{image_b64}"
        else:
            print(f"DEBUG: FLUX.1-dev - Unexpected response type: {type(response)}")
            return generate_stable_diffusion_image(prompt)
            
    except Exception as e:
        print(f"DEBUG: FLUX.1-dev API error: {e}")
        # Fallback to Stable Diffusion
        return generate_stable_diffusion_image(prompt)

def generate_stable_diffusion_image(prompt: str) -> str:
    """Generate an image using Stable Diffusion 3.5 Large (Free)."""
    print(f"DEBUG: Stable Diffusion - Original prompt: '{prompt}'")
    
    if not HF_AVAILABLE:
        print("Stable Diffusion not available, falling back to Unsplash")
        return fetch_unsplash(prompt)
    
    try:
        # Initialize Stable Diffusion 3.5 Large (Free)
        client = InferenceApi(
            repo_id="stabilityai/stable-diffusion-3-5-large"
        )
        
        # Improve prompt for better results with context
        improved_prompt = prompt
        if "biriyani" in prompt.lower() or "biryani" in prompt.lower():
            improved_prompt = "delicious biryani rice dish, indian cuisine, food photography, high quality, detailed"
        elif "lamb" in prompt.lower() and any(word in prompt.lower() for word in ["rogan", "josh", "food", "dish", "curry"]):
            improved_prompt = "lamb rogan josh, kashmiri curry, indian dish, food photography, delicious meal, high quality, detailed"
        elif "lamb" in prompt.lower() and "food" in prompt.lower():
            improved_prompt = "lamb meat dish, food photography, delicious meal, high quality, detailed"
        elif "food" in prompt.lower() or "dish" in prompt.lower():
            improved_prompt = f"{prompt}, food photography, delicious meal, high quality, professional, detailed"
        elif "cleaning" in prompt.lower():
            improved_prompt = "professional cleaning service, clean, modern, high quality, detailed"
        elif "portfolio" in prompt.lower():
            improved_prompt = "professional portfolio work, modern design, high quality, detailed"
        
        print(f"DEBUG: Stable Diffusion - Improved prompt: '{improved_prompt}'")
        
        # Generate image
        response = client(
            inputs=improved_prompt,
            parameters={
                "num_inference_steps": 25,
                "guidance_scale": 7.5,
                "width": 1024,
                "height": 768
            }
        )
        
        # Convert response to base64 image URL
        if isinstance(response, bytes):
            import base64
            image_b64 = base64.b64encode(response).decode()
            print(f"DEBUG: Stable Diffusion - Successfully generated image for '{prompt}'")
            return f"data:image/png;base64,{image_b64}"
        else:
            print(f"DEBUG: Stable Diffusion - Unexpected response type: {type(response)}")
            return fetch_unsplash(prompt)
            
    except Exception as e:
        print(f"DEBUG: Stable Diffusion API error: {e}")
        # Fallback to Unsplash
        return fetch_unsplash(prompt)

def validate_and_repair_html(html: str) -> str:
    """Validate and repair common HTML layout issues."""
    if not html or not html.strip():
        return html
    
    html = html.strip()
    
    # Strip markdown fences like ```html ... ```
    html = re.sub(r'^\s*```(?:html)?\s*', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\s*```\s*$', '', html).strip()
    
    # Fix common layout issues:
    
    # 1. Fix incomplete grid containers in projects section
    html = re.sub(
        r'(<section[^>]*>.*?<h2[^>]*>Featured Projects</h2>.*?)(<div class="card-hover[^>]*>.*?</div>)(.*?</section>)',
        lambda m: f"{m.group(1)}<div class='grid md:grid-cols-2 lg:grid-cols-3 gap-8'>{m.group(2)}</div>{m.group(3)}",
        html,
        flags=re.DOTALL
    )
    
    # 2. Fix orphaned skill bars without proper containers
    html = re.sub(
        r'(<section[^>]*>.*?<h2[^>]*>Skills[^<]*</h2>.*?)(<div class="space-y-4">\s*<div class="flex justify-between[^>]*>.*?</div>\s*<div class="bg-gray-200[^>]*>.*?</div>\s*</div>)(.*?</section>)',
        lambda m: f"{m.group(1)}<div class='max-w-4xl mx-auto space-y-8'>{m.group(2)}</div>{m.group(3)}",
        html,
        flags=re.DOTALL
    )
    
    # 3. Fix orphaned skill tags (floating span elements)
    html = re.sub(
        r'(\s*<span class="px-4 py-2 bg-gray-100[^>]*>[^<]*</span>\s*)+',
        lambda m: f"<div class='flex flex-wrap gap-3 mt-8'>{m.group(0)}</div>",
        html
    )
    
    # 4. Fix incomplete project cards
    html = re.sub(
        r'(<div class="card-hover[^>]*>.*?</div>)(\s*<div class="flex space-x-4">.*?</div>\s*</div>\s*</div>)',
        lambda m: f"{m.group(1)}{m.group(2)}",
        html
    )
    
    # 5. Fix duplicate container wrappers (caused by earlier regex repairs)
    html = re.sub(
        r'(<div class=[\'"]container[^>]*>)(\s*\1)+',
        r'\1',
        html
    )
    
    # 6. Fix duplicate closing tags
    html = re.sub(r'(</div>){4,}', lambda m: '</div></div></div>', html)
    
    return html.strip()

def fill_images(html: str, prompt: str, uploaded_images: dict = None, style_image_hint: str = "") -> str:
    """Replace image placeholders with actual URLs or uploaded images.
    
    Args:
        html: HTML content with {{image: label}} placeholders
        prompt: User prompt for context
        uploaded_images: Dict of {label: data_url} for uploaded images
    """
    if uploaded_images is None:
        uploaded_images = {}
    
    print(f"DEBUG: fill_images - User prompt context: '{prompt}'")
    print(f"DEBUG: fill_images - Processing HTML for image replacement...")
    print(f"DEBUG: fill_images - Uploaded images keys: {list(uploaded_images.keys())}")
    print(f"DEBUG: fill_images - Uploaded images content: {uploaded_images}")
    print(f"DEBUG: fill_images - Original HTML snippet: {html[:500]}...")
    
    # First, clean up any malformed img tags BEFORE processing placeholders
    # Handle double-wrapped: <img src="<img src="https://...">
    html = re.sub(r'<img\s+src="<img\s+src="[^"]*"\s+alt="([^"]*)"[^>]*>"[^>]*>', lambda m: f'{{{{image: {m.group(1)}}}}}', html)
    
    # Handle single wrapped with URL: <img src="https://...">
    html = re.sub(r'<img\s+src="https?://[^"]*"\s+alt="([^"]*)">', lambda m: f'{{{{image: {m.group(1)}}}}}', html)
    
    # Handle HTML entities in URLs (from browser rendering): &lt;img src=&quot;
    html = re.sub(r'<img\s+src="&lt;img\s+src=&quot;([^&]*)&quot;[^&]*&amp;[^&]*&quot;[^>]*>"[^>]*>', lambda m: f'{{{{image: {m.group(1)}}}}}', html)
    html = re.sub(r'&lt;img\s+src=&quot;https?://[^&]*&quot;[^>]*&gt;', lambda m: '{{image: restaurant-interior}}', html)
    
    # Handle specific case: <img src="&lt;img src="URL" alt="profile"&gt;" alt="profile">
    html = re.sub(r'<img\s+src="&lt;img\s+src="([^"]+)"\s+alt="([^"]+)"&gt;"\s+alt="([^"]+)">', lambda m: f'{{{{image: {m.group(2)}}}}}', html)
    
    # Handle case with HTML entities: &lt;img src="URL" alt="profile"&gt;
    html = re.sub(r'&lt;img\s+src="([^"]+)"\s+alt="([^"]+)"&gt;', lambda m: f'{{{{image: {m.group(2)}}}}}', html)
    
    # Handle the specific LinkedIn URL pattern you're experiencing
    # Pattern: <img src="&lt;img src="URL...&amp;...&quot;" alt="profile">
    matches_before = len(re.findall(r'<img\s+src="&lt;img\s+src="[^"]*?&quot;[^>]*&gt;"\s+alt="[^"]+">', html))
    if matches_before > 0:
        print(f"DEBUG: Found {matches_before} LinkedIn URL patterns to fix")
    html = re.sub(r'<img\s+src="&lt;img\s+src="([^"]*?)(?:&amp;[^&]*)*&quot;[^>]*&gt;"\s+alt="([^"]+)">', lambda m: f'{{{{image: {m.group(2)}}}}}', html)
    matches_after = len(re.findall(r'<img\s+src="&lt;img\s+src="[^"]*?&quot;[^>]*&gt;"\s+alt="[^"]+">', html))
    if matches_before > 0 and matches_after == 0:
        print(f"DEBUG: Successfully fixed all LinkedIn URL patterns")
    
    # Handle any case that ends with &quot; instead of proper closing
    html = re.sub(r'<img\s+src="&lt;img\s+src="([^"]*)&quot;[^>]*&gt;"\s+alt="([^"]+)">', lambda m: f'{{{{image: {m.group(2)}}}}}', html)
    
    # Handle the EXACT pattern you're seeing with LinkedIn URLs and spaces
    # Pattern: <img src="&lt;img src=" https://media.licdn.com/...&amp;...&quot;" alt="profile">
    html = re.sub(r'<img\s+src="&lt;img\s+src="([^"]*https://media\.licdn\.com[^"]*)\&quot;[^>]*&gt;"\s+alt="([^"]+)">', lambda m: f'{{{{image: {m.group(2)}}}}}', html)
    
    # Handle any nested img tags with HTML entities - more aggressive approach
    html = re.sub(r'<img\s+src="&lt;img\s+src="[^"]*&quot;[^>]*&gt;"\s+alt="([^"]+)">', lambda m: f'{{{{image: {m.group(1)}}}}}', html)
    
    # Also handle cases where the nested img has proper closing but entities
    html = re.sub(r'<img\s+src="&lt;img\s+src="[^"]*"[^>]*&gt;"\s+alt="([^"]+)">', lambda m: f'{{{{image: {m.group(1)}}}}}', html)
    
    print(f"DEBUG: HTML after cleanup: {html[:500]}...")
    
    # Check for image placeholders before replacement - try multiple patterns
    patterns_to_check = [
        (r'\{\{image:\s*(.*?)\s*\}\}', 'Double braces'),
        (r'{{image:\s*(.*?)\s*}}', 'Single braces'),
        (r'\{image:\s*(.*?)\s*\}', 'Single brace'),
        (r'image:\s*(.*?)\s*', 'Just image:')
    ]
    
    placeholders = []
    for pattern, name in patterns_to_check:
        found = re.findall(pattern, html)
        if found:
            print(f"DEBUG: Found {name} placeholders: {found}")
            placeholders.extend(found)
    
    if not placeholders:
        print("DEBUG: No image placeholders found!")
        # Let's see what image-related content exists
        img_tags = re.findall(r'<img[^>]*>', html)
        print(f"DEBUG: Found img tags: {img_tags[:3]}")
        src_attrs = re.findall(r'src="([^"]*)"', html)
        print(f"DEBUG: Found src attributes: {src_attrs[:3]}")
    else:
        print(f"DEBUG: Total placeholders found: {placeholders}")
    
    def repl(m):
        label = m.group(1).strip()
        print(f"DEBUG: Processing placeholder: '{label}'")
        
        # Check if this image was uploaded
        if label in uploaded_images:
            print(f"DEBUG: Using uploaded image for '{label}': {uploaded_images[label][:50]}...")
            return f'src="{uploaded_images[label]}"'  # Return src attribute with URL
        
        # Special handling for profile images
        if "profile" in label.lower() or "avatar" in label.lower() or "photo" in label.lower():
            print(f"Profile image detected for '{label}' - generating professional headshot")
            # Generate professional profile/headshot image
            profile_prompt = f"professional headshot portrait, {label}, high quality, business professional"
            if style_image_hint:
                profile_prompt += f", in the style of {style_image_hint}"
            photo = generate_flux_image(profile_prompt) or \
                    generate_stable_diffusion_image(profile_prompt) or \
                    f"https://picsum.photos/seed/{label}/400/400"
            print(f"Generated profile image for '{label}': {photo[:50]}...")
            return f'src="{photo}"'  # Return src attribute with URL
        
        # Otherwise, generate image using FLUX.1-dev
        # The label itself is context-specific (e.g., "farm-produce", "food-dish", "salon-interior")
        # Use it directly for better image matching
        image_prompt = label
        if style_image_hint:
            image_prompt = f"{label}, {style_image_hint}"
        photo = generate_flux_image(image_prompt) or \
                f"https://picsum.photos/seed/{label}/800/500"
        print(f"Generated image for '{label}': {photo[:50]}...")
        return f'src="{photo}"'  # Return src attribute with URL
    
    # Try different replacement patterns
    replacement_patterns = [
        (r'src="\{\{image:\s*(.*?)\s*\}\}"', 'src with double braces'),
        (r'src="{{image:\s*(.*?)\s*}}"', 'src with single braces'),
        (r'src="\{image:\s*(.*?)\s*\}"', 'src with single brace'),
        (r'src="image:\s*(.*?)"', 'src with image:'),
        (r'\{\{image:\s*(.*?)\s*\}\}', 'standalone double braces'),
        (r'{{image:\s*(.*?)\s*}}', 'standalone single braces'),
        (r'\{image:\s*(.*?)\s*\}', 'standalone single brace'),
        (r'image:\s*(.*?)\s*', 'just image:')
    ]
    
    for pattern, name in replacement_patterns:
        matches = re.findall(pattern, html)
        if matches:
            print(f"DEBUG: Pattern '{name}' found: {matches[:5]}")  # First 5 matches
            html = re.sub(pattern, repl, html)
            print(f"DEBUG: Replaced placeholders using pattern: {name}")
            break  # Stop after first successful replacement
    else:
        print("DEBUG: No placeholders found to replace")
    
    # FINAL CLEANUP: Remove any remaining malformed img tags that weren't caught
    print("DEBUG: Performing final cleanup of malformed HTML...")
    html = re.sub(r'<img\s+src="&lt;img[^>]*>"[^>]*>', '', html)  # Remove any remaining nested img tags
    html = re.sub(r'&lt;img[^>]*&gt;', '', html)  # Remove any remaining HTML entity img tags
    print(f"DEBUG: Final cleanup completed")
    
    # Final check for any remaining placeholders
    remaining_patterns = [r'\{\{image:.*?\}\}', r'{{image:.*?}}', r'\{image:.*?\}']
    remaining = []
    for pattern in remaining_patterns:
        found = re.findall(pattern, html)
        remaining.extend(found)
    
    if remaining:
        print(f"DEBUG: WARNING - Remaining placeholders: {remaining}")
        # Try one more aggressive replacement
        html = re.sub(r'\{?{image:\s*(.*?)\s*\}?', lambda m: f'<img src="https://picsum.photos/seed/{m.group(1).strip()}/800/500" alt="{m.group(1).strip()}">', html)
        print("DEBUG: Applied aggressive replacement")
    else:
        print("DEBUG: All placeholders replaced successfully")
    
    return html

def fetch_website_design(url: str) -> str:
    """Fetch a reference website and extract design information."""
    try:
        response = requests.get(url, timeout=10)
        if response.ok:
            html_content = response.text
            
            # Extract useful design information
            design_info = f"REFERENCE WEBSITE URL: {url}\n\n"
            
            # Extract title
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', html_content, re.IGNORECASE)
            if title_match:
                design_info += f"Website Title: {title_match.group(1)}\n"
            
            # Extract meta description
            desc_match = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', html_content, re.IGNORECASE)
            if desc_match:
                design_info += f"Description: {desc_match.group(1)}\n"
            
            # Extract color information from CSS
            css_match = re.search(r'<style[^>]*>(.*?)</style>', html_content, re.IGNORECASE | re.DOTALL)
            if css_match:
                css_content = css_match.group(1)[:1000]
                # Look for color definitions
                colors = re.findall(r'(#[0-9a-fA-F]{6}|rgb\([^)]+\)|[a-z-]+:\s*[a-z]+)', css_content)
                if colors:
                    design_info += f"Color Scheme: {', '.join(set(colors[:5]))}\n"
            
            # Extract fonts
            font_match = re.findall(r'font-family:\s*([^;,}]+)', html_content)
            if font_match:
                design_info += f"Fonts Used: {', '.join(set(font_match[:3]))}\n"
            
            # Extract structure info
            has_header = bool(re.search(r'<header|<nav', html_content, re.IGNORECASE))
            has_footer = bool(re.search(r'<footer', html_content, re.IGNORECASE))
            has_hero = bool(re.search(r'hero|banner|jumbotron', html_content, re.IGNORECASE))
            
            design_info += f"\nLayout Elements: "
            elements = []
            if has_header:
                elements.append("Header/Navigation")
            if has_hero:
                elements.append("Hero Section")
            if has_footer:
                elements.append("Footer")
            design_info += ", ".join(elements) if elements else "Standard layout"
            
            # Add HTML structure sample
            design_info += f"\n\nHTML Structure Sample (first 2000 chars):\n{html_content[:2000]}\n"
            
            design_info += "\n\nINSTRUCTIONS: Analyze this website's design, layout, color scheme, typography, and structure. Create a similar design for the new website with the same professional appearance and layout style."
            
            return design_info
    except Exception as e:
        print(f"Error fetching reference website: {e}")
        return None

def load_template(template_name):
    """Load a template file and return its content."""
    template_path = f"templates/{template_name}.html"
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # For portfolio/resume templates, add profile image placeholder
        if 'portfolio' in template_name.lower() or 'resume' in template_name.lower():
            print(f"DEBUG: Adding profile image placeholder for {template_name}")
            # Replace common profile image patterns with placeholder
            content = content.replace(
                'src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d',
                'src="{{image: profile}}"'
            )
            content = content.replace(
                'src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e',
                'src="{{image: profile}}"'
            )
            # Also replace any hero section images
            content = re.sub(
                r'src="https://images\.unsplash\.com/photo-[^"]*\.(?:jpg|jpeg|png)"',
                'src="{{image: profile}}"',
                content
            )
            print(f"DEBUG: Profile image placeholders added to template")
        
        return content
    except FileNotFoundError:
        print(f"Template {template_name} not found")
        return None

def process_reference_files(files):
    """Process multiple uploaded reference files and return content/info for prompt context."""
    if not files or len(files) == 0:
        return None
    
    reference_contents = []
    
    for idx, file in enumerate(files, 1):
        if not file or file.filename == '':
            continue
        
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1].lower()
        
        try:
            if file_ext in ['.txt', '.md']:
                # Text files - read as string
                content = file.read().decode('utf-8', errors='ignore')
                reference_contents.append(f"[File {idx}: {filename}]\n{content[:2000]}")  # Limit to 2000 chars per file
            
            elif file_ext in ['.pdf']:
                # For PDF, try to extract text using basic parsing
                file.seek(0)
                pdf_data = file.read()
                # Simple text extraction from PDF (basic approach)
                try:
                    # Try UTF-8 decoding first
                    pdf_text = pdf_data.decode('utf-8', errors='ignore')
                    # Extract readable text - keep more characters
                    pdf_text = ''.join(c for c in pdf_text if c.isprintable() or c in '\n\t ')
                    # Clean up whitespace
                    pdf_text = ' '.join(pdf_text.split())
                    # Limit to 3000 chars to preserve more content
                    pdf_text = pdf_text[:3000]
                    
                    if pdf_text.strip():
                        reference_contents.append(f"[File {idx}: PDF '{filename}']\nRESUME/DOCUMENT CONTENT:\n{pdf_text}")
                        print(f"Extracted PDF content ({len(pdf_text)} chars): {pdf_text[:200]}...")
                    else:
                        reference_contents.append(f"[File {idx}: PDF '{filename}'] - Resume/document uploaded. Please describe key details (name, email, phone, experience, skills) in the prompt.")
                except Exception as e:
                    print(f"PDF extraction error: {e}")
                    reference_contents.append(f"[File {idx}: PDF '{filename}'] - Resume/document uploaded. Please describe key details in the prompt.")
            
            elif file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                # For images, encode as base64 and include reference
                file.seek(0)
                img_data = file.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')[:500]  # Limit base64 to 500 chars
                reference_contents.append(f"[File {idx}: Image '{filename}' - {len(img_data)} bytes]\nImage data (base64): {img_base64}...\nUse this profile/product image in the website design. Include it as a visual element.")
            
            elif file_ext in ['.doc', '.docx']:
                # For Word docs, note it was uploaded
                reference_contents.append(f"[File {idx}: Word document '{filename}'] - Document uploaded. Please describe its content in the prompt.")
            
            else:
                reference_contents.append(f"[File {idx}: '{filename}'] - File uploaded. Please describe its content in the prompt.")
        
        except Exception as e:
            print(f"Error processing reference file {filename}: {e}")
            reference_contents.append(f"[File {idx}: '{filename}'] - File uploaded but could not be processed. Please describe in the prompt.")
            continue
    
    if reference_contents:
        return "\n".join(reference_contents)
    return None

@app.route('/')
def index():
    return render_template(
        'index.html',
        style_presets_json=json.dumps(STYLE_PRESETS),
        component_library_json=json.dumps(COMPONENT_LIBRARY),
        component_library=COMPONENT_LIBRARY,
        interactive_enhancements=INTERACTIVE_ENHANCEMENTS_LIBRARY,
        interactive_enhancements_json=json.dumps(INTERACTIVE_ENHANCEMENTS_LIBRARY)
    )

@app.route('/generate', methods=['POST'])
def generate_website():
    user_prompt = request.form.get('prompt', '')
    selected_template = request.form.get('selected_template', '')
    reference_url = request.form.get('reference_url', '')
    reference_files = request.files.getlist('reference_files')
    style_preset = request.form.get('style_preset', '')
    preferred_sections_raw = request.form.get('preferred_sections', '')
    interactive_enhancements_raw = request.form.get('interactive_enhancements', '')
    
    preferred_sections = None
    if preferred_sections_raw:
        try:
            preferred_sections = json.loads(preferred_sections_raw)
        except json.JSONDecodeError:
            print("WARNING: Invalid preferred_sections payload; ignoring.")
    
    interactive_enhancements = None
    if interactive_enhancements_raw:
        try:
            interactive_enhancements = json.loads(interactive_enhancements_raw)
        except json.JSONDecodeError:
            print("WARNING: Invalid interactive_enhancements payload; ignoring.")
    
    # Handle profile image
    profile_image = request.files.get('profile_image')
    profile_image_url = request.form.get('profile_image_url', '')
    
    if not user_prompt:
        return jsonify({'error': 'Prompt is required'}), 400
    
    # Load template if selected
    template_content = ""
    if selected_template:
        template_content = load_template(selected_template)
        if template_content:
            print(f"Loaded template: {selected_template}")
    
    llm = get_llm()
    if not llm:
        return jsonify({'error': 'Failed to initialize LLM'}), 500
    
    # Process reference URL if provided
    reference_context = ""
    if reference_url:
        url_content = fetch_website_design(reference_url)
        if url_content:
            reference_context = f"\n\nREFERENCE WEBSITE DESIGN:\n{url_content}"
    
    # Process profile image if provided
    profile_context = ""
    uploaded_images = {}  # Initialize empty dictionary
    
    print(f"DEBUG: Profile image file: {profile_image}")
    print(f"DEBUG: Profile image URL: {profile_image_url}")
    
    if profile_image:
        try:
            img_data = profile_image.read()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            # Store as uploaded image for placeholder replacement
            uploaded_images['profile'] = f"data:image/{profile_image.filename.split('.')[-1]};base64,{img_base64}"
            profile_context = f"\n\nPROFILE IMAGE: User has uploaded a profile picture. Use {{image: profile}} placeholder to include it in the design."
            print(f"DEBUG: Profile image uploaded: {profile_image.filename}")
            print(f"DEBUG: Stored profile image with key 'profile': {uploaded_images['profile'][:50]}...")
        except Exception as e:
            print(f"DEBUG: Error processing profile image: {e}")
    elif profile_image_url:
        try:
            # Validate URL
            if profile_image_url.startswith('http://') or profile_image_url.startswith('https://'):
                uploaded_images['profile'] = profile_image_url
                profile_context = f"\n\nPROFILE IMAGE: User provided profile image URL: {profile_image_url}. Use {{image: profile}} placeholder to include it in the design."
                print(f"DEBUG: Profile image URL provided: {profile_image_url}")
                print(f"DEBUG: Stored profile URL with key 'profile': {uploaded_images['profile']}")
            else:
                print(f"DEBUG: Invalid profile image URL: {profile_image_url}")
        except Exception as e:
            print(f"DEBUG: Error processing profile image URL: {e}")
    else:
        print("DEBUG: No profile image provided")
    
    print(f"DEBUG: Final uploaded_images keys: {list(uploaded_images.keys())}")
    
    # Process reference files if uploaded
    if reference_files and len(reference_files) > 0:
        ref_content = process_reference_files(reference_files)
        if ref_content:
            reference_context += f"\n\nREFERENCE DOCUMENTS:\n{ref_content}"
        
        # Extract uploaded images and convert to data URLs
        for idx, file in enumerate(reference_files, 1):
            if not file or file.filename == '':
                continue
            filename = secure_filename(file.filename)
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                file.seek(0)
                img_data = file.read()
                # Create data URL
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                mime_type = 'image/jpeg' if file_ext in ['.jpg', '.jpeg'] else f'image/{file_ext[1:]}'
                data_url = f"data:{mime_type};base64,{img_base64}"
                # Store with unique label - don't overwrite profile image
                label = f'image-{idx}'
                # Only use 'profile' label if no profile image was uploaded and this is the first image
                if idx == 1 and 'profile' not in uploaded_images:
                    label = 'profile'
                    print(f"Stored uploaded image as 'profile': {len(img_base64)} chars")
                uploaded_images[label] = data_url
                print(f"Stored uploaded image as '{label}': {len(img_base64)} chars")
    
    # Create the prompt
    template_context = ""
    if template_content:
        template_context = f"""TEMPLATE TO MODIFY:
Below is the HTML template that should be modified and customized based on the user's request. 
Use this as the base structure and adapt it according to the user's needs.

<template_html>
{template_content[:3000]}  # Limit template length to avoid token limits
</template_html>

INSTRUCTIONS:
1. Use the provided template as the base structure
2. Modify the content, text, and styling to match the user's request
3. Keep the overall layout and structure from the template
4. Update colors, fonts, and content to fit the user's needs
5. Replace placeholder content with user-specific information
6. Keep all existing CSS classes and structure - just update the details
7. If the template has image placeholders, keep them and they will be filled automatically
"""
    
    prompt = PromptTemplate(
        template=website_prompt_template,
        input_variables=["user_prompt", "template_context"]
    )
    
    style_context = ""
    style_image_hint = ""
    if style_preset:
        style_context, style_image_hint = build_style_context(style_preset)
        print(f"DEBUG: Applying style preset '{style_preset}' to generation.")
    
    component_selections, component_blueprint = build_component_context(
        user_prompt,
        selected_template,
        preferred_sections
    )
    if component_blueprint:
        print("DEBUG: Component blueprint prepared for generation.")
    
    interactive_context = ""
    if interactive_enhancements:
        interactive_context = build_interactive_context(interactive_enhancements)
    
    # Generate the website code with retry logic for MAX_TOKENS
    max_retries = 2
    for attempt in range(max_retries):
        try:
            formatted_prompt = prompt.format(user_prompt=user_prompt, template_context=template_context).strip()
            # Append reference context if available
            if reference_context:
                formatted_prompt += reference_context
            # Append profile context if available
            if profile_context:
                formatted_prompt += profile_context
            # Append style context if selected
            if style_context:
                formatted_prompt += f"\n\n{style_context}"
            if interactive_context:
                formatted_prompt += f"\n\n{interactive_context}"
            if component_blueprint:
                formatted_prompt += f"\n\n{component_blueprint}"
            # Gemini models need an asyncio loop when invoked inside Flask threads
            try:
                # Prefer streaming to bypass hard token limits
                import asyncio
                html_chunks = []
                async def gather():
                    async for chunk in llm.astream(formatted_prompt):
                        part = chunk.content or ""
                        html_chunks.append(part)
                        # Continue collecting until we have a complete closing tag
                        full_html = "".join(html_chunks)
                        if "</html>" in full_html.lower():
                            break
                try:
                    asyncio.run(gather())
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(gather())
                generated_html = "".join(html_chunks)
            except Exception as e:
                # Fallback to non-stream invoke if streaming fails
                try:
                    generated_html = llm.invoke(formatted_prompt)
                except Exception:
                    return jsonify({'error': f'Generation failed: {e}'}), 500
            
            # generated_html may be an AIMessage object; extract text
            from langchain_core.messages import BaseMessage
            if isinstance(generated_html, BaseMessage):
                generated_html = generated_html.content or str(generated_html)

            # DEBUG: Save the raw HTML before image processing
            print("DEBUG: Raw HTML before image processing:")
            print("=" * 50)
            print(generated_html[:1000])  # First 1000 chars
            print("=" * 50)
            
            # Check for any image-like patterns
            import re
            patterns = [
                r'\{\{image:.*?\}\}',
                r'{{image:.*?}}',
                r'\{image:.*?\}',
                r'<img[^>]*>',
                r'src="[^"]*"'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, generated_html)
                if matches:
                    print(f"DEBUG: Pattern '{pattern}' found: {matches[:5]}")  # First 5 matches

            # Check for MAX_TOKENS error
            if not generated_html.strip():
                if attempt < max_retries - 1:
                    print(f"Attempt {attempt + 1}: Empty response, retrying...")
                    continue
                return jsonify({'error': 'LLM returned empty content. Try a shorter prompt.'}), 500

            # Check if this is a portfolio/resume request and add profile image placeholders if needed
            is_portfolio_request = any(keyword in user_prompt.lower() for keyword in [
                'portfolio', 'resume', 'cv', 'curriculum vitae', 'about me', 'personal website',
                'my profile', 'professional profile', 'my resume', 'create resume'
            ])
            
            if is_portfolio_request and 'profile' in uploaded_images:
                print("DEBUG: Portfolio/resume request detected, ensuring profile image placeholder exists")
                # Add profile image placeholder if not present
                if '{{image: profile}}' not in generated_html and '{{image:profile}}' not in generated_html:
                    # Look for common profile image patterns and replace them
                    generated_html = re.sub(
                        r'src="https://images\.unsplash\.com/photo-[^"]*\.(?:jpg|jpeg|png)"[^>]*>',
                        lambda m: f'src="{{image: profile}}"{m.group(0)[m.group(0).find(">"):]}' if ">" in m.group(0) else 'src="{{image: profile}}"',
                        generated_html
                    )
                    # Also replace hero section images
                    generated_html = re.sub(
                        r'<img[^>]*src="https://images\.unsplash\.com/[^"]*"[^>]*>',
                        '<img src="{{image: profile}}" alt="profile">',
                        generated_html
                    )
                    print("DEBUG: Added profile image placeholders to generated HTML")
            
            # fill image placeholders with uploaded images
            print("DEBUG: Starting image replacement...")
            generated_html = fill_images(generated_html, user_prompt, uploaded_images, style_image_hint)
            print("DEBUG: Image replacement completed")
            
            # Validate and repair HTML layout issues
            print("DEBUG: Validating and repairing HTML structure...")
            generated_html = validate_and_repair_html(generated_html)
            print("DEBUG: HTML validation and repair completed")
            
            # DEBUG: Save the processed HTML
            print("DEBUG: Final HTML after all processing:")
            print("=" * 50)
            print(generated_html[:1000])  # First 1000 chars
            print("=" * 50)

            # Save the generated HTML to a temporary file
            temp_dir = Path(tempfile.gettempdir())
            output_file = temp_dir / "generated_website.html"
            
            with open(output_file, "w") as f:
                f.write(generated_html)
            
            # Return the path to the generated file and its content
            return jsonify({
                'success': True,
                'file_path': str(output_file),
                'content': generated_html,
                'component_blueprint': component_blueprint,
                'component_variants': component_selections,
                'preferred_sections': preferred_sections or {}
            })

        except Exception as e:
            if attempt == max_retries - 1:
                return jsonify({'error': f'Error generating website: {e}'}), 500
            print(f"Attempt {attempt + 1} failed: {e}, retrying...")

@app.route('/update', methods=['POST'])
def update_website():
    """Update an existing website based on user feedback/changes."""
    current_html = request.form.get('current_html', '')
    update_prompt = request.form.get('update_prompt', '')
    original_prompt = request.form.get('original_prompt', '')
    profile_image_data = request.form.get('profile_image_data', '')
    style_preset = request.form.get('style_preset', '')
    preferred_sections_raw = request.form.get('preferred_sections', '')
    
    preferred_sections = None
    if preferred_sections_raw:
        try:
            preferred_sections = json.loads(preferred_sections_raw)
        except json.JSONDecodeError:
            print("WARNING: /update received invalid preferred_sections payload.")
    
    if not current_html or not update_prompt:
        return jsonify({'error': 'Current HTML and update prompt are required'}), 400
    
    print(f"DEBUG: /update - Profile image data provided: {bool(profile_image_data)}")
    
    llm = get_llm()
    if not llm:
        return jsonify({'error': 'Failed to initialize LLM'}), 500
    
    # Prepare uploaded_images for profile image if provided
    uploaded_images = {}
    if profile_image_data:
        uploaded_images['profile'] = profile_image_data
        print(f"DEBUG: /update - Stored profile image for update: {profile_image_data[:50]}...")
    
    # Create a prompt that tells the LLM to update the existing HTML
    update_template = """You are a web developer. Here is the current HTML of a website:

<current_html>
{current_html}
</current_html>

The user wants to make the following changes/updates:
{update_prompt}

CRITICAL RULES - MUST FOLLOW EXACTLY:
1. **KEEP THE ENTIRE STRUCTURE** - Do NOT regenerate the whole page
2. **ONLY modify the specific parts** that the user requested
3. **PRESERVE all CSS styling and layout** - Do not change CSS unless requested
4. **PRESERVE all existing content** - Only change what was asked
5. **PRESERVE all image placeholders** - Use EXACTLY the same format: {{{{image: label}}}}
6. **Do NOT regenerate sections** - Just update the requested content
7. Output ONLY the updated HTML (no explanations or markdown)
8. Ensure the HTML is valid and complete
9. Make minimal changes - only what was requested

EXAMPLES:
- If user says "change color to red": Only update color values in CSS, keep everything else
- If user says "add testimonials": Add a new section, don't regenerate the whole page
- If user says "update menu": Only change the menu items, keep layout and styling

Updated HTML:"""
    
    style_context = ""
    style_image_hint = ""
    if style_preset:
        style_context, style_image_hint = build_style_context(style_preset)
        print(f"DEBUG: /update received style preset '{style_preset}'")
    
    component_source_text = original_prompt or update_prompt
    component_selections, component_blueprint = build_component_context(
        component_source_text,
        "",
        preferred_sections
    )
    if component_blueprint:
        print("DEBUG: Component blueprint prepared for update.")

    try:
        formatted_prompt = update_template.format(
            current_html=current_html,
            update_prompt=update_prompt
        )
        if style_context:
            formatted_prompt += f"\n\n{style_context}"
        if component_blueprint:
            formatted_prompt += f"\n\n{component_blueprint}"
        
        # Generate updated HTML
        try:
            import asyncio
            html_chunks = []
            async def gather():
                async for chunk in llm.astream(formatted_prompt):
                    part = chunk.content or ""
                    html_chunks.append(part)
                    full_html = "".join(html_chunks)
                    if "</html>" in full_html.lower():
                        break
            try:
                asyncio.run(gather())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(gather())
            updated_html = "".join(html_chunks)
        except Exception as e:
            try:
                updated_html = llm.invoke(formatted_prompt)
            except Exception:
                return jsonify({'error': f'Update failed: {e}'}), 500
        
        # Extract text if it's an AIMessage object
        from langchain_core.messages import BaseMessage
        if isinstance(updated_html, BaseMessage):
            updated_html = updated_html.content or str(updated_html)
        
        if not updated_html.strip():
            return jsonify({'error': 'LLM returned empty content'}), 500
        
        # Clean up any malformed img tags that LLM might have generated
        # This is critical for updates since LLM sometimes generates img tags instead of placeholders
        updated_html = re.sub(r'<img\s+src="<img\s+src="[^"]*"\s+alt="([^"]*)"[^>]*>"[^>]*>', lambda m: f'{{{{image: {m.group(1)}}}}}', updated_html)
        updated_html = re.sub(r'<img\s+src="https?://[^"]*"\s+alt="([^"]*)">', lambda m: f'{{{{image: {m.group(1)}}}}}', updated_html)
        updated_html = re.sub(r'<img\s+src="&lt;img\s+src=&quot;[^&]*&quot;[^>]*>"[^>]*>', lambda m: '{{image: restaurant-interior}}', updated_html)
        updated_html = re.sub(r'&lt;img\s+src=&quot;https?://[^&]*&quot;[^>]*&gt;', lambda m: '{{image: restaurant-interior}}', updated_html)
        
        # Fill images in the updated HTML
        print(f"DEBUG: /update - Calling fill_images with uploaded_images: {list(uploaded_images.keys())}")
        prompt_reference = update_prompt or original_prompt
        updated_html = fill_images(updated_html, prompt_reference, uploaded_images, style_image_hint)
        
        # Validate and repair HTML layout issues for updates
        print("DEBUG: /update - Validating and repairing HTML structure...")
        updated_html = validate_and_repair_html(updated_html)
        print("DEBUG: /update - HTML validation and repair completed")
        
        return jsonify({
            'success': True,
            'content': updated_html,
            'component_blueprint': component_blueprint,
            'component_variants': component_selections,
            'preferred_sections': preferred_sections or {}
        })
    
    except Exception as e:
        return jsonify({'error': f'Error updating website: {e}'}), 500

@app.route('/test-profile', methods=['GET', 'POST'])
def test_profile_image():
    """Test route to debug profile image processing with static data"""
    
    # Static test data
    test_prompt = """create resume using the details Contact Basingstoke, United Kingdom +447442633106 (Mobile) souvik79@gmail.com www.linkedin.com/in/souvik- basu2013 (LinkedIn) github.com/souvik79 (Personal) Top Skills AI integration Runpod windsurf Languages English (Full Professional) Certifications Google Cloud Fundamentals: Core Infrastructure Software Architecture: From Developer to Architect souvik basu Seasoned Solution Architect and Developer with expertise in Python, PHP, Node.js, AWS, Google Cloud Basingstoke, England, United Kingdom Summary As a Solution Architect and Full Stack Developer at Twyzle, I have over 15 years of experience designing scalable, AI-driven solutions. My expertise in Python, PHP, and Node.js allows me to build robust applications, APIs, and microservices, leveraging AWS and Google Cloud for performance and scalability. I specialize in AI-powered development, integrating LLMs like OpenAI, Lama, Grok, and Mistral to enhance automation, streamline workflows, and optimize decision-making. My background in data engineering includes AI-driven data scraping and defining AI- powered ETL processes to ensure efficient data transformation and utilization. Currently working only on Windsurf. With a strong focus on cloud-native architectures and Google Service integrations, I develop scalable and intelligent solutions that drive business efficiency. Passionate about automation and emerging technologies, I continuously explore ways to enhance efficiency, drive innovation, and contribute to evolving tech ecosystems. Experience Twyzle Senior Software Developer December 2021 - Present (4 years) Basingstoke, England, United Kingdom Senior Full-Stack Engineer | AI & Systems Architect at Twyzle Leading full-stack architecture, AI systems, and data intelligence initiatives at Twyzle — a platform delivering job insights and AI-powered content tools. Driving innovation in classification pipelines, generative AI, and scalable microservices to support platform growth. Page 1 of 4 AI & NLP Innovation Built a hybrid job classification pipeline using HuggingFace Transformers, fine- tuned BERT models, and GPT-based classifiers. Implemented zero-shot classification for niche job titles with precision-focused rules and embeddings. Developed a feedback/logging loop to auto-flag misclassifications and iteratively improve model accuracy. Data & ETL Pipelines Designed scalable scraping pipelines (Selenium, BeautifulSoup) across multiple job boards. Created ETL flows to clean, transform, and post data into MySQL/MongoDB with validation and monitoring layers. Generative AI Projects Fine-tuned AI models (e.g., SDXL, ControlNet) using LoRA and cinematic prompts for custom image generation. Built auto-captioning pipelines with BLIP2 and image conditioning workflows using ComfyUI. System Architecture & Product Dev Architected microservices with Python, Node.js, Docker/Kubernetes on AWS & GCP. Launched a no-code site builder and Twilio-based messenger to extend platform utility. Integrated OpenAI, Google Ads & Facebook APIs for personalized and programmatic content. Team & Delivery Led Agile development across a cross-functional team of 6 engineers and DevOps. Page 2 of 4 Deployed CI/CD pipelines using AWS CodeDeploy and EC2, streamlining release cycles and uptime. Fresh Gravity Manager API Management & Integrations. July 2019 - January 2022 (2 years 7 months) Pune Area, India Fresh Gravity is at the cutting-edge of digital transformation. We drive digital success for our clients by enabling them to adopt transformative technologies that make them nimble, adaptive and responsive to the changing needs of our businesses. Responsible for Defining overall QA Automation strategy- Automation (Performance, UI). Accountable for Client Communications, Multiple QA automation projects, Mentoring and Providing Leadership to the Teams. Handling Projects with multiple Technologies like AWS, Java, Python, Selenium and etc. Independent Consultant Independent Consultant and web solution architect September 2012 - June 2019 (6 years 10 months) Kolkata Area, India IBM Global Services Senior System Developer January 2012 - October 2012 (10 months) •Provide Support and maintenance (Include new developments) of the Perl/ Java applications and take full ownership of them and act a single point of contact. •Provide new ideas on how to improve the performance of the application of the applications. •Create new tools whenever need for monitoring and automate manual processes and make a developers life easy, most of the tools are being developed in Perl HSBC Senior software developer August 2006 - August 2009 (3 years 1 month) Page 3 of 4 •Developing web applications that meet both business requirements and first direct standards •Maintenance and Development of Web Development Environment •Design and implementation of JavaScript Framework •Design and implementation of Perl Frame Framework •Technical consultant on all matters impacting applications. creativeskills Software engineer January 2005 - July 2006 (1 year 7 months) •Involved in development of client side JavaScript. •Involved in the PHP coding of the Client as well as Admin side •Integration of Components Education Manipal Institute of Technology Master's degree, Information Technology · (January 2001 - April 2004) Nagpur University Bachelor of Science - BS, Computer Science · (January 1998 - April 2001) Kendriya Vidyalaya AISCE, Science · (January 1996 - April 1998)"""
    
    test_profile_url = "https://media.licdn.com/dms/image/v2/C5103AQGWUOPsYwCSnQ/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1577957160091?e=1766016000&v=beta&t=SG-j_1QEgcZP5wjIXv2Rfkmmu6RyMvTdbi-x9684T3Y"
    
    print("=== TEST PROFILE IMAGE DEBUG ===")
    print(f"Test prompt length: {len(test_prompt)}")
    print(f"Test profile URL: {test_profile_url}")
    
    # Simulate the profile image processing
    uploaded_images = {}
    if test_profile_url:
        uploaded_images['profile'] = test_profile_url
        print(f"DEBUG: Test - Stored profile URL with key 'profile': {test_profile_url}")
    
    print(f"DEBUG: Test - Final uploaded_images keys: {list(uploaded_images.keys())}")
    print(f"DEBUG: Test - uploaded_images content: {uploaded_images}")
    
    # Test the fill_images function directly
    test_html_with_placeholder = '<div class="profile"><img src="{{image: profile}}" alt="profile"></div>'
    print(f"DEBUG: Test - Original HTML: {test_html_with_placeholder}")
    
    processed_html = fill_images(test_html_with_placeholder, test_prompt, uploaded_images)
    print(f"DEBUG: Test - Processed HTML: {processed_html}")
    print("=== END TEST DEBUG ===")
    
    return jsonify({
        'success': True,
        'test_data': {
            'prompt_length': len(test_prompt),
            'profile_url': test_profile_url,
            'uploaded_images_keys': list(uploaded_images.keys()),
            'original_html': test_html_with_placeholder,
            'processed_html': processed_html
        }
    })

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True)
