  /* Mai: khách sỉ tìm được (tên shop là ví dụ, không có thật) */
  const ev=(kind,text,url)=>({kind,text,url});
  S.prSet={prospect_enabled:"1",prospect_time:"14:30",prospect_inspect_per_run:"8",prospect_facebook:"1",prospect_tiktok:"0",prospect_shopee:"0",prospect_fb_keywords:"2",prospect_ads:"1",prospect_groups:"1",prospect_groups_per_run:"3",prospect_auto_crm:"1",prospect_ai_script:"1"};
  S.prKw={1:["livestream bán trà","live bán ngũ cốc","livestream đồ ăn healthy","live bán thực phẩm sạch"],2:["shop trà túi lọc","bán bột ngũ cốc online","shop đồ ăn healthy","shop cà phê online"],3:["shop tạp hóa online","shop mẹ và bé online","bán hàng đa kênh shopee tiktok"],4:["tuyển đại lý thực phẩm","tìm nguồn hàng trà","nhận phân phối thực phẩm","tìm nguồn hàng sỉ ngũ cốc"],5:["trà túi lọc","ngũ cốc dinh dưỡng","granola","trà thảo mộc","bột ngũ cốc","đồ ăn healthy"]};
  S.pr=[
    {id:7,platform:"facebook",account_name:"Ngọc Hân (ví dụ)",account_url:"https://www.facebook.com/profile.php?id=100000000000007",seller_type:"buyer",tags:"buyer,owner",direction:6,keyword:"Chợ Sỉ Thực Phẩm Khô",
     recent_activity:"Bài mới nhất cách đây 2 giờ",phone:"0903000444",products:"Đang bán đồ ăn healthy online",categories:"Trà, cà phê, đồ uống, ngũ cốc, healthy",score:71,grade:"A",parts:{sales:14,live:0,fit:20,import:15,engage:7,contact:5,expand:0},status:"verified",lead_id:24,
     evidence:[ev("demand","Hỏi nguồn hàng: Mình đang tìm nguồn trà túi lọc, ngũ cốc giá sỉ để bán online, ai có xin gọi 0903 000 444","https://www.facebook.com/groups/vidu/posts/1"),ev("contact","SĐT họ tự ghi: 0903000444","https://www.facebook.com/groups/vidu/posts/1"),ev("sell","Bán hàng online đồ ăn healthy, ship toàn quốc","https://www.facebook.com/profile.php?id=100000000000007")],
     suggested:[{id:1,name:"Trà gừng mật ong túi lọc",why:"đúng nhóm hàng họ đang tìm"},{id:3,name:"Bột ngũ cốc dinh dưỡng 25 loại hạt",why:"đúng nhóm hàng họ đang tìm"}],
     approach:"Chào Ngọc Hân, em là Hà bên Xưởng Trà & Bột. Em thấy chị đang tìm nguồn trà túi lọc trong nhóm. Bên em là xưởng sản xuất trà gừng mật ong túi lọc và bột ngũ cốc, bán sỉ tận xưởng cho người bán online, có ảnh và video thật để đăng bán. Chị đang cần loại nào và số lượng khoảng bao nhiêu để em gửi bảng giá phù hợp ạ?",
     next_action:"Gọi hoặc nhắn Zalo 0903000444 theo kịch bản trong 24 giờ",created_at:"2026-11-04 14:44:00"},
    {id:8,platform:"facebook",account_name:"Granola Nhà Gạo (ví dụ)",shop_name:"Granola Nhà Gạo",account_url:"https://www.facebook.com/granolanhagao.vidu",seller_type:"owner",tags:"ads,owner",direction:5,keyword:"granola",
     recent_activity:"Bài mới nhất cách đây 1 ngày",phone:"0903000555",products:"Granola, ngũ cốc hạt",categories:"Trà, cà phê, đồ uống, ngũ cốc, healthy",score:66,grade:"B",parts:{sales:16,live:0,fit:20,import:9,engage:6,contact:10,expand:5},status:"verified",lead_id:25,
     evidence:[ev("ads","Đang chạy quảng cáo (3 quảng cáo): Granola hạt giòn tan, giao toàn quốc, hotline 0903 000 555","https://www.facebook.com/ads/library/"),ev("sell","Combo 2 hũ granola giá 230k, freeship, inbox đặt hàng","https://www.facebook.com/granolanhagao.vidu")],
     suggested:[{id:3,name:"Bột ngũ cốc dinh dưỡng 25 loại hạt",why:"đúng nhóm hàng họ đang bán"}],
     approach:"Chào Granola Nhà Gạo, em là Hà bên Xưởng Trà & Bột. Em thấy bên mình đang chạy quảng cáo bán ngũ cốc trên Facebook. Bên em là xưởng sản xuất bột ngũ cốc 25 loại hạt, có giá sỉ tận xưởng để shop thêm vào danh mục và có sẵn ảnh, video thật làm quảng cáo. Nếu shop quan tâm, em gửi bảng giá để mình xem trước ạ.",
     next_action:"Gọi hoặc nhắn Zalo 0903000555 theo kịch bản",created_at:"2026-11-04 14:43:30"},
    {id:1,platform:"facebook",account_name:"Bếp Nhà Mây (ví dụ)",shop_name:"Bếp Nhà Mây – Ngũ cốc & Trà",account_url:"https://www.facebook.com/bepnhamay.vidu",shop_url:"https://shopee.vn/shop/100000001",seller_type:"live",tags:"live,multi,owner",direction:1,keyword:"live bán ngũ cốc",
     recent_activity:"Bài mới nhất cách đây 3 giờ",live_freq:"3/5 bài gần nhất là phát trực tiếp",followers:18000,phone:"0903000111",zalo:"https://zalo.me/0903000111",email:null,products:"Shop mình chuyên ngũ cốc hạt, trà thảo mộc, granola",categories:"Trà, cà phê, đồ uống, ngũ cốc, healthy",
     import_signals:"Hàng mới về mỗi tuần, shop nhập số lượng lớn nên giá tốt",score:92,grade:"A",parts:{sales:20,live:20,fit:20,import:12,engage:10,contact:8,expand:2},status:"verified",lead_id:21,
     evidence:[ev("live","Bếp Nhà Mây đã phát trực tiếp · Live chốt đơn granola, freeship từ 2 hũ","https://www.facebook.com/bepnhamay.vidu"),ev("sell","Nhận đơn ship COD toàn quốc, inbox chốt đơn","https://www.facebook.com/bepnhamay.vidu"),ev("import","Hàng mới về mỗi tuần, shop nhập số lượng lớn nên giá tốt","https://www.facebook.com/bepnhamay.vidu"),ev("fit_core","Shop mình chuyên ngũ cốc hạt, trà thảo mộc, granola","https://www.facebook.com/bepnhamay.vidu"),ev("contact","SĐT công khai trên trang: 0903000111","https://www.facebook.com/bepnhamay.vidu"),ev("shop_link","Link gian hàng/tài khoản khác: https://shopee.vn/shop/100000001","https://shopee.vn/shop/100000001")],
     suggested:[{id:3,name:"Bột ngũ cốc dinh dưỡng 25 loại hạt",why:"đúng nhóm hàng họ đang bán"},{id:1,name:"Trà gừng mật ong túi lọc",why:"sản phẩm xưởng đang bán chạy"}],
     approach:"Chào Bếp Nhà Mây, em là Hà bên Xưởng Trà & Bột. Em thấy bên mình đang livestream bán ngũ cốc trên Facebook. Bên em là xưởng sản xuất bột ngũ cốc 25 loại hạt và trà gừng mật ong túi lọc, có giá sỉ cho người bán online và có sẵn ảnh, video thật để đăng bán. Nếu shop quan tâm, em gửi bảng giá để mình xem trước ạ?",
     next_action:"Gọi hoặc nhắn Zalo 0903000111 theo kịch bản trong 24 giờ",created_at:"2026-11-04 14:42:00"},
    {id:2,platform:"facebook",account_name:"Mộc Gia Mart (ví dụ)",shop_name:"Mộc Gia Mart – Tạp hóa online",account_url:"https://www.facebook.com/mocgiamart.vidu",shop_url:"https://www.tiktok.com/@mocgiamart.vidu",seller_type:"multi",tags:"multi,marketplace,owner",direction:3,keyword:"bán hàng đa kênh shopee tiktok",
     recent_activity:"Bài mới nhất cách đây 6 giờ",live_freq:"",followers:7400,phone:"0903000222",zalo:null,email:"mocgia.vidu@gmail.com",products:"Đồ ăn vặt, bánh kẹo, đồ dùng mẹ và bé",categories:"Thực phẩm, đồ ăn vặt, đặc sản; Hàng tiêu dùng khác",
     import_signals:"Tìm nhà cung cấp đồ uống, trà để mở thêm danh mục",score:71,grade:"B",parts:{sales:20,live:0,fit:12,import:15,engage:7,contact:9,expand:5},status:"verified",lead_id:22,
     evidence:[ev("import","Tìm nhà cung cấp đồ uống, trà để mở thêm danh mục","https://www.facebook.com/mocgiamart.vidu"),ev("sell","Hàng về bánh kẹo, inbox nhận báo giá, ship COD","https://www.facebook.com/mocgiamart.vidu"),ev("fit_food","Đồ ăn vặt, bánh kẹo, đồ dùng mẹ và bé","https://www.facebook.com/mocgiamart.vidu"),ev("shop_link","Link gian hàng/tài khoản khác: https://www.tiktok.com/@mocgiamart.vidu","https://www.tiktok.com/@mocgiamart.vidu")],
     suggested:[{id:1,name:"Trà gừng mật ong túi lọc",why:"đúng nhóm hàng họ đang tìm thêm"},{id:3,name:"Bột ngũ cốc dinh dưỡng 25 loại hạt",why:"sản phẩm xưởng đang bán chạy"}],
     approach:"Chào Mộc Gia Mart, em là Hà bên Xưởng Trà & Bột. Em thấy shop đang tìm thêm nhà cung cấp trà, đồ uống. Bên em là xưởng sản xuất trà túi lọc và bột ngũ cốc, có giá sỉ cho người bán online. Shop có muốn em gửi bảng giá và ảnh sản phẩm để tham khảo không ạ?",
     next_action:"Gọi hoặc nhắn Zalo 0903000222 theo kịch bản",created_at:"2026-11-04 14:40:00"},
    {id:6,platform:"facebook",account_name:"Hạt Xinh Shop (ví dụ)",shop_name:"Hạt Xinh Shop – Hạt dinh dưỡng",account_url:"https://www.facebook.com/hatxinhshop.vidu",seller_type:"live",tags:"live,owner",direction:1,keyword:"livestream đồ ăn healthy",
     recent_activity:"Bài mới nhất cách đây 5 giờ",live_freq:"2/4 bài gần nhất là phát trực tiếp",followers:3100,phone:null,zalo:null,email:null,products:"Hạt dinh dưỡng, granola, sữa hạt",categories:"Trà, cà phê, đồ uống, ngũ cốc, healthy",
     score:72,grade:"B",parts:{sales:20,live:20,fit:20,import:9,engage:7,contact:2,expand:0},status:"verified",lead_id:null,
     evidence:[ev("live","Hạt Xinh Shop đã phát trực tiếp · Live xả hàng hạt điều rang muối","https://www.facebook.com/hatxinhshop.vidu"),ev("sell","Inbox chốt đơn, ship toàn quốc","https://www.facebook.com/hatxinhshop.vidu")],
     suggested:[{id:3,name:"Bột ngũ cốc dinh dưỡng 25 loại hạt",why:"đúng nhóm hàng họ đang bán"}],approach:"",
     next_action:"Chưa tìm thấy SĐT công khai (đã đọc cả trang Giới thiệu). Mai sẽ quay lại tìm tiếp; sếp có thể nhắn trang để xin SĐT",created_at:"2026-11-04 14:39:00"},
    {id:3,platform:"facebook",account_name:"Ăn Lành Cùng Thảo (ví dụ)",shop_name:"Ăn Lành Cùng Thảo",account_url:"https://www.facebook.com/anlanhcungthao.vidu",seller_type:"affiliate",tags:"affiliate,koc",direction:2,keyword:"shop đồ ăn healthy",
     recent_activity:"Bài mới nhất cách đây 1 ngày",live_freq:"",followers:42000,phone:null,zalo:null,email:null,products:"Review granola, trà detox",categories:"Trà, cà phê, đồ uống, ngũ cốc, healthy",
     import_signals:"",score:47,grade:"C",parts:{sales:14,live:0,fit:20,import:0,engage:10,contact:2,expand:1},status:"verified",lead_id:null,
     evidence:[ev("affiliate","Unbox granola siêu ngon. Link mua ở bình luận nha","https://www.facebook.com/anlanhcungthao.vidu"),ev("koc","Hợp tác quảng cáo, booking inbox","https://www.facebook.com/anlanhcungthao.vidu"),ev("fit_core","Review trà detox mới, uống thử 1 tuần","https://www.facebook.com/anlanhcungthao.vidu")],
     suggested:[{id:3,name:"Bột ngũ cốc dinh dưỡng 25 loại hạt",why:"đúng nhóm hàng họ đang bán"}],approach:"",
     next_action:"Affiliate/KOC, chưa có bằng chứng tự nhập hàng: chỉ theo dõi, không chào giá sỉ",created_at:"2026-11-04 14:38:00"},
    {id:4,platform:"tiktok",account_name:"Mẹ Bin Shop (ví dụ)",account_url:"https://www.tiktok.com/@mebinshop.vidu",status:"needs_manual",direction:1,keyword:"livestream bán trà",evidence:[ev("found","Mẹ Bin Shop · Live bán trà sữa hạt mỗi tối","https://www.tiktok.com/@mebinshop.vidu")],suggested:[],parts:{},
     next_action:"Sếp mở link xem tay (nền tảng yêu cầu đăng nhập/xác minh, phần mềm không vượt qua)",created_at:"2026-11-04 14:36:00"},
    {id:5,platform:"facebook",account_name:"Tạp hóa Cô Ba (ví dụ)",account_url:"https://www.facebook.com/taphoacoba.vidu",seller_type:"store",tags:"store",direction:3,keyword:"shop tạp hóa online",recent_activity:"Bài mới nhất cách đây 75 ngày",score:14,grade:"D",parts:{sales:0,live:0,fit:5,import:3,engage:0,contact:4,expand:2},status:"verified",
     evidence:[ev("found","Cửa hàng tại chợ Bến Thành, mở cửa từ 6h sáng","https://www.facebook.com/taphoacoba.vidu")],suggested:[],approach:"",next_action:"Cửa hàng truyền thống, không thấy bán online: không ưu tiên",created_at:"2026-11-04 14:35:00"}];
  S.mgSet={mygroups_enabled:"1",mygroups_time:"09:15",auto_leave:"1",leave_per_nick_day:"3",new_group_rest_days:"7",admin_posts_min:"5",admin_posts_max:"10",admin_sell_share:"50"};
  const mgRow=(gid,acc,nick,name,role,origin,verdict,score,members,note,extra)=>({group_id:gid,account_id:acc,nick,name,url:"https://www.facebook.com/groups/vidu"+gid,role,origin,status:verdict==="left"?"left":"joined",verdict,eng_score:score,members,verdict_note:note,pinned:0,joined_at:"2026-11-02 10:00:00",...(extra||{})});
  S.mg=[mgRow(901,1,"Linh Nguyễn","Hội Sỉ Trà & Ngũ Cốc Xưởng Mình (ví dụ)","admin","existing","manage",66,3200,"Nick là quản trị viên: chăm sóc nhóm, đăng đều mỗi ngày",{today:4,target:8}),
    mgRow(902,1,"Linh Nguyễn","Nguồn Hàng Sỉ Thực Phẩm Tận Xưởng","member","existing","post",74,98500,"Mạnh: 21 bài/ngày, mỗi bài TB 24 cảm xúc, 7 bình luận, có bài mới trong giờ qua"),
    mgRow(903,2,"Phương Sỉ Tận Gốc","Mẹ Bỉm Sữa Kinh Doanh Online","member","existing","keep",52,310000,"Mạnh: 40 bài/ngày; Yếu: mỗi bài TB 6 cảm xúc, 2 bình luận (chuẩn 20 cảm xúc, 5 bình luận)"),
    mgRow(904,1,"Linh Nguyễn","Cộng Đồng Bán Hàng Online Toàn Quốc","member","app","rest",69,520000,"Nick mới vào nhóm, nghỉ đến 09/11 rồi mới đăng.",{rest_until:"2026-11-09"}),
    mgRow(905,2,"Phương Sỉ Tận Gốc","Hội Du Lịch Bụi","member","existing","leave",63,500000,"Loại: nhóm không liên quan bán hàng, nguồn hàng hay thực phẩm"),
    mgRow(906,1,"Linh Nguyễn","Quảng Cáo Facebook 2019","member","existing","left",36,15000,"Loại: nhóm gần như không còn hoạt động (bài mới nhất cách đây 730 ngày)",{left_at:"2026-11-04 09:20:00"})];
  const TPL_DEFAULT=`MỘC TÂM
Nhận gia công & sỉ toàn quốc các dòng Trà Túi Lọc, Cafe Hòa Tan, Cốm, Bột Thiên Nhiên...
Sản xuất tại nhà máy đạt các tiêu chuẩn GMP – ISO – FDA – VSATTP
Hơn 100+ mã sản phẩm đa dạng:
Trà thảo mộc • Cafe • Ngũ cốc
Bột • Cốm • Detox • Các dòng thảo mộc...
Nhiều sản phẩm đang được thị trường và các nền tảng TMĐT quan tâm.
Nhận sỉ & gia công trọn gói:
• Bỏ sỉ toàn quốc
• Gia công thương hiệu riêng
• Thiết kế bao bì theo yêu cầu
• Hỗ trợ xây dựng & phát triển sản phẩm
• Hỗ trợ từ khâu sản xuất đến hoàn thiện sản phẩm
Phù hợp cho shop online, đại lý, nhà phân phối, người mới bắt đầu kinh doanh và các thương hiệu muốn phát triển sản phẩm riêng.
Cần catalog sản phẩm + bảng giá sỉ/gia công, ib trực tiếp để được tư vấn.
{số điện thoại}`;
  S.tpl={template:TPL_DEFAULT,enabled:true,made:0};
  function tplVariant(tpl){ const R=a=>a[Math.floor(Math.random()*a.length)]; const sym=R(["•","✅","✔️","🔹","▪️"]);
    const EM=[[/gia công|sỉ toàn quốc|nhận sỉ/i,["🏭","📦","🤝"]],[/gmp|iso|fda|tiêu chuẩn|nhà máy/i,["✅","🏅","🛡️"]],[/mã sản phẩm|đa dạng/i,["🌿","🍃","📋"]],[/trà|cafe|ngũ cốc|bột|cốm/i,["🍵","☕","🌾"]],[/thị trường|tmđt/i,["🔥","📈","🛒"]],[/phù hợp|dành cho/i,["👉","🎯","🙌"]],[/catalog|bảng giá|ib|tư vấn/i,["📩","💬","📲"]]];
    const out=[], bl=[]; const flush=()=>{ if(bl.length){ bl.sort(()=>Math.random()-.5); out.push(...bl.splice(0)); } };
    tpl.split("\n").filter(l=>!/^\s*(ẩn bớt|xem thêm)\s*$/i.test(l)).forEach((raw,i)=>{ let l=raw.trim();
      if(/\{\s*(số điện thoại|phone|sđt|zalo)\s*\}/i.test(l)){ flush(); out.push(`📞 Zalo/ĐT: ${ZALO()}`); return; }
      if(!l){ flush(); out.push(""); return; }
      if(/^[•\-✅✔▪+]/.test(l)){ bl.push(`${sym} ${l.replace(/^[•\-✅✔️▪+\s]+/,"")}`); return; }
      flush(); if(i===0&&l.length<=40){ out.push(R(["🌿 ","✨ ","🏭 ",""])+l.toUpperCase()); return; }
      const m=EM.find(([rx])=>rx.test(l)); out.push(m&&Math.random()<.85?`${R(m[1])} ${l}`:l); });
    flush(); const hook=R(["📣 TÌM ĐỐI TÁC SỈ & GIA CÔNG","🤝 KẾT NỐI SHOP ONLINE – ĐẠI LÝ – NHÀ PHÂN PHỐI","🔎 Shop nào đang tìm nguồn hàng tận xưởng?",""]);
    let txt=(hook?hook+"\n\n":"")+out.join("\n").trim(); if(!txt.includes(ZALO())) txt+=`\n📞 Zalo/ĐT: ${ZALO()}`;
    return txt+"\n\n"+["#nguonhangsi","#giacong","#tratuiloc","#cafehoatan","#ngucoc","#thuonghieurieng","#bansi","#OEM"].sort(()=>Math.random()-.5).slice(0,4).join(" "); }
  S.samples=[{id:1,title:"MỘC TÂM - nhận gia công & sỉ toàn quốc",content:TPL_DEFAULT,enabled:1,made:6,posted:4,comments:9,leads:2},
    {id:2,title:"Tìm đại lý, CTV trà túi lọc",content:"🔥 TÌM ĐẠI LÝ – CTV TRÀ TÚI LỌC TOÀN QUỐC\nXưởng Mộc Tâm cần tìm đại lý, CTV bán trà túi lọc, cafe hòa tan\n• Sản phẩm có sẵn, hàng xưởng\n• Hỗ trợ ảnh, video bán hàng\n• Không cần vốn lớn, nhập ít cũng được\nAi quan tâm ib hoặc kết bạn Zalo {số điện thoại}",enabled:1,made:3,posted:2,comments:4,leads:1}];
  S.cr={min_score:70,ai:true,lessons:["Sếp rút ngắn bài CEO đã duyệt (163 → 110 chữ): duyệt bài dài tối đa khoảng 130 chữ."]};
  function demoCR(){ return {profile:{samples:S.samples.filter(x=>x.enabled).length,min_words:40,max_words:130,emoji_max:12,bad_phrases:[],lessons:S.cr.lessons},min_score:S.cr.min_score,approved:12,rejected:3,boss_fixed:1,accuracy:92,ai:S.cr.ai,
    recent:S.posts.filter(p=>p.review_score!=null).slice(0,6).map(p=>({id:p.id,title:p.title,review_score:p.review_score}))}; }
  function demoCRTry(c){ const t=c||""; const r=[], tips=[]; let sc=0; if(/sỉ|đại lý|gia công|nguồn hàng/i.test(t)) sc+=25; else { r.push("chưa nói rõ tìm khách sỉ / đại lý / gia công"); }
    if(t.replace(/\D/g,"").includes(ZALO())) sc+=20; else { r.push("thiếu số Zalo báo giá"); tips.push(`thêm dòng 💬 Giá vui lòng liên hệ trực tiếp Zalo ${ZALO()}`); }
    if(/^\s*[•\-✅]/m.test(t)) sc+=15; else tips.push("thêm gạch đầu dòng cho dễ đọc"); const w=(t.match(/\S+/g)||[]).length; if(w>=40&&w<=130) sc+=10; else r.push(w<40?`quá ngắn (${w} chữ)`:`quá dài (${w} chữ)`);
    sc+=25; if(/\d+\s*(k|đ)\b/i.test(t)){ r.unshift("còn ghi giá (sếp chốt không công khai giá)"); sc=Math.min(sc,30); } return {score:sc,ok:sc>=S.cr.min_score,reasons:r,tips}; }
  function demoSamples(){ return {items:S.samples,enabled:S.tpl.enabled,ai:true,phone:`📞 Zalo/ĐT: ${ZALO()}`,stats:demoTpl().stats}; }
  function demoTpl(){ const ps=S.posts.filter(p=>p.source==="template"); return {template:S.tpl.template,default:TPL_DEFAULT,enabled:S.tpl.enabled,ai:true,phone:`📞 Zalo/ĐT: ${ZALO()}`,preview:[tplVariant(S.tpl.template),tplVariant(S.tpl.template)],
    stats:{approved:ps.filter(p=>p.status==="approved").length,scheduled:ps.filter(p=>p.status==="scheduled").length,posted_today:ps.filter(p=>p.status==="posted").length}}; }
  function demoMG(){ return {items:S.mg,counts:{},verdicts:{},settings:S.mgSet,last:{detail:"Tuấn rà soát nhóm: nick Linh Nguyễn đang ở 4 nhóm (1 nhóm quản lý); đánh giá 4 nhóm: nên đăng 1, đăng ít 0, không đạt 1; đã thoát Quảng Cáo Facebook 2019 (nhóm gần như không còn hoạt động).",created_at:"2026-11-04 09:21:00"},
    nicks:[{id:1,name:"Linh Nguyễn",sale:"Linh",synced_at:"2026-11-04 09:21:00",groups:3,admin:1,post:1,leave:0},{id:2,name:"Phương Sỉ Tận Gốc",sale:"Phương",synced_at:"2026-11-04 09:24:00",groups:2,admin:0,post:1,leave:1}]}; }
  const PR_TYPES={buyer:"Người đang tìm nguồn hàng",ads:"Đang chạy quảng cáo",owner:"Chủ shop tự nhập hàng",live:"Người bán hàng livestream",multi:"Người bán hàng đa nền tảng",marketplace:"Nhà bán hàng trên sàn TMĐT",ctv:"Cộng tác viên",affiliate:"Affiliate",koc:"KOC/KOL",store:"Cửa hàng truyền thống",unknown:"Chưa rõ"};
  S.prCrit={must:["ship","inbox"],exclude:["quần áo","mỹ phẩm"],bonus:["livestream","zalo"],bonus_points:5,fit:[],regions:["Hà Nội"],followers_min:0,followers_max:0,recent_days:30,skip_types:["affiliate"],crm_min_grade:"C",search_kinds:["pages","posts","posts_recent"],note:""};
  S.prLessons=[{id:1,text:"Gõ “cần nhập trà túi lọc” và “tìm nguồn ngũ cốc” rồi chọn Bài viết gần đây. Ưu tiên shop có livestream. Loại các shop bán “quần áo”, “mỹ phẩm”.",applied:1,created_at:"2026-11-04 20:10:00",
    suggest:{keywords:["cần nhập trà túi lọc","tìm nguồn ngũ cốc"],exclude:["quần áo","mỹ phẩm"],bonus:["livestream"],search_kinds:["posts_recent"],summary:"Em đã ghi bài này vào sổ kiến thức và sẽ làm theo khi đi tìm khách."}}];
  const SKIND={pages:"Trang",posts:"Bài viết",posts_recent:"Bài viết gần đây",people:"Mọi người"};
  const critText=()=>{ const c=S.prCrit, p=[]; if(c.must.length) p.push("Phải có ít nhất 1 trong: "+c.must.join(", ")); if(c.exclude.length) p.push("Loại ngay nếu có: "+c.exclude.join(", "));
    if(c.bonus.length) p.push(`Ưu tiên (+${c.bonus_points} điểm mỗi chữ): `+c.bonus.join(", ")); if(c.regions.length) p.push("Khu vực ưu tiên: "+c.regions.join(", ")); if(c.recent_days) p.push(`Bài mới nhất trong ${c.recent_days} ngày`);
    if(c.skip_types.length) p.push("Bỏ qua: "+c.skip_types.map(k=>PR_TYPES[k]||k).join(", ")); p.push(`Hạng từ ${c.crm_min_grade} trở lên và có SĐT thì vào mục Khách hàng`); p.push("Cách tìm trên Facebook: "+c.search_kinds.map(k=>SKIND[k]).join(", ")); return p.join(". ")+"."; };
  function demoUnderstand(text){ const q=[...text.matchAll(/[“"']([^”"']{2,60})[”"']/g)].map(m=>m[1].trim()); const out={keywords:[],must:[],exclude:[],bonus:[],search_kinds:[]};
    text.split(/[\n.;]+/).forEach(line=>{ const l=line.toLowerCase(), qs=[...line.matchAll(/[“"']([^”"']{2,60})[”"']/g)].map(m=>m[1].trim());
      const after=rx=>{ const m=line.split(rx); return m.length>1?m[1].split(/,| và | hoặc /).map(x=>x.trim().replace(/^(các|những|người|shop|có|đang|bán)\s+/i,"").replace(/^(các|những|người|shop|có|đang|bán)\s+/i,"")).filter(x=>x.length>1&&x.length<=40):[]; };
      if(/loại|bỏ qua|không lấy|tránh/.test(l)) out.exclude.push(...(qs.length?qs:after(/loại|bỏ qua|không lấy|tránh/i)));
      else if(/phải có|bắt buộc|chỉ lấy/.test(l)) out.must.push(...(qs.length?qs:after(/phải có|bắt buộc|chỉ lấy/i)));
      else if(/ưu tiên/.test(l)){ (qs.length?qs:after(/ưu tiên/i)).forEach(x=>/^(ở|tại|khu vực)\s+/i.test(x)?(out.regions=out.regions||[]).push(x.replace(/^(ở|tại|khu vực)\s+/i,"")):out.bonus.push(x)); }
      else out.keywords.push(...qs);
      if(/gần đây|mới nhất/.test(l)) out.search_kinds.push("posts_recent"); });
    const n=out.keywords.length+out.must.length+out.exclude.length+out.bonus.length;
    out.summary="Em đã ghi bài này vào sổ kiến thức và sẽ làm theo khi đi tìm khách."+(n?` Em thấy ${n} điều cài được vào phần mềm, sếp xem và bấm Áp dụng nhé.`:""); return out; }
  function demoPR(qs){ const q=new URLSearchParams(qs||""), g=q.get("grade")||"", pf=q.get("platform")||"", ty=q.get("seller_type")||"", st=q.get("status")||"", ph=q.get("phone")||"";
    const isSeller=x=>["A","B","C"].includes(x.grade);
    const rank={A:0,B:1,C:2,D:3};
    const items=S.pr.filter(x=>(st==="rejected"?x.status==="rejected":x.status!=="rejected")&&(!st||st==="rejected"||x.status===st)&&(!g||x.grade===g)&&(!pf||x.platform===pf)&&(!ty||x.seller_type===ty)&&(!ph||(ph==="yes"?!!x.phone:!x.phone)))
      .sort((a,b)=>(b.phone&&isSeller(b)?1:0)-(a.phone&&isSeller(a)?1:0)||(rank[a.grade]??4)-(rank[b.grade]??4)||(b.score||0)-(a.score||0));
    const counts={}; S.pr.filter(x=>x.status!=="rejected").forEach(x=>{ const k=x.grade||x.status; counts[k]=(counts[k]||0)+1; });
    return {items,counts,manual:S.pr.filter(x=>x.status==="needs_manual").length,crm:S.pr.filter(x=>x.lead_id).length,
      phones:S.pr.filter(x=>x.phone&&isSeller(x)&&x.status!=="rejected").length,phones_today:S.pr.filter(x=>x.phone&&isSeller(x)).length,
      no_phone:S.pr.filter(x=>!x.phone&&isSeller(x)&&x.status==="verified"&&!["affiliate","koc","store"].includes(x.seller_type)).length,
      channels:[{key:"comment",label:"Bình luận dưới bài sale đăng",phones:S.leads.filter(l=>l.origin==="comment"&&l.phone).length,total:S.leads.filter(l=>l.origin==="comment").length},
        ...[["demand","Người hỏi nguồn hàng trong nhóm",6],["ads","Trang đang chạy quảng cáo",5],["pages","Tìm trang, shop livestream",0],["link","Sếp dán link",-1]].map(([k,l,dir])=>{ const xs=S.pr.filter(x=>dir===0?x.direction>=1&&x.direction<=4:dir===-1?!x.direction:x.direction===dir); return {key:k,label:l,phones:xs.filter(x=>x.phone&&isSeller(x)).length,total:xs.length}; })],
      criteria:S.prCrit,lessons:S.prLessons,search_kinds:SKIND,criteria_text:critText(),
      platforms_on:["facebook",...["tiktok","shopee"].filter(k=>S.prSet["prospect_"+k]==="1")],
      directions:{5:"Trang đang chạy quảng cáo bán thực phẩm, đồ uống (thư viện quảng cáo Facebook)",6:"Người đang hỏi tìm nguồn hàng trong nhóm (đọc bài và bình luận)",1:"Người livestream bán trà, ngũ cốc, thực phẩm",2:"Người bán sản phẩm tương tự hoặc bổ trợ",3:"Người bán nhiều nhóm hàng tiêu dùng, có thể mở rộng danh mục",4:"Người tuyển đại lý, tìm nguồn hàng, nhận phân phối, bán sỉ"},
      types:PR_TYPES,platforms:{facebook:"Facebook",tiktok:"TikTok",shopee:"Shopee"},keywords:S.prKw,settings:S.prSet,last:S.prLast||{detail:"Mai tìm khách sỉ xong: tìm được 2 SĐT khách đang bán hàng (xem 9 tài khoản: A 1, B 2, C 1, D 1). Đã chuyển sếp: Bếp Nhà Mây 0903000111 (A), Mộc Gia Mart 0903000222 (B).",created_at:"2026-11-04 14:43:00"}}; }
  const DEMO_LEARN={ceo:["Đang học: cách định giá sỉ theo bậc số lượng","Ôn lại: khi nào nên tuyển thêm nhân sự bán hàng"],minh:["Đang học: cách điều hành họp giao ban 15 phút","Ôn lại: cách giao việc có hạn và người chịu trách nhiệm"],
    lan:["Luyện viết bài về Trà gừng mật ong theo phong cách đã học","Đang học: cách viết câu mở đầu giữ chân người đọc"],tuan:["Đang học: dấu hiệu nhóm tương tác thật và nhóm ảo","Xem lại nhóm cần cân nhắc: Chợ Sỉ Thực Phẩm Khô"],
    ha:["Luyện trả lời khách: chiết khấu nhập số lượng lớn","Đang học: xử lý khách chê giá cao"],mai:["Đang học: phân biệt chủ shop tự nhập hàng với affiliate, KOC","Xem lại bằng chứng khách tiềm năng: Bếp Nhà Mây"],khoa:["Xem lại số liệu bài đăng 7 ngày qua","Đang học: cách tính chi phí trên mỗi khách có SĐT"]};
  function demoFolder(p){ if(!p.image_folder) return {exists:false,source:"",count:0,fresh:0,samples:[]}; const n=[24,18,9,15,6,12][(p.id-1)%6]||10, fr=[17,11,2,9,4,7][(p.id-1)%6]||5; return {path:p.image_folder,exists:true,source:"product",count:n,fresh:fr,posts_left:Math.floor(fr/2),samples:[],error:null}; }
  S.co={status:"active",founded_at:"2026-10-12",day:23,trial_days:60,capital:10000000,orders:[{id:1,lead_name:"Nguyễn Thu Hà",amount:2850000,via:"telegram",created_at:"2026-10-29 15:20:00"},{id:2,lead_name:"Shop Mộc An",amount:4200000,via:"app",created_at:"2026-11-02 10:05:00",note:"Ngũ cốc 50 hũ"}]};
  S.ceoSt={mode:"auto",potential_on:true,milestones:[{amount:50000000,hires:1},{amount:100000000,hires:1}],
    decisions:[{id:3,kind:"keep_slot",status:"done",title:"Không tuyển thay Quân",reason:"Nick Quân Đặc Sản Quê đang lỗi đăng nhập. Sếp xử lý nick xong thì tuyển người thay ở trang Công ty.",created_at:"2026-10-11 08:05:00"},
      {id:2,kind:"fire",status:"done",title:"Sa thải Quân",reason:"Kỳ 12/09 → 11/10: 19/52 khách có SĐT (26 ngày làm việc), không đạt KPI tháng.",created_at:"2026-10-11 08:00:00"}],proposed:[]};
  function demoCeo(){
    const c=demoCompany(), rev=c.finance.revenue, st=S.ceoSt; const ms=st.milestones.map(m=>({...m,done:rev>=m.amount}));
    const act=c.sales.filter(r=>r.status!=="fired"); const waiting=act.filter(r=>r.hired_by==="ceo"&&r.login_status!=="ok").length;
    const hc={working:act.length-waiting,waiting_nick:waiting,total:act.length,max:8};
    const signal=[{label:"Cả phòng trung bình ≥ 10 khách có SĐT/ngày (mức vượt KPI)",value:"6.4/ngày",ok:false},{label:"Mỗi nick vượt 120% chỉ tiêu của mình",value:"73% chỉ tiêu",ok:false}];
    const guards=[{label:"Đủ dữ liệu: ít nhất 14 ngày hoạt động",value:"14 ngày",ok:true},{label:"Khách 7 ngày gần nhất không giảm so với 7 ngày trước",value:"48 so với 41 (+17%)",ok:true},
      {label:"Không còn sale mới đang chờ sếp đăng nhập nick",value:`${waiting} đang chờ`,ok:!waiting},{label:"Văn phòng còn chỗ",value:`${hc.total}/8 sale`,ok:hc.total<8},
      {label:"Vốn đủ nuôi agent ít nhất 60 ngày nữa",value:"hơn 1 năm",ok:true},{label:"Lần tuyển vì tiềm năng gần nhất đã cách 14 ngày",value:"chưa tuyển lần nào",ok:true}];
    return {name:"Đức",mode:st.mode,enabled:true,potential_on:st.potential_on,milestones:ms,next_milestone:ms.find(m=>!m.done)||null,revenue:rev,headcount:hc,
      potential:{window_days:14,leads:89,per_day:6.4,per_nick_day:2.9,quota_pct:73,last7:48,prev7:41,growth:17,free_groups:2,signal,guards,ready:false,
        verdict:"Chưa đủ tiềm năng để tăng người. Phòng đang có 6.4 khách/ngày, mục tiêu tối thiểu 5; tập trung để các nick hiện có đạt KPI trước."},
      decisions:[...st.proposed,...st.decisions],proposed:st.proposed};
  }
  function demoHire(reason){ const names=["Hương","Đạt","Trang","Phúc"]; const used=S.sales.map(x=>x.name); const name=names.find(n=>!used.includes(n))||"Ngọc";
    const r={id:id(),name,fb_name:"",login_status:"not_logged_in",auto_post:1,hired_by:"ceo",hire_reason:reason,status:"active"};
    S.sales.push(r); addNick(r.id,"Nick 1"); S.ceoSt.decisions.unshift({id:id(),kind:"hire",status:"done",title:`Tuyển sale mới: ${name}`,reason,created_at:now()}); log("ceo","Tuyển sale mới",`${name}: ${reason}`); return r; }
  function demoGroupUrl(u){ u=(u||"").trim(); if(!u) return {err:"Dán link nhóm Facebook, ví dụ https://www.facebook.com/groups/tennhom"};
    if(!/^https?:\/\//i.test(u)) u="https://"+u.replace(/^\/+/,""); u=u.replace(/^https?:\/\/(m|mbasic|web|touch|mobile)\.facebook\.com/i,"https://www.facebook.com").replace(/^https?:\/\/(facebook\.com|fb\.com|www\.fb\.com)/i,"https://www.facebook.com");
    const g=u.match(/^(https:\/\/www\.facebook\.com\/groups\/[^/?#]+)/i); if(g) return {url:g[1]}; if(/^https:\/\/www\.facebook\.com\/share\/g\/[^/?#]+/i.test(u)) return {url:u};
    return {err:"Link này không phải link nhóm. Mở nhóm trên Facebook (máy tính), copy link trên thanh địa chỉ, có dạng https://www.facebook.com/groups/…"}; }
  S.errors=[
    {id:3,source:"post",title:"Đăng bài #2 vào Hội Livestream bán hàng bị lỗi",message:"Không tìm thấy nút Đăng trong hộp soạn bài. Nút đang thấy: Đóng, Ảnh/video, Gắn thẻ người khác, Cảm xúc/hoạt động, Tiếp",detail:"Nick: Phương Sỉ Tận Gốc · Bài: Combo trà túi lọc cho shop livestream",hint:"Facebook vừa đổi chữ trên nút. Lỗi có ghi tên các nút sale đang thấy: thêm đúng chữ đó vào backend/fb_selectors.json, hoặc bấm Sao chép rồi gửi cho người hỗ trợ.",screen:"posts",count:2,status:"new",created_at:"2026-11-03 09:12:00",last_at:"2026-11-03 15:40:00",screenshot:null},
    {id:2,source:"post",title:"Đăng bài #5 vào Cộng đồng bán hàng online toàn quốc bị lỗi",message:"Nhóm “Cộng đồng bán hàng online toàn quốc” chưa có link. Vào Hội nhóm, bấm “Thêm link” ở dòng nhóm này rồi bấm Đăng lại",hint:"Vào Hội nhóm, bấm “Thêm link” ở dòng nhóm đó, dán link nhóm rồi đăng lại.",screen:"groups",count:1,status:"new",created_at:"2026-11-03 08:30:00",last_at:"2026-11-03 08:30:00"},
    {id:1,source:"telegram",title:"Không gửi được tin nhắn Telegram",message:"Client error '400 Bad Request': chat not found",hint:"Kết nối Telegram bị lỗi. Vào KPI & Báo cáo, kiểm tra token và ghép nối lại bot.",screen:"kpi",count:3,status:"seen",created_at:"2026-11-02 21:30:00",last_at:"2026-11-03 09:00:00"}];
  const ESRC={ui:"Giao diện",api:"Phần mềm",post:"Đăng bài",bump:"Up bài",scan:"Quét bình luận",browser:"Chrome",nick:"Nick Facebook",telegram:"Telegram",ai:"AI Claude",fanpage:"Fanpage",scheduler:"Lịch tự động"};
  const EHINT=[[/chưa có link/i,"Vào Hội nhóm, bấm “Thêm link” ở dòng nhóm đó, dán link nhóm rồi đăng lại.","groups"],[/không phải link nhóm|Dán link nhóm/i,"Mở nhóm trên Facebook bằng máy tính, copy địa chỉ trên thanh trình duyệt (dạng https://www.facebook.com/groups/…) rồi dán lại.","groups"],[/Nhập (số tiền|vốn)|Nhập doanh thu/i,"Nhập số tiền bằng số, ví dụ 2500000, 2,5tr hoặc 800k.",null]];
  function demoErrors(q){ const st=new URLSearchParams(q||"").get("status")||"open", src=new URLSearchParams(q||"").get("source")||"";
    const items=S.errors.filter(e=>(st==="open"?e.status!=="resolved":st==="all"?true:e.status===st)&&(!src||e.source===src)).map(e=>({...e,source_label:ESRC[e.source]})).sort((a,b)=>b.last_at.localeCompare(a.last_at));
    return {items,new:S.errors.filter(e=>e.status==="new").length,open:S.errors.filter(e=>e.status!=="resolved").length,sources:ESRC}; }
  S.gf={today:["hội chạy quảng cáo facebook","nguồn hàng sỉ thực phẩm","mẹ bỉm sữa kinh doanh online"],by:"ceo",
    pool:["hội chạy quảng cáo facebook","cộng đồng bán hàng online","nguồn hàng sỉ thực phẩm","livestream bán hàng","bán hàng shopee tiktok shop","nhập hàng tận xưởng","mẹ bỉm sữa kinh doanh online","kinh doanh online tại nhà","sỉ trà túi lọc","bột ngũ cốc dinh dưỡng"],
    settings:{discover_enabled:"1",discover_time:"10:30",discover_keywords_per_day:"3",discover_add_per_day:"5",join_enabled:"1",join_per_nick_day:"2",browse_minutes:"2",scout_per_run:"6",review_posts_day:"10",review_avg_reactions:"20",review_avg_comments:"5",review_growth_week:"0.5",review_min_members:"1000",review_join_score:"60",review_consider_score:"40",review_use_best_groups:"1"},
    last:{at:"2026-11-03 10:42:00",sale_id:1,found:7,scouted:6,review:{join:2,consider:2,skip:3},added:2,joins:{joined:1,requested:2}},
    candidates:[{id:501,url:"https://www.facebook.com/groups/qcfbthucchien",name:"Cộng đồng chạy quảng cáo Facebook thực chiến",members:1200000,posts_per_day:50,posts_month:1600,new_members_week:5100,privacy:"private",keyword:"hội chạy quảng cáo facebook",relevance:1,score:118,sampled_posts:0,eng_score:58.5,verdict:"consider",review_note:"Mạnh: 53,3 bài/ngày, +5.100 thành viên/tuần (0,4%); Yếu: chưa xem được bài trong nhóm (nhóm riêng tư, sẽ đánh giá lại sau khi vào)"},
      {id:502,url:"https://www.facebook.com/groups/chosithucpham",name:"Chợ Sỉ Thực Phẩm Khô Toàn Quốc",members:56000,posts_per_day:8,posts_month:640,new_members_week:900,privacy:"public",keyword:"nguồn hàng sỉ thực phẩm",relevance:0.67,score:79,sampled_posts:4,avg_reactions:4.8,avg_comments:1.8,last_post_hours:1,selling_ratio:0.5,eng_score:62.9,verdict:"consider",review_note:"Mạnh: 21,3 bài/ngày, +900 thành viên/tuần (1,6%), có bài mới trong giờ qua; Yếu: mỗi bài TB 4,8 cảm xúc, 1,8 bình luận (chuẩn 20 cảm xúc, 5 bình luận), tương tác mỗi bài thấp hơn 60% chuẩn nên chưa tự vào"}],
    rejected:[{id:503,url:"https://www.facebook.com/groups/chaynho",name:"Chạy quảng cáo nhỏ lẻ",members:640,posts_per_day:0.3,privacy:"public",keyword:"hội chạy quảng cáo facebook",relevance:0.75,score:62,eng_score:37.7,verdict:"skip",status:"rejected",review_note:"Loại: chỉ 640 thành viên (cần từ 1.000)"},
      {id:504,url:"https://www.facebook.com/groups/adsquestions",name:"Hội Quảng Cáo FB Ads Chuyên Sâu",members:86000,posts_month:380,new_members_week:300,privacy:"private",keyword:"hội chạy quảng cáo facebook",relevance:1,eng_score:61.8,verdict:"skip",status:"rejected",review_note:"Loại: luật nhóm cấm bán hàng/quảng cáo (“Nghiêm cấm quảng cáo bán hàng dưới mọi hình thức.”)"},
      {id:505,url:"https://www.facebook.com/groups/choraovat",name:"Chợ Quảng Cáo Facebook Rao Vặt Sỉ Lẻ",members:120000,posts_month:1900,new_members_week:200,privacy:"public",keyword:"hội chạy quảng cáo facebook",relevance:1,sampled_posts:4,avg_reactions:1,avg_comments:0.2,last_post_hours:0.2,selling_ratio:1,eng_score:27.8,verdict:"skip",status:"rejected",review_note:"Mạnh: 63,3 bài/ngày, có bài mới trong giờ qua; Yếu: mỗi bài TB 1 cảm xúc, 0,2 bình luận (chuẩn 20 cảm xúc, 5 bình luận), 100% bài là rao bán mà gần như không ai bình luận (chợ spam)"}],
    pending:[{id:7,name:"Hội Quảng Cáo FB Ads Chuyên Sâu",url:"https://www.facebook.com/groups/adsquestions",sale:"Linh"}]};
  S.groups.push({id:6,name:"Hội Chạy Quảng Cáo Facebook - Ads Việt Nam",url:"https://www.facebook.com/groups/chayqcfb",topic:"hội chạy quảng cáo facebook",members:245000,eng_score:100,verdict:"join",review_note:"Mạnh: 38,3 bài/ngày, mỗi bài TB 42,8 cảm xúc, 15 bình luận, +2.400 thành viên/tuần (1,0%), có bài mới trong ngày",rules:"",min_days_between_posts:3,last_posted_at:null,leads_count:0,source:"search",keyword:"hội chạy quảng cáo facebook",member_account_ids:"11,12",joins:{11:{status:"joined"},12:{status:"joined"},21:{status:"requested"}}},
    {id:7,name:"Mẹ Bỉm Sữa Kinh Doanh Online",url:"https://www.facebook.com/groups/meobim",topic:"mẹ bỉm sữa kinh doanh online",members:310000,rules:"",min_days_between_posts:3,last_posted_at:null,leads_count:0,source:"search",keyword:"mẹ bỉm sữa kinh doanh online",member_account_ids:"",joins:{13:{status:"requested"},21:{status:"needs_answers",note:"Nhóm yêu cầu trả lời câu hỏi khi xin vào"}}});
  const gfToday=g=>S.gf.today.includes(g.keyword)||S.gf.today.some(k=>k.split(" ").filter(w=>w.length>3).some(w=>(g.name+" "+(g.topic||"")).toLowerCase().includes(w)));
  function demoGF(){ const st=S.gf; const se=st.settings; return {today:st.today,today_by:st.by,pool:st.pool,settings:se,last:st.last,candidates:st.candidates.filter(c=>!c.status),rejected:st.rejected||[],
    benchmark_text:`${String(se.review_posts_day).replace(".",",")} bài/ngày, mỗi bài ${se.review_avg_reactions} cảm xúc và ${String(se.review_avg_comments).replace(".",",")} bình luận, +${String(se.review_growth_week).replace(".",",")}% thành viên/tuần`,pending_answers:st.pending,
    stats:st.pool.map((k,i)=>({keyword:k,groups:S.groups.filter(g=>g.keyword===k).length,leads:[4,2,3,1,0,0,0,0,0,0][i]||0,found:0,last_searched:i<3?"2026-11-03 10:40:00":null}))}; }
  S.chat=[]; S.orders=[];
  setInterval(()=>{ if(S.settings.ceo_autopilot==="0") return; const d=S.posts.filter(p=>p.status==="draft"); if(d.length){ d.forEach(p=>p.status="approved"); log("ceo","Duyệt bài",`Duyệt ${d.length} bài`); } },15000);
  function demoChat(){ return {autopilot:S.settings.ceo_autopilot!=="0",running:Object.entries(S.status).filter(([k,v])=>k.startsWith("sale-")&&v.state==="working").map(([k,v])=>`${(S.sales.find(x=>"sale-"+x.id===k)||{}).name}: ${v.text}`),history:S.chat,orders:S.orders.filter(o=>o.active),suggestions:["Tình hình hôm nay thế nào?","Đăng bài lên các nhóm có từ khóa nguồn hàng, bán hàng online","Viết 3 bài về trà gừng mật ong","Xếp lịch đăng nhóm","Tìm nhóm theo chủ đề “hội chạy quảng cáo facebook”","Lan viết bài dài quá, viết dưới 150 chữ","Từ nay bài nào cũng nhắc giao hàng toàn quốc"]}; }
