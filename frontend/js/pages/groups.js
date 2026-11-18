/* --------------------------------------------- hội nhóm */
async function loadGroups(){
  [ST.groups,ST.sales]=await Promise.all([api("/groups"),api("/sales")]);
  const JST={joined:["on","Đã vào nhóm"],requested:["pend","Đã xin vào, chờ quản trị viên duyệt"],needs_answers:["need","Nhóm bắt trả lời câu hỏi: sếp mở Chrome của nick này để tự xin vào"],failed:["need","Xin vào lỗi"],none:["","Chưa vào"]};
  const nicks=ST.sales.filter(x=>x.status!=="fired").flatMap(x=>(x.accounts||[]).map(n=>({...n,sale:x.name})));
  const chips=g=>{ const mem=(g.member_account_ids||"").split(",").filter(Boolean).map(Number); if(!nicks.length) return '<span class="small muted">Chưa có nick</span>';
    return `<div class="member-chips">${nicks.map(x=>{ const j=(g.joins||{})[x.id]; const on=mem.includes(x.id); const [c,t]=on?JST.joined:j?JST[j.status]||["",j.status]:["",g.source==="search"?"Chưa vào":"Bấm để đánh dấu đã vào"];
      return `<button type="button" data-gm="${g.id}" data-s="${x.id}" class="${c}" title="${esc(`${x.sale} · ${x.name}: ${t}${j&&j.note?" ("+j.note+")":""}`)}">${esc(x.name)}${c==="pend"?" ⏳":c==="need"?" ❓":""}</button>`; }).join("")}</div>`; };
  const missing=ST.groups.filter(g=>!g.url).length;
  $("#groupWarn").hidden=!missing; $("#groupWarn").innerHTML=`<b>${missing} nhóm chưa có link</b>: sale không đăng được vào các nhóm này và Tuấn sẽ không xếp bài vào đó. Bấm “Thêm link” ở từng dòng.`;
  const linkCell=g=>`<div class="glink" data-gid="${g.id}">${g.url?`<a class="small" href="${esc(g.url)}" target="_blank" rel="noopener">${esc(g.url.replace(/^https:\/\/www\.facebook\.com/,""))}</a> <button type="button" class="btn sm ghost" data-gedit="${g.id}">Sửa link</button>`:`<span class="chip bad">Chưa có link</span> <button type="button" class="btn sm" data-gedit="${g.id}">Thêm link</button>`}</div>`;
  loadFinder(); loadMyGroups();
  $("#groupRows").innerHTML=ST.groups.map(g=>`<tr><td><b>${esc(g.name)}</b><button type="button" class="gfocus" data-gfocus="${g.id}" aria-pressed="${g.focus?"true":"false"}" title="Tập trung đăng: xếp trước, mỗi ngày 1 bài">${g.focus?"★":"☆"} Tập trung</button>${g.source==="search"?`<span class="src${g.today?" today":""}" title="Sale tìm thấy khi tìm “${esc(g.keyword||"")}”">${g.today?"Chủ đề hôm nay":"Tự tìm"}</span>`:g.today?'<span class="src today">Chủ đề hôm nay</span>':""}${g.eng_score!=null?`<span class="src" title="${esc(g.review_note||"")}">Tương tác ${vn1(g.eng_score)}đ</span>`:""}${linkCell(g)}</td><td>${esc(g.topic)}</td><td class="num">${(+g.members||0).toLocaleString("vi-VN")}</td><td class="small">${esc(g.rules)}</td><td class="num">${g.min_days_between_posts} ngày</td><td>${g.last_posted_at?fmtDate(g.last_posted_at):"Chưa đăng"}</td><td>${!g.url?'<span class="chip bad">Thiếu link</span>':g.source==="search"&&!(g.member_account_ids||"").trim()?'<span class="chip warn" title="Chỉ nick đã vào nhóm mới đăng được">Chờ nick vào nhóm</span>':`<span class="chip ${g.ready?"ok":"warn"}">${g.ready?"Đăng được":"Đang giãn cách"}</span>`}</td><td class="num">${g.leads_count||0}</td><td>${chips(g)}</td><td><button class="btn sm ghost danger" data-g="${g.id}">Xóa</button></td></tr>`).join("");
}
$("#groupRows").addEventListener("click",async e=>{
  const fo=e.target.closest("[data-gfocus]");
  if(fo){ const on=fo.getAttribute("aria-pressed")!=="true"; try{ await api(`/groups/${fo.dataset.gfocus}/focus`,"PUT",{focus:on}); toast(on?"Tuấn sẽ ưu tiên đăng nhóm này, mỗi ngày 1 bài. Chỉnh thêm ở Bài đăng → Chỉ đạo nơi đăng":"Đã bỏ tập trung đăng nhóm này"); loadGroups(); }catch(err){ toast(err.message); } return; }
  const ed=e.target.closest("[data-gedit]");
  if(ed){ const g=ST.groups.find(x=>x.id==ed.dataset.gedit); const box=ed.closest(".glink");
    box.innerHTML=`<form class="row glink-f"><input type="text" inputmode="url" value="${esc(g.url||"")}" placeholder="https://www.facebook.com/groups/…" aria-label="Link nhóm ${esc(g.name)}" required><button class="btn sm primary" type="submit">Lưu</button><button class="btn sm ghost" type="button" data-gcancel>Hủy</button></form>`;
    box.querySelector("input").focus(); return; }
  if(e.target.closest("[data-gcancel]")) return loadGroups();
  const m=e.target.closest("[data-gm]");
  if(m){ const g=ST.groups.find(x=>x.id==m.dataset.gm); let mem=(g.member_account_ids||"").split(",").filter(Boolean).map(Number); const aid=+m.dataset.s;
    mem=mem.includes(aid)?mem.filter(x=>x!==aid):[...mem,aid]; await api(`/groups/${g.id}/members`,"PUT",{account_ids:mem}); return loadGroups(); }
  const b=e.target.closest("[data-g]"); if(!b) return; if(b.dataset.confirm!=="1"){ b.dataset.confirm="1"; b.textContent="Bấm lần nữa để xóa"; return; } await api(`/groups/${b.dataset.g}`,"DELETE"); loadGroups(); });
$("#groupRows").addEventListener("submit",async e=>{ e.preventDefault(); const f=e.target; const gid=f.closest(".glink").dataset.gid;
  try{ await api(`/groups/${gid}`,"PATCH",{url:f.querySelector("input").value}); toast("Đã lưu link nhóm. Bài từng lỗi vì thiếu link đã về hàng chờ để Tuấn xếp lại"); loadGroups(); }
  catch(err){ toast(err.message); } });
$("#groupForm").addEventListener("submit",async e=>{ e.preventDefault(); try{ await api("/groups","POST",{name:$("#grName").value,url:$("#grUrl").value,topic:$("#grTopic").value,members:+$("#grMembers").value||0,rules:$("#grRules").value,min_days_between_posts:+$("#grDays").value||3}); e.target.reset(); toast("Đã thêm nhóm"); loadGroups(); }catch(err){ toast(err.message); } });

