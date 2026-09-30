FROM python:3.12-slim

# Dépendances système :
# - libpq5           : client PostgreSQL (psycopg2)
# - gdal / geos       : geopandas, fiona, shapely
# - pango/cairo/gdk   : weasyprint (génération PDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq5 libpq-dev \
    gdal-bin libgdal-dev \
    libgeos-c1v5 libgeos-dev \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

ENV GDAL_CONFIG=/usr/bin/gdal-config

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads uploads/alertes

EXPOSE 5052

CMD ["gunicorn", "-k", "gevent", "-w", "4", "-b", "0.0.0.0:5052", "--timeout", "120", "app:app"]
