"""llm.json: Claude trả kết quả qua công cụ tra_ket_qua; bị cắt thì thử lại; hỏng thì ghi lại rồi mới dùng nội dung mẫu."""
import os, sys
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
SP = Path(os.environ.get("MT_WORK") or Path(__file__).resolve().parent / "work"); SP.mkdir(exist_ok=True)
import db
db.DB_PATH = SP / "llm.db"; db.DB_PATH.unlink(missing_ok=True); db.init()
import llm as L

U = NS(input_tokens=100, output_tokens=50)
tool = lambda v: NS(type="tool_use", input={"ket_qua": v})
text = lambda t: NS(type="text", text=t)


class Fake:
    def __init__(self): self.queue, self.calls = [], []
    def create(self, **kw):
        self.calls.append(kw); r = self.queue.pop(0)
        if isinstance(r, Exception): raise r
        content, stop = r
        return NS(content=content, stop_reason=stop, usage=U)


f = Fake(); L.llm.client = NS(messages=f)
mock = {"content": "BÀI MẪU"}
ok = []
def check(name, cond): ok.append(cond); print(("OK  " if cond else "LỖI ") + name)

f.queue = [([tool({"content": "bài Claude"})], "tool_use")]
r = L.llm.json("sys", "viết", mock=mock, task="posts")
check("trả qua công cụ", r == {"content": "bài Claude"} and f.calls[-1]["tool_choice"]["name"] == "tra_ket_qua")

f.queue = [([tool('{"content": "chuỗi"}')], "tool_use")]
check("ket_qua là chuỗi JSON", L.llm.json("s", "p", mock=mock, task="posts") == {"content": "chuỗi"})

f.queue = [([tool([{"a": 1}, {"a": 2}])], "tool_use")]
check("kết quả là mảng", L.llm.json("s", "p", mock=mock, task="posts") == [{"a": 1}, {"a": 2}])

f.queue = [([text('Đây:\n```json\n{"content": "chữ"}\n```')], "end_turn")]
check("trả chữ có ```json vẫn đọc được", L.llm.json("s", "p", mock=mock, task="posts") == {"content": "chữ"})

n0 = len(f.calls)
f.queue = [([NS(type="tool_use", input={})], "max_tokens"), ([tool({"content": "đủ"})], "tool_use")]
r = L.llm.json("s", "p", mock=mock, max_tokens=900, task="posts")
check("bị cắt -> thử lại gấp đôi độ dài", r == {"content": "đủ"} and len(f.calls) - n0 == 2 and f.calls[-1]["max_tokens"] == 1800)

f.queue = [([NS(type="tool_use", input={})], "max_tokens"), ([NS(type="tool_use", input={})], "max_tokens")]
check("cắt 2 lần -> dùng mẫu", L.llm.json("s", "p", mock=mock, task="posts") == mock)

f.queue = [([text("xin lỗi, tôi không làm được")], "end_turn")]
check("sai khuôn -> dùng mẫu", L.llm.json("s", "p", mock=mock, task="replies") == mock)

f.queue = [RuntimeError("mạng rớt")]
check("lỗi mạng -> dùng mẫu", L.llm.json("s", "p", mock=mock, task="ceo") == mock)

st = L.fallback_stats(30)
by = {t["task"]: t for t in st["by_task"]}
check(f"đếm dùng mẫu: {st['total']} lần / {st['calls']} lượt",
      st["total"] == 3 and by["posts"]["n"] == 1 and by["replies"]["n"] == 1 and by["ceo"]["n"] == 1)
err = db.q("SELECT title, count FROM errors WHERE source='ai'")
check("màn Lỗi có ghi", any("nội dung mẫu" in e["title"] for e in err))

# không có khóa: chạy mô phỏng, không tính là lỗi
L.llm.client = None
check("không khóa: mô phỏng, không đếm", L.llm.json("s", "p", mock=mock) == mock and L.fallback_stats()["total"] == 3)

# theo lô
res = [NS(custom_id="a", result=NS(type="succeeded", message=NS(model=L.SONNET, usage=U, stop_reason="tool_use", content=[tool({"content": "lô"})]))),
       NS(custom_id="b", result=NS(type="succeeded", message=NS(model=L.SONNET, usage=U, stop_reason="max_tokens", content=[NS(type="tool_use", input={})]))),
       NS(custom_id="c", result=NS(type="errored"))]
L.llm.client = NS(messages=NS(batches=NS(results=lambda bid: res)))
out = L.llm.batch_results("x", "posts")
check("lô: đọc kết quả công cụ", L.parse_json(out["a"]) == {"content": "lô"} and out["b"] is None and out["c"] is None
      and L.fallback_stats()["total"] == 5)

print(("XONG" if all(ok) else "CÓ LỖI") + f" {sum(ok)}/{len(ok)}")
