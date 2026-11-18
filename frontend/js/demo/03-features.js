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
