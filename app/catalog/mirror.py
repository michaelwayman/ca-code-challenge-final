from collections import Counter

from django.apps import apps
from django.db import models


def mirror(
    model: type[models.Model], key_field: str, rows: dict, counts: dict[type, Counter]
) -> None:
    """Make `model`'s table hold exactly `rows` ({key: field values}), matched on `key_field`.

    New keys are created, changed rows updated, unchanged rows left alone and rows whose key
    is missing deleted. Each outcome is counted in counts[model]; rows deleted by a cascade
    are counted against their own model.
    """
    # Deleting first also frees the slugs of rows that left the set.
    _, deleted = model.objects.exclude(**{f"{key_field}__in": list(rows)}).delete()
    for label, number in deleted.items():
        counts[apps.get_model(label)]["deleted"] += number
    existing = model.objects.in_bulk(list(rows), field_name=key_field)
    _park_changing_slugs(model, existing, rows)
    for key, values in rows.items():
        obj = existing.get(key)
        if obj is None:
            model.objects.create(**{key_field: key}, **values)
            counts[model]["created"] += 1
            continue
        changed = [name for name, value in values.items() if getattr(obj, name) != value]
        if changed:
            for name in changed:
                setattr(obj, name, values[name])
            obj.save(update_fields=changed)
            counts[model]["updated"] += 1
        else:
            counts[model]["unchanged"] += 1


def _park_changing_slugs(model, existing: dict, rows: dict) -> None:
    """Move every slug that is about to change to a placeholder first, so a rename into a
    slug another row only gives up later in the loop (or a swap) cannot hit the unique index."""
    if not any(f.name == "slug" for f in model._meta.fields):
        return
    for key, obj in existing.items():
        if obj.slug != rows[key]["slug"]:
            model.objects.filter(pk=obj.pk).update(slug=f"wp-import-parked-{obj.pk}")
            obj.slug = None
