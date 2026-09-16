FROM node:24-alpine AS frontend
WORKDIR /build
COPY Frontend/package*.json ./
RUN npm ci
COPY Frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production PORT=8000
COPY Backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY Backend/ ./Backend/
COPY --from=frontend /build/dist ./Frontend/dist
RUN useradd --create-home nexus && chown -R nexus:nexus /app
USER nexus
EXPOSE 8000
CMD ["sh", "-c", "python Backend/manage.py migrate && cd Backend && gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --timeout 60 api:app"]
