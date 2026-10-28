"""Demo-only: add ~100 fake brands with a few reviews each so /brands/ paginates.
Not part of the spec. Idempotent (keyed on wp_id >= 9,000,000); `--clear` removes them.
`import_wp` mirrors WP, so a re-import deletes these rows.

  docker compose exec -T app python manage.py shell < scripts/seed-demo-brands.py
  docker compose exec -T -e DEMO_CLEAR=1 app python manage.py shell \
    < scripts/seed-demo-brands.py
"""

import os
import random
from datetime import timedelta

from django.utils import timezone

from catalog.models import Brand, Industry, Review

BASE = 9_000_000
COUNT = 100

if os.environ.get("DEMO_CLEAR"):
    print("deleted", Brand.objects.filter(wp_id__gte=BASE).delete())
else:
    rnd = random.Random(42)
    industries = list(Industry.objects.all())
    first = [
        "Nova",
        "Blue",
        "Summit",
        "Harbor",
        "Prime",
        "Apex",
        "Maple",
        "Iron",
        "Clear",
        "Bright",
    ]
    second = [
        "Bank",
        "Telecom",
        "Mutual",
        "Retail",
        "Home",
        "Mobile",
        "Direct",
        "Trust",
        "Cover",
        "Mart",
    ]
    now = timezone.now()
    for i in range(COUNT):
        name = f"{first[i % 10]}{second[(i // 10 + i) % 10]} Demo {i + 1}"
        slug = f"demo-brand-{i + 1}"
        brand, _ = Brand.objects.update_or_create(
            wp_id=BASE + i,
            defaults={
                "name": name,
                "slug": slug,
                "short_description": f"{name} is a demo brand used to exercise pagination.",
                "industry": rnd.choice(industries) if industries else None,
                "published_at": now,
                "modified_at": now,
            },
        )
        for j in range(rnd.randint(0, 4)):
            Review.objects.update_or_create(
                wp_id=BASE + i * 10 + j,
                defaults={
                    "brand": brand,
                    "title": f"Demo review {j + 1} of {name}",
                    "slug": f"demo-review-{i + 1}-{j + 1}",
                    "body": "<p>Demo review text.</p>",
                    "rating": rnd.randint(1, 5),
                    "published_at": now - timedelta(days=rnd.randint(0, 300)),
                    "modified_at": now,
                },
            )
    print("brands:", Brand.objects.count())
