#!/usr/bin/env python3
"""
Integration test to verify portfolio/resume profile image handling
"""

import sys
import os
sys.path.append('.')

import re
from app import load_template, fill_images

def test_portfolio_template_profile_placeholder():
    template_name = 'portfolio-personal'
    print(f"\n=== Testing template placeholder for {template_name} ===")
    content = load_template(template_name)
    if not content:
        print("❌ Failed to load template")
        return False
    placeholder_present = '{{image: profile}}' in content or '{{image:profile}}' in content
    print(f"Placeholder present: {placeholder_present}")
    return placeholder_present

def test_portfolio_generation_flow():
    print("\n=== Testing end-to-end portfolio flow ===")
    initial_html = '<section class="hero"><img src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d" alt="hero"></section>'
    user_prompt = 'Create a professional resume website for Souvik Basu'
    uploaded_images = {
        'profile': 'https://media.licdn.com/dms/image/v2/C5103AQGWUOPsYwCSnQ/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1577957160091?e=1766016000&v=beta&t=SG-j_1QEgcZP5wjIXv2Rfkmmu6RyMvTdbi-x9684T3Y'
    }
    
    # Simulate the portfolio detection logic from /generate
    is_portfolio_request = any(keyword in user_prompt.lower() for keyword in [
        'portfolio', 'resume', 'cv', 'curriculum vitae', 'about me', 'personal website',
        'my profile', 'professional profile', 'my resume', 'create resume'
    ])
    if is_portfolio_request and 'profile' in uploaded_images:
        processed_html = re.sub(
            r'<img[^>]*src="https://images\.unsplash\.com/[^"]*"[^>]*>',
            '<img src="{{image: profile}}" alt="profile">',
            initial_html
        )
    else:
        processed_html = initial_html
    
    final_html = fill_images(processed_html, user_prompt, uploaded_images)
    success = uploaded_images['profile'] in final_html
    print(f"Profile image embedded: {success}")
    print(f"Final HTML: {final_html}\n")
    return success

if __name__ == "__main__":
    template_ok = test_portfolio_template_profile_placeholder()
    flow_ok = test_portfolio_generation_flow()
    if template_ok and flow_ok:
        print("✅ All portfolio integration tests passed")
    else:
        print("❌ Portfolio integration tests failed")
