/* --------------------------------------------- Phòng ban: trưởng phòng đánh giá, đề xuất tuyển, CEO xét, nhân viên mới */
async function loadDp(){ try{ ST.dp=await api("/departments"); }catch(e){ toast(e.message); return; } renderDp(); }
function renderDp(){ const d=ST.dp, PS={pending:["Chờ duyệt","warn"],done:["Đã tuyển","ok"],rejected:["Không tuyển",""]};
  $("#dpNote").textContent=`Quyền CEO: ${d.ceo_mode==="approve"?"chờ sếp duyệt (CEO đồng ý thì sếp bấm Duyệt ở đây)":"CEO tự quyết (đủ số liệu và vốn thì tuyển luôn, báo Telegram)"}. Trưởng phòng tự đánh giá mỗi ${["","thứ Hai","thứ Ba","thứ Tư","thứ Năm","thứ Sáu","thứ Bảy","Chủ nhật"][+d.settings.dept_review_weekday||1]} lúc ${d.settings.dept_review_time||"08:40"}.`;
  $("#dpList").innerHTML=d.depts.map(p=>{ const rv=p.review;
    return `<section class="card dp-card" style="border-top:4px solid ${esc(p.color)}" data-dp="${p.key}"><div class="card-h"><div><h3>${esc(p.name)}</h3><p class="small muted" style="margin:2px 0 0">${esc(p.goal)}</p></div>
      ${p.key!=="director"?`<button type="button" class="btn sm" data-dpa="review">Đánh giá ngay</button>`:""}</div>
      <ul class="dp-mem">${p.members.map(m=>`<li${m.head?' class="hd"':""}><b>${esc(m.name)}</b>${m.head?' <span class="chip ok">Trưởng phòng</span>':""}<span class="small muted"> ${esc(m.role||"")}</span>${m.staff_id?` <button type="button" class="btn sm ghost" data-dpleave="${m.staff_id}">Cho nghỉ</button>`:""}</li>`).join("")}</ul>
      ${rv?`<div class="dp-rv"><p class="small" style="margin:6px 0 2px"><b>${esc(p.head_name)} đánh giá</b> <span class="muted">${esc((rv.created_at||"").slice(8,10))}/${esc((rv.created_at||"").slice(5,7))}</span>: ${esc(rv.summary)}</p>
        ${rv.bottleneck?`<p class="small" style="margin:2px 0"><b>Nút thắt:</b> ${esc(rv.bottleneck)}</p>`:""}${rv.plan&&rv.plan.length?`<ol class="small" style="margin:2px 0;padding-left:18px">${rv.plan.map(x=>`<li>${esc(x)}</li>`).join("")}</ol>`:""}</div>`
        :p.key!=="director"?'<p class="small muted">Trưởng phòng chưa đánh giá lần nào.</p>':""}
      ${p.positions.length?`<p class="small" style="margin:8px 0 2px"><b>Vị trí tuyển được</b></p><ul class="small dp-pos">${p.positions.map(x=>`<li><b>${esc(x.title)}</b> <span class="muted">(${x.have}${x.max?`/${x.max}`:""})</span>: ${esc(x.does)}</li>`).join("")}</ul>`:""}
      ${p.proposals.length?`<p class="small" style="margin:8px 0 2px"><b>Đề xuất tuyển</b></p>${p.proposals.map(x=>{ const [lb,cl]=PS[x.status]||[x.status,""]; const pos=(p.positions.find(y=>y.key===x.position)||{}).title||x.position;
        return `<div class="dp-prop" data-dpp="${x.id}"><span class="chip ${cl}">${lb}</span> <b>${esc(pos)}</b> <span class="small muted">${esc((x.created_at||"").slice(8,10))}/${esc((x.created_at||"").slice(5,7))}</span>
          <p class="small" style="margin:2px 0">${esc(x.reason||"")}</p>${x.ceo_note?`<p class="small muted" style="margin:0">CEO: ${esc(x.ceo_note)}</p>`:""}
          ${x.status==="pending"?`<div class="acts"><button type="button" class="btn sm primary" data-dpd="approve">Duyệt tuyển</button><button type="button" class="btn sm ghost" data-dpd="reject">Không</button></div>`:""}</div>`; }).join("")}`:""}
    </section>`; }).join(""); }
$("#dpAll").onclick=async e=>{ e.target.disabled=true; try{ const ks=ST.dp.depts.map(p=>p.key).filter(k=>k!=="director"); let n=0;
  for(const k of ks){ const r=await api(`/departments/${k}/review`,"POST"); n+=(r.decisions||[]).filter(x=>x.status==="done").length; }
  toast(n?`Các trưởng phòng đã đánh giá, CEO tuyển ${n} người`:"Các trưởng phòng đã đánh giá xong"); loadDp(); }catch(err){ toast(err.message); } e.target.disabled=false; };
$("#v-depts").addEventListener("click",async e=>{ const b=e.target.closest("button"); if(!b) return; b.disabled=true;
  try{ if(b.dataset.dpa==="review"){ const k=b.closest("[data-dp]").dataset.dp, r=await api(`/departments/${k}/review`,"POST"); const dn=(r.decisions||[])[0];
      toast(dn?(dn.status==="done"?`CEO đã tuyển ${dn.name}`:dn.status==="pending"?"CEO đồng ý, chờ sếp duyệt":`CEO không tuyển: ${dn.why||""}`):"Trưởng phòng đã đánh giá xong"); }
    else if(b.dataset.dpd){ const r=await api(`/departments/proposals/${b.closest("[data-dpp]").dataset.dpp}/${b.dataset.dpd}`,"POST"); toast(r.status==="done"?`Đã tuyển ${r.name||""}`:"Đã ghi: không tuyển"); }
    else if(b.dataset.dpleave){ await api(`/departments/staff/${b.dataset.dpleave}/leave`,"POST"); toast("Đã cho nghỉ việc"); }
    else return; loadDp(); }catch(err){ toast(err.message); } finally{ b.disabled=false; } });
