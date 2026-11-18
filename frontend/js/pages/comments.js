/* --------------------------------------------- bình luận tự động */
const CM_ST={scheduled:["Chờ gửi","warn"],running:["Đang gửi","warn"],done:["Đã gửi","ok"],failed:["Lỗi","bad"],skipped:["Bỏ qua",""]};
async function loadCm(quiet){ const q=new URLSearchParams(); [["day","#cmDay"],["status","#cmSt"],["account_id","#cmAcc"],["q","#cmQ"]].forEach(([k,id])=>{ const v=$(id).value.trim(); if(v) q.set(k,v); });
  try{ ST.cm=await api("/comments"+(q.toString()?"?"+q:"")); }catch(e){ if(!quiet) toast(e.message); return; }
  renderCm(); if(!quiet){ try{ await loadBump(await api("/settings")); }catch(e){} } }
function renderCm(){ const d=ST.cm, c=d.counts, set=d.settings||{};
  if(!$("#cmDay").value) $("#cmDay").value=d.day; $("#cmTime").textContent=set.bump_time||"19:30";
  const b=$("#cmBadge"); const nf=d.day===d.today?c.failed:0; b.hidden=!nf; b.textContent=nf||""; b.title=nf?`${nf} bình luận lỗi hôm nay`:"";
  $("#cmStats").innerHTML=[[`${d.covered}<small class="muted" style="font-size:13px">/${d.eligible}</small>`,"Bài có bình luận hôm nay"],[c.done,"Đã gửi"],[c.scheduled+c.running,"Chờ gửi"],[c.failed,"Lỗi"]]
    .map(([v,l])=>`<div class="pr-stat"><b>${v}</b><span>${l}</span></div>`).join("");
  const acc=$("#cmAcc"), cur=acc.value; acc.innerHTML=`<option value="">Mọi nick</option>`+d.nicks.map(n=>`<option value="${n.id}">${esc(n.name)}</option>`).join(""); acc.value=cur;
  const hm=t=>(t||"").slice(11,16);
  $("#cmList").innerHTML=d.items.length?d.items.map(it=>{ const [lb,cl]=CM_ST[it.status]||[it.status,""];
    return `<article class="cm-item st-${it.status}" data-id="${it.id}"><div class="top"><span class="chip ${cl}">${lb}</span><span>${it.status==="done"?"gửi lúc "+hm(it.done_at):"lúc "+hm(it.scheduled_for)}</span><span>· ${esc(it.account_name||it.sale_name||"")}</span><span>· ${esc(it.group_name||"Trang cá nhân")}</span></div>
      <div class="small" style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"><b>${esc(it.title||"Bài #"+it.post_id)}</b></div>
      <p class="tx">${esc(it.text||"")}</p>${it.error?`<p class="er">${esc(it.error)}</p>`:""}
      <div class="acts">${it.status==="scheduled"?`<button type="button" class="btn sm" data-cm="edit">Sửa câu</button><button type="button" class="btn sm" data-cm="rewrite">Bảo viết lại</button><button type="button" class="btn sm ghost" data-cm="cancel">Hủy</button>`:""}${["failed","skipped"].includes(it.status)?`<button type="button" class="btn sm" data-cm="retry">Gửi lại</button>`:""}${it.posted_url?`<a class="btn sm ghost" href="${esc(it.posted_url)}" target="_blank" rel="noopener">Mở bài</a>`:""}${it.screenshot&&!DEMO?`<a class="btn sm ghost" href="${esc(it.screenshot)}" target="_blank" rel="noopener">Ảnh chụp</a>`:""}</div></article>`; }).join("")
    :`<p class="muted small">${d.day===d.today&&!d.planned_today?`Hôm nay chưa xếp lịch. Bảo tự xếp lúc ${esc(set.bump_time||"19:30")}, hoặc bấm <b>Xếp lịch bình luận ngay</b>.`:"Không có bình luận nào khớp bộ lọc."}</p>`;
  $("#cmCov").textContent=`${d.covered} bài đã có lượt hôm nay. Bài vừa đăng dưới 10 giờ hoặc đăng quá ${set.bump_max_age_days||7} ngày thì không bình luận.`;
  $("#cmPosts").innerHTML=d.posts.length?d.posts.map(p=>{ const t=p.today, st=t?(CM_ST[t.status]||[t.status,""]):null, can=p.account_id&&p.permalink_status!=="removed", off=p.bump_enabled===0;
    return `<li><span class="nm" title="${esc(p.title||"")}">${esc(p.title||"Bài #"+p.id)}</span>
      <span class="act">${can?`<button type="button" class="btn sm ghost" data-cmpost="${p.id}" data-on="${off?1:0}">${off?"Bật":"Tắt"} tự bình luận</button>`:""}${can&&!off&&!t?`<button type="button" class="btn sm" data-cmnow="${p.id}">Bình luận ngay</button>`:""}</span>
      <span class="mt">${esc(p.group_name||"Trang cá nhân")}${p.account_name?" · "+esc(p.account_name):""} · đã bình luận ${p.bump_count||0} lần · ${t?`<span class="chip ${st[1]}">${st[0]}</span>`:esc(p.reason||"")}</span></li>`; }).join("")
    :'<li class="muted small">Chưa có bài nào đã đăng trong mấy ngày gần đây.</li>';
  $("#cmNicks").innerHTML=d.nicks.length?d.nicks.map(n=>{ const lim=Math.max(1,Math.min(n.limit,n.per_nick)); return `<li><span><b>${esc(n.name)}</b> <span class="small muted">${n.used}/${lim} lượt</span></span><span class="meter"><i style="width:${Math.min(100,Math.round(n.used/lim*100))}%"></i></span></li>`; }).join("")
    :'<li class="muted small">Chưa có nick nào đăng nhập và đang làm việc.</li>'; }
["#cmDay","#cmSt","#cmAcc"].forEach(id=>$(id).onchange=()=>loadCm(true));
{ let t; $("#cmQ").oninput=()=>{ clearTimeout(t); t=setTimeout(()=>loadCm(true),300); }; }
$("#cmPlan").onclick=()=>$("#bNow").click();
$("#v-comments").addEventListener("click",async e=>{
  const bt=e.target.closest("[data-cm]"); if(bt){ const card=bt.closest(".cm-item"), id=card.dataset.id, act=bt.dataset.cm;
    if(act==="edit"){ const it=ST.cm.items.find(x=>x.id==id); card.querySelector(".tx").outerHTML=`<textarea class="tx" rows="3" maxlength="300" aria-label="Câu bình luận">${esc(it.text||"")}</textarea>`; bt.outerHTML=`<button type="button" class="btn sm primary" data-cm="save">Lưu câu</button>`; card.querySelector("textarea").focus(); return; }
    bt.disabled=true;
    try{ if(act==="save") await api(`/comments/${id}`,"PUT",{text:card.querySelector("textarea").value}); else await api(`/comments/${id}/${act}`,"POST");
      toast({save:"Đã lưu câu bình luận",rewrite:"Bảo đã viết câu mới",cancel:"Đã hủy lượt bình luận này",retry:"Đã xếp gửi lại, sale gửi trong vài phút khi rảnh"}[act]); loadCm(true); }catch(err){ toast(err.message); bt.disabled=false; } return; }
  const tg=e.target.closest("[data-cmpost]"); if(tg){ try{ await api(`/posts/${tg.dataset.cmpost}`,"PATCH",{bump_enabled:+tg.dataset.on}); toast(+tg.dataset.on?"Đã bật tự bình luận bài này":"Đã tắt tự bình luận bài này"); loadCm(true); }catch(err){ toast(err.message); } return; }
  const nw=e.target.closest("[data-cmnow]"); if(nw){ nw.disabled=true; try{ await api(`/posts/${nw.dataset.cmnow}/bump`,"POST"); toast("Sale sẽ bình luận bài này trong vài phút khi rảnh"); loadCm(true); }catch(err){ toast(err.message); nw.disabled=false; } } });

