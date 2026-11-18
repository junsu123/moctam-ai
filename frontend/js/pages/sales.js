/* --------------------------------------------- nhân viên sale */
const LOGIN={ok:["ok","Đã đăng nhập"],not_logged_in:["warn","Chưa đăng nhập"],checkpoint:["bad","Checkpoint / bị chặn"],error:["bad","Lỗi"]};
const PST={scheduled:["warn","Trong lịch"],posting:["talking","Đang đăng"],posted:["ok","Đã đăng"],failed:["bad","Lỗi"],approved:["","Chờ xếp"]};
let salesBusy=false;
async function loadSales(){
  if(salesBusy) return; salesBusy=true; loadHealth();
  try{
    ST.sales=await api("/sales"); const grid=$("#salesGrid");
    const gd=$("#salesGuide"); if(gd&&!gd.dataset.touched){ gd.open=!ST.sales.some(x=>!x.is_sample&&x.status!=="fired"); }
    const ae=document.activeElement; if(ae && grid.contains(ae) && /^(INPUT|SELECT|TEXTAREA)$/.test(ae.tagName)) return; // đang gõ trong form nick
    grid.innerHTML=ST.sales.length?ST.sales.map(s=>{ const [lc,lt]=LOGIN[s.login_status]||["",s.login_status];
      if(s.status==="fired") return `<div class="card" style="opacity:.75"><div class="card-h"><div class="row">${avaHtml(s.agent_id)}<div><h3>${esc(s.name)}</h3><span class="small muted">${s.replaced_by?"Nick đã chuyển cho người thay":`Nick: ${esc(s.fb_name||"chưa có")}`}</span></div></div><span class="chip bad">Đã nghỉ việc</span></div>
        <p class="small muted">${esc(s.fire_reason||"")}</p>${s.replaced_by?'<p class="small">Đã có người thay, nick vẫn hoạt động.</p>':'<a class="btn sm" href="#company">Tuyển người thay, giữ nick</a>'}</div>`;
      const nicks=s.accounts||[]; const cap=nicks.filter(n=>n.enabled).reduce((t,n)=>t+(+n.max_posts_per_day||0),0); const okN=nicks.filter(n=>n.enabled&&n.login_status==="ok").length;
      const BUSY={open:"Đang mở Chrome chờ sếp đăng nhập",check:"Đang kiểm tra phiên",post:"Đang đăng bài",session:"Đang làm ca",bump:"Đang up bài",scan:"Đang quét bình luận",discover:"Đang tìm nhóm",join:"Đang xin vào nhóm"};
      const curNick=nicks.find(n=>n.id===s.busy_account);
      return `<div class="card" data-sale="${s.id}">
      <div class="card-h"><div class="row">${avaHtml(s.agent_id)}<div><h3>${esc(s.name)} ${s.is_sample?'<span class="chip warn">Sale mẫu</span>':""}</h3><span class="small muted">${nicks.length} nick · ${okN} nick đang chạy</span></div></div><span class="chip ${lc}">${lt}</span></div>
      ${s.is_sample?'<p class="small muted">Sale mẫu để xem thử. Khi bạn tuyển sale đầu tiên, các sale mẫu tự rời văn phòng.</p>':""}
      ${s.hired_by==="ceo"&&s.login_status!=="ok"?`<div class="ceo-prop"><div><b>CEO Đức vừa tuyển ${esc(s.name)}</b><span class="small">${esc((s.hire_reason||"").replace(/^(milestone|potential|boss): /,""))}</span><span class="small">Việc của sếp: chuẩn bị 3–5 tài khoản Facebook cho ${esc(s.name)}, bấm <b>Thêm nick</b> rồi <b>Mở Chrome</b> từng nick để đăng nhập. Chưa có nick thì bấm Cho nghỉ việc để hủy tuyển.</span></div></div>`:""}
      ${s.busy?`<span class="chip talking" style="align-self:flex-start">${BUSY[s.busy]||"Đang làm việc"}${curNick?` · nick ${esc(curNick.name)}`:""}</span>`:""}
      <div class="sale-stats"><div><b>${s.posted_today}/${cap}</b><span>Đã đăng hôm nay</span></div><div><b>${s.scheduled_today}</b><span>Trong lịch</span></div><div><b>${s.failed}</b><span>Bài lỗi</span></div></div>
      <div class="nicks"><div class="nicks-h"><b class="small">Nick Facebook (${nicks.length}/${s.max_accounts||5})</b><span class="small muted">Làm theo ca: xong nick này mới chuyển nick khác</span></div>
        ${nicks.map(n=>{ const [nc,nt]=n.enabled||n.login_status==="checkpoint"?(LOGIN[n.login_status]||["",n.login_status]):["","Đang tạm dừng"]; const on=s.busy_account===n.id;
          return `<div class="nick${on?" on":""}${n.enabled?"":" off"}" data-acc="${n.id}">
          <div class="nick-top"><span class="nick-name" title="${esc(n.name)}">${on?'<span class="dot live" aria-hidden="true"></span>':""}${esc(n.name)}</span><span class="chip ${nc}">${on?"Đang làm":nt}</span></div>
          <div class="small muted">${n.posted_today}/${n.max_posts_per_day} bài hôm nay · ${n.scheduled_today} trong lịch · vào ${n.groups_joined} nhóm${n.last_session_at?` · ca gần nhất ${fmtTime(n.last_session_at)}`:""}</div>
          ${n.last_error&&n.login_status!=="ok"?`<div class="err">${esc(n.last_error)}</div>`:""}
          ${n.diag&&n.diag.why&&n.diag.why.length&&(n.diag.idle||n.diag.why.some(w=>w.level!=="info"))?`<div class="nick-why${n.diag.why.some(w=>w.level==="bad")?" bad":""}" role="note"><b class="small">${n.diag.idle?"Vì sao hôm nay nick chưa có việc":"Lưu ý"}</b>${n.diag.why.map(w=>`<span class="small">• ${esc(w.text)}${w.fix?` <span class="muted">→ ${esc(w.fix)}</span>`:""}</span>`).join("")}</div>`:""}
          <div class="actions"><button class="btn sm${n.login_status==="ok"?"":" primary"}" data-na="open" ${s.busy?"disabled":""}>Mở Chrome${n.login_status==="ok"?"":" để đăng nhập"}</button><button class="btn sm" data-na="check" ${s.busy?"disabled":""}>Kiểm tra</button>
            <button class="btn sm ghost" data-na="toggle">${n.enabled?"Tạm dừng nick":"Bật lại nick"}</button></div>
          <details class="limits"><summary>Giới hạn: ${n.max_posts_per_day} bài/ngày, cách ${n.min_gap_minutes} phút, ${esc(n.active_from)}–${esc(n.active_to)}</summary>
            <div class="grid2"><label class="f" for="nn-${n.id}">Tên nick<input type="text" id="nn-${n.id}" value="${esc(n.name)}"></label>
            <label class="f" for="mx-${n.id}">Bài tối đa/ngày<input type="number" min="1" max="10" id="mx-${n.id}" value="${n.max_posts_per_day}"></label>
            <label class="f" for="gap-${n.id}">Cách nhau tối thiểu (phút)<input type="number" min="10" id="gap-${n.id}" value="${n.min_gap_minutes}"></label>
            <label class="f" for="af-${n.id}">Bắt đầu<input type="time" id="af-${n.id}" value="${esc(n.active_from)}"></label>
            <label class="f" for="at-${n.id}">Kết thúc<input type="time" id="at-${n.id}" value="${esc(n.active_to)}"></label></div>
            <div class="actions" style="margin-top:8px"><button class="btn sm primary" data-na="save">Lưu</button><button class="btn sm ghost danger" data-na="del">Xóa nick</button></div></details>
          </div>`; }).join("")||'<p class="small muted">Chưa có nick nào. Thêm nick bên dưới rồi bấm Mở Chrome để đăng nhập.</p>'}
        ${nicks.length<(s.max_accounts||5)?`<form class="row nick-add" data-addnick="${s.id}"><input type="text" id="an-${s.id}" placeholder="Tên nick, ví dụ ${esc(s.name)} Trà Sỉ" aria-label="Tên nick mới của ${esc(s.name)}"><button class="btn sm" type="submit">Thêm nick (${nicks.length}/${s.max_accounts||5})</button></form>
          ${nicks.length<3?'<span class="small muted">Nên giữ 3–5 nick mỗi sale để chia đều bài, mỗi nick đăng ít hơn và an toàn hơn.</span>':""}`:'<span class="small muted">Đã đủ 5 nick.</span>'}
      </div>
      <div class="actions"><button class="btn sm${s.auto_post?"":" primary"}" data-sa="toggle">${s.auto_post?"Tạm dừng cả sale":"Bật lại sale"}</button><button class="btn sm ghost danger" data-sa="del">Cho nghỉ việc</button></div>
      <div><b class="small">Việc gần đây</b><ul class="recent" style="margin-top:4px">${s.recent.length?s.recent.map(r=>{ const [c,t]=PST[r.status]||["",r.status];
        return `<li><span class="chip ${c}">${t}</span><span>${esc(r.group_name||TARGET[r.target_type])}</span>${r.account_name?`<span class="muted">· ${esc(r.account_name)}</span>`:""}<span class="muted">${fmtTime(r.posted_at||r.scheduled_for)}</span>${r.screenshot?`<a href="${esc(r.screenshot)}" target="_blank" rel="noopener">ảnh chụp</a>`:""}${r.error?`<span class="err" style="width:100%">${esc(r.error)}</span>`:""}</li>`; }).join(""):'<li class="muted">Chưa có bài nào.</li>'}</ul></div>
    </div>`; }).join(""):`<div class="empty">Chưa có nhân viên sale. Tuyển sale đầu tiên ở form bên dưới.</div>`;
  }finally{ salesBusy=false; }
}
$("#salesGuide").addEventListener("toggle",e=>{ e.target.dataset.touched="1"; });
$("#salesGrid").addEventListener("click",async e=>{
  const nb=e.target.closest("[data-na]"), b=e.target.closest("[data-sa]"); if(!nb&&!b) return;
  const id=+(nb||b).closest("[data-sale]").dataset.sale; const s=ST.sales.find(x=>x.id===id);
  try{
    if(nb){ const aid=+nb.closest("[data-acc]").dataset.acc; const n=(s.accounts||[]).find(x=>x.id===aid); const a=nb.dataset.na;
      if(a==="open"){ await api(`/accounts/${aid}/open`,"POST"); toast(DEMO?"Bản xem trước không mở được Chrome. Khi chạy trên máy bạn, cửa sổ Chrome của nick sẽ hiện lên.":`Đã mở Chrome của nick ${n.name} trên máy chạy phần mềm. Đăng nhập Facebook rồi đóng cửa sổ.`); }
      if(a==="check"){ await api(`/accounts/${aid}/check`,"POST"); toast(`Đang kiểm tra phiên nick ${n.name}…`); }
      if(a==="toggle"){ await api(`/accounts/${aid}`,"PATCH",{enabled:n.enabled?0:1}); toast(n.enabled?`Đã tạm dừng nick ${n.name}. Bài chờ của nick trả về hàng đợi, các nick khác vẫn làm.`:`Đã bật lại nick ${n.name}`); }
      if(a==="save"){ await api(`/accounts/${aid}`,"PATCH",{name:$(`#nn-${aid}`).value,max_posts_per_day:+$(`#mx-${aid}`).value,min_gap_minutes:+$(`#gap-${aid}`).value,active_from:$(`#af-${aid}`).value,active_to:$(`#at-${aid}`).value}); document.activeElement.blur(); toast("Đã lưu nick"); }
      if(a==="del"){ if(nb.dataset.confirm!=="1"){ nb.dataset.confirm="1"; nb.textContent="Bấm lần nữa để xóa nick"; return; } await api(`/accounts/${aid}`,"DELETE"); toast("Đã xóa nick. Hồ sơ Chrome vẫn giữ trên máy."); }
    } else { const a=b.dataset.sa;
      if(a==="toggle"){ await api(`/sales/${id}`,"PATCH",{auto_post:s.auto_post?0:1}); toast(s.auto_post?"Đã tạm dừng cả sale. Bài chờ của các nick trả về hàng đợi.":"Đã bật lại sale"); }
      if(a==="del"){ if(b.dataset.confirm!=="1"){ b.dataset.confirm="1"; b.textContent="Bấm lần nữa để xác nhận"; return; } await api(`/sales/${id}`,"DELETE"); toast("Đã cho nghỉ. Hồ sơ Chrome các nick vẫn giữ trên máy."); }
    }
  }catch(err){ toast(err.message); }
  loadSales(); refresh();
});
$("#salesGrid").addEventListener("submit",async e=>{ const f=e.target.closest("[data-addnick]"); if(!f) return; e.preventDefault(); const sid=+f.dataset.addnick;
  try{ await api("/accounts","POST",{sale_id:sid,name:$(`#an-${sid}`).value}); toast("Đã thêm nick. Bấm Mở Chrome ở nick mới để đăng nhập Facebook."); }catch(err){ toast(err.message); }
  document.activeElement.blur(); loadSales(); refresh(); });
$("#saleForm").addEventListener("submit",async e=>{ e.preventDefault();
  const hadSample=(ST.sales||[]).some(x=>x.is_sample);
  try{ await api("/sales","POST",{name:$("#saName").value,fb_name:$("#saFb").value}); e.target.reset(); toast((hadSample?"Đã tuyển sale mới. Các sale mẫu đã rời văn phòng. ":"Đã tuyển sale mới. ")+"Bấm Mở Chrome để đăng nhập nick đầu tiên, rồi thêm 2–4 nick nữa."); }catch(err){ toast(err.message); }
  loadSales(); refresh(); });

/* sức khỏe từng nick */
let nhAt=0;
async function loadHealth(force){ if(!force&&Date.now()-nhAt<60000) return; nhAt=Date.now(); try{ ST.nh=await api("/nick-health"); }catch(e){ return; } renderHealth(); }
function renderHealth(){ const d=ST.nh, c=d.counts||{}; $("#nhAuto").checked=!!d.auto;
  const COL={good:"var(--accent)",warn:"var(--honey)",bad:"var(--danger)"}, CH={good:"ok",warn:"warn",bad:"bad"};
  $("#nhSum").innerHTML=[["good","Khỏe"],["warn","Cần để ý"],["bad","Nguy hiểm"]].map(([k,t])=>`<span class="chip ${CH[k]}">${t}: ${c[k]||0}</span>`).join("");
  $("#nhList").innerHTML=d.items.length?d.items.map(r=>`<li class="${r.level}"><div class="hd"><b title="${esc(r.name||"")}">${esc(r.name||"Nick #"+r.id)}</b><span class="small muted">${esc(r.sale_name||"")}</span><span class="sc" style="color:${COL[r.level]}">${r.score}</span></div>
      <span class="meter" role="img" aria-label="Sức khỏe ${r.score}/100"><i style="width:${Math.max(3,r.score)}%;background:${COL[r.level]}"></i></span>
      <div class="row wrap" style="gap:6px"><span class="chip ${CH[r.level]}">${esc(r.label)}</span>${r.factor<1?`<span class="chip">Đang chạy ${Math.round(r.factor*100)}% trần</span>`:""}</div>
      ${r.signals.length?`<ul>${r.signals.map(s=>`<li>${esc(s.text)} <span class="muted">(−${s.minus})</span></li>`).join("")}</ul>`:'<p class="adv muted">Chưa có dấu hiệu rủi ro nào trong 30 ngày.</p>'}
      ${r.advice.length?`<p class="adv"><b>Nên:</b> ${esc(r.advice[0])}</p>`:""}</li>`).join("")
    :'<li class="muted small">Chưa có nick nào.</li>'; }
$("#nhAuto").onchange=async e=>{ try{ ST.nh=await api("/nick-health/settings","PUT",{auto:e.target.checked?1:0}); renderHealth(); toast(e.target.checked?"Nick sức khỏe kém sẽ tự giảm việc":"Đã tắt tự giảm việc theo sức khỏe nick"); }catch(err){ toast(err.message); } };
