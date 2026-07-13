# vito-transcript-cli

A small command-line application for sending audio files to the RTZR STT file
API, waiting for transcription to complete, and exporting the result.

> The API client and transcription workflow have not been implemented yet.

## Requirements

- Python 3.11 or newer

## Installation

Create and activate a virtual environment, then install the project and its
development tools:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and replace the placeholders with local
credentials. Never commit `.env`.

## Usage

```bash
vito-transcript --help
```

## Development

```bash
pytest
ruff check .
ruff format --check .
```

## Documentation

Project documentation lives in [`docs/`](docs/README.md).
