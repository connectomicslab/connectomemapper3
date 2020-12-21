#! /bin/sh
CMP_BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "$CMP_BUILD_DATE"

VERSION=$(python get_version.py)
echo "$VERSION"

VCS_REF=$(git rev-parse --verify HEAD)
echo "$VCS_REF"

docker build --rm --build-arg BUILD_DATE="$CMP_BUILD_DATE "\
				  --build-arg VCS_REF="$VCS_REF" \
				  --build-arg VERSION="$VERSION" \
				  -t sebastientourbier/connectomemapper-bidsapp:"${VERSION}" .
