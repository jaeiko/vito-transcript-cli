"""Tests for the command-line interface skeleton."""

from typer.testing import CliRunner

from vito_transcript.cli import app

runner = CliRunner()


def test_help_lists_transcribe_command() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "transcribe" in result.stdout


def test_transcribe_reports_not_implemented() -> None:
    result = runner.invoke(app, ["transcribe"])

    assert result.exit_code == 0
    assert "not implemented yet" in result.stdout
