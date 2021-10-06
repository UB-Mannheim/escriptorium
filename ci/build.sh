#!/bin/sh -e
# Build the eScriptorium Docker image.
# Requires CI_PROJECT_DIR and CI_REGISTRY_IMAGE to be set.
# VERSION defaults to latest.
# Will automatically login to a registry if CI_REGISTRY, CI_REGISTRY_USER and CI_REGISTRY_PASSWORD are set.
# Will only push an image if $CI_REGISTRY is set.
NAME=$1
if [ -z "$NAME" ]; then
  echo "Missing NAME as first cli arg"
  exit 1
fi

if [ -z "$VERSION" ]; then
	VERSION=${CI_COMMIT_TAG:-latest}
fi

if [ -z "$VERSION" -o -z "$CI_PROJECT_DIR" -o -z "$CI_REGISTRY_IMAGE" ]; then
	echo Missing environment variables
	exit 1
fi

if [ -n "$CI_REGISTRY" -a -n "$CI_REGISTRY_USER" -a -n "$CI_REGISTRY_PASSWORD" ]; then
	echo Logging in to container registry…
	echo $CI_REGISTRY_PASSWORD | docker login -u $CI_REGISTRY_USER --password-stdin $CI_REGISTRY
fi

cd $CI_PROJECT_DIR

if [ "$NAME" = "app" ]; then
	# git is needed to retrieve the base tag
	apk add git

  # App image uses the root level of the container
  DOCKER_IMAGE="$CI_REGISTRY_IMAGE:$VERSION"
  docker build . -t $DOCKER_IMAGE --build-arg VERSION_DATE=$(git tag | sort -V | tail -1)

elif [ "$NAME" = "exim" ]; then
  DOCKER_IMAGE="$CI_REGISTRY_IMAGE/mail:$VERSION"
  docker build exim/ -t $DOCKER_IMAGE

elif [ "$NAME" = "nginx" ]; then
  DOCKER_IMAGE="$CI_REGISTRY_IMAGE/nginx:$VERSION"
  docker build nginx/ -t $DOCKER_IMAGE

else
  echo "Unsupported image $NAME"
  exit 1
fi

if [ -n "$CI_REGISTRY" ] && [ "$CI_COMMIT_BRANCH" = "master" -o -n "$CI_COMMIT_TAG" ]; then
	docker push $DOCKER_IMAGE
fi
