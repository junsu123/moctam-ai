"""Kết nối Claude, có tối ưu chi phí.

- Mỗi loại việc dùng mô hình riêng (Cài đặt): viết bài, tin nhắn khách, cuộc họp.
- Ghi số token và tiền của từng lần gọi vào bảng `usage` để theo dõi chi phí thật.
- Ngân sách tháng: chạm 100% -> mọi việc tự chuyển sang Haiku (rẻ nhất);
  chạm 120% -> ngừng gọi AI, dùng nội dung mẫu cho tới tháng sau hoặc khi sếp nâng ngân sách.
- Viết bài hằng ngày gửi theo lô (Message Batches API) được giảm 50%.
Không có API key -> chạy chế độ mô phỏng, không tốn tiền.
"""
import json
import os
import re
from datetime import datetime

from dotenv import load_dotenv

import db

load_dotenv()

try:
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None

HAIKU, SONNET, OPUS = "claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"
DEFAULT_MODEL = os.getenv("CLAUDE_MODEL", SONNET)
MODEL = DEFAULT_MODEL  # giữ tên cũ cho phần hiển thị

# USD / 1 triệu token (bảng giá Claude Platform, 11/2026). Haiku 5.5: giá cho prompt ≤ 100K token.
PRICES = {
    HAIKU: (0.10, 0.50),
    SONNET: (2.00, 10.00),
    OPUS: (4.00, 20.00),
}
BATCH_DISCOUNT = 0.5
TASKS = {"posts": "Viết bài đăng", "replies": "Tin nhắn khách", "meeting": "Cuộc họp", "learning": "Tự học mỗi đêm", "images": "Tạo ảnh", "ceo": "CEO hiểu lệnh sếp", "knowledge": "Học kiến thức, hỏi khi chưa biết", "other": "Khác"}

PRESETS = {  # gói cấu hình sẵn trong Cài đặt
    "tiet_kiem": {"model_posts": HAIKU, "model_replies": HAIKU, "model_meeting": HAIKU, "model_learning": HAIKU, "model_ceo": HAIKU, "model_knowledge": HAIKU, "use_batch": "1"},
    "can_bang": {"model_posts": SONNET, "model_replies": HAIKU, "model_meeting": HAIKU, "model_learning": HAIKU, "model_ceo": HAIKU, "model_knowledge": HAIKU, "use_batch": "1"},
    "chat_luong": {"model_posts": SONNET, "model_replies": SONNET, "model_meeting": SONNET, "model_learning": HAIKU, "model_ceo": SONNET, "model_knowledge": HAIKU, "use_batch": "1"},
}


def price_of(model: str) -> tuple[float, float]:
    return PRICES.get(model, PRICES[SONNET])


def cost_usd(model: str, tin: int, tout: int, batch: bool = False) -> float:
    pi, po = price_of(model)
    c = (tin * pi + tout * po) / 1_000_000
    return c * BATCH_DISCOUNT if batch else c


def record(task: str, model: str, usage, batch: bool = False):
    if not usage:
        return
    tin = (getattr(usage, "input_tokens", 0) or 0) + (getattr(usage, "cache_read_input_tokens", 0) or 0) \
        + (getattr(usage, "cache_creation_input_tokens", 0) or 0)
    tout = getattr(usage, "output_tokens", 0) or 0
    db.run("""INSERT INTO usage(task, model, input_tokens, output_tokens, cost_usd, batch, created_at)
              VALUES (?,?,?,?,?,?,?)""", (task, model, tin, tout, cost_usd(model, tin, tout, batch), int(batch), db.now()))


def month_spent() -> float:
    r = db.one("SELECT COALESCE(SUM(cost_usd),0) c FROM usage WHERE created_at LIKE ?", (db.clock().strftime("%Y-%m") + "%",))
    return float(r["c"])


def budget_state() -> str:
    try:
        import company
        if company.active() and company.finance()["capital"] and company.capital_left() <= 0:
            return "stop"  # hết vốn công ty
    except Exception as e:
        print("[llm] company", e)
    budget = float(db.get_settings().get("monthly_budget_usd") or 0)
    if budget <= 0:
        return "ok"
    spent = month_spent()
    if spent >= budget * 1.2:
        return "stop"
    if spent >= budget:
        return "economy"
    return "ok"


def model_for(task: str) -> str:
    s = db.get_settings()
    m = s.get(f"model_{task}") or DEFAULT_MODEL
    return HAIKU if budget_state() == "economy" else m


def mask_key(k: str) -> str:
    k = (k or "").strip()
    return f"{k[:10]}…{k[-4:]}" if len(k) > 18 else ("••••" if k else "")


def check_key(key: str) -> dict:
    """Kiểm tra khóa API: còn hiệu lực không, tài khoản còn tín dụng không (tốn ~0,00001 USD)."""
    if not anthropic:
        return {"ok": False, "error": "Thiếu thư viện anthropic. Chạy lại run.bat để cài."}
    key = (key or "").strip()
    if not key.startswith("sk-ant-"):
        return {"ok": False, "error": "Khóa không đúng định dạng. Khóa Claude bắt đầu bằng sk-ant-"}
    c = anthropic.Anthropic(api_key=key, max_retries=0, timeout=25)
    try:
        c.messages.create(model=HAIKU, max_tokens=1, messages=[{"role": "user", "content": "ok"}])
        return {"ok": True}
    except anthropic.AuthenticationError:
        return {"ok": False, "error": "Khóa không hợp lệ hoặc đã bị xóa. Tạo khóa mới tại console.anthropic.com → API Keys."}
    except anthropic.PermissionDeniedError:
        return {"ok": False, "error": "Khóa không có quyền dùng mô hình này. Kiểm tra workspace của khóa trong Anthropic Console."}
    except anthropic.RateLimitError:
        return {"ok": True, "warning": "Khóa hợp lệ nhưng đang bị giới hạn tốc độ, thử lại sau ít phút."}
    except anthropic.BadRequestError as e:
        msg = str(e)
        if "credit" in msg.lower() or "balance" in msg.lower():
            return {"ok": False, "error": "Khóa hợp lệ nhưng tài khoản hết tín dụng. Nạp tiền tại console.anthropic.com → Billing."}
        return {"ok": False, "error": f"Anthropic từ chối yêu cầu: {msg[:200]}"}
    except anthropic.APIConnectionError:
        return {"ok": False, "error": "Không kết nối được tới Anthropic. Kiểm tra Internet hoặc tường lửa của máy."}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


class LLM:
    def __init__(self):
        self.client = None
        self.source = None
        self.reload(use_db=False)

    def current_key(self, use_db: bool = True) -> tuple[str, str | None]:
        """Ưu tiên khóa nhập trong phần mềm, sau đó tới file .env."""
        if use_db:
            try:
                k = (db.get_settings().get("anthropic_api_key") or "").strip()
                if k:
                    return k, "app"
            except Exception:
                pass
        k = os.getenv("ANTHROPIC_API_KEY", "").strip()
        return (k, "env") if k else ("", None)

    def reload(self, use_db: bool = True):
        key, src = self.current_key(use_db)
        self.client = anthropic.Anthropic(api_key=key) if key and anthropic else None
        self.source = src if self.client else None

    @property
    def live(self) -> bool:
        return self.client is not None

    def _mock(self, mock):
        return mock() if callable(mock) else mock

    def chat(self, system: str, prompt: str, mock=None, max_tokens: int = 600, task: str = "other") -> str:
        if not self.client:
            return self._mock(mock) or ""
        if budget_state() == "stop":
            db.log("khoa", "Ngân sách AI", "Đã vượt 120% ngân sách tháng, tạm dùng nội dung mẫu")
            return self._mock(mock) or ""
        model = model_for(task)
        try:
            resp = self.client.messages.create(
                model=model, max_tokens=max_tokens, system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            record(task, model, resp.usage)
            return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        except Exception as e:  # lỗi mạng/khóa -> vẫn chạy bằng mô phỏng
            print(f"[LLM] lỗi: {e}")
            import errors
            errors.report("ai", f"Gọi AI Claude bị lỗi ({TASKS.get(task, task)})",
                          str(e)[:500] + " — tạm dùng nội dung mô phỏng", screen="setup")
            note_fallback(task, "error", str(e)[:300], report=False)
            return self._mock(mock) if mock is not None else f"(Lỗi gọi AI: {e})"

    def json(self, system: str, prompt: str, mock=None, max_tokens: int = 1200, task: str = "other"):
        """Claude trả kết quả qua công cụ tra_ket_qua (khuôn cố định) nên không còn lỗi đọc JSON.
        Bị cắt vì hết độ dài thì thử lại 1 lần với gấp đôi độ dài. Vẫn hỏng thì ghi lại (ai_fallback + màn Lỗi)
        rồi mới dùng nội dung mẫu, để sếp biết bài nào không phải Claude viết."""
        if not self.client or budget_state() == "stop":
            return self._mock(mock)
        model = model_for(task)
        reason, tokens = "", max_tokens
        for attempt in range(2):
            try:
                resp = self.client.messages.create(
                    model=model, max_tokens=tokens, system=system, tools=[RESULT_TOOL],
                    tool_choice={"type": "tool", "name": RESULT_TOOL["name"]},
                    messages=[{"role": "user", "content": prompt + JSON_HINT}])
            except Exception as e:
                print(f"[LLM] lỗi: {e}")
                import errors
                errors.report("ai", f"Gọi AI Claude bị lỗi ({TASKS.get(task, task)})",
                              str(e)[:500] + " — tạm dùng nội dung mô phỏng", screen="setup")
                note_fallback(task, "error", str(e)[:300], report=False)
                return self._mock(mock)
            record(task, model, resp.usage)
            data = result_of(resp)
            if data is not None and getattr(resp, "stop_reason", "") != "max_tokens":
                return data
            reason = "cut" if getattr(resp, "stop_reason", "") == "max_tokens" else "bad_json"
            if reason == "cut" and attempt == 0:
                tokens = min(tokens * 2, MAX_RETRY_TOKENS)
                continue
            if data is not None:  # bị cắt nhưng vẫn đọc được: dùng, không bỏ phí lượt gọi
                return data
            break
        note_fallback(task, reason, f"max_tokens={tokens}")
        return self._mock(mock)

    # ------------------------------------------------ Batch API (giảm 50%, trả kết quả trong vòng vài phút đến 24 giờ)
    def batch_create(self, task: str, items: list[dict], max_tokens: int = 1200) -> str | None:
        """items: [{custom_id, system, prompt}] -> id lô, hoặc None nếu không gửi được."""
        if not self.client or budget_state() == "stop" or not items:
            return None
        model = model_for(task)
        try:
            b = self.client.messages.batches.create(requests=[{
                "custom_id": it["custom_id"],
                "params": {"model": model, "max_tokens": max_tokens, "system": it["system"], "tools": [RESULT_TOOL],
                           "tool_choice": {"type": "tool", "name": RESULT_TOOL["name"]},
                           "messages": [{"role": "user", "content": it["prompt"] + JSON_HINT}]},
            } for it in items])
            return b.id
        except Exception as e:
            print(f"[LLM] không tạo được lô: {e}")
            import errors
            errors.report("ai", "Không gửi được lô viết bài cho AI Claude", str(e)[:500], screen="setup")
            return None

    def batch_status(self, batch_id: str) -> str:
        return self.client.messages.batches.retrieve(batch_id).processing_status  # in_progress | canceling | ended

    def batch_results(self, batch_id: str, task: str) -> dict[str, str | None]:
        out = {}
        for r in self.client.messages.batches.results(batch_id):
            if r.result.type == "succeeded":
                msg = r.result.message
                record(task, msg.model, msg.usage, batch=True)
                data = result_of(msg)
                if data is None:
                    note_fallback(task, "cut" if getattr(msg, "stop_reason", "") == "max_tokens" else "bad_json", "lô")
                out[r.custom_id] = json.dumps(data, ensure_ascii=False) if data is not None else None
            else:
                note_fallback(task, "error", f"lô: {r.result.type}")
                out[r.custom_id] = None
        return out


JSON_HINT = ("\n\nTrả kết quả bằng công cụ tra_ket_qua: đặt đúng JSON theo khuôn yêu cầu ở trên (object hoặc mảng) "
             "vào trường ket_qua, không giải thích thêm.")
RESULT_TOOL = {
    "name": "tra_ket_qua",
    "description": "Trả kết quả công việc dưới dạng JSON đúng khuôn mà yêu cầu đã nêu.",
    "input_schema": {"type": "object", "properties": {"ket_qua": {
        "description": "Kết quả JSON (object hoặc mảng) đúng khuôn yêu cầu"}}, "required": ["ket_qua"]},
}
MAX_RETRY_TOKENS = 8000
FALLBACK_REASONS = {"cut": "Claude viết quá dài nên bị cắt giữa chừng", "bad_json": "Claude trả kết quả sai khuôn",
                    "error": "Gọi Claude bị lỗi (mạng, khóa, tín dụng)"}


def result_of(resp):
    """Lấy kết quả từ công cụ tra_ket_qua; phòng khi Claude trả chữ thường thì đọc JSON trong chữ."""
    text = ""
    for b in getattr(resp, "content", None) or []:
        t = getattr(b, "type", "")
        if t == "tool_use":
            inp = getattr(b, "input", None) or {}
            v = inp.get("ket_qua") if isinstance(inp, dict) and "ket_qua" in inp else inp
            if isinstance(v, str):
                v = parse_json(v)
            if isinstance(v, (dict, list)) and v != {}:
                return v
        elif t == "text":
            text += getattr(b, "text", "") or ""
    return parse_json(text) if text.strip() else None


def note_fallback(task: str, reason: str, detail: str = "", report: bool = True):
    """Ghi một lần phải dùng nội dung mẫu thay cho Claude (đếm ở Cài đặt → Chi phí AI)."""
    try:
        db.run("INSERT INTO ai_fallback(task, reason, detail, created_at) VALUES (?,?,?,?)",
               (task, reason, (detail or "")[:300], db.now()))
    except Exception as e:
        print("[llm] fallback", e)
    print(f"[LLM] dùng nội dung mẫu ({task}): {reason}")
    if report:
        import errors
        errors.report("ai", f"Claude trả kết quả hỏng, đã dùng nội dung mẫu ({TASKS.get(task, task)})",
                      FALLBACK_REASONS.get(reason, reason), detail, screen="setup")


def fallback_stats(days: int = 30) -> dict:
    """Số lần phải dùng nội dung mẫu / tổng lượt gọi Claude trong N ngày, chia theo việc."""
    from datetime import timedelta
    since = (db.clock() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = db.q("SELECT task, reason, COUNT(*) n FROM ai_fallback WHERE created_at>=? GROUP BY task, reason", (since,))
    calls = {r["task"]: r["n"] for r in db.q("SELECT task, COUNT(*) n FROM usage WHERE created_at>=? GROUP BY task", (since,))}
    by = {}
    for r in rows:
        t = by.setdefault(r["task"], {"task": r["task"], "label": TASKS.get(r["task"], r["task"]), "n": 0, "reasons": {}})
        t["n"] += r["n"]
        t["reasons"][FALLBACK_REASONS.get(r["reason"], r["reason"])] = r["n"]
    for t in by.values():
        t["calls"] = calls.get(t["task"], 0)
    total = sum(t["n"] for t in by.values())
    return {"days": days, "total": total, "calls": sum(calls.values()),
            "by_task": sorted(by.values(), key=lambda t: -t["n"])}


def parse_json(text: str):
    if not text:
        return None
    text = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text.strip())
    try:
        return json.loads(text)
    except Exception:
        pass
    dec = json.JSONDecoder()  # bỏ chữ thừa trước / sau: đọc khối JSON đầu tiên hợp lệ
    for i, ch in enumerate(text):
        if ch in "[{":
            try:
                return dec.raw_decode(text[i:])[0]
            except Exception:
                continue
    print("[LLM] không đọc được JSON")
    return None


llm = LLM()
