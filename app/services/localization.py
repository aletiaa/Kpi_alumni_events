from markupsafe import Markup


def display_name(user):
    return Markup('<span data-no-translate data-name-uk="{}" data-name-en="{}">{}</span>').format(
        user.full_name, getattr(user, "full_name_en", None) or user.full_name, user.full_name)


def display_datetime(value):
    if not value:
        return ""
    return Markup('<time data-no-translate data-local-date="{}" datetime="{}">{}</time>').format(
        value.strftime('%Y-%m-%dT%H:%M:%S'), value.isoformat(), value.strftime('%d.%m.%Y, %H:%M'))


def content_text(kind, item_id, field, text):
    return Markup('<span data-content-kind="{}" data-content-id="{}" data-content-field="{}">{}</span>').format(
        kind, item_id, field, text or "")
