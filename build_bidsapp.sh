#! /bin/sh
CMP_BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "$CMP_BUILD_DATE"

VERSION=$(python get_version.py)
echo "$VERSION"

VCS_REF=$(git rev-parse --verify HEAD)
echo "$VCS_REF"

MAIN_DOCKER="sebastientourbier/connectomemapper-ubuntu16.04"
echo "$MAIN_DOCKER"

docker build --rm --build-arg BUILD_DATE="$CMP_BUILD_DATE "\
				  --build-arg VCS_REF="$VCS_REF" \
				  --build-arg VERSION="$VERSION" \
				  -t "${MAIN_DOCKER}":"${VERSION}" ./ubuntu16.04 \


docker build --no-cache --rm --build-arg BUILD_DATE="$CMP_BUILD_DATE" \
                             --build-arg VERSION="$VERSION" \
                             --build-arg MAIN_VERSION="$VERSION" \
                             --build-arg VCS_REF="$VCS_REF" \
                             --build-arg MAIN_DOCKER="$MAIN_DOCKER" \
                             -t sebastientourbier/connectomemapper-bidsapp:"${VERSION}" .
