/* --------------------------------------------- bài đăng */
async function loadPostSamples(){
  let d; try{ d=await api("/samples"); }catch(e){ $("#smpList").innerHTML=`<p class="err">${esc(e.message)}</p>`; return; }
  ST.smp=d; $("#smpOn").checked=d.enabled; const on=d.items.filter(x=>x.enabled).length;
  $("#smpStats").textContent=`${d.items.length} bài mẫu (${on} đang dùng) · ${d.stats.approved} bài Lan viết sẵn chờ xếp lịch · ${d.stats.scheduled} bài đã lên lịch · hôm nay đã đăng ${d.stats.posted_today} bài · cuối mỗi bài: ${d.phone.replace(/^📞\s*/,"")}`;
  $("#smpList").innerHTML=d.items.length?d.items.map(x=>`<article class="smp${x.enabled?"":" off"}" data-smp="${x.id}">
    <div class="smp-h"><b>${esc(x.title||"Bài mẫu #"+x.id)}</b><label class="row small" style="white-space:nowrap"><input type="checkbox" data-smpon ${x.enabled?"checked":""}> Đang dùng</label></div>
    <pre>${esc(x.content)}</pre>
    <div class="smp-st"><span class="chip">${x.made} bài Lan đã viết lại</span><span class="chip">${x.posted} bài đã đăng</span><span class="chip ${x.comments?"ok":""}">${x.comments} bình luận</span><span class="chip ${x.leads?"ok":""}">${x.leads} khách</span></div>
    <div class="row wrap" style="gap:6px"><button class="btn sm" type="button" data-smpprev>Xem Lan viết lại</button><button class="btn sm ghost" type="button" data-smpmore>Xem đủ</button><button class="btn sm ghost" type="button" data-smpedit>Sửa</button><button class="btn sm ghost danger" type="button" data-smpdel>Xóa</button></div>
    <div class="smp-prev" hidden></div></article>`).join(""):'<div class="card empty">Chưa có bài mẫu nào. Dán bài đăng sỉ mẫu ở khung trên.</div>';
}
$("#smpForm").addEventListener("submit",async e=>{ e.preventDefault(); try{ await api("/samples","POST",{content:$("#smpText").value,title:$("#smpTitle").value}); e.target.reset(); toast("Đã thêm bài mẫu. Lan học và dùng từ lượt viết sau"); loadPostSamples(); }catch(err){ toast(err.message); } });
$("#smpBulkBtn").addEventListener("click",()=>{ $("#smpBulk").hidden=!$("#smpBulk").hidden; });
$("#smpBulkGo").addEventListener("click",async()=>{ try{ const r=await api("/samples/import","POST",{text:$("#smpBulkText").value}); $("#smpBulkText").value=""; toast(`Đã thêm ${r.added} bài mẫu`); loadPostSamples(); }catch(err){ toast(err.message); } });
$("#smpOn").addEventListener("change",async e=>{ try{ await api("/post-template","PUT",{enabled:e.target.checked}); toast(e.target.checked?"Bài đăng nhóm chỉ viết từ thư viện bài mẫu":"Đã tắt: Lan viết bài nhóm theo từng sản phẩm như trước"); loadPostSamples(); }catch(err){ toast(err.message); } });
$("#smpMake").addEventListener("click",async e=>{ const b=e.currentTarget; b.disabled=true; try{ const r=await api("/post-template/make","POST",{count:3}); toast(`Lan đã viết ${r.count} bài từ thư viện, chờ Tuấn xếp lịch (xem ở Bài đăng)`); loadPostSamples(); }catch(err){ toast(err.message); } b.disabled=false; });
$("#smpList").addEventListener("change",async e=>{ const c=e.target.closest("[data-smpon]"); if(!c) return; const id=c.closest("[data-smp]").dataset.smp;
  try{ await api(`/samples/${id}`,"PATCH",{enabled:c.checked}); toast(c.checked?"Lan dùng lại bài mẫu này":"Lan tạm không dùng bài mẫu này"); loadPostSamples(); }catch(err){ toast(err.message); } });
$("#smpList").addEventListener("click",async e=>{ const card=e.target.closest("[data-smp]"); if(!card) return; const id=card.dataset.smp, x=ST.smp.items.find(y=>y.id==id); let b;
  try{
    if(e.target.closest("[data-smpmore]")){ card.querySelector("pre").classList.toggle("open"); return; }
    if(e.target.closest("[data-smpprev]")){ const box=card.querySelector(".smp-prev"); box.hidden=false; box.innerHTML='<span class="small muted">Lan đang viết…</span>';
      const r=await api(`/samples/${id}/preview`,"POST"); box.innerHTML=r.preview.map((t,i)=>`<h5 class="small muted" style="margin:0">Bản Lan viết lại ${i+1}</h5><article>${esc(t)}</article>`).join(""); return; }
    if(e.target.closest("[data-smpedit]")){ card.querySelector("pre").outerHTML=`<form class="stack" data-smpsave><input type="text" value="${esc(x.title||"")}" aria-label="Tên bài mẫu"><textarea rows="12" aria-label="Nội dung bài mẫu">${esc(x.content)}</textarea><div class="row"><button class="btn sm primary" type="submit">Lưu</button><button class="btn sm ghost" type="button" data-smpcancel>Hủy</button></div></form>`; return; }
    if(e.target.closest("[data-smpcancel]")) return loadPostSamples();
    if((b=e.target.closest("[data-smpdel]"))){ if(b.dataset.confirm!=="1"){ b.dataset.confirm="1"; b.textContent="Bấm lần nữa để xóa"; return; } await api(`/samples/${id}`,"DELETE"); toast("Đã xóa bài mẫu"); return loadPostSamples(); }
  }catch(err){ toast(err.message); } });
$("#smpList").addEventListener("submit",async e=>{ const f=e.target.closest("[data-smpsave]"); if(!f) return; e.preventDefault(); const id=f.closest("[data-smp]").dataset.smp;
  try{ await api(`/samples/${id}`,"PATCH",{title:f.querySelector("input").value,content:f.querySelector("textarea").value}); toast("Đã lưu bài mẫu"); loadPostSamples(); }catch(err){ toast(err.message); } });
async function loadCeoReview(){
  let d; try{ d=await api("/ceo-review"); }catch(e){ return; }
  const pf=d.profile;
  $("#crBody").innerHTML=`<div class="cr-grid">
    <div class="stack">
      <dl class="cr-kv"><dt>Học từ</dt><dd>${pf.samples} bài mẫu của sếp · ${pf.lessons.length} bài học từ những lần sếp sửa</dd>
        <dt>Bài tốt phải có</dt><dd>Ý tìm khách sỉ / đại lý / gia công; lời kêu gọi + số Zalo; tiêu đề ngắn, gạch đầu dòng; giữ đủ thông tin của bài mẫu; không ghi giá; không hứa công dụng; không trùng bài đã đăng</dd>
        <dt>Độ dài</dt><dd>${pf.min_words}–${pf.max_words} chữ · tối đa ${pf.emoji_max} emoji</dd>
        ${pf.bad_phrases.length?`<dt>Cụm sếp đã bỏ</dt><dd>${pf.bad_phrases.map(esc).join("; ")}</dd>`:""}
        <dt>30 ngày qua</dt><dd>CEO duyệt ${d.approved} bài, loại ${d.rejected} bài; sếp phải sửa hoặc hủy ${d.boss_fixed} bài CEO đã duyệt${d.accuracy!=null?` · <b>duyệt đúng ý sếp ${d.accuracy}%</b>`:""}</dd></dl>
      <form id="crSet" class="row wrap" style="gap:10px;align-items:flex-end"><label class="f" for="crMin" style="max-width:220px">Điểm tối thiểu để duyệt<input type="number" id="crMin" min="40" max="95" value="${d.min_score}"></label>
        <label class="row small"><input type="checkbox" id="crAi" ${d.ai?"checked":""}> Nhờ Claude góp ý khi chấm (khi có khóa)</label><button class="btn sm primary" type="submit">Lưu</button></form>
      ${pf.lessons.length?`<div><b class="small">Bài học CEO rút ra từ sếp</b><ul class="recent" style="margin:4px 0 0">${pf.lessons.map(x=>`<li><span>${esc(x)}</span></li>`).join("")}</ul></div>`:'<p class="small muted" style="margin:0">Chưa có bài học từ sếp. Khi sếp sửa hoặc hủy một bài CEO đã duyệt (ở trang Bài đăng), CEO tự ghi lại và chấm chặt hơn lần sau.</p>'}
    </div>
    <div class="stack">
      <form id="crTry" class="stack"><label class="f" for="crTryIn">Thử: dán một bài để CEO chấm<textarea id="crTryIn" rows="6"></textarea></label><div><button class="btn sm" type="submit">CEO chấm thử</button></div><div id="crTryOut"></div></form>
      ${d.recent.length?`<div><b class="small">CEO chấm gần đây</b><ul class="recent" style="margin:4px 0 0">${d.recent.map(r=>`<li><span>${esc((r.title||"").slice(0,60))}</span><span class="chip ${r.review_score>=d.min_score?"ok":"bad"}">${r.review_score}/100</span></li>`).join("")}</ul></div>`:""}
    </div></div>`;
}
$("#crBody").addEventListener("submit",async e=>{ e.preventDefault();
  try{
    if(e.target.id==="crSet"){ await api("/ceo-review","PUT",{min_score:+$("#crMin").value,ai:$("#crAi").checked}); toast("Đã lưu tiêu chuẩn duyệt bài của CEO"); return loadCeoReview(); }
    if(e.target.id==="crTry"){ const r=await api("/ceo-review/try","POST",{content:$("#crTryIn").value});
      $("#crTryOut").innerHTML=`<div class="ceo-rv ${r.ok?"ok":"bad"}"><b>CEO chấm ${r.score}/100 · ${r.ok?"Duyệt":"Chưa duyệt"}</b>${r.reasons.length?`<br>${r.reasons.map(esc).join("; ")}`:""}${r.tips.length?`<br>Góp ý: ${r.tips.map(esc).join("; ")}`:""}</div>`; }
  }catch(err){ toast(err.message); } });
async function loadTpl(){
  let d; try{ d=await api("/samples"); }catch(e){ return; }
  $("#tplOn").checked=d.enabled; const on=d.items.filter(x=>x.enabled).length;
  $("#tplStats").textContent=`${on} bài mẫu đang dùng · ${d.stats.approved} bài chờ xếp lịch · ${d.stats.scheduled} bài đã lên lịch · hôm nay đã đăng ${d.stats.posted_today} bài. Mọi bài đăng vào nhóm nick đã tham gia và nhóm quản lý là bản viết lại của bài mẫu, cuối bài ${d.phone.replace(/^📞\s*/,"")}.`; }
$("#tplOn").addEventListener("change",async e=>{ try{ await api("/post-template","PUT",{enabled:e.target.checked}); toast(e.target.checked?"Bài đăng nhóm chỉ viết từ thư viện bài mẫu":"Đã tắt: Lan viết bài nhóm theo từng sản phẩm như trước"); loadTpl(); }catch(err){ toast(err.message); } });
async function loadPosts(){
  loadTpl(); loadTg();
  const [posts,products,sales]=await Promise.all([api("/posts"),api("/products"),api("/sales")]); ST.posts=posts; ST.products=products; ST.sales=sales;
  const sel=$("#gProduct"), cur=sel.value; sel.innerHTML=`<option value="">Lan tự chọn</option>`+products.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join(""); sel.value=cur;
  renderBoard();
  loadPosted();
}
function postsTab(tab, focus){
  tab=tab==="posted"?"posted":"work";
  ST.postsTab=tab; try{ localStorage.setItem("postsTab",tab); }catch(e){}
  for(const k of ["work","posted"]){ const b=$("#ptab-"+k), on=k===tab; b.setAttribute("aria-selected",on); b.tabIndex=on?0:-1; $("#ppanel-"+k).hidden=!on; }
  $("#postsActs").hidden=tab!=="work";
  if(focus) $("#ptab-"+tab).focus();
  const want=tab==="posted"?"posts/posted":"posts"; if(location.hash.slice(1)!==want) history.replaceState(null,"","#"+want);
}
$(".ptabs").addEventListener("click",e=>{ const b=e.target.closest("[role=tab]"); if(b) postsTab(b.id.replace("ptab-","")); });
$(".ptabs").addEventListener("keydown",e=>{ if(["ArrowLeft","ArrowRight","Home","End"].includes(e.key)){ e.preventDefault(); postsTab(ST.postsTab==="work"?"posted":"work",true); } });
