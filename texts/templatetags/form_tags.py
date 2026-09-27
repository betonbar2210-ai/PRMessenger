from django import template
from django.forms import CheckboxSelectMultiple
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="add_class")
def add_class(value, css_class):
    widget = value.field.widget
    existing = widget.attrs.get("class", "")
    widget.attrs["class"] = f"{existing} {css_class}".strip()
    return value


@register.filter(name="is_checkbox")
def is_checkbox(field):
    return isinstance(field.field.widget, CheckboxSelectMultiple)


@register.filter(name="render_checkboxes")
def render_checkboxes(field):
    """Рендерит CheckboxSelectMultiple в Bootstrap form-check чекбоксы."""
    if not is_checkbox(field):
        return mark_safe(field.as_widget())

    name = field.html_name
    selected = {str(value) for value in field.value() or []}
    out = []
    for index, (value, label) in enumerate(field.field.choices):
        checked = " checked" if str(value) in selected else ""
        widget_id = f"{name}_{index}"
        out.append(
            format_html(
                '<div class="form-check">'
                '<input class="form-check-input" type="checkbox" '
                'name="{}" value="{}" id="{}"{}>'
                '<label class="form-check-label" for="{}">{}</label>'
                "</div>",
                name,
                value,
                widget_id,
                mark_safe(checked),
                widget_id,
                conditional_escape(label),
            )
        )
    if not out:
        out.append('<div class="text-muted">Нет доступных получателей.</div>')
    return mark_safe("\n".join(out))
