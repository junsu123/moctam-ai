/* --------------------------------------------- sếp giao việc cho CEO */
async function renderOrders(){ const box=$("#ceoOrders"); if(!box) return; let d; try{ d=await api("/ceo/chat"); }catch(e){ return; }
  const AG={all:"Cả đội",minh:"Minh",lan:"Lan",tuan:"Tuấn",ha:"Hà",khoa:"Khoa",mai:"Mai",vy:"Vy",bao:"Bảo",nhi:"Nhi",ceo:"CEO"};
  box.innerHTML=d.orders.length?`<h4 style="margin:4px 0 6px;font-size:13px">Chỉ đạo lâu dài của sếp (CEO đưa vào lời dặn của agent)</h4><ul class="recent">${d.orders.map(o=>`<li><b>${esc(AG[o.agent]||o.agent)}</b><span>${esc(o.text)}</span><span class="muted small">${fmtDate(o.created_at)}</span><button type="button" class="btn sm ghost danger" data-orderoff="${o.id}">Bỏ</button></li>`).join("")}</ul>`:""; }
document.addEventListener("click",async e=>{ const b=e.target.closest("[data-orderoff]"); if(!b) return; await api(`/ceo/orders/${b.dataset.orderoff}`,"DELETE"); toast("Đã bỏ chỉ đạo"); renderOrders(); });
async function loadCeoChat(force){
  if(!force&&document.activeElement===$("#ceoIn")&&ST.ceoChat) return;
  let d; try{ d=await api("/ceo/chat"); }catch(e){ return; }
  const n=(d.history||[]).length, changed=!ST.ceoChat||ST.ceoChat.history.length!==n; ST.ceoChat=d;
  const run=$("#ceoRun"); run.hidden=!(d.running||[]).length; run.innerHTML=(d.running||[]).length?`<span class="dot live"></span><b>Đang làm:</b> ${d.running.map(esc).join(" · ")}`:"";
  $("#ceoChatMode").textContent=d.autopilot?"Luật: sếp chỉ giao việc cho CEO, CEO tự vận hành":"Sếp đang giao việc trực tiếp cho từng agent";
  if(changed){ const log=$("#ceoLog");
    const lastQ=(()=>{ const m=d.history[n-1]; return m&&m.role!=="boss"?(m.actions||[]).find(a=>a&&a.type==="clarify"):null; })();
    log.innerHTML=n?d.history.slice(-12).map(m=>`<div class="${m.role==="boss"?"b":"c"}" style="white-space:pre-line">${esc(m.text)}<time>${m.role==="boss"?"Sếp":"CEO Đức"}${m.via==="telegram"?" · Telegram":""} · ${fmtTime(m.created_at)}</time></div>`).join("")
      :'<div class="c">Dạ, sếp cứ giao việc cho em. Em sẽ tự chia việc cho Lan, Tuấn, Hà, Khoa và các bạn sale, rồi báo lại sếp. Agent nào làm chưa đúng, sếp nói em sửa.</div>';
    if(lastQ&&(lastQ.options||[]).length) log.insertAdjacentHTML("beforeend",`<div class="chips ceo-q">${lastQ.options.map(o=>`<button type="button" data-ceoq="${esc(o)}">${esc(o)}</button>`).join("")}</div>`);
    log.scrollTop=log.scrollHeight; }
  if(!$("#ceoSugg").children.length) $("#ceoSugg").innerHTML=(d.suggestions||[]).map(t=>`<button type="button" data-sugg="${esc(t)}">${esc(t)}</button>`).join("");
}
$("#ceoForm").addEventListener("submit",async e=>{ e.preventDefault(); const v=$("#ceoIn").value.trim(); if(!v) return;
  const btn=e.target.querySelector("button"); btn.disabled=true; btn.textContent="CEO đang xử lý…";
  $("#ceoLog").insertAdjacentHTML("beforeend",`<div class="b">${esc(v)}<time>Sếp · vừa xong</time></div>`); $("#ceoLog").scrollTop=1e6;
  try{ await api("/ceo/chat","POST",{text:v}); $("#ceoIn").value=""; }catch(err){ toast(err.message); }
  btn.disabled=false; btn.textContent="Giao việc"; ST.ceoChat=null; loadCeoChat(true); refresh(); });
$("#ceoLog").addEventListener("click",async e=>{ const b=e.target.closest("[data-ceoq]"); if(!b) return; $("#ceoIn").value=b.dataset.ceoq; $("#ceoForm").requestSubmit(); });
$("#ceoSugg").addEventListener("click",e=>{ const b=e.target.closest("[data-sugg]"); if(!b) return; $("#ceoIn").value=b.dataset.sugg; $("#ceoIn").focus(); });
document.addEventListener("click",e=>{ const b=e.target.closest("[data-askceo]"); if(!b) return; $("#drawer").hidden=true; location.hash="ceo";
  setTimeout(()=>{ $("#ceoIn").value=`${b.dataset.askceo} `; $("#ceoIn").focus(); },300); });

