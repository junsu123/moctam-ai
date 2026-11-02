# Phòng Kinh doanh AI — xưởng trà & bột thiên nhiên

Một "công ty" gồm 5 nhân viên AI làm thay phần việc của đội sale đăng bài tìm khách sỉ
(người bán online, chạy ads, livestream, bán sàn). Bạn là sếp: duyệt bài, nghe họp, ra quyết định.

## Đội ngũ

| Agent | Vị trí | Việc làm hằng ngày |
|---|---|---|
| **Minh** | Trưởng phòng | Chủ trì họp giao ban, chốt quyết định, giao việc cho từng người |
| **Lan** | Content | Viết bài đăng theo sản phẩm, góc tiếp cận, nơi đăng; gợi ý ảnh/video cần chụp |
| **Tuấn** | Hội nhóm | Ghép bài đã duyệt với nhóm phù hợp, tôn trọng luật nhóm và số ngày giãn cách, xếp giờ đăng |
| **Hà** | Chăm sóc khách | Chấm điểm khách, soạn tin nhắn trả lời, nhắc bám khách sau 2 ngày |
| **Khoa** | Phân tích | Đo số bài, số khách, nhóm hiệu quả nhất; đưa số liệu vào cuộc họp |
| **Sale 1…8** | Nhân viên sale | Mỗi sale giữ **một tài khoản Facebook** trong một hồ sơ Chrome riêng, tự đăng bài vào nhóm và trang cá nhân theo lịch |

## Một ngày làm việc

1. **08:30** (đổi được trong Cài đặt): cả đội tự đi vào phòng họp 3D. Mỗi người báo cáo bằng số liệu thật
   trong hệ thống, rồi tranh luận 2 vòng về một chủ đề (trưởng phòng chọn, hoặc sếp tự đặt).
   Sếp gõ ý kiến vào ô "Sếp phát biểu" bất cứ lúc nào, trưởng phòng sẽ phản hồi và cả nhóm tính đến.
2. Kết thúc họp: Minh chốt việc → mục **Việc được giao**.
3. Sau họp (tự động): Lan viết bài nháp → **sếp duyệt** → Tuấn xếp lịch vào nhóm → Hà lọc khách cần bám.
4. Đến giờ trong lịch, nhân viên sale AI tự mở Chrome của nick mình, vào nhóm, dán nội dung, đính kèm ảnh sản phẩm, bấm Đăng,
   chụp ảnh màn hình làm bằng chứng rồi đóng Chrome.
5. Khi có người bình luận/inbox: thêm vào **Khách hàng**, để Hà soạn tin, sao chép gửi khách.
6. Nhập số bình luận và số khách thu được cho từng bài đã đăng → Khoa xếp hạng nhóm hiệu quả.

## Nhân viên sale và tài khoản Facebook

Mỗi sale AI giữ một nick Facebook. Nick nằm trong một hồ sơ Chrome riêng tại `data/profiles/sale-<số>`,
tách biệt với Chrome bạn dùng hằng ngày.

**Lần đầu cho mỗi nick:**

1. Vào **Nhân viên sale** → *Tuyển sale* (tối đa 8 người, mỗi người có bàn riêng trong văn phòng 3D).
2. Bấm **Mở Chrome**. Một cửa sổ Chrome của nick đó hiện lên trên máy đang chạy phần mềm.
   Đăng nhập Facebook (kể cả mã xác thực 2 lớp nếu có), vào sẵn các nhóm cần đăng, rồi **đóng cửa sổ**.
   Phiên đăng nhập được giữ lại trong hồ sơ; phần mềm không lưu mật khẩu.
3. Vào **Hội nhóm**, bấm tên nick ở cột "Nick đã vào nhóm" để đánh dấu nick nào là thành viên nhóm nào,
   và dán đường dẫn nhóm (bắt buộc để sale tìm được nhóm).
4. Ở **Bài đăng**, chọn một bài đã xếp lịch → **Đăng thử**. Sale điền nội dung và ảnh nhưng không bấm Đăng,
   rồi chụp màn hình để bạn kiểm tra. Ổn thì để sale tự đăng theo lịch.

**Tuấn xếp lịch theo các quy tắc an toàn:**

- Nick phải là thành viên nhóm; mỗi nhóm chỉ nhận 1 bài mỗi lượt và phải hết số ngày giãn cách.
- Mỗi nick không vượt số bài/ngày (mặc định 5), hai bài cách nhau tối thiểu 40 phút cộng thêm vài phút ngẫu nhiên,
  chỉ đăng trong khung giờ của nick (mặc định 08:00–22:00). Chỉnh trong thẻ của từng sale.
- Mỗi nick tối đa 1 bài trang cá nhân/ngày. Mỗi bài là một nội dung riêng do Lan viết, không đăng trùng.

**Khi có sự cố:** nếu Facebook chuyển sang trang checkpoint, đăng xuất, hoặc báo tạm chặn, sale dừng ngay,
tắt tự đăng của nick đó, trả các bài chờ về hàng đợi và báo lên Văn phòng. Bạn mở Chrome của nick để xử lý,
rồi bấm **Bật tự đăng**. Phần mềm không giải captcha và không giả mạo trình duyệt.

**Khi Facebook đổi giao diện:** nếu bài báo lỗi "Không tìm thấy ô viết bài", mở `backend/fb_selectors.json`
và thêm chữ đang hiển thị trên nút (ví dụ chữ trong ô "Viết gì đó…" của nhóm) vào danh sách tương ứng.

**Lưu ý:** Điều khoản của Facebook không cho phép tự động hóa đăng bài bằng tài khoản cá nhân. Nick vẫn có thể bị
hạn chế dù đã giãn cách, nên giữ số bài/ngày vừa phải, nội dung có giá trị và đúng luật từng nhóm.
Máy chạy phần mềm phải bật trong giờ đăng bài; Chrome của các nick chạy trên chính máy đó.

## Lưu link bài và tự động up bài

**Link bài:** ngay sau khi đăng, nhân viên sale mở mục "Nội dung của bạn" trong nhóm (hoặc trang cá nhân), tìm đúng bài
vừa đăng và lưu link thật của bài (đã bỏ phần theo dõi `__cft__`). Bài vào hàng chờ duyệt của nhóm được đánh dấu
"chờ duyệt" và sẽ lấy link sau. Không tìm được link thì dán tay vào thẻ bài ở mục **Bài đăng**.

**Up bài hằng ngày:** vào **Cài đặt → Tự động up bài**, chọn thư mục ảnh trên máy chạy phần mềm rồi bấm
*Kiểm tra thư mục*. Từ giờ đã chọn (mặc định 19:30), mỗi nhân viên sale vào lại các bài chính mình đã đăng trong
7 ngày gần nhất và bình luận một ảnh sản phẩm, kèm một câu ngẫu nhiên trong danh sách (để trống thì chỉ gửi ảnh).

```
D:\AnhSanPham\
    Tra gung mat ong\      <- ảnh riêng cho sản phẩm (tên thư mục có dấu hay không dấu đều được)
    Bot ngu coc\
    anh-chung.jpg          <- ảnh để ngoài: dùng cho mọi bài
```

- Bài nào up ảnh của đúng sản phẩm bài đó; ảnh không lặp lại trên cùng một bài cho tới khi dùng hết ảnh.
- Mỗi bài tối đa 1 lần/ngày; bài vừa đăng trong 10 giờ chưa up; mỗi nick tối đa 8 lượt/ngày, cách nhau ≥ 6 phút
  cộng thêm vài phút ngẫu nhiên, trong khung giờ của nick. Đăng bài luôn được ưu tiên trước up bài.
- Bài bị xóa hoặc ẩn: sale tự ngừng up bài đó. Nick gặp checkpoint: dừng cả đăng và up.
- Thẻ bài ở mục **Bài đăng** có nút *Mở bài viết*, *Up ngay*, *Dừng tự up*, số lần đã up và ảnh chụp lượt gần nhất.
- Nếu báo "Không tìm thấy ô bình luận" hoặc "không đính kèm được ảnh", thêm chữ đang hiển thị vào `comment_box`
  hoặc `comment_attach` trong `backend/fb_selectors.json`.

Up bài không gọi AI nên không tốn chi phí Claude.

## Cài đặt và chạy

Cần Python 3.10 trở lên.

**Windows:** bấm đúp `run.bat`.  
**macOS / Linux:** `bash run.sh`

Hoặc thủ công:

```bash
pip install -r requirements.txt
cd backend
python main.py
```

Mở trình duyệt tại <http://localhost:8000>.

Lần chạy đầu, `run.bat` cài thêm trình duyệt dự phòng cho Playwright (khoảng 150MB). Nếu máy đã có Google Chrome,
sale sẽ dùng Chrome thật.

Phần mềm mặc định chỉ mở cho chính máy này (127.0.0.1) vì nó điều khiển được các nick Facebook.
Muốn mở từ máy khác trong mạng nội bộ, đặt `HOST=0.0.0.0` trong `.env` và chỉ làm vậy trong mạng tin cậy.

### Bật bộ não Claude

Chưa có API key, hệ thống vẫn chạy ở **chế độ mô phỏng** (nội dung mẫu) để bạn làm quen giao diện.
Để các agent thực sự suy nghĩ, viết bài và tranh luận:

1. Lấy API key tại <https://console.anthropic.com>.
2. Đổi tên `.env.example` thành `.env`, điền `ANTHROPIC_API_KEY=...`.
3. Khởi động lại. Góc trái dưới giao diện sẽ báo "AI đang hoạt động".

## Cấu trúc mã nguồn

```
backend/
  main.py        API web (FastAPI) + phục vụ giao diện
  agents.py      Hồ sơ 5 agent: vai trò, tính cách, ngoại hình 3D
  workflows.py   Việc của từng agent: viết bài, xếp lịch nhóm, chăm khách, số liệu
  meeting.py     Phòng họp: báo cáo → tranh luận → chốt việc
  scheduler.py   Lịch tự động: họp mỗi sáng, đăng Fanpage đúng giờ
  facebook.py    Đăng Fanpage qua Graph API
  browser_poster.py  Nhân viên sale điều khiển Chrome của nick: đăng nhập lần đầu, đăng bài, lấy link bài, up bài
  media_folder.py    Đọc thư mục ảnh sản phẩm trên máy, chọn ảnh theo sản phẩm
  fb_selectors.json  Chữ hiển thị trên giao diện Facebook (sửa khi Facebook đổi giao diện)
  llm.py         Kết nối Claude (tự chuyển sang mô phỏng khi chưa có key)
  mock_brain.py  Nội dung mẫu cho chế độ mô phỏng
  db.py          Cơ sở dữ liệu SQLite (data/company.db) + dữ liệu mẫu
data/
  profiles/      Hồ sơ Chrome của từng nick (chứa phiên đăng nhập, giữ kín, không chia sẻ)
  media/         Ảnh sản phẩm để đăng kèm
  shots/         Ảnh chụp màn hình sau mỗi lần đăng
frontend/
  index.html     Giao diện web + văn phòng 3D (Three.js)
```

Muốn thêm agent mới: thêm hồ sơ vào `agents.py` (`AGENTS`, `ORDER`), thêm vào `DEBATERS` trong
`meeting.py`, thêm vào `AGENT_DEFS` và một vị trí bàn trong `DESKS` ở `frontend/index.html`.

## Chi phí AI và cách tối ưu

Vào **Cài đặt → Chi phí AI** để xem số tiền thật đã dùng trong tháng (đo từ số token của từng lượt gọi),
dự báo cuối tháng và chi phí theo từng việc.

| Gói | Viết bài | Tin nhắn khách | Cuộc họp | Ước tính / tháng (3 nick sale) |
|---|---|---|---|---|
| Tiết kiệm | Haiku 5.5, theo lô | Haiku 5.5 | Haiku 5.5 | dưới 1 USD |
| **Cân bằng** (mặc định) | Sonnet 5.5, theo lô | Haiku 5.5 | Haiku 5.5 | khoảng 3–6 USD |
| Chất lượng | Sonnet 5.5, theo lô | Sonnet 5.5 | Sonnet 5.5 | khoảng 8–15 USD |

Các cơ chế tiết kiệm có sẵn:

- **Viết theo lô (Batch API):** bài viết hằng ngày gửi một lần, giá giảm 50%, bài có sau vài phút (tối đa 24 giờ).
  Bài sếp bấm "Viết bài" vẫn viết ngay.
- **Chỉ viết đủ số bài cần đăng:** Lan tính số bài đăng được hôm nay (theo số nick, giới hạn bài/ngày, số nhóm đã hết
  giãn cách) rồi trừ bài còn trong kho. Không viết bài thừa.
- **Cuộc họp gọn:** mỗi lượt nói chỉ đưa 12 câu gần nhất vào AI, câu trả lời giới hạn độ dài; chọn được số vòng
  tranh luận và các ngày họp trong tuần. Báo cáo của nhân viên sale lấy thẳng từ số liệu, không tốn AI.
- **Ngân sách tháng:** chạm 100% thì mọi việc tự chuyển sang Haiku; chạm 120% thì tạm ngừng gọi AI và dùng
  nội dung mẫu đến tháng sau. Nên đặt thêm giới hạn chi tiêu trong Anthropic Console để chắc chắn.

Giá dùng để tính (USD / 1 triệu token, vào/ra): Haiku 5.5 0,10/0,50 · Sonnet 5.5 2/10 · Opus 5.5 4/20;
theo lô giảm 50%. Khi Anthropic đổi giá, sửa bảng `PRICES` trong `backend/llm.py`.
