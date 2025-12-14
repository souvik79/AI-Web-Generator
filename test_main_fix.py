#!/usr/bin/env python3
"""
Test the main app.py fix for profile image processing
"""

import sys
import os
sys.path.append('.')

# Import the fill_images function from app.py
from app import fill_images

def test_main_fix():
    """Test the fixed fill_images function"""
    
    print("=== TESTING MAIN APP.PY FIX ===")
    
    # Test data
    test_html = '<div class="profile"><img src="{{image: profile}}" alt="profile"></div>'
    test_prompt = "create resume for Souvik Basu"
    uploaded_images = {
        'profile': 'https://media.licdn.com/dms/image/v2/C5103AQGWUOPsYwCSnQ/profile-displayphoto-shrink_400_400/profile-displayphoto-shrink_400_400/0/1577957160091?e=1766016000&v=beta&t=SG-j_1QEgcZP5wjIXv2Rfkmmu6RyMvTdbi-x9684T3Y'
    }
    
    print(f"Input HTML: {test_html}")
    print(f"Profile URL: {test_html}")
    print(f"Uploaded images: {list(uploaded_images.keys())}")
    
    # Test the function
    result = fill_images(test_html, test_prompt, uploaded_images)
    
    print(f"Output HTML: {result}")
    
    # Check if the profile image URL is correctly embedded
    if test_html in result:
        print("❌ FAILED: Profile image not replaced")
    elif uploaded_images['profile'] in result:
        print("✅ SUCCESS: Profile image correctly embedded")
    else:
        print("⚠️  PARTIAL: Image was processed but URL not found")
    
    print("=== TEST COMPLETE ===")

if __name__ == "__main__":
    test_main_fix()
