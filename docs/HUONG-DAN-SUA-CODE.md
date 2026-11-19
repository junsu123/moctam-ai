# Hướng dẫn sửa code — Phòng Kinh doanh AI MỘC TÂM

Dành cho sếp (hoặc người sếp thuê) khi muốn tự sửa phần mềm, hoặc nhờ Claude sửa cho rẻ và đúng chỗ.
Đọc mục 1–3 một lần; khi cần sửa gì thì tra mục 4 (công thức theo việc).

---

## 1. Chuẩn bị máy để sửa

| Việc | Lệnh / cách làm |
|---|---|
| Lấy code | `git clone https://github.com/junsu123/moctam-ai` (hoặc `git pull` nếu đã có) |
| Python 3.10+ | `pip install -r requirements.txt -r dev/requirements-dev.txt` |
| Trình duyệt cho test | `python -m playwright install chromium` |
| Chạy phần mềm | Windows bấm `run.bat`, macOS / Linux `bash run.sh`, mở <http://localhost:8000> |
| Xem giao diện không cần chạy máy chủ | `dev/check.sh` rồi mở `dev/work/preview/index.html` (bản xem trước dữ liệu mẫu) |

Nên dùng VS Code (mở cả thư mục `moctam-ai`). Đang chạy phần mềm mà sửa code thì phần mềm **tự khởi động lại** khi các sale
rảnh và trang tự tải lại: không cần tắt bật tay.

**Quy tắc vàng:** sửa trên máy thử trước, chạy kiểm tra (mục 5), rồi mới `git push` lên `main`. Máy chạy thật lấy bản mới bằng
`git pull` (hoặc nhắn CEO trên Telegram “cập nhật phần mềm”).

---

## 2. Bản đồ code: cái gì nằm ở đâu

```
backend/                 Python (FastAPI + SQLite)
  main.py                Tạo app, tự khởi động lại khi có bản mới, trả giao diện (~500 dòng)
  routes/<nhóm>.py       Các API /api/... theo nhóm: posts, comments, sales, leads, website, trend_pages...
  db.py                  Bảng dữ liệu (SCHEMA), cột thêm sau (danh sách migration), CÀI ĐẶT MẶC ĐỊNH (DEFAULT_SETTINGS)
  scheduler.py           Lịch tự động: cứ 30 giây gọi xxx.tick(now) của từng tính năng
  agents.py              Hồ sơ agent (tên, vai trò, tính cách, ngoại hình 3D, bàn) + lời dặn (system_prompt)
  llm.py                 Gọi Claude: llm.json(system, prompt, mock=..., task=...)  (tự mô phỏng khi chưa có khóa)
  browser_poster.py      Sale điều khiển Chrome theo nick: đăng bài, bình luận, chuyển sang Trang...
  fb_selectors.json      CHỮ TRÊN NÚT FACEBOOK (sửa khi Facebook đổi giao diện, không cần biết code)
  fb_policy.py           Luật Facebook: giới hạn mỗi nick, kiểm tra bài, sự cố
  ceo_orders.py          CEO hiểu lệnh sếp: mẫu câu (_rule_plan), việc được làm (ACTIONS_DOC), thực hiện (execute)
  telegram_bot.py        Bot Telegram chính (báo cáo, khách, CEO)
  telegram_img.py        Bot Telegram riêng cho ảnh + việc của Nhi
  <tính năng>.py         Mỗi tính năng một file: post_care (up bài), comments, bump_watch, page_grow, trend_pages (Nhi tự học: trend_learn, tự tạo Trang: trend_create),
                         page_inbox, nick_health, replies, group_feed, friends, prospect, website...
frontend/                Giao diện (HTML + CSS + JS thuần, không cần build)
  app.html               Khuôn trang: các dòng @@include ghép file con lại
  css/0x-*.css           Kiểu dáng; 04-theme.css = màu, chữ chính; 08-polish.css = hiệu ứng, tìm nhanh
  views/<trang>.html     Phần HTML của từng trang (<section id="v-<trang>">); _shell.html = thanh bên
  js/pages/<trang>.js    Code của từng trang: loadXxx() lấy dữ liệu, renderXxx() vẽ
  js/router.js           Chuyển trang (show), js/api.js gọi máy chủ, js/ux.js tìm nhanh / thanh tải / tiết kiệm CPU
  js/world3d.js          Văn phòng 3D (Three.js), vị trí bàn (DESKS)
  js/demo/*.js           Dữ liệu giả cho bản xem trước (05-handle.js trả lời thay máy chủ)
dev/                     Kiểm tra: run.sh (chạy test), check.sh (cú pháp), perf.py (đo tốc độ), mockfb.py (Facebook giả)
data/                    DỮ LIỆU THẬT (company.db, hồ sơ Chrome các nick, ảnh) — không sửa tay, không đưa lên git
```

Tên trang trong giao diện ↔ file: Văn phòng `office`, Bài đăng `posts`, Bình luận `comments`, Nuôi Page `page`,
Trang xu hướng `trends`, Khách hàng `leads`, Tìm khách sỉ `prospects`, Nhân viên sale `sales`, Hội nhóm `groups`,
Kết bạn `friends`, Trả lời khách `replies`, Luật Facebook `fbrules`, Cài đặt `setup`.

**Tìm nhanh chỗ cần sửa:** tìm đúng chữ đang thấy trên màn hình trong cả thư mục (VS Code: Ctrl+Shift+F). Chữ hiện trên giao diện
nằm ở `frontend/views/` hoặc `frontend/js/pages/`; chữ báo lỗi / nhật ký nằm ở `backend/`.

---

## 3. Dữ liệu chạy thế nào (để sửa không vỡ)

1. **Giao diện** gọi `api("/xxx")` → **máy chủ** `backend/routes/*.py` (`@app.get("/api/xxx")`) → hàm trong file tính năng → **SQLite** qua
   `db.q(...)` (đọc nhiều dòng), `db.one(...)` (một dòng), `db.run(...)` (ghi).
2. **Cài đặt** đọc bằng `db.get_settings()["ten_cai_dat"]` (luôn là chữ, VD `"1"`), ghi bằng `db.set_setting(k, v)`. Có bộ nhớ đệm 5 giây,
   ghi qua `set_setting` là đọc lại ngay.
3. **Việc tự động** chạy trong `xxx.tick(now)` (scheduler gọi 30 giây một lần). Việc lâu (gọi Claude, mở web) cho chạy trong
   `threading.Thread(..., daemon=True)` để không làm chậm lịch.
4. **Việc trên Facebook** luôn đi qua hàng đợi của sale (`browser_poster.submit`) và ca làm việc theo nick; không mở Chrome ở chỗ khác.
5. **Nhật ký**: `db.log("tên_agent", "Hành động", "chi tiết")` → hiện ở Văn phòng, Telegram gom báo “việc vừa hoàn thành”.
6. **Lỗi cho sếp xem**: `errors.report("nhóm", "Tiêu đề", "chi tiết + cách sửa", screen="trang")` → màn Lỗi.

---

## 4. Công thức theo việc hay sửa

### 4.1. Đổi chữ, màu, cỡ chữ
- Chữ trên một trang: tìm chữ đó trong `frontend/views/<trang>.html` hoặc `frontend/js/pages/<trang>.js`, sửa, lưu, tải lại trang.
- Màu chủ đạo, phông chữ: biến ở đầu `frontend/css/01-layout.css` (`--accent`, `--honey`, `--side`...) và `css/04-theme.css`.
- Không sửa `dev/work/preview/index.html` (file ghép tự sinh, sẽ bị ghi đè).

### 4.2. Facebook đổi giao diện, sale báo “không tìm thấy nút …”
Không cần biết code: mở `backend/fb_selectors.json`, thêm đúng chữ đang thấy trên Facebook vào danh sách tương ứng
(VD nút Đăng → `post_button`, ô bình luận → `comment_box`, nút chuyển sang Trang → `page_switch`, trang tạo Trang của Nhi → `page_create_*`). Lỗi ở màn Lỗi thường ghi sẵn tên
các nút đang thấy. Lưu file là xong (phần mềm đọc lại ở lượt sau).

### 4.3. Thêm / đổi một cài đặt
1. `backend/db.py` → `DEFAULT_SETTINGS`: thêm `"ten_moi": "giá trị mặc định",` (kèm chú thích tiếng Việt).
2. Dùng: `db.get_settings().get("ten_moi", "mặc định")`.
3. Ô sửa trên giao diện: thêm `<input id="...">` trong view, đọc / ghi bằng `api("/settings","PUT",{ten_moi: giá_trị})` (API cài đặt
   nhận mọi khóa). Cho CEO đổi qua lời nói: thêm khóa vào `SETTINGS_OK` trong `ceo_orders.py`.

### 4.4. Thêm cột / bảng dữ liệu
- Bảng mới: thêm `CREATE TABLE IF NOT EXISTS ...` vào `SCHEMA` trong `db.py`.
- Cột mới cho bảng cũ: thêm `("bang", "cot", "KIEU")` vào danh sách migration trong `db.py` (máy đang chạy tự thêm cột khi khởi động).
- Bảng thuộc dữ liệu thử nghiệm: thêm vào `RESET_TABLES` để “Bắt đầu chạy thật” xóa đúng.
- Không bao giờ đổi tên / xóa cột cũ (máy thật đang có dữ liệu).

### 4.5. Thêm một trang mới trên giao diện (khuôn: trang Kết bạn)
1. `frontend/views/<ten>.html`: `<section class="view" id="v-<ten>" hidden> ... </section>`.
2. `frontend/js/pages/<ten>.js`: `async function loadTen(){ ST.ten=await api("/ten"); renderTen(); }` + `function renderTen(){...}`.
3. `frontend/app.html`: thêm `@@include views/<ten>.html` và `@@include js/pages/<ten>.js` cạnh các trang khác.
4. `frontend/views/_shell.html`: thêm nút `<button data-v="<ten>">…</button>` vào nhóm phù hợp (tự có trong Tìm nhanh Ctrl K).
5. `frontend/js/router.js`: thêm `if(v==="<ten>") loadTen();` vào `show()`.
6. Bản xem trước: thêm `demoTen()` ở `js/demo/03-features.js` và một dòng `if(P.startsWith("/ten")) return demoTen(...)` ở `05-handle.js`.
Luôn dùng `esc(...)` khi đưa chữ của người dùng / Facebook vào HTML.

### 4.6. Thêm API
Tạo hoặc mở `backend/routes/<nhóm>.py` (file chạy chung không gian tên với `main.py`: dùng sẵn `app`, `db`, `HTTPException`, `BaseModel`):
```python
@app.get("/api/ten")
def ten_get():
    import ten_tinh_nang
    return ten_tinh_nang.overview()
```
File mới thì thêm tên vào `ROUTES` trong `backend/main.py`. Lỗi muốn báo sếp bằng chữ: `raise HTTPException(400, "Câu dễ hiểu")`.

### 4.7. Thêm việc chạy theo lịch
Trong file tính năng viết `def tick(now): ...` (kiểm tra giờ + cờ “đã làm hôm nay” bằng `db.set_setting`), rồi thêm 2 dòng
`import x` / `x.tick(now)` vào `_tick()` của `scheduler.py`. Việc nặng: chạy trong thread như mục 3.3.

### 4.8. Sửa cách agent viết / nói (prompt)
- Tính cách, vai trò: `backend/agents.py` (mục của agent đó).
- Lời dặn chung mọi lần làm việc: `system_prompt()` trong `agents.py`.
- Đề bài từng việc: tìm `llm.json(` trong file tính năng (VD viết bài nhóm `workflows.py`, bài Trang `page_grow.py`,
  bài Trang xu hướng `trend_pages.py`, câu up bài `post_care.py`). Sửa phần chữ trong đề bài; giữ nguyên dòng “Trả về JSON …”.
- Cách nhanh hơn không cần sửa code: nhắn CEO “Từ nay …” (chỉ đạo lâu dài) hoặc “Lan viết dài quá …” (bài học ghim).

### 4.9. Thêm lệnh cho CEO hiểu
`backend/ceo_orders.py`: thêm dòng mô tả vào `ACTIONS_DOC`, mẫu câu (regex) vào `_rule_plan`, và nhánh `if t == "ten_viec":` trong `execute()`.
Muốn CEO gọi đúng người lên phòng nhận việc đó: thêm `"ten_viec": ["lan"]` vào `WHO` (cùng file). Cảnh đi sang bàn CEO ở
`summon()` (`js/world3d.js`), nhận tín hiệu từ nhật ký “Lên phòng CEO nhận việc” trong `officeVisits` (`js/pages/office.js`).

### 4.10. Thêm agent mới (khuôn: Nhi)
Phòng ban ở `backend/departments.py`: agent thuộc phòng nào (`DEPTS[...]["core"]`), cách nghĩ của trưởng phòng (`MINDSET`), vị trí tuyển
được (`POSITIONS` + luật thiếu người ở `need()`), bàn cho nhân viên tuyển thêm (`DESKS`, khớp `DESKS` trong `js/world3d.js`). Vị trí mới
cần chỗ dùng thật trong code (VD `departments.count("seo_writer")` ở `website.tick`).
`agents.py` (mục mới + `ORDER`), các danh sách `CORE` / `STATUS` (`workflows.py`, `learning.py`, `growth.py`), `knowledge.py`
(`ROLE_NAME`, giáo trình, `STUDY_AGENTS`), `ceo_orders.py` (`AGENT_ALIASES`, mô tả), `fb_policy.py` (`TEACH`); giao diện: bàn trong
`DESKS` (`js/world3d.js`), danh sách agent mẫu `js/demo/01-state.js`, tên ở `js/pages/ceo.js`.

### 4.11. Thêm chữ cho Telegram
Tin gửi: `telegram_bot.send(text)` (bot chính) hoặc `telegram_img.send(text)` (bot ảnh). Chữ dạng HTML: bọc dữ liệu bằng `e(...)`.
Lệnh mới: thêm nhánh trong `handle_message`.

---

## 5. Kiểm tra trước khi đưa lên

| Lệnh | Khi nào | Mất |
|---|---|---|
| `dev/check.sh` | Mọi lần sửa (cú pháp Python 3.10 + JS, ghép giao diện) | vài giây |
| `dev/run.sh <ten>_test` | Sửa một tính năng: chạy test của tính năng đó | 3 giây – 3 phút |
| `dev/run.sh quick` | Trước khi push (các test không mở Chrome) | ~1–2 phút |
| `dev/run.sh` | Sửa phần dùng chung: `db.py`, `browser_poster.py`, `ceo_orders.py`, `scheduler.py` | ~25 phút |
| `python3 dev/perf.py` | Nghi phần mềm chậm / tốn CPU | ~1 phút |

Mỗi test in một dòng; cuối in `TỔNG: n/m đạt`. Test hỏng thì in vài dòng lỗi, log đầy đủ ở `dev/work/out_<test>.log`.
Đẩy lên `main` thì GitHub tự chạy `check` + `quick` (tab **Actions**, dấu ✓ / ✗ cạnh commit, hỏng thì GitHub gửi mail).
Tính năng mới nên có một file `dev/<ten>_test.py` (khuôn `dev/trendpages_test.py`: hàm `chk`, cuối in `XONG a/b`), thêm tên vào `ALL` (và `QUICK` nếu
không mở Chrome) trong `dev/run.sh`.

---

## 6. Giữ phần mềm nhẹ (đỡ tốn CPU)

- **Không gọi việc nặng trong `tick`**: tick chạy 30 giây / lần; kiểm tra “đã làm hôm nay chưa” trước, việc lâu cho vào thread.
- **Không hỏi SQLite trong vòng lặp** từng dòng: gom bằng một câu `SELECT ... WHERE id IN (...)` hoặc `JOIN`.
  Cột hay lọc thì thêm chỉ mục (`CREATE INDEX IF NOT EXISTS`) trong `SCHEMA`.
- **Giao diện tự cập nhật**: dùng `setInterval` có `if(UX.idle()) return;` (dừng khi cửa sổ thu nhỏ) và chỉ tải khi đang ở đúng trang
  (`ST.view==="<ten>"`). Đừng đặt dưới 3 giây.
- **Văn phòng 3D** chỉ vẽ khi trang Văn phòng / Phòng họp đang mở: ~30 hình/giây khi có người đi lại, nói, hoặc sếp đang xoay;
  ~10 hình/giây khi mọi người ngồi làm việc. Thêm vật thể 3D thì dùng chung vật liệu, tránh thêm đèn đổ bóng.
- Đo trước và sau khi sửa bằng `python3 dev/perf.py` (dữ liệu giả 1 năm, 25 nick).

---

## 7. Nhờ Claude sửa cho rẻ

- Mở **phiên mới** cho mỗi ý tưởng lớn (phiên dài đọc lại cả lịch sử mỗi lượt, rất tốn). Claude tự đọc `CLAUDE.md` (bản đồ code + quy
  tắc tiết kiệm) trước khi làm.
- Nói rõ **trang nào, nút / chữ nào, muốn thành gì**, kèm ảnh chụp nếu là giao diện. VD: “Trang Bình luận, thẻ ‘Bình luận có ích không’:
  thêm cột số khách theo nhóm”.
- Nói rõ điều không được làm (đã chốt trong `CLAUDE.md`: không né phát hiện của Facebook, không tự gửi kết bạn, không bình luận 24/24).
- Xong việc Claude tự: chạy test, cập nhật README, commit, push, cập nhật bản xem trước và tài liệu trong Project.

---

## 8. Gỡ rối nhanh

| Hiện tượng | Xem ở đâu |
|---|---|
| Nút trên phần mềm báo lỗi | Màn **Lỗi** (có chi tiết kỹ thuật, nút Sao chép gửi người sửa) |
| Sale không đăng / không bình luận được | Màn Lỗi (có ảnh chụp), sửa `fb_selectors.json` (mục 4.2) |
| Trang trắng / không bấm được | Mở công cụ trình duyệt (F12) → Console xem lỗi JS; chạy `dev/check.sh` |
| Phần mềm không lên sau khi sửa | Xem cửa sổ đen của `run.bat`: dòng lỗi cuối cùng là file / dòng code hỏng |
| Muốn quay lại bản trước | `git log --oneline` tìm bản tốt → `git revert <mã>` (an toàn, giữ lịch sử) rồi push |
| Lỡ hỏng dữ liệu | Bản sao lưu ở `data/backups/` (xem README → Bắt đầu chạy thật) |
