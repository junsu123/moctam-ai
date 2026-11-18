/* --------------------------------------------- phòng họp */
async function loadMeetingPage(){
  const [topics,meetings,tasks]=await Promise.all([api("/meetings/topics"),api("/meetings"),api("/tasks")]);
  if(!$("#topicSel").options.length) $("#topicSel").innerHTML=`<option value="">Để trưởng phòng tự chọn</option>`+topics.map(t=>`<option>${esc(t)}</option>`).join("");
  if(!ST.meetingId && meetings[0]){ ST.meetingId=meetings[0].id; ST.lastMsg=0; ST.msgs=[]; }
  $("#history").innerHTML=meetings.filter(m=>m.status==="done").slice(0,8).map(m=>{ const items=typeof m.action_items==="string"?JSON.parse(m.action_items||"[]"):(m.action_items||[]);
    return `<div class="card mtg" data-m="${m.id}" style="padding:10px 12px"><div class="card-h"><b>${fmtDate(m.date)} · ${esc(m.topic)}</b></div><p class="small muted">${esc(m.summary||"")}</p>${items.length?`<ul class="items">${items.map(i=>`<li><b>${esc(AGENT[i.agent_id]?.name)}</b>: ${esc(i.title)}</li>`).join("")}</ul>`:""}</div>`; }).join("")||`<div class="empty">Chưa có cuộc họp nào kết thúc.</div>`;
  $("#taskList").innerHTML=tasks.length?tasks.map(t=>`<li><label><input type="checkbox" data-t="${t.id}" ${t.status==="done"?"checked":""}><span class="${t.status==="done"?"done":""}"><b>${esc(AGENT[t.agent_id]?.name)}</b> · ${esc(t.title)}</span></label></li>`).join(""):`<li class="empty">Việc được giao sau mỗi cuộc họp sẽ hiện ở đây.</li>`;
  pollMeeting();
}
$("#history").addEventListener("click",e=>{ const c=e.target.closest("[data-m]"); if(!c) return; ST.meetingId=+c.dataset.m; ST.lastMsg=0; ST.msgs=[]; $("#transcript").innerHTML=""; pollMeeting(); $(".main").scrollTop=0; });
$("#taskList").addEventListener("change",async e=>{ const id=e.target.dataset.t; if(!id) return; await api(`/tasks/${id}`,"PATCH",{status:e.target.checked?"done":"todo"}); loadMeetingPage(); });
async function startMeeting(){
  const topic=$("#topicCustom").value.trim()||$("#topicSel").value;
  const r=await api("/meetings","POST",{topic}); ST.meetingId=r.id; ST.lastMsg=0; ST.msgs=[]; $("#transcript").innerHTML=""; $("#topicCustom").value="";
  toast("Đã triệu tập họp, mọi người đang vào phòng"); refresh(); pollMeeting();
}
$("#btnStart").onclick=startMeeting;
$("#bossForm").addEventListener("submit",async e=>{ e.preventDefault(); const t=$("#bossText").value.trim(); if(!t) return;
  if(!ST.dash?.meeting_running){ toast("Chưa có cuộc họp nào đang diễn ra"); return; }
  await api(`/meetings/${ST.meetingId}/say`,"POST",{text:t}); $("#bossText").value=""; World.say("boss",t,6000); pollMeeting(); });
let pollBusy=false;
async function pollMeeting(){
  if(!ST.meetingId||pollBusy) return; pollBusy=true;
  try{
    const m=await api(`/meetings/${ST.meetingId}?after=${ST.lastMsg}`);
    $("#mTopic").textContent=m.topic?`Chủ đề: ${m.topic}`:""; $("#mTitle").textContent=`Biên bản ${fmtDate(m.date)}`;
    const ms=$("#mState"); ms.textContent=m.status==="running"?"Đang họp":"Đã kết thúc"; ms.className="chip "+(m.status==="running"?"talking":"");
    if(m.status==="running") World.setBoard(m.topic);
    if(m.messages.length){
      const box=$("#transcript"); if(!ST.msgs.length) box.innerHTML="";
      for(const x of m.messages){ ST.msgs.push(x); ST.lastMsg=Math.max(ST.lastMsg,x.id);
        const boss=x.agent_id==="boss"; const nm=boss?"Sếp":AGENT[x.agent_id]?.name;
        box.insertAdjacentHTML("beforeend",`<div class="msg${boss?" boss":""}">${avaHtml(x.agent_id)}<div class="body"><header><b>${esc(nm)}</b><span class="phase">${PHASE[x.phase]||""}</span><span class="small muted">${fmtTime(x.created_at)}</span></header>${esc(x.content)}</div></div>`); }
      box.scrollTop=box.scrollHeight;
      const last=m.messages[m.messages.length-1]; if(m.status==="running"&&last.agent_id!=="boss") World.say(last.agent_id,last.content,8000);
    } else if(!ST.msgs.length){ $("#transcript").innerHTML=`<div class="empty">${m.status==="running"?"Mọi người đang đi vào phòng họp…":"Cuộc họp chưa có nội dung."}</div>`; }
    if(m.status!=="running" && ST.view==="meeting" && $("#taskList").dataset.m!=String(m.id)){ $("#taskList").dataset.m=m.id; }
  }catch(e){ console.error(e); }
  pollBusy=false;
}

