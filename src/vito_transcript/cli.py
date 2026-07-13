"""Typer command-line interface for RTZR file transcription."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Annotated, Any

import typer

from vito_transcript.cli_config import (
    Domain,
    Model,
    OutputFormat,
    build_rtzr_config,
    selected_formats,
    validate_audio_file,
    validate_polling_options,
)
from vito_transcript.client import RTZRClient
from vito_transcript.exceptions import RTZRError, RTZROutputError
from vito_transcript.exporters import (
    render_json,
    render_markdown,
    render_srt,
    render_text,
    write_text_file,
)
from vito_transcript.models import Utterance, parse_utterances

DEFAULT_OUTPUT_DIR = Path("outputs")

app = typer.Typer(
    help="Transcribe audio files using the RTZR STT file API.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Provide commands for RTZR VITO transcription."""


@app.command()
def transcribe(
    audio_file: Annotated[
        Path,
        typer.Argument(help="Local audio file to transcribe."),
    ],
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", help="Directory for generated transcripts."),
    ] = DEFAULT_OUTPUT_DIR,
    output_format: Annotated[
        OutputFormat,
        typer.Option("--format", help="Transcript output format."),
    ] = OutputFormat.ALL,
    model: Annotated[
        Model,
        typer.Option("--model", help="RTZR transcription model."),
    ] = Model.SOMMERS,
    language: Annotated[
        str,
        typer.Option("--language", help="Transcription language."),
    ] = "ko",
    domain: Annotated[
        Domain,
        typer.Option("--domain", help="RTZR transcription domain."),
    ] = Domain.GENERAL,
    diarization: Annotated[
        bool,
        typer.Option(
            "--diarization/--no-diarization",
            help="Enable or disable speaker diarization.",
        ),
    ] = False,
    speaker_count: Annotated[
        int | None,
        typer.Option("--speaker-count", help="Known number of speakers."),
    ] = None,
    keywords: Annotated[
        list[str] | None,
        typer.Option("--keyword", help="Keyword to boost; repeat for multiple values."),
    ] = None,
    poll_interval: Annotated[
        float,
        typer.Option("--poll-interval", help="Polling interval in seconds."),
    ] = 5.0,
    timeout: Annotated[
        float,
        typer.Option("--timeout", help="Overall polling timeout in seconds."),
    ] = 1800.0,
) -> None:
    """Transcribe an audio file and export the completed result."""
    try:
        validate_audio_file(audio_file)
        validate_polling_options(poll_interval, timeout)
        config = build_rtzr_config(
            model=model,
            language=language,
            domain=domain,
            diarization=diarization,
            speaker_count=speaker_count,
            keywords=keywords,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from None

    typer.echo(f"Transcribing: {audio_file}")
    try:
        with RTZRClient.from_env() as client:
            payload = client.transcribe(
                audio_file,
                config,
                poll_interval=poll_interval,
                timeout=timeout,
            )
        rendered_outputs = _render_outputs(
            payload,
            audio_file=audio_file,
            output_format=output_format,
        )
        created_paths = _write_outputs(
            rendered_outputs,
            audio_file=audio_file,
            output_dir=output_dir,
        )
    except KeyboardInterrupt:
        typer.echo("Transcription cancelled.", err=True)
        raise typer.Exit(code=130) from None
    except RTZRError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from None

    typer.echo("Transcription completed.")
    typer.echo("Created:")
    for path in created_paths:
        typer.echo(f"- {path}")


def _render_outputs(
    payload: Mapping[str, Any],
    *,
    audio_file: Path,
    output_format: OutputFormat,
) -> list[tuple[OutputFormat, str]]:
    formats = selected_formats(output_format)
    utterance_formats = {
        OutputFormat.TXT,
        OutputFormat.MARKDOWN,
        OutputFormat.SRT,
    }
    utterances: Sequence[Utterance] = ()
    if any(format_ in utterance_formats for format_ in formats):
        utterances = parse_utterances(payload)

    rendered_outputs = []
    for format_ in formats:
        if format_ is OutputFormat.TXT:
            content = render_text(utterances)
        elif format_ is OutputFormat.MARKDOWN:
            content = render_markdown(
                utterances,
                title=f"Transcript: {audio_file.name}",
            )
        elif format_ is OutputFormat.SRT:
            content = render_srt(utterances)
        else:
            content = render_json(payload)
        rendered_outputs.append((format_, content))
    return rendered_outputs


def _write_outputs(
    rendered_outputs: Sequence[tuple[OutputFormat, str]],
    *,
    audio_file: Path,
    output_dir: Path,
) -> list[Path]:
    created_paths = []
    for output_format, content in rendered_outputs:
        output_path = output_dir / f"{audio_file.stem}.{output_format.value}"
        if output_path.resolve() == audio_file.resolve():
            raise RTZROutputError("Refusing to overwrite the source audio file.")
        created_paths.append(write_text_file(output_path, content))
    return created_paths
