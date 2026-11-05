# Run the Java SDK from GitHub Pages

Verify anonymous Maven downloads, load the Java SDK, then optionally list agents and ask a question on your Collate instance.

## Requirements

- Java 11 or later, Maven 3.6.3 or later, Bash, and curl
- A Java SDK version published by the GitHub Pages release workflow
- For API calls, a Collate host and bot JWT token

No GitHub account or personal access token is required to download the SDK.

## Verify the first Pages release

After merging the publishing changes, run **Release AI SDK Java** from GitHub Actions on `main`, with version `0.3.0`. Wait for the workflow's anonymous download check to pass.

From the repository root, run:

```bash
cd cookbook/java-sdk
./run.sh
```

The script downloads the published POM and JAR, compiles this independent Maven project with empty settings and a fresh temporary cache, and checks that Maven obtained the same files from the Pages repository. It then constructs an SDK client without making API calls.

Successful output includes:

```text
Verified anonymous downloads from https://open-metadata.github.io/ai-sdk/maven using a fresh Maven cache.
Loaded AISdk and its dependencies. No API calls were made.
```

The temporary Maven cache is deleted when the script exits. Each run downloads dependencies again so an installed SDK cannot hide a publishing problem.

## Call an agent

Set your Collate connection details, then select `live` mode:

```bash
export AI_SDK_HOST="https://your-org.getcollate.io"
export AI_SDK_TOKEN="your-bot-jwt-token"
./run.sh live
```

This lists API-enabled agents, asks the default agent `What data assets are available?`, and prints its response and conversation ID. The JWT authenticates API calls to Collate; package downloads still use no credentials.

To use a named agent or a different question:

```bash
export AI_SDK_TEST_AGENT="YourAgentName"
export AI_SDK_QUESTION="What tables contain customer data?"
./run.sh live
```

The [Java example](src/main/java/io/openmetadata/cookbook/JavaSdkExample.java) shows both default and named agent invocation.

## Test a different release or repository

Select a published SDK version:

```bash
AI_SDK_VERSION=0.3.1 ./run.sh
```

To test a staged repository served over HTTP, override its URL:

```bash
AI_SDK_MAVEN_REPOSITORY="http://127.0.0.1:8000/maven/" ./run.sh
```

If the first download returns HTTP 404, confirm that the selected version has completed its Pages deployment. The script stops before Maven can fall back to an older copy from Central.

For the repository configuration to use in your own project, see the [Java installation guide](../../java/README.md#installation).
