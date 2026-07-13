# Troubleshooting

This guide describes common local CLI failures. Do not include credentials,
tokens, or full API responses when sharing diagnostics.

## `vito-transcript`: command not found

**Typical symptom:** Your shell reports that `vito-transcript` is unknown or not
recognized.

**Likely cause:** The virtual environment is not active, or the editable package
installation did not complete in the current environment.

**Action:** Activate `.venv`, run `python -m pip install -e .` from the repository
root, and verify with `vito-transcript --help`. On Windows PowerShell, activate
with `.venv\Scripts\Activate.ps1`.

## Missing `RTZR_CLIENT_ID` or `RTZR_CLIENT_SECRET`

**Typical symptom:** The command exits with a configuration error stating that
both RTZR variables must be configured.

**Likely cause:** One or both environment variables are absent or empty.

**Action:** Copy `.env.example` to `.env`, enter credentials issued for your RTZR
Developers application, and retry. Do not paste credentials into command history,
logs, issues, or commits.

## `.env` is not loaded

**Typical symptom:** Credentials exist in a file, but the CLI still reports them
as missing.

**Likely cause:** The file is not named exactly `.env`, is in an unexpected
location, contains malformed entries, or the command is running from a
different installation than expected.

**Action:** Confirm that the file is named `.env`, uses
`RTZR_CLIENT_ID=value` and `RTZR_CLIENT_SECRET=value` entries, and that the
active environment points to this checkout. You can alternatively export the two
variables in the current shell without printing their values.

## Authentication failure

**Typical symptom:** The command exits with an RTZR authentication error before
transcription begins.

**Likely cause:** Credentials are invalid, revoked, copied incorrectly, or belong
to an RTZR application that is not ready for API use.

**Action:** Verify the application in the RTZR Developers console and issue or
copy fresh credentials into `.env`. Never include the credential values in a bug
report.

## Unsupported audio extension

**Typical symptom:** Typer reports `Unsupported audio format` as a usage error.

**Likely cause:** The filename does not end in one of the CLI-supported
extensions: `mp4`, `m4a`, `mp3`, `amr`, `flac`, or `wav`.

**Action:** Provide a supported file or convert your copyright-safe source audio
with a trusted local tool. Renaming an unsupported file does not convert its
encoding.

## Missing audio file

**Typical symptom:** Typer reports that the audio file does not exist or is not a
regular file.

**Likely cause:** The path is misspelled, relative to a different working
directory, or points to a directory.

**Action:** Confirm the path with your shell, then pass the correct file path as
the positional `AUDIO_FILE` argument. File validation does not read or upload the
audio.

## `--speaker-count` without `--diarization`

**Typical symptom:** Typer reports `speaker-count requires --diarization`.

**Likely cause:** A known speaker count was provided while speaker diarization is
disabled.

**Action:** Add `--diarization`, or remove `--speaker-count`. The count must be an
integer greater than or equal to zero.

## Invalid Sommers language

**Typical symptom:** Typer reports that the Sommers model supports only `ko` or
`ja`.

**Likely cause:** Another language was supplied while `--model sommers` was
selected.

**Action:** Use `--language ko` or `--language ja`, or explicitly choose
`--model whisper` with the intended RTZR-supported language value.

## Transcription timeout

**Typical symptom:** The CLI reports that transcription did not complete before
the timeout.

**Likely cause:** The file needs longer than the current overall timeout, RTZR is
under load, or network requests are delayed.

**Action:** Retry with a larger positive `--timeout` and keep
`--poll-interval` positive. The local client stops waiting at its monotonic
deadline; it does not implement cancellation of the remote job.

## Failed transcription

**Typical symptom:** RTZR returns the terminal `failed` status and the CLI exits
with code 1.

**Likely cause:** The file may be corrupt, unreadable, empty, unsuitable for the
selected configuration, or rejected by the service.

**Action:** Verify that the audio plays locally, confirm its actual encoding and
configuration options, and retry. If a safe RTZR error code or message is shown,
use that diagnostic when consulting the official documentation without sharing
credentials or tokens.

## HTTP or network errors

**Typical symptom:** The CLI reports that an authentication, submission, or
status request could not be completed, or reports an HTTP status code.

**Likely cause:** Internet connectivity, DNS, proxy, TLS, firewall, RTZR service,
rate-limit, or account permission issues may be involved.

**Action:** Check network access to the official RTZR endpoints, proxy/firewall
policy, RTZR service documentation, and account limits. Retry later for transient
failures. Do not disable TLS verification or expose Authorization headers while
debugging.

## Output write failure

**Typical symptom:** The CLI reports `Could not write output file` and exits with
code 1.

**Likely cause:** The destination is read-only, a parent component is a regular
file, permissions are insufficient, storage is full, or the output path conflicts
with another resource.

**Action:** Choose a writable directory with `--output-dir`, fix its permissions
or path conflict, verify available storage, and retry. The CLI refuses to
overwrite the source audio file.

## Expected output files are absent

**Typical symptom:** Transcription ran, but the expected extension is not present
under the output directory.

**Likely cause:** The command failed before file writing, a single `--format` was
selected, or a different `--output-dir` was supplied. Filenames use the input
stem, not the complete input filename.

**Action:** Check the exit code and final `Created:` path list. Run with
`--format all` to request `.txt`, `.md`, `.srt`, and `.json`, and inspect the exact
output directory passed to the command.

## Confirm `.env`, local audio, and outputs are ignored

**Typical symptom:** Sensitive or local files appear as candidates for a Git
commit.

**Likely cause:** The file is outside the covered paths, has an unexpected
extension, was force-added previously, or ignore rules were changed.

**Action:** From the repository root, inspect the active ignore rule with:

```bash
git check-ignore -v .env samples/example.m4a outputs/example.txt
```

The repository ignores `.env`, supported sample-audio extensions directly under
`samples/`, and the `outputs/` directory. If a file is already tracked,
`.gitignore` alone does not remove it from Git history or the index; review the
repository state carefully before taking any index-changing action.
