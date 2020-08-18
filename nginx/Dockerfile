FROM nginx:1.15.0-alpine

RUN rm /etc/nginx/conf.d/default.conf

ARG NGINX_CONF=nginx.conf

COPY ${NGINX_CONF} /etc/nginx/conf.d/nginx.conf
COPY ssl_certificates.conf* /etc/nginx/conf.d/
