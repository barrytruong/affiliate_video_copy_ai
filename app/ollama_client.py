import requests

from app.errors import OllamaModelMissingError, OllamaNotRunningError


def check_ollama_health(base_url: str, model: str) -> None:
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise OllamaNotRunningError(str(e)) from e

    names = {m.get("name") for m in resp.json().get("models", [])}
    # Ollama tags can include or omit the ":latest" suffix depending on how the
    # model was pulled, so compare both the exact name and its base name.
    base_names = {n.split(":")[0] for n in names}
    if model not in names and model.split(":")[0] not in base_names:
        raise OllamaModelMissingError(model)


def chat(
    messages: list[dict],
    model: str,
    base_url: str,
    options: dict | None = None,
    timeout: int = 300,
) -> str:
    try:
        resp = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": options or {},
            },
            timeout=timeout,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise OllamaNotRunningError(str(e)) from e

    return resp.json()["message"]["content"]
