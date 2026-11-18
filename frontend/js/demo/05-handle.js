  async function handle(method, path, body){
    const [p, qs] = path.split("?"); const P=p.replace(/^\/api/,""); let m;
    if(P==="/post-care"&&method==="GET"){ const sm=S.baoSamples||(S.baoSamples=[["Mẻ trà gừng mật ong vừa đóng thùng sáng nay, ship toàn quốc","claude",null],["Shop nào cần bột ngũ cốc giá gốc, nhận in nhãn riêng","claude",null],["Kho vừa nhập thêm trà hoa đậu biếc, giao trong ngày","bao",9],["Ảnh thật bột diếp cá tại xưởng, đơn từ 1 thùng vẫn nhận","bao",8],["Xưởng còn sẵn trà gừng, giá tốt lắm","bao",6]].map((x,i)=>({id:i+1,text:x[0],source:x[1],score:x[2],created_at:now()})));
      const lv=S.baoLevel??2; return {today:{done:3,waiting:2,failed:0,skipped:0},alive:S.posts.filter(p=>p.status==="posted").length,contact:S.settings.bump_contact,mode:S.settings.bump_text_mode,
        skill:{level:lv,name:["Học việc","Thạo việc","Giỏi","Master"][lv],master:lv===3,samples:lv?64:0,graded:lv?38:0,pass_rate:lv?84:0,avg:lv?8.4:null,next:lv<3?{name:["Thạo việc","Giỏi","Master"][lv],samples:[20,50,100][lv],pass_rate:[60,80,90][lv],graded:[10,20,40][lv]}:null,calls:lv?14:0,saved:0},samples:sm}; }
    if(P==="/post-care/relearn"){ S.baoLevel=0; log("bao","Học lại","Sếp cho Bảo học lại cách viết câu bình luận: gọi Claude và chấm điểm lại từ đầu"); return {}; }
    if(P==="/bump/preview-text") return {texts:demoBumpLines(+(new URLSearchParams(qs||"").get("n"))||3),mode:S.settings.bump_text_mode||"ai",contact:S.settings.bump_contact||"",ai:false};
    if(P.startsWith("/post-target")||P.startsWith("/friends")||/^\/groups\/\d+\/focus$/.test(P)) return demoFr(method,P,qs,body||{});
    if(P.startsWith("/comments")) return demoCm(method,P,qs,body||{});
    if(P.startsWith("/page-inbox")) return demoIb(method,P,qs,body||{});
    if(P.startsWith("/nick-health")) return demoNh(method,P,qs,body||{});
    if(P.startsWith("/replies")||P.startsWith("/feed")) return demoRp(method,P,qs,body||{});
      if(P.startsWith("/agents/")&&(method==="PUT"||method==="DELETE")){ S.prof=S.prof||{}; const aid=P.split("/")[2], cur=S.prof[aid]=S.prof[aid]||{};
       if(method==="DELETE"){ delete S.prof[aid]; return {id:aid}; }
       if(body.name!=null){ const n=String(body.name).trim(); if(!n||n.length>20) throw new Error("Tên từ 1 đến 20 ký tự"); cur.name=n; }
       if(body.face) cur.face=body.face; return {id:aid,...cur}; }
     if(P==="/focus"||P==="/focus/run"||P==="/focus/settings"||P.startsWith("/focus/resume/")){ S.fc=S.fc||{enabled:true,paused:{}};
        if(P==="/focus/settings") S.fc.enabled=!!body.enabled; if(P.startsWith("/focus/resume/")) delete S.fc.paused[P.split("/").pop()];
        if(P==="/focus/run") S.fc.paused.pages=new Date(Date.now()+30*864e5).toISOString().slice(0,10);
        const ch=[{key:"comment",label:"Bình luận dưới bài mình đăng",verdict:"good",text:"Ra 3 đơn từ 21 SĐT: dồn thêm sức"},{key:"demand",label:"Người hỏi nguồn trong nhóm (Mai đọc)",verdict:"good",text:"Ra 2 đơn từ 9 SĐT: dồn thêm sức"},{key:"pages",label:"Trang, shop livestream (Mai tìm)",verdict:"weak",text:"18 SĐT, sếp đã gọi 11, chưa có đơn nào"},{key:"ads",label:"Trang chạy quảng cáo (Mai quét)",verdict:"call",text:"Có 8 SĐT nhưng sếp mới gọi 2/5: cần gọi thêm mới biết kênh này ra đơn không"}].map(c=>({...c,paused_until:S.fc.paused[c.key]||null}));
        return {days:14,min_phones:8,min_called:5,channels:ch,enabled:S.fc.enabled,mode:"auto",last:P==="/focus/run"?new Date().toISOString().slice(0,10):"",proposed:[],
          plan:S.fc.paused.pages?[{op:"boost",key:"demand",label:"Người hỏi nguồn trong nhóm (Mai đọc)"}]:[{op:"pause",key:"pages",label:"Trang, shop livestream (Mai tìm)"},{op:"boost",key:"demand",label:"Người hỏi nguồn trong nhóm (Mai đọc)"}],
          done:P==="/focus/run"?["Tạm dừng “Trang, shop livestream (Mai tìm)” 30 ngày (18 SĐT, sếp đã gọi 11, chưa có đơn nào)","Dồn sức cho “Người hỏi nguồn trong nhóm (Mai đọc)”"]:[]}; }
    if(method==="GET"){
      if(P==="/health"){ const z=S.settings.app_tz||"Asia/Ho_Chi_Minh"; return {ok:true,ai_live:false,model:"bản xem trước",time:{tz:z,label:(TZ_LIST.find(x=>x.id===z)||TZ_LIST[0]).label,now:tzNow(z),pc_now:now(),choices:TZ_LIST}}; }
      if(P==="/agents"){ const prog=id=>{ const x=S.xp[id]||0, l=lvl(x); return {xp:x,level:l,level_xp:lxp(l),next_xp:lxp(l+1)}; };
        const rec=id=>S.activity.filter(x=>x.agent_id===id).slice(0,2);
        const learnSt=id=>{ const st=S.status[id]; if(st&&st.state!=="idle") return st; const t=DEMO_LEARN[id]||["Ôn lại: cách giữ nick an toàn","Ôn cách trả lời bình luận xin số điện thoại"]; return {state:"learning",text:t[Math.floor(Date.now()/40000)%t.length]}; };
        S.prof=S.prof||{}; const pf=a=>({default_name:a.default_name||a.name,...a,...(S.prof[a.id]||{})});
        return AGENT_DEFS.map(a=>pf({...a,default_name:a.name,kind:"core",level:lvl(S.xp[a.id]||0),progress:prog(a.id),recent:rec(a.id),learned_today:(a.id.length%3)+1,status:learnSt(a.id),tasks:S.tasks.filter(t=>t.agent_id===a.id&&t.status!=="done")}))
.map(x=>({...x,...(S.prof[x.id]||{})}))
          .concat(saleAgents().map(a=>({...a,level:lvl(S.xp[a.id]||0),progress:prog(a.id),recent:rec(a.id),learned_today:1,status:learnSt(a.id),tasks:[],...(S.prof[a.id]||{})}))); }
      if(P==="/sales") return S.sales.map(saleOut);
      if(P==="/dashboard") return {stats:stats(),activity:S.activity.slice(0,30),meeting_running:S.running};
      if(P==="/products") return S.products.slice().sort((a,b)=>(b.is_general||0)-(a.is_general||0)||(b.hot||0)-(a.hot||0)||a.id-b.id).map(p=>({...p,folder:demoFolder(p)})); if(P==="/groups") return S.groups.map(g=>({...g,ready:ready(g),joins:g.joins||{},today:gfToday(g)}));
      if(P==="/posts/posted") return demoPosted(qs);
      if(P==="/fb-policy"){ const F=S.fbp; return {...F,rules:[...F.rules,...F.custom],nicks:S.accounts.filter(a=>a.enabled!==0).slice(0,6).map((a,i)=>{ const sale=S.sales.find(x=>x.id===a.sale_id)||{}; const f=i===0?0.5:1;
          return {id:a.id,name:a.name,sale_name:sale.name,factor:f,rest_until:F.restNick===a.id?F.restUntil:null,limits:{posts:Math.max(1,Math.floor(6*f)),bumps:Math.max(1,Math.floor(6*f)),joins:Math.floor(2*f),gap:Math.round(30/f)},used:{posts:[2,3,1,0,2,1][i%6],bumps:[3,1,0,2,4,0][i%6],joins:[1,0,0,1,2,0][i%6]}}; }),flagged:S.posts.filter(p=>p.policy_note&&p.status!=="posted").length}; }
      if(P==="/website") return {...S.ws,products:S.products.map(p=>{ const m=(p.name||"").match(/combo|\bset\b|bộ quà|các loại|nhiều loại|tổng hợp|(gồm|bộ|hộp)\s*\d+\s*(loại|vị|gói)|\d+\s*(mã|sản phẩm)\b/i); const why=p.is_general?"Ảnh tổng hợp nhà máy, không phải một sản phẩm":m?`Tên có “${m[0]}”: giống combo / nhóm nhiều sản phẩm`:""; const auto=p.site_show==null; return {id:p.id,name:p.name,category:p.category,on:auto?!why:!!p.site_show,why,auto,general:!!p.is_general}; }),posts:S.ws.posts.map(p=>({...p})),stats:{published:S.ws.posts.filter(p=>p.status==="published").length,review:S.ws.posts.filter(p=>p.status==="review").length,planned:S.ws.keywords.filter(k=>k.status==="planned").length,avg_seo:S.ws.posts.length?Math.round(S.ws.posts.reduce((s,p)=>s+p.seo_score,0)/S.ws.posts.length):0},pages:14+S.ws.posts.filter(p=>p.status==="published").length,built:true};
      if((m=P.match(/^\/website\/posts\/(\d+)$/))) return S.ws.posts.find(p=>p.id==m[1]);
      if(P==="/posts/reset"){ const c={approved:0,scheduled:0,failed:0,draft:0}, g={approved:0,scheduled:0,failed:0,draft:0};
        S.posts.forEach(p=>{ if(p.status in c){ c[p.status]++; if(p.target_type==="group") g[p.status]++; } });
        return {counts:c,group_counts:g,scheduled_today:S.posts.filter(p=>p.status==="scheduled"&&(p.scheduled_for||"").startsWith(now().slice(0,10))).length,posting:S.posts.filter(p=>p.status==="posting").length}; }
      if(P==="/posts") return S.posts.map(p=>{ const pr=S.products.find(x=>x.is_general)||S.products.find(x=>x.id===p.product_id); const shared=(S.settings.bump_folder||"").trim()?10:0;
        return {...p,img_required:S.settings.require_images!=="0",img_count:pr?(demoFolder(pr).count||shared):shared}; }); if(P==="/leads") return S.leads; if(P==="/tasks") return S.tasks; if(P==="/settings") return {...S.settings,tg_token:S.settings.tg_token?"••••••":"",models:["claude-haiku-5-5","claude-sonnet-5-5","claude-opus-5-5"]};
      if(P==="/company") return demoCompany();
      if(P==="/errors") return demoErrors(qs);
      if(P==="/ceo") return {...demoCeo(),group_keywords:S.gf.today};
      if(P==="/group-finder") return demoGF();
      if(P==="/ceo/chat") return demoChat();
      if(P==="/reset"){ const c=(n,l)=>n?[{label:l,count:n}]:[]; return {delete:[...c(S.posts.length,"bài đăng"),...c(S.leads.length,"khách hàng"),...c(S.meetings.length,"cuộc họp"),...c(S.activity.length,"nhật ký hoạt động"),...c(S.lessons.length,"bài học của agent"),...c(S.tasks.length,"việc được giao")],keep:{sales:S.sales.filter(x=>!x.is_sample).length,products:0,groups:0},samples:{products:S.products.length,groups:S.groups.length,sales:S.sales.filter(x=>x.is_sample).length},shots:0}; }
      if(P==="/sample-data") return {sales:S.sales.filter(x=>x.is_sample).length,leads:S.leads.filter(x=>x.is_sample).length,groups:S.groups.length,products:S.products.length};
      if(P==="/learning") return demoLearning();
      if(P==="/content-style") return demoStyle();
      if(P==="/prospects") return demoPR(qs);
      if(P==="/my-groups") return demoMG();
      if(P==="/post-template") return demoTpl();
      if(P==="/samples") return demoSamples();
      if(P==="/ceo-review") return demoCR();
      if(P==="/knowledge"){ const u=new URLSearchParams(qs||""); return demoKB(u.get("agent")||"",u.get("q")||""); }
      if(P==="/kpi") return demoKpi();
      if(P==="/funnel"){ const ch=[{key:"comment",label:"Bình luận dưới bài mình đăng",leads:46,phones:21,called:17,won:3,lost:9,lost_noreason:1,revenue:7400000},{key:"demand",label:"Người hỏi nguồn trong nhóm (Mai đọc)",leads:14,phones:9,called:8,won:2,lost:4,lost_noreason:0,revenue:5200000},{key:"pages",label:"Trang, shop livestream (Mai tìm)",leads:18,phones:18,called:11,won:0,lost:8,lost_noreason:0,revenue:0}];
        return {days:30,channels:ch,total:{leads:78,phones:48,called:36,won:5,lost:21,lost_noreason:1,revenue:12600000},ai_vnd:186000,per_phone:3875,per_order:37200,
          reasons:[{key:"wrong_fit",label:"Sai tệp (không bán online, chỉ mua lẻ)",n:8,by_channel:{pages:6,comment:2}},{key:"moq",label:"Chê số lượng nhập tối thiểu",n:6,by_channel:{comment:4,demand:2}},{key:"no_answer",label:"Không nghe máy / sai số",n:4,by_channel:{pages:2,comment:2}},{key:"has_supplier",label:"Đã có nguồn hàng",n:2,by_channel:{demand:2}}],
          channel_names:{comment:"Bình luận dưới bài mình đăng",demand:"Người hỏi nguồn trong nhóm (Mai đọc)",pages:"Trang, shop livestream (Mai tìm)"}}; }
      if(P==="/telegram") return demoTg();
      if(P==="/posts/recent-posted") return S.posts.filter(p=>p.status==="posted").map(p=>({id:p.id,title:p.title,posted_at:p.posted_at,group_name:p.group_name,target_type:p.target_type}));
      if(P==="/bump/folder"){ const f=S.settings.bump_folder; return f?{path:f,exists:true,count:23,root_count:5,products:[{id:1,name:"Trà gừng mật ong túi lọc",count:8},{id:3,name:"Bột ngũ cốc dinh dưỡng 25 loại hạt",count:6},{id:4,name:"Bột cần tây sấy lạnh",count:4}],samples:[]}:{path:"",exists:false,count:0,products:[],samples:[]}; }
      if(P==="/scan/now"){ const sid=S.sales.find(x=>x.login_status==="ok"); if(!sid) return {posts:0}; const aid=`sale-${sid.id}`; S.status[aid]={state:"working",text:"Đang đọc bình luận 3 bài để tìm khách"};
        setTimeout(()=>{ S.status[aid]={state:"idle",text:"Quét xong: 1 khách mới, 1 SĐT"}; S.leads.unshift({id:id(),name:"Đỗ Ngọc Ánh",contact:"0938 222 456",phone:"0938222456",origin:"comment",source:"Bình luận bài #3 · Cộng đồng bán hàng online toàn quốc",business_type:"",need:"Quan tâm trà đậu biếc, 0938222456",score:75,status:"new",escalated_at:now(),escalate_reason:"Khách đã để lại SĐT, cần người gọi/nhắn Zalo tư vấn",consult_note:"Chào chị, em gọi từ xưởng về trà hoa đậu biếc. Giá sỉ 35.000đ/hộp, lẻ gợi ý 60.000đ, nhập từ 50 hộp. Chị đang bán live hay sàn, dự kiến nhập bao nhiêu? Em gửi mẫu thử để chị quay video nhé.",created_at:now()}); S.kpiPhone=(S.kpiPhone||3)+1; log(aid,"Quét bình luận","Bài #3: 1 khách mới, 1 SĐT"); },5000); return {posts:3}; }
      if((m=P.match(/^\/leads\/(\d+)\/escalate$/))){ const l=S.leads.find(x=>x.id==m[1]); Object.assign(l,{escalated_at:now(),escalate_reason:"Sếp chọn tự tư vấn khách này",consult_note:"Chào anh/chị, em gọi từ xưởng. Hỏi kênh bán, số lượng dự kiến, đề nghị gửi mẫu thử."}); return {ok:true,telegram:!!S.tgChats}; }
      if(P==="/learning/run"){ S.learnRunning=true; [...AGENT_DEFS.map(a=>a.id),...S.sales.map(r=>`sale-${r.id}`)].forEach(a=>S.status[a]={state:"working",text:"Đang tự xem lại và rút kinh nghiệm"});
        setTimeout(()=>{ S.learnRunning=false; [...AGENT_DEFS.map(a=>a.id),...S.sales.map(r=>`sale-${r.id}`)].forEach(a=>S.status[a]={state:"idle",text:"Vừa học xong bài học hôm nay"});
          S.lessons.push({id:id(),agent_id:"lan",text:"Mở bài bằng câu hỏi về lợi nhuận của người bán giúp tăng bình luận.",evidence:"Góc lợi nhuận: 6 bình luận/bài so với mức chung 3,1",source:"ai",confidence:0.7,pinned:0});
          S.xp.lan+=15; S.xp.tuan+=5; log("khoa","Tự học","Cả đội rút ra 2 bài học mới, đặt mục tiêu cho ngày mai"); },6000); return {ok:true}; }
      if(P==="/lessons"){ const l={id:id(),agent_id:body.agent_id,text:body.text,evidence:"Sếp dạy",source:"boss",confidence:1,pinned:1}; S.lessons.push(l); log(body.agent_id,"Được sếp dạy",body.text); return l; }
      if((m=P.match(/^\/replies\/(\d+)\/sent$/))) return {ok:true};
      if(P==="/costs"){ const d=new Date(); const daily=[...Array(14)].map((_,i)=>{ const x=new Date(d-(13-i)*864e5); return {day:x.toISOString().slice(0,10),cost:0.09+((i*37)%11)/100}; });
        return {spent:0.38,budget:+S.settings.monthly_budget_usd||0,projected:3.9,state:"ok",batch_saved:0.27,live:false,pending_batches:0,daily,
          by_task:[{task:"posts",label:"Viết bài đăng",calls:96,tin:91200,tout:67300,cost:0.27,batched:84},{task:"replies",label:"Tin nhắn khách",calls:41,tin:45100,tout:8200,cost:0.0086},{task:"meeting",label:"Cuộc họp",calls:28,tin:39800,tout:5600,cost:0.0068}],
          fallback:{days:30,total:2,calls:165,by_task:[{task:"posts",label:"Viết bài đăng",n:2,calls:96,reasons:{"Claude viết quá dài nên bị cắt giữa chừng":2}}]}}; }
      if(P==="/meetings") return S.meetings; if(P==="/meetings/topics") return TOPICS;
      if((m=P.match(/^\/meetings\/(\d+)$/))){ const after=+(new URLSearchParams(qs).get("after")||0); const mt=S.meetings.find(x=>x.id==m[1]); return {...mt,messages:S.msgs.filter(x=>x.meeting_id==m[1]&&x.id>after)}; }
    }
    if(method==="POST"&&P==="/knowledge"){ if(!(body.topic||"").trim()) throw new Error("Nhập chủ đề"); if((body.content||"").trim().length<15) throw new Error("Nội dung kiến thức quá ngắn");
      S.kb.push({id:id(),agent_id:body.agent_id,topic:body.topic.trim(),question:body.question||"",content:body.content.trim(),source:"boss",kind:body.kind||"guide",uses:0,status:"active",created_at:now()}); log("minh","Sếp dạy kiến thức",`${KB_ROLES[body.agent_id]}: ${body.topic}`); return {ok:true,...demoKB()}; }
    if(method==="POST"&&P==="/knowledge/ask"){ const h=kbHit(body.question); if(h){ h.uses++; S.kbLog.memory++; return {answer:h.content,source:"memory",item_id:h.id}; }
      S.kb.push({id:id(),agent_id:"all",topic:body.question,question:body.question,content:"",source:"claude",kind:"guide",uses:0,status:"pending",created_at:now()}); return {answer:null,source:"none"}; }
    if(method==="POST"&&P==="/knowledge/study"){ setTimeout(()=>{ const t=[["lan","cách viết câu mở đầu giữ chân người đọc trong 2 dòng đầu","Mở đầu bằng con số hoặc câu hỏi trúng nỗi lo người bán (VD: 'Nhập 35k bán 60k, lãi 25k/hộp?'). Tránh mở đầu bằng lời chào dài."],["tuan","dấu hiệu nhóm tương tác thật và nhóm ảo","Nhóm thật: bài mới có bình luận hỏi đáp, thành viên mới đều mỗi tuần. Nhóm ảo: nhiều bài rao bán 0 bình luận, lượt thích đều nhau bất thường."]];
      t.forEach(([a,tp,c])=>S.kb.push({id:id(),agent_id:a,topic:tp,question:"",content:c,source:"study",kind:"guide",uses:0,status:"active",created_at:now()})); S.kbLog.study+=2; log("lan","Học kiến thức mới",t[0][1]); },2000); return {ok:true}; }
    if(method==="POST"){
      if(P==="/telegram/token"){ if(!/^\d{5,12}:[A-Za-z0-9_-]{30,}$/.test(body.token||"")) throw new Error("Token không đúng dạng. Token do @BotFather gửi có dạng 123456789:AAH…, copy đủ cả dãy, không thừa dấu cách"); S.settings.tg_token=body.token; log("minh","Kết nối Telegram","Đã lưu token bot @moctam_sales_bot"); return demoTg(); }
      if(P==="/telegram/pair"){ if(!S.settings.tg_token) throw new Error("Dán token bot Telegram và bấm Lưu trước"); S.pairCode=String(Math.floor(100000+Math.random()*899999)); setTimeout(()=>{ S.tgChats=1; S.pairCode=""; log("minh","Kết nối Telegram","Đã ghép nối với Sếp"); },8000); return demoTg(); }
      if(P==="/telegram/send"){ if(!S.tgChats) throw new Error("Chưa ghép nối Telegram. Tạo mã ghép nối và gửi mã đó cho bot"); return {ok:true}; }
      if(P==="/telegram/unlink"){ S.tgChats=0; S.pairCode=""; return demoTg(); }
      if(P==="/posts/generate"){ S.status.lan={state:"working",text:`Đang viết ${body.count} bài`}; await wait(1400); const r=genPosts(Math.min(body.count||3,10),body.product_id,body.target_type||"group",body.angle); S.status.lan={state:"idle",text:`Vừa viết xong ${r.length} bài`}; return r; }
      if(P==="/distribution/plan") return plan();
      if(P==="/meetings") return {id:startMeeting(body.topic)};
      if((m=P.match(/^\/meetings\/(\d+)\/say$/))){ S.msgs.push({id:id(),meeting_id:+m[1],agent_id:"boss",phase:"boss",content:body.text,created_at:now()}); (S.bossQ=S.bossQ||[]).push(body.text); return {ok:true}; }
      if((m=P.match(/^\/posts\/(\d+)\/posted$/))){ const po=S.posts.find(x=>x.id==m[1]); Object.assign(po,{status:"posted",posted_at:now(),posted_url:body.posted_url,poster:body.poster}); const g=S.groups.find(g=>g.id===po.group_id); if(g) g.last_posted_at=now(); log("tuan","Đã đăng",`Bài #${po.id} đã đăng`); return po; }
      if(P==="/sales"){ if(S.sales.length>=8) throw new Error("Văn phòng tối đa 8 nhân viên sale"); const samples=S.sales.filter(x=>x.is_sample); if(samples.length){ const ids=samples.map(x=>x.id); S.sales=S.sales.filter(x=>!x.is_sample);
          S.posts.forEach(p=>{ if(ids.includes(p.sale_id)&&p.status==="scheduled") Object.assign(p,{status:"approved",sale_id:null,sale_name:null,scheduled_for:null}); });
          log("minh","Dọn sale mẫu",`Đã cho ${samples.length} sale mẫu rời văn phòng`); }
        const r={id:id(),name:body.name,fb_name:body.fb_name,login_status:"not_logged_in",auto_post:1,last_error:null,is_sample:0}; S.sales.push(r); addNick(r.id,body.fb_name||"Nick 1"); log("minh","Tuyển sale",`${r.name} nhận quản lý nick ${body.fb_name||"Nick 1"} (thêm được tới 5 nick)`); return saleOut(r); }
      if(P==="/accounts"){ const r=S.sales.find(x=>x.id==body.sale_id); if(!r) throw new Error("Không tìm thấy nhân viên sale"); const a=addNick(r.id,body.name); log("minh","Thêm nick",`${r.name} nhận thêm nick ${a.name}. Bấm Mở Chrome để đăng nhập nick này`); return saleOut(r); }
      if((m=P.match(/^\/accounts\/(\d+)\/(open|check)$/))){ const a=S.accounts.find(x=>x.id==m[1]); if(!a) throw new Error("Không tìm thấy nick"); if(m[2]==="open"&&S.busy[a.sale_id]) throw new Error("Sale đang làm việc trên một nick, chờ xong ca hiện tại rồi mở");
        S.busy[a.sale_id]=m[2]; S.busyAcc[a.sale_id]=a.id; setTimeout(()=>{ delete S.busy[a.sale_id]; delete S.busyAcc[a.sale_id]; if(m[2]==="open"||a.login_status==="not_logged_in"){ a.login_status="ok"; a.last_error=null; } syncSale(a.sale_id); },m[2]==="open"?6000:2000); return {ok:true}; }
      if((m=P.match(/^\/sales\/(\d+)\/(open|check)$/))){ const r=S.sales.find(x=>x.id==m[1]); const a=nicksOf(r.id)[0]; if(!a) throw new Error("Sale này chưa có nick nào. Thêm nick trước"); S.busy[r.id]=m[2]; S.busyAcc[r.id]=a.id; setTimeout(()=>{ delete S.busy[r.id]; delete S.busyAcc[r.id]; a.login_status="ok"; a.last_error=null; syncSale(r.id); },m[2]==="open"?6000:2000); return {ok:true}; }
      if((m=P.match(/^\/posts\/(\d+)\/run$/))){ const po=S.posts.find(x=>x.id==m[1]); const na=S.accounts.find(x=>x.id==body.account_id)||nicksOf(body.sale_id)[0]; const r=na&&S.sales.find(x=>x.id===na.sale_id); if(!r) throw new Error("Chọn nick sale để đăng bài này");
        if(na.login_status!=="ok") throw new Error(`Nick ${na.name} chưa đăng nhập. Vào Nhân viên sale → Mở Chrome của nick để đăng nhập lại`);
        po.sale_id=r.id; po.sale_name=r.name; po.account_id=na.id; po.account_name=na.name; S.busyAcc[r.id]=na.id; const aid=`sale-${r.id}`; S.busy[r.id]="post"; S.status[aid]={state:"working",text:`${body.dry_run?"Đăng thử":"Đang đăng"} bài vào ${po.group_name||"trang cá nhân"}`};
        if(!body.dry_run) po.status="posting";
        setTimeout(()=>{ delete S.busy[r.id]; delete S.busyAcc[r.id]; S.status[aid]={state:"idle",text:"Chờ lịch đăng tiếp theo"};
          if(body.dry_run){ log(aid,"Đăng thử",`Bài #${po.id}: điền nội dung thành công (chưa bấm Đăng)`); }
          else { Object.assign(po,{status:"posted",posted_at:now(),poster:`${r.name} (tự động)`,posted_url:po.group_url||""}); const g=S.groups.find(g=>g.id===po.group_id); if(g) g.last_posted_at=now(); log(aid,"Đã đăng",`Bài #${po.id} lên ${po.group_name||"trang cá nhân"}`); } },5000);
        return {ok:true}; }
      if((m=P.match(/^\/posts\/(\d+)\/bump$/))){ const po=S.posts.find(x=>x.id==m[1]); if(!po.sale_id) throw new Error("Bài này không do nhân viên sale đăng nên chưa up tự động được");
        const aid=`sale-${po.sale_id}`; po.last_bump="running|||"; S.status[aid]={state:"working",text:`Đang up bài ở ${po.group_name||"trang cá nhân"}`};
        setTimeout(()=>{ po.bump_count=(po.bump_count||0)+1; po.last_bump_at=now(); po.last_bump="done|||"; S.status[aid]={state:"idle",text:"Chờ lịch tiếp theo"}; log(aid,"Up bài",`Bình luận ảnh vào bài #${po.id} ở ${po.group_name||"trang cá nhân"}`); },5000);
        return {ok:true}; }
      if(P==="/bump/plan-now") return {scheduled:demoBumpPlan()};
      if((m=P.match(/^\/posts\/(\d+)\/retry$/))){ const po=S.posts.find(x=>x.id==m[1]); Object.assign(po,{status:"approved",error:null,sale_id:null,sale_name:null,scheduled_for:null}); return po; }
      if((m=P.match(/^\/products\/(\d+)\/images$/))){ const pr=S.products.find(x=>x.id==m[1]); const im=JSON.parse(pr.images||"[]"); im.push(body.data); pr.images=JSON.stringify(im); return {images:im}; }
      if((m=P.match(/^\/posts\/(\d+)\/publish-page$/))) return {ok:false,error:"Bản xem trước không kết nối Facebook. Chạy backend và nhập Page Access Token trong Cài đặt."};
      if((m=P.match(/^\/leads\/(\d+)\/reply$/))){ S.status.ha={state:"working",text:"Đang soạn tin nhắn"}; await wait(900); S.status.ha={state:"idle",text:"Chờ duyệt tin"}; return {reply:reply(S.leads.find(l=>l.id==m[1]),body.message)}; }
      if(P==="/leads"){ const l={id:id(),...body,score:60,status:"new",created_at:now()}; S.leads.unshift(l); log("ha","Khách mới",l.name); return l; }
      if(P==="/products"){ if(!(body.name||"").trim()) throw new Error("Nhập tên sản phẩm"); if(S.products.some(p=>p.name.toLowerCase()===body.name.trim().toLowerCase())) throw new Error("Đã có sản phẩm cùng tên. Sửa sản phẩm đó thay vì thêm mới");
        const x={id:id(),...body,name:body.name.trim(),hot:body.hot?1:0,is_general:body.is_general?1:0,images:"[]"}; if(x.is_general) S.products.forEach(p=>p.is_general=0); S.products.push(x); log("minh","Thêm sản phẩm",`${x.name}: Lan có thể viết bài, Hà tư vấn sản phẩm này từ giờ`); return x; }
      if(P==="/groups"){ const u=demoGroupUrl(body.url); if(u.err) throw new Error(u.err); const x={id:id(),...body,url:u.url,leads_count:0,last_posted_at:null}; S.groups.push(x); log("tuan","Thêm nhóm",x.name); return x; }
      if(P==="/posts/reset"){ const ks=body.kinds||["approved","scheduled","failed"]; const del=S.posts.filter(p=>ks.includes(p.status)); S.posts=S.posts.filter(p=>!ks.includes(p.status));
        log("minh","Làm lại bài đăng",`Sếp xóa ${del.length} bài chưa đăng`+(body.rewrite?`. Lan viết lại ${body.rewrite} bài mới`:""));
        if(body.rewrite){ S.status.lan={state:"working",text:`Đang viết ${body.rewrite} bài mới`}; setTimeout(()=>{ genPosts(body.rewrite,null,"group").forEach(p=>{ p.status="approved"; p.source="template"; }); if(body.plan) plan(); S.status.lan={state:"idle",text:"Vừa viết xong bài mới"}; },2500); }
        return {deleted:del.length,rewrite:body.rewrite||0}; }
      if(P==="/run/daily-work"){ genPosts(3,null,"group"); const pl=plan(); return {drafts:3,scheduled:pl.length,follow_ups:S.leads.filter(l=>l.status==="new").length}; }
    }
     if(method==="POST"&&(m=P.match(/^\/leads\/(\d+)\/lost$/))){ const l=S.leads.find(x=>x.id==m[1]); if(!body.reason) throw new Error("Chọn lý do khách không mua"); Object.assign(l,{status:"lost",boss_status:"lost",lost_reason:body.reason,lost_note:body.note||""}); return l; }
    if(method==="PATCH"){
      if((m=P.match(/^\/posts\/(\d+)$/))){ const po=S.posts.find(x=>x.id==m[1]);
        if(body.posted_url&&!/(\/groups\/[^/?#]+\/(posts|permalink)\/\w+|\/posts\/(pfbid\w+|\d+)|story_fbid=|\/permalink\.php|multi_permalinks=\d+|\/share\/p\/\w+)/.test(body.posted_url)) throw new Error("Đây chưa phải link bài viết. Mở bài trên Facebook, bấm vào giờ đăng (VD “2 giờ”) rồi chép link trên thanh địa chỉ (có /posts/ hoặc /permalink/)");
        Object.assign(po,body); if(body.posted_url){ po.permalink_status="found"; po.bump_enabled=1; po.link_error=null; po.link_next_at=null; } if(body.status==="approved") log("minh","Duyệt bài",`Sếp duyệt bài #${po.id}`); return po; }
      if((m=P.match(/^\/leads\/(\d+)$/))){ const l=S.leads.find(x=>x.id==m[1]); const {contacted,...rest}=body; Object.assign(l,rest); if(contacted) l.last_contact_at=now(); return l; }
      if((m=P.match(/^\/tasks\/(\d+)$/))){ S.tasks.find(x=>x.id==m[1]).status=body.status; return {ok:true}; }
    }
    if(method==="PATCH"&&(m=P.match(/^\/groups\/(\d+)$/))){ const g=S.groups.find(x=>x.id==m[1]); if(body.url!=null){ const u=demoGroupUrl(body.url); if(u.err) throw new Error(u.err); body.url=u.url; }
      const had=!!g.url; Object.assign(g,body); if(!had&&g.url) S.posts.filter(p=>p.group_id===g.id&&p.status==="failed").forEach(p=>Object.assign(p,{status:"approved",error:null,sale_id:null,scheduled_for:null})); return {...g,ready:ready(g)}; }
    if(method==="PATCH"&&(m=P.match(/^\/products\/(\d+)$/))){ const pr=S.products.find(x=>x.id==m[1]); if(body.name!=null&&!body.name.trim()) throw new Error("Tên sản phẩm không được để trống");
      if(body.hot!=null&&!!pr.hot!==!!body.hot) log("minh","Sản phẩm bán chạy",`${pr.name}: ${body.hot?"đang bán chạy, cả đội tập trung chào mời":"thôi ưu tiên"}`); if(body.hot!=null) body.hot=body.hot?1:0;
      if(body.is_general!=null){ body.is_general=body.is_general?1:0; if(body.is_general) S.products.forEach(x=>x.is_general=0); log("tuan","Ảnh đăng bài",body.is_general?`Từ giờ mọi bài đăng chỉ lấy ảnh ngẫu nhiên trong “${pr.name}” (ảnh tổng hợp nhà máy)`:`Bỏ ảnh tổng hợp “${pr.name}”`); }
      Object.assign(pr,body); return {...pr,folder:body.image_folder!=null&&pr.image_folder?{...demoFolder(pr),count:20,fresh:20,posts_left:10}:demoFolder(pr)}; }
    if(method==="PATCH"&&(m=P.match(/^\/lessons\/(\d+)$/))){ const l=S.lessons.find(x=>x.id==m[1]); if(body.status==="retired") S.lessons=S.lessons.filter(x=>x!==l); else Object.assign(l,body); return l||{}; }
    if(method==="PATCH"&&(m=P.match(/^\/accounts\/(\d+)$/))){ const a=S.accounts.find(x=>x.id==m[1]); if(!a) throw new Error("Không tìm thấy nick");
      for(const k of ["active_from","active_to"]) if(body[k]!=null&&!/^\d{2}:\d{2}$/.test(body[k])) throw new Error("Giờ phải có dạng HH:MM");
      Object.assign(a,body); if(body.enabled===0) S.posts.filter(p=>p.account_id===a.id&&p.status==="scheduled").forEach(p=>Object.assign(p,{status:"approved",sale_id:null,sale_name:null,account_id:null,account_name:null,scheduled_for:null}));
      syncSale(a.sale_id); return saleOut(S.sales.find(x=>x.id===a.sale_id)); }
    if(method==="PATCH"&&(m=P.match(/^\/sales\/(\d+)$/))){ const r=S.sales.find(x=>x.id==m[1]); Object.assign(r,body); if(body.auto_post===0) S.posts.filter(p=>p.sale_id===r.id&&p.status==="scheduled").forEach(p=>Object.assign(p,{status:"approved",sale_id:null,sale_name:null,scheduled_for:null})); return saleOut(r); }
    if(method==="PUT"&&(m=P.match(/^\/groups\/(\d+)\/members$/))){ const g=S.groups.find(x=>x.id==m[1]); const ids=body.account_ids||[]; g.member_account_ids=ids.join(",");
      g.joins=Object.fromEntries(Object.entries(g.joins||{}).filter(([k,v])=>v.status!=="joined"||ids.includes(+k))); ids.forEach(i=>g.joins[i]={status:"joined"}); return {ok:true}; }
    if(method==="POST"&&P==="/costs/preset"){ const H="claude-haiku-5-5",So="claude-sonnet-5-5",PR={tiet_kiem:[H,H,H,H,H],can_bang:[So,So,H,So,H],chat_luong:[So,So,So,So,So]}[body.name];
      Object.assign(S.settings,{model_posts:PR[0],model_replies:PR[1],model_meeting:PR[2],model_ceo:PR[3],model_review:PR[4],use_batch:"1",cost_preset:body.name}); return S.settings; }
    if(method==="POST"&&P==="/ai-key") throw new Error("Bản xem trước không lưu khóa. Chạy phần mềm trên máy bạn để nhập khóa API.");
    if(method==="PUT"&&P==="/content-style"){ if(body.mode) S.style.mode=body.mode; return demoStyle(); }
    if(method==="POST"&&P==="/content-style/preview"){ const ps=S.products; const p=ps.find(x=>x.id==body.product_id)||ps[Math.floor(Math.random()*ps.length)];
      const hook=["💰 Nhập tận xưởng, biên lãi tốt cho shop online","📦 Nguồn {cat} tận xưởng, không qua trung gian, giá gốc cho người bán online","Chị em chủ live ơi, món này lên hình là ra đơn 🎥"][Math.floor(Math.random()*3)].replace("{wp}",p.wholesale_price).replace("{rp}",p.retail_price).replace("{cat}",p.category.toLowerCase());
      const content=[hook,"",`🌿 ${p.name}: ${p.description}`,...p.selling_points.split(/[,;]/).slice(0,3).map(x=>`✅ ${x.trim()}`),`📦 Nhập tối thiểu: ${p.moq}`,"","🎁 Tặng bộ ảnh, video quay tại xưởng để đăng bán","",'👉 Bình luận "quan tâm" mình inbox tư vấn nhé!',"",`💬 Giá vui lòng liên hệ trực tiếp Zalo ${ZALO()}`].join("\n");
      return {title:hook,content,hashtags:"#nguonhangsi #taxuong #banhangonline",product:p.name,angle:"Biên lợi nhuận cho người bán"}; }
    if(method==="PUT"&&P==="/knowledge/settings"){ if(body.study_time&&!/^\d{2}:\d{2}$/.test(body.study_time)) throw new Error("Giờ phải có dạng HH:MM"); Object.assign(S.kbSet,{self_study:body.self_study?"1":"0",idle_learning:body.idle_learning?"1":"0",idle_study_per_day:String(body.idle_study_per_day??6),knowledge_enabled:body.knowledge_enabled?"1":"0",study_time:body.study_time||S.kbSet.study_time,study_per_agent:String(body.study_per_agent||2)}); return demoKB(); }
    if(method==="DELETE"&&(m=P.match(/^\/knowledge\/(\d+)$/))){ S.kb=S.kb.filter(k=>k.id!=m[1]); return {ok:true}; }
    if(method==="PUT"&&P==="/telegram/report"){ S.settings.tg_report_done=body.report_done?"1":"0"; return demoTg(); }
    if(method==="DELETE"&&P==="/telegram/token"){ S.settings.tg_token=""; S.tgChats=0; S.pairCode=""; return demoTg(); }
    if(method==="PUT"&&P==="/settings"){ if(body.tg_token==="••••••") delete body.tg_token; Object.assign(S.settings,body); return S.settings; }
    if(method==="DELETE"&&(m=P.match(/^\/products\/(\d+)\/images$/))){ const pr=S.products.find(x=>x.id==m[1]); const path=new URLSearchParams(qs).get("path"); pr.images=JSON.stringify(JSON.parse(pr.images||"[]").filter(x=>x!==path)); return {ok:true}; }
    if(method==="POST"&&P==="/company/found"){ Object.assign(S.co,{status:"active",day:1,capital:body.capital,orders:[],founded_at:today()}); log("minh","Thành lập công ty",`Vốn ${body.capital}`); return demoCompany(); }
    if(method==="POST"&&P==="/company/capital"){ S.co.capital+=body.amount; return demoCompany(); }
    if(method==="POST"&&P==="/errors"){ const fp=body.title+"|"+body.message; const o=S.errors.find(e=>e.status!=="resolved"&&e.title+"|"+e.message===fp);
      if(o){ o.count++; o.last_at=now(); o.status="new"; return {id:o.id}; } const h=EHINT.find(([rx])=>rx.test(body.title+" "+body.message));
      const e={id:id(),source:"ui",...body,hint:h?h[1]:null,screen:body.screen||(h&&h[2])||null,count:1,status:"new",created_at:now(),last_at:now()}; S.errors.unshift(e); return {id:e.id}; }
    if(method==="POST"&&P==="/errors/seen"){ S.errors.forEach(e=>{ if(e.status==="new") e.status="seen"; }); return {ok:true}; }
    if(method==="POST"&&P==="/errors/resolve-all"){ S.errors.forEach(e=>e.status="resolved"); return {ok:true}; }
    if(P==="/prospects/criteria"){ const {keywords,rescore,...rest}=body; Object.assign(S.prCrit,rest); if(keywords) S.prKw={...S.prKw,...keywords};
      S.pr.forEach(x=>{ const txt=(x.account_name+" "+(x.products||"")+" "+(x.evidence||[]).map(e=>e.text).join(" ")).toLowerCase(); const ex=S.prCrit.exclude.filter(w=>txt.includes(w.toLowerCase()));
        const fail=[ex.length?"có chữ sếp loại: "+ex.join(", "):"",S.prCrit.skip_types.includes(x.seller_type)?`là ${PR_TYPES[x.seller_type]} (sếp bỏ qua)`:""].filter(Boolean).join("; ");
        x.evidence=(x.evidence||[]).filter(e=>e.kind!=="rule_fail"); if(fail){ x._g=x._g||x.grade; x.grade="D"; x.rule_fail=fail; x.next_action="Không đạt điều kiện của sếp: "+fail; x.evidence.unshift(ev("rule_fail","Không đạt điều kiện của sếp: "+fail)); }
        else if(x.rule_fail){ x.grade=x._g||x.grade; x.rule_fail=null; } });
      return {...demoPR(""),rescore:{checked:S.pr.length,fail:S.pr.filter(x=>x.rule_fail).length,crm:0}}; }
    if(P==="/prospects/lessons"&&method==="POST"){ const l={id:id(),text:body.text,applied:0,created_at:now(),suggest:demoUnderstand(body.text)}; S.prLessons.unshift(l); S.xp.mai=(S.xp.mai||0)+5; log("mai","Học kiến thức mới","Sếp dạy: "+body.text.slice(0,120)); return l; }
    if((m=P.match(/^\/prospects\/lessons\/(\d+)\/apply$/))){ const l=S.prLessons.find(x=>x.id==m[1]); const sg=l.suggest;
      for(const k of ["must","exclude","bonus","regions"]) S.prCrit[k]=[...new Set([...S.prCrit[k],...(sg[k]||[])])]; S.prCrit.search_kinds=[...new Set([...S.prCrit.search_kinds,...(sg.search_kinds||[])])];
      if((sg.keywords||[]).length) S.prKw[1]=[...new Set([...sg.keywords,...S.prKw[1]])]; l.applied=1; return {...demoPR(""),groups_added:0,rescore:{checked:S.pr.length}}; }
    if((m=P.match(/^\/prospects\/lessons\/(\d+)$/))&&method==="DELETE"){ S.prLessons=S.prLessons.filter(x=>x.id!=m[1]); return demoPR(""); }
    if(P==="/ceo-review"&&method==="PUT"){ if(body.min_score) S.cr.min_score=body.min_score; if(body.ai!=null) S.cr.ai=body.ai; return demoCR(); }
    if(P==="/ceo-review/try") return demoCRTry(body.content);
    if(P==="/samples"&&method==="POST"){ const c=(body.content||"").trim(); if(c.length<40) throw new Error("Bài mẫu quá ngắn"); const x={id:id(),title:(body.title||c.split("\n")[0]).slice(0,80),content:c,enabled:1,made:0,posted:0,comments:0,leads:0}; S.samples.push(x); return x; }
    if(P==="/samples/import"){ let n=0; (body.text||"").split(/\n\s*-{3,}\s*\n/).forEach(c=>{ c=c.trim(); if(c.length>=40){ S.samples.push({id:id(),title:c.split("\n")[0].slice(0,80),content:c,enabled:1,made:0,posted:0,comments:0,leads:0}); n++; } }); if(!n) throw new Error("Không thêm được bài nào"); return {added:n}; }
    if((m=P.match(/^\/samples\/(\d+)\/preview$/))){ const x=S.samples.find(y=>y.id==m[1]); return {preview:[tplVariant(x.content),tplVariant(x.content)]}; }
    if((m=P.match(/^\/samples\/(\d+)$/))){ if(method==="DELETE"){ S.samples=S.samples.filter(y=>y.id!=m[1]); return {ok:true}; } const x=S.samples.find(y=>y.id==m[1]);
      if(body.content!=null) x.content=body.content; if(body.title!=null) x.title=body.title; if(body.enabled!=null) x.enabled=body.enabled?1:0; return x; }
    if(P==="/post-template"&&method==="PUT"){ if(body.template!=null){ if(body.template.trim()&&body.template.trim().length<40) throw new Error("Mẫu quá ngắn"); S.tpl.template=body.template.trim()||TPL_DEFAULT; } if(body.enabled!=null) S.tpl.enabled=body.enabled; return demoTpl(); }
    if(P==="/post-template/preview") return {preview:[tplVariant((body.template||"").trim()||S.tpl.template),tplVariant((body.template||"").trim()||S.tpl.template)]};
    if(P==="/post-template/make"){ for(let i=0;i<(body.count||3);i++){ const sm=S.samples.filter(y=>y.enabled); const pickS=sm[Math.floor(Math.random()*sm.length)]||{content:S.tpl.template}; pickS.made=(pickS.made||0)+1; const c=tplVariant(pickS.content); const rvd=demoCRTry(c); S.posts.unshift({id:id(),review_score:Math.max(rvd.score,80),review_ok:1,review_note:`CEO chấm ${Math.max(rvd.score,80)}/100`,agent_id:"lan",product_id:null,product_name:"Mẫu của sếp",target_type:"group",angle:"mau_sep",title:c.split("\n")[0],content:c,hashtags:"",image_idea:"Ảnh catalog / nhà máy",status:"approved",created_at:now(),comments:0,leads:0,source:"template"}); }
      log("lan","Viết bài",`Làm ${body.count||3} bài đăng nhóm theo mẫu của sếp`); return {count:body.count||3}; }
    if(P==="/my-groups/sync"){ S.status.tuan={state:"working",text:"Rà soát nhóm trong các nick"}; setTimeout(()=>{ S.status.tuan={state:"idle",text:"Xong rà soát nhóm"}; },2500); return {nicks:2}; }
    if(P==="/my-groups/settings"){ const m={time:"mygroups_time",rest_days:"new_group_rest_days",leave_per_nick_day:"leave_per_nick_day",admin_min:"admin_posts_min",admin_max:"admin_posts_max",sell_share:"admin_sell_share"};
      for(const [k,v] of Object.entries(m)) if(body[k]!=null) S.mgSet[v]=String(body[k]); if(body.auto_leave!=null) S.mgSet.auto_leave=body.auto_leave?"1":"0"; if(body.enabled!=null) S.mgSet.mygroups_enabled=body.enabled?"1":"0"; return demoMG(); }
    if((m=P.match(/^\/my-groups\/(\d+)\/pin$/))){ S.mg.filter(x=>x.group_id==m[1]).forEach(x=>{ x.pinned=body.pin?1:0; if(x.verdict==="leave"&&body.pin){ x.verdict="keep"; x.verdict_note="Sếp giữ nhóm. "+x.verdict_note; } }); return demoMG(); }
    if((m=P.match(/^\/my-groups\/(\d+)\/leave$/))){ setTimeout(()=>S.mg.filter(x=>x.group_id==m[1]&&x.account_id==body.account_id).forEach(x=>{ x.verdict="left"; x.status="left"; x.left_at=now(); }),1500); return {ok:true}; }
    if(P==="/prospects/analyze"){ const offs=(body.urls||[]).filter(u=>/tiktok/.test(u)&&S.prSet.prospect_tiktok!=="1"||/shopee/.test(u)&&S.prSet.prospect_shopee!=="1");
      if(offs.length&&offs.length===(body.urls||[]).filter(Boolean).length) throw new Error(`${/tiktok/.test(offs[0])?"TikTok":"Shopee"} đang tắt. Bật lại ở mục Nguồn tìm rồi dán link`); }
    if(P==="/prospects/run"||P==="/prospects/analyze"){ S.status.mai={state:"working",text:P.endsWith("analyze")?"Đang phân tích link sếp gửi":"Tìm trên Facebook: livestream bán trà"};
      setTimeout(()=>{ const nid=Math.max(...S.pr.map(x=>x.id))+1;
        S.pr.unshift({id:nid,platform:"facebook",account_name:"Trà Sen Nhà Cúc (ví dụ)",shop_name:"Trà Sen Nhà Cúc",account_url:"https://www.facebook.com/trasennhacuc.vidu",seller_type:"owner",tags:"owner",direction:2,keyword:"shop trà túi lọc",recent_activity:"Bài mới nhất cách đây 1 ngày",live_freq:"",phone:"0903000333",zalo:null,email:null,products:"Trà sen, trà hoa nhài đóng hộp",categories:"Trà, cà phê, đồ uống, ngũ cốc, healthy",import_signals:"Hàng mới về",score:63,grade:"B",parts:{sales:14,live:8,fit:20,import:9,engage:6,contact:2,expand:4},status:"verified",lead_id:null,
          evidence:[ev("fit_core","Trà sen, trà hoa nhài đóng hộp làm quà","https://www.facebook.com/trasennhacuc.vidu"),ev("import","Hàng mới về, nhận đơn sỉ lẻ","https://www.facebook.com/trasennhacuc.vidu")],suggested:[{id:2,name:"Trà hoa đậu biếc - cỏ ngọt",why:"đúng nhóm hàng họ đang bán"}],
          approach:"Chào Trà Sen Nhà Cúc, em là Hà bên Xưởng Trà & Bột. Em thấy bên mình đang bán trà đóng hộp. Bên em là xưởng sản xuất trà túi lọc, có giá sỉ cho người bán online. Shop có muốn em gửi bảng giá tham khảo không ạ?",
          next_action:"Gọi hoặc nhắn Zalo 0903000333 theo kịch bản",created_at:now()});
        S.prLast={detail:"Mai tìm khách sỉ xong: tìm được 1 SĐT khách đang bán hàng (xem 6 tài khoản: A 0, B 1, C 2, D 3). Đã chuyển sếp: Trà Sen Nhà Cúc 0903000333 (B).",created_at:now()};
        S.status.mai={state:"idle",text:"Xong lượt tìm khách"}; log("mai","Tìm khách sỉ",S.prLast.detail); },2500);
      return {account:"Linh Nguyễn",sale_id:1,urls:body.urls}; }
    if(method==="PATCH"&&(m=P.match(/^\/prospects\/(\d+)$/))){ const x=S.pr.find(z=>z.id==m[1]); Object.assign(x,body); return x; }
    if(method==="POST"&&(m=P.match(/^\/prospects\/(\d+)\/crm$/))){ const x=S.pr.find(z=>z.id==m[1]); if(!x.lead_id){ x.lead_id=id(); S.leads.unshift({id:x.lead_id,name:x.shop_name||x.account_name,contact:x.account_url,phone:x.phone,origin:"prospect",channel:"Facebook",source:"Tìm khách sỉ",business_type:PR_TYPES[x.seller_type]||"",need:x.products||"",score:x.score||0,status:"new",note:""}); } return {lead_id:x.lead_id}; }
    if(method==="POST"&&(m=P.match(/^\/prospects\/(\d+)\/recheck$/))){ S.status.mai={state:"working",text:"Đang kiểm tra lại 1 tài khoản"}; setTimeout(()=>S.status.mai={state:"idle",text:"Xong"},2000); return {account:"Linh Nguyễn"}; }
    if(method==="PUT"&&P==="/prospects/settings"){ for(const k of ["enabled","facebook","tiktok","shopee","auto_crm","ai_script"]) if(body[k]!=null) S.prSet["prospect_"+k]=body[k]?"1":"0";
      if(body.groups_per_run!=null) S.prSet.prospect_groups_per_run=String(body.groups_per_run); for(const k of ["ads","groups"]) if(body[k]!=null) S.prSet["prospect_"+k]=body[k]?"1":"0"; if(body.time) S.prSet.prospect_time=body.time; if(body.fb_keywords) S.prSet.prospect_fb_keywords=String(body.fb_keywords); if(body.inspect_per_run) S.prSet.prospect_inspect_per_run=String(body.inspect_per_run); if(body.keywords) S.prKw={...S.prKw,...body.keywords}; return demoPR(""); }
    if(method==="PATCH"&&(m=P.match(/^\/errors\/(\d+)$/))){ const e=S.errors.find(x=>x.id==m[1]); if(e) e.status=body.status; return {ok:true}; }
    if(method==="DELETE"&&P==="/errors/resolved"){ S.errors=S.errors.filter(e=>e.status!=="resolved"); return {ok:true}; }
    if(method==="POST"&&P==="/ceo/chat"){ S.chat.push({id:id(),role:"boss",text:body.text,via:"web",created_at:now()}); await wait(700); const [r,x,q]=demoCeoDo(body.text);
      S.chat.push({id:id(),role:"ceo",text:x?`${r}\n• ${x}`:r,via:"web",created_at:now(),actions:q?[q]:[]}); log("ceo","Nhận việc từ sếp",body.text); return demoChat(); }
    if(method==="PUT"&&P==="/ceo/autopilot"){ S.settings.ceo_autopilot=body.on?"1":"0"; return demoChat(); }
    if(method==="DELETE"&&(m=P.match(/^\/ceo\/orders\/(\d+)$/))){ const o=S.orders.find(x=>x.id==m[1]); if(o) o.active=0; return demoChat(); }
    if(P==="/group-finder"&&method==="PUT"){ const st=S.gf; if(body.pool) st.pool=body.pool.map(x=>x.trim()).filter(Boolean);
      Object.entries({discover_time:body.discover_time,discover_keywords_per_day:body.discover_keywords_per_day,discover_add_per_day:body.discover_add_per_day,join_per_nick_day:body.join_per_nick_day,browse_minutes:body.browse_minutes,scout_per_run:body.scout_per_run,review_posts_day:body.review_posts_day,review_avg_reactions:body.review_avg_reactions,review_avg_comments:body.review_avg_comments,review_growth_week:body.review_growth_week,review_min_members:body.review_min_members,review_join_score:body.review_join_score}).forEach(([k,v])=>{ if(v!=null) st.settings[k]=String(v); });
      if(body.review_use_best_groups!=null) st.settings.review_use_best_groups=body.review_use_best_groups?"1":"0";
      if(body.discover_enabled!=null) st.settings.discover_enabled=body.discover_enabled?"1":"0"; if(body.join_enabled!=null) st.settings.join_enabled=body.join_enabled?"1":"0"; return demoGF(); }
    if(method==="POST"&&P==="/group-finder/today"){ S.gf.today=body.keywords.map(x=>x.trim()).filter(Boolean).slice(0,6); S.gf.by="boss"; return demoGF(); }
    if(method==="POST"&&P==="/group-finder/reroll"){ S.gf.today=S.gf.pool.slice().sort(()=>Math.random()-.5).slice(0,3); S.gf.by="ceo"; log("ceo","Chọn chủ đề tìm nhóm hôm nay",S.gf.today.join("; ")); return demoGF(); }
    if(method==="POST"&&P==="/group-finder/run"){ const ws=workingNicks(); if(!ws.length) throw new Error("Chưa có nick sale nào đăng nhập và đang bật tự đăng"); S.gfNick=((S.gfNick||0)+1)%ws.length; const na=ws[S.gfNick]; const r=S.sales.find(x=>x.id===na.sale_id); const aid=`sale-${r.id}`;
      S.status[aid]={state:"working",text:"Đang lướt Facebook"}; setTimeout(()=>S.status[aid]={state:"working",text:`Đang tìm nhóm: ${S.gf.today[0]}`},3000);
      setTimeout(()=>{ S.status[aid]={state:"idle",text:"Tìm được 2 nhóm mới"}; S.gf.last={at:now(),sale_id:r.id,found:2,added:1,joins:{joined:1,requested:0}};
        S.groups.push({id:id(),name:"Kinh Doanh Online Tại Nhà - Không Cần Vốn",url:"https://www.facebook.com/groups/kdonlinetainha",topic:S.gf.today[0],members:178000,rules:"",min_days_between_posts:3,last_posted_at:null,leads_count:0,source:"search",keyword:S.gf.today[0],member_account_ids:String(na.id),joins:{[na.id]:{status:"joined"}}});
        log(aid,"Tìm nhóm mới",`Tìm “${S.gf.today.join("”, “")}”: 2 nhóm mới, thêm 1 nhóm vào danh sách, xin vào 1 nhóm`); },9000);
      return {sale_id:r.id,account_id:na.id,account:na.name,keywords:S.gf.today}; }
    if(method==="POST"&&P==="/group-finder/join") return {ok:true,sales:workingNicks().length};
    if(method==="POST"&&P==="/group-finder/review"){ const se=S.gf.settings; const js=+se.review_join_score||60; const cnt={join:0,consider:0,skip:0,added:0};
      [...S.gf.candidates.filter(c=>!c.status),...(S.gf.rejected||[])].forEach(c=>{ c.verdict=c.verdict==="skip"&&/^Loại/.test(c.review_note||"")?"skip":c.eng_score>=js&&(c.sampled_posts<3||c.avg_comments>=0.6*se.review_avg_comments)?"join":c.eng_score>=Math.min(40,js-10)?"consider":"skip"; cnt[c.verdict]++; });
      S.gf.candidates.filter(c=>!c.status&&c.verdict==="join").forEach(c=>{ c.status="add"; cnt.added++; S.groups.push({id:id(),name:c.name,url:c.url,topic:c.keyword,members:c.members,eng_score:c.eng_score,verdict:"join",review_note:c.review_note,rules:"",min_days_between_posts:3,last_posted_at:null,leads_count:0,source:"search",keyword:c.keyword,member_account_ids:"",joins:{}}); });
      log("tuan","Đánh giá nhóm",`Chấm lại theo tiêu chí mới: nên vào ${cnt.join}, cân nhắc ${cnt.consider}, bỏ qua ${cnt.skip}`); return {...demoGF(),result:cnt}; }
    if(method==="POST"&&(m=P.match(/^\/group-finder\/candidates\/(\d+)\/(add|ignore)$/))){ let c=S.gf.candidates.find(x=>x.id==m[1]); if(!c){ c=(S.gf.rejected||[]).find(x=>x.id==m[1]); S.gf.rejected=S.gf.rejected.filter(x=>x!==c); S.gf.candidates.push(c); } c.status=m[2];
      if(m[2]==="add") S.groups.push({id:id(),name:c.name,url:c.url,topic:c.keyword,members:c.members,eng_score:c.eng_score,verdict:c.verdict,review_note:c.review_note,rules:"",min_days_between_posts:3,last_posted_at:null,leads_count:0,source:"search",keyword:c.keyword,member_account_ids:"",joins:{}}); return {ok:true}; }
    if(P==="/ceo"&&method==="PUT"){ const st=S.ceoSt; if(body.mode) st.mode=body.mode; if(body.potential!=null) st.potential_on=body.potential; if(body.milestones) st.milestones=body.milestones.slice().sort((a,b)=>a.amount-b.amount); return demoCeo(); }
    if(method==="POST"&&(m=P.match(/^\/ceo\/decisions\/(\d+)$/))){ const d=S.ceoSt.proposed.find(x=>x.id==m[1]); S.ceoSt.proposed=S.ceoSt.proposed.filter(x=>x!==d);
      if(d&&body.approve){ demoHire(d.reason); } else if(d){ S.ceoSt.decisions.unshift({...d,status:"rejected"}); } return demoCeo(); }
    if(method==="POST"&&P==="/ceo/review"){ S.ceoSt.decisions.unshift({id:id(),kind:"review",status:"done",title:"Đánh giá tiềm năng",reason:demoCeo().potential.verdict,created_at:now()}); return demoCeo(); }
    if(method==="POST"&&P==="/company/revenue"){ const l=S.leads.find(x=>body.customer&&x.name.toLowerCase()===body.customer.trim().toLowerCase()); if(l) l.status="ordered"; S.co.orders.unshift({id:id(),lead_name:l?l.name:(body.customer.trim()||"Khách lẻ"),amount:body.amount,note:body.note,via:"app",created_at:now()});
      const rev=S.co.orders.reduce((a,o)=>a+o.amount,0); S.ceoSt.reached=S.ceoSt.reached||[];
      S.ceoSt.milestones.filter(x=>rev>=x.amount&&!S.ceoSt.reached.includes(x.amount)).forEach(x=>{ S.ceoSt.reached.push(x.amount); const why=`Doanh thu đạt mốc ${vnd(x.amount)} (hiện ${vnd(rev)}).`;
        for(let k=0;k<x.hires;k++){ if(S.ceoSt.mode==="approve") S.ceoSt.proposed.unshift({id:id(),kind:"hire",status:"proposed",title:"Đề xuất tuyển thêm 1 sale",reason:why,created_at:now()}); else demoHire(why); } });
      return demoCompany(); }
    if(method==="DELETE"&&(m=P.match(/^\/orders\/(\d+)$/))){ S.co.orders=S.co.orders.filter(o=>o.id!=m[1]); return demoCompany(); }
    if(P==="/junk"||(m=P.match(/^\/leads\/(\d+)\/(un)?junk$/))||P.startsWith("/junk/")){
      const J=S.junk=S.junk||{items:[],skipped:4,dismissed:[]};
      const RS={not_seller:"Không bán hàng online",wrong_niche:"Sai ngành hàng",retail_buyer:"Chỉ mua lẻ, không nhập sỉ",competitor:"Đối thủ / nhà cung cấp",affiliate:"Affiliate / KOC",store:"Cửa hàng truyền thống",bad_phone:"Số điện thoại sai, không liên lạc được",spam:"Tài khoản ảo, spam",other:"Khác"};
      const ov=()=>{ const by={}; J.items.forEach(x=>by[x.reason]=(by[x.reason]||0)+1);
        const pats=J.items.length>=3?[{word:"dropship",label:"dropship",junk:3,good:0},{word:"quang chau",label:"quảng châu",junk:3,good:0}].filter(x=>!J.dismissed.includes(x.word)&&!S.prCrit.exclude.includes(x.label)):[];
        return {items:J.items,total:J.items.length,reasons:RS,by_reason:Object.entries(by).map(([reason,n])=>({reason,n})).sort((a,b)=>b.n-a.n),patterns:pats,skipped:J.skipped}; };
      if(m&&m[2]){ J.items=J.items.filter(x=>x.lead_id!=m[1]); const l=S.leads.find(x=>x.id==m[1]); l.status="new"; return l; }
      if(m){ const l=S.leads.find(x=>x.id==m[1]); const reason=RS[body.reason]?body.reason:"other"; J.items.unshift({id:id(),lead_id:l.id,name:l.name,phone:l.phone,reason,note:body.note||"",created_at:now()}); l.status="junk";
        let learned="Mai đã ghi nhớ, lần sau không đưa lại và loại các trường hợp giống vậy";
        if(reason==="wrong_niche"&&body.note){ const w=body.note.split(/[,;\/.]/).map(s=>s.trim().replace(/^(?:(?:chuyên|bán|shop|kinh doanh|buôn|sỉ|nhập)\s+)+/i,"")).filter(Boolean); S.prCrit.exclude=[...new Set([...S.prCrit.exclude,...w])]; learned="Thêm vào điều kiện loại: "+w.join(", "); }
        log("mai","Ghi nhớ data rác",`Sếp loại ${l.name}: ${RS[reason]}. ${learned}`); return {id:id(),learned}; }
      if(P==="/junk/exclude"){ S.prCrit.exclude.push(body.word); log("mai","Ghi nhớ data rác",`Sếp cho loại hẳn khách có chữ “${body.word}”`); return ov(); }
      if(P==="/junk/dismiss"){ J.dismissed.push(body.word); return ov(); }
      return ov(); }
    if(P.startsWith("/fb-policy")){ const F=S.fbp, ret=()=>handle("GET","/api/fb-policy");
      if(P==="/fb-policy/settings"){ Object.assign(F.settings,body); log("tuan","Sếp chỉnh giới hạn an toàn",Object.entries(body).map(([k,v])=>`${k.replace("fbp_","")}=${v}`).join(", ")); return ret(); }
      if(P==="/fb-policy/check"){ const t=body.text||"", is=[]; const tests=[[/chữa (khỏi|bệnh|dứt)|trị (bệnh|dứt điểm)|thay (thế )?thuốc|giảm \d+\s*(kg|ký|cân)|đặc trị/i,"high","hứa công dụng chữa bệnh, giảm cân (thực phẩm không được quảng cáo như thuốc)"],[/cam kết\s*100\s*%|an toàn tuyệt đối|không (có )?tác dụng phụ/i,"medium","cam kết tuyệt đối, dễ thành quảng cáo gây hiểu nhầm"],
          [/(tốt|rẻ|ngon|uy tín|chất lượng) nhất|duy nhất|số\s*(1|một)\b/i,"medium","dùng từ “nhất” / “số 1” khi không có chứng minh"],[/(like|thích)\s*(và|\+|&)?\s*(share|chia sẻ)|tag\s*\d*\s*(người|bạn)/i,"medium","câu tương tác (like/share/tag/bình luận số) bị Facebook giảm hiển thị"],[/\b(bit\.ly|tinyurl\.com|goo\.gl|cutt\.ly)\/\S*/i,"high","link rút gọn / chuyển hướng là dấu hiệu spam"]];
          tests.forEach(([rx,lv,msg])=>{ const m2=t.match(rx); if(m2) is.push({level:lv,msg,hit:m2[0]}); }); const tags=t.match(/(^|\s)#[^\s#]{2,}/g)||[]; if(tags.length>5) is.push({level:tags.length>10?"high":"medium",msg:`${tags.length} hashtag (tối đa 5)`,hit:""});
          F.custom.forEach(r=>(r.phrases||[]).forEach(ph=>{ if(ph&&t.toLowerCase().includes(ph.toLowerCase())) is.push({level:r.level,msg:`sếp cấm: ${r.title}`,hit:ph}); }));
          return {issues:is,ok:!is.some(i=>i.level==="high")}; }
      if(P==="/fb-policy/rules"&&method==="POST"){ F.custom.push({id:"c"+id(),cat:"content",how:body.phrases&&body.phrases.length?"check":"guide",level:body.level,title:body.title,rule:body.text||"",do:body.phrases&&body.phrases.length?"Bài có cụm: "+body.phrases.join(", ")+" sẽ bị chặn":"",custom:true,phrases:body.phrases}); log("tuan","Sếp thêm luật Facebook",body.title); return ret(); }
      if((m=P.match(/^\/fb-policy\/rules\/(.+)$/))){ F.custom=F.custom.filter(r=>r.id!==m[1]); return ret(); }
      if(P==="/fb-policy/watch"){ setTimeout(()=>{ F.watch_last=now(); F.sources.forEach(s=>s.last_checked=now()); log("tuan","Đọc lại chính sách Facebook",`Đọc ${F.sources.length} trang chính sách, không có gì mới`); },3000); return {started:true}; }
      if((m=P.match(/^\/fb-policy\/changes\/(\d+)\/read$/))){ F.changes.forEach(c=>{ if(c.id==m[1]) c.status="read"; }); return ret(); }
      if((m=P.match(/^\/fb-policy\/nicks\/(\d+)\/lift$/))){ F.restNick=null; return ret(); }
    }
    if((m=P.match(/^\/website\/products\/(\d+)$/))){ const p=S.products.find(x=>x.id==m[1]); p.site_show=body.show==null?null:(body.show?1:0); return {id:p.id}; }
    if(P.startsWith("/website")){ const W=S.ws, ret=()=>handle("GET","/api/website");
      if(P==="/website/settings"){ for(const [k,v] of Object.entries(body)){ if(k==="site_ftp_pass"){ if(v) W.settings.site_ftp_pass_set=true; continue; } W.settings[k]=k==="site_domain"&&v&&!/^https?:/.test(v)?"https://"+v:v; } return ret(); }
      if(P==="/website/keywords"&&method==="POST"){ W.keywords.push({id:id(),keyword:body.keyword,cluster:"",priority:body.priority||2,status:"planned"}); return ret(); }
      if(P==="/website/keywords/plan"){ const add=["gia công trà gừng túi lọc","nguồn sỉ cà phê hòa tan 3in1","gia công bột cần tây sấy lạnh"].filter(k=>!W.keywords.some(x=>x.keyword===k)); add.forEach(k=>W.keywords.push({id:id(),keyword:k,cluster:"gia công",priority:2,status:"planned"})); if(add.length) log("vy","Lên kế hoạch từ khóa",`Thêm ${add.length} từ khóa mới cho website`); return {added:add.length,...(await ret())}; }
      if((m=P.match(/^\/website\/keywords\/(\d+)$/))){ W.keywords=W.keywords.filter(k=>k.id!=m[1]||k.status!=="planned"); return ret(); }
      if(P==="/website/write"){ const k=body.kid?W.keywords.find(x=>x.id==body.kid):W.keywords.filter(x=>x.status==="planned").sort((a,b)=>a.priority-b.priority)[0]; if(!k) throw new Error("Hết từ khóa trong kế hoạch. Thêm từ khóa mới ở mục Website");
        S.status.vy={state:"working",text:`Viết bài SEO: ${k.keyword}`}; setTimeout(()=>{ const a=demoArticle(k.keyword), sc=demoSeo(a); const pid=id(); W.posts.unshift({id:pid,...a,status:"review",seo_score:sc.score,seo:sc,words:sc.words,policy_note:null,created_at:now(),published_at:null}); k.status="written"; S.status.vy={state:"idle",text:"Chờ lịch viết bài tiếp theo"}; log("vy","Viết bài website",`“${a.title}” (từ khóa: ${k.keyword}), ${sc.words} chữ, điểm SEO ${sc.score}/100`); },2500); return {started:true}; }
      if((m=P.match(/^\/website\/posts\/(\d+)$/))){ const p=W.posts.find(x=>x.id==m[1]);
        if(method==="DELETE"){ W.posts=W.posts.filter(x=>x!==p); W.keywords.forEach(k=>{ if(k.keyword===p.keyword) k.status="planned"; }); return {ok:true}; }
        Object.assign(p,body); const sc=demoSeo(p); Object.assign(p,{seo:sc,seo_score:sc.score,words:sc.words,policy_note:sc.policy.map(x=>x.msg).join("; ")||null}); return p; }
      if((m=P.match(/^\/website\/posts\/(\d+)\/(publish|unpublish)$/))){ const p=W.posts.find(x=>x.id==m[1]); if(m[2]==="publish"){ if(p.seo.policy.some(x=>x.level==="high")) throw new Error("Bài phạm luật quảng cáo: "+p.seo.policy.map(x=>x.msg).join("; ")); p.status="published"; p.published_at=now(); log("vy","Đăng bài website",`“${p.title}” lên mục Tin tức`); } else p.status="review"; W.last_build=now(); return p; }
      if(P==="/website/build"){ W.last_build=now(); return {pages:14+W.posts.filter(p=>p.status==="published").length,posts:W.posts.filter(p=>p.status==="published").length,products:S.products.length}; }
      if(P==="/website/check") return {ok:false,fixed:[],steps:[{name:"Tìm tên miền",ok:true,msg:"moctamvn.vn → 103.x.x.x"},{name:"Mở sitemap",ok:false,msg:"Bản demo không mở được tên miền thật. Trên máy chạy phần mềm, Vy mở sitemap như Google, tự tìm thư mục web đúng và đăng lại."}]};
      if(P==="/website/deploy/test") return {ok:false,steps:[{name:"Tìm máy chủ",ok:true,msg:"ftp.moctamvn.vn → 103.x.x.x"},{name:"Mở cổng",ok:false,msg:"Bản demo không kết nối được hosting thật. Trên máy chạy phần mềm, mỗi bước báo rõ lỗi và cách sửa."}]};
      if(P==="/website/deploy"){ if(!W.settings.site_ftp_host) throw new Error("Chưa điền máy chủ FTP, tài khoản và mật khẩu ở mục Website → Đăng lên hosting"); throw new Error("Bản demo không kết nối được hosting thật"); }
    }
    if(method==="POST"&&(m=P.match(/^\/posts\/(\d+)\/fetch-link$/))){ const po=S.posts.find(x=>x.id==m[1]); if(!po.sale_id) throw new Error("Bài này đăng tay, không có nick để tìm lại. Dán link bài vào ô bên dưới");
      po.link_error="Sale đang tìm lại link…"; setTimeout(()=>{ if(po.permalink_status!=="pending"){ Object.assign(po,{permalink_status:"found",posted_url:`https://www.facebook.com/groups/demo/posts/${100000+po.id}`,link_error:null,link_next_at:null}); log(`sale-${po.sale_id}`,"Đã lưu link bài",`Bài #${po.id}: ${po.posted_url}`); } else po.link_error="Bài vẫn đang chờ quản trị viên nhóm duyệt, sale sẽ tự lấy link khi bài được duyệt"; },4000); return {ok:true,queued:1}; }
    if(method==="POST"&&(m=P.match(/^\/leads\/(\d+)\/order$/))){ const l=S.leads.find(x=>x.id==m[1]); l.status="ordered"; S.co.orders.unshift({id:id(),lead_name:l.name,amount:body.amount,via:"app",created_at:now()}); log("ha","Có đơn hàng",`${l.name}: ${body.amount}`); return {ok:true}; }
    if(method==="POST"&&(m=P.match(/^\/sales\/(\d+)\/replace$/))) throw new Error("Bản xem trước không tuyển thay được. Chạy phần mềm trên máy để dùng.");
    if(method==="POST"&&P==="/reset"){ if(String(body.confirm).trim().toUpperCase()!=="CHAY THAT") throw new Error('Gõ đúng "CHAY THAT" để xác nhận');
      S.posts=[]; S.leads=[]; S.meetings=[]; S.msgs=[]; S.tasks=[]; S.activity=[]; S.lessons=[]; S.xp={}; S.goals={}; S.kpiPhone=0; S.sales=S.sales.filter(x=>!x.is_sample);
      if(body.products) S.products=[]; if(body.groups) S.groups=[]; log("minh","Bắt đầu chạy thật","Đã xóa dữ liệu thử nghiệm, giữ nhân viên sale và cài đặt"); return {deleted:[],backup:"data/backups/truoc-khi-chay-that.db"}; }
    if(P==="/coach"){ const A=[["Lan","viết bài đăng nhóm / trang cá nhân",7,2,"Bài mở bằng câu hỏi của người bán được sếp duyệt ngay; bài mở bằng giới thiệu xưởng hay bị sửa.",["Mở bài bằng nhu cầu của người bán lại (nguồn hàng, lãi), giới thiệu xưởng để sau.","Giữ bài dưới 120 chữ: 4/5 bài sếp sửa đều bị rút ngắn."],"Câu đầu đã nói tới người bán lại chưa?"],
        ["CEO Đức","chấm và duyệt bài trước khi đăng",3,1,"",[],""],["Tuấn","chọn nhóm và xếp lịch đăng",5,0,"",[],""],["Hà","soạn tin nhắn, kịch bản tư vấn khách",2,1,"Khách chê số lượng nhập tối thiểu ở 3/4 lần không mua.",["Hỏi khách bán được bao nhiêu hộp mỗi tuần trước khi báo mức nhập tối thiểu."],"Đã hỏi sức bán của khách chưa?"],
        ["Mai","tìm khách sỉ, chấm điểm người bán",6,0,"",[],""],["Bảo","viết câu trả lời khách hỏi mua trong nhóm",4,1,"",[],""]];
      const r={on:true,min:5,days:7,time:"22:30",model:"claude-sonnet-5-5",month_usd:0.042,month_calls:4,waiting:0,
        agents:A.map(([name,job,pending,times,assessment,lessons,check])=>({name,job,pending,times,in_batch:0,at:times?tzNow().slice(0,10)+" 22:41:00":null,assessment,lessons,check}))};
      return method==="POST"?{...r,msg:"Lan, Tuấn, Mai đã gửi việc thật cho Claude chấm, thường có kết quả sau vài phút (bản xem trước)"}:r; }
    if(P==="/housekeeping"){ const r={sizes:{db_mb:186.4,shots_mb:412.7,shots:2310,backups_mb:96.2,profiles_mb:3870.5,tables:[{name:"posts",mb:61.2},{name:"activity",mb:38.9},{name:"reply_tasks",mb:22.4}]},
      last:{at:tzNow().slice(0,10)+" 03:20:11",rows:{activity:18240,comment_seen:5120},shots:{files:640},freed_mb:1310.4},time:"03:20",on:true};
      return method==="POST"?{...r,text:"Em đã dọn: 23360 dòng nhật ký cũ, 640 ảnh chụp cũ, giải phóng 1310.4 MB. (bản xem trước)"}:r; }
    if(method==="DELETE"&&P==="/sample-data"){ S.sales=S.sales.filter(x=>!x.is_sample); S.accounts=S.accounts.filter(a=>S.sales.some(r=>r.id===a.sale_id)); S.leads=S.leads.filter(x=>!x.is_sample); S.groups=[]; S.products=[]; log("minh","Dọn dữ liệu mẫu","Đã xóa dữ liệu mẫu"); return {deleted:{}}; }
    if(method==="DELETE"&&(m=P.match(/^\/sales\/(\d+)$/))){ S.sales=S.sales.filter(x=>x.id!=m[1]); S.accounts=S.accounts.filter(a=>a.sale_id!=m[1]); return {ok:true}; }
    if(method==="DELETE"&&(m=P.match(/^\/accounts\/(\d+)$/))){ const a=S.accounts.find(x=>x.id==m[1]); if(!a) throw new Error("Không tìm thấy nick"); if(S.busyAcc[a.sale_id]===a.id) throw new Error("Nick đang làm việc, chờ xong ca rồi xóa");
      S.accounts=S.accounts.filter(x=>x!==a); S.posts.filter(p=>p.account_id===a.id&&p.status==="scheduled").forEach(p=>Object.assign(p,{status:"approved",sale_id:null,sale_name:null,account_id:null,account_name:null,scheduled_for:null})); syncSale(a.sale_id); return {ok:true}; }
    if(method==="DELETE"){ if((m=P.match(/^\/products\/(\d+)$/))){ const n=S.posts.filter(p=>p.product_id==m[1]&&["draft","approved"].includes(p.status)); n.forEach(p=>p.status="rejected"); S.products=S.products.filter(x=>x.id!=m[1]); return {ok:true,drafts_removed:n.length}; } if((m=P.match(/^\/groups\/(\d+)$/))) S.groups=S.groups.filter(x=>x.id!=m[1]); return {ok:true}; }
    throw new Error("Không hỗ trợ trong bản xem trước: "+path);
  }
  return {handle};
})();

