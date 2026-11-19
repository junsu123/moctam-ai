/* --------------------------------------------- Trang xu hướng (Nhi) */
async function loadTr(){ try{ ST.tr=await api("/trends"); }catch(e){ toast(e.message); return; } renderTr(); }
const trCopy=async t=>{ try{ await navigator.clipboard.writeText(t); toast("Đã chép"); }catch(e){ toast("Không chép được, bôi đen để chép"); } };
function renderTr(){ const d=ST.tr, hm=t=>t?`${t.slice(11,16)} ${t.slice(8,10)}/${t.slice(5,7)}`:"";
  $("#trTg").hidden=!!d.telegram; renderTi(d.img_bot);
  const act=d.pages.filter(p=>p.status==="active"), wait=d.posts.filter(p=>p.status==="need_image");
  $("#trStats").innerHTML=[[act.length,"Trang đang chạy"],[d.pages.filter(p=>p.status==="idea").length,"Ý tưởng Trang mới"],[wait.length,"Bài chờ ảnh"],[d.posts.filter(p=>p.status==="scheduled").length,"Bài đã có ảnh, chờ đăng"]]
    .map(([v,l])=>`<div class="pr-stat"><b>${v}</b><span>${l}</span></div>`).join("");
  $("#trWait").innerHTML=wait.length?wait.map(p=>`<article class="cm-item st-scheduled" data-trp="${p.id}"><div class="top"><span class="chip warn">Chờ ảnh</span><b>${esc(p.page_name)}</b><span>· đăng ${hm(p.scheduled_for)}</span><span>· ${esc(p.trend_topic||"")}</span></div>
      <p class="tx">${esc((p.content||"").slice(0,240))}${(p.content||"").length>240?"…":""}</p>
      <p class="small" style="margin:0"><b>Prompt ảnh:</b> <code style="white-space:pre-wrap;overflow-wrap:anywhere">${esc(p.image_prompt||"")}</code></p>${p.image_note?`<p class="small muted" style="margin:0">${esc(p.image_note)}</p>`:""}
      <div class="acts"><button type="button" class="btn sm" data-tra="copy">Chép prompt</button><label class="btn sm primary" style="cursor:pointer">Tải ảnh lên<input type="file" accept="image/*" data-tra="file" hidden></label><button type="button" class="btn sm" data-tra="ask">Gửi lại lên Telegram</button><button type="button" class="btn sm ghost" data-tra="skip">Bỏ bài</button></div></article>`).join("")
    :'<p class="muted small">Không có bài nào chờ ảnh.</p>';
  const rest=d.posts.filter(p=>p.status!=="need_image"), CH={scheduled:["Có ảnh, chờ đăng","ok"],posting:["Đang đăng","warn"],posted:["Đã đăng",""],failed:["Lỗi","bad"]};
  $("#trPosts").innerHTML=rest.length?rest.map(p=>{ const [lb,cl]=CH[p.status]||[p.status,""]; return `<article class="cm-item st-${p.status==="posted"?"done":p.status==="failed"?"failed":"scheduled"}"><div class="top"><span class="chip ${cl}">${lb}</span><b>${esc(p.page_name)}</b><span>· ${hm(p.posted_at||p.scheduled_for)}</span>${p.status==="posted"?`<span>· ${p.reactions||0} cảm xúc · ${p.comments||0} bình luận · ${p.shares||0} chia sẻ</span>`:""}</div>
      <p class="tx">${esc((p.content||"").split("\n")[0].slice(0,140))}</p>${p.error?`<p class="er">${esc(p.error)}</p>`:""}${p.posted_url?`<div class="acts"><a class="btn sm ghost" href="${esc(p.posted_url)}" target="_blank" rel="noopener">Mở bài</a></div>`:""}</article>`; }).join("")
    :'<p class="muted small">Chưa có bài nào.</p>';
  const nick=sel=>`<option value="">Nick quản trị</option>`+d.nicks.map(n=>`<option value="${n.id}" ${sel==n.id?"selected":""}>${esc(n.name)} (${esc(n.sale_name||"")})</option>`).join("");
  $("#trPages").innerHTML=d.pages.length?d.pages.map(p=>p.status==="idea"?`<article class="cm-item st-scheduled" data-trpg="${p.id}"><div class="top"><span class="chip warn">Ý tưởng</span><b>${esc(p.name)}</b><span>· ${esc(p.niche||"")}</span>${p.category?`<span>· ${esc(p.category)}</span>`:""}</div>
      ${p.description?`<p class="tx">${esc(p.description)}</p>`:""}${p.reason?`<p class="small muted" style="margin:0">Vì sao: ${esc(p.reason)}${p.trends?` (${esc(p.trends)})`:""}</p>`:""}
      ${p.avatar_prompt?`<p class="small" style="margin:0"><b>Ảnh đại diện:</b> <code style="overflow-wrap:anywhere">${esc(p.avatar_prompt)}</code> <button type="button" class="btn sm ghost" data-trcopy="${esc(p.avatar_prompt)}">Chép</button></p>`:""}
      ${p.cover_prompt?`<p class="small" style="margin:0"><b>Ảnh bìa:</b> <code style="overflow-wrap:anywhere">${esc(p.cover_prompt)}</code> <button type="button" class="btn sm ghost" data-trcopy="${esc(p.cover_prompt)}">Chép</button></p>`:""}
      <div class="row wrap" style="gap:6px"><input type="url" data-f="url" placeholder="Link Trang đã tạo (facebook.com/...)" aria-label="Link Trang" style="flex:1 1 220px"><select data-f="admin" aria-label="Nick quản trị">${nick()}</select><input type="number" data-f="per" min="1" max="3" value="2" aria-label="Bài mỗi ngày" style="width:64px" title="Bài mỗi ngày"><input data-f="times" value="09:00,19:30" aria-label="Giờ đăng" style="width:110px" title="Giờ đăng"></div>
      <div class="acts"><button type="button" class="btn sm primary" data-trpa="activate">Tôi đã tạo Trang này</button><button type="button" class="btn sm ghost" data-trpa="dismissed">Bỏ ý tưởng</button></div></article>`
    :`<article class="cm-item st-${p.status==="active"?"done":"x"}" data-trpg="${p.id}"><div class="top"><span class="chip ${p.status==="active"?"ok":""}">${p.status==="active"?"Đang chạy":"Tạm dừng"}</span><b>${esc(p.name)}</b><span>· ${esc(p.niche||"")}</span><span>· nick ${esc(p.admin_name||"?")}</span></div>
      <p class="small muted" style="margin:0">${p.followers!=null?`${Number(p.followers).toLocaleString("vi-VN")} người theo dõi · `:""}${p.posts_per_day} bài/ngày lúc ${esc(p.times||"")}${p.posted_30d!=null?` · ${p.posted_30d} bài 30 ngày, tương tác TB ${p.avg_eng}`:""}</p>
      <div class="acts">${p.url?`<a class="btn sm ghost" href="${esc(p.url)}" target="_blank" rel="noopener">Mở Trang</a>`:""}<button type="button" class="btn sm" data-trpa="${p.status==="active"?"paused":"active"}">${p.status==="active"?"Tạm dừng":"Chạy lại"}</button></div></article>`).join("")
    :'<p class="muted small">Chưa có Trang nào. Bấm <b>Nhi đọc xu hướng ngay</b> để có ý tưởng.</p>';
  renderTrLearn(d.learn);
  $("#trDay").textContent=d.research_day?`Nhi đọc lần cuối ngày ${d.research_day.slice(8,10)}/${d.research_day.slice(5,7)}; mỗi sáng ${d.settings.trend_time||"07:40"}.`:"Nhi chưa đọc xu hướng lần nào.";
  $("#trHot").innerHTML=d.hot.length?d.hot.map(h=>`<li><span class="nm">${esc(h.title)}</span><span class="chip ${h.score>=70?"ok":""}">${h.score}</span><span class="small muted">${esc(h.niche||"")}${h.why?" · "+esc(h.why):""}</span></li>`).join(""):'<li class="muted small">Chưa có.</li>';
  $("#trTrends").innerHTML=d.trends.length?d.trends.map(t=>`<li><span class="nm">${esc(t.title)}</span><span class="small muted">${esc(t.traffic||"")}${t.news&&t.news[0]?" · "+esc(t.news[0].title):""}</span></li>`).join(""):'<li class="muted small">Chưa có.</li>'; }
function renderTrLearn(L){ const box=$("#trLearn"); if(!L){ box.innerHTML=""; return; }
  const bar=(rows,min)=>rows.length?rows.map(r=>`<li><span class="nm">${esc(r.label)}</span><span class="chip ${r.n>=min&&r.avg>=1.15?"ok":r.n>=min&&r.avg<0.85?"bad":""}">${r.avg}×</span><span class="small muted">${r.n} bài${r.n<min?" · chưa đủ để so":""}</span></li>`).join(""):'<li class="muted small">Chưa có bài.</li>';
  const c=L.calib||{}, prog=Math.min(100,Math.round(100*L.n/Math.max(1,L.need)));
  box.innerHTML=`${L.n<L.need?`<p class="small" style="margin:4px 0">Đang gom số liệu: <b>${L.n}/${L.need}</b> bài Trang đã đăng (30 ngày)</p><div class="tl-bar" style="height:6px;background:var(--line,#eee);border-radius:4px;overflow:hidden"><i style="display:block;height:100%;width:${prog}%;background:var(--accent)"></i></div>`:""}
    <p class="small" style="margin:8px 0 2px"><b>Mắt chọn xu hướng:</b> ${c.n?`${c.pct}% chủ đề Nhi chấm từ 70 còn nóng 1–3 ngày sau (${c.hit}/${c.n})${c.flash&&c.flash.length?`<br><span class="muted">Chỉ nóng một ngày: ${esc(c.flash.slice(0,3).join(", "))}</span>`:""}`:'<span class="muted">chưa đủ ngày để chấm</span>'}</p>
    <h4 class="small" style="margin:8px 0 2px">Kiểu bài</h4><ul class="cm-top">${bar(L.kind,L.min_n)}</ul>
    <h4 class="small" style="margin:8px 0 2px">Độ dài</h4><ul class="cm-top">${bar(L.length,L.min_n)}</ul>
    <h4 class="small" style="margin:8px 0 2px">Khung giờ đăng</h4><ul class="cm-top">${bar(L.slot,L.min_n)}</ul>${L.best_slot&&L.best_slot.length?`<p class="small" style="margin:2px 0">💡 Gợi ý: dời giờ đăng vào khung <b>${esc(L.best_slot[0])}</b> (sửa ô Giờ đăng của Trang).</p>`:""}
    ${L.good.length?`<p class="small" style="margin:8px 0 2px"><b>Chủ đề được hưởng ứng:</b> ${L.good.map(t=>`${esc(t.topic)} <span class="muted">${t.x}×</span>`).join(" · ")}</p>`:""}
    ${L.bad.length?`<p class="small" style="margin:2px 0"><b>Ít hưởng ứng:</b> ${L.bad.map(t=>`${esc(t.topic)} <span class="muted">${t.x}×</span>`).join(" · ")}</p>`:""}
    <h4 class="small" style="margin:8px 0 2px">Bài học đang dùng</h4>${L.lessons.length?`<ul class="small" style="margin:0;padding-left:18px">${L.lessons.map(l=>`<li>${esc(l.text)}${l.evidence?` <span class="muted">(${esc(l.evidence)})</span>`:""}</li>`).join("")}</ul>`:'<p class="muted small" style="margin:0">Chưa có: Nhi rút bài học mỗi đêm khi số liệu đủ rõ.</p>'}`; }
$("#trResearch").onclick=async e=>{ e.target.disabled=true; try{ const r=await api("/trends/research","POST"); toast(`Nhi đọc ${r.trends} xu hướng mới, ${r.ideas} ý tưởng Trang mới`); loadTr(); }catch(err){ toast(err.message); } e.target.disabled=false; };
$("#trPlan").onclick=async e=>{ e.target.disabled=true; try{ const r=await api("/trends/plan","POST"); toast(r.written?`Nhi viết ${r.written} bài, đã gửi prompt ảnh lên Telegram`:"Không còn giờ đăng trống hôm nay hoặc chưa có Trang đang chạy"); loadTr(); }catch(err){ toast(err.message); } e.target.disabled=false; };
$("#trAdd").onsubmit=async e=>{ e.preventDefault(); try{ await api("/trends/pages","POST",{name:$("#trAddName").value,niche:$("#trAddNiche").value}); $("#trAddName").value=$("#trAddNiche").value=""; toast("Đã thêm, dán link và chọn nick quản trị để chạy"); loadTr(); }catch(err){ toast(err.message); } };
$("#v-trends").addEventListener("click",async e=>{
  const cp=e.target.closest("[data-trcopy]"); if(cp){ trCopy(cp.dataset.trcopy); return; }
  const b=e.target.closest("[data-tra]"); if(b&&b.dataset.tra!=="file"){ const id=b.closest("[data-trp]").dataset.trp, p=ST.tr.posts.find(x=>x.id==id);
    if(b.dataset.tra==="copy") return trCopy(p.image_prompt||"");
    try{ await api(`/trends/posts/${id}/${b.dataset.tra}`,"POST"); toast(b.dataset.tra==="ask"?"Đã gửi lại prompt lên Telegram":"Đã bỏ bài"); loadTr(); }catch(err){ toast(err.message); } return; }
  const pa=e.target.closest("[data-trpa]"); if(pa){ const card=pa.closest("[data-trpg]"), id=card.dataset.trpg, a=pa.dataset.trpa;
    try{ if(a==="activate"){ const f=k=>card.querySelector(`[data-f=${k}]`).value; await api(`/trends/pages/${id}/activate`,"POST",{url:f("url"),admin_account_id:f("admin"),posts_per_day:f("per"),times:f("times")}); toast("Trang bắt đầu chạy: bấm Lên lịch bài hôm nay hoặc chờ sáng mai"); }
      else { await api(`/trends/pages/${id}/status`,"POST",{status:a}); toast(a==="dismissed"?"Đã bỏ ý tưởng":a==="paused"?"Đã tạm dừng Trang, bỏ các bài chưa đăng":"Trang chạy lại"); }
      loadTr(); }catch(err){ toast(err.message); } } });
$("#v-trends").addEventListener("change",e=>{ const inp=e.target.closest("[data-tra=file]"); if(!inp||!inp.files[0]) return; const id=inp.closest("[data-trp]").dataset.trp, f=inp.files[0], rd=new FileReader();
  rd.onload=async()=>{ try{ await api(`/trends/posts/${id}/image`,"POST",{data:rd.result,ext:(f.type.split("/")[1]||"jpg")}); toast("Đã nhận ảnh, bài đã xếp đăng"); loadTr(); }catch(err){ toast(err.message); } }; rd.readAsDataURL(f); });

/* bot Telegram riêng cho ảnh của Nhi */
function renderTi(b){ const box=$("#tiBody"); if(!b){ box.innerHTML=""; return; }
  const err=b.error?`<p class="er" style="margin:6px 0 0">${esc(b.error)}</p>`:"";
  if(!b.has_token){ box.innerHTML=`<ol class="small" style="margin:4px 0 8px;padding-left:18px"><li>Trên Telegram nhắn <b>@BotFather</b> → <code>/newbot</code>, đặt tên (VD “Nhi Ảnh Mộc Tâm”), nhận token.</li><li>Dán token vào ô dưới → <b>Kiểm tra và lưu</b>.</li><li>Mở bot vừa tạo, gửi <b>mã 6 số</b> phần mềm hiện ra.</li></ol>
      <div class="row wrap" style="gap:6px"><input id="tiToken" placeholder="123456789:AAH…" aria-label="Token bot ảnh" style="flex:1 1 200px" autocomplete="off"><button type="button" class="btn sm primary" data-ti="save">Kiểm tra và lưu</button></div>${err}`; return; }
  if(!b.chats){ box.innerHTML=`<p class="small" style="margin:4px 0">Bot <b>@${esc(b.bot||"")}</b> (${esc(b.token_masked)}) đã lưu. Mở bot trên Telegram và gửi mã:</p>
      <p style="font:800 28px var(--f-display);letter-spacing:4px;margin:4px 0">${esc(b.pair_code||"——")}</p><div class="row wrap" style="gap:6px"><button type="button" class="btn sm" data-ti="pair">Tạo mã mới</button><button type="button" class="btn sm ghost" data-ti="clear">Gỡ bot</button></div>${err}`; return; }
  box.innerHTML=`<p class="small" style="margin:4px 0"><span class="chip ok">Đã kết nối</span> <b>@${esc(b.bot||"")}</b> · ${b.chats} người nhận</p>
    <label class="row small"><input type="checkbox" id="tiReport" ${b.report?"checked":""}> Báo việc của Nhi và báo cáo 21:45 qua bot này</label>
    <p class="small muted" style="margin:4px 0">Lệnh trên bot: /anh (bài chờ ảnh), /trang, /xuhuong, /baocao.</p>
    <div class="row wrap" style="gap:6px"><button type="button" class="btn sm" data-ti="test">Gửi tin thử</button><button type="button" class="btn sm" data-ti="pair">Thêm người nhận</button><button type="button" class="btn sm ghost" data-ti="clear">Gỡ bot</button></div>${err}`; }
$("#tiCard").addEventListener("click",async e=>{ const b=e.target.closest("[data-ti]"); if(!b) return; const a=b.dataset.ti; b.disabled=true;
  try{ if(a==="save"){ await api("/tg-img/token","POST",{token:$("#tiToken").value.trim()}); toast("Token đúng. Mở bot và gửi mã 6 số"); }
    else if(a==="pair"){ await api("/tg-img/pair","POST"); toast("Đã tạo mã mới, gửi mã này cho bot"); }
    else if(a==="test"){ await api("/tg-img/test","POST"); toast("Đã gửi tin thử"); }
    else if(a==="clear"){ if(!b.dataset.sure){ b.dataset.sure="1"; b.textContent="Bấm lần nữa để gỡ"; b.disabled=false; return; } await api("/tg-img/token","DELETE"); toast("Đã gỡ bot ảnh: Nhi dùng bot chính"); }
    loadTr(); }catch(err){ toast(err.message); b.disabled=false; } });
$("#tiCard").addEventListener("change",async e=>{ if(e.target.id!=="tiReport") return; try{ await api("/tg-img/settings","PUT",{report:e.target.checked?1:0}); toast(e.target.checked?"Nhi báo việc qua bot ảnh":"Đã tắt báo việc (prompt ảnh vẫn gửi)"); }catch(err){ toast(err.message); } });
