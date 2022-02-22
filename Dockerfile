FROM node:12-alpine as frontend

WORKDIR /build
COPY ./front /build
RUN npm ci && npm run production

# Pull official base image
FROM registry.gitlab.com/scripta/escriptorium/base:0.10.3

# try to autodetect number of cpus available
# ENV NGINX_WORKER_PROCESSES auto

ARG VERSION_DATE="passthistobuildcmd"
ENV VERSION_DATE=$VERSION_DATE
ENV FRONTEND_DIR=/usr/src/app/front

# set work directory
WORKDIR /usr/src/app

COPY ./app/entrypoint.sh /usr/src/app/entrypoint.sh
COPY ./app /usr/src/app/
COPY --from=frontend /build/dist /usr/src/app/front

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
