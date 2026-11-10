"""Facebook giả lập: soạn bài, bảng tin có link bài, trang bài viết có ô bình luận + đính kèm ảnh."""
import html, json, re
from http.server import BaseHTTPRequestHandler, HTTPServer

SP = str(__import__("os").environ.get("MT_WORK") or __import__("pathlib").Path(__file__).resolve().parent / "work")
POSTS = []          # {id, where, text}
SEED_COMMENTS = [
    ("Nguyễn Thu Hà", "Quan tâm ạ, sđt 0912.345.678 gọi mình nhé"),
    ("Trần Minh", "ib giá sỉ giúp mình"),
    ("Lê Phương Shop", "Mình cần lấy 500 hộp, in nhãn riêng được không? 0987654321"),
    ("Phạm Tuấn", "đẹp quá"),
    ("Linh Nguyễn", "Còn hàng sỉ nhé cả nhà"),
]
REPLIES = []
REMOVED = set()
PREVIEW_JS = """<script>
window.showPreviews = (d, files, box) => { if (window.NOPREVIEW) return;
  let pv = d.querySelector('.pv'); if (!pv) { pv = document.createElement('div'); pv.className = 'pv'; (box || d).appendChild(pv); }
  const bar = document.createElement('div'); bar.setAttribute('role', 'progressbar'); bar.innerText = 'Đang tải lên'; d.appendChild(bar);
  for (const f of files) { const im = document.createElement('img'); im.src = URL.createObjectURL(f); im.width = 120; im.height = 90; pv.appendChild(im); }
  setTimeout(() => bar.remove(), 1500);
};
</script>"""
MODE = {"graphql": "url", "pending": False}   # graphql: url | id | none

MODERN_COMPOSER = """<div role="button" tabindex="0" id="open"><span>Bạn viết gì đi...</span></div>
<script>
document.getElementById('open').onclick = () => {
  const d = document.createElement('div'); d.setAttribute('role','dialog'); d.setAttribute('aria-label','Tạo bài viết');
  d.innerHTML = `<h2>Tạo bài viết</h2><input type="file" accept="image/*,image/heif,image/heic" multiple style="display:none" class="decoy">
  <div role="textbox" contenteditable="true" aria-label="Bạn viết gì đi..." style="min-height:80px;border:1px solid #999"></div>
  <div class="box"></div><div aria-label="Thêm vào bài viết của bạn"><div role="button" aria-label="Ảnh/video" id="ph">Ảnh/video</div></div>
  <div role="button" aria-label="Đăng" aria-disabled="true" id="post">Đăng</div>`;
  document.body.appendChild(d);
  let files = [];
  const real = document.createElement('input'); real.type = 'file'; real.multiple = true; real.accept = 'image/*,image/heif,image/heic,video/*'; real.style.display = 'none';
  document.body.appendChild(real);  // ô ảnh thật nằm ngoài hộp soạn bài
  real.onchange = () => { files = [...files, ...real.files]; showPreviews(d, real.files, d.querySelector('.box')); };
  d.querySelector('#ph').onclick = () => {
    if (!window.DROPZONE) return real.click();
    let z = d.querySelector('.zone'); if (z) return;
    z = document.createElement('div'); z.className = 'zone'; z.innerHTML = '<div role="button" aria-label="Thêm ảnh/video">Thêm ảnh/video<br>hoặc kéo và thả</div>';
    d.querySelector('.box').appendChild(z); z.firstChild.onclick = () => real.click();
  };
  const tb = d.querySelector('[role=textbox]'), btn = d.querySelector('#post');
  tb.addEventListener('input', () => btn.setAttribute('aria-disabled', tb.innerText.trim() ? 'false' : 'true'));
  const fi = {get files() { return files; }};
  %(send)s
  btn.onclick = async () => { if (btn.getAttribute('aria-disabled') === 'true') return; send(); };
};
</script>"""

MODERN_SEND = """
  const send = async () => {
    const r = await fetch('/record', {method:'POST', body: JSON.stringify({where: location.pathname.replace(/\\/$/,''), text: tb.innerText, files: fi ? fi.files.length : 0, real: true})});
    await fetch('/api/graphql/', {method:'POST', headers:{'x-fb-friendly-name':'ComposerStoryCreateMutation','content-type':'application/x-www-form-urlencoded'},
                                  body:'fb_api_req_friendly_name=ComposerStoryCreateMutation&variables=%7B%7D'});
    setTimeout(() => { d.remove(); if (window.PENDING) { const b=document.createElement('div'); b.innerText='Bài viết của bạn đang chờ phê duyệt của quản trị viên'; document.body.prepend(b);} else location.reload(); }, 800); };
"""

COMPOSER = """<div role="button" tabindex="0" id="open"><span>%(label)s</span></div>
<script>
document.getElementById('open').onclick = () => {
  const d = document.createElement('div'); d.setAttribute('role','dialog');
  d.innerHTML = `<h2>Tạo bài viết</h2><div role="textbox" contenteditable="true" style="min-height:80px;border:1px solid #999"></div>
  <div role="button" aria-label="Ảnh/video">Ảnh/video</div><input type="file" accept="image/*" multiple style="display:none">
  <div role="button" aria-label="Đăng" aria-disabled="true" id="post">Đăng</div>`;
  document.body.appendChild(d);
  const tb = d.querySelector('[role=textbox]'), btn = d.querySelector('#post'), fi = d.querySelector('input');
  fi.onchange = () => showPreviews(d, fi.files);
  tb.addEventListener('input', () => btn.setAttribute('aria-disabled', tb.innerText.trim() ? 'false' : 'true'));
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && document.body.contains(d)) { d.remove();
     const c = document.createElement('div'); c.setAttribute('role','dialog'); c.innerHTML = '<div role="button">Bỏ</div>';
     c.firstChild.onclick = () => c.remove(); document.body.appendChild(c);} });
  btn.onclick = async () => {
    if (btn.getAttribute('aria-disabled') === 'true') return;
    await fetch('/record', {method:'POST', body: JSON.stringify({where: location.pathname.replace(/\\/$/,''), text: tb.innerText, files: fi.files.length})});
    setTimeout(() => d.remove(), 800);
  };
};
</script>"""


REAL = """<div role="dialog" aria-label="Tin nhắn" style="position:fixed;bottom:0;right:0"><div role="button">Đóng đoạn chat</div></div>
<input type="file" accept="image/*" id="avatar" style="display:none">
<div role="button" tabindex="0" id="open"><span>%(label)s</span></div>
<script>
const NEXT = %(next)s;
document.getElementById('open').onclick = () => {
  const d = document.createElement('div'); d.setAttribute('role','dialog'); d.setAttribute('aria-label','Tạo bài viết');
  d.innerHTML = `<h2>Tạo bài viết</h2><div role="textbox" contenteditable="true" aria-label="Bạn viết gì đi..." style="min-height:80px;border:1px solid #999"></div>
  <div role="button" aria-label="Ảnh/video" id="ph">Ảnh/video</div>
  <div role="button" aria-label="${NEXT ? 'Tiếp' : 'Đăng'}" aria-disabled="true" id="post">${NEXT ? 'Tiếp' : 'Đăng'}</div>`;
  document.body.appendChild(d);
  let fi = null;
  d.querySelector('#ph').onclick = () => { if (!fi) { fi = document.createElement('input'); fi.type='file'; fi.multiple=true; fi.accept='image/*,image/heif,video/*'; fi.style.display='none'; d.appendChild(fi); fi.onchange = () => showPreviews(d, fi.files); } };
  const tb = d.querySelector('[role=textbox]'), btn = d.querySelector('#post');
  tb.addEventListener('input', () => btn.setAttribute('aria-disabled', tb.innerText.trim() ? 'false' : 'true'));
  const send = async () => { await fetch('/record', {method:'POST', body: JSON.stringify({where: location.pathname.replace(/\\/$/,''), text: tb.innerText, files: fi ? fi.files.length : 0, real: true})}); setTimeout(() => d.remove(), 800); };
  btn.onclick = async () => {
    if (btn.getAttribute('aria-disabled') === 'true') return;
    if (!NEXT) return send();
    d.querySelector('h2').textContent = 'Cài đặt bài viết'; tb.style.display = 'none'; btn.remove();
    const b2 = document.createElement('div'); b2.setAttribute('role','button'); b2.setAttribute('aria-label','Đăng'); b2.textContent='Đăng'; d.appendChild(b2);
    b2.onclick = send;
  };
};
</script>"""

SEARCH_GROUPS = {
    "chayqcfb": ("Hội Chạy Quảng Cáo Facebook - Ads Việt Nam", "Công khai · 245K thành viên · 30+ bài viết mỗi ngày", "public"),
    "qcfbthucchien": ("Cộng đồng chạy quảng cáo Facebook thực chiến", "Riêng tư · 1,2 triệu thành viên · 50 bài viết mỗi ngày", "private"),
    "adsquestions": ("Hội Quảng Cáo FB Ads Chuyên Sâu", "Riêng tư · 86K thành viên · 12 bài viết mỗi ngày", "questions"),
    "chaynho": ("Chạy quảng cáo nhỏ lẻ", "Công khai · 640 thành viên · 2 bài viết mỗi tuần", "public"),
    "nguonhangsi": ("Nguồn Hàng Sỉ Thực Phẩm Tận Xưởng", "Công khai · 98,5K thành viên · 20 bài viết mỗi ngày", "public"),
    "meobim": ("Mẹ Bỉm Sữa Kinh Doanh Online", "Riêng tư · 310K thành viên · 40+ bài viết mỗi ngày", "private"),
    "dulich": ("Hội Du Lịch Bụi", "Công khai · 500K thành viên · 100 bài viết mỗi ngày", "public"),
    "chotrasi": ("Chợ Quảng Cáo Facebook Rao Vặt Sỉ Lẻ", "Công khai · 120K thành viên · 60 bài viết mỗi ngày", "public"),
    "qcfb2019": ("Quảng Cáo Facebook 2019", "Công khai · 15K thành viên", "public"),
    "moctam": ("Hội Sỉ Trà & Ngũ Cốc Mộc Tâm", "Công khai · 3,2K thành viên · 8 bài viết mỗi ngày", "public"),
}
# chỉ số trang Giới thiệu: (bài hôm nay, bài tháng trước, tổng thành viên, +mới tuần trước, luật)
ABOUT = {
    "chayqcfb": (35, "1.150", "245.312", "2.400", "Không spam link. Bài bán hàng đăng đúng chủ đề quảng cáo."),
    "qcfbthucchien": (50, "1.600", "1,2 triệu", "5.100", "Tôn trọng thành viên."),
    "adsquestions": (12, "380", "86.000", "300", "Nghiêm cấm quảng cáo bán hàng dưới mọi hình thức."),
    "chaynho": (0, "8", "640", "2", ""),
    "nguonhangsi": (20, "640", "98.500", "900", "Đăng bài đúng giờ vàng."),
    "meobim": (40, "1.300", "310.000", "1.800", "Các mẹ hỗ trợ nhau."),
    "dulich": (100, "3.000", "500.000", "3.000", ""),
    "chotrasi": (60, "1.900", "120.000", "200", "Thoải mái đăng bán."),
    "qcfb2019": (0, "3", "15.000", "0", ""),
    "moctam": (8, "240", "3.200", "60", "Chỉ đăng bài liên quan trà, ngũ cốc, kinh doanh."),
}
# bài trên bảng tin nhóm công khai: (tuổi, cảm xúc, bình luận, nội dung)
FEEDS = {
    "chayqcfb": [("2 giờ", 48, 17, "Ad account bị khóa phải làm sao các bác?"), ("4 giờ", 35, 22, "Chia sẻ case chạy tin nhắn ngành thực phẩm"),
                 ("5 giờ", 61, 12, "Giá thầu tháng này tăng quá"), ("9 giờ", 27, 9, "Có ai cần nguồn hàng trà để test ads không")],
    "nguonhangsi": [("1 giờ", 3, 1, "Xả kho bột ngũ cốc giá sỉ 85k inbox zalo 0912345678"), ("3 giờ", 5, 2, "Trà túi lọc giá sỉ tận xưởng liên hệ"),
                    ("6 giờ", 9, 4, "Mọi người nhập hàng ở đâu rẻ?"), ("1 ngày", 2, 0, "Nhận ship cod toàn quốc giá lẻ 120k")],
    "chotrasi": [("10 phút", 1, 0, "Xả kho giá sỉ 50k inbox zalo"), ("30 phút", 0, 0, "Bán sỉ lẻ trà sữa giá 30k ib"),
                 ("1 giờ", 2, 0, "Order hàng giá sỉ liên hệ 0987654321"), ("2 giờ", 1, 1, "Freeship giá lẻ 99k inbox")],
    "qcfb2019": [("2 năm", 3, 0, "Còn ai chạy ads không"), ("2 năm", 1, 0, "Up")],
    "moctam": [("3 giờ", 12, 6, "Shop nào đang bán trà gừng mùa này chạy không?"), ("8 giờ", 9, 4, "Mẹo livestream bán ngũ cốc")],
    "chaynho": [("5 ngày", 1, 0, "hello")],
    "dulich": [("1 giờ", 300, 80, "Đà Lạt mùa này đẹp quá")],
}


def about_page(slug):
    name, meta, kind = SEARCH_GROUPS[slug]
    a = ABOUT.get(slug)
    priv = "Công khai" if kind == "public" else "Riêng tư"
    if not a:
        return f"<h1>{html.escape(name)}</h1><p>{priv}</p>"
    return (f"<h1>{html.escape(name)}</h1><h2>Giới thiệu</h2><p>{priv}</p><h2>Hoạt động</h2>"
            f"<div>{a[0]} bài viết mới hôm nay</div><div>{a[1]} bài viết trong tháng trước</div>"
            f"<div>Tổng cộng {a[2]} thành viên</div><div>+ {a[3]} trong tuần trước</div>"
            f"<h2>Quy tắc của quản trị viên nhóm</h2><div>{html.escape(a[4])}</div>")


def public_feed(slug):
    out = '<div role="feed">'
    for i, (age, r, c, t) in enumerate(FEEDS.get(slug, [])):
        out += (f'<div role="article"><b>Thành viên {i}</b> · <a href="/groups/{slug}/posts/{900 + i}">{age}</a>'
                f'<div>{html.escape(t)}</div><span aria-label="Tất cả cảm xúc: {r}">{r}</span> <span>{c} bình luận</span>'
                + "".join(f'<div role="article" aria-label="Bình luận"><span>trả lời {k}</span></div>' for k in range(min(c, 2)))
                + "</div>")
    return out + "</div>"
JOINED, REQUESTED = set(), set()
MY = {"on": False, "groups": {"moctam": True, "nguonhangsi": False, "dulich": False, "qcfb2019": False, "chotrasi": False},
      "left": []}


def joins_html():
    adm = [s for s, a in MY["groups"].items() if a]
    mem = [s for s, a in MY["groups"].items() if not a]
    li = lambda s: f'<div><a href="/groups/{s}/">{html.escape(SEARCH_GROUPS[s][0])}</a> <a href="/groups/{s}/">Xem nhóm</a></div>'
    return ("<h1>Nhóm</h1><h2>Nhóm do bạn quản lý</h2>" + "".join(li(s) for s in adm)
            + "<h2>Tất cả nhóm bạn đã tham gia</h2>" + "".join(li(s) for s in mem) + '<a href="/groups/feed/">Bảng feed</a>')


def my_group_page(slug):
    name = SEARCH_GROUPS[slug][0]
    admin = MY["groups"][slug]
    top = '<div role="button" aria-label="Công cụ quản trị">Công cụ quản trị</div>' if admin else ""
    js = """<script>document.getElementById('jd').onclick=()=>{const m=document.createElement('div');m.setAttribute('role','menu');
m.innerHTML='<div role="menuitem">Rời nhóm</div>';document.body.appendChild(m);m.firstChild.onclick=()=>{m.remove();
const d=document.createElement('div');d.setAttribute('role','dialog');d.innerHTML='<h2>Rời nhóm?</h2><div role="button" aria-label="Hủy">Hủy</div><div role="button" aria-label="Rời nhóm">Rời nhóm</div>';
document.body.appendChild(d);d.querySelector('[aria-label="Rời nhóm"]').onclick=()=>fetch('/leave',{method:'POST',body:JSON.stringify({slug:'%s'})}).then(()=>d.remove());};};</script>""" % slug
    return (f"<h1>{html.escape(name)}</h1>{top}<div role=\"button\" id=\"jd\" aria-label=\"Đã tham gia\">Đã tham gia</div>{js}"
            + REAL % {"label": "Bạn viết gì đi...", "next": "false"} + feed(f"/groups/{slug}", f"/groups/{slug}/posts/{{id}}") + public_feed(slug))

# ---- trang người bán (cho Mai tìm khách sỉ)
SELLERS = {
    "travang.live": ("Trà Vàng Live - Trà & Ngũ cốc",
        "Shop mình chuyên trà túi lọc, ngũ cốc dinh dưỡng, yến mạch. Hàng mới về mỗi tuần, nhận đơn ship COD toàn quốc. "
        "Lịch live 20h tối thứ 3, 5, 7. Zalo 0901 234 567. Email travang.shop@gmail.com. 12K người theo dõi",
        ["https://shopee.vn/shop/888", "https://www.tiktok.com/@travang.live", "https://zalo.me/0901234567"],
        [("2 giờ", "Trà Vàng Live đang phát trực tiếp. Chốt đơn trà gừng combo 3 hộp giá 99k, inbox hoặc comment chốt đơn", 25),
         ("1 ngày", "Trà Vàng Live đã phát trực tiếp. Live xả kho ngũ cốc yến mạch, freeship đơn từ 2 hộp", 40),
         ("2 ngày", "Hàng mới về: bột ngũ cốc 18 loại hạt. Shop nhập số lượng lớn nên giá tốt, còn hàng sẵn kho", 12),
         ("3 ngày", "Trà Vàng Live đã phát trực tiếp. Giao lưu khách quen, giảm giá trà hoa cúc", 30)]),
    "reviewcungbe": ("Review Cùng Bé Na",
        "Review đồ ăn healthy, eat clean. Hợp tác quảng cáo, booking inbox. 50K người theo dõi. Link sản phẩm trong bio",
        ["https://s.shopee.vn/abc123"],
        [("1 ngày", "Unbox granola siêu ngon, giòn tan. Link mua ở bình luận nha cả nhà", 8),
         ("3 ngày", "Review trà detox mới, uống thử 1 tuần. Link ở bình luận, mã giảm giá shopee", 5)]),
    "fanxemlive": ("Ngọc Ánh",
        "Sống tại Hà Nội. Thích nấu ăn",
        [],
        [("3 giờ", "Ngọc Ánh đã chia sẻ video trực tiếp của Trà Vàng Live. Live hay quá mọi người vào xem", 1),
         ("2 ngày", "Cuối tuần đi chơi Ba Vì", 3)]),
    "daimart.online": ("Đại Mart Online - Tạp hóa & Mẹ và bé",
        "Tạp hóa online: đồ gia dụng, mẹ và bé, đồ ăn vặt, bánh kẹo. Bán trên Shopee và TikTok Shop. Tuyển CTV, nhận làm đại lý. "
        "Hotline 0988.111.222. 8.500 người theo dõi",
        ["https://shopee.vn/shop/999", "https://www.tiktok.com/@daimart"],
        [("5 giờ", "Hàng về bánh kẹo Tết, giá sỉ cho CTV. Inbox nhận báo giá, ship COD", 6),
         ("2 ngày", "Combo đồ dùng mẹ và bé giảm giá 20%, đặt hàng ngay", 4),
         ("4 ngày", "Tìm nhà cung cấp đồ uống, trà, cà phê để mở thêm danh mục", 9)]),
    "bepnhamy": ("Bếp Nhà My - Granola & Ngũ cốc",
        "Granola, ngũ cốc hạt nhà làm. Shop mình nhận đơn sỉ lẻ, ship COD. 6.200 người theo dõi",
        [],
        [("4 giờ", "Bếp Nhà My đã phát trực tiếp. Live chốt đơn granola, combo 2 hũ giá 199k, inbox chốt đơn", 14),
         ("1 ngày", "Hàng mới về yến mạch cán dẹt, còn hàng sẵn kho, giá sỉ cho CTV", 6)]),
    "mamxanh.ads": ("Ngũ Cốc Mầm Xanh",
        "Ngũ cốc dinh dưỡng, granola. Shop mình giao hàng toàn quốc, nhận đơn qua inbox",
        [],
        [("6 giờ", "Combo ngũ cốc 2 hũ giá 230k, freeship, inbox đặt hàng", 9)]),
    "cuahangtaphoa.ba": ("Tạp hóa Bà Tư",
        "Cửa hàng tại 12 Lê Lợi, mở cửa từ 6h sáng. Ghé cửa hàng nhé",
        [],
        [("3 tháng", "Nghỉ Tết từ 28 đến mùng 5", 2)]),
}


def ads_html():
    cards = ""
    for slug, name, txt, lid in (("mamxanh.ads", "Ngũ Cốc Mầm Xanh", "Ngũ cốc mầm 20 loại hạt cho cả nhà, giá sỉ cho shop, hotline 0977 456 123", 111),
                                 ("mamxanh.ads", "Ngũ Cốc Mầm Xanh", "Granola hạt giòn tan, đặt ngay hôm nay", 112),
                                 ("thoitrang.abc", "Thời trang ABC", "Váy đầm công sở giảm 50%", 113),
                                 ("travang.live", "Trà Vàng Live - Trà & Ngũ cốc", "Trà gừng túi lọc ấm áp mùa đông", 114)):
        cards += (f'<div class="card"><div><span>Đang hoạt động</span></div><div><span>ID thư viện: {lid}</span></div>'
                  f'<div><span>Bắt đầu chạy vào 1 Th11, 2026</span></div><a href="/{slug}">{html.escape(name)}</a><span>Được tài trợ</span>'
                  f'<div>{html.escape(txt)}</div><a href="/ads/library/?id={lid}">Xem chi tiết quảng cáo</a></div>')
    return "<h1>Thư viện quảng cáo</h1>" + cards


GROUP_CHOSI = [
    ("Phạm Thu Hương", 2001, "Mình đang tìm nguồn trà túi lọc, ngũ cốc giá sỉ để bán online, ai có xin ib hoặc gọi 0935 222 444", [
        ("Nguyễn Văn Bình", 2002, "Mình cũng cần nhập granola, ai có nguồn xin giá sỉ với"),
        ("Xưởng Trà XYZ", 2003, "Bên mình chuyên cung cấp sỉ trà túi lọc, ib nhé")]),
    ("Linh Nguyễn", 2004, "Ai cần tìm nguồn trà túi lọc giá sỉ inbox mình", []),
    ("Trần Hùng", 2005, "Cần tìm nguồn quần áo sỉ giá tốt", []),
]


GROUP_SHOP = [
    ("Mẹ Bắp Shop", 3001, "Shop mình bán online đồ ăn vặt, trà sữa, ship toàn quốc. Ai bán cùng giao lưu nha", [
        ("Thảo Organic", 3002, "Mình cũng bán trà thảo mộc online trên shopee nè"),
        ("Mẹ Bắp Shop", 3001, "Kết nối nha chị"),
        ("Hoàng Long", 3003, "hay quá")]),
    ("Thảo Organic", 3002, "Chốt đơn ngũ cốc dinh dưỡng livestream tối nay, ai muốn làm ctv inbox", []),
    ("Kho Sỉ Trà Đà Lạt", 3004, "Chuyên sỉ trà túi lọc tận xưởng, tuyển đại lý toàn quốc", []),
]


GROUP_HOIMUA = [
    ("Ngọc Ánh", 4001, "Mình đang tìm nguồn trà gừng mật ong túi lọc giá sỉ để bán online, ai có xưởng giới thiệu mình với ạ", []),
    ("Kho Sỉ Trà Đà Lạt", 4002, "Chuyên sỉ trà túi lọc tận xưởng, tuyển đại lý toàn quốc", []),
    ("Lê Minh Tâm", 4003, "Cần tìm xưởng gia công ngũ cốc dinh dưỡng làm thương hiệu riêng, số lượng 500 hộp", [
        ("Hà Vy", 4004, "Mình cũng đang tìm nguồn ngũ cốc nè")]),
    ("Trần Hùng", 4005, "Cần tìm nguồn quần áo trẻ em sỉ giá tốt", []),
    ("Mai Phương", 4006, "Hôm nay trời đẹp quá cả nhà ơi", []),
]
HOIMUA_TXT = {800 + i: r[2] for i, r in enumerate(GROUP_HOIMUA)}


def hoimua_html():
    out = '<h1>Hội Tìm Nguồn Hàng Sỉ</h1><div role="feed">'
    for i, (a, uid, txt, cmts) in enumerate(GROUP_HOIMUA):
        out += (f'<div role="article"><a href="/groups/hoimua/user/{uid}/">{html.escape(a)}</a> · <a href="/groups/hoimua/posts/{800+i}/">2 giờ</a>'
                f'<div>{html.escape(txt)}</div><span>24 bình luận</span><span>60 lượt thích</span>')
        for ca, cu, ct in cmts:
            out += (f'<div role="article" aria-label="Bình luận của {html.escape(ca)}"><a href="/groups/hoimua/user/{cu}/?comment_id=1">{html.escape(ca)}</a>'
                    f'<div>{html.escape(ct)}</div></div>')
        out += "</div>"
    return out + "</div>"


# Bảng tin nhóm (facebook.com/groups/feed/): 25 bài của nhiều nhóm, 12 bài đầu, cuộn thêm 6 bài mỗi lần
G_ADS = ("chayads", "Hội Chạy Quảng Cáo Facebook")
G_MUA = ("hoimua", "Hội Tìm Nguồn Hàng Sỉ")
FEED = [
    (G_MUA, "Ngọc Hân", 5001, "Mình đang tìm nguồn trà túi lọc gừng để bán online, ai có xưởng inbox em với", False),
    (G_ADS, "Shop Mẹ Sóc", 5003, "Tài khoản quảng cáo của shop em bị hạn chế hoài, ai có kinh nghiệm cho em hỏi xử lý sao ạ? Shop bán đồ ăn healthy", False),
    (G_ADS, "Dịch Vụ Ads Pro", 5006, "Nhận chạy quảng cáo, bán via BM giá rẻ, inbox em hỗ trợ ngay", False),
    (G_MUA, "Kho Sỉ Trà", 5008, "Chuyên sỉ trà túi lọc tận xưởng, tuyển đại lý toàn quốc", False),
    (("goiy", "Nhóm Gợi Ý Cho Bạn"), "Khách Lạ", 5009, "Cần nhập trà túi lọc số lượng lớn, xin giá sỉ", True),
    (G_ADS, "Shop Thời Trang Vy", 5007, "Shop quần áo của mình chạy ads mãi không ra đơn, ai giúp với?", False),
] + [(G_ADS if i % 2 else G_MUA, f"Thành viên {i}", 5100 + i, t, False) for i, t in enumerate([
    "Hôm nay trời đẹp quá cả nhà ơi", "Chia sẻ công thức nấu chè ngon", "Ai đi Đà Lạt cuối tuần không", "Chúc cả nhóm buôn may bán đắt",
    "Hôm qua mình bán được 30 đơn, vui quá", "Góc khoe con mèo nhà mình", "Mọi người ăn trưa chưa", "Cuối tuần này nghỉ lễ không mọi người",
    "Review quán cà phê mới mở", "Mình mới vào nhóm, chào mọi người"])] + [
    (G_ADS, "Tuấn Shop", 5004, "Mọi người chạy ads tiktok shop ngân sách bao nhiêu thì ra đơn đều vậy?", False),
    (G_ADS, "Phạm Thu", 5002, "Cần nhập ngũ cốc dinh dưỡng số lượng lớn, xin giá sỉ ạ", False),
    (G_ADS, "Lan Livestream", 5005, "Tối nào em cũng livestream bán hàng mà ít đơn quá, có ai chia sẻ kinh nghiệm không ạ?", False),
] + [(G_MUA, f"Bạn đọc {i}", 5200 + i, t, False) for i, t in enumerate([
    "Sáng nay kẹt xe quá", "Tuần này ai săn sale không", "Hội mình đông vui ghê", "Ai biết sửa máy giặt ở Hà Đông không",
    "Chia sẻ ảnh hoàng hôn", "Mình mới mua cây cảnh"])]
FEED_TXT = {1500 + i: r[3] for i, r in enumerate(FEED)}
FEED_CMTS, FEED_HIDE = {}, set()


def feed_page():
    art = lambda i, r: (f'<div role="article"><a href="/groups/{r[0][0]}/">{html.escape(r[0][1])}</a> · '
                        f'<a href="/groups/{r[0][0]}/user/{r[2]}/">{html.escape(r[1])}</a> · <a href="/groups/{r[0][0]}/posts/{1500 + i}/">3 giờ</a>'
                        f'<div>{html.escape(r[3])}</div>' + ('<div role="button">Tham gia</div>' if r[4] else '') + '</div>')
    rows = [art(i, r) for i, r in enumerate(FEED)]
    more = "".join(f"<template>{x}</template>" for x in rows[12:])
    return (f'<h1>Bảng feed</h1><div role="feed" id="feed">{"".join(rows[:12])}</div>{more}'
            '<script>addEventListener("wheel",()=>{[...document.querySelectorAll("template")].slice(0,6).forEach(t=>{'
            'document.getElementById("feed").appendChild(t.content.cloneNode(true)); t.remove();});});</script>')


def group_feed_html(title, rows, slug):
    out = f'<h1>{title}</h1><div role="feed">'
    for i, (a, uid, txt, cmts) in enumerate(rows):
        out += (f'<div role="article"><a href="/groups/{slug}/user/{uid}/">{html.escape(a)}</a> · <a href="/groups/{slug}/posts/{700+i}/">2 giờ</a>'
                f'<div>{html.escape(txt)}</div><span>12 bình luận</span><span>35 lượt thích</span>')
        for ca, cu, ct in cmts:
            out += (f'<div role="article" aria-label="Bình luận của {html.escape(ca)}"><a href="/groups/{slug}/user/{cu}/?comment_id=1">{html.escape(ca)}</a>'
                    f'<div>{html.escape(ct)}</div></div>')
        out += "</div>"
    return out + "</div>"


def group_chosi_html():
    out = '<h1>Chợ Sỉ Thực Phẩm</h1><div role="feed">'
    for i, (a, uid, txt, cmts) in enumerate(GROUP_CHOSI):
        out += (f'<div role="article"><a href="/groups/chosi/user/{uid}/">{html.escape(a)}</a> · <a href="/groups/chosi/posts/{500+i}/">2 giờ</a>'
                f'<div>{html.escape(txt)}</div>')
        for ca, cu, ct in cmts:
            out += (f'<div role="article" aria-label="Bình luận của {html.escape(ca)}"><a href="/groups/chosi/user/{cu}/?comment_id=1">{html.escape(ca)}</a>'
                    f'<div>{html.escape(ct)}</div></div>')
        out += "</div>"
    return out + "</div>"


def search_pages_html(kind):
    cards = '<a href="/me">Trang của bạn</a><a href="/groups/feed/">Nhóm</a><a href="/watch/">Watch</a>'
    for slug, (name, about, links, posts) in SELLERS.items():
        if kind == "posts":
            cards += (f'<div role="article"><a href="/{slug}">{html.escape(name)}</a> · <a href="/{slug}/posts/77">{posts[0][0]}</a>'
                      f'<div>{html.escape(posts[0][1])}</div></div>')
        else:
            cards += (f'<div role="article"><a href="/{slug}?ref=search">{html.escape(name)}</a><span>Trang · Mua sắm</span>'
                      f'<div role="button" aria-label="Thích">Thích</div></div>')
    return f'<h1>Kết quả tìm kiếm</h1><div role="feed">{cards}</div>'


def seller_html(slug):
    name, about, links, posts = SELLERS[slug]
    out = f"<h1>{html.escape(name)}</h1><div><h2>Giới thiệu</h2><div>{html.escape(about)}</div>"
    out += "".join(f'<a href="{html.escape(l)}">{html.escape(l)}</a> ' for l in links) + '<div role="button">Nhắn tin</div></div><div role="feed">'
    for i, (age, txt, c) in enumerate(posts):
        out += (f'<div role="article"><b>{html.escape(name)}</b> · <a href="/{slug}/posts/{i}">{age}</a><div>{html.escape(txt)}</div>'
                f'<span>{c} bình luận</span></div>')
    return out + "</div>"


def _plainq(t):
    import unicodedata
    t = unicodedata.normalize("NFD", t.lower().replace("đ", "d"))
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def search_html(q):
    words = [w for w in _plainq(q).split() if len(w) > 2 and w not in ("hoi", "nhom")]
    cards = '<a href="/groups/feed/">Bảng feed nhóm</a><a href="/groups/discover/">Khám phá</a>'
    for slug, (name, meta, kind) in SEARCH_GROUPS.items():
        if words and not any(w in _plainq(name) for w in words):
            continue
        state = "Truy cập" if slug in JOINED else "Tham gia"
        cards += (f'<div role="article"><a href="/groups/{slug}/" aria-label="ảnh"><img alt=""></a>'
                  f'<div><a href="/groups/{slug}/?ref=search">{html.escape(name)}</a></div><span>{html.escape(meta)}</span>'
                  f'<div role="button" aria-label="{state}">{state}</div></div>')
    return f'<h1>Kết quả tìm kiếm</h1><div role="feed">{cards}</div>'


def group_page(slug):
    name, meta, kind = SEARCH_GROUPS[slug]
    if slug in JOINED:
        return f"<h1>{html.escape(name)}</h1>" + REAL % {"label": "Bạn viết gì đi...", "next": "false"} + feed(f"/groups/{slug}", f"/groups/{slug}/posts/{{id}}")
    if slug in REQUESTED:
        return f'<h1>{html.escape(name)}</h1><div role="button" aria-label="Hủy yêu cầu">Hủy yêu cầu</div>'
    js = ("document.getElementById('j').onclick=()=>{"
          + ("const d=document.createElement('div');d.setAttribute('role','dialog');d.innerHTML='<h2>Trả lời câu hỏi</h2><p>Bạn bán hàng gì?</p><div role=textbox contenteditable=true></div>';document.body.appendChild(d);document.addEventListener('keydown',e=>{if(e.key==='Escape')d.remove()});"
             if kind == "questions" else f"fetch('/join',{{method:'POST',body:JSON.stringify({{slug:'{slug}'}})}}).then(()=>location.reload());")
          + "};")
    return (f'<h1>{html.escape(name)}</h1><div role="button" id="j" aria-label="Tham gia nhóm">Tham gia nhóm</div><script>{js}</script>'
            + (public_feed(slug) if kind == "public" else "<p>Tham gia nhóm để xem bài viết</p>"))


def comments_html(pid):
    out = ""
    for i, (a, t) in enumerate(SEED_COMMENTS + [c for c in EXTRA if c[2] == pid for c in [c] ][:0] + [(c[0], c[1]) for c in EXTRA if c[2] == pid]):
        out += (f'<div role="article" aria-label="Bình luận của {html.escape(a)} 5 phút trước"><a href="/u/{i}">{html.escape(a)}</a>'
                f'<div>{html.escape(t)}</div><span>5 phút</span><div role="button" class="rep" data-a="{html.escape(a)}">Phản hồi</div></div>')
    return out + """<script>document.querySelectorAll('.rep').forEach(b=>b.onclick=()=>{const tb=document.createElement('div');
tb.setAttribute('role','textbox');tb.contentEditable='true';tb.setAttribute('aria-label','Trả lời '+b.dataset.a);b.after(tb);tb.focus();
tb.addEventListener('keydown',async e=>{if(e.key==='Enter'){e.preventDefault();await fetch('/reply',{method:'POST',body:JSON.stringify({to:b.dataset.a,text:tb.innerText})});tb.remove();}});});</script>"""


EXTRA = []  # (author, text, post_id)

COMMENT = """<div id="cmt"><div role="textbox" contenteditable="true" aria-label="Viết bình luận công khai..." style="border:1px solid #aaa;min-height:30px"></div>
<div role="button" aria-label="Đính kèm ảnh hoặc video" id="att">📷</div><input type="file" accept="image/*,video/*" id="fi" style="display:none"></div>
<div id="comments"></div>
<script>
const box=document.querySelector('#cmt [role=textbox]'), fi=document.getElementById('fi');
document.getElementById('att').onclick=()=>fi.click();
fi.onchange=()=>showPreviews(document.getElementById('cmt'), fi.files);
box.addEventListener('keydown', async e=>{ if(e.key==='Enter'&&!e.shiftKey){ e.preventDefault();
  await fetch('/comment',{method:'POST',body:JSON.stringify({post:%(id)s,text:box.innerText,files:[...fi.files].map(f=>f.name)})});
  document.getElementById('comments').innerText='Đã bình luận'; box.innerText=''; }});
</script>"""


# Ô bình luận kiểu Facebook 2026: nút "Đính kèm MỘT ảnh hoặc video", ô tệp nằm trong <form> của bình luận,
# trên trang còn khung "Ảnh/video" của hộp đăng bài (ô tệp riêng, không hiện ảnh xem trước vào bình luận),
# ảnh xem trước là <div style="background-image:url(blob:...)"> trong form; chữ mờ "Viết bình luận..." mất khi gõ.
COMMENT26 = """<div id="topcomp"><div role="button" id="tpa">Ảnh/video</div><input type="file" accept="image/*,image/heif,image/heic,video/*" id="tpf" style="display:none"></div>
<div id="zone"><div><form id="cmt" onsubmit="return false"><div style="position:relative"><div id="ph" style="position:absolute;pointer-events:none;color:#888">Viết bình luận...</div>
<div role="textbox" contenteditable="true" aria-label="Bình luận dưới tên Linh Nguyễn" style="border:1px solid #aaa;min-height:30px"></div></div>
<div><div role="button" aria-label="Chèn emoji">🙂</div><div role="button" aria-label="Đính kèm một ảnh hoặc video" id="att">📷</div>
<div role="button" aria-label="Bình luận" id="send" aria-disabled="true">➤</div>
<input type="file" multiple accept="video/*,  video/x-m4v, video/webm, image/*, image/heic, image/heif" id="fi" style="position:absolute;opacity:0;width:1px;height:1px"></div></form></div>
<div id="pv"></div></div>
<div id="comments"></div>
<script>
const box=document.querySelector('#cmt [role=textbox]'), fi=document.getElementById('fi'), send=document.getElementById('send');
let uploading=false, files=[];
document.getElementById('tpa').onclick=()=>document.getElementById('tpf').click();
document.getElementById('att').onclick=()=>fi.click();
const upd=()=>{ document.getElementById('ph').style.display=box.innerText.trim()?'none':''; send.setAttribute('aria-disabled', (uploading||(!box.innerText.trim()&&!files.length))?'true':'false'); };
box.addEventListener('input',upd);
fi.onchange=()=>{ files=[...fi.files]; uploading=true; upd(); setTimeout(()=>{ for(const f of files){ const d=document.createElement('div'); d.style.cssText='width:80px;height:80px;opacity:.5;background-size:cover;background-image:url('+URL.createObjectURL(f)+')';
  const x=document.createElement('div'); x.setAttribute('role','button'); x.setAttribute('aria-label','Xóa'); x.innerText='×'; d.appendChild(x); document.getElementById('pv').appendChild(d);} }, 1500);
  setTimeout(()=>{ uploading=false; document.querySelectorAll('#pv div').forEach(d=>d.style.opacity=1); upd(); }, window.UPLOAD_MS||12000); };
async function doSend(){ if(uploading) return; if(send.getAttribute('aria-disabled')==='true') return;
  await fetch('/comment',{method:'POST',body:JSON.stringify({post:%(id)s,text:box.innerText,files:files.map(f=>f.name)})});
  document.getElementById('comments').innerText='Đã bình luận'; box.innerText=''; files=[]; document.getElementById('pv').innerHTML=''; upd(); }
send.onclick=doSend;
box.addEventListener('keydown', e=>{ if(e.key==='Enter'&&!e.shiftKey){ e.preventDefault(); doSend(); }});
</script>"""


def modern_feed(where, link_fmt, pending=False):
    """Bảng tin kiểu Facebook mới: không có role=article, link mốc thời gian chỉ hiện khi rê chuột."""
    arts = "".join(f'<div aria-posinset="{i+1}" aria-setsize="-1"><div><a href="/profile.php?id=100001">Linh Nguyễn</a>'
                   f'<span><a href="#" data-h="{link_fmt.format(id=p["id"])}/?__cft__[0]=AZx&__tn__=%2CO%2CP-R" '
                   f'onmouseover="this.href=this.dataset.h" onfocus="this.href=this.dataset.h" aria-label="2 phút">2 phút</a></span></div>'
                   f'<div data-ad-preview="message"><div dir="auto">{html.escape(p["text"][:200])}</div>… Xem thêm</div>'
                   f'<a href="/groups/modern/">Nhóm hiện đại</a><a href="#">Thích</a><a href="#">Bình luận</a>'
                   + (f'<div role="article" aria-label="Bình luận của Trần Minh"><a href="{link_fmt.format(id=p["id"])}/?comment_id=5">1 giờ</a>ib giá sỉ</div>' if MODE.get("comments") else "")
                   + '</div>'
                   for i, p in enumerate(reversed([q for q in POSTS if q["where"] == where and bool(q.get("pending")) == pending])))
    return f'<div role="feed">{arts}</div>'


def feed(where, link_fmt):
    arts = "".join(f'<div role="article"><a href="{link_fmt.format(id=p["id"])}?__cft__=abc&__tn__=R">2 phút</a>'
                   f'<div>{html.escape(p["text"][:200])}… Xem thêm</div></div>'
                   for p in reversed(POSTS) if p["where"] == where)
    return f'<div role="feed">{arts}</div>'


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _html(self, body, code=200, headers=()):
        self.send_response(code)
        self.send_header("content-type", "text/html; charset=utf-8")
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(f"<!doctype html><html><head><meta charset='utf-8'>{PREVIEW_JS}</head><body>{body}</body></html>".encode())

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/") or "/"
        if path.startswith("/setlogin"):
            return self._html("ok", headers=[("Set-Cookie", "c_user=100001; Path=/; Max-Age=999999")])
        if path == "/groups/joins" and MY["on"]:
            return self._html(joins_html())
        if path == "/groups/chosi":
            return self._html(group_chosi_html())
        if path == "/groups/hoimua":
            return self._html(hoimua_html())
        mh = re.match(r"^/groups/hoimua/posts/(\d+)$", path)
        if mh and int(mh.group(1)) in HOIMUA_TXT:
            pid = int(mh.group(1))
            return self._html(f'<div role="article"><div>{html.escape(HOIMUA_TXT[pid])}</div><span>24 bình luận</span></div>'
                              + (COMMENT26 if MODE.get("cmt") == "fb26" else COMMENT) % {"id": pid})
        if path == "/groups/feed":
            return self._html(feed_page())
        mf = re.match(r"^/groups/\w+/posts/(\d+)$", path)
        if mf and int(mf.group(1)) in FEED_TXT:
            pid = int(mf.group(1))
            cm = "" if pid in FEED_HIDE else "".join(f'<div role="article"><b>Linh Nguyễn</b><div>{html.escape(t)}</div></div>'
                                                     for t in FEED_CMTS.get(pid, []))
            return self._html(f'<div role="article"><div>{html.escape(FEED_TXT[pid])}</div></div>{cm}' + COMMENT26 % {"id": pid})
        if path == "/groups/shoponline":
            return self._html(group_feed_html("Hội Bán Hàng Online", GROUP_SHOP, "shoponline"))
        mu = re.match(r"^/profile\.php$", path)
        if mu:
            return self._html('<h1>Trang cá nhân</h1><div role="button" aria-label="Thêm bạn bè">Thêm bạn bè</div>')
        if path.startswith("/groups/blocked"):
            return self._html("", 302, [("Location", "/checkpoint/123")])
        if path.startswith("/checkpoint"):
            return self._html("<h1>Xác nhận danh tính</h1>")
        m = re.match(r"^/groups/(\w+)/(?:posts|permalink)/(\d+)$", path) or re.match(r"^/posts/pfbid(\d+)$", path)
        if m:
            pid = int(m.groups()[-1])
            if pid in REMOVED or not any(p["id"] == pid and not p.get("pending") for p in POSTS):
                return self._html("<h2>Nội dung này hiện không hiển thị</h2>")
            p = next(p for p in POSTS if p["id"] == pid)
            return self._html(f'<div role="article"><div>{html.escape(p["text"])}</div><span>3 bình luận</span></div>' + comments_html(pid) + ((COMMENT26 if MODE.get("cmt") == "fb26" else COMMENT) % {"id": pid}))
        if path.startswith("/search/groups"):
            from urllib.parse import urlparse, parse_qs
            return self._html(search_html(parse_qs(urlparse(self.path).query).get("q", [""])[0]))
        ma = re.match(r"^/groups/([\w-]+)/about$", path)
        if ma and ma.group(1) in SEARCH_GROUPS:
            return self._html(about_page(ma.group(1)))
        m2 = re.match(r"^/groups/([\w-]+)$", path)
        if m2 and m2.group(1) in SEARCH_GROUPS:
            if MY["on"] and m2.group(1) in MY["groups"]:
                return self._html(my_group_page(m2.group(1)))
            return self._html(group_page(m2.group(1)))
        if path == "/groups/notmember":
            return self._html('<h1>Nhóm riêng tư</h1><div role="button" aria-label="Tham gia nhóm">Tham gia nhóm</div>')
        if path in ("/groups/modern", "/groups/modern/my_posted_content"):
            comp = (MODERN_COMPOSER % {"send": MODERN_SEND}) if path == "/groups/modern" else ""
            return self._html(f"<script>window.PENDING={'true' if MODE['pending'] else 'false'};window.DROPZONE={'true' if MODE.get('dropzone') else 'false'};window.NOPREVIEW={'true' if MODE.get('nopreview') else 'false'}</script>"
                              f"<h1>Nhóm hiện đại</h1>" + comp
                              + modern_feed("/groups/modern", "/groups/modern/posts/{id}"))
        if path == "/groups/modern/my_pending_content":
            return self._html("<h1>Đang chờ</h1>" + modern_feed("/groups/modern", "/groups/modern/pending/{id}", pending=True))
        if path == "/groups/real":
            return self._html("<h1>Nhóm thật</h1>" + REAL % {"label": "Bạn viết gì đi...", "next": "false"} + feed("/groups/real", "/groups/real/posts/{id}"))
        if path == "/realme":
            return self._html(REAL % {"label": "Bạn đang nghĩ gì, Linh?", "next": "true"} + feed("/realme", "/posts/pfbid{id}"))
        m = re.match(r"^/groups/(\w+)(/my_posted_content)?$", path)
        if m:
            g = f"/groups/{m.group(1)}"
            top = "" if m.group(2) else COMPOSER % {"label": "Viết gì đó..."}
            return self._html(f"<h1>Nhóm {m.group(1)}</h1>{top}{feed(g, g + '/posts/{id}')}")
        if path.startswith("/groups/") and path.endswith("/my_pending_content"):
            return self._html("<h1>Đang chờ</h1>")
        if path.startswith("/ads/library"):
            return self._html(ads_html())
        if path == "/profile.php":
            from urllib.parse import urlparse, parse_qs
            uid = parse_qs(urlparse(self.path).query).get("id", [""])[0]
            if uid == "2001":
                return self._html('<h1>Phạm Thu Hương</h1><div>Bán hàng online đồ ăn healthy, ship toàn quốc</div><div role="feed">'
                                  '<div role="article"><b>Phạm Thu Hương</b> · <a href="#">1 ngày</a><div>Lên đơn hạt dinh dưỡng cho khách, inbox đặt hàng</div><span>4 bình luận</span></div></div>')
            return self._html(f"<h1>Người dùng {uid}</h1>")
        if path.startswith("/search/pages") or path.startswith("/search/posts"):
            return self._html(search_pages_html("posts" if "posts" in path else "pages"))
        mab = re.match(r"^/([\w.]+)/(about|about_contact_and_basic_info)$", path)
        if mab and mab.group(1) in SELLERS:
            body = "<h1>Giới thiệu</h1><h2>Thông tin liên hệ</h2>"
            if mab.group(1) == "bepnhamy" and mab.group(2) == "about_contact_and_basic_info":
                body += "<div>Di động</div><div>0912 888 999</div><div>Email</div><div>bepnhamy.vidu@gmail.com</div>"
            return self._html(body)
        if path.strip("/") in SELLERS:
            return self._html(seller_html(path.strip("/")))
        if path == "/me":
            return self._html(COMPOSER % {"label": "Bạn đang nghĩ gì?"} + feed("/me", "/posts/pfbid{id}"))
        return self._html("<h1>Facebook giả lập</h1>")

    def do_POST(self):
        n = int(self.headers.get("content-length", 0))
        raw = self.rfile.read(n).decode()
        if self.path.startswith("/api/graphql"):
            last = POSTS[-1] if POSTS else {"id": 0}
            if MODE["graphql"] == "url" and not last.get("pending"):
                body = {"data": {"story_create": {"story": {"id": "UzpfS", "url": f"http://localhost:8098/groups/modern/permalink/{last['id']}/",
                                                             "legacy_story_hideable_id": str(last["id"])}}}}
            elif MODE["graphql"] == "id" or last.get("pending"):
                body = {"data": {"story_create": {"story": None, "post_id": str(last["id"]) * 2 if False else f"{last['id']:06d}",
                                                  "is_pending": bool(last.get("pending"))}}}
            else:
                body = {"data": {"story_create": None}}
            out = json.dumps(body).replace("/", "\\/").encode()
            self.send_response(200); self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(out)
            return
        d = json.loads(raw)
        if self.path == "/mockmode":
            MODE.update(d)
        if self.path == "/approve_post":
            for p in POSTS:
                if p["id"] == d["id"]:
                    p["pending"] = False
        if self.path == "/mygroups":
            MY["on"] = bool(d.get("on", True))
        if self.path == "/leave":
            MY["groups"].pop(d["slug"], None); MY["left"].append(d["slug"])
        if self.path == "/record":
            d["id"] = 1000 + len(POSTS)
            if MODE["pending"] and d.get("where") == "/groups/modern":
                d["pending"] = True
            POSTS.append(d)
        if self.path == "/join":
            kind = SEARCH_GROUPS[d["slug"]][2]
            (JOINED if kind == "public" else REQUESTED).add(d["slug"])
        if self.path == "/approve":
            REQUESTED.discard(d["slug"]); JOINED.add(d["slug"])
        if self.path == "/remove":
            REMOVED.add(d["id"])
        if self.path == "/addcomment":
            EXTRA.append((d["author"], d["text"], d["post"]))
        if self.path == "/comment" and isinstance(d.get("post"), int):
            FEED_CMTS.setdefault(d["post"], []).append(d.get("text") or "")
        if self.path == "/hidecmt":
            FEED_HIDE.add(d["post"])
        if self.path == "/reply":
            REPLIES.append(d)
        with open(f"{SP}/mockfb_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"path": self.path, **d}, ensure_ascii=False) + "\n")
        self._html("ok")


HTTPServer(("127.0.0.1", 8098), H).serve_forever()
