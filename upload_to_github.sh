#!/bin/bash

# This script uploads files from the folder target/universal to Github releases.
# The first parameter of this script must be the API token.

# WARNING: 
# Do not uncomment in production as it can expose the token.
#set -x

if [[ "${IS_GIT_TAG}" != "true" ]]; then
    # Build is not triggerd by a git tag push webhook.
    # See http://docs.shippable.com/ci/env-vars/#stdEnv
    echo "Build is not triggerd by a git tag push webhook."
    exit 0
fi

###### Configuration ######
# Token grants access to the github API
GITHUB_API_TOKEN=$1
# Files to use as asset
FILES="target/universal/*.tgz"
# Github API URL
GITHUB_API="https://api.github.com"

###### Script ######

GITHUB_REPO="${GITHUB_API}/repos/${ORG_NAME}/${REPO_NAME}"
AUTH_SUFFIX="access_token=${GITHUB_API_TOKEN}"

# Determine files for release
UPLOAD_FILES=( ${FILES} )
if [[ "$OSTYPE" == "darwin"* ]]; then
    HASH=$(md5 -r ${UPLOAD_FILES[0]} | awk '{ print $1 }')
else
    HASH=$(md5sum ${UPLOAD_FILES[0]} | awk '{ print $1 }')
fi

# Create Github release:
GITHUB_RELEASES_URL="${GITHUB_REPO}/releases?${AUTH_SUFFIX}"
BODY="Build URL: ${BUILD_URL}\nCommit ID: ${COMMIT}\nMD5 Hash: ${HASH}"
RELEASE_JSON=$(printf '{"tag_name": "%s", "target_commitish": "master", "name": "%s", "body": "%s", "draft": true, "prerelease": false}' "${GIT_TAG_NAME}" "${GIT_TAG_NAME}" "${BODY}")
# Python is one way to parse the JSON data returned by the previous curl request.
RESULT=$(curl --data "${RELEASE_JSON}" ${GITHUB_RELEASES_URL})
RELEASE_ID="$(echo $RESULT | python -c "import sys, json; print json.load(sys.stdin)['id']")"


# Upload artifact
CONTENT_TYPE="Content-Type: application/x-bzip2"
UPLOAD_URL="https://uploads.github.com/repos/${ORG_NAME}/${REPO_NAME}/releases/${RELEASE_ID}/assets?name=$(basename "${UPLOAD_FILES[0]}")&${AUTH_SUFFIX}"
curl --data-binary @"${UPLOAD_FILES[0]}" -H "${CONTENT_TYPE}" "${UPLOAD_URL}"
