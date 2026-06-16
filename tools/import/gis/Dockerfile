# SUMO GIS API container image (ADR-008)

FROM ghcr.io/eclipse-sumo/sumo:latest

WORKDIR /opt/sumo
ENV SUMO_HOME=/opt/sumo
ENV GIS_API_WORKSPACE=/data/scenarios
ENV PYTHONUNBUFFERED=1

COPY tools/import/gis/requirements.txt /tmp/gis-requirements.txt
RUN pip install --no-cache-dir -r /tmp/gis-requirements.txt

COPY tools/import/gis /opt/sumo/tools/import/gis

EXPOSE 8000
VOLUME ["/data/scenarios"]

CMD ["python", "tools/import/gis/api/main.py"]
