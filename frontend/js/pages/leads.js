/* --------------------------------------------- khách hàng */
async function loadLeads(){
  ST.leads=await api("/leads");
  try{ ST.junk=await api("/junk"); }catch(e){ ST.junk=null; }
  renderJunk();
  const shown=ST.leads.filter(l=>ST.showJunk?l.status==="junk":l.status!=="junk");
  api("/posts/recent-posted").then(ps=>{ const sel=$("#lPost"); const cur=sel.value; sel.innerHTML='<option value="">Không rõ / khác</option>'+ps.map(p=>`<option value="${p.id}">#${p.id} · ${esc(p.group_name||"Trang cá nhân")} · ${fmtDate(p.posted_at)} · ${esc((p.title||"").slice(0,40))}</option>`).join(""); sel.value=cur; }).catch(()=>{});
  $("#pipe").innerHTML=Object.entries(LEAD_ST).map(([k,l])=>`<div><b class="num">${ST.leads.filter(x=>x.status===k).length}</b><span>${l}</span></div>`).join("");
  $("#leadRows").innerHTML=(shown.length?"":`<tr><td colspan="6" class="muted small">${ST.showJunk?"Chưa loại khách nào.":"Chưa có khách."}</td></tr>`)+shown.map(l=>`<tr class="click${ST.selLead===l.id?" sel":""}" data-l="${l.id}"><td><b>${esc(l.name)}</b><div class="small muted">${l.origin==="comment"?"Từ bình luận":esc(l.contact)}${l.business_type?` · ${esc(l.business_type)}`:""}</div></td><td>${l.phone?`<span class="phone">${esc(fmtPhone(l.phone))}</span>`:'<span class="muted small">Chưa có</span>'}</td><td class="small">${esc(l.need)}</td><td class="small">${esc(l.source)}</td><td class="num score" style="color:${l.score>=75?"var(--accent)":"inherit"}">${l.score}</td><td><span class="chip ${l.status==="ordered"?"ok":l.status==="lost"?"bad":l.status==="new"?"warn":l.status==="junk"?"junk":""}">${LEAD_ST[l.status]||"Data rác"}</span>${l.escalated_at&&!["ordered","lost"].includes(l.status)?`<span class="chip warn" style="margin-top:3px">${l.boss_status==="called"?"Sếp đã gọi":"Chờ sếp"}</span>`:""}</td></tr>`).join("");
  if(ST.selLead&&shown.some(l=>l.id===ST.selLead)) renderLead(); else { ST.selLead=null; $("#leadDetail").innerHTML='<div class="empty">Chọn một khách để Hà soạn tin nhắn.</div>'; }
}
function renderJunk(){
  const j=ST.junk, el=$("#junkCard"), tg=$("#junkToggle"); if(!j){ el.hidden=true; tg.hidden=true; return; }
  tg.hidden=!j.total&&!ST.showJunk; tg.textContent=ST.showJunk?"← Về danh sách khách":`🗑 Data rác đã loại (${j.total})`;
  if(!j.total){ el.hidden=true; return; } el.hidden=false;
  const R=j.reasons||{};
  el.innerHTML=`<div class="card-h"><h3>Mai ghi nhớ data rác</h3><span class="chip junk">${j.total} khách đã loại</span></div>
   <p class="small muted" style="margin:0">Lần tìm khách sau, Mai bỏ qua đúng các tài khoản, SĐT này và trừ điểm khách có dấu hiệu giống. Đã tự bỏ qua <b>${j.skipped||0}</b> lần.</p>
   <div class="jr">${(j.by_reason||[]).map(r=>`<span class="chip">${esc(R[r.reason]||r.reason)} · ${r.n}</span>`).join("")}</div>
   ${(j.patterns||[]).length?`<b class="small">Data rác hay có chữ (khách thường hiếm khi có):</b><ul class="jpat">${j.patterns.map(x=>`<li><span><b>“${esc(x.label||x.word)}”</b> <span class="small muted">${x.junk} khách rác · ${x.good} khách thường</span></span><span class="row"><button class="btn sm danger" data-jx="${esc(x.label||x.word)}" title="Thêm vào điều kiện loại của Mai">Loại hẳn</button><button class="btn sm" data-jd="${esc(x.word)}" title="Chữ này không phải dấu hiệu rác">Bỏ qua</button></span></li>`).join("")}</ul>
     <p class="small muted" style="margin:6px 0 0">Khách mới có các chữ này bị Mai trừ 25 điểm. Bấm <b>Loại hẳn</b> để không bao giờ đưa vào danh sách.</p>`
   :`<p class="small muted" style="margin:6px 0 0">Khi sếp loại thêm vài khách giống nhau (từ 3 khách), Mai tự tìm chữ chung để đề xuất loại.</p>`}`;
}
$("#junkToggle").onclick=()=>{ ST.showJunk=!ST.showJunk; ST.selLead=null; loadLeads(); };
$("#junkCard").addEventListener("click",async e=>{ const b=e.target.closest("[data-jx],[data-jd]"); if(!b) return; b.disabled=true;
  try{ if(b.dataset.jx){ await api("/junk/exclude","POST",{word:b.dataset.jx}); toast(`Mai sẽ loại hẳn khách có chữ “${b.dataset.jx}”`); }
       else { await api("/junk/dismiss","POST",{word:b.dataset.jd}); toast("Đã bỏ qua, Mai không coi chữ này là dấu hiệu rác"); } }catch(err){ toast(err.message); } loadLeads(); });
$("#leadRows").addEventListener("click",e=>{ const r=e.target.closest("[data-l]"); if(!r) return; ST.selLead=+r.dataset.l; loadLeads(); });
function renderLead(){
  const l=ST.leads.find(x=>x.id===ST.selLead); if(!l) return;
  if(l.status==="junk"){ const jr=((ST.junk||{}).items||[]).find(x=>x.lead_id===l.id)||{}; const RS=(ST.junk||{}).reasons||{};
    $("#leadDetail").innerHTML=`<div class="card-h"><h3>${esc(l.name)}</h3><span class="chip junk">Data rác</span></div>
     <div class="note"><b>Sếp đã loại:</b> ${esc(RS[jr.reason]||"Không phù hợp tệp khách")}${jr.note?` · ${esc(jr.note)}`:""}${jr.created_at?` <span class="muted small">(${fmtDate(jr.created_at)})</span>`:""}<br>Mai không đưa lại tài khoản, SĐT này và trừ điểm khách giống vậy.</div>
     <dl class="kv"><dt>Số điện thoại</dt><dd>${l.phone?esc(fmtPhone(l.phone)):"Chưa có"}</dd><dt>Liên hệ</dt><dd>${esc(l.contact)}</dd><dt>Nguồn</dt><dd>${esc(l.source)}</dd><dt>Nhu cầu</dt><dd>${esc(l.need)}</dd></dl>
     <div class="actions"><button class="btn" id="lUnjunk">Không phải rác, khôi phục</button></div>`;
    $("#lUnjunk").onclick=async()=>{ await api(`/leads/${l.id}/unjunk`,"POST"); toast("Đã khôi phục khách, Mai bỏ ghi nhớ"); ST.showJunk=false; loadLeads(); };
    return; }
  $("#leadDetail").innerHTML=`<div class="card-h"><h3>${esc(l.name)}</h3><span class="chip">${l.score} điểm</span></div>
   ${l.escalated_at?`<div class="note"><b>Đã chuyển cho sếp</b> ${fmtTime(l.escalated_at)} ${fmtDate(l.escalated_at)}: ${esc(l.escalate_reason||"")}${l.consult_note?`<br><br><b>Kịch bản Hà gợi ý:</b> ${esc(l.consult_note)}`:""}</div>`:""}
   <dl class="kv"><dt>Số điện thoại</dt><dd>${l.phone?`<span class="phone">${esc(fmtPhone(l.phone))}</span>`:"Chưa có"}</dd><dt>Liên hệ</dt><dd>${esc(l.contact)}</dd><dt>Kinh doanh</dt><dd>${esc(l.business_type)}</dd><dt>Nguồn</dt><dd>${esc(l.source)}</dd><dt>Nhu cầu</dt><dd>${esc(l.need)}</dd></dl>
   <form class="row" id="lOrder"><input type="text" class="grow" id="lAmt" inputmode="numeric" placeholder="Giá trị đơn, VD 2,5tr" aria-label="Giá trị đơn hàng"><button class="btn primary" type="submit">Ghi đơn hàng</button></form>
   <label class="f" for="lStatus">Trạng thái<select id="lStatus">${Object.entries(LEAD_ST).map(([k,v])=>`<option value="${k}" ${k===l.status?"selected":""}>${v}</option>`).join("")}</select></label>
   <div class="lostbox" id="lLost" ${l.status==="lost"?"":"hidden"}><span class="small"><b>Vì sao khách không mua?</b> ${l.lost_reason?`Đã ghi: ${esc(LOST_R[l.lost_reason]||l.lost_reason)}${l.lost_note?` — ${esc(l.lost_note)}`:""}`:'<span style="color:var(--honey)">Chưa chọn lý do</span>'}</span>
     <div class="reasons" id="lLr" style="margin-top:6px">${Object.entries(LOST_R).map(([k,v])=>`<button type="button" data-lr="${k}" class="${k===l.lost_reason?"on":""}">${esc(v)}</button>`).join("")}</div>
     <div class="row" style="margin-top:6px"><input type="text" class="grow" id="lLn" placeholder="Ghi thêm (không bắt buộc), VD: đang nhập trà ở xưởng khác" value="${esc(l.lost_note||"")}" aria-label="Ghi chú lý do"><button class="btn sm primary" type="button" id="lLgo" ${l.lost_reason?"":"disabled"}>Lưu lý do</button></div></div>
   <label class="f" for="lMsg">Khách vừa nhắn gì?<textarea id="lMsg" rows="3" placeholder="Dán tin nhắn của khách, để trống nếu muốn Hà nhắn chủ động"></textarea></label>
   <div class="actions"><button class="btn primary" id="lDraft">Hà soạn tin trả lời</button>${l.escalated_at?"":`<button class="btn" id="lEsc">Chuyển cho sếp qua Telegram</button>`}</div>
   <div id="lReply"></div>
   <details class="junkbox" id="lJunk"><summary>Loại bỏ: data rác, không hợp tệp khách</summary>
     <div class="stack"><span class="small muted">Vì sao không phù hợp? Mai ghi nhớ để lần sau tìm khách tự loại các trường hợp giống vậy.</span>
     <div class="reasons" id="lJr">${Object.entries((ST.junk||{}).reasons||{other:"Khác"}).map(([k,v])=>`<button type="button" data-jr="${k}">${esc(v)}</button>`).join("")}</div>
     <label class="f" for="lJn">Ghi chú cho Mai (không bắt buộc)<input type="text" id="lJn" placeholder="VD: bán mỹ phẩm, quần áo"></label>
     <div><button class="btn danger" id="lJgo" disabled>Loại bỏ và để Mai ghi nhớ</button></div></div></details>`;
  let jr=null;
  $("#lJr").onclick=e=>{ const b=e.target.closest("[data-jr]"); if(!b) return; jr=b.dataset.jr; $("#lJr").querySelectorAll("button").forEach(x=>x.classList.toggle("on",x===b)); $("#lJgo").disabled=false;
    $("#lJn").placeholder=jr==="wrong_niche"?"Ghi ngành hàng của họ, VD: mỹ phẩm, quần áo (Mai thêm vào điều kiện loại)":"VD: chỉ hỏi giá rồi im, bán đồ Quảng Châu…"; };
  $("#lJgo").onclick=async e=>{ e.target.disabled=true; try{ const r=await api(`/leads/${l.id}/junk`,"POST",{reason:jr,note:$("#lJn").value}); toast(`Đã loại ${l.name}. ${r.learned}`); ST.selLead=null; loadLeads(); refresh(); }catch(err){ toast(err.message); e.target.disabled=false; } };
  const esc2=$("#lEsc"); if(esc2) esc2.onclick=async()=>{ esc2.disabled=true; const r=await api(`/leads/${l.id}/escalate`,"POST"); toast(r.telegram?"Đã gửi phiếu khách kèm kịch bản tư vấn qua Telegram":"Đã chuyển cho sếp. Kết nối Telegram ở trang KPI & Báo cáo để nhận phiếu trên điện thoại."); loadLeads(); };
  $("#lOrder").addEventListener("submit",async ev=>{ ev.preventDefault(); const a=parseVnd($("#lAmt").value); if(a===null){ toast("Nhập giá trị đơn, ví dụ 2500000 hoặc 2,5tr"); return; }
    try{ await api(`/leads/${l.id}/order`,"POST",{amount:a}); toast(`Đã ghi đơn ${vnd(a)} cho ${l.name}`); }catch(err){ toast(err.message); } loadLeads(); refresh(); });
  let lr=l.lost_reason||null;
  $("#lLr").onclick=e=>{ const b=e.target.closest("[data-lr]"); if(!b) return; lr=b.dataset.lr; $("#lLr").querySelectorAll("button").forEach(x=>x.classList.toggle("on",x===b)); $("#lLgo").disabled=false; };
  $("#lLgo").onclick=async e=>{ e.target.disabled=true; try{ await api(`/leads/${l.id}/lost`,"POST",{reason:lr,note:$("#lLn").value}); toast("Đã ghi lý do. Cả đội sẽ rút kinh nghiệm từ lý do này"); loadLeads(); }catch(err){ toast(err.message); e.target.disabled=false; } };
  $("#lStatus").onchange=async e=>{ if(e.target.value==="lost"){ $("#lLost").hidden=false; toast("Chọn lý do khách không mua rồi bấm Lưu lý do"); return; } if(e.target.value==="ordered"){ e.target.value=l.status; $("#lAmt").focus(); toast("Nhập giá trị đơn rồi bấm Ghi đơn hàng để tính doanh thu"); return; } await api(`/leads/${l.id}`,"PATCH",{status:e.target.value}); toast("Đã cập nhật trạng thái"); loadLeads(); };
  $("#lDraft").onclick=async e=>{ e.target.disabled=true; e.target.textContent="Hà đang soạn…"; const r=await api(`/leads/${l.id}/reply`,"POST",{message:$("#lMsg").value});
    $("#lReply").innerHTML=`<label class="f" for="lReplyTxt">Tin nhắn đề xuất (sửa được)<textarea id="lReplyTxt" rows="7">${esc(r.reply)}</textarea></label><div class="actions"><button class="btn" id="lCopy">Sao chép</button><button class="btn primary" id="lSent">Đã gửi cho khách</button></div>`;
    $("#lCopy").onclick=()=>copyText($("#lReplyTxt").value);
    $("#lSent").onclick=async()=>{ if(r.reply_id) await api(`/replies/${r.reply_id}/sent`,"POST",{text:$("#lReplyTxt").value}); await api(`/leads/${l.id}`,"PATCH",{status:l.status==="new"?"contacted":l.status,contacted:true}); toast("Đã ghi nhận. Khi khách chốt hoặc từ chối, Hà sẽ học từ tin nhắn này."); loadLeads(); };
    e.target.disabled=false; e.target.textContent="Soạn lại"; };
}
$("#leadForm").addEventListener("submit",async e=>{ e.preventDefault(); await api("/leads","POST",{name:$("#lName").value,contact:$("#lContact").value,post_id:+$("#lPost").value||null,business_type:$("#lType").value,need:$("#lNeed").value}); const fromPost=!!$("#lPost").value; e.target.reset(); toast(fromPost?"Đã thêm khách và ghi công cho bài đăng nguồn":"Đã thêm khách, Hà đã chấm điểm"); loadLeads(); refresh(); });

