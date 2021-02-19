FROM nginx:1.15.0-alpine

RUN rm /etc/nginx/conf.d/default.conf

COPY ssl_certificates.conf* /etc/nginx/conf.d/
