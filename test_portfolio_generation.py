#!/usr/bin/env python3
"""
Test script to generate a complete portfolio HTML page using the template and profile data
"""

import re
import base64
import os
from urllib.parse import urlparse

def fill_images(html: str, prompt: str, uploaded_images: dict = None) -> str:
    """Test version of fill_images function with debugging"""
    if uploaded_images is None:
        uploaded_images = {}
    
    print(f"DEBUG: fill_images - Processing HTML for image replacement...")
    print(f"DEBUG: fill_images - Uploaded images keys: {list(uploaded_images.keys())}")
    
    # First, clean up any malformed img tags BEFORE processing placeholders
    html = re.sub(r'<img\s+src="<img\s+src="[^"]*"\s+alt="([^"]*)"[^>]*>"[^>]*>', lambda m: f'{{{{image: {m.group(1)}}}}}', html)
    html = re.sub(r'<img\s+src="https?://[^"]*"\s+alt="([^"]*)">', lambda m: f'{{{{image: {m.group(1)}}}}}', html)
    html = re.sub(r'<img\s+src="&lt;img\s+src=&quot;([^&]*)&quot;[^&]*&amp;[^&]*&quot;[^>]*>"[^>]*>', lambda m: f'{{{{image: {m.group(1)}}}}}', html)
    html = re.sub(r'&lt;img\s+src=&quot;https?://[^&]*&quot;[^>]*&gt;', lambda m: '{{image: restaurant-interior}}', html)
    html = re.sub(r'<img\s+src="&lt;img\s+src="([^"]+)"\s+alt="([^"]+)"&gt;"\s+alt="([^"]+)">', lambda m: f'{{{{image: {m.group(2)}}}}}', html)
    html = re.sub(r'&lt;img\s+src="([^"]+)"\s+alt="([^"]+)"&gt;', lambda m: f'{{{{image: {m.group(2)}}}}}', html)
    
    # Handle the specific LinkedIn URL pattern
    matches_before = len(re.findall(r'<img\s+src="&lt;img\s+src="[^"]*?&quot;[^>]*&gt;"\s+alt="[^"]+">', html))
    if matches_before > 0:
        print(f"DEBUG: Found {matches_before} LinkedIn URL patterns to fix")
    html = re.sub(r'<img\s+src="&lt;img\s+src="([^"]*?)(?:&amp;[^&]*)*&quot;[^>]*&gt;"\s+alt="([^"]+)">', lambda m: f'{{{{image: {m.group(2)}}}}}', html)
    
    # Handle any case that ends with &quot; instead of proper closing
    html = re.sub(r'<img\s+src="&lt;img\s+src="([^"]*)&quot;[^>]*&gt;"\s+alt="([^"]+)">', lambda m: f'{{{{image: {m.group(2)}}}}}', html)
    html = re.sub(r'<img\s+src="&lt;img\s+src="([^"]*https://media\.licdn\.com[^"]*)\&quot;[^>]*&gt;"\s+alt="([^"]+)">', lambda m: f'{{{{image: {m.group(2)}}}}}', html)
    html = re.sub(r'<img\s+src="&lt;img\s+src="[^"]*&quot;[^>]*&gt;"\s+alt="([^"]+)">', lambda m: f'{{{{image: {m.group(1)}}}}}', html)
    html = re.sub(r'<img\s+src="&lt;img\s+src="[^"]*"[^>]*&gt;"\s+alt="([^"]+)">', lambda m: f'{{{{image: {m.group(1)}}}}}', html)
    
    print(f"DEBUG: HTML after cleanup: {html[:500]}...")
    
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
    
    # FINAL CLEANUP: Remove any remaining malformed img tags
    print("DEBUG: Performing final cleanup of malformed HTML...")
    html = re.sub(r'<img\s+src="&lt;img[^>]*>"[^>]*>', '', html)
    html = re.sub(r'&lt;img[^>]*&gt;', '', html)
    print(f"DEBUG: Final cleanup completed")
    
    return html

def customize_portfolio_template(template_html, profile_data):
    """Customize the portfolio template with user's profile data"""
    
    # Replace basic information
    template_html = template_html.replace('Alex Chen', profile_data['name'])
    template_html = template_html.replace('Creative Developer', profile_data['title'])
    template_html = template_html.replace('AC', profile_data['initials'])
    
    # Replace hero section content
    template_html = template_html.replace(
        'Hi, I\'m <span class="gradient-text">Alex</span>',
        f'Hi, I\'m <span class="gradient-text">{profile_data["name"].split()[0]}</span>'
    )
    
    template_html = template_html.replace(
        'I craft beautiful, functional web experiences with modern technologies. \n                        Passionate about clean code, intuitive design, and pushing creative boundaries.',
        profile_data['summary']
    )
    
    # Replace about section
    template_html = template_html.replace(
        'I\'m a full-stack developer with a passion for creating exceptional digital experiences. \n                            My journey in web development started 5 years ago, and since then, I\'ve worked with \n                            startups and established companies to build scalable, user-friendly applications.',
        f'I\'m a {profile_data["title"]} with over 15 years of experience designing scalable, AI-driven solutions. \n                            My expertise in Python, PHP, and Node.js allows me to build robust applications, APIs, and microservices.'
    )
    
    template_html = template_html.replace(
        'I specialize in React, Node.js, and modern web technologies. When I\'m not coding, \n                            you\'ll find me exploring new design trends, contributing to open-source projects, \n                            or capturing moments through photography.',
        f'I specialize in AI-powered development, integrating LLMs like OpenAI, Lama, Grok, and Mistral to enhance automation. \n                            My background in data engineering includes AI-driven data scraping and defining AI-powered ETL processes.'
    )
    
    # Replace contact links
    template_html = template_html.replace('href="#"', f'href="{profile_data["linkedin"]}"', 1)  # LinkedIn
    template_html = template_html.replace('href="#"', f'href="{profile_data["github"]}"', 1)  # GitHub
    
    # Replace stats
    template_html = template_html.replace('50+', '100+')
    template_html = template_html.replace('30+', '50+')
    template_html = template_html.replace('Projects Completed', 'AI Projects Delivered')
    template_html = template_html.replace('Happy Clients', 'Enterprise Solutions')
    
    # Replace skills with actual skills from profile
    skills_section = '''
                <div class="space-y-4">
                    <div class="flex justify-between items-center">
                        <span class="font-semibold text-gray-700">AI Integration</span>
                        <span class="text-gray-600">95%</span>
                    </div>
                    <div class="bg-gray-200 rounded-full h-3">
                        <div class="hero-gradient h-3 rounded-full skill-bar" style="width: 95%"></div>
                    </div>
                </div>
                <div class="space-y-4">
                    <div class="flex justify-between items-center">
                        <span class="font-semibold text-gray-700">Python Development</span>
                        <span class="text-gray-600">90%</span>
                    </div>
                    <div class="bg-gray-200 rounded-full h-3">
                        <div class="hero-gradient h-3 rounded-full skill-bar" style="width: 90%"></div>
                    </div>
                </div>
                <div class="space-y-4">
                    <div class="flex justify-between items-center">
                        <span class="font-semibold text-gray-700">Cloud Architecture</span>
                        <span class="text-gray-600">85%</span>
                    </div>
                    <div class="bg-gray-200 rounded-full h-3">
                        <div class="hero-gradient h-3 rounded-full skill-bar" style="width: 85%"></div>
                    </div>
                </div>
                <div class="space-y-4">
                    <div class="flex justify-between items-center">
                        <span class="font-semibold text-gray-700">Data Engineering</span>
                        <span class="text-gray-600">88%</span>
                    </div>
                    <div class="bg-gray-200 rounded-full h-3">
                        <div class="hero-gradient h-3 rounded-full skill-bar" style="width: 88%"></div>
                    </div>
                </div>
    '''
    
    # Find and replace the skills section
    skills_start = template_html.find('<div class="space-y-4">')
    skills_end = template_html.find('</div>', skills_start) + 6
    template_html = template_html[:skills_start] + skills_section + template_html[skills_end:]
    
    # Replace technology tags
    tech_tags = '''
                <span class="px-4 py-2 bg-gray-100 rounded-full text-gray-700">Python</span>
                <span class="px-4 py-2 bg-gray-100 rounded-full text-gray-700">Node.js</span>
                <span class="px-4 py-2 bg-gray-100 rounded-full text-gray-700">AWS</span>
                <span class="px-4 py-2 bg-gray-100 rounded-full text-gray-700">Google Cloud</span>
                <span class="px-4 py-2 bg-gray-100 rounded-full text-gray-700">OpenAI</span>
                <span class="px-4 py-2 bg-gray-100 rounded-full text-gray-700">Docker</span>
                <span class="px-4 py-2 bg-gray-100 rounded-full text-gray-700">Kubernetes</span>
                <span class="px-4 py-2 bg-gray-100 rounded-full text-gray-700">MongoDB</span>
                <span class="px-4 py-2 bg-gray-100 rounded-full text-gray-700">MySQL</span>
                <span class="px-4 py-2 bg-gray-100 rounded-full text-gray-700">LLM Integration</span>
    '''
    
    tech_start = template_html.find('<div class="flex flex-wrap justify-center gap-4 mt-12">')
    tech_end = template_html.find('</div>', tech_start) + 6
    template_html = template_html[:tech_start] + tech_tags + template_html[tech_end:]
    
    # Replace projects with relevant AI/ML projects
    projects_section = '''
                <div class="card-hover bg-gray-50 rounded-2xl overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1677442136019-21780ecad995?w=400&h=250&fit=crop" 
                         alt="AI Classification Pipeline" 
                         class="w-full h-48 object-cover">
                    <div class="p-6">
                        <h3 class="text-xl font-bold text-gray-900 mb-2">AI Job Classification Pipeline</h3>
                        <p class="text-gray-600 mb-4">Built hybrid classification system using HuggingFace Transformers and fine-tuned BERT models with zero-shot classification capabilities.</p>
                        <div class="flex flex-wrap gap-2 mb-4">
                            <span class="text-xs px-2 py-1 bg-teal-100 text-teal-700 rounded">Python</span>
                            <span class="text-xs px-2 py-1 bg-teal-100 text-teal-700 rounded">Transformers</span>
                            <span class="text-xs px-2 py-1 bg-teal-100 text-teal-700 rounded">BERT</span>
                        </div>
                        <div class="flex space-x-4">
                            <a href="#" class="text-teal-600 hover:text-teal-700">
                                <i class="fas fa-external-link-alt"></i> Live Demo
                            </a>
                            <a href="#" class="text-gray-600 hover:text-gray-700">
                                <i class="fab fa-github"></i> Code
                            </a>
                        </div>
                    </div>
                </div>
                <div class="card-hover bg-gray-50 rounded-2xl overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=400&h=250&fit=crop" 
                         alt="Generative AI Platform" 
                         class="w-full h-48 object-cover">
                    <div class="p-6">
                        <h3 class="text-xl font-bold text-gray-900 mb-2">Generative AI Content Platform</h3>
                        <p class="text-gray-600 mb-4">Fine-tuned SDXL and ControlNet models using LoRA for custom image generation with auto-captioning pipelines.</p>
                        <div class="flex flex-wrap gap-2 mb-4">
                            <span class="text-xs px-2 py-1 bg-teal-100 text-teal-700 rounded">SDXL</span>
                            <span class="text-xs px-2 py-1 bg-teal-100 text-teal-700 rounded">ControlNet</span>
                            <span class="text-xs px-2 py-1 bg-teal-100 text-teal-700 rounded">LoRA</span>
                        </div>
                        <div class="flex space-x-4">
                            <a href="#" class="text-teal-600 hover:text-teal-700">
                                <i class="fas fa-external-link-alt"></i> Live Demo
                            </a>
                            <a href="#" class="text-gray-600 hover:text-gray-700">
                                <i class="fab fa-github"></i> Code
                            </a>
                        </div>
                    </div>
                </div>
                <div class="card-hover bg-gray-50 rounded-2xl overflow-hidden">
                    <img src="https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400&h=250&fit=crop" 
                         alt="Microservices Architecture" 
                         class="w-full h-48 object-cover">
                    <div class="p-6">
                        <h3 class="text-xl font-bold text-gray-900 mb-2">Cloud-Native Microservices Platform</h3>
                        <p class="text-gray-600 mb-4">Architected scalable microservices with Python, Node.js, Docker/Kubernetes on AWS & GCP with CI/CD pipelines.</p>
                        <div class="flex flex-wrap gap-2 mb-4">
                            <span class="text-xs px-2 py-1 bg-teal-100 text-teal-700 rounded">Docker</span>
                            <span class="text-xs px-2 py-1 bg-teal-100 text-teal-700 rounded">Kubernetes</span>
                            <span class="text-xs px-2 py-1 bg-teal-100 text-teal-700 rounded">AWS</span>
                        </div>
                        <div class="flex space-x-4">
                            <a href="#" class="text-teal-600 hover:text-teal-700">
                                <i class="fas fa-external-link-alt"></i> Live Demo
                            </a>
                            <a href="#" class="text-gray-600 hover:text-gray-700">
                                <i class="fab fa-github"></i> Code
                            </a>
                        </div>
                    </div>
                </div>
    '''
    
    projects_start = template_html.find('<div class="grid md:grid-cols-2 lg:grid-cols-3 gap-8">')
    projects_end = template_html.find('</div>', projects_start) + 6
    template_html = template_html[:projects_start] + projects_section + template_html[projects_end:]
    
    # Replace contact information
    template_html = template_html.replace('souvik79@gmail.com', profile_data['email'])
    template_html = template_html.replace('+447442633106', profile_data['phone'])
    
    # Replace footer
    template_html = template_html.replace(
        '&copy; 2024 Alex Chen. Built with passion and lots of coffee ☕',
        f'&copy; 2024 {profile_data["name"]}. Built with AI expertise and cloud solutions 🚀'
    )
    
    return template_html

def test_portfolio_generation():
    """Test complete portfolio generation with profile data"""
    
    # Profile data
    profile_data = {
        'name': 'Souvik Basu',
        'title': 'Seasoned Solution Architect and Developer',
        'initials': 'SB',
        'summary': 'As a Solution Architect and Full Stack Developer at Twyzle, I have over 15 years of experience designing scalable, AI-driven solutions. My expertise in Python, PHP, and Node.js allows me to build robust applications, APIs, and microservices, leveraging AWS and Google Cloud for performance and scalability.',
        'email': 'souvik79@gmail.com',
        'phone': '+447442633106',
        'linkedin': 'https://www.linkedin.com/in/souvik-basu2013',
        'github': 'https://github.com/souvik79'
    }
    
    # Profile image URL
    profile_image_url = "https://media.licdn.com/dms/image/v2/C5103AQGWUOPsYwCSnQ/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1577957160091?e=1766016000&v=beta&t=SG-j_1QEgcZP5wjIXv2Rfkmmu6RyMvTdbi-x9684T3Y"
    
    print("=== PORTFOLIO GENERATION TEST ===")
    print(f"Generating portfolio for: {profile_data['name']}")
    print(f"Profile image URL: {profile_image_url}")
    
    # Read the portfolio template
    try:
        with open('templates/portfolio-personal.html', 'r') as f:
            template_html = f.read()
        print("✅ Successfully loaded portfolio template")
    except FileNotFoundError:
        print("❌ Portfolio template not found")
        return None
    
    # Customize template with profile data
    customized_html = customize_portfolio_template(template_html, profile_data)
    print("✅ Template customized with profile data")
    
    # Add profile image placeholder
    # Replace the hero image with profile image placeholder
    customized_html = customized_html.replace(
        'src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=500&h=600&fit=crop&crop=face"',
        'src="{{image: profile}}"'
    )
    
    # Set up uploaded images
    uploaded_images = {'profile': profile_image_url}
    print(f"✅ Profile image prepared: {profile_image_url[:50]}...")
    
    # Process image placeholders
    final_html = fill_images(customized_html, "portfolio generation", uploaded_images)
    print("✅ Image placeholders processed")
    
    # Save the generated HTML
    output_file = 'generated_portfolio.html'
    with open(output_file, 'w') as f:
        f.write(final_html)
    
    print(f"✅ Portfolio generated successfully: {output_file}")
    print("=== TEST COMPLETE ===")
    
    return output_file

if __name__ == "__main__":
    print("Starting portfolio generation test...")
    result = test_portfolio_generation()
    if result:
        print(f"\n🎉 SUCCESS! Open {result} in your browser to see the result!")
    else:
        print("\n❌ FAILED! Check the error messages above.")
