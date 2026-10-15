FROM node:24-bookworm-slim AS mobile
WORKDIR /build/mobile
COPY mobile/package*.json ./
RUN npm ci
COPY mobile/ ./
ENV EXPO_PUBLIC_API_URL=/
RUN npx expo export --platform web

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BIOGUARD_DATA_DIR=/data
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/*.py /app/backend/
COPY backend/species_catalog.json /app/backend/
COPY bioguard_comparison_winner.zip /app/
RUN python /app/backend/setup_model.py && useradd --create-home --uid 10001 bioguard && mkdir /data && chown bioguard:bioguard /data
COPY web/ /app/web/
COPY --from=mobile /build/mobile/dist/ /app/mobile/dist/
USER bioguard
WORKDIR /app/backend
EXPOSE 8000
HEALTHCHECK --interval=30s --start-period=120s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=5)"
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000","--proxy-headers","--forwarded-allow-ips=*"]
