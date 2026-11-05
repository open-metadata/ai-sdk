#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
sdk_version="${AI_SDK_VERSION:-0.3.0}"
repository_url="${AI_SDK_MAVEN_REPOSITORY:-https://open-metadata.github.io/ai-sdk/maven/}"
repository_url="${repository_url%/}"
check_dir=$(mktemp -d)
trap 'rm -rf "$check_dir"' EXIT

echo "Checking SDK $sdk_version at $repository_url"
artifact_path="org/open-metadata/ai-sdk/$sdk_version/ai-sdk-$sdk_version"
for extension in pom jar; do
  curl --disable --fail --silent --show-error --location \
    "$repository_url/$artifact_path.$extension" --output "$check_dir/published.$extension"
done

printf '%s\n' '<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"/>' > "$check_dir/settings.xml"
maven_args=(--batch-mode --no-transfer-progress
  --settings "$check_dir/settings.xml" --global-settings "$check_dir/settings.xml"
  "-Dmaven.repo.local=$check_dir/repository"
  "-Dai-sdk.version=$sdk_version" "-Dai-sdk.repository=$repository_url")
mvn "${maven_args[@]}" clean compile

cached_artifact="$check_dir/repository/$artifact_path"
for extension in pom jar; do
  cmp "$check_dir/published.$extension" "$cached_artifact.$extension"
  grep -Fq "ai-sdk-$sdk_version.$extension>openmetadata=" "$(dirname "$cached_artifact")/_remote.repositories"
done
echo "Verified anonymous downloads from $repository_url using a fresh Maven cache."

mvn "${maven_args[@]}" exec:java "-Dexec.args=$*"
