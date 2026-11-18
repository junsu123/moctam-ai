  /* chỉ đạo nơi đăng + kết bạn (bản xem trước) */
  const viP=t=>" "+(t||"").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/đ/g,"d")+" ";
  const tgWords=v=>{ const a=Array.isArray(v)?v.join(","):(v||""); const out=[]; a.split(/[,;\n]+/).map(x=>x.trim()).filter(Boolean).forEach(w=>{ if(!out.some(o=>viP(o)===viP(w))) out.push(w.slice(0,60)); }); return out.slice(0,40); };
  const tgHit=(g,kws)=>{ const t=viP(`${g.name} ${g.topic||""} ${g.keyword||""}`); return kws.find(k=>{ const p=viP(k).trim(); return p&&new RegExp("(^|[^a-z0-9])"+p.replace(/[.*+?^${}()|[\]\\]/g,"\\$&")+"([^a-z0-9]|$)").test(t); }); };
  const tgClass=(g,c)=>{ let w=tgHit(g,c.exclude); if(w) return ["exclude",`có từ khóa tránh “${w}”`]; if(g.focus) return ["focus","sếp chọn tập trung đăng"]; w=tgHit(g,c.include); if(w) return ["match",`có từ khóa “${w}”`]; return ["other",""]; };
  const tgPreview=c=>{ const cnt={focus:0,match:0,other:0,exclude:0}; const ord={focus:0,match:1,other:2,exclude:3};
    const items=S.groups.map(g=>{ const [k,why]=tgClass(g,c); cnt[k]++; const posted=!(k==="exclude"||(c.mode==="only"&&k==="other")); return {id:g.id,name:g.name,members:g.members,focus:g.focus?1:0,managed:0,kind:k,why,will_post:posted,ready:true}; }).sort((a,b)=>ord[a.kind]-ord[b.kind]||(!a.will_post)-(!b.will_post));
    const usable=items.filter(i=>i.will_post).length; const warn=c.mode==="only"&&!usable?"Chưa có nhóm nào khớp chỉ đạo: Tuấn sẽ không xếp bài vào nhóm nào. Thêm từ khóa hoặc chọn nhóm tập trung.":c.mode!=="all"&&!(cnt.focus+cnt.match)?"Chưa có nhóm nào khớp từ khóa: Tuấn vẫn đăng các nhóm khác như bình thường.":"";
    return {counts:cnt,will_post:usable,warn,items}; };
  const tgOverview=()=>({...S.tg,modes:{},focus:S.groups.filter(g=>g.focus).map(g=>({id:g.id,name:g.name,members:g.members})),preview:tgPreview(S.tg)});
  const FR_PEOPLE=[["Phạm Thu Hương","Đang hỏi nguồn hàng hợp ngành; Đang bán hàng online; Đăng bài trong nhóm",90,"Mình đang tìm nguồn trà túi lọc, ngũ cốc giá sỉ để bán online, ai có xin ib"],
    ["Thảo Organic","Quan tâm trà, ngũ cốc, đồ uống; Đang bán hàng online; Hoạt động 3 lần trên bảng tin",80,"Chốt đơn ngũ cốc dinh dưỡng livestream tối nay, ai muốn làm ctv inbox"],
    ["Mẹ Bắp Shop","Quan tâm trà, ngũ cốc, đồ uống; Đang bán hàng online; Đăng bài trong nhóm",70,"Shop mình bán online đồ ăn vặt, trà sữa, ship toàn quốc"],
    ["Nguyễn Văn Bình","Đang hỏi nguồn hàng hợp ngành; Bình luận trong nhóm",70,"Mình cũng cần nhập granola, ai có nguồn xin giá sỉ với"],
    ["Hà Linh Store","Đang bán hàng online; Đăng bài trong nhóm",45,"Live 8h tối nay, xả kho đồ gia dụng"],
    ["Quỳnh Anh","Quan tâm trà, ngũ cốc, đồ uống; Bình luận trong nhóm",45,"Trà gừng mật ong uống mùa lạnh hợp ghê"],
    ["Đỗ Minh Tuấn","Bình luận trong nhóm; Hoạt động 2 lần trên bảng tin",30,"Hóng giá ạ"],
    ["Bếp Nhà Sim","Quan tâm trà, ngũ cốc, đồ uống; Đang bán hàng online; Bình luận trong nhóm",65,"Bên em đang bán bột ngũ cốc cho mẹ bầu, cần thêm mẫu trà"]];
  const frQuota=aid=>{ const f=aid===12?0.5:1; const lim=Math.floor(+S.fr.settings.fbp_friends_day*f); const used=S.fr.items.filter(x=>x.account_id===aid&&x.sent_at&&x.sent_at>=today()).length; return {limit:lim,used,left:Math.max(0,lim-used),factor:f,resting:false}; };
  const frAdd=(aid,gid,n)=>{ const nick=S.accounts.find(a=>a.id===aid), g=S.groups.find(x=>x.id===gid); let k=0;
    for(const [name,reason,score,snip] of FR_PEOPLE){ const url=`https://www.facebook.com/profile.php?id=${100040+FR_PEOPLE.findIndex(p=>p[0]===name)}`; if(k>=n||S.fr.items.some(x=>x.profile_url===url)) continue;
      S.fr.items.push({id:id(),account_id:aid,group_id:gid,group_name:g.name,nick:nick.name,name,profile_url:url,reason,score:score-(k%3)*5,snippet:snip,status:"suggested",created_at:now(),sent_at:null}); k++; } g.friends_scanned_at=now(); return k; };
  const frGroups=aid=>{ const nicks=S.accounts.filter(a=>a.enabled&&a.login_status==="ok"&&(!aid||a.id==aid));
    return S.groups.map(g=>{ const pd=(g.posts_month||0)/30, gr=g.members?(g.new_members_week||0)/g.members*100:0; const parts={posts:Math.min(30,pd*3),comments:Math.min(30,(g.avg_comments||0)*3),reactions:Math.min(15,(g.avg_reactions||0)/2),growth:Math.min(15,gr*15),size:g.members>=10?Math.min(10,Math.log10(g.members)*2):0};
      const it=S.fr.items.filter(x=>x.group_id===g.id); const [k]=tgClass(g,S.tg);
      return {id:g.id,name:g.name,url:g.url,members:g.members,score:Math.round(Object.values(parts).reduce((s,v)=>s+v,0)),known:!!g.posts_month,parts,per_day:Math.round(pd*10)/10,growth:Math.round(gr*100)/100,avg_comments:g.avg_comments,avg_reactions:g.avg_reactions,focus:g.focus?1:0,target:k,
        nicks:nicks.map(a=>({id:a.id,name:a.name})),scanned_at:g.friends_scanned_at||null,found:it.length,sent:it.filter(x=>["sent","accepted"].includes(x.status)).length,accepted:it.filter(x=>x.status==="accepted").length}; })
      .sort((a,b)=>(a.target==="exclude")-(b.target==="exclude")||(b.score+(b.focus?10:0))-(a.score+(a.focus?10:0))); };
  const BUMP_OPEN=["Xưởng vừa ra mẻ {p} mới","Ảnh thật {p} tại xưởng hôm nay","{p} đóng gói xong, sẵn hàng giao ngay","Mẻ {p} sáng nay vừa đóng thùng","Hàng {p} chuẩn xưởng, giá tận gốc","Nhận sỉ {p} số lượng lớn","Lô {p} mới về kho, ảnh thật","Shop online cần nguồn {p} thì ghé xưởng","{p} có sẵn, nhận in nhãn theo yêu cầu"];
  const BUMP_TAIL=[""," 🌿",", ship toàn quốc",", có hóa đơn đầy đủ",", nhận đơn từ 1 thùng"," 📦"];
  function demoBumpLines(n){ const c=(S.settings.bump_contact||"").trim(); const out=[];
    if(S.settings.bump_text_mode==="list"){ const L=(S.settings.bump_texts||"").split("\n").map(x=>x.trim()).filter(Boolean); for(let i=0;i<n;i++) out.push(L.length?L[Math.floor(Math.random()*L.length)]:""); }
    else { const used=new Set(), op=[...BUMP_OPEN].sort(()=>Math.random()-.5); while(out.length<n&&used.size<60){ const pr=S.products[Math.floor(Math.random()*S.products.length)]; let wd=(pr?pr.name:"trà, ngũ cốc").replace(/\s*[\(\[].*?[\)\]]/g,"").split(/\s[-–|/]\s|[,;:]/)[0].trim().split(/\s+/).slice(0,7); while(wd.length>2&&/^(\d+\S*|loại|vị|gói|túi)$/i.test(wd[wd.length-1])) wd.pop(); const p=wd.join(" ").toLowerCase();
      let l=op[(out.length+used.size)%op.length].replace("{p}",p); l=l[0].toUpperCase()+l.slice(1)+BUMP_TAIL[Math.floor(Math.random()*BUMP_TAIL.length)]; if(used.has(l)) continue; used.add(l); out.push(l); } }
    return out.map(l=>{ if(!l||!c) return l||c; l=l.replace(/[ .]+$/,""); return `${l}${/[\p{L}\p{N}]$/u.test(l)?".":""} 👉 ${c}`; }); }
  const RP_DEMO=[["Ngọc Ánh","Mình đang tìm nguồn trà gừng mật ong túi lọc giá sỉ để bán online, ai có xưởng giới thiệu mình với ạ","trà gừng mật ong túi lọc"],
    ["Lê Minh Tâm","Cần tìm xưởng gia công ngũ cốc dinh dưỡng làm thương hiệu riêng, số lượng 500 hộp, ai nhận báo giá giúp mình","ngũ cốc dinh dưỡng"],
    ["Shop Mẹ Sóc","Có ai biết chỗ lấy sỉ trà hoa đậu biếc với cà phê rang xay không ạ, mình mới mở shop online","trà hoa đậu biếc"],
    ["Hoàng Yến","Xin nguồn bột cacao, bột matcha giá sỉ cho quán nhỏ, ship về Đà Nẵng","bột matcha"],
    ["Trần Bảo Ngọc","Mọi người ơi tìm nhà cung cấp trà túi lọc thảo mộc để làm quà tặng doanh nghiệp, cần hóa đơn đỏ","trà túi lọc thảo mộc"]];
  const RP_OPEN=["Chào bạn, bên mình là xưởng sản xuất {p}, có giá sỉ cho shop mới","Bạn tham khảo {p} bên mình nhé, hàng làm trực tiếp tại nhà máy","Xưởng mình có {p}, nhận in nhãn riêng nếu bạn muốn làm thương hiệu"],
        RP_TAIL=["gửi mẫu thử được nha","mình gửi bạn catalog và bảng giá nhé","bạn cần số lượng bao nhiêu để mình báo giá"];
  const rpContact=()=>S.rp.settings.reply_contact||S.settings.bump_contact||"";
  const rpQuota=aid=>{ const f=aid===12?0.5:1, lim=Math.floor(+S.rp.settings.replies_per_nick_day*f); const d=today(); const mine=S.rp.items.filter(x=>x.account_id===aid&&((x.sent_at||"").slice(0,10)===d||(x.status==="approved"&&(x.scheduled_for||"").slice(0,10)===d)));
    const used=mine.length, sl=Math.min(lim,Math.floor(+S.fd.settings.feed_seller_per_nick_day*f)), su=mine.filter(x=>x.kind==="seller").length;
    return {limit:lim,used,left:Math.max(0,lim-used),seller_limit:sl,seller_used:su,seller_left:Math.max(0,Math.min(sl-su,lim-used))}; };
  const FD_SELL=[["Shop Mẹ Sóc","Tài khoản quảng cáo của shop em bị hạn chế hoài, ai có kinh nghiệm cho em hỏi xử lý sao ạ? Shop bán đồ ăn healthy","tai khoan quang cao",82,"Chúc shop sớm mở lại tài khoản nha. Bên mình là xưởng trà túi lọc, ngũ cốc, shop bán đồ healthy muốn thêm mặt hàng thì mình gửi catalog nhé"],
    ["Tuấn Shop","Mọi người chạy ads tiktok shop ngân sách bao nhiêu thì ra đơn đều vậy?","chay ads",74,"Mình bên xưởng trà và ngũ cốc, nhiều shop TikTok đang lấy về bán kèm, bạn muốn thêm mặt hàng thì mình gửi mẫu thử"],
    ["Lan Livestream","Tối nào em cũng livestream bán hàng mà ít đơn quá, có ai chia sẻ kinh nghiệm không ạ?","livestream",72,"Chúc phiên live của shop đông khách. Bên mình sản xuất trà túi lọc, ngũ cốc, shop muốn thêm hàng lên live thì mình gửi mẫu thử"]];
  const FD_IMG=["tra-gung-mat-ong-03.jpg","ngu-coc-hop-12.jpg","tra-hoa-dau-biec-07.jpg","xuong-dong-goi-02.jpg"];
  const fdAdd=(aid,gid,nb,ns)=>{ const g=S.groups.find(x=>x.id===gid)||S.groups[0], nick=S.accounts.find(a=>a.id===aid); let k=0; const n0=rpAdd(aid,gid,nb);
    (n0?S.rp.items.slice(-n0):[]).forEach((x,i)=>Object.assign(x,{kind:"buyer",origin:"feed",score:78+i*4,reason:"Đang hỏi nguồn hàng hợp ngành",image:"D:\\AnhSanPham\\"+FD_IMG[(x.id+i)%FD_IMG.length]}));
    for(const [who,txt,w,sc,rep] of FD_SELL){ if(k>=ns) break; if(S.rp.items.some(x=>x.kind==="seller"&&x.author===who)) continue;
      S.rp.items.push({id:id(),account_id:aid,group_id:g.id,group_name:g.name,nick:nick.name,author:who,author_url:"",post_url:`https://facebook.com/groups/${g.id}/posts/${(who.length*733+g.id)%100000}`,post_text:txt,reply:rep+". 👉 "+rpContact(),source:"claude",status:"draft",created_at:now(),kind:"seller",origin:"feed",score:sc,reason:`Người bán online đang hỏi (“${w}”)`,image:null}); k++; }
    S.fd.scans.push({account_id:aid,created_at:now(),read:20+Math.floor(Math.random()*9),buyers:n0,sellers:k}); return n0+k; };
  const fdView=()=>({settings:{...S.fd.settings},no_pitch:[],recent:[],nicks:S.accounts.filter(a=>a.enabled&&a.login_status==="ok").map(a=>{ const sc=S.fd.scans.filter(x=>x.account_id===a.id&&x.created_at.slice(0,10)===today()), q=rpQuota(a.id), n=a.id===12?1:+S.fd.settings.feed_scans_day;
    const pend=S.rp.items.filter(x=>x.account_id===a.id&&["draft","approved"].includes(x.status)).length;
    const why=S.fd.settings.feed_enabled==="0"?"Sếp đang tắt lướt bảng tin nhóm":pend>=q.limit?`Đã có ${pend} câu chờ duyệt / chờ gửi, đủ cho ${q.limit} câu/ngày của nick, chưa cần lướt thêm`:sc.length>=n?`Đã lướt đủ ${n} lượt hôm nay theo luật của nick`:`Lượt ${sc.length+1}/${n} khoảng ${sc.length?"3 giờ nữa":"đầu giờ làm"}`;
    return {id:a.id,name:a.name,plan:{scans:n,done:sc.length,why},scans:sc.length,read:sc.reduce((s,x)=>s+x.read,0),buyers:sc.reduce((s,x)=>s+x.buyers,0),sellers:sc.reduce((s,x)=>s+x.sellers,0),...q}; })});
  const rpAdd=(aid,gid,n)=>{ const g=S.groups.find(x=>x.id===gid)||S.groups[0], nick=S.accounts.find(a=>a.id===aid); let k=0;
    for(const [who,txt,pr] of RP_DEMO){ if(k>=n) break; const url=`https://facebook.com/groups/${g.id}/posts/${(who.length*977+g.id)%100000}`; if(S.rp.items.some(x=>x.post_url===url)) continue;
      const line=RP_OPEN[(k+g.id)%3].replace("{p}",pr)+", "+RP_TAIL[(k+aid)%3]; S.rp.items.push({id:id(),account_id:aid,group_id:g.id,group_name:g.name,nick:nick.name,author:who,author_url:"",post_url:url,post_text:txt,reply:line+". 👉 "+rpContact(),source:k%2?"claude":"bao",status:"draft",created_at:now()}); k++; } return k; };
  const rpSlot=aid=>{ if(!rpQuota(aid).left) return null; const last=S.rp.items.filter(x=>x.account_id===aid&&["approved","sent"].includes(x.status)).map(x=>x.sent_at||x.scheduled_for).filter(t=>t&&t.slice(0,10)===today()).sort().pop();
    let t=new Date(Date.now()+120000); if(last){ const l=new Date(last.replace(" ","T")); l.setMinutes(l.getMinutes()+45+Math.floor(Math.random()*45)); if(l>t) t=l; } if(t.getHours()>=22) return null; const p=n=>String(n).padStart(2,"0"); return `${t.getFullYear()}-${p(t.getMonth()+1)}-${p(t.getDate())} ${p(t.getHours())}:${p(t.getMinutes())}`; };
  function demoRp(method,P,qs,body){ let m; const q=new URLSearchParams(qs||"");
    if(P==="/feed") return fdView();
    if(P==="/feed/run"){ const nk=S.accounts.filter(a=>a.enabled&&a.login_status==="ok"); if(!nk.length) throw new Error("Chưa có nick nào đăng nhập và đang làm việc để lướt bảng tin nhóm");
      S.status.bao={state:"working",text:"Đọc bảng tin nhóm tìm người hỏi mua, người bán online"};
      setTimeout(()=>{ nk.forEach((a,i)=>{ const n=fdAdd(a.id,(S.groups[i%S.groups.length]||S.groups[0]).id,1,1); log("bao","Lướt bảng tin nhóm",`Nick ${a.name} lướt bảng tin nhóm, đọc ${S.fd.scans.slice(-1)[0].read} bài: ${n} bài đáng bình luận. Sếp duyệt ở trang Trả lời khách.`); }); S.status.bao={state:"idle",text:"Chờ sếp duyệt bình luận"}; },3000);
      return {queued:nk.map(a=>a.name),skipped:[]}; }
    if(P==="/feed-settings"){ if(body.feed_per_group_day&&(+body.feed_per_group_day<1||+body.feed_per_group_day>3)) throw new Error("Mỗi nhóm 1–3 bình luận/ngày để nhóm không coi là spam"); if(body.reply_gap_min&&(+body.reply_gap_min<30||+body.reply_gap_min>240)) throw new Error("Giãn cách 30–240 phút giữa 2 bình luận của một nick"); if(body.feed_seller_per_nick_day&&+body.feed_seller_per_nick_day>3) throw new Error("Chào người bán tối đa 3 câu/nick/ngày để không bị báo cáo spam"); Object.assign(S.fd.settings,body); return fdView(); }
    if(!S.rp.seeded){ S.rp.seeded=1; const nk=S.accounts.filter(a=>a.enabled&&a.login_status==="ok"); if(nk[0]&&S.groups[0]){ rpAdd(nk[0].id,S.groups[0].id,3); fdAdd(nk[0].id,(S.groups[1]||S.groups[0]).id,1,2); }
      if(nk[1]&&S.groups[2]) fdAdd(nk[1].id,S.groups[2].id,1,1);
      const x=S.rp.items[2]; if(x){ x.status="sent"; x.sent_at=now(); }
      S.rp.samples=[["Chào bạn, bên mình là xưởng trà gừng túi lọc, có giá sỉ cho shop mới, gửi mẫu thử được nha","claude",null],["Bạn cần bao nhiêu hộp ngũ cốc để mình báo giá gia công nhãn riêng nhé","claude",null],["Xưởng mình có trà hoa đậu biếc, giao toàn quốc, mình gửi catalog nhé","bao",8]].map((s,i)=>({id:i+1,text:s[0],source:s[1],score:s[2],created_at:now()})); }
    if(P==="/replies"&&method==="GET"){ const st=q.get("status")||""; const ord={draft:0,failed:1};
      const items=S.rp.items.filter(x=>st?x.status===st:["draft","approved","failed"].includes(x.status)).sort((a,b)=>(ord[a.status]??2)-(ord[b.status]??2)||b.id-a.id);
      const all=S.rp.items, nicks=S.accounts.filter(a=>a.enabled&&a.login_status==="ok").map(a=>({id:a.id,name:a.name,...rpQuota(a.id)}));
      const n=S.rp.samples.filter(x=>x.source==="claude").length, gr=S.rp.samples.filter(x=>x.source==="bao");
      return {items,nicks,contact:rpContact(),samples:S.rp.samples.slice().reverse(),settings:{...S.rp.settings},
        stats:{draft:all.filter(x=>x.status==="draft").length,approved:all.filter(x=>x.status==="approved").length,sent:all.filter(x=>x.status==="sent").length,today:all.filter(x=>(x.sent_at||"").slice(0,10)===today()).length},
        skill:{level:0,name:"Học việc",master:false,samples:n,graded:gr.length,pass_rate:gr.length?Math.round(gr.filter(x=>x.score>=8).length*100/gr.length):0,avg:null,next:{name:"Thạo việc",samples:20,pass_rate:60,graded:10},calls:S.rp.calls||1,saved:0}}; }
    if(P==="/replies/scan"){ const nk=S.accounts.filter(a=>a.enabled&&a.login_status==="ok"&&(!body.account_id||a.id===body.account_id)); if(!nk.length) throw new Error("Chưa có nick nào đăng nhập và đang làm việc để mở nhóm");
      const a=nk[0], gs=S.groups.slice(0,+S.rp.settings.replies_groups_per_run); S.status.bao={state:"working",text:"Tìm người đang hỏi mua trong nhóm sôi nổi"};
      setTimeout(()=>{ const n=gs.reduce((s,g)=>s+rpAdd(a.id,g.id,2),0); S.rp.calls=(S.rp.calls||1)+1; S.status.bao={state:"idle",text:"Chờ sếp duyệt câu trả lời khách"};
        log("bao","Tìm bài hỏi mua",`Bảo đọc ${gs.length} nhóm sôi nổi trên nick ${a.name}: ${n} bài đang hỏi mua hợp ngành, đã viết sẵn câu trả lời. Sếp duyệt ở trang Trả lời khách, duyệt xong nick gửi trong giờ làm.`); },3000);
      return {account:a.name,account_id:a.id}; }
    const approve=(r,txt)=>{ const t=(txt!=null?txt:r.reply||"").trim(); if(!t) throw new Error("Câu trả lời đang trống");
      if(/chữa|trị bệnh|giảm cân|tiểu đường|thay thuốc/i.test(t)) throw new Error("Câu trả lời phạm luật Facebook: hứa công dụng chữa bệnh, giảm cân (thực phẩm không được quảng cáo như thuốc)");
      if(txt!=null&&txt.trim()!==r.reply) S.rp.samples.push({id:id(),text:t.replace(/\s*👉.*$/,""),source:"claude",score:null,created_at:now()});
      const sl=r.kind==="seller"&&!rpQuota(r.account_id).seller_left?null:rpSlot(r.account_id); const tm=new Date(Date.now()+86400000); const p=n=>String(n).padStart(2,"0");
      r.reply=t; r.status="approved"; r.error=null; r.scheduled_for=sl||`${tm.getFullYear()}-${p(tm.getMonth()+1)}-${p(tm.getDate())} 09:${p(10+Math.floor(Math.random()*40))}`; return {id:r.id,status:"approved",scheduled_for:sl,later:!sl}; };
    if((m=P.match(/^\/replies\/(\d+)$/))){ const r=S.rp.items.find(x=>x.id==m[1]); if(!r) throw new Error("Không tìm thấy câu trả lời");
      if(body.action==="approve") return approve(r,body.reply);
      if(body.action==="skip"||body.action==="junk"){ r.status="skipped"; if(body.action==="junk") log("mai","Ghi nhớ data rác",`Sếp loại ${r.author}: không hợp tệp khách`); return {id:r.id,status:"skipped"}; } }
    if(P==="/replies/approve-all"){ let n=0,later=0; S.rp.items.filter(x=>x.status==="draft").forEach(r=>{ try{ const x=approve(r,null); n++; if(x.later) later++; }catch(e){} }); return {approved:n,later}; }
    if(P==="/replies/relearn"){ log("bao","Học lại","Sếp cho Bảo học lại cách viết câu trả lời khách: gọi Claude và chấm điểm lại từ đầu"); return {}; }
    if(P==="/replies-settings"){ if(body.replies_per_nick_day&&+body.replies_per_nick_day>10) throw new Error("Mỗi nick tối đa 10 câu/ngày để không bị coi là spam"); Object.assign(S.rp.settings,body); return demoRp("GET","/replies","",{}); }
    throw new Error("Không hỗ trợ trong bản xem trước"); }
  function demoFr(method,P,qs,body){ let m; const q=new URLSearchParams(qs||"");
    if(!S.fr.seeded){ S.fr.seeded=1; frAdd(11,3,5); frAdd(11,1,3); frAdd(12,4,3); S.fr.items.slice(0,2).forEach((x,i)=>{ x.status=i?"opened":"sent"; if(!i) x.sent_at=now(); }); }
    if(P==="/post-target"){ if(method==="PUT"){ if(body.mode) S.tg.mode=body.mode; if(body.include!=null) S.tg.include=tgWords(body.include); if(body.exclude!=null) S.tg.exclude=tgWords(body.exclude); log("tuan","Nhận chỉ đạo nơi đăng",`${({all:"Mọi nhóm đủ điều kiện",prefer:"Ưu tiên nhóm chỉ định",only:"Chỉ nhóm chỉ định"})[S.tg.mode]} · từ khóa: ${S.tg.include.join(", ")||"—"} · tránh: ${S.tg.exclude.join(", ")||"—"}`); } return tgOverview(); }
    if(P==="/post-target/preview") return tgPreview({mode:body.mode||S.tg.mode,include:body.include!=null?tgWords(body.include):S.tg.include,exclude:body.exclude!=null?tgWords(body.exclude):S.tg.exclude});
    if((m=P.match(/^\/groups\/(\d+)\/focus$/))){ const g=S.groups.find(x=>x.id==m[1]); g.focus=body.focus?1:0; log("tuan",g.focus?"Tập trung đăng":"Bỏ tập trung đăng",g.name); return {id:g.id,focus:g.focus}; }
    if(P==="/friends"&&method==="GET"){ const aid=+q.get("account_id")||null, st=q.get("status")||"";
      const nicks=S.accounts.filter(a=>a.enabled&&a.login_status==="ok").map(a=>{ const it=S.fr.items.filter(x=>x.account_id===a.id); return {id:a.id,name:a.name,sale:(S.sales.find(s=>s.id===a.sale_id)||{}).name,...frQuota(a.id),wait:it.filter(x=>x.status==="suggested").length,opened:it.filter(x=>x.status==="opened").length,sent_all:it.filter(x=>["sent","accepted"].includes(x.status)).length,accepted:it.filter(x=>x.status==="accepted").length}; });
      const ord={opened:0,suggested:1}; const items=S.fr.items.filter(x=>(!aid||x.account_id===aid)&&(st?x.status===st:["suggested","opened"].includes(x.status))).sort((a,b)=>(ord[a.status]??2)-(ord[b.status]??2)||b.score-a.score);
      const all=S.fr.items, sent=all.filter(x=>["sent","accepted"].includes(x.status)).length, ok=all.filter(x=>x.status==="accepted").length;
      return {nicks,groups:frGroups(aid).slice(0,15),items,stats:{found:all.length,sent,accepted:ok,today:all.filter(x=>x.sent_at&&x.sent_at>=today()).length,accept_rate:sent?Math.round(ok*100/sent):null},settings:{...S.fr.settings}}; }
    if(P==="/friends/scan"){ const nicks=S.accounts.filter(a=>a.enabled&&a.login_status==="ok"&&(!body.account_id||a.id===body.account_id)); if(!nicks.length) throw new Error("Chưa có nick nào đăng nhập và đang làm việc để mở nhóm");
      const a=nicks.sort((x,y)=>frQuota(y.id).left-frQuota(x.id).left)[0]; const gs=body.group_ids&&body.group_ids.length?body.group_ids:frGroups(a.id).filter(g=>g.target!=="exclude").slice(0,+S.fr.settings.friends_groups_per_run).map(g=>g.id);
      S.status.tuan={state:"working",text:"Tìm người đáng kết bạn trong nhóm sôi nổi"};
      setTimeout(()=>{ const per=gs.map(g=>[S.groups.find(x=>x.id===g).name,frAdd(a.id,g,4)]); const n=per.reduce((s,x)=>s+x[1],0); S.status.tuan={state:"idle",text:"Xong lượt tìm người kết bạn"}; const qq=frQuota(a.id);
        log("tuan","Gợi ý kết bạn",`Tuấn đọc ${gs.length} nhóm trên nick ${a.name}: thêm ${n} người nên kết bạn (${per.map(x=>`${x[0].slice(0,40)}: ${x[1]}`).join("; ")}). Hôm nay nick còn gửi được ${qq.left}/${qq.limit} lời mời; sale mở hồ sơ và tự bấm Thêm bạn bè.`); },3000);
      return {account:a.name,account_id:a.id}; }
    if(P==="/friends/open"){ const qq=frQuota(body.account_id); if(!qq.left) throw new Error(`Nick đã gửi đủ ${qq.limit} lời mời hôm nay. Mai gửi tiếp để không bị Facebook chặn tính năng kết bạn`);
      const rows=S.fr.items.filter(x=>x.account_id===body.account_id&&x.status==="suggested").sort((a,b)=>b.score-a.score).slice(0,Math.min(body.n||5,qq.left,10)); if(!rows.length) throw new Error("Chưa có ai trong danh sách chờ gửi. Bấm “Tìm người để kết bạn” trước");
      rows.forEach(r=>{ r.status="opened"; r.opened_at=now(); }); log("tuan","Mở hồ sơ để kết bạn",`Nick ${S.accounts.find(a=>a.id===body.account_id).name}: ${rows.map(r=>r.name).join(", ")}`); return {opened:rows.map(r=>r.id),names:rows.map(r=>r.name),quota:qq}; }
    if((m=P.match(/^\/friends\/(\d+)$/))){ const r=S.fr.items.find(x=>x.id==m[1]); const st=body.status==="junk"?"skipped":body.status;
      if(st==="sent"||st==="accepted") r.sent_at=r.sent_at||now(); if(st==="suggested") r.sent_at=null; r.status=st; if(body.status==="junk") log("mai","Ghi nhớ data rác",`Sếp loại ${r.name}: không hợp tệp khách`);
      const qq=frQuota(r.account_id); return {id:r.id,status:st,quota:qq,over:["sent","accepted"].includes(st)&&qq.used>qq.limit}; }
    if(P==="/friends-settings"){ for(const [k,v] of Object.entries(body)){ if(k==="friends_time"&&!/^\d{1,2}:\d{2}$/.test(v)) throw new Error("Giờ có dạng HH:MM"); S.fr.settings[k]=String(v); } return demoFr("GET","/friends","",{}); }
    throw new Error("Không hỗ trợ trong bản xem trước"); }
