/* =========================================================== trạng thái giao diện */
const ST = {view:"office", agents:[], dash:null, posts:[], groups:[], leads:[], products:[], meetingId:null, lastMsg:0, msgs:[], selLead:null, openPost:new Set(), editPost:null, postedForm:null};
const avaHtml=(id,size)=>{ const a=AGENT[id]; if(!a) return `<div class="ava" style="background:#a86f0e${size?`;width:${size}px;height:${size}px`:""}">S</div>`; return a.face?`<img class="ava" src="${esc(a.face)}" alt="${esc(a.name)}" style="object-fit:cover${size?`;width:${size}px;height:${size}px`:""}">`:`<div class="ava" style="background:${a.look.shirt}">${a.name[0]}</div>`; };

function show(v){
  let sub=""; if(v&&v.includes("/")) [v,sub]=v.split("/");
  if(!document.getElementById("v-"+v)) v="office";
  if(v==="posts"){ let saved=""; try{ saved=localStorage.getItem("postsTab")||""; }catch(e){} postsTab(sub||(ST.view==="posts"?ST.postsTab:saved)||"work"); }
  ST.view=v; document.querySelectorAll(".view").forEach(s=>s.hidden=s.id!=="v-"+v);
  document.querySelectorAll("#nav button").forEach(b=>b.classList.toggle("on",b.dataset.v===v));
  if(v==="office"){ World.mount($("#slot-office")); World.setCam("office"); }
  if(v==="ceo") loadCeoChat(true);
  if(v==="meeting"){ World.mount($("#slot-meeting")); World.setCam("meeting"); loadMeetingPage(); }
  if(v==="errors") loadErrors(); if(v==="posts") loadPosts(); if(v==="comments") loadCm(); if(v==="page") loadPg(); if(v==="trends") loadTr(); if(v==="depts") loadDp(); if(v==="company") loadCompany(); if(v==="kpi") loadKpi(); if(v==="learn") loadLearn(); if(v==="sales") loadSales(); if(v==="groups") loadGroups(); if(v==="leads") loadLeads(); if(v==="prospects") loadProspects(); if(v==="samples"){ loadPostSamples(); loadCeoReview(); } if(v==="fbrules") loadFbp(); if(v==="friends") loadFr(); if(v==="replies") loadRp(); if(v==="website") loadWs(); if(v==="products") loadProducts(); if(v==="setup") loadSettings();
  $(".main").scrollTop=0;
}
$("#nav").addEventListener("click",e=>{ if(e.target.closest("#navMore")){ const o=!document.body.classList.contains("nav-open"); document.body.classList.toggle("nav-open",o); $("#navMore").setAttribute("aria-expanded",o); return; }
  const b=e.target.closest("button[data-v]"); if(b){ document.body.classList.remove("nav-open"); $("#navMore").setAttribute("aria-expanded","false"); location.hash=b.dataset.v; } });
addEventListener("keydown",e=>{ if(e.key==="Escape"&&document.body.classList.contains("nav-open")){ document.body.classList.remove("nav-open"); $("#navMore").setAttribute("aria-expanded","false"); } });
/* chấm đỏ trên nút "Thêm" (điện thoại) khi mục ẩn trong đó có việc cần sếp xem */
setInterval(()=>{ const hid=[...document.querySelectorAll("#nav button[data-v]:not(.pri) .badge")].some(x=>!x.hidden); const mb=$("#moreBadge"); if(mb) mb.hidden=!hid; },1500);
addEventListener("hashchange",()=>show(location.hash.slice(1)||"office"));
$("#camOffice").onclick=()=>World.setCam("office"); $("#camMeet").onclick=()=>World.setCam("meeting");

