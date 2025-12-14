#!/usr/bin/env python3
"""
Standalone script to debug profile image processing issue
"""

import re
import base64
import os
from urllib.parse import urlparse

def fill_images(html: str, prompt: str, uploaded_images: dict = None) -> str:
    """Test version of fill_images function with debugging"""
    if uploaded_images is None:
        uploaded_images = {}
    
    print(f"DEBUG: fill_images - User prompt context: '{prompt[:100]}...'")
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
        matches = re.findall(pattern, html)
        if matches:
            print(f"DEBUG: Found {name} placeholders: {matches[:5]}")  # First 5 matches
            placeholders.extend(matches)
    
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
            photo = f"https://picsum.photos/seed/{label}/400/400"  # Fallback for testing
            print(f"Generated profile image for '{label}': {photo[:50]}...")
            return f'src="{photo}"'  # Return src attribute with URL
        
        # Otherwise, generate placeholder image
        photo = f"https://picsum.photos/seed/{label}/800/500"
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
    
    return html

def test_profile_image():
    """Test profile image processing with static data"""
    
    # Static test data
    test_prompt = """create resume using the details Contact Basingstoke, United Kingdom +447442633106 (Mobile) souvik79@gmail.com www.linkedin.com/in/souvik- basu2013 (LinkedIn) github.com/souvik79 (Personal) Top Skills AI integration Runpod windsurf Languages English (Full Professional) Certifications Google Cloud Fundamentals: Core Infrastructure Software Architecture: From Developer to Architect souvik basu Seasoned Solution Architect and Developer with expertise in Python, PHP, Node.js, AWS, Google Cloud Basingstoke, England, United Kingdom Summary As a Solution Architect and Full Stack Developer at Twyzle, I have over 15 years of experience designing scalable, AI-driven solutions. My expertise in Python, PHP, and Node.js allows me to build robust applications, APIs, and microservices, leveraging AWS and Google Cloud for performance and scalability. I specialize in AI-powered development, integrating LLMs like OpenAI, Lama, Grok, and Mistral to enhance automation, streamline workflows, and optimize decision-making. My background in data engineering includes AI-driven data scraping and defining AI- powered ETL processes to ensure efficient data transformation and utilization. Currently working only on Windsurf. With a strong focus on cloud-native architectures and Google Service integrations, I develop scalable and intelligent solutions that drive business efficiency. Passionate about automation and emerging technologies, I continuously explore ways to enhance efficiency, drive innovation, and contribute to evolving tech ecosystems. Experience Twyzle Senior Software Developer December 2021 - Present (4 years) Basingstoke, England, United Kingdom Senior Full-Stack Engineer | AI & Systems Architect at Twyzle Leading full-stack architecture, AI systems, and data intelligence initiatives at Twyzle — a platform delivering job insights and AI-powered content tools. Driving innovation in classification pipelines, generative AI, and scalable microservices to support platform growth. Page 1 of 4 AI & NLP Innovation Built a hybrid job classification pipeline using HuggingFace Transformers, fine- tuned BERT models, and GPT-based classifiers. Implemented zero-shot classification for niche job titles with precision-focused rules and embeddings. Developed a feedback/logging loop to auto-flag misclassifications and iteratively improve model accuracy. Data & ETL Pipelines Designed scalable scraping pipelines (Selenium, BeautifulSoup) across multiple job boards. Created ETL flows to clean, transform, and post data into MySQL/MongoDB with validation and monitoring layers. Generative AI Projects Fine-tuned AI models (e.g., SDXL, ControlNet) using LoRA and cinematic prompts for custom image generation. Built auto-captioning pipelines with BLIP2 and image conditioning workflows using ComfyUI. System Architecture & Product Dev Architected microservices with Python, Node.js, Docker/Kubernetes on AWS & GCP. Launched a no-code site builder and Twilio-based messenger to extend platform utility. Integrated OpenAI, Google Ads & Facebook APIs for personalized and programmatic content. Team & Delivery Led Agile development across a cross-functional team of 6 engineers and DevOps. Page 2 of 4 Deployed CI/CD pipelines using AWS CodeDeploy and EC2, streamlining release cycles and uptime. Fresh Gravity Manager API Management & Integrations. July 2019 - January 2022 (2 years 7 months) Pune Area, India Fresh Gravity is at the cutting-edge of digital transformation. We drive digital success for our clients by enabling them to adopt transformative technologies that make them nimble, adaptive and responsive to the changing needs of our businesses. Responsible for Defining overall QA Automation strategy- Automation (Performance, UI). Accountable for Client Communications, Multiple QA automation projects, Mentoring and Providing Leadership to the Teams. Handling Projects with multiple Technologies like AWS, Java, Python, Selenium and etc. Independent Consultant Independent Consultant and web solution architect September 2012 - June 2019 (6 years 10 months) Kolkata Area, India IBM Global Services Senior System Developer January 2012 - October 2012 (10 months) •Provide Support and maintenance (Include new developments) of the Perl/ Java applications and take full ownership of them and act a single point of contact. •Provide new ideas on how to improve the performance of the application of the applications. •Create new tools whenever need for monitoring and automate manual processes and make a developers life easy, most of the tools are being developed in Perl HSBC Senior software developer August 2006 - August 2009 (3 years 1 month) Page 3 of 4 •Developing web applications that meet both business requirements and first direct standards •Maintenance and Development of Web Development Environment •Design and implementation of JavaScript Framework •Design and implementation of Perl Frame Framework •Technical consultant on all matters impacting applications. creativeskills Software engineer January 2005 - July 2006 (1 year 7 months) •Involved in development of client side JavaScript. •Involved in the PHP coding of the Client as well as Admin side •Integration of Components Education Manipal Institute of Technology Master's degree, Information Technology · (January 2001 - April 2004) Nagpur University Bachelor of Science - BS, Computer Science · (January 1998 - April 2001) Kendriya Vidyalaya AISCE, Science · (January 1996 - April 1998"""
    
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
    
    return processed_html

if __name__ == "__main__":
    print("Starting profile image debug test...")
    result = test_profile_image()
    print("\n=== FINAL RESULT ===")
    print(result)
    print("=== TEST COMPLETE ===")
