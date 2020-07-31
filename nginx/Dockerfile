FROM nginx:1.15.0-alpine

RUN rm /etc/nginx/conf.d/default.conf

ARG NGINX_CONF=nginx.conf
ARG SSL_CERT=./certs/fullchain.pem
ARG SSL_KEY=./certs/privkey.pem

COPY ${NGINX_CONF} /etc/nginx/conf.d/nginx.conf
COPY ${SSL_CERT} /etc/certs/cert.pem
COPY ${SSL_KEY} /etc/certs/key.pem
