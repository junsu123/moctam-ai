  // Các Trang của Nhi: từ khóa sếp đặt, hàng chờ duyệt, Nhi ghi nhớ theo sếp
  function demoNp(method,P,qs,body){ if(!S.tr) demoTr("GET","/trends",{},{}); const td=today(), pn=id=>(S.tr.pages.find(p=>p.id===id)||{}).name||"";
    if(!S.np){ S.np={review:true,seq:50,hist:{ok:14,edit:4,reject:2},
        mem:[{id:1,page_id:1,kind:"lesson",text:"Sếp thích bài ngắn hơn: khoảng 60 chữ"},{id:2,page_id:1,kind:"reject",text:"Giọng văn chưa hợp (từ khóa “món chay”)"},{id:3,page_id:1,kind:"note",text:"Luôn gợi ý món hợp mùa"}],
        queue:[{id:950,page_id:1,page_kw:"món chay",trend_kind:"evergreen",trend_topic:"món chay",scheduled_for:`${td} 19:30`,content:"🥗 Thứ Hai ăn chay nhẹ bụng: đậu hũ sốt nấm 15 phút\n\nĐậu hũ chiên vàng, rưới sốt nấm đông cô, thêm chút tiêu. Cơm nóng ăn kèm là hết sạch nồi.\n\nNhà bạn hay nấu món chay nào nhất? 👇\n#monchay #bepnhaminh"},
          {id:951,page_id:1,page_kw:null,trend_kind:"trend",trend_topic:"món ngon cuối tuần",scheduled_for:`${td} 21:00`,content:"🍲 Cuối tuần này nấu gì? 3 món cả nhà mê mà không tốn công\n\n1. Canh chua cá lóc\n2. Thịt kho trứng\n3. Rau muống xào tỏi\n\nBạn chọn món nào? Bình luận để mình gửi cách làm nhé!"}]};
      S.tr.pages.forEach(p=>{ if(p.id===1&&p.keywords==null) Object.assign(p,{keywords:"món chay, canh chua, mẹo nấu cơm, món ngon cuối tuần",avoid:"rượu bia",boss_note:"Giọng thân mật, xưng mình"}); }); }
    const N=S.np, smart=h=>{ const n=h.ok+h.edit+h.reject; return {n,ok:h.ok,edit:h.edit,reject:h.reject,pct:n?Math.round(100*h.ok/n):0,need:20,suggest_off:n>=20&&h.ok/n>=0.85}; }; let m;
    if(P==="/nhi-pages"&&method==="GET") return {review:N.review,noimg:N.noimg!==false,auto_kw:N.auto_kw!==false,smart:smart(N.hist),reasons:["Sai chủ đề của Trang","Không đúng từ khóa","Giọng văn chưa hợp","Quá dài","Quá ngắn","Thông tin chưa đúng / bịa","Trùng bài cũ","Khác"],
      queue:N.queue.map(q=>({...q,page_name:pn(q.page_id)})),
      pages:S.tr.pages.filter(p=>["active","paused","creating"].includes(p.status)).map(p=>({...p,admin_name:p.admin_name||"Linh 1",posts_per_day:p.posts_per_day||2,times:p.times||"09:00,19:30",
        kw:(p.keywords||"").split(",").map(x=>x.trim()).filter(Boolean).map((k,i)=>({kw:k,n:[5,3,2,1][i]||0,ok:[4,2,1,0][i]||0,bad:i===1?1:0,eng:[42,30,18,9][i]||0,last:""})),
        memory:N.mem.filter(x=>x.page_id===p.id).slice().reverse(),smart:smart(N.hist),today:N.queue.filter(q=>q.page_id===p.id).map(q=>({...q,status:"page_review"}))}))};
    if(P==="/nhi-pages/settings"){ if("review" in body) N.review=!!body.review; ["noimg","auto_kw"].forEach(k=>{ if(k in body) N[k]=!!body[k]; }); return {ok:true}; }
    if(P==="/nhi-pages/approve-all"){ const n=N.queue.length; N.hist.ok+=n; N.queue=[]; return {approved:n}; }
    if((m=P.match(/^\/nhi-pages\/posts\/(\d+)\/review$/))){ const q=N.queue.find(x=>x.id==m[1]); if(!q) throw new Error("Bài này không còn chờ duyệt"); N.queue=N.queue.filter(x=>x!==q);
      if(body.action==="reject"){ N.hist.reject++; N.mem.push({id:++N.seq,page_id:q.page_id,kind:"reject",text:body.reason}); return {status:"rejected"}; }
      const ed=(body.content||q.content).trim()!==q.content.trim(); if(ed){ N.hist.edit++; N.mem.push({id:++N.seq,page_id:q.page_id,kind:"lesson",text:`Sếp thích bài khoảng ${body.content.trim().split(/\s+/).length} chữ`}); } else N.hist.ok++;
      S.tr.posts.unshift({id:q.id,status:"need_image",page_name:pn(q.page_id),trend_topic:q.trend_topic,scheduled_for:q.scheduled_for,content:body.content||q.content,image_prompt:"Warm home kitchen scene, 4:5 portrait, no text"}); return {review_result:ed?"edit":"ok"}; }
    if((m=P.match(/^\/nhi-pages\/memory\/(\d+)$/))){ N.mem=N.mem.filter(x=>x.id!=m[1]); return {ok:true}; }
    if((m=P.match(/^\/nhi-pages\/(\d+)\/suggest$/))) return {keywords:["bữa sáng nhanh","thực đơn tuần","món ăn dặm cho bé"]};
    if((m=P.match(/^\/nhi-pages\/(\d+)$/))&&method==="PUT"){ const p=S.tr.pages.find(x=>x.id==m[1]); if(body.teach){ N.mem.push({id:++N.seq,page_id:p.id,kind:"note",text:body.teach}); return p; }
      Object.assign(p,{niche:body.niche,keywords:body.keywords,avoid:body.avoid,boss_note:body.boss_note,posts_per_day:+body.posts_per_day||p.posts_per_day,times:body.times||p.times}); return p; }
    throw new Error("Bản xem trước chưa hỗ trợ thao tác này"); }
  function demoTr(method,P,qs,body){ let m; const td=today(), hm=(d,t)=>`${d} ${t}`;
    if(!S.tr){ const a=workingNicks()[0]||{}; S.tr={id:900,
      pages:[{id:1,name:"Bếp Nhà Mình Mỗi Ngày",niche:"mẹo nấu ăn",category:"Ẩm thực",status:"active",auto_created_at:"x",avatar_path:"x",avatar_done:1,avatar_prompt:"Minimal flat logo icon: cooking pot with steam, warm orange, no text, square",cover_prompt:"Wide banner of a cozy Vietnamese home kitchen, no text, 1640x624",url:"https://facebook.com/bepnhaminh",admin_account_id:a.id,admin_name:a.name,posts_per_day:2,times:"09:00,19:30",followers:3420,posted_30d:41,avg_eng:58.3},
        {id:2,name:"Góc Thú Cưng",niche:"nuôi chó mèo",category:"Thú cưng",status:"idea",description:"Mẹo chăm chó mèo, ảnh dễ thương, hỏi đáp cho người mới nuôi.",reason:"“mẹo nuôi mèo”, “thức ăn cho chó” lên xu hướng 5/7 ngày gần đây, cộng đồng hỏi đáp lâu dài",trends:"mẹo nuôi mèo, thức ăn cho chó",
          avatar_prompt:"Cute minimal flat illustration of a cat and a dog sitting together, warm pastel background, centered, no text, square",cover_prompt:"Wide cozy living room illustration with a cat and a dog playing, soft morning light, no text, 1640x624"}],
      posts:[{id:901,status:"need_image",page_name:"Bếp Nhà Mình Mỗi Ngày",trend_topic:"món ngon cuối tuần",scheduled_for:hm(td,"19:30"),content:"🍲 Cuối tuần nấu gì cho cả nhà? 3 món dễ làm trong 30 phút mà ai cũng mê...\nBạn hay nấu món gì cuối tuần? 👇",image_prompt:"Overhead photo-style illustration of three Vietnamese home-cooked dishes on a wooden table, warm natural light, 4:5 portrait, no text, no people",image_note:"Ảnh 3 món ăn gia đình, ánh sáng ấm, không chữ"},
        {id:902,status:"scheduled",page_name:"Bếp Nhà Mình Mỗi Ngày",trend_topic:"canh chua",scheduled_for:hm(td,"09:00"),content:"🥣 Bí quyết nồi canh chua trong veo, thơm lừng"},
        {id:903,status:"posted",page_name:"Bếp Nhà Mình Mỗi Ngày",posted_at:hm(td,"07:30"),content:"🍳 Mẹo chiên trứng không dính chảo",reactions:84,comments:17,shares:9,posted_url:"https://facebook.com/bepnhaminh/posts/1"}],
      hot:[["món ngon cuối tuần",86,"mẹo nấu ăn","Lượt tìm tăng mạnh 3 ngày liên tiếp"],["mẹo nuôi mèo",78,"nuôi chó mèo","Lặp lại 5/7 ngày"],["thời tiết hà nội",55,"thời tiết","Tin ngắn hạn, khó làm Trang"]].map((h,i)=>({id:i,title:h[0],score:h[1],niche:h[2],why:h[3]})),
      trends:[["món ngon cuối tuần","200K+","10 món ngon cuối tuần dễ làm"],["thời tiết hà nội","100K+","Hà Nội trở lạnh"],["mẹo nuôi mèo","50K+","Cách chọn hạt cho mèo"],["giá vàng","500K+","Giá vàng hôm nay"]].map(t=>({title:t[0],traffic:t[1],news:[{title:t[2]}]}))}; }
    S.ti=S.ti||{has_token:false,token_masked:"",bot:null,chats:0,pair_code:"",error:null,report:true};
    if(P.startsWith("/tg-img")){ const t=S.ti;
      if(P==="/tg-img/token"&&method==="POST"){ if(!/^\d{5,12}:[A-Za-z0-9_-]{30,}$/.test(body.token||"")) throw new Error("Token không đúng dạng. Token do @BotFather gửi có dạng 123456789:AAH…, copy đủ cả dãy"); Object.assign(t,{has_token:true,token_masked:body.token.split(":")[0]+":…"+body.token.slice(-4),bot:"nhi_anh_mt_bot",pair_code:String(Math.floor(1e5+Math.random()*9e5))}); setTimeout(()=>{ t.chats=1; },6000); return t; }
      if(P==="/tg-img/token"&&method==="DELETE"){ Object.assign(t,{has_token:false,token_masked:"",bot:null,chats:0,pair_code:""}); return t; }
      if(P==="/tg-img/pair"){ t.pair_code=String(Math.floor(1e5+Math.random()*9e5)); return t; }
      if(P==="/tg-img/settings"){ t.report=!!+body.report; return t; }
      if(P==="/tg-img/test") return {ok:true};
      return t; }
    const view=()=>({learn:{n:34,need:16,min_n:8,kind:[{key:"evergreen",label:"bền (không gắn tin nóng)",n:14,avg:1.32},{key:"trend",label:"bám tin nóng",n:20,avg:0.78}],
        length:[{key:"mid",label:"vừa (80–120 chữ)",n:15,avg:1.21},{key:"short",label:"ngắn (dưới 80 chữ)",n:12,avg:0.94},{key:"long",label:"dài (trên 120 chữ)",n:7,avg:0.71}],
        slot:[{key:"evening",label:"tối (18–24h)",n:17,avg:1.18},{key:"morning",label:"sáng (5–11h)",n:17,avg:0.82}],best_slot:["tối (18–24h)"],
        good:[{topic:"món ngon cuối tuần",x:1.9,n:3},{topic:"canh chua",x:1.4,n:2}],bad:[{topic:"giá vàng",x:0.4,n:2}],calib:{n:18,hit:8,pct:44,flash:["giá vàng","thời tiết hà nội"]},
        lessons:[{text:"Bài bền (không gắn tin nóng) được hưởng ứng gấp 1.7 lần bài bám tin nóng: ưu tiên bài bền (không gắn tin nóng).",evidence:"14 và 20 bài Trang 30 ngày, z=2.4"},{text:"Bài Trang đăng tối (18–24h) được tương tác gấp 1.4 lần sáng (5–11h): gợi ý sếp dời giờ đăng vào khung này.",evidence:"17 và 17 bài Trang 30 ngày, z=2.1"}]},
      img_bot:S.ti,pages:S.tr.pages.filter(p=>p.status!=="dismissed"),posts:S.tr.posts.filter(p=>p.status!=="rejected"),hot:S.tr.hot,trends:S.tr.trends,telegram:true,research_day:td,
      nicks:workingNicks().map(a=>({id:a.id,name:a.name,sale_name:(S.sales.find(x=>x.id===a.sale_id)||{}).name})),settings:{trend_on:"1",trend_time:"07:40",trend_autocreate:"1",trend_create_per_week:"1",trend_create_nick:""},created_7d:S.tr.pages.filter(p=>p.auto_created_at).length});
    if(method==="GET") return view();
    if(P==="/trends/research") return {ok:true,trends:4,hot:3,ideas:0};
    if(P==="/trends/plan"){ const pg=S.tr.pages.find(p=>p.status==="active"); if(!pg) return {written:0}; S.tr.posts.unshift({id:++S.tr.id,status:"need_image",page_name:pg.name,trend_topic:"mẹo bếp",scheduled_for:hm(td,"21:00"),content:"🔪 5 mẹo giữ dao bếp luôn sắc. Bạn mài dao bao lâu một lần?",image_prompt:"Kitchen knives on a wooden board with a sharpening stone, warm light, 4:5, no text"}); log("nhi","Lên lịch bài Trang xu hướng","Viết 1 bài, đã gửi prompt ảnh lên Telegram"); return {written:1}; }
    if(P==="/trends/pages"){ if(!(body.name||"").trim()) throw new Error("Điền tên Trang"); S.tr.pages.push({id:S.tr.pages.length+10,name:body.name,niche:body.niche||body.name,status:"idea",reason:"Sếp thêm"}); return {}; }
    if(P==="/trends/ideas"){ const nm=(body.name||"").trim(); if(nm.length<3) throw new Error("Điền tên Trang (ít nhất 3 ký tự)");
      const taken=S.tr.pages.some(p=>p.name.toLowerCase()===nm.toLowerCase()), name=taken?`${nm} Mỗi Ngày`:nm, a=workingNicks()[0]||{}, niche=body.niche||nm;
      const pg={id:S.tr.pages.length+20,name,requested_name:nm,name_note:taken?"Trùng tên Trang đã có trong phần mềm":null,niche,category:"Blog cá nhân",status:a.id?"creating":"idea",admin_account_id:a.id,admin_name:a.name,
        description:`Chia sẻ ${niche}: mẹo hay, thông tin hữu ích.`,avatar_prompt:`Minimal flat vector logo icon about ${niche}, no text, square 1:1`,cover_prompt:`Wide banner illustration about ${niche}, no text, 1640x624`,reason:"Sếp giao"};
      S.tr.pages.unshift(pg); log("nhi","Nhận ý tưởng Trang của sếp",name); return {page:pg,renamed:taken,queued:!!a.id,nick:a.name,why:a.id?"":"Không có nick đủ an toàn"}; }
    if((m=P.match(/^\/trends\/pages\/(\d+)\/(picture|ask-pictures)$/))){ const p=S.tr.pages.find(x=>x.id==m[1]); if(m[2]==="picture"){ p[body.kind+"_path"]="x"; return {msg:`Đã nhận ${body.kind==="avatar"?"logo":"banner"} cho Trang ${p.name}`}; } return {ok:true}; }
    if((m=P.match(/^\/trends\/pages\/(\d+)\/autocreate$/))){ const p=S.tr.pages.find(x=>x.id==m[1]), a=workingNicks()[0]; if(!a) throw new Error("Không có nick đủ an toàn: chưa có nick đăng nhập, đang làm việc");
      Object.assign(p,{status:"creating",admin_account_id:a.id,admin_name:a.name}); log("nhi","Chuẩn bị tạo Trang",`Trang ${p.name} sẽ được tạo bằng nick ${a.name} ở ca làm việc tới`); return {ok:true,page_id:p.id,nick:a.name}; }
    if((m=P.match(/^\/trends\/pages\/(\d+)\/(activate|status)$/))){ const p=S.tr.pages.find(x=>x.id==m[1]);
      if(m[2]==="activate"){ if(!/facebook\.com/.test(body.url||"")) throw new Error("Dán link Trang trên facebook.com (VD https://facebook.com/tentrang)"); if(!body.admin_account_id) throw new Error("Chọn nick quản trị Trang");
        const a=S.accounts.find(x=>x.id==body.admin_account_id)||{}; Object.assign(p,{status:"active",url:body.url,admin_account_id:a.id,admin_name:a.name,posts_per_day:+body.posts_per_day||2,times:body.times,posted_30d:0,avg_eng:0}); return p; }
      p.status=body.status; return {ok:true}; }
    if((m=P.match(/^\/trends\/posts\/(\d+)\/(image|ask|skip)$/))){ const p=S.tr.posts.find(x=>x.id==m[1]); if(m[2]==="skip") p.status="rejected"; if(m[2]==="image") p.status="scheduled"; return {ok:true,...p}; }
    throw new Error("Không hỗ trợ"); }
  function demoPg(method,P,qs,body){ let m; const td=today(), hm=(d,t)=>`${d} ${t}`; const add=(dd)=>{ const x=new Date(Date.now()+dd*864e5), p=n=>String(n).padStart(2,"0"); return `${x.getFullYear()}-${p(x.getMonth()+1)}-${p(x.getDate())}`; };
    const L={knowledge:"Kiến thức nguyên liệu",recipe:"Cách pha, công thức",factory:"Hậu trường xưởng",seller:"Mẹo bán hàng online",faq:"Hỏi đáp khách sỉ",poll:"Hỏi ý kiến",product:"Giới thiệu sản phẩm"};
    if(!S.pg){ const a=workingNicks()[0]||{}; S.pg={id:800,settings:{page_grow_on:"1",page_url:"https://facebook.com/moctamvn",page_admin_account:String(a.id||""),page_grow_per_day:"2",page_grow_times:"08:30,20:30",page_grow_sale_pct:"20",page_grow_review:"0",page_grow_off:""},
      upcoming:[{id:701,page_topic:"recipe",status:"scheduled",scheduled_for:hm(td,"20:30"),content:"☕ Pha trà gừng mật ong ấm bụng ngày mưa trong 3 bước:\n1. Tráng cốc bằng nước nóng\n2. Thả 1 túi trà gừng, rót 180ml nước sôi để nguội bớt\n3. Đợi 4 phút, thêm 1 thìa mật ong\nBạn thích uống nóng hay thêm đá? 👇"},
        {id:702,page_topic:"factory",status:"scheduled",scheduled_for:hm(add(1),"08:30"),content:"🏭 6 giờ sáng ở xưởng: gừng tươi được rửa, thái lát và sấy lạnh trước khi nghiền, đóng túi lọc. Mỗi mẻ đều kiểm tra độ ẩm và mùi trước khi đóng thùng."}],
      posted:[["product",46,9,4,2,"✨ Trà sen túi lọc đang được nhiều shop online nhập về bán"],["seller",61,14,9,1,"📸 Mẹo chụp ảnh sản phẩm trà bằng điện thoại cho shop online"],["knowledge",38,6,3,0,"🌿 Vì sao gừng sấy lạnh giữ mùi thơm lâu hơn?"],["poll",29,21,1,0,"💬 Shop bạn bán vị nào chạy nhất?"],["recipe",52,8,7,0,"☕ 3 bước pha ngũ cốc sữa hạt buổi sáng"],["faq",24,5,2,1,"❓ Nhập ít có được không? Xưởng trả lời"]].map((r,i)=>({id:690-i,page_topic:r[0],reactions:r[1],comments:r[2],shares:r[3],leads:r[4],content:r[5],posted_at:hm(add(-i-1),i%2?"20:30":"08:30"),posted_url:"https://facebook.com/moctamvn/posts/"+(9000+i)}))}; }
    if(!S.pg.pages){ const a=workingNicks()[0]||{}; S.pg.pages=[{id:1,name:"Mộc Tâm - Trà & Ngũ Cốc",kind:"grow",status:"active",url:"https://facebook.com/moctamvn",admin_account_id:a.id,posts_per_day:2,times:"08:30,20:30",niche:"trà, ngũ cốc, nhận sỉ và gia công",keywords:"trà gừng, trà sen, ngũ cốc dinh dưỡng",followers:1284,followers_7d:37,stats_at:hm(td,"09:12")},
        {id:2,name:"Góc Pha Trà Ngon",kind:"grow",status:"active",url:"https://facebook.com/gocphatra",admin_account_id:(workingNicks()[1]||a).id,posts_per_day:1,times:"20:00",niche:"pha chế trà tại nhà",keywords:"công thức trà, trà detox",followers:412,followers_7d:21,stats_at:hm(td,"10:05")}];
      S.pg.upcoming.forEach((u,i)=>{ u.page_id=1+(i%2); }); S.pg.posted.forEach((u,i)=>{ u.page_id=1+(i%3===2?1:0); }); }
    const pn=id=>(S.pg.pages.find(x=>x.id===id)||{}).name||"";
    const view=()=>{ const ps=S.pg.posted.map(p=>({...p,page_name:pn(p.page_id),eng:p.reactions+2*p.comments+3*p.shares})); const off=(S.pg.settings.page_grow_off||"").split(",");
      const topics=Object.keys(L).map(k=>{ const xs=ps.filter(p=>p.page_topic===k); return {topic:k,label:L[k],n:xs.length,eng:xs.length?Math.round(xs.reduce((n,p)=>n+p.eng,0)/xs.length*10)/10:0,leads:xs.reduce((n,p)=>n+(p.leads||0),0),on:!off.includes(k)}; });
      const pages=S.pg.pages.filter(p=>p.status!=="dismissed").map(p=>{ const adm=S.accounts.find(a=>a.id==p.admin_account_id); return {...p,admin_name:adm&&adm.name,ready:p.status!=="active"?null:!p.url?`Trang ${p.name} chưa có link`:!adm?`Trang ${p.name} chưa chọn nick quản trị`:null}; });
      const act=pages.filter(p=>p.status==="active");
      return {ready:!act.length?"Chưa có Trang nào: bấm Thêm Trang, dán link và chọn nick quản trị":act.every(p=>p.ready)?act[0].ready:null,pages,followers:act.reduce((n,p)=>n+(p.followers||0),0),followers_7d:act.reduce((n,p)=>n+(p.followers_7d||0),0),
        nicks:workingNicks().map(a=>({id:a.id,name:a.name,sale_name:(S.sales.find(x=>x.id===a.sale_id)||{}).name})),upcoming:S.pg.upcoming.map(u=>({...u,page_name:pn(u.page_id)})),posted:ps,top:[...ps].sort((a,b)=>b.eng-a.eng).slice(0,5),topics,
        avg_eng:Math.round(ps.reduce((n,p)=>n+p.eng,0)/ps.length*10)/10,stats_at:hm(td,"09:12"),review:!S.np||S.np.review,settings:{...S.pg.settings}}; };
    const chkPage=(b,cur)=>{ if(b.url!=null&&!/facebook\.com/.test(b.url)) throw new Error("Dán link Trang trên facebook.com (VD https://facebook.com/tentrang)"); if(!cur&&!b.admin_account_id) throw new Error("Chọn nick quản trị Trang (nick sale là quản trị viên / biên tập viên của Trang)"); };
    if(method==="GET") return view();
    if(P==="/page-grow/settings"){ Object.assign(S.pg.settings,body); return view(); }
    if(P==="/page-grow/pages"&&method==="POST"){ if(!(body.name||"").trim()) throw new Error("Điền tên Trang"); if(S.pg.pages.some(x=>x.name.toLowerCase()===body.name.trim().toLowerCase()&&x.status!=="dismissed")) throw new Error("Đã có Trang tên này trong danh sách"); chkPage(body);
      S.pg.pages.push({id:Math.max(0,...S.pg.pages.map(x=>x.id))+1,kind:"grow",status:"active",name:body.name.trim(),url:body.url,admin_account_id:+body.admin_account_id,posts_per_day:+body.posts_per_day||1,times:body.times||"08:30,20:30",niche:body.niche||"",keywords:body.keywords||"",followers:null,followers_7d:null});
      log("nhi","Nhận nuôi Trang",`Trang ${body.name}: Nhi viết bài 80/20, nick quản trị đăng theo giờ`); return view(); }
    if((m=P.match(/^\/page-grow\/pages\/(\d+)$/))){ const pg=S.pg.pages.find(x=>x.id==m[1]); chkPage(body,pg); Object.assign(pg,body,{admin_account_id:+(body.admin_account_id||pg.admin_account_id),posts_per_day:+(body.posts_per_day||pg.posts_per_day)}); return view(); }
    if((m=P.match(/^\/page-grow\/pages\/(\d+)\/status$/))){ const pg=S.pg.pages.find(x=>x.id==m[1]); pg.status=body.status; if(body.status!=="active") S.pg.upcoming=S.pg.upcoming.filter(u=>u.page_id!==pg.id); return view(); }
    if(P==="/page-grow/write"){ const v=view(), pg=v.pages.find(x=>x.id==body.page_id)||v.pages.find(x=>x.status==="active"&&!x.ready); if(!pg) throw new Error(v.ready||"Chưa có Trang nào"); if(pg.ready) throw new Error(pg.ready);
      const ks=Object.keys(L).filter(k=>!(S.pg.settings.page_grow_off||"").split(",").includes(k)&&k!=="product"); const k=ks[Math.floor(Math.random()*ks.length)]||"product"; const rv=v.review;
      const p={id:++S.pg.id,page_id:pg.id,page_topic:k,status:rv?"page_review":"scheduled",scheduled_for:hm(add(1),(pg.times||"20:30").split(",")[0]),content:{knowledge:"🌿 Lá sen phơi khô đúng cách giữ mùi thơm nhẹ, pha lên nước trong. Cách chọn lá sen ngon: lá già, xanh đều, không mốc.",recipe:"☕ Công thức trà sen nhãn mát lạnh cho buổi chiều: 1 túi trà sen, 5 quả nhãn nhục, đá viên. Bạn đã thử chưa?",factory:"🏭 Hậu trường đóng gói: mỗi túi lọc được cân đúng 2g, hàn kín miệng trước khi vào hộp.",seller:"📦 Mẹo cho shop mới: chọn 2–3 vị dễ bán trước, chụp ảnh cạnh ly đã pha, đăng giờ 20h–22h.",faq:"❓ Khách sỉ hỏi: xưởng có in nhãn riêng không? Có, nhận in nhãn theo thương hiệu của shop từ số lượng nhỏ.",poll:"💬 Sáng nay bạn uống gì: trà gừng, trà sen hay ngũ cốc? Bình luận vị bạn chọn nhé!"}[k]};
      S.pg.upcoming.push(p); log("nhi","Viết bài nuôi Trang",`${pg.name} · bài #${p.id} (${L[k]})`); return {...p,page_name:pg.name}; }
    if((m=P.match(/^\/page-grow\/(\d+)\/skip$/))){ S.pg.upcoming=S.pg.upcoming.filter(x=>x.id!=m[1]); return view(); }
    throw new Error("Không hỗ trợ"); }
  function demoNh(method,P,qs,body){ if(body&&"auto" in body) S.nhAuto=!!+body.auto; const auto=S.nhAuto!==false;
    const SIG=[[],[["comment",18,"3 bình luận bị nhóm xóa"],["removed",8,"1 bài bị gỡ / ẩn"]],[["block",35,"Bị Facebook chặn / checkpoint 1 lần trong 7 ngày"],["removed",16,"2 bài bị gỡ / ẩn"],["friends",10,"Chỉ 17% lời mời kết bạn được đồng ý (2/12)"]]];
    const ADV={block:"Cho nick nghỉ vài ngày, sếp đăng nhập tay lướt như người thường; giữ nửa trần khi chạy lại",comment:"Bớt bình luận ở nhóm đã xóa bình luận; câu bình luận ngắn, đúng nội dung bài",removed:"Xem nội quy các nhóm đã gỡ bài (Luật Facebook → sự cố), bớt đăng nhóm cấm bán hàng",friends:"Mời ít hơn, chỉ mời người đang hỏi nguồn hàng hợp ngành"};
    const acs=S.accounts.filter(a=>a.enabled), items=acs.map((a,i)=>{ const sg=SIG[i===1?1:i===acs.length-1?2:0], sc=100-sg.reduce((n,x)=>n+x[1],0), lv=sc>=80?"good":sc>=50?"warn":"bad";
      return {id:a.id,name:a.name,sale_name:(S.sales.find(x=>x.id===a.sale_id)||{}).name,score:sc,level:lv,label:{good:"Khỏe",warn:"Cần để ý",bad:"Nguy hiểm"}[lv],
        signals:sg.map(([c,m,t])=>({code:c,minus:m,text:t})),advice:sg.slice(0,2).map(x=>ADV[x[0]]),factor:auto?{good:1,warn:0.75,bad:0.5}[lv]:1}; }).sort((x,y)=>x.score-y.score);
    const counts={good:0,warn:0,bad:0}; items.forEach(r=>counts[r.level]++); return {items,counts,auto}; }
  function demoIb(method,P,qs,body){ let m; const ago=min=>{ const d=new Date(Date.now()-min*60000), p=n=>String(n).padStart(2,"0"); return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:00`; };
    if(!S.ib){ S.ib={settings:{page_inbox_on:"1",page_inbox_minutes:"10",page_inbox_auto:"0"},last:now(),items:[
      {id:1,name:"Shop Mộc An",phone:null,last_text:"Shop mình cần nhập trà gừng túi lọc tầm 200 hộp, bên bạn báo giá sỉ giúp mình nhé",last_at:ago(35),status:"waiting",left_h:23.4,draft:`Dạ em chào shop Mộc An ạ! Trà gừng túi lọc bên em có sẵn, nhập 200 hộp được giá sỉ tốt. Shop cho em xin SĐT hoặc Zalo để em gửi catalog, ảnh thật và báo giá trực tiếp nhé? Hoặc shop nhắn Zalo ${S.settings.price_zalo||"0386992326"} ạ.`},
      {id:2,name:"Ngọc Trâm",phone:"0912 345 678",last_text:"Số mình 0912 345 678, gửi mình bảng giá bột ngũ cốc nha",last_at:ago(190),status:"waiting",left_h:20.8,draft:"Dạ em cảm ơn chị Trâm ạ! Em nhắn Zalo cho chị trong ít phút để gửi catalog và báo giá bột ngũ cốc nhé."},
      {id:3,name:"Hùng Livestream",phone:null,last_text:"Bên bạn có nhận gia công nhãn riêng không",last_at:ago(600),status:"sent",sent_text:"Dạ bên em nhận gia công in nhãn riêng ạ, anh cho em xin SĐT/Zalo để em gửi quy trình và mẫu nhé.",left_h:null},
      {id:4,name:"Bảo Ngọc",phone:null,last_text:"Cho mình xin catalog",last_at:ago(1600),status:"expired",left_h:null}]}; }
    const view=()=>({configured:true,items:S.ib.items,counts:{},last_sync:S.ib.last,settings:{...S.ib.settings}});
    if(method==="GET") return view();
    if(P==="/page-inbox/sync"){ S.ib.last=now(); return {ok:true,conversations:4,new:0,answered:0}; }
    if(P==="/page-inbox/settings"){ Object.assign(S.ib.settings,body); return view(); }
    if((m=P.match(/^\/page-inbox\/(\d+)\/(send|skip|redraft)$/))){ const t=S.ib.items.find(x=>x.id==m[1]); if(!t||t.status!=="waiting") throw new Error("Cuộc trò chuyện này không còn chờ trả lời");
      if(m[2]==="skip"){ t.status="skipped"; return t; }
      if(m[2]==="redraft"){ t.draft=`Dạ em chào ${t.name} ạ! Anh/chị cho em xin SĐT hoặc Zalo để em gửi ảnh thật, catalog và báo giá sỉ nhé?`; return t; }
      const txt=String(body.text||t.draft||"").trim(); if(/chữa|khỏi bệnh|giảm cân/i.test(txt)) throw new Error("Câu trả lời vi phạm Luật Facebook: hứa công dụng chữa bệnh");
      Object.assign(t,{status:"sent",sent_text:txt,left_h:null}); log("ha","Trả lời tin nhắn Fanpage",`Gửi ${t.name}: “${txt.slice(0,60)}”`); return t; }
    throw new Error("Không hỗ trợ"); }
  function demoCm(method,P,qs,body){ const q=new URLSearchParams(qs||""), td=today(); let m;
    const acc=sid=>{ const a=S.accounts.find(x=>x.sale_id===sid)||{}; return {account_id:a.id||null,account_name:a.name||((S.sales.find(x=>x.id===sid)||{}).name)||""}; };
    const row=b=>{ const p=S.posts.find(x=>x.id===b.post_id)||{}; return {...b,title:p.title||(p.content||"").split("\n")[0].slice(0,70),group_name:p.group_name||"",posted_url:p.posted_url||""}; };
    const ps=S.posts.filter(p=>p.status==="posted");
    if(!S.cm){ S.cm=[]; S.cmId=900; const tx=demoBumpLines(6); ps.filter(p=>p.sale_id&&p.bump_enabled!==0&&p.permalink_status==="found").slice(0,6).forEach((p,i)=>{ const st=i<3?"done":i<5?"scheduled":"failed";
      const h=`${td} ${st==="done"?"19":"20"}:${String(31+i*5).padStart(2,"0")}`; S.cm.push({id:++S.cmId,post_id:p.id,...acc(p.sale_id),text:tx[i],status:st,scheduled_for:h,done_at:st==="done"?h+":20":null,error:st==="failed"?"Không thấy ô bình luận: nhóm đã tắt bình luận bài này":null,gain_comments:i===0?2:i===1?0:null,gain_leads:i===0?1:i===1?0:null,measured_at:i<2?h:null,_day:td}); });
      const gp=ps.find(p=>p.group_id&&p.sale_id&&!S.cm.some(b=>b.post_id===p.id)); S.cmRest=gp?[{id:gp.group_id,name:gp.group_name||"Nhóm",no_bump_until:`${td.slice(0,8)}28 08:00:00`}]:[]; S.cmStop=[]; S.cmGo=[]; }
    if((m=P.match(/^\/comments\/(post|group)\/(\d+)\/resume$/))){ if(m[1]==="group") S.cmRest=S.cmRest.filter(g=>g.id!=m[2]); else S.cmGo.push(+m[2]); return {ok:true}; }
    if(method==="GET"){ const day=q.get("day")||td, st=q.get("status")||"", aid=+q.get("account_id")||null, s=(q.get("q")||"").toLowerCase();
      const all=S.cm.filter(b=>(b.scheduled_for||"").slice(0,10)===day).map(row); const counts={scheduled:0,running:0,done:0,failed:0,skipped:0}; all.forEach(b=>counts[b.status]++);
      const items=all.filter(b=>(!st||b.status===st)&&(!aid||b.account_id===aid)&&(!s||(b.text+b.title+b.group_name).toLowerCase().includes(s)));
      const posts=ps.map(p=>{ const b=[...S.cm].reverse().find(x=>x.post_id===p.id&&x._day===td), a=acc(p.sale_id);
        const rest=S.cmRest.find(g=>g.id===p.group_id), stop=!b&&p.sale_id&&!rest&&!S.cmGo.includes(p.id)&&p.bump_enabled!==0&&p.permalink_status==="found"&&(S.cmStop.length<2&&!S.cmStop.includes(p.id)?S.cmStop.push(p.id):S.cmStop.includes(p.id));
        const reason=b?null:rest&&p.sale_id?`Nhóm đã xóa bình luận của mình: tạm ngừng bình luận nhóm này tới ${rest.no_bump_until.slice(8,10)}/${rest.no_bump_until.slice(5,7)}`:stop?"3 lượt bình luận gần nhất không thêm bình luận hay khách nào: Bảo thôi bình luận bài này":!p.sale_id?"Không do nick sale đăng (fanpage/sếp tự đăng) nên không tự bình luận được":p.permalink_status==="removed"?"Bài đã bị gỡ hoặc ẩn":p.bump_enabled===0?"Sếp đã tắt tự bình luận bài này":p.permalink_status==="pending"?"Bài đang chờ nhóm duyệt, có link mới bình luận được":"Hết lượt hôm nay của nick (trần an toàn), mai bình luận tiếp";
        return {id:p.id,title:row({post_id:p.id}).title,posted_at:p.posted_at,posted_url:p.posted_url,account_id:p.sale_id?a.account_id:null,account_name:p.sale_id?a.account_name:"",permalink_status:p.permalink_status,bump_enabled:p.bump_enabled,bump_count:p.bump_count||0,group_name:p.group_name,stopped:!!stop&&!b,resting:!!rest&&!b&&!!p.sale_id,today:b?{id:b.id,status:b.status}:null,reason}; });
      const nicks=workingNicks().map(a=>({id:a.id,name:a.name,limit:6,per_nick:+S.settings.bump_max_per_nick||8,used:S.cm.filter(b=>b.account_id===a.id&&b._day===td&&b.status==="done").length}));
      const dn=S.cm.filter(b=>b.status==="done").length, tops=ps.filter(p=>p.sale_id).slice(0,3);
      const effect={days:30,done:dn+41,measured:dn+33,useful:15,comments:26,leads:4,removed:S.cmRest.length,useful_pct:Math.round(1500/(dn+33)),stop_after:+S.settings.bump_stop_after||3,resting:S.cmRest,
        top:tops.map((p,i)=>({post_id:p.id,title:row({post_id:p.id}).title,group_name:p.group_name,n:6-i,gc:[7,4,3][i],gl:[2,1,1][i]}))};
      return {effect,day,today:td,items,counts,posts,nicks,covered:posts.filter(p=>p.today).length,eligible:posts.filter(p=>p.today||/^Hết lượt|^Chờ/.test(p.reason||"")).length,planned_today:true,settings:{...S.settings}}; }
    const b=S.cm.find(x=>x.id==(P.match(/\/comments\/(\d+)/)||[])[1]); if(!b) throw new Error("Không tìm thấy lượt bình luận này");
    if(method==="PUT"){ if(b.status!=="scheduled") throw new Error("Chỉ sửa được bình luận đang chờ gửi"); const t=String(body.text||"").trim().replace(/\s+/g," "); if(t.length<4) throw new Error("Câu bình luận quá ngắn"); b.text=t; log("bao","Sửa bình luận",`Sếp sửa câu bình luận bài #${b.post_id}: “${t.slice(0,60)}”`); return row(b); }
    if((m=P.match(/\/(cancel|retry|rewrite)$/))){
      if(m[1]!=="retry"&&b.status!=="scheduled") throw new Error("Chỉ sửa, hủy hoặc viết lại bình luận đang chờ gửi");
      if(m[1]==="cancel"){ b.status="skipped"; b.error="Sếp hủy"; return row(b); }
      if(m[1]==="rewrite"){ b.text=demoBumpLines(1)[0]; return row(b); }
      if(!["failed","skipped"].includes(b.status)) throw new Error("Chỉ thử lại lượt bị lỗi hoặc bỏ qua");
      if(S.cm.some(x=>x.post_id===b.post_id&&x._day===td&&["scheduled","running","done"].includes(x.status))) throw new Error("Bài này hôm nay đã có lượt bình luận (mỗi bài tối đa 1 lần/ngày)");
      const n={...b,id:++S.cmId,status:"scheduled",error:null,done_at:null,scheduled_for:now().slice(0,16),_day:td}; S.cm.push(n); return row(n); }
    throw new Error("Không hỗ trợ"); }
  function demoBumpPlan(){ const ps=S.posts.filter(p=>p.status==="posted"&&p.sale_id&&p.bump_enabled!==0&&p.permalink_status!=="removed").slice(0,8); const tx=demoBumpLines(ps.length);
    S.status.nam={state:"working",text:"Rà soát bài đã đăng, viết câu bình luận kèm ảnh"}; setTimeout(()=>{ S.status.nam={state:"idle",text:`Hôm nay xếp ${ps.length} lượt up bài`}; },3000);
    log("bao","Lịch up bài",`Rà soát bài đã đăng: xếp ${ps.length} lượt bình luận ảnh kèm câu mới và dòng liên hệ`);
    const td=today(); S.cm=S.cm||null; if(S.cm===null) demoCm("GET","/comments","",{}); const sel=ps.filter(p=>!S.cm.some(x=>x.post_id===p.id&&x._day===td&&x.status!=="skipped"&&x.status!=="failed"));
    const it=sel.map((p,i)=>{ const a=S.accounts.find(x=>x.sale_id===p.sale_id)||{}; const n={id:++S.cmId,post_id:p.id,account_id:a.id||null,account_name:a.name||"",text:tx[i],status:"scheduled",scheduled_for:now().slice(0,16),_day:td}; S.cm.push(n); return n; });
    it.forEach((b,i)=>setTimeout(()=>{ b.status="done"; b.done_at=now(); },4000+i*3000));
    ps.forEach((p,i)=>setTimeout(()=>{ p.bump_count=(p.bump_count||0)+1; p.last_bump_at=now(); p.last_bump="done|||"; log(`sale-${p.sale_id}`,"Up bài",`Bình luận ảnh vào bài #${p.id}: “${tx[i]}”`); },4000+i*3000)); return ps.length; }
  // CEO gọi đúng người phụ trách lên phòng nhận việc (giống WHO trong backend/ceo_orders.py)
  function demoSummon(t){ const low=t.toLowerCase(), who=new Set();
    const called=AGENT_DEFS.find(g=>g.id!=="ceo"&&new RegExp(`(gọi|kêu|mời)\\s+${g.name.toLowerCase()}\\s`,"u").test(low)); if(called) who.add(called.id);
    if(!called) [[/viết|bài viết/,"lan"],[/lịch|nhóm/,"tuan"],[/website|seo/,"vy"],[/trang|page/,"nhi"],[/khách sỉ|tìm khách/,"mai"],[/tin nhắn|trả lời khách/,"ha"],[/báo cáo|số liệu/,"khoa"],[/up bài|bình luận/,"bao"],[/bán chạy|tuyển/,"minh"]]
      .forEach(([rx,a])=>{ if(rx.test(low)) who.add(a); });
    [...who].slice(0,3).forEach(a=>log(a,"Lên phòng CEO nhận việc",t.slice(0,120))); }
  function demoCeoDo(t){ const low=t.toLowerCase();
    if(/^viết bài đi$|^viết bài$|^đăng bài đi$/.test(low.trim())) return ["Dạ sếp muốn em viết bài về sản phẩm nào ạ?",null,{type:"clarify",question:"Dạ sếp muốn em viết bài về sản phẩm nào ạ?",options:["Trà gừng mật ong","Bột ngũ cốc","Sản phẩm đang bán chạy"]}];
    if(["trà gừng mật ong","bột ngũ cốc","sản phẩm đang bán chạy"].includes(low.trim())) return [`Dạ, em giao Lan viết 3 bài về ${t.trim().toLowerCase()} (theo bài mẫu của sếp), CEO chấm xong em cho Tuấn xếp lịch.`];
    if(/vì sao.*ít khách|báo cáo tuần/.test(low)) return ["Dạ sếp, 14 ngày qua có 48 SĐT, sếp đã gọi 36, chốt 5 đơn (12,6 triệu).","Nút thắt: kênh trang / shop livestream ra 18 SĐT nhưng 0 đơn, đa số “sai tệp”. Em đã cho Mai đòi bằng chứng đang bán online và dồn sức đọc nhóm hỏi nguồn (ra 2 đơn / 9 SĐT)."];
    if(/hướng mới|từ khóa mới|giống khách đã mua/.test(low)) return ["Dạ em đã xem 5 khách mua gần nhất: đa số bán livestream đồ uống healthy, hay viết “cần nguồn ổn định”.","Đã cho thử 14 ngày: Mai (hướng 1): livestream trà healthy; Mai (hướng 4): cần nguồn trà ổn định; Tìm nhóm: hội bán đồ uống healthy online. Không ra SĐT thì em bỏ."]; const ag=[["lan","Lan"],["tuấn","Tuấn"],["hà","Hà"],["khoa","Khoa"],["minh","Minh"]].find(([k])=>new RegExp(`(^|\\s)${k}(\\s|$|,)`).test(low));
    const crit=/(sai|không đúng|dài quá|quá dài|ngắn quá|kém|đừng|không được|phải|nên|cấm|nhầm|chán|nhạt|sửa)/.test(low); let m;
    if(/tình hình|thế nào|báo cáo/.test(low)&&!crit){ const st=stats(); return ["Dạ sếp, tình hình hôm nay:",`Hôm nay ${S.kpiPhone||3}/5 khách có SĐT; ${st.drafts} bài nháp; ${st.approved} bài đã duyệt/lên lịch; ${st.posted_total} bài đã đăng.`]; }
    if(ag&&crit){ const aid=ag[0]==="tuấn"?"tuan":ag[0]==="hà"?"ha":ag[0]; S.lessons.push({id:id(),agent_id:aid,text:t,evidence:"Sếp nhắc qua CEO",source:"boss",confidence:1,pinned:1}); log(aid,"CEO yêu cầu sửa",t); return ["Dạ em nhận việc.",`Yêu cầu ${ag[1]} sửa: “${t}” (đã ghim vào sổ tay, áp dụng từ việc tiếp theo)`]; }
    if(!/(chỉ|ưu tiên|tập trung|không|đừng|cấm|tránh)\s+(đăng|post)/.test(low)&&!/\bbị\b|tại sao|vì sao|hôm qua|\?\s*$/.test(low)&&(m=low.match(/(?:đăng|post)\s*(?:\d+\s*)?(?:bài\s*)?(?:viết\s*)?(?:ngay\s*)?(?:lên|vào|ở|trong|tại|cho)\s*(?:các\s*|những\s*|mấy\s*)?(?:nhóm|group|hội)\s*(?:có\s*)?(?:từ khóa|tên|chữ|về|liên quan(?: tới| đến)?)?\s*[:“"']?\s*(.+)/))){
      const what=m[1].replace(/[”"'.!?]+$/,"").replace(/\s+(ngay|luôn|hôm nay|nhé|nha|giúp|giùm)(\s.*)?$/,"").trim(); const kws=tgWords(what.split(/,|;| và | hoặc /).join(",")); const kw=kws.map(k=>`“${k}”`).join(", ");
      const nm=low.match(/(\d+)\s*(bài|nhóm)/); const found=S.groups.filter(g=>tgHit(g,kws)&&!tgHit(g,S.tg.exclude)); const rd=found.filter(ready);
      if(!found.length) return ["Dạ em nhận việc.",`Chưa có nhóm nào có từ khóa ${kw} trong danh sách nhóm. Sếp nhắn “tìm nhóm theo chủ đề ${kws[0]||""}” để sale đi tìm và xin vào nhóm trước`];
      if(!rd.length) return ["Dạ em nhận việc.",`Có ${found.length} nhóm có từ khóa ${kw} nhưng hôm nay chưa nhóm nào đăng được (đang giãn cách sau bài trước)`];
      const want=Math.min(nm?+nm[1]:rd.length,rd.length,10); const ap=S.posts.filter(p=>p.status==="approved"&&p.target_type==="group").length;
      if(ap<want) genPosts(want-ap,null,"group").forEach(p=>p.status="approved");
      const pl=plan(g=>rd.includes(g),want);
      return ["Dạ em nhận việc.",`Có ${found.length} nhóm có từ khóa ${kw}, hôm nay đăng được ${rd.length} nhóm. Em giao đăng ${want} nhóm. ${ap<want?`Lan viết thêm ${want-ap} bài, em đã duyệt. `:""}Tuấn xếp ${pl.length} bài: ${pl.map(x=>`${x.time.slice(11)} ${x.sale?x.sale+" → ":""}${x.group}`).join("; ")}.`]; }
    if(/(rà soát|comment|bình luận|cmt|up)\s*(lại\s*)?(vào\s*|cho\s*)?(các\s*|những\s*|mấy\s*)?(bài|post)\s*(viết\s*)?(đã|vừa)\s*đăng|\bup (lại )?(các |những )?bài\b/.test(low)){ const n=demoBumpPlan(); const ex=demoBumpLines(1)[0];
      return ["Dạ em nhận việc.",`Bảo rà soát bài đã đăng và xếp ${n} lượt bình luận ảnh, mỗi bài một câu riêng kèm “${S.settings.bump_contact}”. Sale bắt đầu trong vài phút. VD: “${ex}”`]; }
    if(/(lướt|đọc|quét)\s*(feed|bảng tin)|groups\/feed|bảng tin (các )?nhóm|feed (các )?nhóm/.test(low)){ const r=demoRp("POST","/feed/run","",{});
      return ["Dạ em nhận việc.",`${r.queued.length} nick đi lướt bảng tin nhóm (${r.queued.join(", ")}), mỗi nick đọc ít nhất ${S.fd.settings.feed_min_posts} bài. Bảo chỉ chọn người đang hỏi mua (bình luận kèm ảnh) và người đang bán hàng online (chào nhẹ kèm Zalo), không comment mọi bài vì Facebook coi là spam và khóa nick. Sếp duyệt ở trang Trả lời khách, duyệt xong nick gửi trong giờ làm, cách nhau 45–90 phút.`]; }
    if(/(comment|bình luận|cmt|trả lời|rep)\b.{0,60}(nhóm|group|hội|người hỏi|bài hỏi|hỏi mua)|tìm (bài|người) hỏi (mua|nguồn|hàng)/.test(low)){ const r=demoRp("POST","/replies/scan","",{}); const q=rpQuota(r.account_id);
      return ["Dạ em nhận việc.",`Nick ${r.account} đi đọc các nhóm sôi nổi nhất, Bảo chọn bài đang HỎI MUA / hỏi nguồn hàng hợp ngành và viết sẵn câu trả lời. Sếp duyệt ở trang Trả lời khách, duyệt xong nick gửi trong giờ làm, mỗi nick tối đa ${q.limit} câu/ngày, cách nhau 45–90 phút.${/24\/24|24\/7|cả đêm|liên tục/.test(low)?" Em không cho chạy 24/24 và không bình luận dạo: Facebook coi là spam, nhóm xóa bình luận và khóa nick.":""}`]; }
    if((m=low.match(/viết\s*(\d+)?\s*bài/))){ const n=+(m[1]||3); S.status.lan={state:"working",text:`Đang viết ${n} bài`}; setTimeout(()=>{ genPosts(n,null,"group"); S.status.lan={state:"idle",text:`Vừa viết xong ${n} bài`}; },5000); return ["Dạ em nhận việc.",`Giao Lan viết ${n} bài đăng nhóm (CEO sẽ duyệt rồi cho Tuấn xếp lịch)`]; }
    if(/xếp lịch|lên lịch/.test(low)){ const pl=plan(); return ["Dạ em nhận việc.",`Giao Tuấn xếp lịch: ${pl.length} bài đã có giờ đăng`]; }
    if(/(tìm|kiếm|săn)\b.{0,30}?(nhóm|group|cộng đồng)/.test(low)){ setTimeout(()=>S.chat.push({id:id(),role:"ceo",text:`Linh tìm xong theo “${S.gf.today.join("”, “")}”: 2 nhóm mới, em đã thêm 1 nhóm tốt vào danh sách Hội nhóm: Kinh Doanh Online Tại Nhà. Đã vào 1 nhóm, đang chờ duyệt 0 nhóm.`,via:"web",created_at:now()}),10000); const kws=(t.match(/[“"']([^”"']{3,60})[”"']/g)||[]).map(x=>x.slice(1,-1)); if(kws.length){ S.gf.today=kws; S.gf.by="boss"; } return ["Dạ em nhận việc.",`Giao sale Linh lướt Facebook rồi tìm nhóm: ${S.gf.today.join(", ")}`]; }
    if(/\bhọp\b/.test(low)){ const topic=t.replace(/.*?họp\s*(về|bàn)?\s*/i,""); startMeeting(topic||null); return ["Dạ em nhận việc.",`Triệu tập họp${topic?": "+topic:""}`]; }
    if(/từ nay|từ giờ|luôn luôn|không được|cấm|bắt buộc/.test(low)){ const o={id:id(),agent:"all",text:t,active:1,created_at:now()}; S.orders.unshift(o); return ["Dạ em nhận việc.",`Ghi chỉ đạo lâu dài #${o.id} cho cả đội: “${t}”`]; }
    return ["Dạ em chưa hiểu rõ việc này. Sếp nói cụ thể hơn giúp em, ví dụ: “Viết 3 bài về trà gừng”, “Tìm nhóm theo chủ đề hội chạy quảng cáo facebook”, “Lan viết dài quá, viết ngắn lại”.",null]; }
  function demoCompany(){
    const c=S.co; const ai=Math.round(0.42*25800); const revenue=c.orders.reduce((a,o)=>a+o.amount,0); const spent=ai;
    const by_task=[["posts","Viết bài đăng (Lan)",.19,96],["meeting","Họp giao ban (cả đội)",.11,230],["replies","Tư vấn, trả lời khách (Hà, sale)",.08,61],["learning","Tự học mỗi đêm (cả đội)",.04,23]].map(([task,label,usd,calls])=>({task,label,usd,calls,vnd:Math.round(usd*25800)}));
    const last7=[...Array(7)].map((_,i)=>{ const d=new Date(Date.now()-(6-i)*864e5); return {date:d.toISOString().slice(0,10),vnd:[420,510,380,640,470,550,300][i]}; });
    const avg=Math.round(last7.reduce((a,d)=>a+d.vnd,0)/7);
    const rv=(sid,got,tgt,day,wd)=>({period_start:"2026-10-12",day,work_days:wd,target_so_far:tgt,target_month:Math.round(tgt/wd*30),leads_phone:got,pct:Math.round(got/tgt*100),risk:got/tgt>=.9?"safe":got/tgt>=.6?"warn":"danger",days_left:30-day});
    const sales=S.sales.filter(x=>!x.is_sample).map((r,i)=>({...r,status:r.status||"active",review:r.hired_by==="ceo"&&r.login_status!=="ok"?{risk:"waiting",day:0,work_days:0,target_so_far:0,target_month:60,leads_phone:0,pct:0}:rv(r.id,[38,21,9][i%3],44,23,22)}));
    if(!sales.filter(x=>x.hired_by!=="ceo").length){ sales.unshift({id:1,name:"Linh",fb_name:"Linh Nguyễn",status:"active",review:rv(1,38,44,23,22)},{id:2,name:"Phương",fb_name:"Phương Sỉ Tận Gốc",status:"active",review:rv(2,26,44,23,22)},{id:9,name:"Quân",fb_name:"Quân Đặc Sản Quê",status:"fired",fire_reason:"Kỳ 12/09 → 11/10: 19/52 khách có SĐT (26 ngày làm việc), không đạt KPI tháng."}); }
    return {status:c.status,founded_at:c.founded_at,day:c.day,trial_days:c.trial_days,dissolved_at:c.dissolved_at,dissolved_reason:c.dissolved_reason,
      finance:{capital:c.capital,ai_vnd:ai,ai_usd:0.42,spent,left:c.capital-spent,by_task,last7,avg_day:avg,runway_days:avg?Math.floor((c.capital-spent)/avg):null,revenue,orders:c.orders.length,customers:c.orders.length,profit:revenue-spent,rate:25800},
      sales,orders:c.orders};
  }
  function demoKpi(){
    const d=new Date(); const mn=+S.settings.kpi_min||5, mx=+S.settings.kpi_max||10; const ph=S.kpiPhone??3;
    const history=[...Array(14)].map((_,i)=>{ const x=new Date(d-(13-i)*864e5); const v=i===13?ph:[4,6,5,7,3,8,6,5,9,6,11,7,8][i]; const p2=n=>String(n).padStart(2,"0"); return {date:`${x.getFullYear()}-${p2(x.getMonth()+1)}-${p2(x.getDate())}`,target_min:mn,target_max:mx,leads_phone:v,leads_total:v+3,achieved:+(v>=mn)}; });
    const boss=S.leads.filter(l=>l.escalated_at&&!["ordered","lost"].includes(l.status)&&l.boss_status!=="called").length;
    const td={date:today(),target_min:mn,target_max:mx,leads_phone:ph,leads_total:ph+3,leads_no_phone:3,from_comments:ph+1,asked_phone:4,posts:3,bumps:5,escalated:ph,boss_pending:boss,ordered:1,achieved:ph>=mn,exceeded:ph>=mx,pct:Math.round(ph/mn*100)};
    return {today:td,pace:{expected:2.4,behind:false,frac:0.48},streak:4,history,per_sale:[{id:1,name:"Linh",active:true,target_min:3,target_max:5,leads_phone:Math.min(ph,2),leads:4,posts:2,bumps:3,asked:3,failed:0},{id:2,name:"Phương",active:true,target_min:3,target_max:5,leads_phone:Math.max(0,ph-2),leads:2,posts:1,bumps:2,asked:1,failed:0},{id:3,name:"Nam",active:false,target_min:0,target_max:0,leads_phone:0,leads:0,posts:0,bumps:0,asked:0,failed:0}]};
  }
  function demoLearning(){
    const all=[...AGENT_DEFS.map(a=>({...a,kind:"core"})),...saleAgents()];
    return {running:S.learnRunning,last:today(),agents:all.map(a=>{ const xp=S.xp[a.id]||0, L=lvl(xp);
      return {id:a.id,name:a.name,role:a.role,kind:a.kind,look:a.look,progress:{xp,level:L,level_xp:lxp(L),next_xp:lxp(L+1),goal:S.goals[a.id]||null},
        skills:SK[a.id]||[{label:"Khách mỗi bài",unit:"",now:0.7,prev:0.5},{label:"Đăng thành công",unit:"%",now:92,prev:85},{label:"Lượt up bài",unit:"",now:18,prev:9}],
        lessons:S.lessons.filter(l=>l.agent_id===a.id).sort((x,y)=>y.pinned-x.pinned||y.confidence-x.confidence),retired:a.id==="lan"?3:0}; }),
      data:{posts:23,need:40,each:15,ready:false},ai_last:"",
      choices:{explore:+(S.settings.learn_explore||0.25),golden_hours:[],
        angles:[["Sản phẩm dễ livestream",.38,9,8.4],["Biên lợi nhuận cho người bán",.19,7,4.6],["Nguồn hàng tận xưởng",.15,8,3.5],["Sản phẩm dễ chạy quảng cáo",.12,5,2.9],["Nhận in nhãn riêng (OEM)",.09,3,1.8],["Câu chuyện xưởng",.07,6,1.2]].map(([name,weight,n,avg])=>({name,weight,n,avg})),
        products:[["Bột ngũ cốc dinh dưỡng 25 loại hạt",.31],["Trà hoa đậu biếc - cỏ ngọt",.22],["Trà gừng mật ong túi lọc",.17],["Bột cần tây sấy lạnh",.12],["Cà phê hòa tan 3in1 vị đậm",.1],["Bột diếp cá - rau má",.08]].map(([name,weight])=>({name,weight}))}};
  }
  const nickOut=a=>{ const mine=S.posts.filter(p=>p.account_id===a.id); return {...a,posted_today:mine.filter(p=>p.status==="posted").length,scheduled_today:mine.filter(p=>["scheduled","posting"].includes(p.status)).length,
    groups_joined:S.groups.filter(g=>((g.joins||{})[a.id]||{}).status==="joined").length,
    diag:(()=>{ const n=mine.filter(p=>["posted","scheduled","posting"].includes(p.status)).length; const why=[];
      if(a.login_status!=="ok") why.push({level:"bad",text:"Nick chưa đăng nhập hoặc phiên đã hết",fix:"Bấm Mở Chrome, đăng nhập lại rồi bấm Kiểm tra"});
      else if(!n) why.push({level:"bad",text:"Nick không ở nhóm nào trong danh sách đăng",fix:"Cho nick xin vào nhóm (Hội nhóm → Tìm nhóm) hoặc Rà soát nhóm của nick"});
      return {idle:!n,why}; })()}; };
  const saleOut=r=>{ const mine=S.posts.filter(p=>p.sale_id===r.id); return {...r,agent_id:`sale-${r.id}`,busy:S.busy[r.id]||null,busy_account:S.busyAcc[r.id]||null,accounts:nicksOf(r.id).map(nickOut),max_accounts:5,posted_today:mine.filter(p=>p.status==="posted").length,scheduled_today:mine.filter(p=>["scheduled","posting"].includes(p.status)).length,failed:mine.filter(p=>p.status==="failed").length,
    recent:mine.slice(0,6).map(p=>({id:p.id,status:p.status,target_type:p.target_type,group_name:p.group_name,account_name:p.account_name,posted_at:p.posted_at,scheduled_for:p.scheduled_for,error:p.error,screenshot:null}))}; };
  function plan(only,limit){
    const ap=S.posts.filter(p=>p.status==="approved"&&p.target_type==="group").slice(0,limit||99); const gs=S.groups.filter(ready).filter(g=>!only||only(g)); const slots=["09:10","10:05","11:20","14:40","16:15","20:05"]; const out=[];
    const ok=workingNicks();
    ap.slice(0,gs.length).forEach((p,i)=>{ const g=gs[i]; const a=ok.length?ok[i%ok.length]:null; const sa=a?S.sales.find(x=>x.id===a.sale_id):null; Object.assign(p,{group_id:g.id,group_name:g.name,group_url:g.url,status:"scheduled",scheduled_for:`${today()} ${slots[i%6]}`,sale_id:sa?.id||null,sale_name:sa?.name||null,account_id:a?.id||null,account_name:a?.name||null}); out.push({post_id:p.id,group:g.name,time:p.scheduled_for,sale:sa?`${sa.name} · ${a.name}`:null}); });
    log("tuan","Xếp lịch",out.length?`Đã xếp ${out.length} bài vào ${out.length} nhóm`:"Chưa có bài đã duyệt để xếp lịch"); return out;
  }
  function stats(){
    const c=f=>S.posts.filter(f).length;
    return {drafts:c(p=>p.status==="draft"),approved:c(p=>["approved","scheduled"].includes(p.status)),posted_total:c(p=>p.status==="posted"),posted_today:c(p=>p.status==="posted"),
      groups:S.groups.length,groups_ready:S.groups.filter(ready).length,leads:S.leads.length,leads_new:S.leads.filter(l=>l.status==="new").length,
      prospects_a:S.pr.filter(x=>x.grade==="A"&&x.status==="verified").length,prospects_manual:S.pr.filter(x=>x.status==="needs_manual").length,
      leads_hot:S.leads.filter(l=>l.score>=75&&!["ordered","lost"].includes(l.status)).length,leads_ordered:S.leads.filter(l=>l.status==="ordered").length,
      errors_new:S.errors.filter(e=>e.status==="new").length,autopilot:S.settings.ceo_autopilot!=="0",tasks_open:S.tasks.filter(t=>t.status!=="done").length,ai_live:false,failed:c(p=>p.status==="failed"),kpi:demoKpi().today,company:S.co.status==="setup"?null:{status:S.co.status,day:S.co.day,trial_days:S.co.trial_days,capital:S.co.capital,capital_left:demoCompany().finance.left,revenue:demoCompany().finance.revenue,orders:S.co.orders.length,at_risk:demoCompany().sales.filter(r=>r.review&&["warn","danger"].includes(r.review.risk)).map(r=>`${r.name} (${r.review.leads_phone}/${r.review.target_so_far})`)},bumps_today:S.posts.reduce((n,p)=>n+(p.bump_count||0),0),sales_total:S.sales.length,sales_ok:S.sales.filter(x=>x.login_status==="ok"&&x.auto_post).length,sales_problem:S.sales.filter(x=>x.login_status!=="ok").length,nicks_total:S.accounts.length,nicks_ok:workingNicks().length,nicks_problem:S.accounts.filter(a=>a.enabled&&a.login_status!=="ok").length,best_group:"Tìm nguồn hàng sỉ - Đầu mối tận xưởng",lead_per_post:0};
  }
  const TOPICS=["Tuần này nên tập trung đẩy sản phẩm nào cho khách sỉ?","Đăng nhiều bài mỗi ngày hay ít bài nhưng chất lượng hơn?","Có nên công khai giá sỉ ngay trong bài đăng hội nhóm không?","Gửi mẫu thử miễn phí cho khách sỉ mới: có đáng chi phí không?","Nên ưu tiên tệp khách livestream hay tệp khách chạy quảng cáo?","Có nên đẩy dịch vụ in nhãn riêng (OEM) cho shop online không?"];
  const DEB={lan:["Em nghĩ phải mạnh dạn hơn: nội dung có video thật, câu chuyện xưởng sẽ khác biệt so với bài nguồn hàng đăng tràn lan.","Em đồng ý cần số liệu với anh Khoa, nhưng không thử nội dung mới thì lấy đâu ra số liệu để so ạ?"],
    tuan:["Em hơi lo: nhóm lớn kiểm duyệt rất chặt, làm quá tay là bị chặn đăng cả nick. Phải theo luật nhóm trước.","Em đề xuất thử ở 2 nhóm nhỏ trước, nhóm lớn giữ nhịp cũ. Chị Lan làm video thì em xếp vào khung 20h là đẹp."],
    ha:["Từ phía khách thì họ cần 3 thứ: giá rõ, có mẫu thử, có ảnh/video để bán lại. Đáp ứng được là chốt nhanh.","Em ủng hộ ý anh Tuấn. Khách mới sợ ôm hàng, chính sách nhập ít sẽ thuyết phục hơn mọi bài viết."],
    khoa:["Dữ liệu hiện chưa đủ để kết luận. Em đề xuất A/B test 7 ngày: chia đôi số bài, đo số khách và tỉ lệ chốt.","Nếu theo hướng của Lan thì đặt ngưỡng: sau 7 ngày không tăng ít nhất 20% khách/bài thì quay lại cách cũ."]};
  function startMeeting(topic){
    if(S.running) return S.running;
    topic = topic || TOPICS[Math.floor(Math.random()*TOPICS.length)];
    const m={id:id(),date:today(),topic,status:"running",summary:"",action_items:[],created_at:now()}; S.meetings.unshift(m); S.running=m.id;
    const st=stats(); const lines=[["minh","open",`Ok mọi người, họp sáng nay gọn nhé: báo cáo trước, rồi tranh luận "${topic}", cuối giờ mình chốt việc.`],
      ["ceo","open",`Chỉ đạo của tôi: doanh thu đang ${vnd(demoCompany().finance.revenue)}, mốc tăng người tiếp theo là 50 triệu. Mục tiêu tuần này: mọi nick đạt KPI, không để ai bị sa thải.`],
      ["lan","report",`Bên content: kho có ${st.drafts} bài nháp, ${st.approved} bài đã duyệt chờ đăng. Góc 'dễ livestream' đang được bình luận nhiều nhất.`],
      ["tuan","report",`Đang theo dõi ${st.groups} nhóm, hôm nay ${st.groups_ready} nhóm đủ điều kiện đăng lại. Đề nghị không đăng trùng nội dung giữa các nhóm.`],
      ["ha","report",`Có ${st.leads} khách tiềm năng, ${st.leads_new} khách mới chưa liên hệ, ${st.leads_hot} khách nóng. Khách hỏi nhiều nhất là chính sách gửi mẫu.`],
      ["khoa","report","Nhóm 'Tìm nguồn hàng sỉ' đang mang về nhiều khách nhất. Đề nghị gắn nguồn cho mọi khách để đo chính xác hơn."],
      ["minh","debate",`Cảm ơn mọi người. Giờ vào chủ đề chính: "${topic}". Cứ phản biện thẳng thắn.`],
      ...["lan","tuan","ha","khoa"].map(a=>[a,"debate",DEB[a][0]]), ...["khoa","lan","tuan","ha"].map(a=>[a,"debate",DEB[a][1]]),
      ["minh","close","Chốt lại: thử nghiệm có kiểm soát trong 7 ngày. Lan làm nội dung mới kèm video thật, Tuấn chỉ áp dụng ở nhóm nhỏ, Hà chuẩn hóa chính sách mẫu thử, Khoa đo A/B và báo cáo cuối tuần."],
      ["minh","close","Giao việc xong. Hết giờ họp, mọi người về vị trí làm việc nhé!"]];
    const items=[{agent_id:"lan",title:"Viết 3 bài mới có kịch bản video pha chế tại xưởng"},{agent_id:"tuan",title:"Chọn 2 nhóm nhỏ để thử nghiệm, lên lịch đăng tuần này"},{agent_id:"ha",title:"Soạn kịch bản tin nhắn gửi mẫu thử cho khách mới"},{agent_id:"khoa",title:"Thiết lập bảng A/B: khách/bài theo từng góc nội dung"}];
    const allIds=()=>AGENT_DEFS.map(a=>a.id).concat(S.sales.map(r=>`sale-${r.id}`));
    allIds().forEach(a=>S.status[a]={state:"meeting",text:"Đi tới phòng họp"});
    const saleLines=S.sales.map(r=>[`sale-${r.id}`,"report",`Em giữ nick ${r.fb_name}: hôm nay đã đăng ${S.posts.filter(p=>p.sale_id===r.id&&p.status==="posted").length} bài, còn ${S.posts.filter(p=>p.sale_id===r.id&&p.status==="scheduled").length} bài trong lịch. Tình trạng: ${r.login_status==="ok"?"nick hoạt động bình thường":"nick đang bị đăng xuất, nhờ sếp đăng nhập lại"}.`]);
    lines.splice(6,0,...saleLines);
    let i=0;
    const step=()=>{
      if(S.bossQ&&S.bossQ.length){ const t=S.bossQ.shift(); push("minh","boss",`Dạ em ghi nhận ý kiến của sếp: "${t}". Cả nhóm sẽ tính đến điểm này khi chốt việc.`); return setTimeout(step,2600); }
      if(i>=lines.length){ m.status="done"; m.summary=lines[lines.length-2][2].replace("Chốt lại: ",""); m.action_items=items;
        items.forEach(it=>S.tasks.unshift({id:id(),agent_id:it.agent_id,title:it.title,status:"todo",meeting_id:m.id}));
        S.running=null; allIds().forEach(a=>S.status[a]={state:"idle",text:"Quay về bàn làm việc"}); log("minh","Kết thúc họp",`Chủ đề: ${topic}. Giao 4 việc.`);
        setTimeout(()=>{S.status.lan={state:"working",text:"Đang viết 3 bài"}; setTimeout(()=>{genPosts(3,null,"group"); S.status.lan={state:"idle",text:"Vừa viết xong 3 bài"};},5000);},4000);
        return; }
      const [a,ph,t]=lines[i++]; push(a,ph,t); setTimeout(step,2600);
    };
    const push=(a,ph,t)=>{ allIds().forEach(x=>{ if(S.status[x]?.state==="talking") S.status[x]={state:"meeting",text:"Đang họp"}; }); S.status[a]={state:"talking",text:t.slice(0,60)}; S.msgs.push({id:id(),meeting_id:m.id,agent_id:a,phase:ph,content:t,created_at:now()}); };
    setTimeout(step,3200); return m.id;
  }
  function reply(l,msg){ const n=l.name; return `Chào ${n} ạ! Cảm ơn ${n} đã quan tâm hàng bên xưởng 🌿\nMình gửi ${n} ảnh thật nhé; giá sỉ ${n} nhắn Zalo ${ZALO()} để được báo trực tiếp. Với nhu cầu "${l.need||msg}", mình gợi ý ${n} nhập thử combo nhỏ trước để test thị trường, xưởng gửi kèm mẫu thử + bộ ảnh/video để ${n} đăng bán luôn.\n${n} đang bán chủ yếu kênh nào (live, ads hay sàn) để mình tư vấn sản phẩm hợp nhất ạ?`; }
  const wait=ms=>new Promise(r=>setTimeout(r,ms));

  /* Phòng ban (bản xem trước) */
  const DP_LOOK={skin:"#f2c9a0",pants:"#2c2236",hair:"#3b2414",hairStyle:"bun",accessory:"glasses"};
  function dpState(){ if(S.dp) return S.dp; const td=today();
    S.dp={id:3,staff:[{id:1,dept:"website",position:"seo_writer",name:"Thảo",desk:20}],
      reviews:{website:{summary:"Viết 6 bài trong 14 ngày, SEO trung bình 84/100; còn 18 từ khóa chờ viết (4,5 tuần).",bottleneck:"Từ khóa chờ viết nhiều hơn sức viết",plan:["Vy viết 3 bài, Thảo viết 1 bài, đo điểm SEO từng bài","Ưu tiên từ khóa gia công trà túi lọc","Duyệt hết bài chờ trước thứ Sáu"],created_at:td+" 08:41:00"},
        pages:{summary:"2 Trang đang chạy, 11 bài đã đăng 7 ngày, 1 bài bỏ vì thiếu ảnh.",bottleneck:"Ảnh về chậm làm bỏ bài",plan:["Nhi gửi prompt ảnh sớm hơn 2 giờ","Trang Bếp viết bài bền nhiều hơn","Theo dõi Trang mới tạo"],created_at:td+" 08:42:00"},
        groups:{summary:"64 nhóm trong nick, 28 nhóm chưa đánh giá 7 ngày, mỗi lượt xem 8 nhóm.",bottleneck:"Nhóm chưa được rà soát kịp",plan:["Tuấn rà soát 8 nhóm mỗi lượt","Bảo theo dõi nhóm xóa bình luận","Thoát nhóm chợ spam"],created_at:td+" 08:43:00"},
        sales:{summary:"21 khách có SĐT 14 ngày, 3 đơn; 5 khách chờ sếp gọi.",bottleneck:"Khách có SĐT chưa được gọi kịp",plan:["Hà soạn kịch bản gọi 5 khách chờ","Mai tìm thêm 3 SĐT livestream","Lan viết bài nhắm người bán online"],created_at:td+" 08:44:00"}},
      props:[{id:1,dept:"website",position:"seo_writer",reason:"Còn 18 từ khóa chờ viết, với 3 bài/tuần phải mất 6 tuần; SEO trung bình 84/100",status:"done",ceo_note:"CEO tuyển",created_at:td+" 08:41:00"},
        {id:2,dept:"groups",position:"group_scout",reason:"28 nhóm trong nick chưa được đánh giá 7 ngày qua, mỗi lượt chỉ xem 8 nhóm (3,5 lượt mới xem hết)",status:"pending",ceo_note:"CEO đồng ý, chờ sếp duyệt",created_at:td+" 08:43:00"}]};
    return S.dp; }
  const DP_DEPTS=[["director","Phòng Giám đốc","ceo",["ceo","khoa"],"#d4af37","Điều hành toàn công ty: vốn, doanh thu, nhân sự, xét đề xuất của các phòng"],
    ["sales","Phòng Kinh doanh","minh",["minh","lan","ha","mai"],"#2f5d3a","Khách sỉ có số điện thoại và đơn hàng"],
    ["groups","Phòng Hội nhóm","tuan",["tuan","bao"],"#f08a24","Nhóm đăng được, nhóm tương tác cao, bình luận có ích, không để nick bị chặn"],
    ["pages","Phòng Trang Facebook","nhi",["nhi"],"#e0559b","Trang mới theo xu hướng bền, người theo dõi và tương tác bài Trang tăng đều"],
    ["website","Phòng Website","vy",["vy"],"#3c6fd8","Bài website chuẩn SEO đúng hạn, website luôn lên đúng hosting"]];
  const DP_POS={seo_writer:["website","Biên tập viên SEO",2,"Viết thêm 1 bài website chuẩn SEO mỗi tuần, bài ghi tên người viết"],
    page_editor:["pages","Biên tập Trang",2,"Viết bài (kèm prompt ảnh) cho một phần các Trang đang chạy; phòng được tự tạo thêm 1 Trang mỗi 7 ngày"],
    group_scout:["groups","Chuyên viên rà soát nhóm",2,"Mỗi lượt rà soát đánh giá thêm 6 nhóm trong các nick"],
    sale:["sales","Nhân viên sale",null,"Giữ 3–5 nick Facebook: đăng bài, up bài, quét bình luận (sếp cần thêm nick)"]};
  function demoStaff(){ const d=dpState(); return d.staff.map(s=>({id:"st-"+s.id,kind:"staff",name:s.name,role:`${DP_POS[s.position][1]} · ${DP_DEPTS.find(x=>x[0]===s.dept)[1]}`,
    short:DP_POS[s.position][3],personality:"Chăm chỉ",look:{...DP_LOOK,shirt:DP_DEPTS.find(x=>x[0]===s.dept)[4]},desk:s.desk,dept:s.dept,face:""})); }
  function demoDp(method,P,body){ const d=dpState(); let m; const nm=id=>(AGENT[id]||{}).name||id;
    if(method==="GET") return {ceo_mode:"auto",settings:{dept_on:"1",dept_review_weekday:"1",dept_review_time:"08:40"},depts:DP_DEPTS.map(([k,name,head,core,color,goal])=>({key:k,name,goal,color,head,head_name:nm(head),
      members:core.map(i=>({id:i,name:nm(i),role:(AGENT[i]||{}).role||"",head:i===head})).concat(d.staff.filter(s=>s.dept===k).map(s=>({id:"st-"+s.id,name:s.name,role:DP_POS[s.position][1],staff_id:s.id,head:false})))
        .concat(k==="sales"?saleAgents().map(a=>({id:a.id,name:a.name,role:a.role,head:false})):[]),
      review:d.reviews[k]||null,positions:Object.entries(DP_POS).filter(([p,v])=>v[0]===k).map(([p,v])=>({key:p,title:v[1],max:v[2],does:v[3],have:d.staff.filter(s=>s.position===p).length})),
      proposals:d.props.filter(x=>x.dept===k).slice().reverse()}))};
    if((m=P.match(/^\/departments\/(\w+)\/review$/))){ const r=d.reviews[m[1]]; if(r) r.created_at=today()+" "+new Date().toTimeString().slice(0,8); log(DP_DEPTS.find(x=>x[0]===m[1])[2],"Đánh giá phòng",(r||{}).summary||""); return {...(r||{}),decisions:[]}; }
    if((m=P.match(/^\/departments\/proposals\/(\d+)\/(approve|reject)$/))){ const p=d.props.find(x=>x.id==m[1]); if(!p||p.status!=="pending") throw new Error("Đề xuất này đã được xử lý");
      if(m[2]==="reject"){ p.status="rejected"; p.ceo_note="Sếp không duyệt"; return {status:"rejected"}; }
      const desk={groups:[18,19],website:[20,21],pages:[22,23]}[p.dept].find(x=>!d.staff.some(s=>s.desk===x)); const name=["Quân","Ngân","Phúc","Trâm"].find(n=>!d.staff.some(s=>s.name===n));
      d.staff.push({id:++d.id,dept:p.dept,position:p.position,name,desk}); p.status="done"; p.ceo_note="Sếp duyệt"; log("ceo","Tuyển nhân viên",`${name} vào làm ${DP_POS[p.position][1]}`); return {status:"done",name}; }
    if((m=P.match(/^\/departments\/staff\/(\d+)\/leave$/))){ d.staff=d.staff.filter(s=>s.id!=m[1]); return {ok:true}; }
    return {}; }
