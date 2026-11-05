"""Shared configuration and preflight checks for local Ollama workflows."""
import os

import requests


DEFAULT_MODEL = "koesn/llama3-8b-instruct:latest"
DEFAULT_EMBEDDING_MODEL = "snowflake-arctic-embed"


def ollama_config():
    base_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
    embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    return base_url, model, embedding_model


def ollama_preflight():
    """Return a user-facing error when Ollama or configured models are missing."""
    base_url, model, embedding_model = ollama_config()
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=3)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        return (f"Cannot reach Ollama at {base_url}. Start it with `ollama serve` "
                f"and check OLLAMA_API_URL. Details: {exc}")
    except ValueError:
        return f"Ollama at {base_url} returned an invalid model list."

    installed = {item.get("name", "") for item in payload.get("models", [])}
    installed.update(item.get("model", "") for item in payload.get("models", []))
    missing = [name for name in (model, embedding_model) if name not in installed]
    if missing:
        commands = " ".join(f"ollama pull {name}" for name in missing)
        return f"Ollama is running, but required model(s) are missing: {', '.join(missing)}. Install with: {commands}"
    return None
