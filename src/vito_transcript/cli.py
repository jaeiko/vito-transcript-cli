"""Typer application entry point."""

import typer

app = typer.Typer(
    help="Transcribe audio files using the RTZR STT file API.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Provide commands for RTZR VITO transcription."""


@app.command()
def transcribe() -> None:
    """Transcribe an audio file (not implemented yet)."""
    typer.echo("The transcription workflow is not implemented yet.")
