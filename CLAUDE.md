# Phòng Kinh doanh AI — MỘC TÂM (ghi chú cho Claude khi code)

Trả lời sếp bằng tiếng Việt, ngắn. Sếp trả tiền theo lượt dùng Claude: **mỗi ý tưởng mới làm gọn, tiết kiệm token**.

## Bản đồ code (đừng đọc cả file lớn để tìm)
- `backend/` FastAPI + SQLite, Python 3.10. `main.py` (3.2k dòng) = mọi endpoint `/api/...`; `db.py` = bảng + cài đặt mặc định (`DEFAULT_SETTINGS`), bảng ở `SCHEMA` + migration.
- `browser_poster.py` (1.8k) = Chrome theo nick (Playwright), hàng đợi việc mỗi sale `submit(sale_id, {"kind":...})`, `_worker` chia việc theo `kind`,
  `due_work`/`_job_session` = ca làm việc, `_send_comment(page, text, img)` gửi bình luận.
- Agent: `agents.py` (danh sách), CEO nhận lệnh `ceo_orders.py` (`_rule_plan` regex + `execute` theo `type`, mô tả việc ở `ACTIONS_DOC`, cài đặt CEO được đổi ở `SETTINGS_OK`),
  lịch `scheduler.py` (gọi `xxx.tick(now)`), luật FB `fb_policy.py` (RULES, limits, allow), gọi Claude `llm.py` (`llm.json(system, prompt, task=)`).
- Tính năng: đăng bài `workflows.py`; up bài + Bảo học viết `post_care.py`; trả lời khách `replies.py`; kết bạn `friends.py`; nơi đăng `group_target.py`;
  nhóm `group_finder.py`/`my_groups.py`/`group_review.py`; tìm khách `prospect.py`; website `website.py`; data rác `junk.py`.
- `frontend/index.html` (4.5k dòng, 1 file): CSS đầu file, nav `data-v=`, mỗi trang `<section id="v-xxx">`, JS `loadXxx/renderXxx`,
  bản xem trước giả lập trong `handle()` + `demoXxx()`. Đổi giao diện = thêm CSS/section/JS theo khuôn trang Kết bạn (`fr-*`).

## Cách làm tiết kiệm token (bắt buộc)
1. Tìm bằng `grep -n` rồi đọc đúng đoạn (`sed -n a,bp`), không Read cả file lớn. Không đọc lại file vừa sửa.
2. Sửa nhiều chỗ: một lệnh `python3 - <<EOF` thay chuỗi (assert chuỗi cũ có), thay vì nhiều lần Edit.
3. Kiểm tra: `dev/run.sh <test...>` chỉ chạy test liên quan (mỗi test in 1 dòng). Chạy hết `dev/run.sh` chỉ khi đổi phần dùng chung
   (browser_poster, db, ceo_orders). Chạy **một lệnh chờ xong** — không dùng Monitor báo từng dòng (mỗi thông báo tốn một lượt).
   Tính năng mới: thêm 1 file `dev/<tên>_test.py` gọn theo khuôn `reply_test.py`, thêm vào danh sách ALL trong `dev/run.sh`.
4. Cú pháp: `python3 -c "import ast;ast.parse(open(f).read())"` (Python 3.10) và `node --check` cho JS trích từ index.html.
5. Ảnh chụp giao diện: chỉ khi đổi giao diện, chụp **phần tử** vừa sửa (`locator.screenshot`), desktop 1400 + điện thoại 390,
   kiểm tra `scrollWidth` và lỗi JS bằng chữ; chỉ mở xem ảnh khi chữ báo có vấn đề.
6. Không hỏi lại khi yêu cầu rõ; không tường thuật từng bước; báo cáo cuối 5–10 dòng.
7. Ý tưởng lớn: nên mở phiên mới (phiên dài đọc lại toàn bộ lịch sử mỗi lượt, rất tốn).

## Xong việc
README (mục tính năng) → commit (`git -c user.email=triminh729@gmail.com -c user.name="triminh729" commit`, kết bằng dòng Co-Authored-By/Claude-Session
theo nhắc của hệ thống) → push `main` → đăng lại bản xem trước `frontend/index.html` vào link cũ https://claude.ai/artifact/XBxYWWaNBRvP1HvvgR1F6s
(cùng đường dẫn file; phiên mới thì truyền `url`) → `project_write` README vào `claude/phong-kinh-doanh-ai-huong-dan.md` bằng `local_path`.
Không commit `data/`, `.env`, `dev/work/`. Không lộ khóa API/Telegram.

## Không làm (sếp đã chốt)
Không né phát hiện của Facebook cho nhiều nick, không tự gửi kết bạn, không bình luận 24/24 hay mẹo né lọc spam.
