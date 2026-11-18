/* --------------------------------------------- khởi động */
(async()=>{
  const h=await detect();
  if(!DEMO){ checkHealth(h); setInterval(pollHealth,20000); [1500,4000,8000].forEach(t=>setTimeout(pollHealth,t)); }
  $("#demoBanner").hidden=!DEMO;
  $("#modeBox").innerHTML = DEMO ? `<span class="dot sim"></span><b>Bản xem trước</b><br>Dữ liệu mẫu, không lưu lại.` : h.ai_live ? `<span class="dot live"></span><b>AI đang hoạt động</b><br>${esc(h.model)}` : `<span class="dot sim"></span><b>Chế độ mô phỏng</b><br><a href="#setup">Nhập khóa API Claude</a>`;
  try{ const s=await api("/settings"); $("#coName").textContent=s.company_name; }catch(e){}
  show(location.hash.slice(1)||"office");
  await refresh();
  setInterval(refresh,3000);
  setInterval(()=>{ if(ST.view==="ceo") loadCeoChat(); },6000);
  setInterval(()=>{ if(ST.view==="company") loadCompany(); if(ST.view==="kpi") loadKpi(); if(ST.view==="sales") loadSales(); if(ST.view==="posts"&&!ST.editPost&&!ST.postedForm&&ST.posts.some(p=>p.status==="posting")) loadPosts(); },4000);
  setInterval(()=>{ if(ST.dash?.meeting_running||ST.view==="meeting") pollMeeting(); },1500);
  try{ const h=DEMO?await api("/health"):null; if(h) setTz(h.time); }catch(e){}
  const tick=()=>{ const c=$("#clock"); c.textContent=tzNow().slice(11,16)+" · "+(TZ.label.match(/GMT[^)]*/)||[""])[0]; c.title="Giờ trên phần mềm: "+TZ.label; }; tick(); setInterval(tick,20000);
})();
