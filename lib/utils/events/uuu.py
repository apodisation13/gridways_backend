from typing import Any

from jinja2 import Template


def render_template(template_str: str, context: dict[str, Any]) -> str:
    """Рендеринг Jinja2 шаблона с контекстом"""
    template = Template(template_str)
    return template.render(**context)