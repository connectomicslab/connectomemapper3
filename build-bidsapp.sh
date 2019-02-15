#! /bin/sh
CMP_BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo $CMP_BUILD_DATE

VERSION=$(python ../connectomemapper3/get_version.py)
echo $VERSION

VCS_REF=$(git rev-parse --verify HEAD --git-path ../connectomemapper3 | tail -1)
echo $VCS_REF

docker build --no-cache --rm --build-arg password=${BITBUCKET_PWD} --build-arg BUILD_DATE=$CMP_BUILD_DATE --build-arg VERSION=$VERSION --build-arg VCS_REF=$VCS_REF -t sebastientourbier/connectomemapper-bidsapp:dev .
