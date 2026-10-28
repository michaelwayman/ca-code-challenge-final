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
RUN pip install --no-cache-dir --find-links /wheels -r requirements.txt
COPY auth/ .
EXPOSE 8001
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py ensure_signing_key && exec python manage.py runserver 0.0.0.0:8001"]
