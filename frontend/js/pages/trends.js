/* --------------------------------------------- Trang xu hướng (Nhi) */
async function loadTr(){ try{ ST.tr=await api("/trends"); }catch(e){ toast(e.message); return; } renderTr(); }
const trCopy=async t=>{ try{ await navigator.clipboard.writeText(t); toast("Đã chép"); }catch(e){ toast("Không chép được, bôi đen để chép"); } };
function renderTr(){ const d=ST.tr, hm=t=>t?`${t.slice(11,16)} ${t.slice(8,10)}/${t.slice(5,7)}`:"";
  $("#trTg").hidden=!!d.telegram;
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
  $("#trDay").textContent=d.research_day?`Nhi đọc lần cuối ngày ${d.research_day.slice(8,10)}/${d.research_day.slice(5,7)}; mỗi sáng ${d.settings.trend_time||"07:40"}.`:"Nhi chưa đọc xu hướng lần nào.";
  $("#trHot").innerHTML=d.hot.length?d.hot.map(h=>`<li><span class="nm">${esc(h.title)}</span><span class="chip ${h.score>=70?"ok":""}">${h.score}</span><span class="small muted">${esc(h.niche||"")}${h.why?" · "+esc(h.why):""}</span></li>`).join(""):'<li class="muted small">Chưa có.</li>';
  $("#trTrends").innerHTML=d.trends.length?d.trends.map(t=>`<li><span class="nm">${esc(t.title)}</span><span class="small muted">${esc(t.traffic||"")}${t.news&&t.news[0]?" · "+esc(t.news[0].title):""}</span></li>`).join(""):'<li class="muted small">Chưa có.</li>'; }
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

