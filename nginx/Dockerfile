FROM nginx:1.26.1-alpine

# needed by the container healthcheck
RUN apk add --no-cache curl

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/nginx.conf
