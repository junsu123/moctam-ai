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

## KPI phòng kinh doanh và báo cáo Telegram

**KPI:** số khách MỚI để lại số điện thoại mỗi ngày (mặc định tối thiểu 5, mục tiêu vượt 10; chỉnh ở trang
**KPI & Báo cáo**). KPI chia đều cho các nick đang chạy; khách tính cho nick đã đăng bài mà khách bình luận.

**Sale tìm khách và xin SĐT:**

- Vào các mốc giờ quét (mặc định 11:30, 16:30, 20:45) và mỗi lần up bài, nhân viên sale đọc bình luận trên các bài
  của chính nick mình (7 ngày gần nhất).
- Bình luận có SĐT (0912.345.678, +84…) hoặc thể hiện quan tâm ("quan tâm", "ib", "xin giá", "lấy sỉ"…) được tạo
  thành khách, ghi nguồn là bài đăng đó. Bình luận của chính nick và câu up bài bị bỏ qua; không tạo trùng khách.
- Khách quan tâm nhưng chưa để số: sale trả lời ngay dưới bình luận để xin SĐT/Zalo (câu chọn ngẫu nhiên trong danh
  sách, tối đa 10 câu mỗi nick/ngày). Lần quét sau, nếu khách để lại số, hệ thống tự cập nhật vào đúng khách đó.
- Đến giờ kiểm tra (mặc định 15:00), nếu KPI đang chậm so với tiến độ trong ngày, đội tự quét lại bình luận và báo sếp.

**Chuyển khách cho sếp** (AI không gọi điện hay nhắn Zalo được), bật/tắt từng loại:

- Khách đã để lại SĐT.
- Khách hỏi vượt khả năng AI: số lượng lớn (≥ 100 sản phẩm, theo thùng/kg), in nhãn riêng, chiết khấu, đại lý,
  hóa đơn/VAT, giấy kiểm nghiệm, khiếu nại, đổi trả.
- Khách có SĐT mà quá 2 giờ chưa ai tư vấn.

Mỗi khách được gửi qua Telegram một phiếu gồm: tên, SĐT (bấm để gọi trên điện thoại), nội dung bình luận, link bài
nguồn, lý do chuyển và **kịch bản tư vấn Hà soạn sẵn** (báo giá đúng sản phẩm khách quan tâm, câu hỏi khai thác nhu
cầu, đề nghị chốt). Nút bấm ngay trên tin: **Đã gọi**, **Chốt đơn**, **Không mua**, **Nhắc sau 2 giờ**. Kết quả được ghi
lại vào phần mềm và dùng cho việc tự học của Hà.

**Kết nối Telegram (5 phút):**

1. Trên Telegram, nhắn **@BotFather** → `/newbot` → đặt tên → nhận token.
2. Phần mềm → **KPI & Báo cáo** → dán token → **Lưu token** → **Tạo mã ghép nối**.
3. Mở bot vừa tạo, gửi mã 6 số. Bot trả lời "Đã kết nối". Chỉ chat đã ghép nối mới nhận báo cáo và ra lệnh được.

Bot chạy ngay trên máy của bạn (không cần tên miền hay mở cổng). Máy phải bật và có Internet thì bot mới trả lời.

**Báo cáo tự động:**

| Lúc | Nội dung |
|---|---|
| 09:00 | KPI hôm qua, chuỗi ngày đạt KPI, mục tiêu hôm nay, lịch đăng, kết luận và việc giao trong cuộc họp sáng, nick cần xử lý |
| Ngay khi có | Phiếu khách cần sếp tư vấn, nick bị checkpoint/đăng xuất |
| 15:00 | Cảnh báo nếu KPI đang chậm |
| Khi đạt | Chúc mừng đạt KPI tối thiểu, vượt KPI |
| 21:30 | KPI cả ngày theo từng nick, khách còn chờ sếp gọi, đơn đã chốt, bài học mới, chi phí AI |

**Lệnh Telegram:** `/baocao` báo cáo nhanh · `/kpi` tiến độ · `/khach` khách đang chờ sếp · `/hop [chủ đề]` triệu tập họp
(gửi kết luận khi họp xong) · `/tamdung` tạm dừng mọi nick · `/tieptuc` bật lại.

Hôm trước chưa đạt KPI thì cuộc họp sáng tự lấy chủ đề "làm gì để đạt KPI hôm nay".

**Lưu ý:** việc trả lời bình luận là hành động công khai của nick; giữ số câu trả lời mỗi ngày vừa phải và câu chữ
tự nhiên. Muốn sale chỉ đọc bình luận mà không trả lời, tắt "Trả lời khách quan tâm…" trong trang KPI.

## Agent tự học và phát triển

Mỗi agent có **sổ tay kinh nghiệm**, **cấp độ** và **mục tiêu hằng ngày** (trang **Đào tạo**).

**Học từ đâu** (dữ liệu thật, không đoán):

| Tín hiệu | Lấy từ | Ai học |
|---|---|---|
| Khách và bình luận của từng bài | Gắn khách với "bài đăng nguồn" khi thêm khách; số bình luận đọc tự động khi sale up bài | Lan, Tuấn, sale |
| Sếp duyệt ngay / sửa / loại bài | Nút Duyệt, Sửa, Loại (chọn lý do: Quá dài, Không hấp dẫn…) | Lan |
| Tin nhắn chốt được đơn hay không | Bấm "Đã gửi cho khách" (lưu bản cuối), rồi đổi trạng thái khách sang Đã nhập hàng / Không mua | Hà |
| Lỗi đăng, bài bị gỡ, bài chờ duyệt | Nhân viên sale ghi lại khi đăng và up bài | Tuấn, sale |
| Quyết định trong cuộc họp | Kết luận của Minh | Minh |

**Học thế nào:**

1. **Thống kê (không tốn AI):** điểm mỗi bài = khách × 5 + bình luận, làm mượt để vài bài may mắn không làm lệch.
   Lan chọn góc viết và sản phẩm theo điểm này (vẫn dành 25% để thử cái mới, chỉnh được), Tuấn dời lịch đăng vào
   "giờ vàng" khi có đủ dữ liệu.
2. **Ví dụ mẫu:** bài nhiều khách nhất, bản sếp đã sửa và tin nhắn đã chốt đơn được đưa vào prompt để agent học cách viết.
3. **Phản tỉnh mỗi đêm** (mặc định 23:15): mỗi agent đọc số liệu của mình, ghi tối đa 2 bài học mới có bằng chứng,
   bỏ bài học không còn đúng và đặt mục tiêu cho ngày mai. Dùng Claude Haiku, khoảng 0,002 USD/đêm; không có API key
   thì vẫn học bằng luật thống kê.

Sổ tay giữ tối đa 10 bài học đang dùng mỗi agent (bài ghim không tính); 6 bài quan trọng nhất được đưa vào prompt.
Sếp có thể **dạy trực tiếp** (bài học được ghim), **ghim** hoặc **bỏ** bất kỳ bài học nào.

**Kinh nghiệm và cấp độ:** agent nhận điểm kinh nghiệm khi bài được duyệt, được đăng, có khách, khách chốt đơn,
rút ra bài học… Cấp độ hiện trên nhân vật 3D. Trang Đào tạo so sánh kỹ năng tuần này với tuần trước
(tỉ lệ bài duyệt ngay, khách mỗi bài, tỉ lệ đăng thành công, tỉ lệ chốt…).

**Ranh giới:** bài học chỉ thay đổi cách viết và cách chọn góc, sản phẩm, nhóm, giờ đăng. Giới hạn bài/ngày, giãn cách,
luật nhóm và việc dừng khi checkpoint là do sếp đặt; bài học đề xuất tăng tần suất, lách luật hay hứa công dụng chữa
bệnh bị tự động loại.

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

Chưa có khóa API, hệ thống vẫn chạy ở **chế độ mô phỏng** (nội dung mẫu, không tốn tiền) để bạn làm quen giao diện.
Để các agent thực sự suy nghĩ, viết bài, họp và tư vấn:

1. Vào <https://console.anthropic.com> → **API Keys** → **Create Key**. Nạp tín dụng ở **Billing** và nên đặt giới hạn
   chi tiêu tháng tại đó.
2. Trong phần mềm: **Cài đặt → Khóa API Claude** → dán khóa → **Kiểm tra và lưu**.
   Phần mềm gửi một yêu cầu rất nhỏ tới Anthropic để kiểm tra khóa còn hiệu lực và tài khoản còn tín dụng, rồi mới lưu.
   Khóa có hiệu lực ngay, không cần khởi động lại.
3. Góc trái dưới giao diện báo "AI đang hoạt động".

Khóa được lưu trong `data/company.db` trên máy bạn, chỉ hiện dạng che (`sk-ant-api…abcd`). Vẫn có thể đặt
`ANTHROPIC_API_KEY` trong file `.env` như trước; khóa nhập trong phần mềm được ưu tiên hơn.

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
  kpi.py         KPI: nhận diện SĐT, tiến độ, chia theo nick, lịch sử; chuyển khách cho sếp, kịch bản tư vấn
  telegram_bot.py  Bot Telegram: ghép nối, báo cáo, phiếu khách có nút bấm, lệnh /baocao /kpi /khach /hop
  learning.py    Tự học: thống kê hiệu quả, chọn góc/sản phẩm/giờ, sổ tay bài học, cấp độ, phản tỉnh mỗi đêm
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
