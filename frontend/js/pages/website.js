/* ---------- WEBSITE ---------- */
const WS_INFO=[["site_name","Tên thương hiệu"],["site_legal_name","Tên công ty (pháp lý)"],["site_tagline","Khẩu hiệu"],["site_domain","Tên miền (VD moctam.vn)"],["site_phone","Zalo / điện thoại"],["site_email","Email"],
  ["site_address","Địa chỉ nhà máy"],["site_certs","Tiêu chuẩn, chứng nhận"],["site_color","Màu thương hiệu"],["site_ga_id","Mã Google Analytics (G-...)"]];
const WS_ST={draft:["","Nháp"],review:["warn","Chờ sếp duyệt"],published:["ok","Đã đăng"]};
function wsTab(k){ ST.wsTab=k; for(const x of ["posts","kw","prod","info","host"]){ const on=x===k; $("#wtab-"+x).setAttribute("aria-selected",on); $("#wtab-"+x).tabIndex=on?0:-1; $("#wpanel-"+x).hidden=!on; } }
$("#wsProds").addEventListener("change",async e=>{ const sel=e.target.closest("[data-wsshow]"); if(!sel) return; const v=sel.value;
  try{ await api(`/website/products/${sel.dataset.wsshow}`,"PUT",{show:v==="auto"?null:v==="1"}); await loadWs(); toast("Đã lưu. Bấm Dựng lại website để cập nhật trang sản phẩm"); }catch(err){ toast(err.message); } });
$("#wsTabs").addEventListener("click",e=>{ const b=e.target.closest("[role=tab]"); if(b) wsTab(b.id.replace("wtab-","")); });
$("#wsTabs").addEventListener("keydown",e=>{ const ks=["posts","kw","prod","info","host"]; if(!["ArrowLeft","ArrowRight"].includes(e.key)) return; e.preventDefault();
  const i=(ks.indexOf(ST.wsTab||"posts")+(e.key==="ArrowRight"?1:4))%5; wsTab(ks[i]); $("#wtab-"+ks[i]).focus(); });
async function loadWs(){ try{ ST.ws=await api("/website"); }catch(e){ toast(e.message); return; } renderWs(); }
function renderWs(){
  const d=ST.ws; if(!d) return; const s=d.stats, cf=d.settings;
  const pr=d.products||[]; $("#wsProds").innerHTML=pr.length?pr.map(p=>`<tr><td><b>${esc(p.name)}</b><br><span class="small muted">${esc(p.category||"")}</span></td>
    <td>${p.on?'<span class="chip ok">Hiện</span>':'<span class="chip">Ẩn</span>'}${p.why?`<br><span class="small muted">${esc(p.why)}</span>`:""}</td>
    <td><select data-wsshow="${p.id}" aria-label="Hiện hay ẩn ${esc(p.name)} trên website"${p.general?" disabled":""}><option value="auto"${p.auto?" selected":""}>Vy tự nhận</option><option value="1"${!p.auto&&p.on?" selected":""}>Luôn hiện</option><option value="0"${!p.auto&&!p.on?" selected":""}>Luôn ẩn</option></select></td></tr>`).join("")
    :'<tr><td colspan="3" class="muted small">Chưa có sản phẩm. Thêm ở trang Sản phẩm.</td></tr>';
  $("#wsStats").innerHTML=[[s.published,"Bài đã đăng"],[s.review,"Chờ sếp duyệt"],[s.planned,"Từ khóa chờ viết"],[s.avg_seo||"—","Điểm SEO trung bình"],[d.pages||0,"Trang trên website"]]
    .map(([v,l])=>`<div class="pr-stat" style="cursor:default"><b>${v}</b><span>${l}</span></div>`).join("");
  $("#wsWriteInfo").textContent=`Vy viết ${cf.site_posts_week||3} bài/tuần vào ${(cf.site_write_days||"1,3,5").split(",").map(x=>["","T2","T3","T4","T5","T6","T7","CN"][+x]||x).join(", ")} lúc ${cf.site_write_time||"09:45"}`+(d.last_build?` · dựng website lần cuối ${fmtTime(d.last_build)} ${fmtDate(d.last_build)}`:" · chưa dựng website");
  ST.wsOpen=ST.wsOpen||null;
  $("#wsPosts").innerHTML=d.posts.length?d.posts.map(p=>{ const [cls,lab]=WS_ST[p.status]||["",p.status]; const open=ST.wsOpen===p.id;
    return `<tr class="click ws-row${open?" open":""}" data-ws="${p.id}" tabindex="0" aria-expanded="${open}"><td class="ws-main"><div class="ws-t">${esc(p.title)}</div><div class="small muted">Từ khóa: ${esc(p.keyword)}${p.policy_note?` · <span class="err">⚠ ${esc(p.policy_note)}</span>`:""}</div></td>
      <td data-l="SEO" class="num"><span class="chip ${p.seo_score>=(+cf.site_min_seo||75)?"ok":p.seo_score>=50?"warn":"bad"}">${p.seo_score}</span></td><td data-l="Tình trạng"><span class="chip ${cls}">${lab}</span></td>
      <td data-l="Chữ" class="num">${p.words||0}</td><td data-l="Ngày" class="small">${fmtDate(p.published_at||p.created_at)}</td></tr>`
      +(open?`<tr class="ws-edit"><td colspan="5" id="wsEd-${p.id}"><p class="muted small">Đang tải…</p></td></tr>`:""); }).join("")
    :`<tr><td colspan="5"><div class="empty">Chưa có bài nào. Bấm “Vy viết bài mới”.</div></td></tr>`;
  if(ST.wsOpen&&d.posts.some(p=>p.id===ST.wsOpen)) openWsPost(ST.wsOpen);
  $("#wsKws").innerHTML=d.keywords.map(k=>`<tr><td>${esc(k.keyword)}</td><td class="small">${esc(k.cluster||"")}</td><td class="small">${["","Cao","Vừa","Thấp"][k.priority]||k.priority}</td>
    <td>${k.status==="written"?'<span class="chip ok">Đã viết</span>':'<span class="chip">Chờ viết</span>'}</td>
    <td>${k.status==="planned"?`<button class="btn sm" data-kwwrite="${k.id}">Viết ngay</button> <button class="btn sm ghost" data-kwdel="${k.id}">Xóa</button>`:""}</td></tr>`).join("");
  $("#wsInfoFields").innerHTML=WS_INFO.map(([k,l])=>`<label class="f" for="wi-${k}">${l}<input type="${k==="site_color"?"color":"text"}" id="wi-${k}" data-k="${k}" value="${esc(cf[k]||"")}"></label>`).join("")
    +`<label class="f" for="wi-site_about" style="grid-column:1/-1">Giới thiệu nhà máy (trang Giới thiệu)<textarea id="wi-site_about" data-k="site_about" rows="4" placeholder="Để trống: Vy viết đoạn giới thiệu từ thông tin nhà máy">${esc(cf.site_about||"")}</textarea></label>`;
  $("#wsSchedFields").innerHTML=[["site_posts_week","Số bài / tuần","number"],["site_write_days","Ngày viết (1=T2 … 7=CN)","text"],["site_write_time","Giờ viết","time"],["site_min_seo","Điểm SEO tối thiểu để đăng","number"]]
    .map(([k,l,ty])=>`<label class="f" for="wi-${k}">${l}<input type="${ty}" id="wi-${k}" data-k="${k}" value="${esc(cf[k]||"")}"></label>`).join("");
  $("#wsAuto").checked=cf.site_auto_publish==="1";
  const md=cf.site_deploy_mode||"auto", isHttp=md==="http"; $("#wsMode").value=md; $("#wsHttpBox").hidden=!isHttp; $("#wsFtpFields").hidden=isHttp;
  $("#wf-site_sync_url").value=cf.site_sync_url||""; $("#wsSyncUrlShow").textContent=cf.site_sync_url_auto||"(điền tên miền ở tab Thông tin công ty)";
  $("#wsAutoDeploy").checked=cf.site_auto_deploy!=="0"; $("#wf-site_chmod_file").value=cf.site_chmod_file||"755"; $("#wf-site_chmod_dir").value=cf.site_chmod_dir||"755";
  $("#wsFtpFields").innerHTML=[["site_ftp_host","Máy chủ FTP (VD ftp.moctamvn.vn hoặc IP)","text"],["site_ftp_user","Tài khoản FTP","text"],["site_ftp_pass",cf.site_ftp_pass_set?"Mật khẩu (đã lưu, để trống nếu giữ nguyên)":"Mật khẩu FTP","password"],["site_ftp_dir","Thư mục trên hosting","text"]]
    .map(([k,l,ty])=>`<label class="f" for="wf-${k}">${l}<input type="${ty}" id="wf-${k}" data-k="${k}" autocomplete="off" value="${k==="site_ftp_pass"?"":esc(cf[k]||"")}"></label>`).join("");
  const cm=cf.site_check_msg||""; $("#wsCheckInfo").textContent=cm?(cm.startsWith("OK")?"Lần kiểm tra trước: ổn":"Lần kiểm tra trước: "+cm.replace(/^LỖI \S+ \S+: /,"lỗi ở ")):"";
  const msg=cf.site_deploy_msg||"";
  $("#wsDeployInfo").textContent=(d.last_deploy?`Đăng lần cuối ${fmtTime(d.last_deploy)} ${fmtDate(d.last_deploy)}`:"Chưa đăng lên hosting")
    +(msg.startsWith("LỖI")?" · "+msg:"")+(cf.site_sync_pending?" · có thay đổi chờ đẩy lên":"");
  $("#wsDeployInfo").classList.toggle("ws-err",msg.startsWith("LỖI"));
  $("#wsSitemap").textContent=(cf.site_domain||"https://ten-mien-cua-ban")+"/sitemap.xml";
}
function wsMd(b){ const e=esc; let out=[],lst=null; const inl=x=>e(x).replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>").replace(/\[([^\]]+)\]\(([^)\s]+)\)/g,'<a href="#" title="$2">$1</a>');
  const close=()=>{ if(lst){ out.push(`</${lst}>`); lst=null; } };
  (b||"").split("\n").forEach(r=>{ const l=r.trim(); if(!l){ close(); return; }
    if(l.startsWith("### ")){ close(); out.push(`<h3>${inl(l.slice(4))}</h3>`); } else if(l.startsWith("## ")){ close(); out.push(`<h2>${inl(l.slice(3))}</h2>`); }
    else if(/^[-*•]\s+/.test(l)){ if(lst!=="ul"){ close(); out.push("<ul>"); lst="ul"; } out.push(`<li>${inl(l.replace(/^[-*•]\s+/,""))}</li>`); }
    else if(/^\d+[.)]\s+/.test(l)){ if(lst!=="ol"){ close(); out.push("<ol>"); lst="ol"; } out.push(`<li>${inl(l.replace(/^\d+[.)]\s+/,""))}</li>`); }
    else { close(); out.push(`<p>${inl(l)}</p>`); } }); close(); return out.join(""); }
async function openWsPost(pid){
  let p; try{ p=await api(`/website/posts/${pid}`); }catch(e){ toast(e.message); return; }
  const box=$(`#wsEd-${pid}`); if(!box) return; ST.wsCur=p;
  const cnt=(v,a,b)=>`<span class="ws-cnt${v<a||v>b?" bad":""}">${v} ký tự (${a}–${b})</span>`;
  const seo=p.seo||{items:[],policy:[]};
  const faqTxt=(p.faq||[]).map(q=>`H: ${q.q}\nĐ: ${q.a||""}`).join("\n\n");
  box.innerHTML=`<div class="ws-ed"><div class="stack">
      <label class="f" for="we-title">Tiêu đề (H1) ${cnt(p.title.length,30,65)}<input type="text" id="we-title" value="${esc(p.title)}"></label>
      <div class="grid2"><label class="f" for="we-kw">Từ khóa chính<input type="text" id="we-kw" value="${esc(p.keyword)}"></label><label class="f" for="we-slug">Đường dẫn<input type="text" id="we-slug" value="${esc(p.slug)}"></label></div>
      <label class="f" for="we-mt">Thẻ tiêu đề trên Google ${cnt((p.meta_title||"").length,30,60)}<input type="text" id="we-mt" value="${esc(p.meta_title||"")}"></label>
      <label class="f" for="we-md">Mô tả trên Google ${cnt((p.meta_desc||"").length,120,160)}<textarea id="we-md" rows="2">${esc(p.meta_desc||"")}</textarea></label>
      <label class="f" for="we-body"><span>Nội dung (<code>## Mục</code>, <code>- gạch đầu dòng</code>, <code>[chữ](/san-pham/....html)</code>)</span><textarea id="we-body" rows="16">${esc(p.body)}</textarea></label>
      <label class="f" for="we-faq"><span>Câu hỏi thường gặp (mỗi câu: dòng <code>H:</code> rồi dòng <code>Đ:</code>)</span><textarea id="we-faq" rows="6">${esc(faqTxt)}</textarea></label>
      <div class="row wrap"><button class="btn" data-wsact="save">Lưu & chấm lại</button>${p.status==="published"?`<button class="btn" data-wsact="unpub">Gỡ khỏi website</button><a class="btn ghost" href="/site/tin-tuc/${esc(p.slug)}.html" target="_blank" rel="noopener" data-wsview>Xem trên website</a>`:`<button class="btn primary" data-wsact="pub">Duyệt &amp; đăng</button>`}<button class="btn ghost" data-wsact="prev">Xem dạng trang</button><button class="btn ghost danger" data-wsact="del">Xóa bài</button></div>
      <div class="ws-prev" id="wsPrev" hidden></div></div>
    <div class="stack"><div><b>Điểm SEO ${seo.score??p.seo_score}/100</b> <span class="small muted">· ${seo.words||p.words} chữ · mật độ từ khóa ${seo.density??"—"}%</span></div>
      <ul class="ws-seo">${(seo.items||[]).map(i=>`<li><span class="${i.ok?"ok":"no"}">${i.ok?"✓":"✗"}</span><span>${esc(i.label)} <span class="muted">(${i.points}/${i.max})</span>${i.tip?`<br><span class="small muted">${esc(i.tip)}</span>`:""}</span></li>`).join("")}</ul>
      ${(seo.policy||[]).length?`<div><b class="err">Luật quảng cáo</b>${seo.policy.map(x=>`<div class="fbp-issue"><span class="chip ${x.level==="high"?"bad":"warn"}">${x.level==="high"?"Chặn":"Nhắc"}</span><span>${esc(x.msg)}${x.hit?` (“${esc(x.hit)}”)`:""}</span></div>`).join("")}</div>`:`<p class="small" style="color:var(--accent);margin:0">✓ Không phạm luật quảng cáo</p>`}
      ${p.cover?`<p class="small muted" style="margin:0">Ảnh đại diện: ${esc(p.cover)} · alt: ${esc(p.cover_alt||"")}</p>`:`<p class="small err" style="margin:0">Chưa có ảnh đại diện (thêm thư mục ảnh ở mục Sản phẩm)</p>`}</div></div>`;
}
$("#wsPosts").addEventListener("click",async e=>{
  const a=e.target.closest("[data-wsact]");
  if(a){ const p=ST.wsCur; if(!p) return; const act=a.dataset.wsact;
    const faq=$("#we-faq").value.split(/\n\s*\n/).map(b=>{ const q=(b.match(/^H:\s*(.+)$/m)||[])[1], an=(b.match(/^Đ:\s*([\s\S]+)$/m)||[])[1]; return q?{q:q.trim(),a:(an||"").trim()}:null; }).filter(Boolean);
    try{
      if(act==="prev"){ const pv=$("#wsPrev"); pv.hidden=!pv.hidden; if(!pv.hidden) pv.innerHTML=`<h1 style="font-size:24px">${esc($("#we-title").value)}</h1>`+wsMd($("#we-body").value); return; }
      if(act==="save"){ await api(`/website/posts/${p.id}`,"PATCH",{title:$("#we-title").value,keyword:$("#we-kw").value,slug:$("#we-slug").value,meta_title:$("#we-mt").value,meta_desc:$("#we-md").value,body:$("#we-body").value,faq}); toast("Đã lưu, Vy chấm lại SEO"); }
      if(act==="pub"){ await api(`/website/posts/${p.id}`,"PATCH",{title:$("#we-title").value,keyword:$("#we-kw").value,slug:$("#we-slug").value,meta_title:$("#we-mt").value,meta_desc:$("#we-md").value,body:$("#we-body").value,faq});
        await api(`/website/posts/${p.id}/publish`,"POST"); toast("Đã đăng bài lên website"); }
      if(act==="unpub"){ await api(`/website/posts/${p.id}/unpublish`,"POST"); toast("Đã gỡ bài khỏi website"); }
      if(act==="del"){ if(a.dataset.c!=="1"){ a.dataset.c="1"; a.textContent="Bấm lần nữa để xóa"; return; } await api(`/website/posts/${p.id}`,"DELETE"); ST.wsOpen=null; toast("Đã xóa bài, từ khóa về lại kế hoạch"); }
    }catch(err){ toast(err.message); return; }
    return loadWs(); }
  if(e.target.closest("tr.ws-edit")) return;
  const r=e.target.closest("tr[data-ws]"); if(!r) return; const id=+r.dataset.ws; ST.wsOpen=ST.wsOpen===id?null:id; renderWs(); });
$("#wsPosts").addEventListener("keydown",e=>{ if((e.key==="Enter"||e.key===" ")&&e.target.matches("tr[data-ws]")){ e.preventDefault(); e.target.click(); } });
$("#wsWrite").onclick=async e=>{ e.target.disabled=true; try{ await api("/website/write","POST",{}); toast("Vy đang viết bài theo từ khóa ưu tiên kế tiếp (khoảng 1–2 phút)"); setTimeout(loadWs,4000); setTimeout(loadWs,30000); setTimeout(loadWs,90000); }catch(err){ toast(err.message); } setTimeout(()=>e.target.disabled=false,5000); };
$("#wsKwForm").addEventListener("submit",async e=>{ e.preventDefault(); try{ ST.ws=await api("/website/keywords","POST",{keyword:$("#wsKw").value,priority:+$("#wsKwPr").value}); e.target.reset(); $("#wsKwPr").value="2"; renderWs(); toast("Đã thêm từ khóa vào kế hoạch của Vy"); }catch(err){ toast(err.message); } });
$("#wsKwPlan").onclick=async e=>{ e.target.disabled=true; try{ const r=await api("/website/keywords/plan","POST"); ST.ws=r; renderWs(); toast(r.added?`Vy thêm ${r.added} từ khóa mới`:"Vy chưa nghĩ ra từ khóa mới"); }catch(err){ toast(err.message); } e.target.disabled=false; };
$("#wsKws").addEventListener("click",async e=>{ const w=e.target.closest("[data-kwwrite]"), d=e.target.closest("[data-kwdel]");
  try{ if(w){ w.disabled=true; await api("/website/write","POST",{kid:+w.dataset.kwwrite}); toast("Vy đang viết bài cho từ khóa này"); setTimeout(loadWs,4000); setTimeout(loadWs,30000); }
    if(d){ ST.ws=await api(`/website/keywords/${d.dataset.kwdel}`,"DELETE"); renderWs(); } }catch(err){ toast(err.message); } });
$("#wsInfo").addEventListener("submit",async e=>{ e.preventDefault(); const body={}; e.target.querySelectorAll("[data-k]").forEach(i=>body[i.dataset.k]=i.value); body.site_auto_publish=$("#wsAuto").checked?"1":"0";
  try{ ST.ws=await api("/website/settings","PUT",body); renderWs(); toast("Đã lưu thông tin. Bấm “Dựng lại website” để cập nhật trang"); }catch(err){ toast(err.message); } });
$("#wsFtp").addEventListener("submit",async e=>{ e.preventDefault(); const body={}; e.target.querySelectorAll("[data-k]").forEach(i=>body[i.dataset.k]=i.value); body.site_auto_deploy=$("#wsAutoDeploy").checked?"1":"0";
  try{ ST.ws=await api("/website/settings","PUT",body); renderWs(); toast("Đã lưu kết nối hosting"); }catch(err){ toast(err.message); } });
$("#wsCheck").onclick=async e=>{ e.target.disabled=true; const o=$("#wsCheckOut"); o.hidden=false; o.innerHTML='<li class="muted">Đang mở sitemap trên tên miền như Google đọc… (có lỗi sửa được thì Vy sửa và đăng lại, có thể mất 1–2 phút)</li>';
  try{ const r=await api("/website/check","POST");
    o.innerHTML=(r.fixed&&r.fixed.length?`<li class="ok"><b>Vy đã sửa:</b> ${esc(r.fixed.join("; "))}</li>`:"")
      +r.steps.map(x=>`<li class="${x.ok?"ok":"bad"}"><b>${x.ok?"✓":"✗"} ${esc(x.name)}</b> ${esc(x.msg||"")}${x.fix_domain?` <button class="btn" type="button" data-fixdom="${esc(x.fix_domain)}">Dùng ${esc(x.fix_domain)}</button>`:""}</li>`).join("")
      +(r.ok?`<li class="ok"><b>Google đọc được sitemap.</b> ${esc(r.next||"")}</li>`:"");
    loadWs();
  }catch(err){ o.innerHTML=`<li class="bad">${esc(err.message)}</li>`; } e.target.disabled=false; };
$("#wsCheckOut").addEventListener("click",async e=>{ const b=e.target.closest("[data-fixdom]"); if(!b) return; b.disabled=true;
  try{ ST.ws=await api("/website/settings","PUT",{site_domain:b.dataset.fixdom}); await api("/website/build","POST"); toast("Đã đổi tên miền, Vy dựng lại và tự đẩy lên sau ít phút. Bấm Kiểm tra lại sau 2 phút"); renderWs(); }catch(err){ toast(err.message); } });
$("#wsMode").addEventListener("change",e=>{ const h=e.target.value==="http"; $("#wsHttpBox").hidden=!h; $("#wsFtpFields").hidden=h; });
$("#wsSyncDl").addEventListener("click",()=>setTimeout(loadWs,800));
$("#wsTest").onclick=async e=>{ e.target.disabled=true; const o=$("#wsTestOut"); o.hidden=false; o.innerHTML='<li class="muted">Đang kiểm tra… (lưu cài đặt trước khi kiểm tra)</li>';
  try{ const r=await api("/website/deploy/test","POST");
    o.innerHTML=r.steps.map(x=>`<li class="${x.ok?"ok":"bad"}"><b>${x.ok?"✓":"✗"} ${esc(x.name)}</b> ${esc(x.msg||"")}</li>`).join("")+(r.ok?'<li class="ok"><b>Kết nối tốt.</b> Bấm “Đăng lên hosting”.</li>':"");
  }catch(err){ o.innerHTML=`<li class="bad">${esc(err.message)}</li>`; } e.target.disabled=false; };
$("#wsDeploy").onclick=async e=>{ e.target.disabled=true; $("#wsDeployInfo").textContent="Đang tải website lên hosting…";
  try{ const r=await api("/website/deploy","POST"); toast((r.files||r.deleted?`Đã đăng ${r.files} tệp mới/sửa (quyền ${r.perms})${r.deleted?`, xóa ${r.deleted} tệp cũ`:""} lên ${r.host}`:`Website trên ${r.host} đã mới nhất`)+(r.warn?". "+r.warn:"")); loadWs(); }catch(err){ toast(err.message); $("#wsDeployInfo").textContent=err.message; } e.target.disabled=false; };
$("#wsBuild").onclick=async e=>{ e.target.disabled=true; try{ const r=await api("/website/build","POST"); toast(`Đã dựng lại website: ${r.pages} trang, ${r.posts} bài viết`); loadWs(); }catch(err){ toast(err.message); } e.target.disabled=false; };
document.addEventListener("click",e=>{ const a=e.target.closest("#wsView,#wsZip,[data-wsview]"); if(a&&DEMO){ e.preventDefault(); toast("Bản demo: website thật nằm trên máy chạy phần mềm, mở tại địa chỉ /site/"); } });

ST.pd=ST.pd||{page:1,size:20,q:"",group_id:"",account_id:"",link:"",days:"0",sort:"new"};
ST.pdOpen=ST.pdOpen||new Set();
async function loadPosted(){
  const f=ST.pd, qs=new URLSearchParams(Object.entries(f).filter(([k,v])=>v!==""&&v!=null&&!(k==="days"&&v==="0"))).toString();
  try{ ST.posted=await api("/posts/posted?"+qs); }catch(e){ $("#pdStats").textContent=e.message; return; }
  ST.pd.page=ST.posted.page;
  const keep=(sel,opts,cur)=>{ sel.innerHTML=opts; sel.value=cur; };
  keep($("#pdGroup"),`<option value="">Tất cả nhóm</option>`+ST.posted.groups.map(g=>`<option value="${g.id}">${esc(g.name)} (${g.n})</option>`).join(""),f.group_id);
  keep($("#pdAcc"),`<option value="">Tất cả nick</option>`+ST.posted.accounts.map(a=>`<option value="${a.id}">${esc(a.sale_name?a.sale_name+" · ":"")}${esc(a.name)} (${a.n})</option>`).join(""),f.account_id);
  renderPosted(); renderBoard();
}
function pdLinkCell(p){
  const st=p.permalink_status;
  if(st==="found") return `<a class="btn sm" href="${esc(p.posted_url)}" target="_blank" rel="noopener">Mở bài</a>`;
  if(st==="pending") return `<span class="chip warn">Chờ nhóm duyệt</span>`;
  if(st==="removed") return `<span class="chip bad">Bị xóa/ẩn</span>`;
  return `<span class="chip bad">Chưa có link</span>`;
}
function renderPosted(){
  const d=ST.posted; if(!d) return;
  const s=d.stats;
  $("#pdStats").innerHTML=`<b>${s.total}</b> bài đã đăng · hôm nay ${s.today} · <b>${s.found}</b> có link`+(s.missing?` · <span style="color:var(--danger)">${s.missing} chưa có link</span>`:"")+(s.pending?` · ${s.pending} chờ nhóm duyệt`:"")+(s.removed?` · ${s.removed} bị xóa/ẩn`:"")+` · ${s.comments} bình luận · ${s.leads} khách`;
  const imgs=p=>{ try{ return JSON.parse(p.images_used||"[]").length; }catch(e){ return 0; } };
  $("#pdRows").innerHTML=d.items.length?d.items.map(p=>{ const open=ST.pdOpen.has(p.id);
    const where=p.group_name||TARGET[p.target_type]||p.target_type;
    return `<tr class="click pd-row${open?" open":""}" data-pd="${p.id}" tabindex="0" aria-expanded="${open}" title="Bấm để xem chi tiết, dán link, up bài">
      <td data-l="Ngày đăng" class="small">${fmtTime(p.posted_at)}<br>${fmtDate(p.posted_at)}</td>
      <td class="pd-main"><div class="pd-title">#${p.id} · ${esc(p.title||"(Không tiêu đề)")}</div><div class="pd-snip">${esc((p.content||"").replace(/\s+/g," ").slice(0,140))}</div>${p.product_name?`<span class="chip" style="margin-top:3px">${esc(p.product_name)}</span>`:""}</td>
      <td data-l="Đăng ở" class="small">${esc(where)}</td>
      <td data-l="Nick" class="small">${p.account_name?esc((p.sale_name?p.sale_name+" · ":"")+p.account_name):esc(p.poster||"Đăng tay")}</td>
      <td data-l="Ảnh" class="num">${imgs(p)||'<span class="chip bad">0</span>'}</td>
      <td data-l="Link bài">${pdLinkCell(p)}</td>
      <td data-l="Up" class="num">${p.bump_count||0}</td>
      <td data-l="Bình luận" class="num">${p.comments||0}</td>
      <td data-l="Khách" class="num">${p.leads?`<b style="color:var(--accent)">${p.leads}</b>`:0}</td></tr>`
      +(open?`<tr class="pd-detail"><td colspan="9">${postCard(p)}</td></tr>`:""); }).join("")
    :`<tr><td colspan="9"><div class="empty">${d.stats.total?"Không có bài nào khớp bộ lọc.":"Chưa có bài nào được đăng."}</div></td></tr>`;
  const pg=d.page, n=d.pages, win=[...new Set([1,pg-2,pg-1,pg,pg+1,pg+2,n])].filter(x=>x>=1&&x<=n).sort((a,b)=>a-b);
  const btns=[]; win.forEach((x,i)=>{ if(i&&x-win[i-1]>1) btns.push(`<span class="muted">…</span>`); btns.push(`<button type="button" data-pg="${x}" ${x===pg?'aria-current="page"':""}>${x}</button>`); });
  const from=d.total?(pg-1)*d.size+1:0, to=Math.min(pg*d.size,d.total);
  $("#pdPager").innerHTML=`<span class="small muted">${from}–${to} trên ${d.total} bài</span>
    <div class="pg"><button type="button" data-pg="${pg-1}" ${pg<=1?"disabled":""} aria-label="Trang trước">‹ Trước</button>${btns.join("")}<button type="button" data-pg="${pg+1}" ${pg>=n?"disabled":""} aria-label="Trang sau">Sau ›</button></div>
    <label class="row small">Mỗi trang <select id="pdSize">${[10,20,50,100].map(x=>`<option ${x===d.size?"selected":""}>${x}</option>`).join("")}</select></label>`;
}
$("#pdFilters").addEventListener("change",e=>{ const map={pdGroup:"group_id",pdAcc:"account_id",pdLink:"link",pdDays:"days",pdSort:"sort"}; const k=map[e.target.id]; if(!k) return; ST.pd[k]=e.target.value; ST.pd.page=1; loadPosted(); });
let pdT; $("#pdQ").addEventListener("input",e=>{ clearTimeout(pdT); pdT=setTimeout(()=>{ ST.pd.q=e.target.value.trim(); ST.pd.page=1; loadPosted(); },350); });
$("#pdPager").addEventListener("click",e=>{ const b=e.target.closest("[data-pg]"); if(!b||b.disabled) return; ST.pd.page=+b.dataset.pg; loadPosted().then(()=>$("#postedCard").scrollIntoView({block:"start",behavior:"smooth"})); });
$("#pdPager").addEventListener("change",e=>{ if(e.target.id==="pdSize"){ ST.pd.size=+e.target.value; ST.pd.page=1; loadPosted(); } });
$("#pdRows").addEventListener("click",e=>{ if(e.target.closest("tr.pd-detail")) return; const r=e.target.closest("tr[data-pd]"); if(!r||e.target.closest("a")) return;
  const id=+r.dataset.pd; ST.pdOpen.has(id)?ST.pdOpen.delete(id):ST.pdOpen.add(id); renderPosted(); });
$("#pdRows").addEventListener("keydown",e=>{ if((e.key==="Enter"||e.key===" ")&&e.target.matches("tr[data-pd]")){ e.preventDefault(); e.target.click(); } });
function postCard(p){
  const open=ST.openPost.has(p.id), editing=ST.editPost===p.id, posting=ST.postedForm===p.id;
  const SRCP={self:["ok","Lan tự viết"],claude:["","Claude viết"],boss:["talking","Sếp sửa"],template:["ok","Từ bài mẫu"]};
  const meta=`<div class="meta">${SRCP[p.source]?`<span class="chip ${SRCP[p.source][0]}" title="Ai viết nội dung bài này">${SRCP[p.source][1]}</span>`:""}<span class="chip">${TARGET[p.target_type]||p.target_type}</span>${p.product_name?`<span class="chip">${esc(p.product_name)}</span>`:""}${p.group_name?`<span class="chip ok">${esc(p.group_name)}</span>`:""}${p.fit_note&&p.status!=="posted"||p.orig_content&&p.fit_note?`<span class="chip ${p.orig_content?"talking":""}" title="${esc(p.fit_note)}">${p.orig_content?"✎ Chỉnh theo nhóm":"Giữ bài gốc"}</span>`:""}${p.scheduled_for&&p.status==="scheduled"?`<span class="chip warn">${fmtTime(p.scheduled_for)} ${fmtDate(p.scheduled_for)}</span>`:""}${p.sale_name?`<span class="chip">${esc(p.sale_name)}${p.account_name?` · nick ${esc(p.account_name)}`:""}</span>`:""}${p.status==="posting"?`<span class="chip talking">Đang đăng…</span>`:""}${p.status==="failed"?`<span class="chip bad">Đăng lỗi</span>`:""}${p.policy_note&&p.status!=="posted"?`<span class="chip bad" title="${esc(p.policy_note)}">⚠ Luật Facebook</span>`:""}${noImg(p)?`<span class="chip bad" title="Bài đăng lên Facebook bắt buộc kèm ảnh">📷 Thiếu ảnh, không đăng</span>`:p.img_count&&p.status!=="posted"?`<span class="chip" title="Số ảnh sản phẩm sẵn để đính kèm">📷 ${p.img_count} ảnh</span>`:""}</div>`;
  let acts="";
  const shot = p.screenshot?`<a class="btn sm ghost" href="${esc(p.screenshot)}" target="_blank" rel="noopener">Ảnh chụp</a>`:"";
  const salePick = p.target_type!=="page" && ST.sales?.some(s=>(s.accounts||[]).length) ? `<select class="sm" id="sale-${p.id}" aria-label="Nick đăng bài" style="width:auto;max-width:100%;padding:4px 8px;font-size:12.5px">${ST.sales.filter(s=>s.status!=="fired"&&(s.accounts||[]).length).map(s=>`<optgroup label="${esc(s.name)}">${s.accounts.map(n=>`<option value="${n.id}" ${n.id===p.account_id?"selected":""}>${esc(n.name)}${n.login_status!=="ok"||!n.enabled?" (chưa sẵn sàng)":""}</option>`).join("")}</optgroup>`).join("")}</select><button class="btn sm primary" data-act="runNow">Đăng ngay</button><button class="btn sm" data-act="dry">Đăng thử</button>`:"";
  if(p.status==="draft") acts=`<button class="btn sm primary" data-act="approve">Duyệt</button><button class="btn sm" data-act="edit">Sửa</button><button class="btn sm ghost danger" data-act="rejectAsk">Loại</button>`;
  if(p.status==="draft"&&ST.rejectForm===p.id) acts=`<div style="width:100%"><span class="small muted">Vì sao loại? Lan sẽ rút kinh nghiệm.</span><div class="reasons" style="margin-top:4px">${["Quá dài","Không hấp dẫn","Sai thông tin","Sai giọng văn","Trùng ý bài khác","Không hợp nhóm"].map(r=>`<button type="button" data-act="reject" data-reason="${r}">${r}</button>`).join("")}<button type="button" data-act="reject" data-reason="">Bỏ qua</button><button type="button" data-act="cancel">Hủy</button></div></div>`;
  else if(p.status==="approved"||p.status==="scheduled") acts=(noImg(p)?`<a class="btn sm primary" href="#products">Thêm ảnh sản phẩm</a>`:(p.target_type==="page"?`<button class="btn sm primary" data-act="page">Đăng Fanpage</button>`:"")+(p.target_type==="profile"||p.group_id?salePick:""))+`<button class="btn sm ghost" data-act="copy">Sao chép</button>${p.group_url?`<a class="btn sm ghost" href="${esc(p.group_url)}" target="_blank" rel="noopener">Mở nhóm</a>`:""}<button class="btn sm ghost" data-act="posted">Đăng tay xong</button>${shot}`;
  else if(p.status==="posting") acts=`<span class="small muted">${esc(p.sale_name||"Sale")} đang mở Chrome và đăng bài…</span>`;
  else if(p.status==="failed") acts=`<button class="btn sm primary" data-act="retry">Đưa về hàng đợi</button>${shot}`;
  else if(p.status==="posted"){
    const found=p.permalink_status==="found";
    acts=`${found?`<a class="btn sm primary" href="${esc(p.posted_url)}" target="_blank" rel="noopener">Mở bài viết</a>`:p.posted_url?`<a class="btn sm" href="${esc(p.posted_url)}" target="_blank" rel="noopener">Xem nhóm</a>`:""}`
      +(p.sale_id&&p.permalink_status!=="removed"?`<button class="btn sm" data-act="bump">Up ngay</button><button class="btn sm ghost" data-act="bumpToggle">${p.bump_enabled===0?"Bật tự up":"Dừng tự up"}</button>`:"")
      +`${shot}<span class="small muted">${esc(p.poster||"")} · ${fmtTime(p.posted_at)} ${fmtDate(p.posted_at)}</span>`;
  }
  const body = editing ? `<textarea id="edit-${p.id}" rows="10">${esc(p.content)}</textarea><div class="acts"><button class="btn sm primary" data-act="save">Lưu</button><button class="btn sm ghost" data-act="cancel">Hủy</button></div>`
    : `<pre class="${open?"open":""}">${esc(p.content)}</pre>${p.content.length>260?`<button class="btn ghost sm" data-act="more" style="align-self:flex-start">${open?"Thu gọn":"Xem đủ"}</button>`:""}`;
  const posted = posting ? `<div class="inline-form"><input type="text" id="poster-${p.id}" placeholder="Ai đăng? (VD: Linh - nick 2)"><input type="url" id="purl-${p.id}" placeholder="Dán link bài vừa đăng"><div class="acts"><button class="btn sm primary" data-act="confirmPosted">Xác nhận đã đăng</button><button class="btn sm ghost" data-act="cancel">Hủy</button></div></div>`:"";
  const result = p.status==="posted" ? `<div class="row small"><label class="f" style="flex:1">Bình luận<input type="number" min="0" value="${p.comments||0}" id="cm-${p.id}"></label><label class="f" style="flex:1">Khách thu được<input type="number" min="0" value="${p.leads||0}" id="ld-${p.id}"></label><button class="btn sm" data-act="result" style="align-self:flex-end">Lưu</button></div>`:"";
  const rv=p.review_score!=null?`<div class="ceo-rv ${p.review_ok===0?"bad":p.review_score>=85?"ok":""}"><b>CEO chấm ${p.review_score}/100</b>${(p.review_note||"").replace(/^CEO chấm \d+\/100:?\s*\.?\s*/,"")?` · ${esc((p.review_note||"").replace(/^CEO chấm \d+\/100:?\s*\.?\s*/,""))}`:""}</div>`:"";
  return `<article class="post" data-p="${p.id}"><h4>${esc(p.title||"(Không tiêu đề)")}</h4>${meta}${rv}${body}${p.hashtags?`<div class="tags">${esc(p.hashtags)}</div>`:""}${p.image_idea&&p.status!=="posted"?`<div class="idea"><b>Ảnh/video:</b> ${esc(p.image_idea)}</div>`:""}${postImgs(p)}${p.error?`<div class="err">${esc(p.error)}</div>`:""}${p.status==="posted"?linkBox(p):""}${posted}${result}<div class="acts">${acts}</div></article>`;
}
const PLINK={found:["ok","Đã lưu link bài"],pending:["warn","Bài chờ nhóm duyệt"],not_found:["bad","Chưa lưu được link"],removed:["bad","Bài đã bị xóa/ẩn"]};
function noLink(p){ return p.status==="posted"&&!["found","removed"].includes(p.permalink_status); }
function linkBox(p){
  const [c,t]=PLINK[p.permalink_status]||(p.sale_id?["warn","Chưa lấy được link"]:["","Đăng tay"]);
  const lb=(p.last_bump||"").split("|"); const BST={done:"đã up",failed:"up lỗi",skipped:"bỏ qua",scheduled:"chờ up",running:"đang up"};
  const bumpTxt=p.bump_count?`Đã up ${p.bump_count} lần · lần cuối ${fmtTime(p.last_bump_at)} ${fmtDate(p.last_bump_at)}`:"Chưa up lần nào";
  const needLink=p.permalink_status!=="found"&&p.permalink_status!=="removed";
  return `<div class="meta"><span class="chip ${c}">${t}</span>${p.sale_id?`<span class="chip">${bumpTxt}</span>`:""}${lb[0]&&lb[0]!=="done"?`<span class="chip ${lb[0]==="failed"?"bad":"warn"}">Lượt gần nhất: ${BST[lb[0]]||lb[0]}</span>`:""}</div>`
    +(lb[0]==="failed"||lb[0]==="skipped"?(lb[1]?`<div class="err">${esc(lb[1])}</div>`:""):"")
    +(needLink&&p.link_error?`<div class="small ${p.link_next_at?"muted":"err"}">${esc(p.link_error)}</div>`:"")
    +(needLink?`<div class="row wrap"><input type="url" id="plink-${p.id}" placeholder="Dán link bài viết (có /posts/ hoặc /permalink/)" style="padding:5px 8px;font-size:12.5px;flex:1 1 100%;min-width:0"><button class="btn sm" data-act="saveLink">Lưu link</button>${p.account_id?`<button class="btn sm ghost" data-act="fetchLink" title="Sale mở Chrome của nick đã đăng để tìm lại link">Lấy link ngay</button>`:""}</div>`:"");
}
function noImg(p){ return p.img_required&&p.img_count===0&&p.status!=="posted"; }
function postImgs(p){
  let imgs=[]; try{ imgs=JSON.parse(p.images_used||"[]"); }catch(e){}
  if(!imgs.length) return "";
  const label=p.status==="posted"?`Đã đăng kèm ${imgs.length} ảnh`:`Lần đăng thử chọn ${imgs.length} ảnh`;
  const base=n=>n.split(/[\\/]/).pop();
  return `<div><span class="small muted">${label}</span><div class="thumbs" style="margin-top:4px">${DEMO?imgs.map(n=>`<span class="fname" title="${esc(n)}">${esc(base(n))}</span>`).join(""):imgs.map(n=>`<figure><img src="/api/image?path=${encodeURIComponent(n)}" alt="${esc(base(n))}" title="${esc(base(n))}" loading="lazy"></figure>`).join("")}</div></div>`;
}
function renderBoard(){
  const cols=[["draft","Chờ duyệt"],["approved","Đã duyệt"],["scheduled","Lịch đăng hôm nay"]];
  const inCol=(p,s)=>s==="scheduled"?["scheduled","posting","failed"].includes(p.status):p.status===s;
  const miss=ST.posts.filter(p=>noImg(p)&&["approved","scheduled","draft","failed"].includes(p.status)).length, bar=$("#noImgBar");
  const nl=ST.posted?ST.posted.stats.missing+ST.posted.stats.pending:ST.posts.filter(noLink).length, lb=$("#noLinkBar");
  lb.hidden=!nl; if(nl) lb.innerHTML=`<b>${nl} bài đã đăng chưa lưu được link.</b> Bài chờ nhóm duyệt: sale tự lấy link khi bài được duyệt. Bài chưa tìm thấy: sale tự thử lại (sau 20 phút, 2, 6, 12, 24 giờ); hoặc bấm <b>Lấy link ngay</b>, hay dán link vào bài trong bảng dưới đây (lọc “Chưa có link”).`;
  bar.hidden=!miss; if(miss) bar.innerHTML=`<b>${miss} bài chưa có ảnh nên sẽ không đăng.</b> Bài đăng lên Facebook bắt buộc kèm ảnh sản phẩm. Thêm thư mục ảnh cho sản phẩm ở <a href="#products">Sản phẩm</a> hoặc thư mục ảnh chung ở <a href="#setup">Bình luận → Cài đặt</a>, Tuấn sẽ tự xếp lại các bài này.`;
  renderPosted();
  const work=ST.posts.filter(p=>["draft","approved","scheduled","posting","failed"].includes(p.status)).length;
  $("#ptabWorkN").textContent=work||"";
  if(ST.posted){ const s=ST.posted.stats, n=$("#ptabPostedN"); n.textContent=s.total||""; n.className="chip num"+(s.missing?" bad":"");
    n.title=s.missing?`${s.missing} bài chưa có link`:""; }
  $("#board").innerHTML=cols.map(([s,l])=>{ const list=ST.posts.filter(p=>inCol(p,s)); return `<div class="col"><header><b>${l}</b><span class="chip num">${list.length}</span></header>${list.map(postCard).join("")||`<div class="empty">Trống</div>`}</div>`; }).join("");
}
async function postAction(e){
  const b=e.target.closest("[data-act]"); if(!b) return; const card=b.closest("[data-p]"); const id=+card.dataset.p; const p=ST.posts.find(x=>x.id===id)||((ST.posted||{}).items||[]).find(x=>x.id===id); const act=b.dataset.act;
  if(!p) return;
  const patch=async body=>{ Object.assign(p,await api(`/posts/${id}`,"PATCH",body)); };
  if(act==="more"){ ST.openPost.has(id)?ST.openPost.delete(id):ST.openPost.add(id); return renderBoard(); }
  if(act==="edit"){ ST.editPost=id; return renderBoard(); }
  if(act==="cancel"){ ST.editPost=null; ST.postedForm=null; ST.rejectForm=null; return renderBoard(); }
  if(act==="save"){ await patch({content:$(`#edit-${id}`).value}); ST.editPost=null; toast("Đã lưu bài"); return renderBoard(); }
  if(act==="approve"){ await patch({status:"approved"}); toast("Đã duyệt. Tuấn sẽ xếp lịch."); refresh(); return loadPosts(); }
  if(act==="rejectAsk"){ ST.rejectForm=id; return renderBoard(); }
  if(act==="reject"){ await patch({status:"rejected",reason:b.dataset.reason||""}); ST.rejectForm=null; toast(b.dataset.reason?`Đã loại bài. Lan ghi nhận: "${b.dataset.reason}"`:"Đã loại bài"); return loadPosts(); }
  if(act==="copy") return copyText(`${p.content}\n\n${p.hashtags||""}`);
  if(act==="posted"){ ST.postedForm=id; return renderBoard(); }
  if(act==="confirmPosted"){ await api(`/posts/${id}/posted`,"POST",{poster:$(`#poster-${id}`).value,posted_url:$(`#purl-${id}`).value}); ST.postedForm=null; toast("Đã ghi nhận bài đăng"); refresh(); return loadPosts(); }
  if(act==="page"){ b.disabled=true; try{ const r=await api(`/posts/${id}/publish-page`,"POST"); toast(r.ok?"Đã đăng lên Fanpage kèm ảnh":r.error); }catch(err){ toast(err.message); } b.disabled=false; return loadPosts(); }
  if(act==="runNow"||act==="dry"){ const aid=+$(`#sale-${id}`).value; b.disabled=true;
    try{ await api(`/posts/${id}/run`,"POST",{account_id:aid,dry_run:act==="dry"}); toast(act==="dry"?"Sale đang mở Chrome điền thử bài, không bấm Đăng. Ảnh chụp sẽ có sau ít giây.":"Sale đang mở Chrome để đăng bài"); }
    catch(err){ toast(err.message); } b.disabled=false; refresh(); return loadPosts(); }
  if(act==="bump"){ b.disabled=true; try{ await api(`/posts/${id}/bump`,"POST"); toast(`${p.sale_name||"Sale"} sẽ bình luận ảnh để up bài trong vòng 1 phút`); }catch(err){ toast(err.message); } b.disabled=false; return loadPosts(); }
  if(act==="bumpToggle"){ await patch({bump_enabled:p.bump_enabled===0?1:0}); toast(p.bump_enabled===0?"Đã dừng tự up bài này":"Đã bật tự up bài này"); return renderBoard(); }
  if(act==="fetchLink"){ b.disabled=true; try{ await api(`/posts/${id}/fetch-link`,"POST"); toast(`${p.sale_name||"Sale"} đang mở Chrome nick đã đăng để tìm link bài`); }catch(err){ toast(err.message); } b.disabled=false; return loadPosts(); }
  if(act==="saveLink"){ const v=$(`#plink-${id}`).value.trim(); if(!/^https?:\/\/\S+/.test(v)){ toast("Dán đường dẫn bài viết, bắt đầu bằng https://"); return; } try{ await patch({posted_url:v}); }catch(err){ toast(err.message); return; } toast("Đã lưu link. Sale sẽ up bài này theo lịch."); ST.pdOpen.delete(id); return loadPosted(); }
  if(act==="retry"){ await api(`/posts/${id}/retry`,"POST"); toast("Đã đưa bài về hàng đợi. Tuấn sẽ xếp lại."); return loadPosts(); }
  if(act==="result"){ await patch({comments:+$(`#cm-${id}`).value,leads:+$(`#ld-${id}`).value}); toast("Khoa đã ghi nhận kết quả bài"); loadPosted(); }
}
$("#board").addEventListener("click",postAction);
$("#pdRows").addEventListener("click",postAction);
$("#genForm").addEventListener("submit",async e=>{ e.preventDefault(); const btn=$("#gBtn"); btn.disabled=true; btn.textContent="Lan đang viết…";
  try{ const r=await api("/posts/generate","POST",{count:+$("#gCount").value||3,product_id:+$("#gProduct").value||null,target_type:$("#gTarget").value,angle:$("#gAngle").value||null,note:$("#gNote").value});
    toast(`Lan đã viết ${r.length} bài, chờ sếp duyệt`); }catch(err){ toast(err.message); }
  btn.disabled=false; btn.textContent="Viết bài"; loadPosts(); refresh(); });
async function renderReset(){
  const el=$("#resetPanel"); const r=await api("/posts/reset"); ST.resetInfo=r;
  const sel=ST.resetSel||(ST.resetSel=new Set(["approved","scheduled","failed"]));
  const kinds=[["approved","Đã duyệt (chờ xếp lịch)"],["scheduled",`Lịch đăng${r.scheduled_today?` (hôm nay ${r.scheduled_today})`:""}`],["failed","Đăng lỗi"],["draft","Chờ duyệt"]];
  const total=kinds.filter(([k])=>sel.has(k)).reduce((s,[k])=>s+(r.counts[k]||0),0);
  const grp=kinds.filter(([k])=>sel.has(k)).reduce((s,[k])=>s+(r.group_counts[k]||0),0);
  if(ST.resetN==null) ST.resetN=Math.min(20,Math.max(grp,3));
  el.innerHTML=`<div class="card-h"><div><h3>Làm lại bài đăng</h3><p class="small muted" style="margin:2px 0 0">Xóa hẳn các bài chưa đăng bị lỗi hoặc không dùng nữa, rồi giao Lan viết bài mới. Bài đã đăng lên Facebook${r.posting?` và ${r.posting} bài đang đăng dở`:""} được giữ nguyên.</p></div></div>
    <div class="rk">${kinds.map(([k,l])=>`<label><input type="checkbox" data-rk="${k}" ${sel.has(k)?"checked":""}><span><b>${r.counts[k]||0}</b> ${l}</span></label>`).join("")}</div>
    <div class="grid3">
      <label class="f" for="rsN">Lan viết lại (bài đăng nhóm)<input type="number" id="rsN" min="0" max="20" value="${ST.resetN}"></label>
      <label class="row small" style="align-self:end"><input type="checkbox" id="rsPlan" checked> Viết xong cho Tuấn xếp lịch luôn</label>
    </div>
    <p class="small muted">${ST.resetN>0?"Bài nhóm viết theo thư viện bài mẫu của sếp (nếu đang bật), CEO chấm trước khi đăng. Bài vẫn phải có ảnh mới được đăng.":"Để 0 nếu chỉ muốn xóa, chưa viết bài mới."}</p>
    <div class="actions"><button class="btn danger" id="rsGo" ${total?"":"disabled"} data-confirm="0">Xóa ${total} bài${ST.resetN>0?` và viết lại ${ST.resetN} bài`:""}</button><button class="btn ghost" id="rsCancel">Hủy</button></div>`;
}
$("#btnReset").onclick=async()=>{ const el=$("#resetPanel"), open=el.hidden; el.hidden=!open; $("#btnReset").setAttribute("aria-expanded",String(open));
  if(open){ ST.resetSel=null; ST.resetN=null; try{ await renderReset(); el.scrollIntoView({block:"nearest",behavior:"smooth"}); }catch(e){ toast(e.message); } } };
$("#resetPanel").addEventListener("change",e=>{ const k=e.target.dataset.rk; if(k){ e.target.checked?ST.resetSel.add(k):ST.resetSel.delete(k); ST.resetN=null; renderReset(); }
  if(e.target.id==="rsN"){ ST.resetN=Math.max(0,Math.min(20,+e.target.value||0)); renderReset(); } });
$("#resetPanel").addEventListener("click",async e=>{
  if(e.target.id==="rsCancel"){ $("#resetPanel").hidden=true; $("#btnReset").setAttribute("aria-expanded","false"); return; }
  const b=e.target.closest("#rsGo"); if(!b) return;
  if(b.dataset.confirm!=="1"){ b.dataset.confirm="1"; b.textContent="Bấm lần nữa để xóa hẳn (không hoàn tác được)"; return; }
  b.disabled=true;
  try{ const r=await api("/posts/reset","POST",{kinds:[...ST.resetSel],rewrite:ST.resetN||0,plan:$("#rsPlan").checked});
    toast(`Đã xóa ${r.deleted} bài.`+(r.rewrite?` Lan đang viết ${r.rewrite} bài mới${$("#rsPlan").checked?", viết xong Tuấn xếp lịch":""}.`:""));
    $("#resetPanel").hidden=true; $("#btnReset").setAttribute("aria-expanded","false"); }
  catch(err){ toast(err.message); b.disabled=false; }
  loadPosts(); refresh(); if(ST.resetN) setTimeout(loadPosts,4000); });
$("#btnPlan").onclick=async()=>{ const r=await api("/distribution/plan","POST"); toast(r.length?`Tuấn đã xếp ${r.length} bài: ${r.map(x=>`${fmtTime(x.time)} ${x.sale?x.sale+" → ":""}${x.group}`).join("; ")}`.slice(0,220):"Chưa xếp được bài nào: chưa có bài đã duyệt, nhóm đang giãn cách, hoặc các nick đã đủ bài/ngày"); loadPosts(); refresh(); };

