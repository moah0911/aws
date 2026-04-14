from __future__ import annotations

import os
from typing import Protocol


class LocalModelClient(Protocol):
    def generate(self, prompt: str, system_prompt: str | None = None) -> str: ...


class PyTorchLocalModelClient:
    """Local model client using PyTorch + Transformers.

    This client downloads (once) and caches the model locally, then runs generation
    fully on local hardware (CPU/GPU) without requiring Ollama.
    """

    def __init__(
        self,
        model_id: str | None = None,
        cache_dir: str | None = None,
        max_new_tokens: int | None = None,
        temperature: float | None = None,
    ) -> None:
        self.model_id = model_id or os.getenv("VOOC_TORCH_MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct")
        self.cache_dir = cache_dir or os.getenv("VOOC_MODEL_CACHE_DIR", os.path.expanduser("~/.cache/vooc"))
        self.max_new_tokens = max_new_tokens or int(os.getenv("VOOC_MAX_NEW_TOKENS", "220"))
        self.temperature = temperature if temperature is not None else float(os.getenv("VOOC_TEMPERATURE", "0.7"))

        self._loaded = False
        self._torch = None
        self._tokenizer = None
        self._model = None

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        if not prompt.strip():
            raise ValueError("Prompt must not be empty")

        self._ensure_loaded()

        messages = [
            {"role": "system", "content": system_prompt or "You are a concise enterprise content assistant."},
            {"role": "user", "content": prompt},
        ]

        if hasattr(self._tokenizer, "apply_chat_template"):
            formatted = self._tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            formatted = f"System: {messages[0]['content']}\nUser: {messages[1]['content']}\nAssistant:"

        inputs = self._tokenizer(formatted, return_tensors="pt")
        device = "cuda" if self._torch.cuda.is_available() else "cpu"
        inputs = {k: v.to(device) for k, v in inputs.items()}
        self._model.to(device)

        with self._torch.no_grad():
            output_ids = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=True,
                temperature=self.temperature,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        generated = output_ids[0][inputs["input_ids"].shape[1] :]
        text = self._tokenizer.decode(generated, skip_special_tokens=True).strip()
        if not text:
            raise RuntimeError("PyTorch local model returned empty output")
        return text

    def preload_model(self) -> str:
        """Download/cache model locally for offline usage."""
        self._ensure_loaded()
        return f"Model ready locally: {self.model_id} (cache: {self.cache_dir})"

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return

        try:
            import torch  # type: ignore
            from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "PyTorch local model backend requires 'torch' and 'transformers'. "
                "Install them and retry."
            ) from exc

        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_id, cache_dir=self.cache_dir)
        self._model = AutoModelForCausalLM.from_pretrained(self.model_id, cache_dir=self.cache_dir)
        self._loaded = True


class FallbackLocalModelClient:
    def generate(self, prompt: str, system_prompt: str | None = None) -> str:  # noqa: ARG002
        subject = _extract_field(prompt, "Prompt") or "the requested topic"
        tone = _extract_field(prompt, "Tone") or "balanced"
        platform = _extract_field(prompt, "Target platform") or "generic"

        return "\n".join(
            [
                f"Hook: Why {subject} matters right now for {platform} creators.",
                f"Development: In a {tone} tone, explain one challenge, one insight, and one execution framework teams can apply this week.",
                "Resolution: End with a measurable next step and a call-to-action for audience feedback.",
            ]
        )


def _extract_field(prompt: str, key: str) -> str | None:
    prefix = f"{key.lower()}:"
    for line in prompt.splitlines():
        if line.lower().startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None
