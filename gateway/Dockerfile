# Imagen del API Gateway: nginx + la plantilla de configuración + el frontend.
# Se construye desde la RAÍZ del repo (necesita la carpeta frontend/):
#   docker build -f gateway/Dockerfile -t itinerario/gateway .
FROM nginx:1.27-alpine

# Valores por defecto para Docker Compose (en Kubernetes se sobreescriben)
ENV DNS_RESOLVER=127.0.0.11 \
    SERVICE_SUFFIX=""

COPY gateway/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY frontend /usr/share/nginx/html

EXPOSE 80
