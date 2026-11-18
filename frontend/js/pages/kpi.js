/* --------------------------------------------- KPI & Telegram */
function kpiHero(k,pace,extra=""){
  const mx=Math.max(k.target_max,k.leads_phone,1); const w=v=>Math.min(100,v/mx*100);
  const st=k.exceeded?["ok","Vượt KPI"]:k.achieved?["ok","Đạt KPI"]:pace&&pace.behind?["bad","Đang chậm tiến độ"]:["warn","Đang thực hiện"];
  return `<div><span class="small muted">KPI hôm nay · khách có SĐT</span><div class="big">${k.leads_phone}<small> / ${k.target_min}</small></div></div>
    <div><div class="kbar"><i class="${k.achieved?"ok":""}" style="width:${w(k.leads_phone)}%"></i><div class="mk" style="left:${w(k.target_min)}%"><span>Tối thiểu ${k.target_min}</span></div><div class="mk end" style="left:calc(${w(k.target_max)}% - 2px)"><span>Vượt ${k.target_max}</span></div></div>
      <p class="small muted" style="margin-top:22px">${k.leads_total} khách mới (${k.from_comments} từ bình luận) · đã xin SĐT ${k.asked_phone} người · chuyển sếp ${k.escalated} · đang chờ sếp ${k.boss_pending}${pace&&pace.expected?` · lúc này nên có ~${pace.expected}`:""}</p></div>
    <div style="text-align:right"><span class="chip ${st[0]}">${st[1]}</span>${extra}</div>`;
}
const fmtPhone=p=>p&&p.length===10?`${p.slice(0,4)} ${p.slice(4,7)} ${p.slice(7)}`:(p||"");
async function loadTeam(){
  let list; try{ list=await api("/agents"); }catch(e){ return; }
  list.forEach(a=>{ AGENT[a.id]={...(AGENT[a.id]||{}),...a}; });
  $("#teamList").innerHTML=list.filter(a=>!a.sample).map(a=>`<li data-tm="${a.id}">${avaHtml(a.id,48)}<div class="tl-main">
      <div class="small muted">${esc(a.role||"")}${a.default_name&&a.default_name!==a.name?` · tên gốc ${esc(a.default_name)}`:""}</div>
      <input type="text" maxlength="20" value="${esc(a.name)}" aria-label="Tên của ${esc(a.name)}" data-tmname>
      <div class="tl-act"><button class="btn sm primary" type="button" data-tmsave>Lưu tên</button>
        <label class="btn sm" style="cursor:pointer">${a.face?"Đổi ảnh mặt":"Tải ảnh mặt"}<input type="file" accept="image/*" hidden data-tmface></label>
        ${a.face||(a.default_name&&a.default_name!==a.name)?`<button class="btn sm ghost" type="button" data-tmreset>Về mặc định</button>`:""}</div></div></li>`).join("");
}
function shrinkImage(file,max=640){ return new Promise((ok,bad)=>{ const r=new FileReader(); r.onerror=()=>bad(new Error("Không đọc được ảnh"));
  r.onload=()=>{ const im=new Image(); im.onerror=()=>bad(new Error("Không đọc được ảnh. Chọn ảnh JPG, PNG hoặc WEBP"));
    im.onload=()=>{ if(Math.min(im.width,im.height)<48){ bad(new Error("Ảnh quá nhỏ, chọn ảnh từ 48×48 điểm ảnh trở lên")); return; }
      const side=Math.min(im.width,im.height), sx=(im.width-side)/2, sy=Math.max(0,(im.height-side)*0.4), out=Math.min(max,side);
      const cv=document.createElement("canvas"); cv.width=cv.height=out;  // cắt vuông giữa ảnh, lệch lên để giữ mặt
      cv.getContext("2d").drawImage(im,sx,sy,side,side,0,0,out,out); ok(cv.toDataURL("image/jpeg",0.88)); }; im.src=r.result; }; r.readAsDataURL(file); }); }
$("#teamList").addEventListener("click",async e=>{ const li=e.target.closest("[data-tm]"); if(!li) return; const id=li.dataset.tm;
  if(e.target.closest("[data-tmsave]")){ try{ const r=await api(`/agents/${id}`,"PUT",{name:li.querySelector("[data-tmname]").value}); toast(`Đã đổi tên thành ${r.name}`); }catch(err){ toast(err.message); } loadTeam(); refresh(); }
  if(e.target.closest("[data-tmreset]")){ await api(`/agents/${id}/profile`,"DELETE"); toast("Đã trả về tên và mặt mặc định"); loadTeam(); refresh(); } });
$("#teamList").addEventListener("change",async e=>{ const inp=e.target.closest("[data-tmface]"); if(!inp||!inp.files[0]) return; const id=inp.closest("[data-tm]").dataset.tm;
  try{ const url=await shrinkImage(inp.files[0],400); await api(`/agents/${id}`,"PUT",{face:url}); toast("Đã đổi ảnh mặt"); }catch(err){ toast(err.message); } loadTeam(); refresh(); });
async function loadFunnel(){
  let d; try{ d=await api(`/funnel?days=${$("#fnDays").value||30}`); }catch(e){ return; }
  const T=d.total, pct=(a,b)=>b?Math.round(a/b*100)+"%":"—";
  if(!d.channels.length){ $("#fnBody").innerHTML='<p class="muted small">Chưa có khách trong khoảng này.</p>'; return; }
  $("#fnBody").innerHTML=`<div class="tbl-wrap"><table class="fn-tbl" style="min-width:560px"><thead><tr><th>Kênh</th><th class="num">SĐT</th><th class="num">Sếp đã gọi</th><th class="num">Chốt</th><th class="num">Không mua</th><th class="num">Doanh thu</th></tr></thead><tbody>
    ${d.channels.map(c=>`<tr><td>${esc(c.label)}</td><td class="num"><b>${c.phones}</b><span class="fn-rate">${c.leads} khách</span></td><td class="num">${c.called}<span class="fn-rate">${pct(c.called,c.phones)} số</span></td><td class="num"><b>${c.won}</b><span class="fn-rate">${pct(c.won,c.called)} đã gọi</span></td><td class="num">${c.lost}${c.lost_noreason?`<span class="fn-rate" style="color:var(--honey)">${c.lost_noreason} chưa lý do</span>`:""}</td><td class="num">${c.revenue?vnd(c.revenue):"—"}</td></tr>`).join("")}
    <tr><td><b>Tổng</b></td><td class="num"><b>${T.phones}</b></td><td class="num"><b>${T.called}</b></td><td class="num"><b>${T.won}</b></td><td class="num"><b>${T.lost}</b></td><td class="num"><b>${T.revenue?vnd(T.revenue):"—"}</b></td></tr></tbody></table></div>
    <p class="small" style="margin-top:8px">Chi phí AI ${d.days} ngày: <b>${vnd(d.ai_vnd)}</b> · ${d.per_phone!=null?`${vnd(d.per_phone)}/SĐT`:"chưa có SĐT"} · ${d.per_order!=null?`<b>${vnd(d.per_order)}/đơn</b>`:"chưa có đơn"}</p>
    ${d.reasons.length?`<div class="small"><b>Khách không mua vì</b><div class="fn-rs">${d.reasons.map(r=>`<span class="chip" title="${esc(Object.entries(r.by_channel).map(([k,n])=>`${d.channel_names[k]||k}: ${n}`).join(" · "))}">${esc(r.label)} · ${r.n}</span>`).join("")}</div>
      <p class="muted" style="margin-top:6px">Lý do được đưa vào lời dặn của Mai, Lan, Hà, CEO và Minh để đổi cách tìm khách, viết bài, tư vấn.</p></div>`
      :`<p class="small muted">Chưa có khách không mua nào được ghi lý do. Bấm “Không mua” trên Telegram hoặc trang Khách hàng rồi chọn lý do.</p>`}
    ${T.lost_noreason?`<p class="small" style="color:var(--honey)">${T.lost_noreason} khách không mua chưa ghi lý do: mở khách ở trang Khách hàng để chọn.</p>`:""}`;
}
$("#fnDays").onchange=loadFunnel;
const FC_V={good:["ok","Ra đơn"],weak:["bad","Chưa ra đơn"],call:["warn","Cần gọi thêm"],wait:["","Chưa đủ dữ liệu"]};
async function loadFocus(d){
  if(!d){ try{ d=await api("/focus"); }catch(e){ return; } }
  $("#fcMode").textContent=d.mode==="approve"?"Chờ sếp duyệt":"CEO tự quyết"; $("#fcOn").checked=d.enabled;
  $("#fcIntro").textContent=`CEO xem ${d.days} ngày gần nhất: kênh có từ ${d.min_phones} SĐT và sếp đã gọi từ ${d.min_called} khách mà chưa ra đơn thì tạm dừng 30 ngày rồi tự thử lại; kênh ra đơn thì được dồn thêm sức (đọc thêm nhóm, xem thêm trang mỗi lượt, trong giới hạn an toàn). Đăng bài nhóm không bao giờ tự dừng.${d.last?` Lần xem gần nhất: ${fmtDate(d.last)}.`:""}`;
  $("#fcList").innerHTML=d.channels.length?d.channels.map(c=>{ const [cl,tx]=FC_V[c.verdict]||["",""];
    return `<li><div><b>${esc(c.label)}</b><span class="small muted">${esc(c.text)}</span>${c.paused_until?`<span class="small" style="color:var(--honey)">Đang tạm dừng tới ${fmtDate(c.paused_until)}</span>`:""}</div>
      ${c.paused_until?`<button class="btn sm" type="button" data-fcres="${c.key}">Chạy lại</button>`:`<span class="chip ${cl}">${tx}</span>`}</li>`; }).join(""):'<li class="muted small">Chưa có khách trong khoảng này.</li>';
  const pr=(d.proposed||[])[0];
  $("#fcProp").innerHTML=pr?`<div class="note warn" style="margin-top:8px"><b>${esc(pr.title)}</b><br>${esc(pr.reason)}<div class="actions" style="margin-top:6px"><button class="btn sm primary" type="button" data-fcok="${pr.id}">Duyệt</button><button class="btn sm" type="button" data-fcno="${pr.id}">Không</button></div></div>`
    :(d.plan||[]).length?`<p class="small" style="margin-top:8px">Lần xem tới CEO sẽ: ${d.plan.map(a=>`${a.op==="pause"?"tạm dừng":"dồn sức cho"} “${esc(a.label)}”`).join("; ")}.</p>`:"";
}
$("#fcRun").onclick=async e=>{ e.target.disabled=true; try{ const r=await api("/focus/run","POST"); toast(r.proposed?"CEO đã gửi đề xuất, sếp duyệt ngay bên dưới":r.done.length?r.done.join(". "):"Chưa có kênh nào đủ dữ liệu để dừng hay dồn sức"); loadFocus(r); }catch(err){ toast(err.message); } e.target.disabled=false; };
$("#fcOn").onchange=async e=>{ loadFocus(await api("/focus/settings","PUT",{enabled:e.target.checked})); };
$("#fcCard").addEventListener("click",async e=>{ let b;
  if((b=e.target.closest("[data-fcres]"))){ loadFocus(await api(`/focus/resume/${b.dataset.fcres}`,"POST")); toast("Đã cho kênh chạy lại"); }
  else if((b=e.target.closest("[data-fcok],[data-fcno]"))){ const ok=!!b.dataset.fcok; try{ await api(`/ceo/decisions/${b.dataset.fcok||b.dataset.fcno}`,"POST",{approve:ok}); toast(ok?"Đã duyệt, CEO làm ngay":"Đã bỏ đề xuất"); }catch(err){ toast(err.message); } loadFocus(); } });
async function loadKpi(){
  loadFunnel(); loadFocus();
  const [d,s,tg]=await Promise.all([api("/kpi"),api("/settings"),api("/telegram")]);
  $("#kpiHero").innerHTML=kpiHero(d.today,d.pace);
  $("#kStreak").textContent=d.streak?`Đạt KPI liên tiếp ${d.streak} ngày`:"";
  const mx=Math.max(...d.history.map(h=>Math.max(h.leads_phone,h.target_min)),1);
  $("#kHist").innerHTML=d.history.map(h=>`<div class="col2" title="${fmtDate(h.date)}: ${h.leads_phone}/${h.target_min} khách có SĐT"><span>${h.leads_phone}</span><div class="b ${h.leads_phone>=h.target_min?"ok":""}" style="height:${h.leads_phone/mx*80}%"></div><span>${h.date.slice(8,10)}</span></div>`).join("")+`<div class="line" style="bottom:calc(${d.today.target_min/mx*80}% + 18px)" title="KPI tối thiểu"></div>`;
  $("#kSales").innerHTML=d.per_sale.length?d.per_sale.map(r=>`<tr><td><b>${esc(r.name)}</b>${r.active?"":' <span class="chip">Tạm dừng</span>'}</td><td class="num"><b style="color:${r.active&&r.leads_phone>=r.target_min?"var(--accent)":"inherit"}">${r.leads_phone}</b> / ${r.target_min}</td><td class="num">${r.leads}</td><td class="num">${r.asked}</td><td class="num">${r.posts}</td><td class="num">${r.bumps}</td></tr>`).join(""):'<tr><td colspan="6" class="muted">Chưa có nhân viên sale.</td></tr>';
  if(!$("#kpiForm").contains(document.activeElement)){
    $("#kMin").value=s.kpi_min; $("#kMax").value=s.kpi_max; $("#kCheck").value=s.kpi_check_time; $("#kEscPhone").checked=s.escalate_all_phone==="1"; $("#kEscCx").checked=s.escalate_complex==="1";
    $("#kEscH").value=s.escalate_after_hours; $("#kScan").checked=s.scan_enabled==="1"; $("#kScanT").value=s.scan_times; $("#kScanAge").value=s.scan_max_age_days;
    $("#kReply").checked=s.auto_reply_comments==="1"; $("#kReplyMax").value=s.reply_max_per_nick; $("#kReplyT").value=s.reply_texts; }
  if(!$("#tgForm").contains(document.activeElement)){
    $("#tgToken").value=s.tg_token||""; $("#tgM").value=s.tg_morning; $("#tgE").value=s.tg_evening; $("#tgL").checked=s.tg_alert_leads==="1"; $("#tgK").checked=s.tg_alert_kpi==="1"; $("#tgN").checked=s.tg_alert_nick==="1"; }
  showTg(tg);
  const boss=(await api("/leads")).filter(l=>l.escalated_at&&!["won","lost","called"].includes(l.boss_status||"")&&!["ordered","lost"].includes(l.status));
  $("#kBoss").innerHTML=boss.length?boss.slice(0,8).map(l=>`<li><span class="phone">${esc(fmtPhone(l.phone)||"—")}</span><b>${esc(l.name)}</b><span class="muted small">${esc(l.escalate_reason||"")}</span></li>`).join(""):'<li class="muted">Không có khách nào đang chờ sếp.</li>';
}
function showTg(t){
  const st=!t.has_token?["","Chưa có token"]:t.error?["bad","Lỗi kết nối"]:t.chats?["ok",`Đã kết nối ${t.chats} chat`]:["warn","Chờ ghép nối"];
  $("#tgState").className="chip "+st[0]; $("#tgState").textContent=st[1];
  $("#tgPair").innerHTML=t.error?`<div class="err">${esc(t.error)}</div>`:t.pair_code?`<div class="note">Mở <b>@${esc(t.bot||"bot của bạn")}</b> trên Telegram và gửi mã:<div class="tg-code" style="margin-top:6px">${esc(t.pair_code)}</div></div>`:t.bot?`<p class="small muted">Bot: <b>@${esc(t.bot)}</b></p>`:"";
}
$("#tgForm").addEventListener("submit",async e=>{ e.preventDefault(); const k=$("#tgToken").value.trim(); if(!k||k==="••••••"){ toast("Dán token bot Telegram vào ô trước"); return; }
  try{ const t=await api("/telegram/token","POST",{token:k}); $("#tgToken").value="••••••"; toast(`Token đúng: bot @${t.bot}`); showTg(t); }catch(err){ toast(err.message); } });
$("#tgPairBtn").onclick=async()=>{ try{ showTg(await api("/telegram/pair","POST")); toast("Gửi mã này cho bot trên Telegram"); }catch(err){ toast(err.message); } };
$("#tgTest").onclick=async()=>{ try{ await api("/telegram/send","POST",{kind:"test"}); toast("Đã gửi tin thử. Kiểm tra Telegram."); }catch(err){ toast(err.message); } };
$("#tgNow").onclick=async()=>{ try{ await api("/telegram/send","POST",{kind:"evening"}); toast("Đã gửi báo cáo qua Telegram"); }catch(err){ toast(err.message); } };
$("#tgUnlink").onclick=async e=>{ const b=e.target; if(b.dataset.confirm!=="1"){ b.dataset.confirm="1"; b.textContent="Bấm lần nữa để hủy"; return; } b.dataset.confirm=""; b.textContent="Hủy ghép nối"; showTg(await api("/telegram/unlink","POST")); toast("Đã hủy ghép nối Telegram"); };
$("#tgSave").onclick=async()=>{ await api("/settings","PUT",{tg_morning:$("#tgM").value,tg_evening:$("#tgE").value,tg_alert_leads:$("#tgL").checked?"1":"0",tg_alert_kpi:$("#tgK").checked?"1":"0",tg_alert_nick:$("#tgN").checked?"1":"0"}); toast("Đã lưu cài đặt báo cáo"); };
$("#kpiForm").addEventListener("submit",async e=>{ e.preventDefault();
  if(+$("#kMax").value < +$("#kMin").value){ toast("Mục tiêu vượt phải lớn hơn hoặc bằng mức tối thiểu"); return; }
  await api("/settings","PUT",{kpi_min:$("#kMin").value,kpi_max:$("#kMax").value,kpi_check_time:$("#kCheck").value,escalate_all_phone:$("#kEscPhone").checked?"1":"0",escalate_complex:$("#kEscCx").checked?"1":"0",escalate_after_hours:$("#kEscH").value||"0",scan_enabled:$("#kScan").checked?"1":"0",scan_times:$("#kScanT").value.replace(/\s/g,""),scan_max_age_days:$("#kScanAge").value,auto_reply_comments:$("#kReply").checked?"1":"0",reply_max_per_nick:$("#kReplyMax").value,reply_texts:$("#kReplyT").value});
  document.activeElement.blur(); toast("Đã lưu KPI"); loadKpi(); refresh(); });
$("#btnScan").onclick=async()=>{ const r=await api("/scan/now","POST"); toast(r.posts?`Các nick đang đọc bình luận ${r.posts} bài để tìm khách`:"Chưa có bài nào đã lưu link để quét (cần nick đã đăng nhập và bài đã đăng)"); };

