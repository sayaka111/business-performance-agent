# DeepSeek provider

Gemini remains available with `--gemini` or `--provider gemini`. Select DeepSeek
with `--provider deepseek`. Both providers use the same intent parser, constrained
router, JSON schemas/local validation, two-attempt retry limit, deterministic
report fallback and trace format. Current behavior, reliability observations and
remaining intent failures are documented in the [evaluation overview](portfolio/evaluation.md).

DeepSeek uses Python's standard-library HTTP client, so no extra package is needed
beyond the existing editable project installation. Gemini still requires its
existing optional `google-genai` dependency.

## Configuration

Set these in the process environment; the application does not auto-load `.env`:

| Variable | Default |
|---|---|
| DEEPSEEK_API_KEY | Required for real requests; never logged |
| DEEPSEEK_BASE_URL | https://api.deepseek.com |
| DEEPSEEK_MODEL | deepseek-v4-flash |
| DEEPSEEK_TIMEOUT | 60 seconds per request |

Defaults live in `DeepSeekSettings`. `--model` overrides the selected provider's
model. The endpoint uses `/chat/completions`, JSON mode, non-streaming output and
disabled thinking. JSON mode is followed by the same strict local validation used
for Gemini; it is not treated as a guarantee that every field is correct.
API references: [first API call](https://api-docs.deepseek.com/) and
[JSON output](https://api-docs.deepseek.com/guides/json_mode/).

## Smoke test

In PowerShell, after setting `$env:DEEPSEEK_API_KEY` to your key:

```powershell
# Run from the repository root containing pyproject.toml.
python -m business_performance_agent.app.provider_smoke --provider deepseek
```

This explicitly sends at most one request and checks structured intent against a
fixed GMV question and periods. Success prints `API_OK`. It does not run an Eval or
query business data. Failures expose only safe event metadata, not response bodies
or headers. This command is optional and is not required for offline use.


## CLI diagnosis

```powershell
python -m business_performance_agent --provider deepseek --input examples/gmv_input.json --json
```

This uses synthetic data with a real provider. For measured reliability and known intent failures, see [evaluation](portfolio/evaluation.md). Ordinary discovery uses mocked transports and skips Live tests.
