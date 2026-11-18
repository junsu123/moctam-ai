/* --------------------------------------------- sổ kiến thức */
const KB_SRC={rule:["ok","Luật Facebook"],study:["ok","Tự học"],claude:["warn","Hỏi Claude"],boss:["talking","Sếp dạy"],library:["","Thư viện có sẵn"],experience:["ok","Kinh nghiệm"]};
let kbTimer=null;
async function loadKB(){
  let d; try{ d=await api(`/knowledge?agent=${encodeURIComponent($("#kbAgent").value||"")}&q=${encodeURIComponent($("#kbSearch").value||"")}`); }catch(e){ return; }
  ST.kb=d; const m=d.month||{};
  $("#kbSelf").className="chip "+(m.self_rate==null?"":m.self_rate>=50?"ok":"warn"); $("#kbSelf").textContent=m.self_rate==null?"Chưa có lượt hỏi":`Tự lực ${m.self_rate}%`;
  $("#kbSelf").title="Tỉ lệ câu hỏi agent tự trả lời bằng kiến thức đã học, không cần hỏi Claude (30 ngày)";
  $("#kbStats").innerHTML=[[d.total,"Kiến thức trong sổ"],[d.today,"Học hôm nay"],[m.memory||0,"Tự trả lời bằng sổ (30 ngày)"],[m.claude||0,"Phải hỏi Claude (30 ngày)"],[d.pending,"Câu chờ học"]].map(([v,l])=>`<div><b>${num(v)}</b><span>${l}</span></div>`).join("");
  const roles=d.roles||{}; const sel=$("#kbAgent"); if(sel.options.length<2){ sel.innerHTML='<option value="">Cả đội</option>'+Object.entries(roles).map(([k,v])=>`<option value="${k}">${esc(v)}${d.counts[k]?` (${d.counts[k]})`:""}</option>`).join(""); $("#kbTAgent").innerHTML=Object.entries(roles).map(([k,v])=>`<option value="${k}">${esc(v)}</option>`).join(""); }
  $("#kbList").innerHTML=d.items.length?d.items.map(k=>{ const [sc,st]=k.status==="pending"?["warn","Chờ học"]:KB_SRC[k.source]||["",k.source];
    return `<li><div><b>${esc(k.topic||k.question)}</b><div class="meta"><span class="chip">${esc(roles[k.agent_id]||k.agent_id)}</span><span class="chip ${sc}">${st}</span>${k.kind==="faq"?'<span class="chip ok">Trả lời khách</span>':""}${(k.source==="study"||k.source==="library")&&(d.settings||{}).self_study!=="1"?'<span class="chip warn" title="Kiến thức chung, không đưa vào lời dặn khi tự học kiến thức chung đang tắt">Không dùng khi làm việc</span>':""}${k.uses?`<span class="small muted">dùng ${k.uses} lần</span>`:""}<span class="small muted">${fmtDate(k.created_at)}</span></div>
      ${k.question&&k.question!==k.topic?`<div class="small muted">Hỏi: ${esc(k.question)}</div>`:""}<div class="small">${k.status==="pending"?"Đội chưa biết, sẽ học trong buổi tự học tới.":esc(k.content)}</div></div>
      <button type="button" class="btn sm ghost danger" data-kbdel="${k.id}">Xóa</button></li>`; }).join(""):'<li class="muted small">Chưa có kiến thức nào. Bấm “Học ngay” hoặc chờ buổi tự học hằng ngày.</li>';
  const st=d.settings||{}; if(!$("#kbSet").contains(document.activeElement)){ $("#kbOn").checked=st.knowledge_enabled!=="0"; $("#kbStudyOn").checked=st.self_study==="1"; $("#kbIdle").checked=st.idle_learning!=="0"; $("#kbIdleN").value=st.idle_study_per_day||6; $("#kbTime").value=st.study_time||"07:00"; $("#kbN").value=st.study_per_agent||2; }
}
$("#kbAgent").onchange=loadKB;
$("#kbSearch").oninput=()=>{ clearTimeout(kbTimer); kbTimer=setTimeout(loadKB,300); };
$("#kbAsk").addEventListener("submit",async e=>{ e.preventDefault(); const q=$("#kbQ").value.trim(); if(!q) return; const b=e.target.querySelector("button"); b.disabled=true; b.textContent="Đang tra sổ…";
  try{ const r=await api("/knowledge/ask","POST",{question:q});
    $("#kbAns").innerHTML=r.source==="memory"?`<div class="kb-ans"><span class="chip ok">Trả lời từ sổ kiến thức, không cần hỏi Claude</span><p>${esc(r.answer)}</p></div>`
      :r.source==="claude"?`<div class="kb-ans"><span class="chip warn">Đội chưa biết, đã hỏi Claude và lưu vào sổ</span><p>${esc(r.answer)}</p></div>`
      :r.source==="none"?`<div class="kb-ans"><span class="chip">Đội chưa biết</span><p>Câu này đã được ghi vào danh sách “Câu chờ học”. Có khóa Claude, đội sẽ học trong buổi tự học tới.</p></div>`
      :`<div class="kb-ans">Chưa tra cứu được, thử lại sau.</div>`; }
  catch(err){ toast(err.message); } b.disabled=false; b.textContent="Hỏi"; loadKB(); });
$("#kbStudy").onclick=async()=>{ await api("/knowledge/study","POST"); toast((ST.kb?.settings||{}).self_study==="1"?"Cả đội đang tự học kiến thức mới…":"Cả đội đang trả lời các câu sếp và khách hỏi còn chờ…"); setTimeout(loadKB,3000); setTimeout(loadKB,10000); };
$("#kbList").addEventListener("click",async e=>{ const b=e.target.closest("[data-kbdel]"); if(!b) return; if(b.dataset.confirm!=="1"){ b.dataset.confirm="1"; b.textContent="Bấm lần nữa"; return; } await api(`/knowledge/${b.dataset.kbdel}`,"DELETE"); loadKB(); });
$("#kbTeach").addEventListener("submit",async e=>{ e.preventDefault();
  try{ await api("/knowledge","POST",{agent_id:$("#kbTAgent").value,topic:$("#kbTTopic").value,question:$("#kbTQ").value,content:$("#kbTC").value,kind:$("#kbTFaq").checked?"faq":"guide"}); e.target.reset(); toast("Đã dạy. Agent dùng kiến thức này từ việc tiếp theo."); }catch(err){ toast(err.message); } loadKB(); });
$("#kbSet").addEventListener("submit",async e=>{ e.preventDefault(); try{ await api("/knowledge/settings","PUT",{knowledge_enabled:$("#kbOn").checked,self_study:$("#kbStudyOn").checked,study_time:$("#kbTime").value,study_per_agent:+$("#kbN").value,idle_learning:$("#kbIdle").checked,idle_study_per_day:+$("#kbIdleN").value}); toast("Đã lưu cài đặt tự học"); document.activeElement.blur(); }catch(err){ toast(err.message); } loadKB(); });

