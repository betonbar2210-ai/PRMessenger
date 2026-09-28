from django import template
from django.forms import CheckboxSelectMultiple, RadioSelect
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="add_class")
def add_class(value, css_class):
    widget = value.field.widget
    existing = widget.attrs.get("class", "")
    # Фильтр может вызываться несколько раз на одном виджете, поэтому класс
    # не должен дублироваться ("form-control form-control").
    added = [name for name in existing.split() if name]
    for name in css_class.split():
        if name not in added:
            added.append(name)
    widget.attrs["class"] = " ".join(added)
    return value


@register.filter(name="is_checkbox")
def is_checkbox(field):
    return isinstance(field.field.widget, CheckboxSelectMultiple)


@register.filter(name="is_radio")
def is_radio(field):
    return isinstance(field.field.widget, RadioSelect)


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


@register.filter(name="render_radios")
def render_radios(field):
    """Рисует RadioSelect по��оками Bootstrap, а не блоком с form-control."""
    if not is_radio(field):
        return mark_safe(field.as_widget())

    name = field.html_name
    selected = str(field.value() or "")
    out = []
    for index, (value, label) in enumerate(field.field.choices):
        checked = " checked" if str(value) == selected else ""
        widget_id = f"{name}_{index}"
        out.append(
            format_html(
                '<div class="form-check form-check-inline">'
                '<input class="form-check-input" type="radio" '
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
    return mark_safe("\n".join(out))
