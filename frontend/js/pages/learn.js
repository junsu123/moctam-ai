/* --------------------------------------------- đào tạo */
const SRC={auto:"Số liệu",ai:"Tự rút ra",boss:"Sếp dạy",meeting:"Cuộc họp"};
const fmtSkill=(v,u)=>v===null||v===undefined?"—":`${v}${u}`;
function trend(s){ if(s.now==null||s.prev==null||s.now===s.prev) return ""; const up=s.now>s.prev; return `<span class="${up?"trend-up":"trend-down"}">${up?"▲":"▼"} ${Math.abs(Math.round((s.now-s.prev)*100)/100)}${s.unit}</span>`; }
function wbars(rows){ const mx=Math.max(0.0001,...rows.map(r=>r.weight)); return rows.sort((a,b)=>b.weight-a.weight).map(r=>`<div class="wb"><span title="${esc(r.name)}">${esc(r.name)}</span><div class="track"><i style="width:${Math.round(r.weight/mx*100)}%"></i></div><span class="num small">${Math.round(r.weight*100)}%</span></div>`).join(""); }
function showCoach(c){
  $("#coMin").textContent=c.min; $("#coDays").textContent=c.days; $("#coTime").textContent=c.time;
  const ready=c.agents.filter(a=>a.pending>=c.min).length;
  $("#coChip").className="chip "+(c.on?(c.waiting?"warn":"ok"):""); $("#coChip").textContent=!c.on?"Đang tắt":c.waiting?"Claude đang chấm":ready?`${ready} agent đủ kết quả`:"Đang gom kết quả";
  $("#coList").innerHTML=c.agents.map(a=>{ const pct=Math.min(100,Math.round(a.pending/c.min*100));
    return `<div class="co-i"><div class="co-h"><b>${esc(a.name)}</b><span class="small muted">${esc(a.job)}</span></div>
      <div class="co-bar" title="${a.pending}/${c.min} kết quả mới"><i style="width:${pct}%"></i></div>
      <div class="small muted">${a.pending}/${c.min} kết quả mới${a.in_batch?` · ${a.in_batch} đang chờ Claude chấm`:""}${a.times?` · đã kèm ${a.times} lần, lần gần nhất ${fmtDate(a.at)}`:" · chưa kèm lần nào"}</div>
      ${a.assessment?`<p class="small co-say">“${esc(a.assessment)}”</p>`:""}
      ${(a.lessons||[]).length?`<ul class="small co-les">${a.lessons.map(l=>`<li>${esc(l)}</li>`).join("")}</ul>`:""}
      ${a.check?`<p class="small muted">Tự kiểm trước khi làm: ${esc(a.check)}</p>`:""}</div>`; }).join("");
  $("#coCost").textContent=`Tháng này: ${c.month_calls} lượt chấm, ${c.month_usd.toFixed(3)} USD`+(c.model?` · mô hình ${c.model.replace("claude-","").replace(/-5-5$/," 5.5")}`:"");
}
async function loadCoach(){ try{ showCoach(await api("/coach")); }catch(e){} }
$("#coRun").onclick=async e=>{ const b=e.target; b.disabled=true;
  try{ const r=await api("/coach","POST"); showCoach(r); toast(r.msg); }catch(err){ toast(err.message); } b.disabled=false; };
async function loadLearn(){
  loadKB(); loadStyle(); loadCoach();
  const d=await api("/learning"); ST.learn=d; const s=await api("/settings");
  $("#angleBars").innerHTML=wbars(d.choices.angles.map(a=>({...a,name:`${a.name} · ${a.n} bài`})));
  $("#prodBars").innerHTML=d.choices.products.length?wbars(d.choices.products):'<p class="small muted">Chưa có sản phẩm.</p>';
  const dr=d.data||{}; $("#learnData").innerHTML=dr.need?(dr.ready
    ?`<span class="muted">Đủ dữ liệu (${dr.posts} bài/30 ngày). Chỉ góc, sản phẩm, giờ có từ ${dr.each} bài và chênh lệch rõ (không phải may rủi) mới được ưu tiên hay thành bài học.</span>`
    :`<span style="color:var(--honey)">Mới ${dr.posts}/${dr.need} bài đã đăng trong 30 ngày: chưa đủ để biết góc nào, giờ nào tốt hơn, nên Lan thử đều các góc và chưa rút bài học từ số liệu.</span>`)
    +(d.ai_last?` <span class="muted">Claude xem lại số liệu mỗi tuần, lần gần nhất ${fmtDate(d.ai_last)}.</span>`:""):"";
  $("#explTxt").textContent=`Thử cái mới ${Math.round(d.choices.explore*100)}%${d.choices.golden_hours.length?` · Giờ vàng: ${d.choices.golden_hours.map(h=>h+"h").join(", ")}`:""}`;
  $("#learnLast").textContent=d.last?`Lần học gần nhất: ${fmtDate(d.last)}`:"Chưa học lần nào";
  $("#lnOn").checked=s.learn_enabled!=="0"; $("#lnTime").value=s.learn_time||"23:15"; $("#lnExp").value=s.learn_explore||"0.25";
  $("#btnLearn").disabled=d.running; $("#btnLearn").textContent=d.running?"Cả đội đang học…":"Cho cả đội học ngay";
  if(document.activeElement&&$("#learnGrid").contains(document.activeElement)&&document.activeElement.tagName==="INPUT") return;
  $("#learnGrid").innerHTML=d.agents.map(a=>{ const p=a.progress; const pct=Math.round((p.xp-p.level_xp)/Math.max(1,p.next_xp-p.level_xp)*100);
    return `<div class="card" data-la="${a.id}">
      <div class="card-h"><div class="row">${avaHtml(a.id)}<div><h3>${esc(a.name)}</h3><span class="small muted">${esc(a.role)}</span></div></div><span class="lv">Cấp ${p.level}</span></div>
      <div><div class="xp"><i style="width:${pct}%"></i></div><span class="small muted">${p.xp} kinh nghiệm · còn ${p.next_xp-p.xp} để lên cấp ${p.level+1}</span></div>
      ${p.goal?`<div class="goal"><b>Mục tiêu hôm nay:</b> ${esc(p.goal)}</div>`:""}
      ${a.skills.length?`<div class="skills">${a.skills.map(s=>`<div><b>${fmtSkill(s.now,s.unit)}</b> ${trend(s)}<span>${esc(s.label)} · tuần trước ${fmtSkill(s.prev,s.unit)}</span></div>`).join("")}</div>`:""}
      <div><b class="small">Sổ tay kinh nghiệm (${a.lessons.length})</b>${a.retired?` <span class="small muted">· đã bỏ ${a.retired} bài học cũ</span>`:""}
        <ul class="lessons" style="margin-top:6px">${a.lessons.length?a.lessons.map(l=>`<li class="${l.pinned?"pin":""}" data-l="${l.id}"><span class="src">${SRC[l.source]||l.source}</span><span>${esc(l.text)}${l.evidence?`<span class="ev">${esc(l.evidence)}</span>`:""}</span>
          <span class="ops"><button type="button" data-op="pin" title="${l.pinned?"Bỏ ghim":"Ghim: luôn dùng"}" aria-label="${l.pinned?"Bỏ ghim":"Ghim"}">${l.pinned?"★":"☆"}</button><button type="button" data-op="del" title="Bỏ bài học này" aria-label="Bỏ bài học">✕</button></span></li>`).join(""):'<li class="muted" style="display:block">Chưa có bài học. Cần thêm bài đã đăng có số khách/bình luận, hoặc sếp dạy trực tiếp bên dưới.</li>'}</ul></div>
      <form class="row" data-teach="${a.id}" data-direct><input type="text" class="grow" id="teach-${a.id}" placeholder="Dạy ${esc(a.name)} một điều…" aria-label="Dạy ${esc(a.name)}"><button class="btn sm primary" type="submit">Dạy</button></form>
    </div>`; }).join("");
}
$("#learnGrid").addEventListener("click",async e=>{ const b=e.target.closest("[data-op]"); if(!b) return; const id=+b.closest("[data-l]").dataset.l;
  const l=ST.learn.agents.flatMap(a=>a.lessons).find(x=>x.id===id);
  if(b.dataset.op==="pin") await api(`/lessons/${id}`,"PATCH",{pinned:l.pinned?0:1});
  if(b.dataset.op==="del"){ await api(`/lessons/${id}`,"PATCH",{status:"retired"}); toast("Đã bỏ bài học này khỏi sổ tay"); }
  loadLearn(); });
$("#learnGrid").addEventListener("submit",async e=>{ const f=e.target.closest("[data-teach]"); if(!f) return; e.preventDefault(); const aid=f.dataset.teach; const v=$(`#teach-${aid}`).value.trim(); if(!v) return;
  try{ await api("/lessons","POST",{agent_id:aid,text:v}); toast(`Đã dạy ${AGENT[aid]?.name||""}. Bài học được ghim và dùng từ lần làm việc tới.`); }catch(err){ toast(err.message); }
  $(`#teach-${aid}`).value=""; document.activeElement.blur(); loadLearn(); });
$("#btnLearn").onclick=async()=>{ await api("/learning/run","POST"); toast("Cả đội đang xem lại số liệu và rút kinh nghiệm…"); $("#btnLearn").disabled=true; setTimeout(loadLearn,4000); setTimeout(loadLearn,12000); refresh(); };
$("#learnForm").addEventListener("submit",async e=>{ e.preventDefault(); await api("/settings","PUT",{learn_enabled:$("#lnOn").checked?"1":"0",learn_time:$("#lnTime").value,learn_explore:$("#lnExp").value}); toast("Đã lưu cài đặt tự học"); loadLearn(); });

