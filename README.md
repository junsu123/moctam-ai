# Phòng Kinh doanh AI — xưởng trà & bột thiên nhiên

Một "công ty" gồm 5 nhân viên AI làm thay phần việc của đội sale đăng bài tìm khách sỉ
(người bán online, chạy ads, livestream, bán sàn). Bạn là sếp: duyệt bài, nghe họp, ra quyết định.

## Mục tiêu chính: tìm khách sỉ trên mạng, lấy được số điện thoại

Mọi agent đều làm cho một mục tiêu: **tìm khách sỉ (người bán hàng online) và lấy SĐT để sếp liên lạc**. Mọi việc được đo bằng số khách sỉ có SĐT. Các kênh:

| Kênh | Ai làm | Cách làm |
|---|---|---|
| Viết bài, đăng nhóm, đọc bình luận dưới bài mình | Lan, Tuấn, sale | Lan viết bài, sale đăng vào nhóm và trang cá nhân, quét bình luận, xin SĐT người hỏi giá |
| Đọc bài và bình luận trong nhóm | Mai (mượn Chrome của sale) | Bắt người đang hỏi “tìm nguồn”, “cần nhập”, “xin giá sỉ” trà, ngũ cốc: khách nóng nhất |
| Quét trang chạy quảng cáo | Mai | Thư viện quảng cáo Facebook: trang đang trả tiền quảng cáo bán thực phẩm, đồ uống là người bán thật, có ngân sách |
| Tìm trang, shop livestream | Mai | Tìm trang theo 4 hướng, đọc trang Giới thiệu lấy SĐT kinh doanh công khai |

Trang **Tìm khách sỉ** có dòng số SĐT tìm được theo từng kênh trong 7 ngày; CEO cũng báo con số này khi sếp hỏi tình hình.

## Đội ngũ

| Agent | Vị trí | Việc làm hằng ngày |
|---|---|---|
| **Đức** | CEO | Điều hành nhân sự: thực hiện sa thải theo luật KPI, quyết định tuyển người thay vào nick cũ, tăng sale khi doanh thu chạm mốc hoặc khi tìm khách trên Facebook có tiềm năng; chỉ đạo đầu mỗi cuộc họp |
| **Minh** | Trưởng phòng | Chủ trì họp giao ban, chốt quyết định, giao việc cho từng người |
| **Lan** | Content | Viết bài đăng theo sản phẩm, góc tiếp cận, nơi đăng; gợi ý ảnh/video cần chụp |
| **Tuấn** | Hội nhóm | Ghép bài đã duyệt với nhóm phù hợp, tôn trọng luật nhóm và số ngày giãn cách, xếp giờ đăng |
| **Hà** | Chăm sóc khách | Chấm điểm khách, soạn tin nhắn trả lời, nhắc bám khách sau 2 ngày |
| **Khoa** | Phân tích | Đo số bài, số khách, nhóm hiệu quả nhất; đưa số liệu vào cuộc họp |
| **Mai** | Tìm khách sỉ | Tìm người đang bán hàng online (livestream, Facebook, TikTok Shop, Shopee, đa nền tảng), chấm điểm 100 có bằng chứng, đưa khách hạng A/B vào mục Khách hàng; không tự nhắn tin |
| **Vy** | Website & SEO | Quản lý website công ty, lên kế hoạch từ khóa, viết bài chuẩn SEO (tự chấm theo bảng kiểm), dựng website và đăng lên hosting |
| **Bảo** | Chăm sóc bài đã đăng, bình luận khách | Mỗi ngày rà soát các bài đã đăng còn hiển thị, giao đúng nick đã đăng bình luận 1 ảnh sản phẩm kèm câu ngắn tự viết và dòng liên hệ Zalo của sếp; đọc bảng tin nhóm của mọi nick, viết sẵn bình luận cho người hỏi mua và người bán online (sếp duyệt) |
| **Sale 1…8** | Nhân viên sale | Mỗi sale giữ **3–5 tài khoản Facebook**, mỗi nick một hồ sơ Chrome riêng; làm theo ca từng nick: đăng bài vào nhóm và trang cá nhân, up bài, quét bình luận, rồi chuyển nick kế tiếp |

## Một ngày làm việc

1. **08:30** (đổi được trong Cài đặt): cả đội tự đi vào phòng họp 3D. Mỗi người báo cáo bằng số liệu thật
   trong hệ thống, rồi tranh luận 2 vòng về một chủ đề (trưởng phòng chọn, hoặc sếp tự đặt).
   Sếp gõ ý kiến vào ô "Sếp phát biểu" bất cứ lúc nào, trưởng phòng sẽ phản hồi và cả nhóm tính đến.
2. Kết thúc họp: Minh chốt việc → mục **Việc được giao**.
3. Sau họp (tự động): Lan viết bài nháp → **sếp duyệt** → Tuấn xếp lịch vào nhóm → Hà lọc khách cần bám.
4. Đến giờ trong lịch, nhân viên sale AI tự mở Chrome của nick có việc, vào nhóm, dán nội dung, đính kèm ảnh sản phẩm, bấm Đăng,
   chụp ảnh màn hình làm bằng chứng rồi đóng Chrome.
5. Khi có người bình luận/inbox: thêm vào **Khách hàng**, để Hà soạn tin, sao chép gửi khách.
6. Nhập số bình luận và số khách thu được cho từng bài đã đăng → Khoa xếp hạng nhóm hiệu quả.

## Nhân viên sale và tài khoản Facebook

Mỗi sale AI giữ **3–5 nick Facebook** (tối đa 5). Mỗi nick nằm trong một hồ sơ Chrome riêng tại
`data/profiles/acc-<số>` (nick từ bản cũ giữ nguyên thư mục `sale-<số>`, không phải đăng nhập lại),
tách biệt với Chrome bạn dùng hằng ngày.

**Sale làm theo ca, từng nick một.** Mỗi lúc một sale chỉ mở Chrome của một nick: mở nick, làm hết việc đã đến giờ
của nick đó (đăng bài, up bài, quét bình luận), đóng Chrome rồi chuyển sang nick kế tiếp có việc. Đến lượt sau
sale bắt đầu từ nick sau nick vừa làm, nên các nick được làm xoay vòng đều nhau. Tìm nhóm và xin vào nhóm cũng
xoay vòng theo nick (mỗi nick xin vào tối đa 2 nhóm/ngày).

**Chia bài đều cho mọi nick.** Khi xếp lịch, Tuấn chọn nick đang có ít bài nhất hôm nay trước, rồi lấy nhóm tốt nhất mà nick
đó đăng được (trước đây chọn nhóm tốt nhất rồi mới tới nick, nên nick không ở các nhóm tốt nhất hay bị bỏ cả ngày). Thẻ nick
ở trang **Nhân viên sale** có ô **“Vì sao hôm nay nick chưa có việc”** khi nick chưa có bài, lượt up nào trong ngày (hoặc có điều
cần lưu ý), kèm cách xử lý: nick tắt, chưa đăng nhập, sale tạm dừng, đang nghỉ theo Luật Facebook, chưa rà soát nhóm,
không ở nhóm nào trong danh sách đăng (hay chỉ 1–2 nhóm), hết giờ làm, đã đủ bài, nick mới đang chạy nửa trần, chưa có bài
đã duyệt. Nick chỉ được xếp vào nhóm nick đó thật sự đang ở; nick không ở nhóm nào trong danh sách thì phải cho nick vào nhóm
(hoặc Rà soát nhóm của nick để thêm nhóm nick đang ở) mới có việc.

**Rải bài đều cả ngày.** Bài thứ k của một nick không xếp sớm hơn mốc k trong khung giờ làm của nick (VD 08:00–22:00, 5 bài/ngày
thì khoảng 2 giờ 48 phút một bài), các nick cùng sale lệch nhau. Sale giữ 5 nick, mỗi nick 5 bài: 25 bài rải từ 08:00 tới khoảng
21:30, cứ khoảng 34 phút một bài, thay vì dồn hết vào buổi sáng mỗi 10 phút một bài. Tắt bằng cài đặt `spread_posts=0`.
Một sale tối đa 5 nick; nhiều nick thì cần nhiều nhóm hơn (mỗi nhóm 1 bài/ngày, rồi giãn cách vài ngày) và nhiều bài đã duyệt
hơn (mỗi bài một nội dung riêng): 5 nick × 5 bài cần khoảng 25 nhóm đăng được mỗi ngày, tức danh sách 60–80 nhóm nick đang ở.

**Lần đầu cho mỗi nick:**

1. Vào **Nhân viên sale** → *Tuyển sale* (tối đa 8 người, mỗi người có bàn riêng trong văn phòng 3D), đặt tên nick đầu tiên.
   Sale mẫu (nếu có) tự rời văn phòng ngay khi bạn tuyển người đầu tiên.
   Rồi bấm **Thêm nick** trong thẻ sale cho đủ 3–5 nick.
2. Ở từng nick, bấm **Mở Chrome**. Một cửa sổ Chrome của nick đó hiện lên trên máy đang chạy phần mềm.
   Đăng nhập Facebook (kể cả mã xác thực 2 lớp nếu có), vào sẵn các nhóm cần đăng, rồi **đóng cửa sổ**.
   Phiên đăng nhập được giữ lại trong hồ sơ; phần mềm không lưu mật khẩu.
3. Vào **Hội nhóm**, bấm tên nick ở cột "Nick đã vào nhóm" để đánh dấu nick nào là thành viên nhóm nào,
   và dán đường dẫn nhóm (bắt buộc để sale tìm được nhóm).
4. Ở **Bài đăng**, chọn một bài đã xếp lịch → **Đăng thử**. Sale điền nội dung và ảnh nhưng không bấm Đăng,
   rồi chụp màn hình để bạn kiểm tra. Ổn thì để sale tự đăng theo lịch.

**Tuấn xếp lịch theo các quy tắc an toàn:**

- Nick phải là thành viên nhóm; mỗi nhóm chỉ nhận 1 bài mỗi lượt và phải hết số ngày giãn cách.
- Bài được chia đều cho các nick đang chạy. Mỗi nick không vượt số bài/ngày (mặc định 3 cho nick mới), hai bài
  cách nhau tối thiểu 45 phút cộng thêm vài phút ngẫu nhiên, chỉ đăng trong khung giờ của nick (mặc định 08:00–22:00).
  Hai nick của cùng một sale cách nhau ít nhất 8–14 phút (thời gian đổi ca). Chỉnh ở mục *Giới hạn* của từng nick.
- Mỗi nick tối đa 1 bài trang cá nhân/ngày. Mỗi bài là một nội dung riêng do Lan viết, không đăng trùng.

**Khi có sự cố:** nếu Facebook chuyển sang trang checkpoint, đăng xuất, hoặc báo tạm chặn, sale dừng ngay
**riêng nick đó** (các nick khác của sale vẫn làm), trả các bài chờ của nick về hàng đợi để Tuấn xếp cho nick khác,
và báo lên Văn phòng, Telegram. Bạn mở Chrome của nick để xử lý, rồi bấm **Bật lại nick**.
Muốn cho cả sale nghỉ tạm thì bấm **Tạm dừng cả sale**. Phần mềm không giải captcha và không giả mạo trình duyệt.

**Khi sale không đăng được bài:** lỗi hiện ở thẻ bài (mục Bài đăng) và thẻ sale, kèm ảnh chụp màn hình lúc lỗi.

| Lỗi | Cách xử lý |
|---|---|
| Nhóm chưa có link | Hội nhóm → bấm **Thêm link** ở dòng nhóm đó, dán link nhóm (link điện thoại hay link chia sẻ đều được). Bài từng lỗi vì thiếu link tự về hàng chờ để Tuấn xếp lại. Nhóm mẫu cài sẵn không có link |
| Nick chưa là thành viên nhóm / đang chờ duyệt vào nhóm | Mở Chrome của đúng nick đó, tham gia nhóm, chờ quản trị viên duyệt |
| Hồ sơ Chrome của nick đang mở ở cửa sổ khác | Đóng cửa sổ Chrome của sale (cửa sổ mở bằng nút "Mở Chrome") rồi bấm đăng lại. Chrome cũ còn treo chạy ẩn (do phần mềm từng tắt đột ngột) được phần mềm tự đóng |
| Thông báo đỏ "Đang có 2 phần mềm chạy cùng lúc" / log báo `404` liên tục | Chạy lại run.bat: bản mới tự tìm và tắt mọi bản phần mềm đang chạy trước đó (kể cả bản cũ và Chrome của nó) rồi mới chạy |
| Cửa sổ đen hiện chữ đỏ `KeyboardInterrupt` | Không phải lỗi: phần mềm nhận lệnh dừng (bấm Ctrl+C trong cửa sổ đen). Từ bản này Ctrl+C chỉ hiện "Đã tắt phần mềm."; bấm chuột vào cửa sổ đen không còn làm phần mềm bị treo. Chạy lại run.bat để bật phần mềm |
| Thông báo "Đã có bản mới trên máy" | Không cần làm gì: phần mềm tự khởi động lại bằng bản mới khi các sale làm xong việc đang dở, trang tự tải lại. Muốn ngay thì bấm **Khởi động lại ngay** |
| Chrome của sale tự đóng ngay khi mở ("Target page, context or browser has been closed") | Phần mềm tự thử lại một lần. Nếu vẫn lỗi: đóng hết cửa sổ Chrome của sale, cập nhật Google Chrome lên bản mới nhất, tạm tắt phần mềm diệt virus đang chặn Chrome. Màn hình Lỗi nêu rõ nguyên nhân đoán được (ví dụ hồ sơ tạo bằng bản Chrome mới hơn bản trên máy) |
| Cửa sổ Chrome bị đóng khi sale đang làm | Không tắt cửa sổ Chrome lúc sale đang đăng bài; muốn không thấy cửa sổ thì bật "Ẩn cửa sổ Chrome khi sale đăng bài" trong Cài đặt |
| Nick chưa đăng nhập | Nhân viên sale → bấm **Mở Chrome để đăng nhập** ở đúng nick đó |
| Không tìm thấy ô viết bài / nút Đăng | Facebook đổi chữ trên nút. Lỗi ghi sẵn tên các nút đang thấy; thêm đúng chữ đó vào `backend/fb_selectors.json` (`group_composer`, `profile_composer`, `post_button`, `next_button`) |

Sale tự xử lý bước **Tiếp** mà Facebook hay chèn trước nút **Đăng**, tự đổi link nhóm dạng điện thoại (`m.facebook.com`)
sang giao diện máy tính. Nếu không đính được ảnh, sale vẫn đăng phần chữ và ghi chú lại để sếp biết.

**Lưu ý:** Điều khoản của Facebook không cho phép tự động hóa đăng bài bằng tài khoản cá nhân. Nick vẫn có thể bị
hạn chế dù đã giãn cách, nên giữ số bài/ngày vừa phải, nội dung có giá trị và đúng luật từng nhóm.
Máy chạy phần mềm phải bật trong giờ đăng bài; Chrome của các nick chạy trên chính máy đó.

### Chrome chạy ngầm: sếp vẫn dùng máy bình thường

**Cài đặt → Chrome của sale khi làm việc** (mặc định **Chạy ngầm**):
- **Chạy ngầm** (nên dùng): sale vẫn dùng Google Chrome thật với hồ sơ của nick, nhưng cửa sổ được đặt ra ngoài vùng màn hình.
  Sếp không thấy cửa sổ, dùng máy, gõ phím, chép dán bình thường. Phần mềm điều khiển Chrome qua kênh riêng của trình duyệt,
  **không dùng chuột, bàn phím hay khay nhớ tạm của máy**, nên sale và sếp không giành nhau. Đã tắt cơ chế Chrome tự giảm tốc
  tab bị che / không được chú ý, nên sale vẫn thao tác đều khi sếp mở cửa sổ khác. Biểu tượng Chrome vẫn có ở thanh tác vụ;
  đừng đóng nó khi sale đang làm.
- **Hiện cửa sổ**: xem sale làm việc (cửa sổ có thể hiện lên mỗi khi sale bắt đầu việc mới).
- **Ẩn hoàn toàn**: không có cửa sổ. Facebook dễ nhận ra trình duyệt chạy ẩn và hay hỏi xác minh hơn; chỉ nên dùng trên máy chủ.

Đăng nhập nick, nút **Mở Chrome** và **Mở hồ sơ** (kết bạn) luôn hiện cửa sổ trên màn hình vì cần người thao tác. Đổi chế độ
áp dụng từ lượt việc tiếp theo. Máy vẫn phải bật, không ngủ và còn mạng thì sale mới làm việc được.

## Luật Facebook: học luật, kiểm bài, giữ nhịp đăng an toàn

Mục **Luật Facebook** (nhóm Facebook ở thanh bên). Cả đội học luật từ chính sách của Meta và luật quảng cáo thực phẩm Việt Nam:
- Meta Community Standards: Spam, Tính toàn vẹn của tài khoản, Danh tính thật, Hành vi không xác thực, cách Meta hạn chế tài khoản.
- Tin Meta siết nội dung spam (04/2025).
- Luật Quảng cáo sửa đổi (hiệu lực 01/01/2026).

**Nói thẳng điều quan trọng nhất:** chính sách Tính toàn vẹn của tài khoản cấm dùng tài khoản bằng phần mềm tự động
(script), trừ khi qua kênh được phép. Đăng bằng nick cá nhân qua Chrome tự động vẫn có thể bị khóa dù làm đúng mọi giới hạn.
Các giới hạn dưới đây giảm rủi ro chứ không loại bỏ được. Kênh tự động được phép là Fanpage qua Graph API.

**Luật nằm ở đâu trong công việc:**
- **Sổ kiến thức**: mỗi luật được ghi vào sổ kiến thức của Lan, Tuấn, CEO, sale, Vy; lời dặn của mọi agent khi viết bài có
  phần “Luật Facebook cả đội phải giữ”.
- **CEO kiểm bài khi duyệt**: phạm nặng (hứa chữa bệnh, giảm cân, link rút gọn, nhồi hashtag, bài gần như y hệt bài đã đăng)
  thì không duyệt; phạm nhẹ (“nhất”, “số 1”, cam kết 100%, câu like/share/tag, bài khá giống bài cũ) thì trừ điểm và góp ý.
  Thẻ bài hiện chip **⚠ Luật Facebook**.
- **Sale kiểm lại ngay trước khi đăng**: bài phạm nặng về chờ duyệt để sửa; nick chưa đủ khoảng cách, hết trần bài/ngày, hoặc
  đã đăng vào nhóm đó trong 24 giờ thì bài được dời giờ, không đăng dồn.
- **Giới hạn an toàn mỗi nick** (sửa được): 6 bài/ngày tính cả bài nhóm mình quản lý, cách nhau ít nhất 30 phút, 6 lượt up bài,
  2 lần xin vào nhóm, 10 lời mời kết bạn (sale tự bấm), 1 bài/nhóm/24 giờ, tối đa 5 hashtag. Nick mới (dưới 14 ngày) chạy nửa giới hạn. Bảng **Nhịp đăng hôm
  nay** cho thấy mỗi nick đã làm bao nhiêu trên trần.
- **Rút kinh nghiệm**: nick bị chặn thì nghỉ 3 ngày rồi chạy nửa giới hạn 7 ngày; Tuấn ghi lại 24 giờ trước đó nick đã đăng, up,
  xin vào nhóm bao nhiêu. 2 nick bị chặn trong 7 ngày thì tự hạ trần chung 1 bài. Nhóm gỡ 2 bài trong 30 ngày thì ngừng đăng
  nhóm đó 30 ngày.
- **Luật của sếp**: thêm luật riêng kèm cụm từ cấm (VD tên đối thủ); bài có cụm đó bị chặn, cả đội học luật mới.
- **Kiểm thử một bài**: dán bài để xem phạm luật nào.

**Luôn cập nhật chính sách:** mỗi tuần (mặc định thứ Hai 06:40) Tuấn mở lại các trang chính sách của Meta bằng Chrome ẩn
(các trang này dựng bằng JavaScript), so với lần trước. Trang có thay đổi thì ghi dòng thêm / bớt, tóm tắt (có Claude thì
tóm tắt ảnh hưởng tới việc đăng bài), báo lên đầu mục Luật Facebook, nhật ký và Telegram. Bấm **Đọc lại chính sách ngay**
để đọc bất cứ lúc nào.

Lưu ý về bài mẫu: các biến thể của cùng một bài mẫu giống nhau khoảng 76–91% chữ. Bài giống từ 95% bị chặn, từ 85% bị nhắc.
Thêm nhiều bài mẫu khác nhau vào thư viện (hoặc bật Claude viết biến thể) giúp các nick ít bị coi là đăng lặp lại.

## Website công ty: Vy viết bài chuẩn SEO

Mục **Website** (nhóm Bán hàng). Vy (Biên tập Website & SEO) quản lý một website giới thiệu nhà máy:
- **Các trang**: Trang chủ, Giới thiệu, Gia công, Sản phẩm (mỗi sản phẩm một trang, không ghi giá, mời liên hệ Zalo), Tin
  tức (phân trang 12 bài), Liên hệ, 404.
- **Chuẩn kỹ thuật**: sitemap.xml, robots.txt, thẻ canonical và Open Graph, dữ liệu có cấu trúc schema.org (Organization,
  WebSite, Article, FAQPage, BreadcrumbList, Product, Service), mục lục bài, nút Chat Zalo, HTML tĩnh nhẹ, chạy tốt trên điện thoại.

**Kế hoạch từ khóa**: 16 từ khóa ban đầu cho người tìm xưởng gia công và nguồn sỉ (gia công trà túi lọc, OEM thương hiệu
riêng, nguồn hàng trà túi lọc sỉ...). Sếp thêm từ khóa; bấm **Vy nghĩ thêm từ khóa** để Vy đề xuất theo sản phẩm thật.

**Vy viết bài** (mặc định 3 bài/tuần vào T2, T4, T6 lúc 09:45, hoặc bấm **Vy viết bài mới** / **Viết ngay**). Có Claude thì
Vy viết 1000–1400 chữ theo từ khóa và sản phẩm thật; chưa có Claude thì dựng bài từ thông tin nhà máy và sản phẩm. Ảnh đại diện
lấy từ thư mục ảnh sản phẩm (ảnh tổng hợp nhà máy nếu đã tích), thu nhỏ cho web. Vy tự chấm theo **bảng kiểm SEO 100 điểm**:
- Từ khóa trong tiêu đề, 100 chữ đầu và 1 mục H2.
- Tiêu đề 30–65 ký tự, thẻ title 30–60, mô tả 120–160.
- Đường dẫn không dấu, ít nhất 4 mục H2, từ 900 chữ, mật độ từ khóa 0,5–2,5%.
- Ít nhất 2 liên kết nội bộ, 3 câu hỏi thường gặp, ảnh có chữ thay thế, đoạn văn ngắn.

Chưa đạt thì Vy sửa tối đa 2 lần. Bài hứa chữa bệnh bị chặn, không đăng được.

**Sếp duyệt**: mở bài trong bảng để sửa tiêu đề, mô tả, nội dung, câu hỏi thường gặp (điểm SEO chấm lại khi lưu), xem dạng
trang, rồi **Duyệt & đăng**. Bật “Vy tự đăng” để bài đạt điểm tối thiểu (mặc định 75) tự lên website.

**Đưa lên mạng**: website dựng vào `data/site/`, xem trước tại `/site/` trên máy chạy phần mềm. Điền tên miền ở tab Thông tin
công ty. Đăng lên hosting bằng FTP / FTPS (tab Đăng lên hosting) hoặc tải zip rồi tải lên `public_html`. Sau đó gửi
`https://ten-mien/sitemap.xml` vào Google Search Console.

### Giao diện website (bán hàng)

- **Trang chủ**: khối đầu màu lá trà đậm với lời giới thiệu nhà máy, nút **Nhận catalog & báo giá** (Zalo) và **Xem sản phẩm**,
  3 con số tin cậy (tiêu chuẩn, số mã sản phẩm, giao toàn quốc) và cụm 3 ảnh sản phẩm thật kèm nhãn “Giá tận xưởng”; rồi lưới
  sản phẩm, dịch vụ sỉ / gia công, bài viết, dải kêu gọi màu mật ong “Cần catalog và bảng giá sỉ?”.
- **Danh sách sản phẩm** (`/san-pham/`): **chỉ hiện từng sản phẩm riêng lẻ**. Vy tự bỏ sản phẩm “Ảnh tổng hợp nhà máy”, combo,
  bộ / hộp quà, “các loại”, “nhiều loại”, bảng giá, danh mục; “25 loại hạt”, “trà 5 vị” vẫn là một sản phẩm. Nhận sai thì vào
  **Website → Sản phẩm** chọn *Luôn hiện* / *Luôn ẩn*. Nút lọc theo nhóm sản phẩm (kèm số lượng). Thẻ sản phẩm: ảnh vuông,
  rê chuột xem ảnh thứ hai, nhãn “Bán chạy”, số ảnh, nhóm, tên, mô tả 2 dòng, nhập tối thiểu, nút **Hỏi giá sỉ** (Zalo).
- **Trang sản phẩm**: **thư viện tối đa 10 ảnh** của đúng sản phẩm (ảnh tải lên trong phần mềm và thư mục ảnh riêng của sản
  phẩm), vuốt trên điện thoại, nút trước / sau, dải ảnh nhỏ, bộ đếm “3 / 6”, bấm ảnh để **phóng to toàn màn hình** (phím ←/→,
  Esc). Sản phẩm chưa có ảnh riêng thì dùng tạm vài ảnh nhà máy (ghi rõ “Ảnh tại nhà máy”). Bên phải: tên, mô tả ngắn, điểm nổi
  bật, bảng thông tin (nhóm, nhập tối thiểu, giá sỉ, gia công), nút **Nhận báo giá qua Zalo** và **Gọi**, cam kết nhà máy / giao
  hàng / mẫu thử; dưới cùng là mô tả đầy đủ và sản phẩm khác. Schema Product có danh sách ảnh.
- **Chuẩn dùng**: chữ Be Vietnam Pro (dành cho tiếng Việt), co giãn theo màn hình (điện thoại 2 cột sản phẩm, menu cuộn ngang),
  thanh **Gọi / Chat Zalo** cố định đáy màn hình trên điện thoại, nút Chat Zalo nổi trên máy tính, viền nổi khi dùng bàn phím,
  tôn trọng chế độ giảm chuyển động. Ảnh được thu nhỏ (ảnh lớn 1400px, ảnh thẻ 520px) và chỉ tạo lại khi ảnh gốc đổi.

## Bảng bài đã đăng (phân trang)

Mục **Bài đăng** có 2 tab (số bên cạnh tên tab là số bài; tab Bài đã đăng hiện đỏ khi có bài chưa có link):
- **Bài đăng**: việc đang chạy: bài mẫu, giao Lan viết, Làm lại bài đăng, 3 cột Chờ duyệt / Đã duyệt / Lịch đăng hôm nay.
- **Bài đã đăng**: bảng có phân trang. Mở thẳng bằng link `#posts/posted`; phần mềm nhớ tab sếp xem lần trước.

Bảng **Bài đã đăng**:
- Dòng tổng: số bài đã đăng, hôm nay, có link / chưa có link / chờ nhóm duyệt / bị xóa-ẩn, tổng bình luận và khách.
- Mỗi dòng: ngày giờ đăng, mã và tên bài (kèm vài chữ đầu), nhóm, sale · nick, số ảnh, link bài (nút **Mở bài** hoặc
  trạng thái), số lần up, bình luận, khách.
- **Lọc** theo nhóm, nick, tình trạng link, thời gian (hôm nay, 7, 30, 90 ngày); **tìm** theo chữ trong bài, tên nhóm,
  link hoặc `#mã bài`; **sắp xếp** mới nhất, cũ nhất, nhiều khách, nhiều bình luận.
- **Phân trang** 10 / 20 / 50 / 100 bài mỗi trang.
- Bấm vào một dòng để mở chi tiết ngay trong bảng: nội dung, ảnh đã đăng, dán link, **Lấy link ngay**, **Up ngay**,
  bật/dừng tự up, ghi số bình luận và khách.
- Trên điện thoại mỗi bài hiện thành một khối gọn, không phải kéo ngang.

## Làm lại bài đăng (xóa bài lỗi, viết bài mới)

Ở mục **Bài đăng**, nút **Làm lại bài đăng** (cạnh “Tuấn xếp lịch đăng nhóm”) mở bảng cho biết sẽ xóa bao nhiêu bài:
**Đã duyệt** (chờ xếp lịch), **Lịch đăng** (ghi rõ số bài của hôm nay), **Đăng lỗi**, và tùy chọn **Chờ duyệt**. Tích các
nhóm bài muốn xóa, chọn số bài Lan **viết lại** (mặc định bằng số bài nhóm bị xóa, tối đa 20; để 0 nếu chỉ xóa) và có cho
Tuấn xếp lịch ngay khi viết xong không. Bấm nút xóa 2 lần để xác nhận (không hoàn tác được).

- Bài **đã đăng** lên Facebook và bài **đang đăng dở** luôn được giữ nguyên.
- Bài bị xóa biến mất hẳn khỏi bảng, lịch đăng của các nick và màn Lỗi; không bị tính là “sếp loại bài” nên Lan không học
  sai từ các bài này.
- Bài mới viết theo thư viện bài mẫu của sếp (nếu đang bật), CEO chấm trước; vẫn phải có ảnh mới được đăng.

## Thư viện bài mẫu sỉ: Lan học từ bài mẫu của sếp để viết lại hay hơn

Mục **Kho tri thức → Bài mẫu sỉ**. Sếp tạo danh sách các bài đăng sỉ mẫu; mọi bài đăng vào **nhóm nick đã tham gia** và **nhóm nick quản lý** là bản viết lại từ thư viện này: chỉ nội dung tìm khách sỉ, gia công, không đăng bài linh tinh, không ghi giá.

- **Thêm bài mẫu**: dán một bài (tên gợi nhớ không bắt buộc), hoặc **Dán nhiều bài một lần**, các bài cách nhau bằng một dòng chỉ có `---`. Viết `{số điện thoại}` ở chỗ cần ghi số, phần mềm thay bằng số Zalo báo giá (Cài đặt). Dòng “Ẩn bớt / Xem thêm” chép từ Facebook tự bị bỏ. Mẫu MỘC TÂM sếp gửi trước đó là bài mẫu đầu tiên.
- Mỗi bài mẫu có: **Đang dùng** (bật/tắt), **Xem Lan viết lại** (2 bản thử), **Sửa**, **Xóa**, và số liệu: số bài Lan đã viết lại, đã đăng, số bình luận, số khách.
- **Lan học thế nào**: thư viện được ghi vào sổ kiến thức của Lan. Có khóa Claude: Lan đọc cả thư viện (học cách mở đầu, bố cục, gạch đầu dòng, lời kêu gọi) rồi viết bài mới hay hơn từ một bài mẫu, giữ đúng thông tin của bài mẫu đó, không thêm thông tin mới. Chưa có khóa: Lan tự biến thể bài mẫu (đổi emoji, cách nói tương đương, thứ tự gạch đầu dòng, câu mở đầu, hashtag, có thể nhắc sản phẩm đang bán chạy). Mỗi bài đăng là một bản khác nhau, không trùng trong 14 ngày.
- **Mẫu nào hiệu quả thì dùng nhiều hơn**: Lan chọn bài mẫu theo số khách và bình luận trên mỗi bài đã đăng, vẫn chừa 25% lượt thử đều các mẫu khác.
- Bài viết từ bài mẫu được duyệt sẵn (nội dung do sếp đưa), Tuấn xếp lịch ngay; phần mềm vẫn tự bỏ mọi con số giá. Nút **Lan viết ngay 3 bài**; công tắc **Đăng nhóm theo bài mẫu** (tắt thì Lan viết bài nhóm theo từng sản phẩm như trước). Bài trang cá nhân và Fanpage vẫn viết theo sản phẩm.

## CEO học viết bài để duyệt bài tốt hơn

Khung **CEO học duyệt bài** ở cuối trang Bài mẫu sỉ. Mọi bài đăng (bài viết lại từ bài mẫu và bài nháp Lan viết) đều được CEO Đức chấm điểm 100 trước khi đăng; điểm và góp ý hiện trên từng bài ở trang Bài đăng.

| Tiêu chí | Điểm | CEO học từ |
|---|---|---|
| Nói rõ tìm khách sỉ / đại lý / gia công | 25 | Thư viện bài mẫu |
| Lời kêu gọi + số Zalo báo giá | 20 | Bài mẫu, quy định giá |
| Bố cục giống bài mẫu (tiêu đề ngắn, gạch đầu dòng, emoji vừa phải) | 15 | Bài mẫu, sếp chê nhiều emoji |
| Độ dài trong khoảng của bài mẫu | 10 | Bài mẫu, sếp rút ngắn bài |
| Giữ đủ thông tin chính của bài mẫu (thương hiệu, GMP, ISO, FDA…) | 15 | Bài mẫu gốc của bài đó |
| Không trùng bài đã đăng 14 ngày | 15 | Chống Facebook coi là spam |

Ghi giá, hứa công dụng chữa bệnh, có cụm câu sếp từng bỏ, hoặc trùng y hệt bài đã đăng thì không duyệt. Từ **70 điểm** trở lên mới duyệt (sửa được). Bài viết lại từ bài mẫu mà chưa đạt thì Lan viết lại bản khác (tối đa 4 lần) theo góp ý của CEO. Có khóa Claude thì CEO nhờ Claude đọc bài cùng thư viện mẫu và các bài học để góp ý thêm.

**CEO rút kinh nghiệm từ sếp**: sếp sửa hoặc hủy một bài CEO đã duyệt (trang Bài đăng) thì CEO ghi bài học vào sổ tay và sổ kiến thức: sếp rút ngắn thì hạ độ dài tối đa, sếp bỏ câu nào thì lần sau gặp câu đó không duyệt, sếp hủy vì “nhiều emoji” thì giới hạn emoji chặt hơn. Khung CEO học duyệt bài hiện: chuẩn CEO đang dùng, bài học từ sếp, số bài CEO duyệt/loại trong 30 ngày, tỉ lệ **duyệt đúng ý sếp**, và ô **CEO chấm thử** để sếp dán một bài bất kỳ. CEO cũng tự học thêm các chủ đề viết bài (tiêu chí bài tốt, dấu hiệu bài bị coi là spam, cách viết lời kêu gọi) lúc rảnh.

## Chỉ đạo nơi đăng: nhóm có từ khóa nào, tập trung nhóm nào

Ô **Chỉ đạo nơi đăng** ở trang **Bài đăng** (tab Bài đăng). Bấm **Sửa chỉ đạo**:
- **Đăng ở đâu**: *Mọi nhóm đủ điều kiện* (như cũ), *Ưu tiên nhóm chỉ định* (nhóm tập trung trước, rồi nhóm có từ khóa, còn bài
  thì đăng nhóm khác) hoặc *Chỉ nhóm chỉ định* (chỉ đăng nhóm tập trung hoặc nhóm có từ khóa, không đăng nhóm khác).
- **Đăng ở nhóm có từ khóa**: VD “trà, ngũ cốc, nguồn hàng sỉ”. So với tên, chủ đề và từ khóa tìm ra nhóm, không phân biệt dấu
  (gõ “ngu coc” cũng khớp “Ngũ Cốc”), khớp trọn cụm từ.
- **Không đăng nhóm có từ khóa**: VD “quần áo, mỹ phẩm”. Áp dụng cả khi chọn *Mọi nhóm*.
- **Nhóm tập trung đăng**: chọn nhóm từ danh sách (hoặc bấm **☆ Tập trung** cạnh tên nhóm ở trang Hội nhóm). Nhóm tập trung được
  xếp trước và đăng **mỗi ngày 1 bài** thay vì giãn cách vài ngày; luật 1 bài/nhóm/24 giờ của mỗi nick vẫn giữ.
- **Xem trước** ngay khi gõ: nhóm nào sẽ được đăng, nhóm nào không và vì sao. Chọn *Chỉ nhóm chỉ định* mà không nhóm nào khớp
  thì có cảnh báo: Tuấn sẽ không xếp bài vào nhóm nào.

Tuấn áp dụng từ lần xếp lịch tiếp theo, bài đã xếp lịch giữ nguyên. Chỉ đạo áp dụng cho nhóm thường; nhóm nick quản lý vẫn được
chăm đều mỗi ngày. Tuấn, CEO và Lan đều thấy chỉ đạo này trong lời dặn. Nhắn CEO cũng được: “chỉ đăng ở nhóm có từ khóa trà túi
lọc, ngũ cốc”, “không đăng vào nhóm mẹ bỉm”, “tập trung đăng vào nhóm Hội Bán Hàng Online”.

### Lệnh CEO: đăng bài ngay lên các nhóm theo từ khóa

Nhắn CEO (trên web hoặc Telegram), VD:
- “Đăng bài lên các nhóm có từ khóa trà, ngũ cốc”
- “Đăng 3 bài vào nhóm về mẹ bỉm”
- “Post bài lên group bán hàng online”

CEO tìm các nhóm có từ khóa (tên, chủ đề nhóm, không phân biệt dấu) và báo: có bao nhiêu nhóm khớp, hôm nay đăng được bao nhiêu
nhóm, nhóm còn lại vì sao chưa đăng (thiếu link, đang giãn cách, đã có bài chờ, sếp cấm, Tuấn đánh giá không nên đăng). Số bài:
theo số sếp nói, không nói thì mỗi nhóm đăng được một bài (tối đa 10). Đủ bài đã duyệt thì Tuấn xếp lịch ngay vào đúng các nhóm
đó; thiếu thì Lan viết thêm, CEO duyệt (chế độ CEO tự vận hành) rồi Tuấn xếp và CEO báo lại giờ đăng, nick đăng, tên nhóm.
Đây là lệnh một lần trong ngày: bài duyệt sau trong ngày vẫn được ưu tiên vào các nhóm này; khác với “chỉ đăng ở nhóm có từ khóa …”
là chỉ đạo lâu dài ở trên. Luật Facebook vẫn giữ (trần bài/nick/ngày, giãn cách, giờ đăng). Chưa có nhóm nào khớp thì CEO gợi ý
nhắn “tìm nhóm theo chủ đề …” để sale đi tìm nhóm trước.

## Lan chỉnh bài theo nhóm sắp đăng (dữ liệu thật của nhóm)

Bài được viết trước khi biết đăng nhóm nào. Khi Tuấn đã xếp bài vào một nhóm, Lan xem nhóm đó có **dữ liệu thật** không:
câu người trong nhóm đăng hỏi mua / tìm nguồn mà nick đọc được (lướt bảng tin, trả lời khách), bình luận của khách dưới bài mình
từng đăng ở nhóm, bài mình từng đăng ở nhóm có khách hoặc nhiều bình luận. Đủ dữ liệu (mặc định từ 2 tín hiệu) thì Lan nhờ Claude
sửa **câu mở đầu và thứ tự ý** cho trúng điều người nhóm đó đang hỏi, dùng cách gọi tên hàng giống họ.

- **Không thêm thông tin mới**: chỉ dùng thông tin của bài gốc (giá, chứng nhận, số liệu, quà tặng mới đều không được thêm), giữ dòng
  Zalo (thiếu thì tự gắn lại), độ dài gần bài gốc, luật nhóm được đưa vào lời dặn.
- **Giữ bài gốc** khi nhóm chưa đủ dữ liệu, bản chỉnh phạm luật Facebook, hoặc dài / ngắn quá. Thẻ bài ở mục Bài đăng hiện
  **✎ Chỉnh theo nhóm** (rê chuột xem đã sửa gì, dựa trên mấy câu hỏi, bình luận) hoặc **Giữ bài gốc** kèm lý do.
- Bài gốc được lưu lại: bài đổi sang nhóm khác thì chỉnh lại từ bài gốc, nhóm mới chưa có dữ liệu thì dùng bài gốc. Sếp sửa chữ
  bài thì bản của sếp là bản cuối, Lan không chỉnh đè. Bài còn dưới 3 phút nữa là đăng thì không đụng tới.
- Áp dụng cho bài đăng nhóm thường (cả bài viết lại từ bài mẫu); nhóm mình quản lý không chỉnh. Mỗi bài chỉnh 1 lần gọi Claude
  (mô hình của việc Viết bài đăng). Tắt ở **Cài đặt → Nhân viên sale đăng bài → Lan chỉnh bài theo nhóm**.

## Kết bạn với thành viên trong nhóm sôi nổi

Mục **Kết bạn** (nhóm Facebook ở thanh bên).

- **Nhóm sôi nổi nhất**: Tuấn chấm điểm 0–100 mỗi nhóm nick đang ở: số bài mỗi ngày (30 điểm), bình luận trung bình mỗi bài (30),
  cảm xúc (15), thành viên mới mỗi tuần so với tổng (15), quy mô (10); 3 ngày không ai đăng thì chia đôi. Nhóm sếp chọn tập trung
  đăng được xếp trên. Nhóm sếp cấm đăng không được chọn.
- **Tìm người**: mỗi ngày (mặc định 10:40, hoặc bấm **Tuấn tìm người ngay** / **Tìm người** ở một nhóm, hoặc nhắn CEO “cho các
  nick kết bạn với thành viên nhóm”), nick còn lượt mời mở bảng tin 2 nhóm sôi nổi nhất lâu chưa đọc (bài mới nhất), cuộn đọc
  bài và bình luận, chỉ đọc. Tuấn chọn người đang đăng bài, bình luận và chấm điểm hợp tệp khách: đang hỏi nguồn hàng hợp ngành
  (+45), quan tâm trà, ngũ cốc, đồ uống (+20), đang bán hàng online (+15), hoạt động nhiều lần (+5 mỗi lần). Bỏ xưởng / người bán
  sỉ cạnh tranh, tên nick của mình, data sếp đã loại. Một người chỉ được **một nick** của công ty mời (nhiều nick cùng mời một
  người là dấu hiệu mạng lưới tài khoản). Tối đa 12 người mỗi nhóm.
- **Gửi lời mời: sale tự bấm.** Phần mềm **không tự bấm “Thêm bạn bè”**: Facebook coi gửi lời mời hàng loạt bằng công cụ tự động
  là spam, nick bị chặn tính năng kết bạn hoặc khóa. Bấm **Mở hồ sơ** ở nick: Chrome của nick mở sẵn tối đa 5 trang cá nhân
  (mỗi trang một tab, trong trần còn lại). Bấm Thêm bạn bè trên từng trang, rồi đánh dấu **Đã gửi lời mời**. Người không hợp
  bấm **Bỏ qua** hoặc **Không hợp** (Mai ghi nhớ là data rác). Khi họ đồng ý, bấm **Họ đã đồng ý** để theo dõi tỷ lệ đồng ý.
- **Trần lời mời** (Luật Facebook): mặc định 10 lời mời/nick/ngày, nick mới hoặc vừa bị chặn còn một nửa, nick đang nghỉ không mời.
  Hết trần thì nút Mở hồ sơ khóa tới hôm sau. Tỷ lệ đồng ý dưới 30% là dấu hiệu mời nhầm người: giảm lời mời, chọn kỹ hơn.
- Đọc bảng tin xong, Tuấn cập nhật luôn chỉ số tương tác của nhóm (khi đọc được đủ bài).

## Bảo trả lời khách hỏi mua trong nhóm (sếp duyệt, nick gửi)

Mục **Trả lời khách** (nhóm Facebook ở thanh bên). Ngoài đăng bài, Bảo tìm những người **đang hỏi mua / hỏi nguồn hàng** trong
các nhóm sôi nổi để nick vào trả lời đúng lúc họ cần hàng.

- **Giao việc**: nhắn CEO, ví dụ “điều nhân viên đi comment vào các bài ở hội nhóm tương tác cao”, “trả lời khách trong nhóm”,
  hoặc bấm **Bảo tìm bài ngay**. Mỗi ngày Bảo tự làm một lượt (mặc định 09:20, sửa trong cài đặt).
- **Tìm bài**: nick ít việc nhất mở bảng tin 3 nhóm sôi nổi nhất mà nick đang ở (xếp theo điểm sôi nổi như mục Kết bạn), cuộn đọc,
  chỉ đọc. Bảo chỉ giữ bài gốc (không phải bình luận) mà người đăng đang hỏi mua / tìm nguồn / tìm xưởng **hợp ngành** (trà,
  ngũ cốc, cà phê, bột…). Bỏ bài người bán khác, bài không hỏi mua, bài ngoài ngành, bài của chính các nick, người sếp đã loại.
  Tối đa 4 bài mỗi nhóm, một bài chỉ trả lời một lần.
- **Viết câu trả lời**: Claude đọc nội dung bài và viết một câu 15–35 chữ trả lời đúng điều người đó hỏi (gợi ý gửi mẫu, báo giá),
  không ghi số điện thoại, không hứa chữa bệnh; Bảo tự gắn dòng liên hệ (mặc định dòng của Up bài, đổi riêng được). Cùng lượt gọi,
  Claude chấm điểm câu Bảo tự viết. Bảo lưu mẫu và lên tay nghề riêng cho việc trả lời khách (Học việc → Thạo việc → Giỏi → Master),
  tới **Master thì tự viết, không gọi Claude nữa**. Câu sếp sửa khi duyệt cũng được lưu làm mẫu. Không có khóa Claude thì Bảo tự viết.
- **Sếp duyệt**: mỗi bài hiện câu khách hỏi và câu trả lời (sửa được). **Duyệt và gửi**, **Bỏ qua**, **Không hợp** (người bán khác,
  Mai ghi nhớ là data rác), hoặc **Duyệt tất cả**. Câu phạm luật Facebook (hứa chữa bệnh, giảm cân, link rút gọn…) không duyệt được.
- **Nick gửi**: câu đã duyệt được xếp giờ trong **giờ làm của nick**, cách câu trước **45–90 phút**, tối đa **5 câu/nick/ngày** (sửa
  được, trần 10; nick mới hoặc vừa bị chặn còn một nửa). Hết lượt thì dời sang sáng mai. Tới giờ, ca làm việc của sale mở bài, gõ câu
  vào ô bình luận (chỉ chữ, không ảnh), bấm gửi, kiểm tra đã gửi và chụp ảnh. Lúc gửi kiểm lại giờ làm, trần và giãn cách; nick đang
  nghỉ sau sự cố thì không gửi; bài đã bị xóa thì bỏ qua.
- **Vì sao không chạy 24/24, không bình luận dạo**: bình luận quảng cáo vào bài không hỏi mua, cùng một câu ở nhiều bài, bình luận
  liên tục cả ngày lẫn đêm là spam theo luật Facebook (mục Luật Facebook → “Bình luận vào bài người khác”): nhóm xóa bình luận, chặn
  thành viên, Facebook khóa tính năng bình luận rồi khóa nick. Phần mềm cũng không dùng mẹo né bộ lọc spam của Facebook.

### Lướt bảng tin nhóm (facebook.com/groups/feed): mọi nick, sếp duyệt

Nút **Lướt bảng tin ngay** ở trang Trả lời khách, hoặc nhắn CEO “cho các nick lướt bảng tin nhóm và comment”. Mỗi nick đang làm
việc mở **bảng tin nhóm** (bài mới của mọi nhóm nick đang ở), cuộn đọc **ít nhất 20 bài** (sửa được, 10–60), chỉ đọc. Bài “gợi ý”
của nhóm nick chưa vào (có nút Tham gia) bị bỏ; nhóm mới thấy trên feed được tự thêm vào Hội nhóm và ghi nick là thành viên.

**Bảo lọc 3 lớp** để biết bài nào đáng bình luận, bài khác chỉ đọc qua:
1. **Lọc bằng chữ** (không tốn tiền), chia hai loại:
   - **Hỏi mua**: có ý định mua (“tìm nguồn”, “cần nhập”, “xin giá sỉ”…) và đúng ngành (trà, ngũ cốc, bột, đồ uống…).
   - **Người bán online**: không nhắc tới hàng của xưởng nhưng đang kinh doanh online và đang hỏi (tài khoản quảng cáo, chạy ads,
     BM, livestream, chốt đơn, ship COD, TikTok Shop, Shopee…; sếp thêm dấu hiệu riêng ở cài đặt).
   - Bỏ: người chào bán sỉ / tuyển đại lý, người bán dịch vụ (bán via, BM, nhận chạy quảng cáo, khóa học), bài của chính các nick,
     data rác sếp đã loại, chữ trong mục **Loại ngay nếu có** của điều kiện tìm khách sỉ, nhóm sếp cấm đăng.
2. **Claude đọc hiểu bài** (khi có khóa): xác định lại loại (hỏi mua / người bán / không phù hợp), chấm điểm 0–100 kèm một câu lý do,
   và viết câu chào riêng cho người bán. Chỉ bài từ **70 điểm** (sửa được) mới có bình luận. Chưa có khóa thì chỉ giữ bài khớp chắc ở lớp 1.
3. **Học từ sếp**: bài sếp **Bỏ qua** làm bài giống vậy bị trừ 20 điểm; **Không hợp** thì Mai ghi data rác; bài sếp duyệt / bỏ gần đây
   được đưa cho Claude làm ví dụ.

Mỗi bình luận hiện loại, điểm, lý do và đúng câu người đăng viết.

**Hai kiểu bình luận:**
- **Hỏi mua**: câu trả lời đúng điều họ hỏi (Claude viết, Bảo học dần rồi tự viết như phần trên) + **1 ảnh ngẫu nhiên** trong thư mục
  ảnh của sản phẩm họ cần (không có thì thư mục chung), ưu tiên ảnh chưa dùng ở nhóm đó + dòng Zalo.
- **Người bán online**: **chỉ chữ**, chào nhẹ, bám vào điều họ viết, giới thiệu xưởng, mời nhắn nếu cần thêm mặt hàng + dòng Zalo.
  Loại này bị báo cáo nhiều hơn nên giữ chặt hơn: **luôn chờ sếp duyệt**, tối đa **2 câu/nick/ngày** (sửa được 0–3, nick mới một
  nửa, nằm trong trần chung 5 câu), **mỗi người chỉ một nick chào một lần**, không chào ở nhóm cấm bán hàng. Sau 6 giờ nick mở lại
  bài xem bình luận chào còn không; nhóm đã xóa thì **ngừng chào người bán ở nhóm đó 30 ngày** (hiện ở trang Trả lời khách).

**Nhịp do luật của nick quyết định**, không đặt tay: mỗi nick tự lướt tối đa 2 lượt/ngày (nick mới hoặc vừa bị chặn 1 lượt), lượt đầu
lệch nhau giữa các nick trong giờ làm, lượt sau cách khoảng 3 giờ; nick đang nghỉ sau sự cố không lướt; nick đã có đủ câu chờ duyệt /
chờ gửi cho trần ngày thì không lướt thêm. Gửi bình luận vẫn theo nhịp chung: trong giờ làm, cách nhau 45–90 phút, tối đa 5 câu/nick/ngày.
Thẻ nick ở trang Trả lời khách cho biết hôm nay nick đã lướt mấy lượt, đọc bao nhiêu bài, tìm được bao nhiêu người và vì sao chưa lướt tiếp.

## Nhóm có sẵn trong nick: đăng ở đâu, thoát nhóm nào, chăm sóc nhóm mình quản lý

Mục **Hội nhóm → Nhóm trong các nick**.

- **Đọc danh sách nhóm thật của nick**: mỗi ngày (mặc định 09:15, hoặc bấm “Tuấn rà soát ngay”, hoặc nói với CEO “rà soát nhóm”) sale mở Facebook → Nhóm → *Nhóm bạn đã tham gia* của từng nick, lưu lại nhóm nào nick là **quản trị viên**, nhóm nào là thành viên. Nhóm mới thấy trong nick được tự thêm vào danh sách Hội nhóm.
- **Chỉ đăng vào nhóm nick đang ở**: khi nick đã được rà soát, Tuấn chỉ xếp bài của nick vào nhóm có trong danh sách của chính nick đó.
- **Nhóm mới vào thì chưa đăng**: nhóm do phần mềm xin vào phải nghỉ 7 ngày (sửa được) mới bắt đầu đăng. Nhóm có sẵn trong nick đăng được ngay.
- **Tuấn đánh giá từng nhóm** (đọc trang Giới thiệu và bảng tin như khi tìm nhóm mới, kèm kiểm tra nhóm có liên quan bán hàng, nguồn hàng, thực phẩm không): **Nên đăng**, **Đăng ít** (tương tác trung bình) hoặc **Thoát nhóm** (không liên quan, gần như không hoạt động, cấm bán hàng, chợ spam không ai bình luận). Mỗi lượt xem tối đa 8 nhóm, mỗi nhóm đánh giá lại sau 7 ngày.
- **Tự thoát nhóm**: tối đa 3 nhóm/nick/ngày cho tự nhiên. Không bao giờ thoát nhóm nick quản lý, nhóm đã mang về khách, nhóm sếp bấm **Giữ nhóm**. Sếp có thể bấm **Thoát** ở từng nhóm, hoặc tắt tự thoát trong cài đặt.
- **Nhóm mình quản lý**: mỗi nhóm nick là quản trị viên được đăng **5–10 bài mỗi ngày** (sửa được), rải đều trong khung giờ của nick, cách nhau ít nhất 25 phút. Tất cả là bài tìm khách sỉ, gia công viết lại từ thư viện bài mẫu của sếp (mỗi bài một bản khác nhau); Lan chỉ làm số bài còn kịp đăng trong ngày. Bài trong nhóm mình quản lý không tính vào giới hạn số bài/ngày của nick.

## Sale tự tìm hội nhóm mới

Mỗi ngày (mặc định 10:30) CEO Đức chọn 3 chủ đề tìm nhóm, ví dụ "hội chạy quảng cáo facebook", "nguồn hàng sỉ thực phẩm".
CEO ưu tiên chủ đề từng mang về khách, xen kẽ chủ đề chưa thử, và để dành chủ đề vừa tìm hôm trước. Rồi:

1. Một sale (luân phiên các nick) mở Chrome, **lướt bảng tin** vài phút (chỉ xem, không bấm thích, không bình luận),
   rồi vào Facebook → Tìm kiếm → **Nhóm** với từng chủ đề, cuộn đọc kết quả: tên, link, số thành viên,
   công khai/riêng tư, số bài mỗi ngày.
2. **Sale khảo sát rồi báo cáo.** Với các nhóm hứa hẹn nhất (mặc định 6 nhóm/lần), sale mở trang **Giới thiệu** và **bảng tin**
   của nhóm (chỉ đọc), ghi lại: số bài mới hôm nay và trong tháng, tổng thành viên và số thành viên mới tuần trước, cảm xúc và
   bình luận trung bình của các bài mới, bài mới nhất cách đây bao lâu, bao nhiêu bài là rao bán, luật nhóm có cấm bán hàng không.
   Báo cáo của sale hiện ở nhật ký và Telegram.
3. **Tuấn (chuyên viên hội nhóm) đánh giá có nên vào nhóm không**, so với **chuẩn nhóm tương tác cao**:

   | Chỉ số | Chuẩn mặc định | Trọng số |
   |---|---|---|
   | Tương tác mỗi bài | 20 cảm xúc, 5 bình luận | 45 điểm (bình luận 25, cảm xúc 20) |
   | Độ sôi nổi | 10 bài mới/ngày | 20 điểm |
   | Đúng chủ đề | tên nhóm khớp chủ đề tìm | 10 điểm |
   | Quy mô | càng đông càng tốt (đủ điểm từ 100.000) | 10 điểm |
   | Tăng trưởng | +0,5% thành viên/tuần | 10 điểm |
   | Bài mới nhất | trong 6 giờ | 5 điểm |

   Khi đã có nhóm thật mang về khách (và đã đo chỉ số), chuẩn tự lấy theo **trung vị các nhóm mang về nhiều khách nhất**.
   Nhóm toàn bài rao bán mà gần như không ai bình luận (chợ spam) bị trừ 20 điểm. **Loại ngay**: tên không khớp chủ đề,
   dưới 1.000 thành viên, luật nhóm cấm bán hàng/quảng cáo, nhóm chết (7 ngày không có bài, hoặc dưới 10 bài/tháng).

   | Kết luận | Điều kiện | Việc tiếp theo |
   |---|---|---|
   | **Nên vào** | từ 60 điểm **và** tương tác mỗi bài đạt từ 60% chuẩn | Tự thêm vào Hội nhóm (tối đa 5 nhóm/ngày), nick xin vào nhóm điểm cao trước |
   | **Cân nhắc** | 40–59 điểm, hoặc điểm cao nhưng mỗi bài ít người tương tác | Chờ sếp bấm **Thêm** hoặc **Bỏ** |
   | **Bỏ qua** | dưới 40 điểm hoặc bị loại | Nằm ở "Tuấn đã loại" kèm lý do; sếp vẫn bấm **Vẫn thêm** được |

   Nhóm riêng tư chưa xem được bài: chỉ "Nên vào" khi số bài mỗi ngày đạt chuẩn. Vào được nhóm rồi, sale đọc bài trong nhóm
   và Tuấn chấm lại bằng tương tác thật. Tuấn gửi bảng đánh giá qua Telegram: từng nhóm, điểm, chỉ số và lý do.
   Sửa chuẩn ở **Hội nhóm → Tìm nhóm mới → Sửa chuẩn nhóm tương tác cao**, bấm **Tuấn chấm lại** để áp dụng ngay.
   Khi xếp lịch đăng, Tuấn ưu tiên nhóm mang về khách, rồi nhóm điểm tương tác cao.
4. Mỗi nick **xin vào** tối đa 2 nhóm mới/ngày, giãn cách giữa các lần. Nhóm công khai vào ngay, nhóm riêng tư chờ
   quản trị viên duyệt (sale tự kiểm tra lại). Nhóm bắt **trả lời câu hỏi** thì sale không tự trả lời thay sếp: phần mềm
   và Telegram báo để sếp mở Chrome của sale tự xin vào.
5. Tuấn **ưu tiên đăng** vào nhóm hợp chủ đề hôm nay. Nhóm sale tự tìm chỉ nhận bài từ nick đã vào nhóm.

Sửa chủ đề hôm nay, kho chủ đề, giờ tìm, số nhóm thêm/xin vào mỗi ngày ở **Hội nhóm → Tìm nhóm mới**. Nút
**Sale đi tìm ngay** / **Xin vào nhóm ngay** chạy luôn không cần chờ giờ. Báo cáo sáng trên Telegram có chủ đề hôm nay.

**Lưu ý:** xin vào nhiều nhóm trong thời gian ngắn dễ bị Facebook hạn chế; nên giữ 1–2 nhóm/nick/ngày.

## Mai tìm khách sỉ (người đang bán hàng online)

Mục **Bán hàng → Tìm khách sỉ**. **Mục tiêu số 1 của Mai: tìm ra số điện thoại** của người đang bán hàng online để sếp liên lạc. Mai **tập trung Facebook**; TikTok và Shopee có công tắc riêng ở dòng **Nguồn tìm** đầu trang (đang hoạt động / không hoạt động, mặc định không hoạt động; cũng có thể nói với CEO “bật TikTok”, “tắt Shopee”).

**Điều kiện tìm khách sỉ của sếp** (trang Tìm khách sỉ, khung bên trái): sếp đặt điều kiện, Mai áp dụng cho mọi tài khoản tìm được và chấm lại các khách cũ ngay khi sếp lưu:
- **Bắt buộc phải có** ít nhất 1 chữ (VD ship, inbox): thiếu thì *Không đạt* (hạng D, không vào Khách hàng).
- **Loại ngay nếu có** (VD quần áo, mỹ phẩm): có là *Không đạt*.
- **Ưu tiên**: mỗi chữ khớp cộng điểm (mặc định 5, tối đa 20); **Khu vực ưu tiên** cộng thêm; **Ngành hàng phù hợp thêm**: khớp thì đủ điểm hợp ngành.
- Người theo dõi từ/đến, bài mới nhất trong N ngày, loại người bán bỏ qua (affiliate, KOC, cửa hàng truyền thống...).
- Hạng tối thiểu để vào mục Khách hàng (A, B hoặc C; vẫn phải có SĐT).
- **Cách tìm trên Facebook**: Trang, Bài viết, Bài viết gần đây, Mọi người; và **từ khóa** gõ vào ô tìm kiếm cho từng hướng.
- **Sếp dặn thêm**: lời dặn tự do, Mai đọc khi tìm và khi viết kịch bản.

Điều kiện được ghi vào sổ kiến thức của Mai và đưa vào lời dặn của Mai. Mỗi khách hiện rõ dòng “Đúng điều kiện của sếp” hoặc “Không đạt điều kiện của sếp: ...”.

**Sếp dạy Mai kỹ năng tìm kiếm Facebook** (khung bên phải, hoặc nhắn CEO “Dạy Mai: ...”): sếp viết như chỉ việc cho nhân viên, từ khóa để trong ngoặc kép, dùng chữ “ưu tiên”, “loại”, “bắt buộc phải có”; dán link nhóm để Mai đọc bình luận nhóm đó. Mai lưu nguyên bài dạy vào sổ kiến thức (nguồn: Sếp dạy), rồi tóm lại điều Mai hiểu: từ khóa, chữ phải có, chữ loại, ưu tiên, khu vực, cách tìm (VD “Bài viết gần đây”), nhóm cần đọc. Sếp xem và bấm **Áp dụng** thì các điều đó thành điều kiện tìm khách (từ khóa sếp dạy được tìm trước) và Mai chấm lại các khách đã tìm. Có khóa Claude thì Claude giúp Mai đọc bài dạy; chưa có thì Mai đọc theo mẫu câu.

**Đọc bình luận trong nhóm** (công tắc “Bình luận trong nhóm”): mỗi lượt Mai mở 3 nhóm trong danh sách Hội nhóm (nhóm lâu chưa đọc trước), lướt bài mới nhất, đọc cả bài và bình luận. Ai viết “tìm nguồn”, “cần nhập”, “xin giá sỉ”, “ai có nguồn” kèm tên hàng hợp ngành (trà, ngũ cốc, granola, đồ ăn healthy, thực phẩm) thì được lưu với đúng câu họ viết làm bằng chứng. Người chào bán sỉ (“nhận sỉ”, “cung cấp sỉ”, “tuyển đại lý”) là nhà cung cấp nên bỏ qua; bài của chính nick mình cũng bỏ qua. Họ tự ghi SĐT thì lấy luôn; người đang tìm nguồn trà, ngũ cốc tối thiểu hạng B, có SĐT thì hạng A. Chưa để SĐT thì việc tiếp theo là sếp/Hà trả lời bài hoặc nhắn tin xin SĐT bằng tay. Mai chỉ đọc, không bình luận, và không mở mục thông tin cá nhân của họ.

**Quét trang chạy quảng cáo** (công tắc “Trang chạy quảng cáo”): Mai mở Thư viện quảng cáo Facebook (Việt Nam, quảng cáo đang hoạt động), tìm theo từ khóa sản phẩm (sửa ở “Từ khóa hướng 5”), chỉ giữ quảng cáo hợp ngành, rồi mở trang của người chạy quảng cáo để tìm SĐT. Đang chạy quảng cáo bán hàng được tính ít nhất 16/20 điểm bán hàng; hotline ghi trong quảng cáo cũng được lấy.

**Cách Mai tìm SĐT**: đọc phần giới thiệu và các bài gần nhất của Trang (hotline, “Zalo 09...”, “liên hệ 09...”, nút gọi điện, link zalo.me); chưa thấy thì đọc thêm bài và mở **Giới thiệu → Thông tin liên hệ**; vẫn chưa có thì 3 ngày sau quay lại tìm (tối đa 3 lần). Số tìm được từ bài đăng công khai của chính họ trong kết quả tìm kiếm cũng được tính. Chỉ lấy SĐT kinh doanh do shop tự công khai.

**Có SĐT và đang bán hàng (hạng A/B/C, không phải affiliate)** → tự vào mục **Khách hàng** (tính vào KPI khách có SĐT) và **chuyển sếp qua Telegram ngay** bằng thẻ khách (SĐT, link trang, kịch bản tiếp cận, nút Đã gọi / Nhắc lại). Trang Tìm khách sỉ đưa khách có SĐT lên đầu, có bộ lọc “Chỉ khách có SĐT” và nút chép số.

Mai tìm người **đang bán hàng thật** có thể nhập trà túi lọc, ngũ cốc về bán lại: người livestream bán hàng, bán qua Facebook, TikTok, TikTok Shop, Shopee, bán đa nền tảng, đang tìm nguồn hàng hay tuyển đại lý. Cửa hàng truyền thống không thấy bán online thì xếp cuối. **Chất lượng quan trọng hơn số lượng**: mỗi người có link nguồn, bằng chứng, điểm và việc nên làm tiếp.

**Cách Mai làm mỗi lượt** (mặc định 14:30 mỗi ngày, hoặc bấm “Mai đi tìm ngay”, hoặc nói với CEO “tìm khách sỉ đang livestream bán trà”):

1. Mai mượn Chrome của một nick sale đang rảnh (luân phiên các nick) để mở trang công khai. Tìm trên Facebook theo 4 hướng, mỗi hướng 2 từ khóa đổi vòng mỗi ngày (sửa được trong “Cách Mai tìm và cài đặt”):
   - Hướng 1: người livestream bán trà, ngũ cốc, thực phẩm.
   - Hướng 2: người bán sản phẩm tương tự hoặc bổ trợ.
   - Hướng 3: người bán nhiều nhóm hàng tiêu dùng, có thể mở rộng danh mục.
   - Hướng 4: người công khai tuyển đại lý, tìm nguồn hàng, nhận phân phối, bán sỉ.
2. Facebook: tìm Trang và bài đăng công khai. TikTok, Shopee (chỉ khi sếp bật): mở trang tìm kiếm công khai; **gặp đăng nhập hay captcha thì dừng** và ghi “cần sếp xem tay” (không vượt qua cơ chế bảo vệ).
3. Mở từng tài khoản (mặc định tối đa 10/lượt), chỉ đọc phần giới thiệu và vài bài gần nhất: đang bán gì, bài mới nhất bao lâu, có tự phát trực tiếp không, link gian hàng ở nền tảng khác, SĐT/Zalo/email **kinh doanh được công khai trên trang**.
4. Phân loại riêng từng kiểu (không gộp): chủ shop tự nhập hàng, người bán livestream, bán đa nền tảng, nhà bán trên sàn, cộng tác viên, affiliate, KOC/KOL, cửa hàng truyền thống.
5. Kiểm tra trùng theo link, SĐT, tên; người đã có trong mục Khách hàng thì không đưa lại.
6. Chấm điểm, đề xuất sản phẩm của xưởng hợp với họ (ưu tiên sản phẩm đang bán chạy), viết kịch bản tiếp cận, ghi việc nên làm tiếp.
7. Có SĐT thì vào mục **Khách hàng** (nguồn “Tìm khách sỉ”) và chuyển sếp qua Telegram để **gọi/nhắn tay**.

**Thang điểm 100**

| Mục | Điểm | Mai cho điểm khi thấy |
|---|---|---|
| Hoạt động bán hàng | 20 | Chữ bán hàng trên trang: giá, inbox, ship COD, chốt đơn, combo, còn hàng... (bài cũ hơn 30 ngày thì giảm một nửa) |
| Livestream | 20 | Bài **của chính họ** “đang/đã phát trực tiếp” trong 7 ngày (20), trong 30 ngày (14), lâu hơn hoặc chỉ có lịch live (8) |
| Phù hợp ngành hàng | 20 | Trà, cà phê, ngũ cốc, đồ uống, healthy (20); thực phẩm, đồ ăn vặt, đặc sản (12); hàng tiêu dùng khác (5) |
| Khả năng tự nhập hàng | 15 | Nhập hàng, hàng mới về, kho, giá sỉ, tuyển đại lý/CTV, tìm nguồn hàng; có gian hàng riêng |
| Hoạt động và tương tác | 10 | Bài mới trong 3 ngày có bình luận; trang không bán hàng thì tối đa 3 |
| Khả năng liên hệ | 10 | SĐT kinh doanh (5), Zalo (3), email (2), nút nhắn tin (2) |
| Mở rộng sản phẩm | 5 | Bán nhiều nhóm hàng hoặc nhiều nền tảng |

Hạng **A** 80–100 (liên hệ trong 24 giờ), **B** 60–79 (theo dõi thêm rồi tiếp cận), **C** 40–59 (lưu theo dõi), **D** dưới 40 (không ưu tiên).

**Nguyên tắc Mai luôn giữ**: không tạo dữ liệu giả; mục nào không có chữ làm bằng chứng thì 0 điểm; không đoán số đơn hay doanh thu từ lượt xem; người chỉ xem hoặc chia sẻ livestream của người khác không phải người bán; affiliate chưa có bằng chứng tự nhập hàng thì không chào giá sỉ (chỉ hỏi thăm mô hình kinh doanh); không thu thập thông tin riêng tư; không vượt qua đăng nhập, captcha, giới hạn truy cập; **không tự nhắn tin**; kịch bản không hứa giá, chiết khấu hay chính sách (Claude chỉ được viết lại dựa trên bằng chứng).

**Sếp dán link**: dán link Facebook, TikTok, Shopee vào ô “Dán link để Mai phân tích” (hoặc gửi link cho CEO qua Telegram). Mai mở và chấm như trên; trang bắt đăng nhập thì ghi “cần sếp xem tay”.

Mỗi thẻ khách có nút: Chép kịch bản, Vào Khách hàng, Đã liên hệ, Kiểm tra lại, Loại. Mai cũng báo cáo số khách A/B tìm được trong cuộc họp sáng, và tự học các kiến thức tìm khách (phân biệt chủ shop với affiliate, dấu hiệu livestream thật...) lúc rảnh.

### Loại data rác: Mai ghi nhớ để lần sau tự loại

Ở mục **Khách hàng**, mở một khách rồi bấm **Loại bỏ: data rác, không hợp tệp khách**, chọn lý do (Không bán hàng online, Sai ngành hàng, Chỉ mua lẻ, Đối thủ / nhà cung cấp, Affiliate / KOC, Cửa hàng truyền thống, SĐT sai, Tài khoản ảo, Khác) và ghi chú nếu muốn. Trên Telegram, thẻ khách cũng có nút **🗑 Data rác**.

Khách bị loại biến khỏi danh sách và không tính vào KPI. Mai ghi nhớ như sau:
- **Chặn đích danh**: link trang, SĐT, tên tài khoản đó. Lần tìm sau Mai bỏ qua (báo cáo ghi “bỏ qua N tài khoản sếp đã đánh dấu data rác”). Người đó bình luận để lại SĐT cũng không được tạo lại.
- **Sai ngành hàng + ghi chú** (VD “bán mỹ phẩm, quần áo”): các ngành đó vào thẳng **Loại ngay nếu có** trong điều kiện tìm khách.
- **Affiliate / KOC, cửa hàng truyền thống**: sếp loại kiểu này từ 2 lần thì Mai bỏ qua luôn kiểu người bán đó.
- **Giống hệt data rác** (trùng trên 60% chữ): Mai loại.
- **Học chữ chung**: từ 3 khách rác trở lên, Mai so với các khách chưa bị loại để tìm chữ hay có ở data rác mà khách thường không có (VD “dropship”, “Quảng Châu”). Chữ thuộc ngành hàng của xưởng (trà, ngũ cốc, livestream, đại lý...) không bao giờ bị học thành chữ rác. Khách mới có các chữ này bị trừ 25 điểm. Thẻ **Mai ghi nhớ data rác** ở đầu trang Khách hàng liệt kê các chữ đó: bấm **Loại hẳn** để thêm vào điều kiện loại, hoặc **Bỏ qua** nếu chữ đó không phải dấu hiệu rác.

Mọi lần loại được ghi vào sổ kiến thức của Mai (“Data rác sếp đã loại”) và Mai chấm lại các khách đã tìm. Bấm **Data rác đã loại** để xem lại; bấm nhầm thì mở khách đó và bấm **Không phải rác, khôi phục**.

Chạy thật với TikTok, Shopee: hai nền tảng này thường bắt đăng nhập hoặc captcha với trình duyệt tự động, nên phần lớn tài khoản sẽ ở trạng thái “cần sếp xem tay”. Vì vậy mặc định tắt; khi tắt, link TikTok/Shopee sếp dán cũng không được mở.

## Sản phẩm và sản phẩm đang bán chạy

**Không công khai giá** (sếp chốt): sản phẩm không còn ô giá sỉ, giá bán lẻ. Mọi bài đăng, tin nhắn Hà soạn, kịch bản tiếp cận của Mai, bài chăm sóc nhóm đều không ghi giá hay mức lãi; khi nói tới giá chỉ ghi “💬 Giá vui lòng liên hệ trực tiếp Zalo 0386992326”. Phần mềm tự bỏ mọi dòng có giá (99k, 35.000đ/hộp, “Giá sỉ: …”) trước khi lưu bài và thêm câu mời liên hệ Zalo nếu bài chưa có. Lời dặn của mọi agent và chỉ đạo chung của CEO cũng ghi rõ quy định này. Số Zalo và câu mời liên hệ sửa ở **Cài đặt**.

Trang **Sản phẩm** là tài liệu bán hàng của cả đội:

- **Thêm sản phẩm** ở form cuối trang (tên, dòng, nhập tối thiểu, mô tả, điểm mạnh, thư mục ảnh).
  Không thêm được 2 sản phẩm trùng tên.
- **Sửa thông tin**: bấm ở thẻ sản phẩm, sửa trực tiếp rồi **Lưu thay đổi**. Agent dùng thông tin mới từ việc tiếp theo.
- **Xóa sản phẩm**: bấm 2 lần để xác nhận. Bài nháp và bài chờ đăng của sản phẩm đó bị bỏ theo; bài đã đăng vẫn giữ.

**🔥 Đang bán chạy:** bấm nút 🔥 trên thẻ (hoặc tích khi thêm/sửa, hoặc nhắn CEO "Bột ngũ cốc đang bán chạy, tập trung chào nhé",
"Thôi ưu tiên trà sen"). Có thể ghi thêm lưu ý khi chào (VD: "tặng 5 hộp khi nhập từ 100 hộp"). Khi có sản phẩm bán chạy:

- Lan viết khoảng **70% số bài** về các sản phẩm này (cài đặt `hot_share`), phần còn lại xoay vòng sản phẩm khác để không bỏ quên.
- Mọi agent nhận danh sách sản phẩm bán chạy và lưu ý của sếp trong lời dặn: Hà soạn tin và kịch bản tư vấn chào các sản phẩm
  này trước khi khách hỏi chung chung, Minh và CEO đề xuất trong họp.
- Tuấn up bài của sản phẩm bán chạy trước.
- Báo cáo sáng trên Telegram nhắc các sản phẩm đang đẩy.

## Ảnh sản phẩm: chọn ngẫu nhiên, không đăng trùng

Mỗi sản phẩm có **một thư mục ảnh riêng** trên máy chạy phần mềm (trang **Sản phẩm** → ô *Thư mục ảnh* → **Lưu**),
ví dụ `D:\AnhSanPham\Tra gung mat ong`. Bỏ vào đó bao nhiêu ảnh cũng được (JPG, PNG, WEBP, kể cả thư mục con).

Khi đăng bài, nhân viên sale chọn **ngẫu nhiên 2–4 ảnh** (chỉnh ở **Cài đặt → Nhân viên sale đăng bài**) trong thư mục
của đúng sản phẩm bài đó, theo thứ tự ưu tiên:

1. Không dùng lại ảnh đã đăng ở **cùng nhóm** trong 14 ngày.
2. Không dùng lại ảnh mà **cùng nick** đã đăng trong 14 ngày.
3. Ảnh **chưa đăng lần nào** trước, rồi tới ảnh lâu chưa dùng nhất; thứ tự ảnh trong bài cũng ngẫu nhiên.

Mọi lần dùng ảnh (đăng bài và up bài) đều được ghi lại. Nếu thư mục ít ảnh tới mức không còn ảnh mới, sale nới dần điều
kiện thay vì đăng không ảnh, và nhật ký báo "Thiếu ảnh mới" để bạn bổ sung. Trang Sản phẩm cho biết mỗi thư mục còn bao
nhiêu ảnh chưa đăng và đủ cho khoảng bao nhiêu bài nữa. Thẻ bài ở mục **Bài đăng** hiện đúng các ảnh đã đăng kèm.

Sản phẩm chưa có thư mục riêng sẽ dùng thư mục chung (Cài đặt → Tự động up bài): thư mục con trùng tên sản phẩm,
hoặc ảnh để thẳng trong thư mục chung.

**Ảnh tổng hợp nhà máy**: ở trang Sản phẩm, mỗi sản phẩm có ô **Ảnh tổng hợp nhà máy**. Tạo một mục (VD “Tổng hợp sản
phẩm nhà máy”), điền thư mục chứa ảnh tổng hợp các sản phẩm của nhà máy, rồi tích ô đó: từ giờ **mọi bài đăng** (và ảnh
bình luận up bài) chỉ lấy ngẫu nhiên ảnh trong thư mục này, không lấy ảnh ở các sản phẩm khác nữa. Vẫn áp dụng các quy
tắc chống trùng ở trên. Chỉ tích được 1 mục: tích mục khác thì mục cũ tự bỏ tích. Mục tổng hợp chưa có ảnh thì bài không
đăng (không quay về dùng ảnh sản phẩm khác). Bỏ tích thì bài lại lấy ảnh theo đúng sản phẩm của bài. Đầu trang Sản phẩm
luôn ghi bài đăng đang lấy ảnh ở đâu.

**Bắt buộc có ảnh** (Cài đặt → Nhân viên sale đăng bài, mặc định bật): bài không có ảnh thì **không đăng lên Facebook**,
ở mọi đường đăng (hội nhóm, nhóm mình quản lý, trang cá nhân, Fanpage):
- Tuấn không xếp lịch bài thiếu ảnh. Bài nằm lại cột Đã duyệt với dòng đỏ “Bài chưa có ảnh nên không đăng: ...” chỉ rõ
  cần điền thư mục ảnh ở đâu, và chip **📷 Thiếu ảnh, không đăng**. Đầu trang Bài đăng báo số bài thiếu ảnh; nút
  Đăng ngay, Đăng thử, Đăng Fanpage được thay bằng **Thêm ảnh sản phẩm**. Có ảnh rồi thì Tuấn tự xếp lại các bài đó.
- Bài mẫu sỉ và bài chăm sóc nhóm quản lý (không gắn sản phẩm) lấy ảnh ở thư mục chung; chưa có thư mục chung thì Lan
  không làm thêm các bài này.
- Lúc đăng, sale chọn ảnh trước khi mở hộp soạn bài; không chọn được ảnh thì không mở.
- Sale đính ảnh **như người thật**: bấm nút **Ảnh/video** (hoặc ô “Thêm ảnh/video” hiện ra sau đó), chọn ảnh trong hộp
  chọn tệp của Facebook, rồi **chờ ảnh xem trước hiện trong bài** và chờ tải lên xong mới bấm Đăng. Không dùng các ô chọn
  tệp ẩn có sẵn trong hộp soạn bài (Facebook có ô ẩn không gắn với ảnh bài, chọn vào đó bài lên không có ảnh).
- Ảnh không hiện trong bài thì sale **hủy bài đang soạn, không bấm Đăng**, chụp lại hộp soạn bài, trả bài về hàng chờ và
  báo ở màn Lỗi (“Facebook không nhận ảnh nên chưa đăng bài”). Cùng một bài bị 2 lần thì dừng hẳn bài đó (cột Lịch đăng,
  trạng thái lỗi, có ảnh chụp); sửa xong bấm **Đưa về hàng đợi**.
- Up bài bằng bình luận ảnh cũng vậy: ảnh không hiện trong ô bình luận thì không gửi.
- Fanpage: ảnh được tải lên trước rồi gắn vào bài (Graph API `photos` + `attached_media`); không có ảnh thì không gọi API.
- Thẻ bài chưa đăng hiện **📷 N ảnh** là số ảnh sẵn để đính kèm.

Bỏ chọn “Bắt buộc có ảnh” nếu muốn cho phép đăng bài chỉ có chữ như trước.

## Lưu link bài và tự động up bài

**Link bài (bắt buộc lưu):** mỗi bài đăng phải có link thật trên Facebook (đã bỏ phần theo dõi `__cft__`). Sale lấy link
theo thứ tự:
1. **Phản hồi của Facebook lúc bấm Đăng**: Facebook trả về link hoặc mã bài vừa tạo; sale đọc ngay, không cần tìm.
2. **Bài trên trang đang mở**: bài mới thường hiện đầu bảng tin nhóm. Sale nhận ra bài theo 2 đoạn chữ đầu, tìm được cả
   khi bài không có `role="article"` (giao diện Facebook mới), và **rê chuột lên mốc thời gian** vì Facebook chỉ gắn link
   thật vào đó khi rê chuột.
3. **Nội dung của bạn** trong nhóm (`/my_posted_content`, `/my_content/posted`), bảng tin nhóm, hoặc trang cá nhân.
4. **Bài chờ quản trị viên duyệt**: ghi “Bài chờ nhóm duyệt” (lưu sẵn link nếu Facebook đã trả mã bài), 3 giờ một lần
   sale xem lại, bài hiện thì chuyển thành “Đã lưu link”. Theo dõi tối đa 3 ngày.

Chưa tìm thấy thì sale **tự thử lại** sau 20 phút, 2 giờ, 6 giờ, 12 giờ, 24 giờ (trong ca làm việc của nick đã đăng).
Thẻ bài ghi lý do và giờ thử lại; nút **Lấy link ngay** cho sale đi tìm luôn. Thử hết lượt vẫn không được thì màn **Lỗi**
báo “Không lưu được link bài #...”: mở bài trên Facebook, bấm vào giờ đăng (VD “2 giờ”), chép link dán vào thẻ bài.
Ô dán link chỉ nhận link bài viết (có `/posts/`, `/permalink/`, `story_fbid`...), dán nhầm link nhóm sẽ bị báo. Đầu
trang **Bài đăng** báo số bài đã đăng chưa lưu được link. Facebook đổi chữ báo chờ duyệt thì thêm vào `pending_texts`
trong `backend/fb_selectors.json`.

**Up bài hằng ngày:** vào **Cài đặt → Tự động up bài**, chọn thư mục ảnh trên máy chạy phần mềm rồi bấm
*Kiểm tra thư mục*. Từ giờ đã chọn (mặc định 19:30), mỗi nhân viên sale vào lại các bài chính mình đã đăng trong
7 ngày gần nhất và bình luận một ảnh sản phẩm.

**Bảo (Chăm sóc bài đã đăng) phụ trách up bài:** mỗi ngày Bảo rà soát các bài đã đăng (còn hiển thị, đăng trong số ngày đã
chọn, đã đăng hơn 10 giờ, chưa up hôm nay; bài bị nhóm gỡ thì ngừng), xếp cho đúng nick đã đăng vào bình luận **1 ảnh bất kỳ
trong thư mục ảnh** (ưu tiên ảnh ít dùng, không lặp ảnh trên cùng bài) kèm:
- **một câu ngắn Bảo tự viết** cho từng bài theo sản phẩm của bài (VD “Mẻ trà gừng mật ong túi lọc sáng nay vừa đóng thùng”).
  Có khóa Claude thì Bảo gọi Claude viết cả lượt trong một lần; chưa có thì ghép từ mẫu có sẵn. Mỗi bài một câu, khác các câu
  nick đã dùng 14 ngày qua (Facebook coi bình luận giống hệt lặp lại là spam), không hứa chữa bệnh, câu tự ghi số điện thoại bị bỏ;
- **dòng liên hệ của sếp** luôn gắn cuối, mặc định “Cần hàng liên hệ Zalo 0386992326”, VD:
  “Mẻ trà gừng mật ong túi lọc sáng nay vừa đóng thùng. 👉 Cần hàng liên hệ Zalo 0386992326”.

**Bảo tự học để không phải gọi Claude mãi.** Mỗi câu Claude viết được lưu làm **câu mẫu**. Bảo tách câu mẫu thành khuôn câu
(thay tên sản phẩm bằng chỗ trống) và hai vế trước / sau dấu phẩy, rồi tự ghép câu mới cùng giọng cho sản phẩm của từng bài.
Trong lúc học, mỗi lượt Bảo nộp vài câu tự viết để Claude **chấm điểm 1–10 ngay trong cùng lần gọi** (không tốn thêm lượt gọi).
Tay nghề:

| Tay nghề | Câu mẫu Claude | Câu tự viết đã chấm | Đạt từ 8 điểm (40 câu gần nhất) |
|---|---|---|---|
| Học việc | – | – | – |
| Thạo việc | 20 | 10 | 60% |
| Giỏi | 50 | 20 | 80% |
| **Master** | 100 | 40 | 90% |

Đạt **Master** thì Bảo tự viết toàn bộ, **không gọi Claude nữa** (đếm số lần gọi đã bớt). Câu tự viết vẫn qua bộ lọc: không trùng
câu nick dùng 14 ngày qua, không hứa công dụng. Chưa có khóa Claude thì Bảo tự viết từ những gì đã học (chưa học thì dùng mẫu
gốc). Thấy câu tự viết chưa ổn, bấm **Cho Bảo học lại**: điểm chấm xóa, Bảo gọi Claude và được chấm lại từ đầu, mẫu đã học
vẫn giữ. Tay nghề, số lần gọi Claude và các câu mẫu gần đây hiện ngay trong ô Tự động up bài.

**Đính ảnh vào bình luận:** sale ghim đúng ô soạn bình luận (không nhầm chữ mờ “Viết bình luận…”) và khung bình luận chứa nó,
rồi chỉ đính ảnh trong khung đó: đặt tệp thẳng vào ô tệp của khung, không được thì bấm nút “Đính kèm (một) ảnh hoặc video” trong
khung, cuối cùng mới tìm nút đính kèm của bình luận trên cả trang (không bao giờ dùng nút “Ảnh/video” của hộp đăng bài). Mỗi cách
chờ ảnh xem trước tới 30 giây; ảnh không hiện thì không gửi, báo lỗi ghi rõ đã thử những cách nào. Ảnh thường mất 10–20 giây
mới tải lên: sale chờ **nút gửi (mũi tên) sáng lên** và hết thanh tiến trình (tối đa 90 giây), rồi **bấm nút mũi tên** để gửi
(không thấy nút thì chờ đủ 20 giây và nhấn Enter). Gửi xong sale kiểm tra ô bình luận đã trống; chữ vẫn còn thì thử lại một lần,
vẫn không đi thì báo lỗi chứ không ghi là đã up. Lượt up lỗi được thử lại
khi bấm **Up bài ngay** hoặc nhắn CEO “rà soát lại các bài đã đăng”.

Chỉnh ở **Cài đặt → Tự động up bài · Bảo phụ trách**: ô *Dòng liên hệ*, chọn *Bảo tự viết* hoặc *Chọn ngẫu nhiên từ danh sách*,
nút **Xem thử câu Bảo viết** (chưa gửi). Nhắn CEO cũng được: “rà soát lại các bài đã đăng và comment ảnh kèm zalo” (Bảo xếp
ngay), “từ nay đổi zalo liên hệ thành 09xxxxxxxx”. Số lượt mỗi nick/ngày vẫn theo Luật Facebook (mặc định 6 lượt up/nick/ngày).

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

**Từ SĐT tới đơn hàng (đo tới khách mua, không chỉ tới số điện thoại):** KPI đếm SĐT, nhưng thứ cần là đơn hàng. Thẻ
**Từ SĐT tới đơn hàng** ở trang KPI & Báo cáo cho từng kênh (bình luận dưới bài mình, người hỏi nguồn trong nhóm, trang chạy quảng
cáo, trang / shop livestream, link sếp dán, sếp nhập tay): số khách → có SĐT → sếp đã gọi → chốt đơn → không mua → doanh thu, kèm
**chi phí AI mỗi SĐT và mỗi đơn** (7 / 30 / 90 ngày).

- **Khách không mua phải có lý do**: Không nghe máy / sai số, Sai tệp (không bán online, chỉ mua lẻ), Đã có nguồn hàng, Chê số lượng
  nhập tối thiểu, Chê giá, Không hợp sản phẩm, Hẹn để sau, Lý do khác. Trên Telegram, bấm **❌ Không mua** thì phiếu khách hiện ngay
  các nút lý do; ở trang Khách hàng, chọn trạng thái “Không mua” thì hiện hộp chọn lý do (ghi thêm được). Khách chưa ghi lý do
  được nhắc ở thẻ phễu và báo cáo tối.
- **Cả đội học từ lý do**: từ 3 khách không mua có lý do (60 ngày), kết quả gọi khách và lý do (kênh nào nhiều nhất) được đưa vào lời
  dặn của Mai, Lan, Hà, CEO, Minh, kèm việc mỗi người nên làm khác đi: VD “Sai tệp” → Mai đòi bằng chứng đang bán online, Lan nói rõ
  bài dành cho người bán lại; “Chê số lượng nhập tối thiểu” → Lan ghi rõ mức nhập, Hà hỏi sức bán trước; “Đã có nguồn” → Hà đề nghị
  gửi mẫu so sánh. Chỉ đổi cách làm, không đổi quy định giá của sếp.
- Báo cáo tối trên Telegram có dòng **Từ SĐT tới đơn hàng** 7 ngày: SĐT → sếp gọi → chốt, chi phí AI mỗi đơn, kênh ra đơn nhiều
  nhất, 3 lý do không mua hay gặp.

**Dồn sức vào kênh ra đơn** (thẻ ngay dưới phễu, trang KPI & Báo cáo): mỗi tuần (thứ Hai, sau 08:00) CEO xem 14 ngày gần nhất
của từng kênh tìm khách và chỉ kết luận khi **đủ dữ liệu thật**: kênh có từ 8 SĐT và sếp đã gọi từ 5 khách.

| Kết quả | CEO làm |
|---|---|
| ✅ Ra đơn (từ 1 đơn) | Dồn thêm sức trong giới hạn an toàn: Mai đọc thêm 1 nhóm mỗi lượt (tối đa 6), xem thêm 3 trang mỗi lượt (tối đa 20), thêm từ khóa quét quảng cáo (tối đa 4) |
| ⛔ Đủ cuộc gọi mà 0 đơn | **Tạm dừng kênh 30 ngày** rồi tự chạy lại để thử lại; vừa chạy lại thì chờ đủ dữ liệu mới, không dừng ngay vì số liệu cũ |
| 📞 Có SĐT nhưng sếp gọi chưa đủ | Nhắc sếp gọi thêm và bấm Đã gọi / Chốt đơn / Không mua, chưa kết luận |
| ⏳ Chưa đủ SĐT | Chờ thêm |

- Kênh dừng / dồn sức được: người hỏi nguồn trong nhóm (Mai đọc bình luận), trang chạy quảng cáo, trang / shop livestream (Mai tìm theo
  4 hướng). **Đăng bài nhóm không bao giờ tự dừng**: kênh này chưa ra đơn thì CEO chỉ báo để sếp xem lại nội dung bài và nhóm đăng.
- Theo quyền của CEO: *CEO tự quyết* thì làm luôn và báo Telegram; *Chờ sếp duyệt* thì thành đề xuất có nút **Duyệt / Không**
  (trên thẻ, trang Công ty và Telegram). Kênh đang dừng có nút **Chạy lại**. Bấm **CEO xem lại ngay** hoặc nhắn CEO “kênh nào ra đơn”,
  “dồn sức vào kênh ra đơn”. Tắt việc xem hằng tuần bằng ô **Mỗi tuần CEO tự xem lại**.

**Kết nối Telegram (5 phút):**

1. Trên Telegram, nhắn **@BotFather** → `/newbot` → đặt tên → nhận token.
2. Phần mềm → **Cài đặt → Bot Telegram** (hoặc **KPI & Báo cáo**) → dán token → **Kiểm tra và lưu** → **Tạo mã ghép nối**.
   Phần mềm hỏi Telegram trước khi lưu: token sai dạng, sai hoặc bot đã bị xóa thì báo ngay, không lưu. Token chỉ hiện dạng che
   (`123456789:…abcd`). Đổi sang bot khác thì phải ghép nối lại; **Xóa token** để ngừng gửi Telegram.
3. Mở bot vừa tạo, gửi mã 6 số. Bot trả lời "Đã kết nối". Chỉ chat đã ghép nối mới nhận báo cáo và ra lệnh được.

Bot chạy ngay trên máy của bạn (không cần tên miền hay mở cổng). Máy phải bật và có Internet thì bot mới trả lời.

**Báo cáo tự động:**

| Lúc | Nội dung |
|---|---|
| 09:00 | KPI hôm qua, chuỗi ngày đạt KPI, mục tiêu hôm nay, lịch đăng, kết luận và việc giao trong cuộc họp sáng, nick cần xử lý |
| Ngay khi có | Phiếu khách cần sếp tư vấn, nick bị checkpoint/đăng xuất |
| Khoảng mỗi phút | **Mọi việc vừa hoàn thành**, gom thành một tin: sale đăng bài (kèm link bài), đăng thử, up bài, xong ca trên nick, quét bình luận, tìm nhóm, xin vào nhóm, nick đăng nhập xong; Lan viết bài; Tuấn xếp lịch, thêm nhóm, đăng Fanpage; Hà soạn tin, khách mới; Khoa báo cáo, cả đội tự học; kết thúc họp; CEO duyệt bài, chọn chủ đề, sửa agent, tuyển/sa thải |
| Khi CEO làm xong việc sếp giao | Lời CEO báo lại, kể cả việc sếp giao trên phần mềm (không chỉ việc giao qua Telegram) |
| 15:00 | Cảnh báo nếu KPI đang chậm |
| Khi đạt | Chúc mừng đạt KPI tối thiểu, vượt KPI |
| 21:30 | KPI cả ngày theo từng nick, khách còn chờ sếp gọi, đơn đã chốt, bài học mới, chi phí AI |

Tắt báo việc xong ở **Cài đặt → Bot Telegram** nếu thấy nhiều tin (báo cáo sáng/tối, khách và cảnh báo vẫn gửi).
Việc chính sếp vừa bấm trên phần mềm (duyệt bài, tự đánh dấu đã đăng) không báo lại.

**Lệnh Telegram:** `/baocao` báo cáo nhanh · `/kpi` tiến độ · `/khach` khách đang chờ sếp · `/congty` vốn, chi phí nuôi agent, doanh thu, tình trạng sale · `/doanhthu 2tr5 Tên khách` nhập doanh thu · `/ceo` nhân sự, mốc doanh thu, tiềm năng · nhắn tin thường = giao việc cho CEO · `/hop [chủ đề]` triệu tập họp
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

1. **Thống kê (không tốn AI), không học từ số ít:** điểm mỗi bài = khách × 5 + bình luận, làm mượt mạnh (coi như mỗi lựa chọn
   đã có 10 bài ở mức trung bình). Một góc viết, sản phẩm, giờ đăng chỉ được coi là tốt / kém hơn khi **mỗi bên có từ 15 bài**
   và **chênh lệch rõ, khó là may rủi** (kiểm định thống kê, mức tin cậy ~95%); nhóm đăng từ 5 bài mỗi nhóm. Chưa đủ **40 bài đã
   đăng trong 30 ngày** thì Lan thử đều các góc, Tuấn chưa có “giờ vàng”. Bài học thống kê ghi kèm số bài và độ chênh (z). Số liệu
   không còn đủ chứng minh thì bài học tự bị bỏ. Hà cần từ 10 tin có kết quả mới rút tỉ lệ chốt; sếp sửa từ 5 lần mới rút thói
   quen độ dài. Trang Đào tạo báo “Mới N/40 bài, chưa đủ dữ liệu” để sếp biết đội đang thử chứ chưa kết luận. Chỉnh ngưỡng bằng
   các cài đặt `learn_min_each`, `learn_min_total`, `learn_z`.
2. **Ví dụ mẫu:** bài nhiều khách nhất, bản sếp đã sửa và tin nhắn đã chốt đơn được đưa vào prompt để agent học cách viết.
3. **Phản tỉnh bằng Claude mỗi tuần** (mặc định 7 ngày, chạy cùng lượt tự học 23:15): mỗi agent đọc số liệu (có số bài mỗi mục),
   ghi tối đa 2 bài học mới có bằng chứng, bỏ bài học không còn đúng. Claude được dặn không kết luận từ mục dưới 15 bài hay từ 1–2
   khách. Các đêm khác chỉ chạy luật thống kê và đặt mục tiêu ngày mai (không tốn AI). Không có API key thì vẫn học bằng thống kê.

Sổ tay giữ tối đa 10 bài học đang dùng mỗi agent (bài ghim không tính); 6 bài quan trọng nhất được đưa vào prompt.
Sếp có thể **dạy trực tiếp** (bài học được ghim), **ghim** hoặc **bỏ** bất kỳ bài học nào.

**Kinh nghiệm và cấp độ:** agent nhận điểm kinh nghiệm khi bài được duyệt, được đăng, có khách, khách chốt đơn,
rút ra bài học… Cấp độ hiện trên nhân vật 3D. Trang Đào tạo so sánh kỹ năng tuần này với tuần trước
(tỉ lệ bài duyệt ngay, khách mỗi bài, tỉ lệ đăng thành công, tỉ lệ chốt…).

**Ranh giới:** bài học chỉ thay đổi cách viết và cách chọn góc, sản phẩm, nhóm, giờ đăng. Giới hạn bài/ngày, giãn cách,
luật nhóm và việc dừng khi checkpoint là do sếp đặt; bài học đề xuất tăng tần suất, lách luật hay hứa công dụng chữa
bệnh bị tự động loại.

## Kho bài và phong cách viết: Lan học để tự viết content

- **Lưu toàn bộ bài Claude viết** vào kho bài (bảng `content_library`), ghi rõ agent chịu trách nhiệm (Lan), sản phẩm, góc viết,
  nơi đăng. Kho không bị xóa khi "Bắt đầu chạy thật". Bài sếp sửa rồi lưu cũng vào kho (nguồn "Sếp sửa", học nặng hơn).
  Bài cũ do Claude viết trước bản này được tự đưa vào kho; bài mẫu có sẵn của phần mềm thì không.
- **Ghi nhớ phong cách**: mỗi bài được tách thành câu mở đầu, ý lợi ích, dòng giá, dịch vụ xưởng, câu kêu gọi, đoạn kể chuyện,
  hashtag. Tên sản phẩm, giá, nhập tối thiểu, dòng sản phẩm được thay bằng chỗ trống để dùng cho sản phẩm khác; câu nhắc
  riêng một loại hàng chỉ dùng lại cho đúng sản phẩm đó; dòng mô tả/điểm mạnh sản phẩm thì lấy từ trang Sản phẩm.
  Câu ở bài được duyệt, có bình luận, có khách được cộng điểm; bài bị loại bị trừ điểm (cập nhật mỗi đêm).
  Hồ sơ phong cách: độ dài, số dòng, emoji hay dùng, gạch đầu dòng, hashtag; được nhắc lại khi Claude viết để giữ đồng nhất.
- **Tự viết**: đủ vốn (mặc định 12 bài Claude viết, 4 câu mở đầu, 2 câu kêu gọi) thì Lan tự ghép bài mới không gọi Claude,
  chọn câu theo góc viết và điểm, không trùng bài cũ (bài quá giống thì để Claude viết).
  - **Tự động** (mặc định): tỉ lệ tự viết tăng dần theo số bài đã học (tối đa 80%), giảm nếu bài tự viết bị loại nhiều hơn bài
    Claude viết; bài có yêu cầu riêng của sếp vẫn nhờ Claude. Chưa có khóa Claude: tự viết khi đủ vốn.
  - **Luôn tự viết** / **Tắt**.
- Trang **Đào tạo → Lan học phong cách viết**: số bài đã lưu, tiến độ học, tỉ lệ tự viết, so sánh tỉ lệ duyệt và khách giữa bài
  Claude viết và bài Lan tự viết, câu mở đầu và câu kêu gọi hay dùng, kho bài, nút **Lan viết thử 1 bài** (xem trước, không lưu).
  Thẻ bài ở mục Bài đăng ghi "Lan tự viết" / "Claude viết" / "Sếp sửa".

## Sổ kiến thức: chỉ học từ dữ liệu thật, ít phụ thuộc Claude

Ngoài bài học rút từ kết quả (phần trên), mỗi agent có **sổ kiến thức** (trang **Đào tạo → Sổ kiến thức của đội**).

**Chỉ dùng kiến thức có dữ liệu thật.** Lời dặn khi agent làm việc và câu Hà tự trả lời khách chỉ lấy từ: **điều sếp dạy**
(kể cả bài mẫu, điều kiện tìm khách, data rác, bài học duyệt bài), **luật Facebook**, **câu sếp và khách hỏi thật** (Claude trả lời
rồi lưu lại) và kinh nghiệm thật. Kiến thức chung do Claude tự viết từ hiểu biết chung (“Tự học”) và thư viện viết sẵn (“Thư viện có
sẵn”) **không được đưa vào lời dặn**: chúng không có thông tin mới của xưởng, dễ đưa lời khuyên chung chung vào bài. Trang Đào tạo vẫn
hiện các mục này với nhãn **Không dùng khi làm việc** để sếp xóa hoặc xem lại.

1. **Mỗi ngày trả lời câu còn chờ** (mặc định 07:00): câu sếp hỏi mà đội chưa biết và câu khách hỏi thật trong 7 ngày (Hà).
   Có khóa Claude: mỗi agent có câu chờ thì 1 lần gọi Haiku. Không có câu chờ thì không gọi.
2. **Tra sổ trước khi làm**: khi viết bài, soạn tin, tư vấn, họp, kiến thức liên quan được đưa vào lời dặn của agent.
3. **Biết rồi thì tự trả lời, không gọi Claude**: Hà gặp câu khách đã từng hỏi (VD "nhập nhiều có chiết khấu không?") thì tự
   soạn tin từ sổ; sếp hỏi CEO điều đội đã biết thì CEO trả lời ngay từ sổ.
4. **Chưa biết mới hỏi Claude, và luôn lưu lại**: mỗi lần hỏi Claude, câu trả lời dùng lại được được ghi vào sổ (Hà soạn tin
   thì rút ra câu hỏi chung của khách và cách trả lời). Chưa có khóa thì câu hỏi được ghi vào "Câu chờ học" để học sau.

**Tự học kiến thức chung với Claude** (giáo trình theo vai trò, học lúc rảnh): **mặc định tắt**, bật ở Đào tạo → Sổ kiến thức →
Cài đặt nếu muốn. Bật thì các mục “Tự học”, “Thư viện có sẵn” lại được đưa vào lời dặn. Nhắn CEO “cho cả đội học thêm kiến
thức” khi đang tắt: CEO cho đội trả lời các câu còn chờ và nhắc sếp dạy trực tiếp.

Trang Đào tạo cho biết: số kiến thức, số học hôm nay, số lần tự trả lời bằng sổ và số lần phải hỏi Claude trong 30 ngày,
**tỉ lệ tự lực**. Sếp hỏi đội ngay ở ô **Hỏi**, tìm, lọc theo agent, xóa kiến thức sai, **dạy kiến thức** mới (tích "trả lời
khách" để Hà tự dùng khi khách hỏi đúng ý đó). Trên Telegram: hỏi CEO bằng câu hỏi (VD "Khách chê giá cao thì trả lời sao?"),
hoặc nhắn "Cho cả đội học thêm kiến thức". Kiến thức học mỗi ngày được báo trong tin "Việc vừa hoàn thành".

## Văn phòng: agent luôn làm việc hoặc học để lên cấp

Trang **Văn phòng** chỉ có văn phòng 3D và cột **Đội đang làm gì**: mỗi agent (cả nhân viên sale) hiện trạng thái
Đang làm / Đang học / Đang họp, việc đang làm, cấp độ và thanh kinh nghiệm tới cấp sau, số kiến thức học hôm nay và
2 việc vừa xong. Ô giao việc cho CEO, KPI hôm nay và nhật ký chuyển sang trang **Giao việc**.

Agent không bao giờ ngồi không. Mỗi 30 giây, agent nào không có việc thật (và không đang họp) tự vào một buổi 6–12 phút:

1. **Học với Claude** (Haiku): **chỉ khi bật “Tự học kiến thức chung”** (mặc định tắt, xem Sổ kiến thức). Tối đa 6 buổi/agent/ngày,
   cách nhau ít nhất 45 phút; mỗi kiến thức mới lưu vào sổ, **+5 kinh nghiệm**.
2. **Luyện tập** không tốn tiền: Lan luyện viết bài theo phong cách đã học, Hà luyện trả lời câu khách hay hỏi, Tuấn xem lại
   nhóm cần cân nhắc, Khoa xem số liệu, sale ôn cách giữ nick: **+2 kinh nghiệm**, tối đa 10/ngày.
3. **Ôn lại** kiến thức trong sổ: **+1 kinh nghiệm**, tối đa 10/ngày.

Việc thật luôn được ưu tiên: có việc là agent chuyển sang làm ngay. Kinh nghiệm từ học có giới hạn mỗi ngày, nên muốn lên cấp
nhanh vẫn phải làm ra kết quả (bài được duyệt, khách, đơn). Báo cáo tối trên Telegram có số kiến thức cả đội học trong ngày và
ai lên cấp. Luyện tập và ôn lại không tốn tiền; bật học với Claude thì khoảng 0,02 USD/ngày cho 7 agent × 6 buổi.

## Công ty: vốn, sa thải, giải thể

Trang **Công ty** quản lý vốn, chi phí nuôi agent, doanh thu và luật sống còn. Bấm **Thành lập công ty** (mặc định vốn 10.000.000đ)
để bắt đầu tính luật; nên chạy **Bắt đầu chạy thật** trước (có ô "thành lập công ty ngay sau khi dọn").

**Luật:**

1. **Sa thải sale theo KPI tháng.** Mỗi nhân viên sale giữ nick có kỳ đánh giá 30 ngày. Chỉ tiêu kỳ = tổng chỉ tiêu
   các ngày nick thật sự làm việc (đã đăng nhập, không bị sếp tạm dừng); mỗi ngày chỉ tiêu của một nick bằng KPI tối thiểu
   của phòng chia đều cho số nick đang chạy. Cuối kỳ, số **khách để lại SĐT** từ bài của nick phải đạt chỉ tiêu, không thì
   bị **sa thải**: nick dừng đăng, bài trong lịch trả về hàng chờ. Kỳ có dưới 15 ngày làm việc (nick lỗi, sếp tạm dừng) thì
   được kéo dài thay vì đánh giá. 7 ngày đầu kỳ là thời gian làm quen. Đạt thì sang kỳ mới và được +100 kinh nghiệm.
   Ngày 20 của kỳ, nếu đang dưới chỉ tiêu, Telegram báo trước cho sếp.
2. **Sa thải hết sale → giải thể.**
3. **60 ngày không có khách chốt đơn và doanh thu → giải thể.** Telegram nhắc ở giữa kỳ, còn 15 ngày và còn 5 ngày.
   Chỉ cần 1 đơn có doanh thu là qua luật này.
4. **Vốn chỉ dùng để nuôi các agent:** chi phí gọi API Claude khi agent viết bài, họp, tư vấn, trả lời khách, tự học.
   Phần mềm tự tính từ mỗi lần gọi API và quy đổi từ USD (tỷ giá nhập lúc thành lập, mặc định 25.800đ/USD). Chi phí hàng
   hóa, giao hàng của đơn không tính ở đây. Ảnh sản phẩm lấy từ thư mục ảnh của sếp nên không tốn phí (phần mềm không gọi
   API tạo ảnh). Trang Công ty chia chi phí theo từng việc, biểu đồ 7 ngày và dự báo vốn còn đủ bao lâu. Còn 20% vốn
   Telegram báo; hết vốn thì mọi việc gọi AI dừng tới khi **bơm thêm vốn**.
5. **Đội lõi** (CEO Đức, Minh, Lan, Tuấn, Hà, Khoa) không bị sa thải theo KPI; chỉ giải tán khi công ty giải thể.

**Doanh thu do sếp nhập** (sếp là người chốt và làm việc với khách), ở một trong các chỗ:

- Trang **Công ty → Nhập doanh thu**: số tiền, tên hoặc SĐT khách (không bắt buộc; trùng khách trong danh sách thì tự gắn).
- Telegram: `/doanhthu 2tr5 Shop Mộc An`, hoặc bấm **Chốt đơn** trên phiếu khách rồi trả lời số tiền.
- Trang **Khách hàng**: chọn trạng thái "Đã nhập hàng" và nhập số tiền.

Số tiền viết kiểu `2500000`, `2.500.000`, `2,5tr`, `2tr5`, `800k` đều được. Nhập nhầm thì bấm **Xóa** hai lần. Lệnh `/congty` xem nhanh vốn,
chi phí nuôi agent, doanh thu và tình trạng từng sale.

**Sale bị sa thải:** nick và phiên đăng nhập vẫn giữ. Ở trang Công ty, nhập tên người thay → **Tuyển thay, giữ nick**:
sale mới nhận toàn bộ các nick, hội nhóm của các nick cũ và bắt đầu kỳ KPI mới.

**Sau khi giải thể:** sale dừng đăng, AI dừng, văn phòng 3D đóng cửa. Dữ liệu vẫn còn để xem lại; có thể **Thành lập lại**
với vốn mới.

## Luật: sếp chỉ giao việc cho CEO

Mặc định bật (tắt/bật ở trang Công ty → khung CEO). Sếp không giao việc trực tiếp cho Minh, Lan, Tuấn, Hà, Khoa hay các
sale nữa: các nút giao việc trực tiếp được ẩn, thay bằng khung **Giao việc cho CEO Đức** ở Văn phòng. Trên Telegram, nhắn
tin bình thường (không cần lệnh) là giao việc cho CEO.

**CEO tự làm:**

- Hiểu lời sếp và chia việc: viết bài (Lan), xếp lịch (Tuấn), họp, tìm nhóm và xin vào nhóm, quét bình luận, tạm dừng/bật
  lại nick, đổi một số cài đặt (số bài/ngày, KPI, giờ quét, giờ họp…), tuyển thêm hoặc cho sale nghỉ khi sếp nói rõ,
  báo cáo tình hình. Mỗi lần CEO trả lời rõ đã làm những gì.
- **Sửa agent làm sai:** sếp nói "Lan viết bài dài quá, viết dưới 150 chữ" → CEO ghi thành bài học bắt buộc (ghim) trong sổ
  tay của Lan, áp dụng từ bài tiếp theo.
- **Chỉ đạo lâu dài:** "Từ nay bài nào cũng nhắc giao hàng toàn quốc" → CEO ghi thành chỉ đạo, đưa vào lời dặn của cả đội ở
  mọi lần làm việc. Xem và bỏ chỉ đạo ở khung CEO. Chỉ đạo ảnh hưởng nội dung agent viết và trao đổi; các giới hạn an
  toàn (số bài/ngày, giãn cách, luật nhóm) vẫn theo cài đặt.
- **Tự duyệt bài nháp** của Lan: loại bài hứa công dụng chữa bệnh, quá ngắn, quá dài hoặc trùng bài 30 ngày qua (lý do
  được ghi để Lan rút kinh nghiệm), duyệt bài đạt rồi cho Tuấn xếp lịch. Sau họp sáng, cả đội luôn vào việc hằng ngày.

**CEO báo lại:** việc giao cho sale (tìm nhóm, xin vào nhóm) và cho Lan (viết bài) chạy nền; làm xong CEO nhắn lại kết quả
trong khung chat (và Telegram nếu sếp giao qua Telegram). Khung chat có dòng "Đang làm" cho biết sale nào đang làm gì.
Nếu chưa làm được (chưa có nick đăng nhập, nick bị tạm dừng, nick đang mở Chrome chờ đăng nhập…), CEO nói rõ lý do và
sếp cần làm gì.

Có khóa API Claude thì CEO dùng AI để hiểu lệnh (Haiku, rất rẻ); chưa có khóa thì CEO hiểu các mẫu câu thường gặp
("Viết 3 bài về…", "Xếp lịch", "Họp về…", "Tìm nhóm theo chủ đề “…”", "Tạm dừng Linh", "<Tên agent> … sai/dài quá/đừng…",
"Từ nay …", "Tình hình hôm nay thế nào?").

## CEO: tuyển dụng và sa thải

CEO **Đức** điều hành nhân sự phòng kinh doanh (khung **CEO** trên trang Công ty, lệnh `/ceo` trên Telegram). Mọi quyết
định dựa trên luật và số liệu thật, không gọi AI nên không tốn tiền.

**Sa thải và tuyển người thay.** Cuối kỳ KPI, CEO thực hiện sa thải sale không đạt rồi xét nick của người đó:

| Tình huống | CEO quyết định |
|---|---|
| Nick vẫn đăng nhập tốt, đạt từ 30% chỉ tiêu trở lên | Tuyển người mới tiếp quản nick (giữ phiên đăng nhập, hội nhóm), chạy kỳ KPI mới |
| Nick đạt dưới 30% chỉ tiêu | Không tuyển thay: vấn đề nằm ở nick hoặc các nhóm, báo sếp kiểm tra |
| Người thay cũng trượt (lần 2 liên tiếp trên cùng nick) | Dừng nick, đề nghị sếp đổi nick hoặc bổ sung hội nhóm |
| Nick đang lỗi đăng nhập | Chờ sếp xử lý nick rồi mới tuyển thay |

Nếu tất cả sale bị sa thải cùng lúc, công ty giải thể trước khi CEO kịp tuyển thay (đúng luật giải thể).

**Tăng người theo doanh thu.** Mặc định doanh thu (từ khi thành lập) chạm **50 triệu** thì tuyển thêm 1 sale, chạm
**100 triệu** thêm 1 sale nữa. Sửa mốc và số người mỗi mốc ở khung CEO → **Sửa mốc**. Doanh thu sếp vừa nhập chạm mốc là
CEO tuyển ngay.

**Tăng người theo tiềm năng Facebook.** Mỗi sáng CEO xem số liệu 14 ngày gần nhất. Cần ít nhất một tín hiệu:

- cả phòng trung bình đạt mức KPI vượt (mặc định 10 khách có SĐT/ngày), hoặc
- các nick vượt 120% chỉ tiêu của mình;

và đủ các điều kiện an toàn: có đủ 14 ngày dữ liệu, số khách tuần này không giảm, không còn sale mới đang chờ nick,
văn phòng còn chỗ (tối đa 8 sale), vốn đủ nuôi agent ít nhất 60 ngày, lần tuyển vì tiềm năng trước đã cách 14 ngày.
Bấm **Đánh giá ngay** để CEO xem lại lập tức; tắt "Tự tuyển thêm khi thấy tiềm năng" nếu chỉ muốn tăng người theo mốc doanh thu.

**Việc của sếp khi có sale mới:** mỗi sale cần 3–5 tài khoản Facebook. CEO tạo chỗ làm và nick đầu tiên, Telegram báo
sếp; sếp vào **Nhân viên sale** → **Thêm nick** cho đủ số nick, rồi bấm **Mở Chrome để đăng nhập** ở từng nick. Kỳ KPI của sale mới chỉ bắt đầu từ ngày
nick chạy được, nên chờ nick không bị tính là trượt KPI. CEO nhắc lại mỗi 3 ngày nếu chưa có nick; chưa có nick thì
cho nghỉ việc để hủy tuyển.

**Quyền của CEO:** chế độ **CEO tự quyết** (mặc định) hoặc **Chờ sếp duyệt**. Ở chế độ chờ duyệt, mọi việc tuyển thêm
và tuyển thay hiện thành đề xuất có nút **Duyệt / Không** trong phần mềm và trên Telegram. Sa thải theo luật KPI luôn
được thực hiện.

## Màn hình Lỗi

Mọi lỗi đều được ghi về màn hình **Lỗi** (menu trái, chấm đỏ khi có lỗi mới):

- Thao tác của sếp bị lỗi ở bất kỳ màn hình nào (nhập sai, phần mềm báo từ chối, mất kết nối) và lỗi hiển thị của giao diện.
- Lỗi trong các việc tự động: đăng bài, up bài, quét bình luận, Chrome của sale, nick bị Facebook chặn, Telegram,
  AI Claude, Fanpage, lịch tự động. Lỗi bất ngờ của phần mềm được ghi kèm chi tiết kỹ thuật và mã lỗi.

Mỗi lỗi có: màn hình xảy ra, thời gian, số lần lặp (lỗi giống nhau được gộp lại), **cách xử lý**, nút mở đúng màn hình
cần sửa, ảnh chụp màn hình lúc lỗi (khi sale đăng bài hoặc up bài), nút **Sao chép** để gửi cho người hỗ trợ.
Thông báo lỗi ở các màn hình khác có nút **Xem lỗi** dẫn thẳng tới đây. Sửa xong bấm **Đã xử lý**; lỗi đã xử lý mà xảy
ra lại sẽ hiện thành lỗi mới. Lỗi đã xử lý tự xóa sau 30 ngày.

## Bắt đầu chạy thật

Sau khi thử nghiệm xong: **Cài đặt → Bắt đầu chạy thật** → gõ `CHAY THAT` → **Xóa dữ liệu thử nghiệm**.

- **Xóa:** bài đăng, lượt up bài, lịch sử dùng ảnh, khách hàng, tin nhắn, bình luận đã quét, cuộc họp, việc giao,
  nhật ký, bài học và cấp độ của agent, lịch sử KPI, ảnh chụp màn hình, cùng toàn bộ sản phẩm/hội nhóm/sale **mẫu**.
  Có thể chọn xóa cả sản phẩm và hội nhóm bạn đã nhập.
- **Giữ nguyên:** nhân viên sale và phiên đăng nhập Facebook của họ, sản phẩm và hội nhóm bạn đã nhập, khóa API Claude,
  Telegram, KPI và mọi cài đặt, thư mục ảnh trên máy, chi phí AI đã tiêu (để ngân sách tháng vẫn đúng).
- Trước khi xóa, phần mềm tự sao lưu toàn bộ dữ liệu vào `data/backups/`. Muốn khôi phục: tắt phần mềm, chép file sao lưu
  đè lên `data/company.db`.

Từ bản này, phần mềm không còn tạo khách hàng giả khi cài mới. Khi trang mở từ phần mềm trên máy mà phần mềm bị tắt,
giao diện báo "Mất kết nối" và tự kết nối lại, không bao giờ hiển thị dữ liệu mẫu thay cho dữ liệu thật.

## Dữ liệu mẫu

Lần đầu chạy, phần mềm tạo sẵn vài sản phẩm và hội nhóm **mẫu** để bạn xem thử (bản cũ còn tạo cả khách hàng mẫu). Chúng được đánh dấu riêng:

- Khách mẫu không bao giờ được chuyển sang Telegram và tự bị xóa khi có khách thật đầu tiên.
- Sale mẫu tự rời văn phòng 3D khi bạn tuyển sale đầu tiên.
- Sản phẩm và hội nhóm mẫu: thay bằng thông tin thật, hoặc vào **Cài đặt → Dữ liệu mẫu → Xóa toàn bộ dữ liệu mẫu**.

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

**Cập nhật bản mới:** tải code mới về (`git pull`) ngay cả khi phần mềm đang chạy. Phần mềm tự nhận ra có bản mới, chờ
lúc các sale không có việc dở, rồi tự chạy lại `run.bat` (cài thêm thư viện nếu cần) và trang tự tải lại. Chạy `run.bat`
khi đang có bản khác chạy cũng không sao: bản mới tự tắt bản cũ. Phần mềm luôn chỉ chạy một bản.

### Múi giờ

Phần mềm chạy theo **giờ Việt Nam (GMT+7)** dù máy tính đặt múi giờ nào (Windows hay bị đặt sai múi giờ): giờ họp, giờ đăng bài,
giờ quét bình luận, báo cáo Telegram, đồng hồ trong văn phòng đều theo giờ này. Đổi ở **Cài đặt → Công ty & lịch làm việc →
Múi giờ**; trang này cũng cho biết giờ trên phần mềm và báo nếu máy tính đang đặt múi giờ khác (không cần sửa máy).
Cập nhật bản này, `run.bat` tự cài thêm thư viện `tzdata` (dữ liệu múi giờ cho Windows); thiếu thư viện thì phần mềm vẫn tính
đúng giờ Việt Nam bằng độ lệch cố định.

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
  accounts.py    Nick Facebook của sale: mỗi sale 3–5 nick, hồ sơ Chrome và giới hạn riêng, chuyển dữ liệu bản cũ
  browser_poster.py  Nhân viên sale điều khiển Chrome của nick: đăng nhập lần đầu, ca làm việc theo nick, đăng bài, lấy link bài, up bài
  media_folder.py    Thư mục ảnh từng sản phẩm: chọn ngẫu nhiên, xoay vòng, chống đăng trùng theo nhóm và nick
  errors.py      Sổ lỗi: ghi lỗi từ mọi màn hình và việc tự động, gộp lỗi trùng, gợi ý cách xử lý
  ceo_review.py  CEO chấm bài 100 điểm theo bài mẫu, quy định và bài học từ sếp
  post_template.py  Thư viện bài mẫu sỉ của sếp, Lan viết lại mỗi bài khác nhau, chọn mẫu hiệu quả
  my_groups.py   Nhóm có sẵn trong nick: đọc danh sách nhóm, Tuấn đánh giá, tự thoát nhóm kém, nhóm mới vào nghỉ, chăm sóc nhóm quản lý
  prospect_rules.py  Điều kiện tìm khách sỉ sếp đặt, bài sếp dạy Mai, chấm lại theo điều kiện
  junk.py        Data rác sếp loại: chặn đích danh, học chữ chung của data rác, trừ điểm/loại khách giống vậy
  fb_policy.py   Luật Facebook: bộ luật, kiểm bài, giới hạn an toàn mỗi nick, sự cố & bài học, theo dõi chính sách Meta
  website.py     Website công ty + Vy: từ khóa, viết bài, bảng kiểm SEO, dựng trang tĩnh, sitemap, schema, zip, FTP
  group_target.py Sếp chỉ đạo nơi đăng: chế độ all/prefer/only, từ khóa nên đăng / tránh, nhóm tập trung, xem trước
  post_care.py   Bảo chăm bài đã đăng: câu bình luận up bài tự viết (Claude hoặc mẫu), dòng liên hệ Zalo, xem thử
  group_feed.py  Lướt bảng tin nhóm: mọi nick đọc >=20 bài, lọc 3 lớp (chữ, Claude, học từ sếp), bình luận người hỏi mua (kèm ảnh)
                 và chào người bán online (chỉ chữ, trần riêng), nhịp lướt theo luật nick, ngừng chào ở nhóm xóa bình luận
  friends.py     Kết bạn trong nhóm: điểm sôi nổi của nhóm, đọc bảng tin tìm người hợp tệp khách, trần lời mời, mở hồ sơ cho sale
  prospect.py    Mai tìm khách sỉ: tìm, đọc trang công khai, phân loại người bán, chấm điểm 100 có bằng chứng, lưu CRM
  group_finder.py  Tìm nhóm mới: CEO chọn chủ đề, sale lướt Facebook, tìm nhóm, khảo sát chỉ số tương tác, xin vào nhóm
  group_review.py  Tuấn đánh giá nhóm theo chuẩn nhóm tương tác cao: chấm điểm, Nên vào / Cân nhắc / Bỏ qua, lý do
  ceo_orders.py  Sếp giao việc cho CEO: hiểu lệnh, chia việc cho agent, sửa agent, chỉ đạo lâu dài, CEO tự duyệt bài
  products.py    Sản phẩm đang bán chạy: đánh dấu, danh sách để các agent ưu tiên chào mời
  ceo.py         CEO: sa thải theo luật, tuyển người thay, tăng người theo mốc doanh thu và tiềm năng Facebook
  company.py     Công ty: vốn, chi phí, doanh thu, đánh giá KPI tháng, sa thải, giải thể
  kpi.py         KPI: nhận diện SĐT, tiến độ, chia theo nick, lịch sử; chuyển khách cho sếp, kịch bản tư vấn
  telegram_bot.py  Bot Telegram: ghép nối, báo cáo, phiếu khách có nút bấm, lệnh /baocao /kpi /khach /hop
  content_style.py  Kho bài Claude viết, phong cách viết của Lan, Lan tự ghép bài mới theo phong cách đã học
  growth.py      Agent rảnh thì tự học với Claude, luyện tập, ôn bài để lên cấp (không bao giờ ngồi không)
  knowledge.py   Sổ kiến thức: tự học mỗi ngày, tra sổ trước khi làm, chỉ hỏi Claude khi chưa biết và lưu lại câu trả lời
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

| Gói | Viết bài | Hà tư vấn khách | CEO hiểu lệnh sếp | Cuộc họp, CEO chấm bài | Ước tính / tháng (3 nick sale) |
|---|---|---|---|---|---|
| Tiết kiệm | Haiku 5.5, theo lô | Haiku 5.5 | Haiku 5.5 | Haiku 5.5 | dưới 1 USD |
| **Cân bằng** (mặc định) | Sonnet 5.5, theo lô | **Sonnet 5.5** | **Sonnet 5.5** | Haiku 5.5 | khoảng 5–9 USD |
| Chất lượng | Sonnet 5.5, theo lô | Sonnet 5.5 | Sonnet 5.5 | Sonnet 5.5 | khoảng 8–15 USD |

**Đặt mô hình tốt ở chỗ ra tiền:** gói Cân bằng dùng Sonnet cho kịch bản tư vấn và tin nhắn khách của Hà (phiếu khách gửi sếp,
kịch bản tiếp cận khách Mai tìm) và cho CEO hiểu lệnh sếp: ít lượt nhưng ảnh hưởng thẳng tới đơn hàng. Việc nhiều lượt (họp, CEO chấm
từng bài, tự học) vẫn dùng Haiku. Máy đang dùng gói Cân bằng được tự nâng lên một lần khi cập nhật; cấu hình sếp tự chỉnh giữ nguyên.
Chỉnh riêng từng việc ở Cài đặt → Chi phí AI (Viết bài, Hà tư vấn khách, Cuộc họp, CEO hiểu lệnh sếp, CEO chấm bài).

Các cơ chế tiết kiệm có sẵn:

- **Viết theo lô (Batch API):** bài viết hằng ngày gửi một lần, giá giảm 50%, bài có sau vài phút (tối đa 24 giờ).
  Bài sếp bấm "Viết bài" vẫn viết ngay.
- **Chỉ viết đủ số bài cần đăng:** Lan tính số bài đăng được hôm nay (theo số nick, giới hạn bài/ngày, số nhóm đã hết
  giãn cách) rồi trừ bài còn trong kho. Không viết bài thừa.
- **Cuộc họp gọn:** mỗi lượt nói chỉ đưa 12 câu gần nhất vào AI, câu trả lời giới hạn độ dài; chọn được số vòng
  tranh luận và các ngày họp trong tuần. Báo cáo của nhân viên sale lấy thẳng từ số liệu, không tốn AI.
- **Ngân sách tháng:** chạm 100% thì mọi việc tự chuyển sang Haiku; chạm 120% thì tạm ngừng gọi AI và dùng
  nội dung mẫu đến tháng sau. Nên đặt thêm giới hạn chi tiêu trong Anthropic Console để chắc chắn.
- **Không âm thầm dùng nội dung mẫu:** Claude trả kết quả qua một công cụ có khuôn cố định (không còn lỗi đọc JSON). Bài viết
  quá dài bị cắt giữa chừng thì tự thử lại 1 lần với gấp đôi độ dài. Vẫn hỏng (hoặc lỗi mạng, khóa, tín dụng) thì mới dùng nội
  dung mẫu, và mỗi lần như vậy được đếm ở **Cài đặt → Chi phí AI** (“N lần phải dùng nội dung mẫu thay Claude”, chia theo việc
  và lý do) và ghi vào màn **Lỗi**. Chưa có khóa Claude (chế độ mô phỏng) thì không tính.

Giá dùng để tính (USD / 1 triệu token, vào/ra): Haiku 5.5 0,10/0,50 · Sonnet 5.5 2/10 · Opus 5.5 4/20;
theo lô giảm 50%. Khi Anthropic đổi giá, sửa bảng `PRICES` trong `backend/llm.py`.

## Kiểm tra trên Facebook giả lập (cho người lập trình)

Thư mục `dev/`: Facebook giả lập (`mockfb.py`, cổng 8098), TikTok/Shopee giả lập (`mockmkt.py`, 8096/8095) và các bài kiểm tra.
`dev/run.sh` tự bật giả lập, chạy test rồi tắt; mỗi test in một dòng kết quả, log đầy đủ ở `dev/work/`.
Chạy một vài test: `dev/run.sh reply_test care_test`. Chạy hết: `dev/run.sh`. File `CLAUDE.md` ghi bản đồ code và cách làm tiết kiệm token.
