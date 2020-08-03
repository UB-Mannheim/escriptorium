FROM nginx:1.15.0-alpine

RUN rm /etc/nginx/conf.d/default.conf

ARG NGINX_CONF=nginx.conf
ARG ACME_FILE
ARG SSL_CERT
ARG SSL_KEY

COPY ${NGINX_CONF} /etc/nginx/conf.d/nginx.conf
COPY ${SSL_CERT} /etc/certs/cert.pem
COPY ${SSL_KEY} /etc/certs/key.pem
COPY ${ACME_FILE} /usr/share/nginx/html/
