# Phòng Kinh doanh AI — MỘC TÂM (ghi chú cho Claude khi code)

Trả lời sếp bằng tiếng Việt, ngắn. Sếp trả tiền theo lượt dùng Claude: **mỗi ý tưởng mới làm gọn, tiết kiệm token**.

## Bản đồ code (đừng đọc cả file lớn để tìm)
- `backend/` FastAPI + SQLite, Python 3.10. `main.py` (~500 dòng) = tạo app, tự khởi động lại, trả giao diện; endpoint `/api/...` nằm ở
  `backend/routes/<nhóm>.py` (posts, comments, sales, prospects, website...; chạy chung không gian tên với main.py, thứ tự ở `ROUTES`,
  thêm nhóm mới = tạo file + thêm tên). `db.py` = bảng + cài đặt mặc định (`DEFAULT_SETTINGS`), bảng ở `SCHEMA` + migration.
- `browser_poster.py` (1.8k) = Chrome theo nick (Playwright), hàng đợi việc mỗi sale `submit(sale_id, {"kind":...})`, `_worker` chia việc theo `kind`,
  `due_work`/`_job_session` = ca làm việc, `_send_comment(page, text, img)` gửi bình luận.
- Agent: `agents.py` (danh sách; phòng ban + nhân viên tuyển thêm `st-<id>` ở `departments.py`: `DEPTS`, `POSITIONS`, `need`, `review`, bàn `DESKS` 18–23 trong `world3d.js`), CEO nhận lệnh `ceo_orders.py` (`_rule_plan` regex + `execute` theo `type`, mô tả việc ở `ACTIONS_DOC`, cài đặt CEO được đổi ở `SETTINGS_OK`),
  lịch `scheduler.py` (gọi `xxx.tick(now)`), luật FB `fb_policy.py` (RULES, limits, allow; `factor` lấy thêm sức khỏe nick `nick_health.py`), gọi Claude `llm.py` (`llm.json(system, prompt, task=)`).
- Tính năng: đăng bài `workflows.py`; up bài + Bảo học viết `post_care.py` (màn Bình luận `comments.py`, đo hiệu quả / nhóm xóa `bump_watch.py`); tin nhắn Fanpage `page_inbox.py`; Trang xu hướng của Nhi `trend_pages.py` (Nhi tự học `trend_learn.py`, gọi từ `learning.py`; Nhi tự tạo Trang `trend_create.py`, chạy trong `_job_session` qua `due_work["create_pages"]`; bot ảnh riêng `telegram_img.py`, dự phòng bot chính; ảnh nhận ở `handle_message` của bot, bài có `fb_page_ref`, `image_path`); nuôi Page qua Chrome nick quản trị `page_grow.py` (`_switch_to_page/_switch_back` trong browser_poster); trả lời khách `replies.py`; lướt bảng tin nhóm `group_feed.py`; kết bạn `friends.py`; nơi đăng `group_target.py`;
  nhóm `group_finder.py`/`my_groups.py`/`group_review.py`; tìm khách `prospect.py`; website `website.py` (đội SEO Vy / Hương / Khải + Google: `seo_team.py`, API `routes/seo.py`, tab `js/pages/seoteam.js`); data rác `junk.py`.
- Giao diện chia nhỏ trong `frontend/`: khuôn `app.html` (dòng `@@include <file>`), CSS `css/0x-*.css`, nav ở `views/_shell.html`,
  mỗi trang `views/<trang>.html` (`<section id="v-xxx">`) + `js/pages/<trang>.js` (`loadXxx/renderXxx`), `js/router.js` (`show()`),
  `js/api.js`, `js/world3d.js`, bản xem trước giả lập `js/demo/*.js` (`05-handle.js` = `handle()`, `demoXxx()` ở 02–04).
  `backend/ui.py` ghép lại thành một trang khi chạy (mọi JS vẫn trong một `<script>`, như bản một file cũ). Không còn `frontend/index.html`.
  Đổi giao diện = sửa đúng file của trang đó, theo khuôn trang Kết bạn (`fr-*`: `views/friends.html`, `js/pages/friends.js`).

- Hiệu suất: `db.get_settings()` có bộ nhớ đệm 5 giây (ghi qua `set_setting`/`run` câu có `settings` là xóa đệm); giao diện tự cập nhật thì
  dùng `if(UX.idle()) return;` (`js/ux.js`); 3D chỉ vẽ khi đang xem. Đo bằng `python3 dev/perf.py`. Hướng dẫn cho sếp: `docs/HUONG-DAN-SUA-CODE.md`
  (cập nhật khi đổi cấu trúc code).

## Cách làm tiết kiệm token (bắt buộc)
1. Tìm bằng `grep -n` rồi đọc đúng đoạn (`sed -n a,bp`), không Read cả file lớn. Không đọc lại file vừa sửa.
2. Sửa nhiều chỗ: một lệnh `python3 - <<EOF` thay chuỗi (assert chuỗi cũ có), thay vì nhiều lần Edit.
3. Kiểm tra: `dev/run.sh <test...>` chỉ chạy test liên quan (mỗi test in 1 dòng). Chạy hết `dev/run.sh` chỉ khi đổi phần dùng chung
   (browser_poster, db, ceo_orders). Chạy **một lệnh chờ xong** — không dùng Monitor báo từng dòng (mỗi thông báo tốn một lượt).
   `dev/run.sh quick` = nhóm test không mở Chrome (~1 phút). Test hỏng khi thoát mã ≠ 0, in `CÓ LỖI a/b`, `KẾT QUẢ: LỖI` hoặc `XONG a/b` thiếu;
   cuối in `TỔNG: n/m đạt`. GitHub Actions (`.github/workflows/test.yml`) tự chạy check + quick mỗi lần push `main`; bộ đầy đủ chạy
   tay ở tab Actions và mỗi Chủ nhật. Thư viện chỉ cho test: `dev/requirements-dev.txt`.
   Tính năng mới: thêm 1 file `dev/<tên>_test.py` gọn theo khuôn `reply_test.py` (in `XONG a/b` hoặc assert), thêm vào ALL (và QUICK nếu không mở Chrome) trong `dev/run.sh`.
4. Cú pháp: `dev/check.sh` (vài giây: Python theo cú pháp 3.10 + ghép giao diện + `node --check` JS; ra luôn `dev/work/preview/index.html`).
5. Ảnh chụp giao diện (mở `dev/work/preview/index.html#<trang>`, chạy chế độ giả lập): chỉ khi đổi giao diện, chụp **phần tử** vừa sửa (`locator.screenshot`), desktop 1400 + điện thoại 390,
   kiểm tra `scrollWidth` và lỗi JS bằng chữ; chỉ mở xem ảnh khi chữ báo có vấn đề.
6. Không hỏi lại khi yêu cầu rõ; không tường thuật từng bước; báo cáo cuối 5–10 dòng.
7. Ý tưởng lớn: nên mở phiên mới (phiên dài đọc lại toàn bộ lịch sử mỗi lượt, rất tốn).

## Xong việc
README (mục tính năng) → commit (`git -c user.email=triminh729@gmail.com -c user.name="triminh729" commit`, kết bằng dòng Co-Authored-By/Claude-Session
theo nhắc của hệ thống) → push `main` → `dev/check.sh` rồi đăng lại bản xem trước `dev/work/preview/index.html` (đăng với tên `index.html`) vào link cũ
https://claude.ai/artifact/XBxYWWaNBRvP1HvvgR1F6s → `project_write` README vào `claude/phong-kinh-doanh-ai-huong-dan.md` bằng `local_path`.
Không commit `data/`, `.env`, `dev/work/`. Không lộ khóa API/Telegram.

## Không làm (sếp đã chốt)
Không né phát hiện của Facebook cho nhiều nick, không tự gửi kết bạn, không bình luận 24/24 hay mẹo né lọc spam.
