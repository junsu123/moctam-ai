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

## Sổ kiến thức: tự học mỗi ngày, ít phụ thuộc Claude

Ngoài bài học rút từ kết quả (phần trên), mỗi agent có **sổ kiến thức** (trang **Đào tạo → Sổ kiến thức của đội**):

1. **Tự học mỗi ngày** (mặc định 07:00, trước họp sáng): mỗi agent học 2 kiến thức mới hợp với việc đang làm, theo thứ tự:
   câu hỏi còn bỏ ngỏ (câu sếp hỏi mà đội chưa biết) → việc thực tế hôm nay (sản phẩm đang bán chạy, chủ đề tìm nhóm, câu
   khách hay hỏi) → giáo trình theo vai trò (Lan: viết bài bán sỉ; Tuấn: nhóm Facebook; Hà: tư vấn, xử lý từ chối; Khoa: chỉ số;
   Minh: điều hành; CEO: chiến lược; sale: nuôi nick an toàn). Có khóa Claude: mỗi agent 1 lần gọi Haiku/ngày (khoảng 0,001 USD).
   Chưa có khóa: học từ thư viện kiến thức có sẵn trong phần mềm.
2. **Tra sổ trước khi làm**: khi viết bài, soạn tin, tư vấn, họp, kiến thức liên quan được đưa vào lời dặn của agent.
3. **Biết rồi thì tự trả lời, không gọi Claude**: Hà gặp câu khách đã từng hỏi (VD "nhập nhiều có chiết khấu không?") thì tự
   soạn tin từ sổ; sếp hỏi CEO điều đội đã biết thì CEO trả lời ngay từ sổ.
4. **Chưa biết mới hỏi Claude, và luôn lưu lại**: mỗi lần hỏi Claude, câu trả lời dùng lại được được ghi vào sổ (Hà soạn tin
   thì rút ra câu hỏi chung của khách và cách trả lời). Chưa có khóa thì câu hỏi được ghi vào "Câu chờ học" để học sau.

Trang Đào tạo cho biết: số kiến thức, số học hôm nay, số lần tự trả lời bằng sổ và số lần phải hỏi Claude trong 30 ngày,
**tỉ lệ tự lực**. Sếp hỏi đội ngay ở ô **Hỏi**, tìm, lọc theo agent, xóa kiến thức sai, **dạy kiến thức** mới (tích "trả lời
khách" để Hà tự dùng khi khách hỏi đúng ý đó). Trên Telegram: hỏi CEO bằng câu hỏi (VD "Khách chê giá cao thì trả lời sao?"),
hoặc nhắn "Cho cả đội học thêm kiến thức". Kiến thức học mỗi ngày được báo trong tin "Việc vừa hoàn thành".

## Văn phòng: agent luôn làm việc hoặc học để lên cấp

Trang **Văn phòng** chỉ có văn phòng 3D và cột **Đội đang làm gì**: mỗi agent (cả nhân viên sale) hiện trạng thái
Đang làm / Đang học / Đang họp, việc đang làm, cấp độ và thanh kinh nghiệm tới cấp sau, số kiến thức học hôm nay và
2 việc vừa xong. Ô giao việc cho CEO, KPI hôm nay và nhật ký chuyển sang trang **Giao việc**.

Agent không bao giờ ngồi không. Mỗi 30 giây, agent nào không có việc thật (và không đang họp) tự vào một buổi 6–12 phút:

1. **Học với Claude** (Haiku): tối đa 6 buổi/agent/ngày (chỉnh ở Đào tạo → Sổ kiến thức → Cài đặt), cách nhau ít nhất
   45 phút; mỗi kiến thức mới lưu vào sổ, **+5 kinh nghiệm**. Chưa có khóa: học từ thư viện có sẵn đến khi hết.
2. **Luyện tập** không tốn tiền: Lan luyện viết bài theo phong cách đã học, Hà luyện trả lời câu khách hay hỏi, Tuấn xem lại
   nhóm cần cân nhắc, Khoa xem số liệu, sale ôn cách giữ nick: **+2 kinh nghiệm**, tối đa 10/ngày.
3. **Ôn lại** kiến thức trong sổ: **+1 kinh nghiệm**, tối đa 10/ngày.

Việc thật luôn được ưu tiên: có việc là agent chuyển sang làm ngay. Kinh nghiệm từ học có giới hạn mỗi ngày, nên muốn lên cấp
nhanh vẫn phải làm ra kết quả (bài được duyệt, khách, đơn). Báo cáo tối trên Telegram có số kiến thức cả đội học trong ngày và
ai lên cấp. Chi phí: khoảng 0,02 USD/ngày cho 7 agent với 6 buổi học mỗi agent.

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
