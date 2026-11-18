/* --------------------------------------------- nhóm trong các nick (Tuấn rà soát) */
const MG_V={manage:["ok","Nhóm mình quản lý"],post:["ok","Nên đăng"],keep:["","Đăng ít"],rest:["warn","Mới vào, đang nghỉ"],leave:["bad","Sẽ thoát"],left:["","Đã thoát"],pending:["","Chưa rà soát"]};
function mgLi(x){
  const [c,lbl]=MG_V[x.verdict]||["",x.verdict];
  const prog=x.target?`<div class="mg-prog"><div class="bar"><i style="width:${Math.min(100,Math.round(x.today/x.target*100))}%"></i></div>Hôm nay ${x.today}/${x.target} bài</div>`:"";
  const meta=[`nick ${esc(x.nick)}`,x.role==="admin"?"quản trị viên":x.origin==="app"?`phần mềm xin vào ${fmtDate(x.joined_at)}`:"có sẵn trong nick",
    x.members?`${num(x.members)} thành viên`:"",x.eng_score!=null?`${vn1(x.eng_score)} điểm tương tác`:"",x.rest_until?`đăng từ ${fmtDate(x.rest_until)}`:"",x.left_at?`thoát ${fmtDate(x.left_at)}`:"",x.pinned?"sếp giữ":""].filter(Boolean).join(" · ");
  const act=x.status==="left"?"":`<div class="row" style="gap:4px;flex-wrap:nowrap">${x.role==="admin"?"":`<button class="btn sm ghost" type="button" data-mgpin="${x.group_id}" data-on="${x.pinned?0:1}">${x.pinned?"Bỏ giữ":"Giữ nhóm"}</button>`}
    ${x.role==="admin"||x.verdict==="left"?"":`<button class="btn sm ghost danger" type="button" data-mgleave="${x.group_id}" data-acc="${x.account_id}">Thoát</button>`}</div>`;
  return `<li><div><a class="nm" href="${esc(x.url||"#")}" target="_blank" rel="noopener">${esc(x.name)}</a> <span class="chip ${c}">${lbl}</span><div class="meta">${meta}</div>${prog}</div>${act}
    ${x.verdict_note&&x.verdict!=="manage"?`<div class="why">${esc(x.verdict_note.slice(0,220))}</div>`:""}</li>`;
}
async function loadMyGroups(){
  const box=$("#mgBody"); if(box.contains(document.activeElement)&&document.activeElement.matches("input")) return;
  let d; try{ d=await api("/my-groups"); }catch(e){ box.innerHTML=`<p class="err">${esc(e.message)}</p>`; return; }
  ST.mg=d; const st=d.settings, it=d.items;
  const sec=(title,rows,empty)=>rows.length?`<div class="mg-sec"><h4>${title} <span class="chip">${rows.length}</span></h4><ul class="mg-list">${rows.map(mgLi).join("")}</ul></div>`:empty||"";
  const by=v=>it.filter(x=>x.verdict===v);
  box.innerHTML=`<div class="mg-nicks">${d.nicks.map(n=>`<div class="mg-nick"><b>${esc(n.name)}</b> <span class="muted">(${esc(n.sale)})</span><br>${n.synced_at?`${n.groups} nhóm · ${n.admin} nhóm quản lý · ${n.post} nhóm đăng được${n.leave?` · ${n.leave} nhóm sẽ thoát`:""}`:"Chưa đọc danh sách nhóm"}</div>`).join("")||'<span class="small muted">Chưa có nick nào đang chạy.</span>'}</div>
    ${d.last?`<p class="small muted" style="margin:4px 0 0">${fmtTime(d.last.created_at)} ${fmtDate(d.last.created_at)}: ${esc(d.last.detail)}</p>`:""}
    ${it.length?"":'<p class="small muted">Chưa đọc danh sách nhóm của nick nào. Bấm “Tuấn rà soát ngay”: sale mở Facebook → Nhóm → Nhóm bạn đã tham gia của từng nick, Tuấn xem từng nhóm rồi quyết định.</p>'}
    ${sec("Nhóm mình quản lý: chăm sóc mỗi ngày",by("manage"))}${sec("Nên đăng",by("post"))}${sec("Đăng ít (tương tác trung bình)",by("keep"))}
    ${sec("Nhóm mới vào, đang nghỉ chưa đăng",by("rest"))}${sec(st.auto_leave==="1"?"Tuấn sẽ tự thoát (không liên quan hoặc tương tác kém)":"Nên thoát (đang tắt tự thoát)",by("leave"))}
    ${sec("Chưa rà soát",by("pending"))}${sec("Đã thoát",by("left").slice(0,15))}
    <details style="margin-top:12px"><summary class="small">Cài đặt rà soát nhóm và chăm sóc nhóm quản lý</summary>
      <form id="mgForm" class="stack" style="margin-top:8px">
        <div class="grid3"><label class="f" for="mgTime">Giờ rà soát mỗi ngày<input type="time" id="mgTime" value="${esc(st.mygroups_time||"09:15")}"></label>
          <label class="f" for="mgRest">Nhóm mới vào nghỉ (ngày) rồi mới đăng<input type="number" id="mgRest" min="0" max="30" value="${esc(st.new_group_rest_days||7)}"></label>
          <label class="f" for="mgLeave">Thoát tối đa (nhóm/nick/ngày)<input type="number" id="mgLeave" min="0" max="10" value="${esc(st.leave_per_nick_day||3)}"></label>
          <label class="f" for="mgMin">Nhóm quản lý: ít nhất (bài/ngày)<input type="number" id="mgMin" min="0" max="20" value="${esc(st.admin_posts_min||5)}"></label>
          <label class="f" for="mgMax">Nhóm quản lý: nhiều nhất (bài/ngày)<input type="number" id="mgMax" min="1" max="20" value="${esc(st.admin_posts_max||10)}"></label></div>
        <label class="row small"><input type="checkbox" id="mgAuto" ${st.auto_leave!=="0"?"checked":""}> Tự thoát nhóm không liên quan hoặc tương tác kém (không bao giờ thoát nhóm mình quản lý, nhóm đã ra khách, nhóm sếp giữ)</label>
        <label class="row small"><input type="checkbox" id="mgOn" ${st.mygroups_enabled!=="0"?"checked":""}> Rà soát mỗi ngày và chăm sóc nhóm quản lý</label>
        <div><button class="btn sm primary" type="submit">Lưu</button></div></form></details>`;
}
$("#mgRun").addEventListener("click",async e=>{ const b=e.currentTarget; b.disabled=true; try{ const r=await api("/my-groups/sync","POST"); toast(`${r.nicks} nick sẽ mở danh sách nhóm, Tuấn rà soát xong sẽ báo`); setTimeout(loadMyGroups,3500); }catch(err){ toast(err.message); } b.disabled=false; });
$("#mgBody").addEventListener("click",async e=>{ let b;
  try{
    if((b=e.target.closest("[data-mgpin]"))){ await api(`/my-groups/${b.dataset.mgpin}/pin`,"POST",{pin:b.dataset.on==="1"}); toast(b.dataset.on==="1"?"Đã giữ nhóm: Tuấn sẽ không thoát nhóm này":"Đã bỏ giữ nhóm"); return loadMyGroups(); }
    if((b=e.target.closest("[data-mgleave]"))){ if(b.dataset.confirm!=="1"){ b.dataset.confirm="1"; b.textContent="Bấm lần nữa để thoát"; return; }
      await api(`/my-groups/${b.dataset.mgleave}/leave`,"POST",{account_id:+b.dataset.acc}); toast("Sale sẽ mở Chrome của nick và thoát nhóm này"); setTimeout(loadMyGroups,3000); return; }
  }catch(err){ toast(err.message); } });
$("#mgBody").addEventListener("submit",async e=>{ e.preventDefault();
  try{ await api("/my-groups/settings","PUT",{time:$("#mgTime").value,rest_days:+$("#mgRest").value,leave_per_nick_day:+$("#mgLeave").value,admin_min:+$("#mgMin").value,admin_max:+$("#mgMax").value,auto_leave:$("#mgAuto").checked,enabled:$("#mgOn").checked});
    toast("Đã lưu cài đặt"); loadMyGroups(); }catch(err){ toast(err.message); } });

