# vito-transcript-cli

`vito-transcript-cli` is a Python command-line application that uploads a local
audio file to the RTZR file STT API, polls until transcription reaches a terminal
state, and exports the completed result as plain text, Markdown, SRT subtitles,
raw JSON, or all four formats.

## Key features

- Complete RTZR file STT flow: authentication, upload, polling, and export.
- Supported audio extensions: `mp4`, `m4a`, `mp3`, `amr`, `flac`, and `wav`.
- Output formats: TXT, Markdown, SRT, and UTF-8-friendly raw JSON.
- Korean and Japanese validation for the `sommers` model, plus CLI access to the
  `whisper` model.
- Optional speaker diarization, known speaker count, domain selection, and
  repeatable keyword boosting.
- Explicit HTTP and overall polling timeouts.
- Safe project-specific errors that avoid printing credentials, access tokens,
  headers, or complete API responses.
- Mocked unit tests that do not require RTZR credentials or network access.

## How it works

1. The CLI validates the audio path, extension, options, and RTZR configuration.
2. `RTZRClient` exchanges the configured client credentials for an access token.
3. The audio file and JSON configuration are submitted as multipart form data.
4. The client polls the transcription job with the Bearer token until it is
   `completed`, `failed`, or reaches the configured timeout.
5. Completed utterances are validated and converted to immutable model objects
   for TXT, Markdown, and SRT rendering. JSON export preserves the complete raw
   completed response.
6. Selected outputs are written as UTF-8 files beneath the output directory.

The CLI prints high-level start and completion messages and the created paths. It
does not print every polling status.

## Requirements

- Python 3.11 or newer.
- An RTZR Developers application with your own client credentials.
- A local audio file in a supported format that you are legally permitted to
  process. This repository does not include sample audio; provide your own
  copyright-safe recording.

## Installation

Create a virtual environment and install the project in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

On Windows PowerShell, activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## RTZR credentials and environment setup

Copy the placeholder environment file:

```bash
cp .env.example .env
```

Then replace the placeholders in `.env` with credentials issued for your RTZR
Developers application:

```dotenv
RTZR_CLIENT_ID=replace_with_your_client_id
RTZR_CLIENT_SECRET=replace_with_your_client_secret
```

Never commit `.env`. It is ignored by this repository, but you should still
review staged changes before every commit. The CLI loads `.env` locally through
`python-dotenv`; it never prints or writes credentials or access tokens.

## Quick start

```bash
vito-transcript transcribe path/to/audio.m4a \
  --output-dir outputs \
  --format all \
  --language ko
```

On success, the CLI prints output similar to:

```text
Transcribing: path/to/audio.m4a
Transcription completed.
Created:
- outputs/audio.txt
- outputs/audio.md
- outputs/audio.srt
- outputs/audio.json
```

## Command options

Run `vito-transcript transcribe --help` to see the installed command help.

| Option | Accepted values and behavior | Default |
| --- | --- | --- |
| `--output-dir` | Directory in which generated files are written | `outputs` |
| `--format` | `txt`, `md`, `srt`, `json`, or `all` | `all` |
| `--model` | `sommers` or `whisper` | `sommers` |
| `--language` | Language value sent to RTZR; `sommers` accepts only `ko` or `ja` in the current CLI | `ko` |
| `--domain` | `GENERAL` or `CALL` | `GENERAL` |
| `--diarization / --no-diarization` | Enable or disable speaker diarization | disabled |
| `--speaker-count` | Optional integer greater than or equal to zero; requires `--diarization` | omitted |
| `--keyword` | Keyword sent to RTZR; repeat the option to provide multiple keywords | omitted |
| `--poll-interval` | Positive polling interval in seconds | `5.0` |
| `--timeout` | Positive overall polling timeout in seconds | `1800.0` |

Model, domain, and output-format values are case-sensitive. Audio file extensions
are validated case-insensitively.

## Usage examples

### Generate all formats

```bash
vito-transcript transcribe recordings/interview.m4a \
  --output-dir outputs \
  --format all \
  --language ko
```

### Generate TXT only

```bash
vito-transcript transcribe recordings/interview.wav \
  --output-dir outputs \
  --format txt
```

### Enable diarization with a known speaker count

```bash
vito-transcript transcribe recordings/conversation.mp3 \
  --output-dir outputs \
  --format all \
  --diarization \
  --speaker-count 2
```

### Supply repeated keywords

```bash
vito-transcript transcribe recordings/meeting.m4a \
  --keyword 리턴제로 \
  --keyword 음성인식 \
  --format md
```

### Use the Whisper model

```bash
vito-transcript transcribe recordings/english.m4a \
  --model whisper \
  --language en \
  --domain GENERAL \
  --format srt
```

## Generated outputs

Output filenames use the input filename stem. For example,
`recordings/interview.m4a` with `--output-dir outputs --format all` creates:

- `outputs/interview.txt`
- `outputs/interview.md`
- `outputs/interview.srt`
- `outputs/interview.json`

TXT contains message text in utterance order:

```text
안녕하세요.
현재 파이썬으로 프로그램을 개발하고 있습니다.
```

Markdown includes millisecond timestamps and speaker labels:

```markdown
# Transcript: interview.m4a

**[00:00:02.036] Speaker 1**

안녕하세요.
```

SRT includes sequence numbers and start/end timestamps:

```srt
1
00:00:02,036 --> 00:00:07,256
[Speaker 1] 안녕하세요.
```

JSON preserves the complete completed RTZR API payload rather than rebuilding it
from the parsed utterance models:

```json
{
  "id": "job-id",
  "status": "completed",
  "results": {
    "utterances": [
      {
        "start_at": 2036,
        "duration": 5220,
        "spk": 0,
        "msg": "안녕하세요.",
        "lang": "ko"
      }
    ]
  }
}
```

## Project structure

```text
vito-transcript-cli/
├── .github/workflows/test.yml
├── docs/
│   ├── README.md
│   ├── architecture.md
│   └── troubleshooting.md
├── samples/README.md
├── src/vito_transcript/
│   ├── cli.py
│   ├── cli_config.py
│   ├── client.py
│   ├── exceptions.py
│   ├── models.py
│   └── exporters/
├── tests/
├── .env.example
├── pyproject.toml
└── README.md
```

The `samples/` directory contains instructions only. Local recordings and
generated `outputs/` are intentionally ignored by Git.

## Error handling and security

Invalid command usage—such as an unsupported extension, a negative timeout, or
`--speaker-count` without `--diarization`—is reported by Typer with its normal
usage error exit code. Expected RTZR, parsing, timeout, and output failures are
reported without a Python traceback and exit with code 1. Cancellation with
Ctrl+C exits with code 130.

The client reads credentials from the environment (including the local `.env`)
but does not write them to another file. The access token is kept in client
memory. Authentication sends the client ID and secret only to the authentication
endpoint, and Bearer tokens are sent only to authenticated transcription
endpoints. The client does not include credentials, tokens, request headers, or
complete raw responses in its error messages.

Audio is uploaded to the RTZR API. Confirm that you have the necessary rights and
consent before processing any recording.

## Testing and GitHub Actions

Install the development tools and run the same checks used by CI:

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
```

The tests use mocked HTTP sessions and temporary files; they do not require RTZR
credentials, a `.env` file, local audio, sleeping, or network access. The existing
GitHub Actions workflow runs linting, format checks, and tests on Python 3.11,
3.12, 3.13, and 3.14.

## Troubleshooting

See the [troubleshooting guide](docs/troubleshooting.md) for installation,
credentials, authentication, input validation, timeout, network, and output
issues.

## References

- [RTZR Developers documentation](https://developers.rtzr.ai/docs/en/)
- [RTZR authentication API](https://developers.rtzr.ai/docs/en/authentications/)
- [RTZR file STT API](https://developers.rtzr.ai/docs/en/stt-file/)

This implementation follows the official RTZR authentication, file submission,
and polling flow. Refer to the official documentation for account setup, service
limits, current API behavior, and supported configuration details.

## License

This project is declared as MIT-licensed in `pyproject.toml`.
