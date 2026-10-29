# Build context is the repo root so the shared library in libs/ is reachable.
FROM python:3.12-slim AS wheels
WORKDIR /build
COPY libs/ ./libs/
RUN pip wheel --no-deps --wheel-dir /wheels ./libs

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/auth
COPY --from=wheels /wheels /wheels
COPY auth/requirements.txt .
# cauth comes only from the wheel built above, and must be the version pinned in requirements.txt
# (the build fails when they differ); everything else comes from the index.
RUN pip install --no-cache-dir --no-deps --no-index --find-links /wheels "$(grep '^cauth==' requirements.txt | cut -d' ' -f1)" \
 && pip install --no-cache-dir -r requirements.txt
COPY auth/ .
EXPOSE 8001
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py add_signing_key --if-none && exec python manage.py runserver 0.0.0.0:8001"]
