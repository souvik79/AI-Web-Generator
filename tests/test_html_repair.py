import pytest

from app import validate_and_repair_html


def test_strips_markdown_fences_and_whitespace():
    messy_html = """\n```html\n<section class=\"wrapper\">\n  <div class=\"card-hover\">Card</div>\n```\n"""
    cleaned = validate_and_repair_html(messy_html)

    assert cleaned.startswith("<section"), "Markdown fences should be stripped"
    assert "```" not in cleaned


def test_wraps_orphaned_skill_tags_and_projects():
    html = """
    <section>
      <h2>Skills</h2>
      <span class="px-4 py-2 bg-gray-100">Python</span>
      <span class="px-4 py-2 bg-gray-100">Flask</span>
    </section>
    <section>
      <h2>Featured Projects</h2>
      <div class="card-hover">Project card</div>
    </section>
    """

    repaired = validate_and_repair_html(html)

    assert "flex flex-wrap gap-3 mt-8" in repaired, "Skill tags should be wrapped"
    assert "grid md:grid-cols-2 lg:grid-cols-3 gap-8" in repaired, "Project cards should be wrapped in grid"
