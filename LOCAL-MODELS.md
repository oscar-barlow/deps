# OmniCoder in pi

The APT declarations include `llama.cpp-tools` and
`libggml0-backend-vulkan`. Weights are downloaded separately and stay outside
Git. Download and run the 4-bit model with:

```sh
llama-cli -hf Tesslate/OmniCoder-9B-GGUF:Q4_K_M \
  --device Vulkan1 -ngl 999 -c 8192 -n 64 --single-turn \
  -p 'Explain what a unit test does.'
```

`-hf` downloads into the Hugging Face/llama.cpp cache and reuses cached files
on later runs. Run `llama-cli --list-devices` first: on this laptop `Vulkan1`
is the RTX 5070; `Vulkan0` is Intel graphics. GPU device numbers can change.

## Start the server

Leave this running in a separate terminal:

```sh
llama-server -hf Tesslate/OmniCoder-9B-GGUF:Q4_K_M \
  --alias omnicoder-9b --device Vulkan1 -ngl 999 \
  -c 8192 -np 1 --jinja --host 127.0.0.1 --port 8080
```

This uses single-model mode with an explicit alias. It does not use pi's
`/llama` router interface. Check startup logs for all model layers offloaded
to the NVIDIA GPU. If allocation fails, reduce context to 4096 in both the
server command and pi configuration below.

## Connect pi

Merge the following provider into `~/.pi/agent/models.json`. Preserve any
existing providers. The dummy key is for pi's provider availability check;
the local server does not require authentication.

```json
{
  "providers": {
    "local-llama": {
      "baseUrl": "http://127.0.0.1:8080/v1",
      "api": "openai-completions",
      "apiKey": "local",
      "compat": {
        "supportsDeveloperRole": false,
        "supportsReasoningEffort": false
      },
      "models": [
        {
          "id": "omnicoder-9b",
          "name": "OmniCoder 9B local",
          "reasoning": true,
          "input": ["text"],
          "contextWindow": 8192,
          "maxTokens": 2048
        }
      ]
    }
  }
}
```

Start pi in your project:

```sh
pi --model local-llama/omnicoder-9b
```

Alternatively choose it in `/model`. Ctrl+S in the model picker saves it as
the startup default. Keep early tasks small: the 8K context includes pi's
system prompt, tool definitions, conversation, file contents, and output.

## Enable subagents

The installed pi npm package includes the upstream example extension. Run:

```sh
pi_package="$(npm root -g)/@earendil-works/pi-coding-agent"
test -f "$pi_package/examples/extensions/subagent/index.ts"
mkdir -p ~/.pi/agent/extensions/subagent ~/.pi/agent/agents
ln -sfn "$pi_package/examples/extensions/subagent/index.ts" \
  ~/.pi/agent/extensions/subagent/index.ts
ln -sfn "$pi_package/examples/extensions/subagent/agents.ts" \
  ~/.pi/agent/extensions/subagent/agents.ts
```

These links follow the currently installed package, so updating pi also
updates the example. Check for existing files at those destinations before
running the linking commands if you have previously configured subagents.
With this repo's default npm prefix, `pi_package` is
`~/.local/lib/node_modules/@earendil-works/pi-coding-agent`.

In pi, authenticate your cloud provider through `/login` and use `/model`
to find the exact available cloud model ID. Create
`~/.pi/agent/agents/adviser.md` with the following contents, replacing
`PROVIDER/MODEL_ID` with that cloud model's provider-qualified ID:

```markdown
---
name: adviser
description: Cloud adviser for diagnosis, design decisions, and stuck tasks
tools: read, grep, find, ls
model: PROVIDER/MODEL_ID
---

You advise a local coding agent. Read relevant code if needed, diagnose the
problem, and return a concise plan with file references and validation steps.
Explain assumptions. Do not modify files. Prefer small, concrete changes.
```

The adviser's configured tools inspect the project but do not edit it or run
shell commands. Its prompt, selected code, and tool results are sent to the
cloud provider. A subagent with no `model` field inherits the parent's model;
set this field explicitly for cloud advice.

Restart pi after installing the extension. In the local session, try:

```text
Use the adviser subagent to inspect this error and suggest a fix.
Then implement the fix locally and run the relevant tests.
```

Suggested session instruction:

```text
Handle routine edits and tests locally. Consult adviser before architectural
changes, when a failure is unclear, or after two unsuccessful fixes. Give it
the goal, relevant files, exact errors, and what you have already tried.
```

This is a prompt policy, not an automatic enforced routing rule. For manual
cloud takeover, switch with `/model`, get help, and select the local model
again. Unlike a subagent, switching the main model sends the session context
to the selected provider.

References: [OmniCoder model card](https://huggingface.co/Tesslate/OmniCoder-9B),
[pi subagent example](https://github.com/earendil-works/pi/tree/main/packages/coding-agent/examples/extensions/subagent).
