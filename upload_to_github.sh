#!/bin/bash

#set -x

###### Configuration ######

# First script parameter
GITHUB_API_TOKEN=$1
# Commit ID
TAG="v0.1"
# Files to use as asset
FILES="target/universal/*.tgz"
# Github API URL
GITHUB_API="https://api.github.com"
# Owner
OWNER="DingFabrik"
# Repository
REPO="rfiding-server"


###### Script ######

GITHUB_REPO="${GITHUB_API}/repos/${OWNER}/${REPO}"
AUTH_SUFFIX="access_token=${GITHUB_API_TOKEN}"

# Create Github release:
GITHUB_RELEASES_URL="${GITHUB_REPO}/releases?${AUTH_SUFFIX}"
BODY="Build URL: ${BUILD_URL}\nCommit ID: ${COMMIT}"
RELEASE_JSON=$(printf '{"tag_name": "%s", "target_commitish": "master", "name": "%s", "body": "%s", "draft": true, "prerelease": false}' "${TAG}" "${TAG}" "${BODY}")
# Python is one way to parse the JSON data returned by the previous curl request.
RELEASE_ID="$(curl --data "${RELEASE_JSON}" ${GITHUB_RELEASES_URL} | python -c "import sys, json; print json.load(sys.stdin)['id']")"

# Create tarball:
UPLOAD_FILES=( ${FILES} )

# Upload tarball
CONTENT_TYPE="Content-Type: application/x-bzip2"
UPLOAD_URL="https://uploads.github.com/repos/${OWNER}/${REPO}/releases/${RELEASE_ID}/assets?name=$(basename "${UPLOAD_FILES[0]}")&${AUTH_SUFFIX}"
curl --data-binary @"${UPLOAD_FILES[0]}" -H "${CONTENT_TYPE}" "${UPLOAD_URL}"
