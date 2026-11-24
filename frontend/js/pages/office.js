/* --------------------------------------------- văn phòng */
/* agent tự đi sang bàn đồng nghiệp khi việc cần trao đổi (theo nhật ký việc vừa xong), thỉnh thoảng báo cáo trưởng phòng */
const DEPT_OF={ceo:"director",khoa:"director",minh:"sales",lan:"sales",ha:"sales",mai:"sales",tuan:"groups",bao:"groups",nhi:"pages",vy:"website",huong:"website",khai:"website"};
const DEPT_HEAD={director:"ceo",sales:"minh",groups:"tuan",pages:"nhi",website:"vy"};
const VISIT={lastId:null,lastChat:Date.now(),wait:[]};  // wait: người đang bận đi việc khác, rảnh sẽ đi (giữ 90 giây)
function visitTarget(x,agents){ const a=x.agent_id||"", act=x.action||"", det=x.detail||"";
  if(a.startsWith("st-")) return DEPT_HEAD[(agents.find(g=>g.id===a)||{}).dept]||null;
  if(/Đánh giá phòng|Đề xuất tuyển/.test(act)) return "ceo";
  if(a==="ceo"&&/Tuyển nhân viên/.test(act)){ const st=agents.find(g=>g.kind==="staff"&&det.startsWith(g.name)); return st?st.id:null; }
  if(a==="ceo"&&/[Dd]uyệt/.test(act)) return "tuan";
  if(a==="lan") return "ceo";
  if(a==="tuan"&&/Xếp lịch|lịch/.test(act)){ const sl=agents.find(g=>g.kind==="sale"); return sl?sl.id:null; }
  if(a==="mai"&&/[Kk]hách|SĐT/.test(act+det)) return "ha";
  if(a==="ha"||a==="khoa") return a==="ha"?"minh":"ceo";
  if(a==="bao") return "tuan";
  if(a==="nhi"&&/Đã tạo Trang|Nghiên cứu/.test(act)) return "ceo";
  if(a.startsWith("sale-")&&/Xong ca|Đăng bài/.test(act)) return "tuan";
  if(a!=="ceo"){ const o=agents.find(g=>g.id!==a&&g.name&&new RegExp(`(^|[^\\p{L}])${g.name}([^\\p{L}]|$)`,"u").test(det)); if(o) return o.id; } // nhắc tên đồng nghiệp: sang trao đổi
  return null; }
function goVisit(from,to,text){ if(!World.visit(from,to,text)) VISIT.wait.push({from,to,text,until:Date.now()+90000}); }
function officeVisits(agents,acts){ if(ST.view!=="office"||typeof World==="undefined"||!World.visit) return;
  const top=acts.length?acts[0].id:0; if(VISIT.lastId===null){ VISIT.lastId=top; return; }
  const w=VISIT.wait.filter(v=>v.until>Date.now()); VISIT.wait=[]; w.forEach(v=>goVisit(v.from,v.to,v.text));
  const fresh=acts.filter(x=>x.id>VISIT.lastId).reverse().slice(-5); VISIT.lastId=Math.max(VISIT.lastId,top);
  fresh.forEach((x,i)=>{ if(x.action==="Lên phòng CEO nhận việc"){ setTimeout(()=>World.summon("ceo",x.agent_id,`Dạ em nhận việc: ${(x.detail||"").slice(0,80)}`),i*1800); return; }
    const to=visitTarget(x,agents); if(to) setTimeout(()=>goVisit(x.agent_id,to,`${x.action}: ${(x.detail||"").slice(0,70)}`),i*2500); });
  if(!fresh.length&&Date.now()-VISIT.lastChat>150000){ VISIT.lastChat=Date.now(); // lâu không có việc chung: một người sang báo cáo trưởng phòng
    const pool=agents.filter(g=>{ const d=g.kind==="staff"?g.dept:DEPT_OF[g.id]; return d&&DEPT_HEAD[d]!==g.id&&(g.status||{}).state==="working"; });
    const g=pool[Math.floor(Math.random()*pool.length)]; if(g){ const d=g.kind==="staff"?g.dept:DEPT_OF[g.id]; World.visit(g.id,DEPT_HEAD[d],`Báo cáo: ${((g.status||{}).text||"việc đang làm").slice(0,70)}`); } } }
async function refresh(){
  try{
    const [agents,dash]=await Promise.all([api("/agents"),api("/dashboard")]); ST.agents=agents; ST.dash=dash;
    World.sync(agents, !!dash.meeting_running);
    if(!dash.meeting_running) officeVisits(agents, dash.activity||[]);
    const s=dash.stats;
    $("#kpis").innerHTML=[["Bài chờ duyệt",s.drafts,s.drafts>0],["Bài đã duyệt / lên lịch",s.approved],["Bài đã đăng",s.posted_total],["Khách nóng",s.leads_hot,s.leads_hot>0],["Khách mới chưa liên hệ",s.leads_new,s.leads_new>0],["Nick đang chạy",s.nicks_total!=null?`${s.nicks_ok||0}/${s.nicks_total||0}`:`${s.sales_ok||0}/${s.sales_total||0}`,!!(s.nicks_problem??s.sales_problem)]]
      .map(([l,v,w])=>`<div class="kpi${w?" warn":""}"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");
    renderCrew(agents);
    $("#feed").innerHTML=dash.activity.length?dash.activity.map(x=>`<li>${avaHtml(x.agent_id)}<div><b>${esc(x.action)}</b> · ${esc(x.detail)}<time>${esc(AGENT[x.agent_id]?.name||"")} · ${fmtTime(x.created_at)} ${fmtDate(x.created_at)}</time></div></li>`).join(""):`<li class="muted">Chưa có hoạt động.</li>`;
    const db=$("#draftBadge"); db.hidden=!s.drafts; db.textContent=s.drafts; setErrBadge(s.errors_new||0);
    document.body.classList.toggle("autopilot",!!s.autopilot);
    if(!DEMO&&s.ai_live) $("#modeBox").innerHTML=`<span class="dot live"></span><b>AI đang hoạt động</b><br>Chi phí tháng này: <b>${usd(s.ai_cost_month||0)}</b>`;
    if($("#bumpToday")) $("#bumpToday").textContent=`Hôm nay đã up ${s.bumps_today||0} lượt`;
    companyBanner(s.company);
    if(s.kpi){ $("#officeKpi").innerHTML=kpiHero(s.kpi,null,`<span class="small muted" style="display:block;margin-top:6px">Xem KPI →</span>`); const bb=$("#bossBadge"); bb.hidden=!s.kpi.boss_pending; bb.textContent=s.kpi.boss_pending; }
    const np=s.nicks_problem??s.sales_problem??0; const prob=np+(s.failed||0); $("#saleBadge").hidden=!np; $("#saleAlert").hidden=!prob;
    $("#saleAlertTxt").textContent=[np?`${np} nick cần sếp đăng nhập lại hoặc xử lý checkpoint`:"",s.failed?`${s.failed} bài đăng lỗi`:""].filter(Boolean).join(" · ");
    $("#liveBadge").hidden=!dash.meeting_running;
    { const pb=$("#prBadge"), pn=(s.prospects_a||0)+(s.prospects_manual||0); pb.hidden=!pn; pb.textContent=pn; pb.title=`${s.prospects_a||0} khách hạng A chưa liên hệ, ${s.prospects_manual||0} tài khoản cần sếp xem tay`; }
    if(ST.view==="prospects"&&!document.querySelector("#v-prospects :focus")) loadProspects(true);
    if(dash.meeting_running && ST.meetingId!==dash.meeting_running){ ST.meetingId=dash.meeting_running; ST.lastMsg=0; ST.msgs=[]; }
  }catch(e){ console.error(e); }
}
function renderCrew(agents){
  const n={working:0,learning:0,meeting:0}; agents.forEach(a=>{ const st=a.status?.state; if(st==="talking") n.meeting++; else if(n[st]!=null) n[st]++; });
  const sum=$("#crewSum"); if(sum) sum.textContent=[n.working&&`${n.working} đang làm việc`,n.learning&&`${n.learning} đang tự học`,n.meeting&&`${n.meeting} đang họp`].filter(Boolean).join(" · ")||"Cả đội đang sẵn sàng.";
  if(document.activeElement&&$("#team").contains(document.activeElement)&&document.activeElement.tagName!=="BUTTON") return;
  $("#team").innerHTML=agents.map(a=>{ const st=a.status?.state||"idle"; const pr=a.progress||{}; const span=Math.max(1,(pr.next_xp||1)-(pr.level_xp||0)); const pct=Math.max(2,Math.min(100,((pr.xp||0)-(pr.level_xp||0))/span*100));
    const rec=(a.recent||[]).slice(0,2);
    return `<button class="crew-item ${st}" data-a="${a.id}">${avaHtml(a.id)}<span class="who">
      <span class="crew-top"><b>${esc(a.name)}</b><span class="lv">Cấp ${a.level||1}</span><span class="chip ${st}">${STATUS_TXT[st]||"Rảnh"}</span></span>
      <span class="crew-role">${esc(a.role)}</span>
      <span class="crew-now">${esc(a.status?.text||"Đang sẵn sàng")}</span>
      <span class="xp" title="${pr.xp||0}/${pr.next_xp||0} kinh nghiệm để lên cấp ${(a.level||1)+1}"><i style="width:${pct}%"></i></span>
      <span class="crew-meta">${num(pr.xp||0)}/${num(pr.next_xp||0)} XP${a.learned_today?` · học ${a.learned_today} kiến thức hôm nay`:""}</span>
      ${rec.length?`<span class="crew-rec">${rec.map(r=>`<span>✓ ${esc(r.action)}${r.detail?`: ${esc(r.detail.slice(0,70))}`:""} <time>${fmtTime(r.created_at)}</time></span>`).join("")}</span>`:""}
    </span></button>`; }).join("");
}
$("#team").addEventListener("click",e=>{ const b=e.target.closest("[data-a]"); if(b) openAgent(b.dataset.a); });
function openAgent(id){
  const a=ST.agents.find(x=>x.id===id)||AGENT[id]; const d=$("#drawer");
  d.innerHTML=`<div class="row" style="justify-content:space-between"><div class="row">${avaHtml(id)}<div><h2>${esc(a.name)}</h2><span class="muted small">${esc(a.role)}</span></div></div><button class="btn ghost" id="dClose" aria-label="Đóng">Đóng</button></div>
   <span class="chip ${a.status?.state||""}" style="align-self:flex-start">${STATUS_TXT[a.status?.state]||"Rảnh"} · ${esc(a.status?.text||"")}</span>
   <div><h3>Nhiệm vụ</h3><p class="muted" style="margin-top:4px">${esc(a.short)}</p></div>
   <div><h3>Tính cách</h3><p class="muted" style="margin-top:4px">${esc(a.personality)}</p></div>
   <div id="dLearn"></div>
   <div><h3>Việc đang mở</h3><ul class="tasks" style="margin-top:6px">${(a.tasks||[]).length?a.tasks.map(t=>`<li>· ${esc(t.title)}</li>`).join(""):'<li class="muted small">Không có việc tồn.</li>'}</ul></div>
   ${id!=="ceo"&&!String(id).startsWith("sale-")?`<div class="ap-note">Luật: sếp chỉ giao việc cho CEO. <button type="button" class="btn sm" data-askceo="${esc(a.name)}">Nhắn CEO về ${esc(a.name)}</button></div>`:""}
   <div class="actions" data-direct>${{lan:'<a class="btn primary" href="#posts">Giao Lan viết bài</a>',tuan:'<button class="btn primary" id="dPlan">Xếp lịch đăng nhóm</button>',ha:'<a class="btn primary" href="#leads">Mở danh sách khách</a>',khoa:'<a class="btn primary" href="#kpi">Xem số liệu</a>',minh:'<a class="btn primary" href="#meeting">Vào phòng họp</a>'}[id]||'<a class="btn primary" href="#sales">Quản lý nick</a>'}</div>`;
  d.hidden=false; $("#dClose").onclick=()=>d.hidden=true; d.querySelectorAll("a").forEach(x=>x.addEventListener("click",()=>d.hidden=true));
  api("/learning").then(L=>{ const x=L.agents.find(z=>z.id===id); if(!x||!$("#dLearn")) return; const pg=x.progress;
    $("#dLearn").innerHTML=`<h3>Phát triển <span class="lv">Cấp ${pg.level}</span></h3>${pg.goal?`<p class="goal" style="margin-top:6px">${esc(pg.goal)}</p>`:""}
      <ul class="lessons" style="margin-top:6px">${x.lessons.slice(0,3).map(l=>`<li style="display:block">${esc(l.text)}</li>`).join("")||'<li class="muted" style="display:block">Chưa có bài học.</li>'}</ul>
      <a class="btn sm" href="#learn" style="margin-top:6px">Xem sổ tay, dạy ${esc(x.name)}</a>`;
    $("#dLearn a").addEventListener("click",()=>d.hidden=true); }).catch(()=>{});
  const p=$("#dPlan"); if(p) p.onclick=async()=>{ const r=await api("/distribution/plan","POST"); toast(r.length?`Tuấn đã xếp ${r.length} bài vào nhóm`:"Chưa có bài đã duyệt để xếp"); d.hidden=true; refresh(); };
}
$("#btnDaily").onclick=async e=>{ e.target.disabled=true; toast("Đang giao việc cho cả đội…"); try{ const r=await api("/run/daily-work","POST"); toast(`${r.draft_mode==="batch"?`Lan gửi lô ${r.drafts} bài (giảm 50%), bài có sau vài phút`:r.drafts?`${r.drafts} bài mới`:"Kho bài đã đủ, không viết thêm"} · ${r.scheduled} bài lên lịch · ${r.follow_ups} khách cần bám`);}catch(err){toast(err.message);} e.target.disabled=false; refresh(); };
$("#btnCall").onclick=()=>{ location.hash="meeting"; setTimeout(()=>startMeeting(),200); };

