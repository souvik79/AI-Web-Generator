#!/usr/bin/env python3

import re
import sys
import os

# Add the current directory to Python path to import from app.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def validate_and_repair_html(html: str) -> str:
    """Validate and repair common HTML layout issues."""
    if not html or not html.strip():
        return html
    
    print("Original HTML issues found:")
    
    # Fix common layout issues:
    
    # 1. Fix incomplete grid containers in projects section
    projects_pattern = r'(<section[^>]*>.*?<h2[^>]*>Featured Projects</h2>.*?)(<div class="card-hover[^>]*>.*?</div>)(.*?</section>)'
    if re.search(projects_pattern, html, flags=re.DOTALL):
        print("- Found incomplete project grid containers")
        html = re.sub(
            projects_pattern,
            lambda m: f"{m.group(1)}<div class='grid md:grid-cols-2 lg:grid-cols-3 gap-8'>{m.group(2)}</div>{m.group(3)}",
            html,
            flags=re.DOTALL
        )
    
    # 2. Fix orphaned skill bars without proper containers
    skills_pattern = r'(<section[^>]*>.*?<h2[^>]*>Skills[^<]*</h2>.*?)(<div class="space-y-4">\s*<div class="flex justify-between[^>]*>.*?</div>\s*<div class="bg-gray-200[^>]*>.*?</div>\s*</div>)(.*?</section>)'
    if re.search(skills_pattern, html, flags=re.DOTALL):
        print("- Found orphaned skill bars")
        html = re.sub(
            skills_pattern,
            lambda m: f"{m.group(1)}<div class='max-w-4xl mx-auto space-y-8'>{m.group(2)}</div>{m.group(3)}",
            html,
            flags=re.DOTALL
        )
    
    # 3. Fix orphaned skill tags (floating span elements)
    orphaned_tags_pattern = r'(\s*<span class="px-4 py-2 bg-gray-100[^>]*>[^<]*</span>\s*)+'
    if re.search(orphaned_tags_pattern, html):
        print("- Found orphaned skill tags")
        html = re.sub(
            orphaned_tags_pattern,
            lambda m: f"<div class='flex flex-wrap gap-3 mt-8'>{m.group(0)}</div>",
            html
        )
    
    # 4. Fix duplicate closing tags
    if '</div></div></div>' in html:
        print("- Found duplicate closing div tags")
        html = re.sub(r'</div></div></div>', '</div></div>', html)
    
    print("HTML repair completed!")
    return html

def test_html_repair():
    """Test the HTML repair function on the existing generated HTML."""
    
    # Read the existing generated HTML
    project_root = os.path.dirname(os.path.abspath(__file__))
    html_file = os.path.join(project_root, "generated_portfolio.html")
    
    try:
        with open(html_file, 'r') as f:
            original_html = f.read()
        
        print(f"Loaded HTML file: {html_file}")
        print(f"Original HTML length: {len(original_html)} characters")
        print("=" * 50)
        
        # Apply the repair function
        repaired_html = validate_and_repair_html(original_html)
        
        print("=" * 50)
        print(f"Repaired HTML length: {len(repaired_html)} characters")
        print(f"HTML changed: {'Yes' if original_html != repaired_html else 'No'}")
        
        # Save the repaired version for comparison
        output_file = os.path.join(project_root, "generated_portfolio_repaired.html")
        with open(output_file, 'w') as f:
            f.write(repaired_html)
        
        print(f"Repaired HTML saved to: {output_file}")
        
        # Show some key differences
        print("\nKey improvements made:")
        if 'grid md:grid-cols-2 lg:grid-cols-3 gap-8' in repaired_html and 'grid md:grid-cols-2 lg:grid-cols-3 gap-8' not in original_html:
            print("- Added proper grid container for projects")
        if 'max-w-4xl mx-auto space-y-8' in repaired_html and 'max-w-4xl mx-auto space-y-8' not in original_html:
            print("- Added proper container for skills section")
        if 'flex flex-wrap gap-3 mt-8' in repaired_html and 'flex flex-wrap gap-3 mt-8' not in original_html:
            print("- Fixed orphaned skill tags with proper container")
        
        return True
        
    except FileNotFoundError:
        print(f"Error: Could not find {html_file}")
        print("Please generate a website first to test the repair function.")
        return False
    except Exception as e:
        print(f"Error testing HTML repair: {e}")
        return False

if __name__ == "__main__":
    test_html_repair()
