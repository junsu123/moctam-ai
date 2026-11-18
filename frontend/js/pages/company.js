/* --------------------------------------------- công ty */
const vnd=n=>`${Math.round(n||0).toLocaleString("vi-VN")}đ`;
const parseVnd=t=>{ t=String(t||"").toLowerCase().replace(/\s|đ|vnd/g,""); let m;
  if((m=t.match(/^(\d+)(tr|triệu|trieu)(\d{1,3})?$/))) return +m[1]*1e6+(m[3]?+m[3].padEnd(3,"0")*1000:0);
  if((m=t.match(/^(\d+(?:[.,]\d+)?)(tr|triệu|trieu|m)$/))) return Math.round(parseFloat(m[1].replace(",","."))*1e6);
  if((m=t.match(/^(\d+(?:[.,]\d+)?)(k|nghìn|ngàn)$/))) return Math.round(parseFloat(m[1].replace(",","."))*1000);
  const d=t.replace(/[.,]/g,""); return /^\d+$/.test(d)&&+d>0?+d:null; };
const RISK={waiting:["risk-warn","Chờ sếp đăng nhập nick"],new:["","Mới vào kỳ (7 ngày đầu)"],safe:["risk-safe","An toàn"],warn:["risk-warn","Cần cố gắng"],danger:["risk-danger","Nguy cơ bị sa thải"],idle:["","Chưa có ngày làm việc"],extend:["","Kéo dài kỳ (thiếu ngày làm việc)"],pass:["risk-safe","Đạt, chờ đánh giá"],fail:["risk-danger","Sẽ bị sa thải"]};
const RULES=`<ol class="rules"><li>Mỗi nhân viên sale giữ nick phải tìm được khách. Mỗi kỳ 30 ngày phải đạt chỉ tiêu <b>khách có SĐT</b> từ bài của nick mình, không đạt thì bị <b>sa thải</b>.</li>
  <li>Chỉ tiêu tháng = tổng chỉ tiêu của những ngày nick làm việc được. Ngày nick bị lỗi đăng nhập hay sếp tạm dừng không bị tính; kỳ có dưới 15 ngày làm việc được kéo dài.</li>
  <li>Toàn bộ nhân viên sale bị sa thải thì công ty <b>giải thể</b>.</li>
  <li>Sau <b>60 ngày</b> chưa có khách chốt đơn và chưa có doanh thu thì công ty <b>giải thể</b>.</li>
  <li>Vốn chỉ dùng để <b>nuôi các agent</b>: chi phí gọi API Claude (viết bài, họp, tư vấn, tự học), quy đổi từ USD. Chi phí hàng hóa, giao hàng của đơn không tính ở đây. Hết vốn thì việc gọi AI tạm dừng tới khi bơm thêm.</li>
  <li><b>Doanh thu do sếp nhập</b>, vì sếp là người chốt và làm việc với khách.</li>
  <li><b>Sếp chỉ giao việc cho CEO</b>: CEO tự chia việc cho các agent, tự duyệt bài nháp, tự xếp lịch và báo lại. Agent nào làm chưa đúng, sếp nói CEO sửa. Bật/tắt luật này ở khung CEO.</li>
  <li><b>CEO Đức điều hành nhân sự</b>: thực hiện sa thải theo luật, quyết định có tuyển người thay vào nick cũ, tăng sale khi doanh thu chạm mốc hoặc khi tìm khách trên Facebook cho thấy còn tiềm năng. Sale mới cần sếp đăng nhập một nick Facebook; kỳ KPI tính từ ngày nick chạy.</li>
  <li>Đội lõi (CEO Đức, Minh, Lan, Tuấn, Hà, Khoa) không bị sa thải theo KPI, chỉ giải tán khi công ty giải thể.</li></ol>`;
async function loadCompany(){
  const [c,o]=await Promise.all([api("/company"),api("/ceo").catch(()=>null)]); ST.company=c; ST.ceo=o; const f=c.finance; const body=$("#coBody");
  const chip={setup:["warn","Chưa thành lập"],active:["ok",`Đang hoạt động · ngày ${c.day}/${c.trial_days}`],dissolved:["bad","Đã giải thể"]}[c.status];
  $("#coState").className="chip "+chip[0]; $("#coState").textContent=chip[1];
  if(document.activeElement&&body.contains(document.activeElement)&&document.activeElement.tagName==="INPUT") return;
  if(c.status!=="active"){
    body.innerHTML=`<div class="learn-top"><form class="card" id="foundForm">
        ${c.status==="dissolved"?`<div class="err"><b>Công ty đã giải thể</b> ${c.dissolved_at?`ngày ${fmtDate(c.dissolved_at)}`:""}: ${esc(c.dissolved_reason||"")}</div>
          <p class="small muted">Kết quả: vốn ${vnd(f.capital)}, chi phí nuôi agent ${vnd(f.spent)}, doanh thu ${vnd(f.revenue)} (${f.orders} đơn).</p>`:""}
        <h3>${c.status==="dissolved"?"Thành lập lại công ty":"Thành lập công ty"}</h3>
        <p class="small muted">Từ ngày thành lập, luật KPI và thời hạn 60 ngày bắt đầu tính. Nên dọn dữ liệu thử nghiệm trước (Cài đặt → Bắt đầu chạy thật).</p>
        <div class="grid2"><label class="f" for="coCap">Vốn ban đầu (đồng)<input type="text" id="coCap" value="10.000.000" inputmode="numeric"></label>
          <label class="f" for="coRate">Tỷ giá USD → VND (để quy đổi chi phí AI)<input type="number" id="coRate" value="${f.rate||25800}" min="1"></label></div>
        <div><button class="btn primary" type="submit">${c.status==="dissolved"?"Thành lập lại":"Thành lập công ty"}</button></div>
      </form><div class="card"><h3>Luật của công ty</h3>${RULES}</div></div>`;
    $("#foundForm").addEventListener("submit",async e=>{ e.preventDefault(); const cap=parseVnd($("#coCap").value);
      if(cap===null){ toast("Nhập vốn bằng số, ví dụ 10.000.000 hoặc 10tr"); return; }
      try{ await api("/company/found","POST",{capital:cap,usd_vnd:+$("#coRate").value||null}); toast(`Công ty đã thành lập với vốn ${vnd(cap)}`); }catch(err){ toast(err.message); }
      loadCompany(); refresh(); });
    return;
  }
  const leftPct=f.capital?Math.max(0,Math.min(100,f.left/f.capital*100)):0;
  const dleft=Math.max(0,c.trial_days-c.day+1);
  body.innerHTML=`<div class="co-tiles">
      <div class="co-tile"><span class="l">Vốn còn lại</span><span class="v" style="color:${f.left<=0?"var(--danger)":leftPct<20?"var(--honey)":"inherit"}">${vnd(f.left)}</span><div class="bar"><i class="${leftPct<20?"bad":leftPct<50?"warn":""}" style="width:${leftPct}%"></i></div><span class="l">trên ${vnd(f.capital)} vốn${f.runway_days!=null?` · ${f.runway_days>365?"đủ hơn 1 năm":`đủ ~${f.runway_days} ngày nữa`}`:""}</span></div>
      <div class="co-tile"><span class="l">Chi phí nuôi agent</span><span class="v">${vnd(f.spent)}</span><span class="l">API Claude $${f.ai_usd} · trung bình ${vnd(f.avg_day)}/ngày</span></div>
      <div class="co-tile"><span class="l">Doanh thu (sếp nhập)</span><span class="v" style="color:${f.revenue?"var(--accent)":"inherit"}">${vnd(f.revenue)}</span><span class="l">${f.orders} đơn · ${f.customers} khách mua</span></div>
      <div class="co-tile"><span class="l">Thời hạn 60 ngày</span><span class="v">${f.orders?"Đã đạt":`Còn ${dleft} ngày`}</span><span class="l">${f.orders?"Đã có khách chốt đơn, không bị giải thể vì thời hạn":"Cần ít nhất 1 khách chốt đơn có doanh thu"}</span></div>
    </div>
    ${o?ceoBlock(o):""}
    <div class="learn-top">
      <div class="sidecol">
        <div class="tbl-wrap"><table style="min-width:560px"><thead><tr><th>Nhân viên sale</th><th>Kỳ đánh giá</th><th class="num">Khách có SĐT / chỉ tiêu</th><th>Tình trạng</th></tr></thead><tbody>
          ${c.sales.length?c.sales.map(r=>{ if(r.status==="fired") return `<tr><td><b>${esc(r.name)}</b><div class="small muted">${esc(r.fb_name||"")}</div></td><td colspan="2" class="small muted">${esc(r.fire_reason||"")}</td><td><span class="chip bad">Đã nghỉ việc</span><div class="row" style="margin-top:6px"><input type="text" id="rp-${r.id}" placeholder="Tên (không bắt buộc)" style="padding:4px 8px;font-size:12.5px;width:150px"><button class="btn sm" type="button" data-replace="${r.id}">Tuyển thay, giữ nick</button></div></td></tr>`;
            const v=r.review; const [cls,txt]=RISK[v.risk]||["",v.risk];
            if(v.risk==="waiting") return `<tr><td><b>${esc(r.name)}</b><div class="small muted">${r.hired_by==="ceo"?"CEO tuyển":"Chưa có nick"}</div></td><td colspan="2" class="small muted">Kỳ KPI chưa bắt đầu: tính từ ngày nick chạy được.</td><td><b class="${cls}">${txt}</b><div class="small"><a href="#sales">Đăng nhập nick →</a></div></td></tr>`;
            return `<tr><td><b>${esc(r.name)}</b><div class="small muted">${esc(r.fb_name||"")}${r.hired_by==="ceo"?" · CEO tuyển":""}</div></td><td>Ngày ${Math.min(v.day,30)}/30<div class="small muted">${v.work_days} ngày làm việc</div></td><td class="num"><b>${v.leads_phone}</b> / ${v.target_so_far}<div class="small muted">dự kiến cả tháng ~${v.target_month}</div></td><td><b class="${cls}">${txt}</b>${v.target_so_far?`<div class="small muted">${v.pct}% chỉ tiêu tới hôm nay</div>`:""}</td></tr>`; }).join(""):'<tr><td colspan="4" class="muted">Chưa có nhân viên sale. Tuyển ở trang Nhân viên sale.</td></tr>'}
        </tbody></table></div>
        <form class="card" id="revForm"><h3>Nhập doanh thu</h3><p class="small muted" style="margin-top:-4px">Sếp chốt khách thì ghi ở đây, trên Telegram (<code>/doanhthu 2tr5 Tên khách</code>) hoặc ở trang Khách hàng.</p>
          <div class="grid3"><label class="f" for="rvAmt">Số tiền<input type="text" id="rvAmt" inputmode="numeric" placeholder="VD 2tr5" required></label>
            <label class="f" for="rvCus">Khách (tên hoặc SĐT)<input type="text" id="rvCus" placeholder="Không bắt buộc"></label>
            <label class="f" for="rvNote">Ghi chú<input type="text" id="rvNote" placeholder="VD 50 hũ ngũ cốc"></label></div>
          <div><button class="btn primary" type="submit">Ghi doanh thu</button></div>
          <ul class="recent">${c.orders.length?c.orders.map(o=>`<li><b class="num">${vnd(o.amount)}</b><span>${esc(o.lead_name||"Khách lẻ")}</span><span class="muted small">${fmtDate(o.created_at)}${o.via==="telegram"?" · Telegram":""}</span>${o.note&&o.note!=="Sếp nhập qua Telegram"?`<span class="muted small">${esc(o.note)}</span>`:""}<button type="button" class="btn sm ghost danger" data-delorder="${o.id}" aria-label="Xóa khoản doanh thu">Xóa</button></li>`).join(""):'<li class="muted">Chưa có doanh thu nào.</li>'}</ul></form>
      </div>
      <div class="sidecol">
        <div class="card"><h3>Chi phí nuôi agent</h3><p class="small muted" style="margin-top:-4px">Tự tính từ mỗi lần agent gọi API Claude, tỷ giá ${vnd(f.rate)}/USD.</p>
          ${f.by_task.length?(()=>{ const mx=Math.max(...f.by_task.map(t=>t.vnd),1); return `<ul class="costs">${f.by_task.map(t=>`<li><span>${esc(t.label)}</span><b class="num">${vnd(t.vnd)}</b><div class="bar"><i style="width:${Math.max(2,t.vnd/mx*100)}%"></i></div><span class="muted small">${t.calls} lần gọi</span></li>`).join("")}</ul>`; })():'<p class="muted small">Chưa có chi phí. Khi agent viết bài, họp, tư vấn hay tự học bằng Claude, chi phí sẽ hiện ở đây.</p>'}
          ${f.last7.some(d=>d.vnd)?(()=>{ const mx=Math.max(...f.last7.map(d=>d.vnd),1); return `<div class="small muted" style="margin-top:6px">7 ngày gần nhất</div><div class="spark7" role="img" aria-label="Chi phí 7 ngày gần nhất">${f.last7.map(d=>`<div title="${fmtDate(d.date)}: ${vnd(d.vnd)}"><i style="height:${d.vnd?Math.max(4,d.vnd/mx*100):0}%"></i><span>${d.date.slice(8)}</span></div>`).join("")}</div>`; })():""}
          <p class="small muted">Ảnh sản phẩm lấy từ thư mục ảnh của sếp nên không tốn phí; phần mềm hiện không gọi API tạo ảnh.</p>
        </div>
        <form class="card" id="capForm"><h3>Bơm thêm vốn</h3><div class="row"><input type="text" class="grow" id="capAmt" inputmode="numeric" placeholder="VD 5tr" aria-label="Số vốn bơm thêm"><button class="btn" type="submit">Bơm vốn</button></div></form>
        <div class="card"><h3>Luật của công ty</h3>${RULES}</div>
      </div>
    </div>`;
  renderOrders();
  $("#revForm").addEventListener("submit",async e=>{ e.preventDefault(); const a=parseVnd($("#rvAmt").value); if(a===null){ toast("Nhập số tiền, ví dụ 2500000 hoặc 2tr5"); return; }
    try{ await api("/company/revenue","POST",{amount:a,customer:$("#rvCus").value,note:$("#rvNote").value}); toast(`Đã ghi doanh thu ${vnd(a)}`); }catch(err){ toast(err.message); } loadCompany(); refresh(); });
  $("#capForm").addEventListener("submit",async e=>{ e.preventDefault(); const a=parseVnd($("#capAmt").value); if(a===null){ toast("Nhập số tiền, ví dụ 5000000 hoặc 5tr"); return; }
    await api("/company/capital","POST",{amount:a}); toast(`Đã bơm thêm ${vnd(a)}`); loadCompany(); refresh(); });
}
function confirmInline(btn){ // bấm 2 lần để xóa, tránh xóa nhầm
  if(btn.dataset.armed) return true; btn.dataset.armed="1"; const t=btn.textContent; btn.textContent="Bấm lần nữa để xóa";
  setTimeout(()=>{ if(btn.isConnected){ delete btn.dataset.armed; btn.textContent=t; } },3000); return false; }
$("#coBody").addEventListener("click",async e=>{
  const d=e.target.closest("[data-delorder]"); if(d){ if(!confirmInline(d)) return; await api(`/orders/${d.dataset.delorder}`,"DELETE"); toast("Đã xóa khoản doanh thu"); return loadCompany(); }
  const r=e.target.closest("[data-replace]"); if(r){ const id=r.dataset.replace; const name=$(`#rp-${id}`).value.trim();
    try{ await api(`/sales/${id}/replace`,"POST",{name}); toast(`${name||"Người mới"} đã tiếp quản nick, không cần đăng nhập lại`); }catch(err){ toast(err.message); } loadCompany(); refresh(); }
});
const DKIND={fire:"🚪",replace:"🔁",hire:"👔",keep_slot:"⏸",hold:"✋",review:"🔎"};
function ceoBlock(o){
  const p=o.potential, hc=o.headcount, rev=o.revenue;
  const chk=x=>`<li class="${x.ok?"ok":"no"}"><span aria-hidden="true">${x.ok?"✓":"✗"}</span><div>${esc(x.label)}<div class="small muted">${esc(x.value)}</div></div></li>`;
  return `<section class="card ceo">
    <div class="ceo-h"><div class="row">${avaHtml("ceo")}<div><h3>CEO ${esc(o.name)} · điều hành nhân sự</h3><span class="small muted">${hc.working} nick đang chạy · ${hc.waiting_nick} chờ nick · ${hc.total}/${hc.max} chỗ trong văn phòng</span></div></div>
      <div class="row wrap"><div class="seg" role="group" aria-label="Quyền quyết định của CEO"><button type="button" data-ceomode="auto" class="${o.mode==="auto"?"on":""}">CEO tự quyết</button><button type="button" data-ceomode="approve" class="${o.mode==="approve"?"on":""}">Chờ duyệt</button></div>
        <button class="btn sm" type="button" data-ceo="review">Đánh giá ngay</button></div></div>
    <div class="row wrap small" style="gap:10px"><label class="row" style="gap:6px"><input type="checkbox" id="apToggle" ${document.body.classList.contains("autopilot")?"checked":""}> <b>Luật: sếp chỉ giao việc cho CEO</b> (CEO tự giao việc cho các agent, tự duyệt bài, tự xếp lịch)</label><a href="#ceo">Giao việc cho CEO →</a></div>
    <div id="ceoOrders"></div>
    ${o.group_keywords&&o.group_keywords.length?`<div class="gf-today small"><b>Hôm nay sale tìm và ưu tiên đăng nhóm chủ đề:</b>${o.group_keywords.map(k=>`<span class="kw">${esc(k)}</span>`).join("")}<a href="#groups">Xem nhóm tìm được →</a></div>`:""}
    ${o.proposed.length?`<div class="ceo-prop">${o.proposed.map(d=>`<div><b>${esc(d.title)}</b><span class="small">${esc(d.reason)}</span><div class="row"><button class="btn sm primary" type="button" data-ceook="${d.id}">Duyệt</button><button class="btn sm ghost" type="button" data-ceono="${d.id}">Không</button></div></div>`).join("")}</div>`:""}
    <div class="ceo-grid">
      <div><h4>Tăng người theo doanh thu</h4><ul class="ms">${o.milestones.map(m=>`<li class="${m.done?"done":""}"><div class="row" style="justify-content:space-between"><span>${m.done?"✓ ":""}Mốc <b>${vnd(m.amount)}</b></span><span class="small muted">+${m.hires} sale</span></div><div class="bar"><i style="width:${Math.min(100,rev/m.amount*100)}%"></i></div></li>`).join("")||'<li class="muted small">Chưa đặt mốc nào.</li>'}</ul>
        <details class="ms-edit"><summary class="small">Sửa mốc</summary><div id="msRows">${o.milestones.map(m=>msRow(m.amount,m.hires)).join("")}</div>
          <div class="row" style="margin-top:6px"><button class="btn sm ghost" type="button" data-ceo="addms">+ Thêm mốc</button><button class="btn sm primary" type="button" data-ceo="savems">Lưu mốc</button></div></details></div>
      <div><h4>Tiềm năng tìm khách trên Facebook</h4><p class="small ${p.ready?"risk-safe":""}">${esc(p.verdict)}</p>
        <label class="row small" style="gap:6px"><input type="checkbox" data-ceo="pot" ${o.potential_on?"checked":""}> Tự tuyển thêm khi thấy tiềm năng</label>
        <details><summary class="small">Số liệu ${p.window_days} ngày: ${p.per_day} khách/ngày · ${p.quota_pct}% chỉ tiêu</summary>
          <p class="small muted" style="margin:6px 0 2px">Tín hiệu (cần ít nhất 1)</p><ul class="checks">${p.signal.map(chk).join("")}</ul>
          <p class="small muted" style="margin:6px 0 2px">Điều kiện an toàn (cần đủ)</p><ul class="checks">${p.guards.map(chk).join("")}</ul></details></div>
      <div><h4>Quyết định gần đây</h4><ul class="dec">${o.decisions.filter(d=>!["proposed","approved"].includes(d.status)).slice(0,6).map(d=>`<li><span aria-hidden="true">${DKIND[d.kind]||"•"}</span><div><b>${esc(d.title)}</b>${d.status==="rejected"?' <span class="chip">Sếp không duyệt</span>':""}<div class="small muted">${fmtDate(d.created_at)} · ${esc(d.reason||"")}</div></div></li>`).join("")||'<li class="muted small">CEO chưa có quyết định nào.</li>'}</ul></div>
    </div></section>`;
}
const msRow=(a,h)=>`<div class="row ms-row"><input type="text" inputmode="numeric" value="${a?vnd(a).replace("đ",""):""}" placeholder="VD 50tr" aria-label="Mốc doanh thu"><input type="number" min="1" max="4" value="${h||1}" aria-label="Số sale tuyển thêm"><span class="small muted">sale</span><button class="btn sm ghost danger" type="button" data-ceo="delms" aria-label="Xóa mốc">✕</button></div>`;
$("#coBody").addEventListener("click",async e=>{
  const t=e.target; let r;
  try{
    if((r=t.closest("[data-ceomode]"))){ await api("/ceo","PUT",{mode:r.dataset.ceomode}); toast(r.dataset.ceomode==="auto"?"CEO được tự quyết tuyển dụng":"Mọi việc tuyển dụng sẽ chờ sếp duyệt"); return loadCompany(); }
    if((r=t.closest("[data-ceook],[data-ceono]"))){ const ok=!!r.dataset.ceook; await api(`/ceo/decisions/${r.dataset.ceook||r.dataset.ceono}`,"POST",{approve:ok}); toast(ok?"Đã duyệt. Sale mới chờ sếp đăng nhập nick ở trang Nhân viên sale":"Đã từ chối đề xuất"); loadCompany(); return refresh(); }
    if((r=t.closest('[data-ceo="review"]'))){ await api("/ceo/review","POST"); toast("CEO đã đánh giá lại"); loadCompany(); return refresh(); }
    if(t.closest('[data-ceo="addms"]')){ $("#msRows").insertAdjacentHTML("beforeend",msRow(0,1)); return; }
    if((r=t.closest('[data-ceo="delms"]'))){ r.closest(".ms-row").remove(); return; }
    if(t.closest('[data-ceo="savems"]')){ const ms=[...document.querySelectorAll("#msRows .ms-row")].map(x=>{ const [a,h]=x.querySelectorAll("input"); return {amount:parseVnd(a.value),hires:+h.value}; });
      if(ms.some(m=>!m.amount)){ toast("Nhập số tiền cho mỗi mốc, ví dụ 50tr"); return; } await api("/ceo","PUT",{milestones:ms}); toast("Đã lưu mốc tăng người"); return loadCompany(); }
  }catch(err){ toast(err.message); }
});
$("#coBody").addEventListener("change",async e=>{ if(e.target.id==="apToggle"){ await api("/ceo/autopilot","PUT",{on:e.target.checked}); document.body.classList.toggle("autopilot",e.target.checked); toast(e.target.checked?"Từ giờ sếp chỉ giao việc cho CEO, CEO tự vận hành":"Sếp giao việc trực tiếp cho từng agent"); return; }
  if(e.target.dataset.ceo==="pot"){ await api("/ceo","PUT",{potential:e.target.checked}); toast(e.target.checked?"CEO sẽ tự tuyển thêm khi thấy tiềm năng":"Tắt tuyển thêm theo tiềm năng"); loadCompany(); } });
