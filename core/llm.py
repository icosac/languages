import requests


class LLMServiceError(Exception):
    def __init__(self, message: str, *, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class BaseLLMProvider:
    name = "base"

    def generate(
        self,
        *,
        api_key: str,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict:
        raise NotImplementedError


class OpenAIProvider(BaseLLMProvider):
    name = "openai"

    def __init__(self, api_base: str = "https://api.openai.com/v1"):
        self.api_base = api_base.rstrip("/")

    def generate(
        self,
        *,
        api_key: str,
        messages: list[dict],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> dict:
        if not api_key:
            raise LLMServiceError("OpenAI API key is missing.", status_code=400)

        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=45,
            )
        except requests.RequestException as exc:
            raise LLMServiceError(f"OpenAI request failed: {exc}", status_code=502) from exc

        if response.status_code >= 400:
            error_payload = {}
            try:
                error_payload = response.json()
            except ValueError:
                pass
            message = (
                error_payload.get("error", {}).get("message")
                or response.text
                or "OpenAI returned an error."
            )
            raise LLMServiceError(message, status_code=502)

        try:
            payload = response.json()
            choice = (payload.get("choices") or [])[0]
            content = (choice.get("message") or {}).get("content", "")
        except (ValueError, IndexError, AttributeError, TypeError) as exc:
            raise LLMServiceError("Unexpected response format from OpenAI.", status_code=502) from exc

        return {
            "provider": self.name,
            "model": payload.get("model", model),
            "response": content,
            "usage": payload.get("usage", {}),
        }


def _provider_registry(api_base: str) -> dict[str, BaseLLMProvider]:
    return {
        "openai": OpenAIProvider(api_base=api_base),
    }


def generate_llm_response(
    *,
    provider: str,
    api_key: str,
    messages: list[dict],
    model: str,
    temperature: float,
    max_tokens: int,
    openai_api_base: str,
) -> dict:
    registry = _provider_registry(api_base=openai_api_base)
    provider_key = (provider or "").strip().lower()
    selected = registry.get(provider_key)

    if selected is None:
        supported = ", ".join(sorted(registry.keys()))
        raise LLMServiceError(
            f"Provider '{provider}' is not supported yet. Supported providers: {supported}.",
            status_code=400,
        )

    return selected.generate(
        api_key=api_key,
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )