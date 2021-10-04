#!/bin/sh -e
# Build the eScriptorium Docker image.
# Requires CI_PROJECT_DIR and CI_REGISTRY_IMAGE to be set.
# VERSION defaults to latest.
# Will automatically login to a registry if CI_REGISTRY, CI_REGISTRY_USER and CI_REGISTRY_PASSWORD are set.
# Will only push an image if $CI_REGISTRY is set.

if [ -z "$VERSION" ]; then
	# Ensure this is a base tag, then tell sh to remove the base- prefix.
	case $CI_COMMIT_TAG in
		base-*)
			VERSION=${CI_COMMIT_TAG#base-};;
		*)
			echo build-base can only be used with 'base-*' tags.
			exit 1;;
	esac
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

# Directly build and push as we always are on a base tag
docker build app/ -t "$CI_REGISTRY_IMAGE/base:$VERSION"
docker push "$CI_REGISTRY_IMAGE/base:$VERSION"
