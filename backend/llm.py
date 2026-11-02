"""Kết nối mô hình ngôn ngữ (Claude). Không có API key -> chạy chế độ mô phỏng."""
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

try:
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None


class LLM:
    def __init__(self):
        self.client = None
        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if key and anthropic:
            self.client = anthropic.Anthropic(api_key=key)

    @property
    def live(self) -> bool:
        return self.client is not None

    def chat(self, system: str, prompt: str, mock=None, max_tokens: int = 900) -> str:
        if not self.client:
            return mock() if callable(mock) else (mock or "")
        try:
            resp = self.client.messages.create(
                model=MODEL, max_tokens=max_tokens, system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        except Exception as e:  # lỗi mạng/khóa -> vẫn chạy bằng mô phỏng
            print(f"[LLM] lỗi: {e}")
            return mock() if callable(mock) else (mock or f"(Lỗi gọi AI: {e})")

    def json(self, system: str, prompt: str, mock=None, max_tokens: int = 2000):
        if not self.client:
            return mock() if callable(mock) else mock
        text = self.chat(system, prompt + "\n\nChỉ trả về JSON hợp lệ, không giải thích, không markdown.",
                         mock=None, max_tokens=max_tokens)
        m = re.search(r"(\[.*\]|\{.*\})", text, re.S)
        try:
            return json.loads(m.group(1) if m else text)
        except Exception:
            print("[LLM] không đọc được JSON, dùng mô phỏng")
            return mock() if callable(mock) else mock


llm = LLM()
