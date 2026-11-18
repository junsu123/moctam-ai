/* --------------------------------------------- lỗi */
const ESRC_ICON={ui:"🖱",api:"⚙️",post:"📝",bump:"🔁",scan:"💬",browser:"🌐",nick:"🔒",telegram:"✈️",ai:"🤖",fanpage:"📣",scheduler:"⏰"};
const EST={status:"open",source:""};
function setErrBadge(n){ const b=$("#errBadge"); b.hidden=!n; b.textContent=n>99?"99+":n; }
async function errBadge(){ if(ERR.off) return; if(ERR.badgeAt&&Date.now()-ERR.badgeAt<3000) return; ERR.badgeAt=Date.now();
  try{ const r=await api("/errors?status=new"); setErrBadge(r.new); if(ST.view==="errors") loadErrors(); }catch(e){} }
function errText(e){ return `[Lỗi #${e.id}] ${e.last_at} · ${e.source_label}${e.screen?` · màn hình ${VIEW_NAME[e.screen]||e.screen}`:""}${e.count>1?` · lặp ${e.count} lần`:""}
${e.title}
${e.message||""}${e.action?`\nThao tác: ${decodeURIComponent(e.action)}`:""}${e.detail?`\n--- chi tiết ---\n${e.detail}`:""}`; }
async function loadErrors(){
  let r; try{ r=await api(`/errors?status=${EST.status}&source=${encodeURIComponent(EST.source)}`); }
  catch(e){ $("#errList").innerHTML=`<div class="err">Không tải được danh sách lỗi: ${esc(e.message)}. ${HEALTH.bad?"Xem thông báo đỏ phía dưới màn hình.":"Phần mềm trên máy có thể đang chạy bản cũ: đóng cửa sổ run.bat rồi chạy lại."}</div>`; pollHealth(); return; }
  ST.errors=r.items; setErrBadge(r.new);
  const sel=$("#errSrc"); if(sel.options.length<2) sel.insertAdjacentHTML("beforeend",Object.entries(r.sources).map(([k,v])=>`<option value="${k}">${esc(v)}</option>`).join(""));
  $("#errSum").textContent=`${r.open} lỗi chưa xử lý · ${r.new} lỗi mới`;
  $("#errList").innerHTML=r.items.length?r.items.map(e=>`<article class="ecard ${e.status}" data-e="${e.id}">
    <div class="ecard-h"><div><h3>${ESRC_ICON[e.source]||"⚠️"} ${esc(e.title)}</h3>
      <div class="meta"><span>${esc(e.source_label)}</span>${e.screen?`<span>Màn hình: ${esc(VIEW_NAME[e.screen]||e.screen)}</span>`:""}<span>${fmtTime(e.last_at)} ${fmtDate(e.last_at)}</span>${e.count>1?`<span><b>Lặp ${e.count} lần</b> từ ${fmtDate(e.created_at)}</span>`:""}<span>#${e.id}</span></div></div>
      <span class="chip ${e.status==="new"?"bad":e.status==="seen"?"warn":"ok"}">${{new:"Mới",seen:"Đã xem",resolved:"Đã xử lý"}[e.status]}</span></div>
    ${e.message?`<div class="emsg">${esc(e.message)}</div>`:""}
    ${e.hint?`<div class="fix"><b>Cách xử lý:</b> ${esc(e.hint)}</div>`:'<div class="fix">Chưa có hướng dẫn cho lỗi này. Bấm <b>Sao chép</b> và gửi cho người hỗ trợ.</div>'}
    ${e.detail||e.action?`<details><summary class="small">Chi tiết kỹ thuật</summary><pre>${esc((e.action?"Thao tác: "+decodeURIComponent(e.action)+"\n":"")+(e.detail||""))}</pre></details>`:""}
    <div class="actions">${e.screen&&e.screen!=="errors"?`<a class="btn sm primary" href="#${esc(e.screen)}">Mở màn hình ${esc(VIEW_NAME[e.screen]||e.screen)}</a>`:""}
      ${e.screenshot?`<a class="btn sm" href="${esc(e.screenshot)}" target="_blank" rel="noopener">Ảnh chụp lúc lỗi</a>`:""}
      <button class="btn sm" type="button" data-ecopy="${e.id}">Sao chép</button>
      ${e.status!=="resolved"?`<button class="btn sm" type="button" data-eres="${e.id}">Đã xử lý</button>`:`<button class="btn sm ghost" type="button" data-eopen="${e.id}">Mở lại</button>`}</div>
  </article>`).join(""):`<div class="empty">${EST.status==="open"?"Không có lỗi nào cần xử lý. Khi có lỗi ở bất kỳ màn hình nào, lỗi sẽ hiện ở đây kèm cách xử lý.":"Không có lỗi nào."}</div>`;
  if(r.new&&EST.status!=="resolved") api("/errors/seen","POST").catch(()=>{});   // đã mở màn hình Lỗi: lỗi mới chuyển sang Đã xem
}
$("#errList").addEventListener("click",async ev=>{ const t=ev.target; let b;
  if((b=t.closest("[data-ecopy]"))){ const e=ST.errors.find(x=>x.id==b.dataset.ecopy); return copyText(errText(e)); }
  if((b=t.closest("[data-eres]"))){ await api(`/errors/${b.dataset.eres}`,"PATCH",{status:"resolved"}); toast("Đã đánh dấu đã xử lý"); return loadErrors(); }
  if((b=t.closest("[data-eopen]"))){ await api(`/errors/${b.dataset.eopen}`,"PATCH",{status:"seen"}); return loadErrors(); }
});
document.querySelectorAll("[data-es]").forEach(b=>b.onclick=()=>{ EST.status=b.dataset.es; document.querySelectorAll("[data-es]").forEach(x=>x.classList.toggle("on",x===b)); loadErrors(); });
$("#errSrc").onchange=e=>{ EST.source=e.target.value; loadErrors(); };
$("#errCopyAll").onclick=async()=>{ const r=await api("/errors?status=open"); if(!r.items.length) return toast("Không có lỗi nào chưa xử lý"); copyText(r.items.map(errText).join("\n\n==========\n\n")); };
$("#errResolveAll").onclick=async()=>{ await api("/errors/resolve-all","POST"); toast("Đã đánh dấu tất cả đã xử lý"); loadErrors(); };
$("#errClear").onclick=async e=>{ const b=e.currentTarget; if(!confirmInline(b)) return; await api("/errors/resolved","DELETE"); toast("Đã xóa các lỗi đã xử lý"); loadErrors(); };
function companyBanner(co){
  const b=$("#coBanner"), ov=$("#closedOverlay"), badge=$("#coBadge");
  ov.hidden=!(co&&co.status==="dissolved"); if(co&&co.status==="dissolved") $("#closedReason").textContent="";
  if(!co){ b.hidden=false; b.innerHTML='Công ty <b>chưa thành lập</b>: luật KPI tháng và thời hạn 60 ngày chưa áp dụng. <a href="#company">Thành lập công ty</a>'; badge.hidden=false; return; }
  badge.hidden=!(co.status==="dissolved"||(co.at_risk&&co.at_risk.length)||co.capital_left<=0);
  if(co.status==="dissolved"){ b.hidden=false; b.innerHTML='<b>Công ty đã giải thể.</b> Mọi hoạt động tự động đã dừng. <a href="#company">Xem lý do và thành lập lại</a>'; return; }
  const parts=[`Ngày ${co.day}/${co.trial_days}`,`vốn còn ${vnd(co.capital_left)}`,`doanh thu ${vnd(co.revenue)} (${co.orders} đơn)`];
  const warn=[]; if(!co.orders) warn.push(`còn ${Math.max(0,co.trial_days-co.day+1)} ngày để có đơn đầu tiên`); if(co.at_risk.length) warn.push(`nguy cơ sa thải: ${co.at_risk.map(esc).join(", ")}`); if(co.capital_left<=0) warn.push("hết vốn, AI đã tạm dừng");
  b.hidden=false; b.innerHTML=`🏢 ${parts.join(" · ")}${warn.length?` · <b>${warn.join(" · ")}</b>`:""}`;
}

