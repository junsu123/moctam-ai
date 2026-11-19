/* =========================================================== API */
let DEMO = false;
const VIEW_NAME={office:"Văn phòng",company:"Công ty",meeting:"Phòng họp",posts:"Bài đăng",sales:"Nhân viên sale",groups:"Hội nhóm",leads:"Khách hàng",products:"Sản phẩm",kpi:"KPI & Báo cáo",learn:"Đào tạo",setup:"Cài đặt",errors:"Lỗi"};
const ERR={queue:[],seen:{},lastAt:0};
/* Ghi lỗi người dùng gặp ở màn hình hiện tại vào sổ lỗi (gộp lỗi trùng trong 10 giây, giữ hàng đợi khi mất kết nối) */
function reportUi(title,message,detail="",action=""){
  const key=title+"|"+message; if(ERR.seen[key]&&Date.now()-ERR.seen[key]<10000) return; ERR.seen[key]=Date.now(); ERR.lastAt=Date.now();
  const e={title:String(title).slice(0,200),message:String(message||"").slice(0,1000),detail:String(detail||"").slice(0,4000),screen:ST.view||"",action:String(action).slice(0,200)};
  if(DEMO){ Demo.handle("POST","/api/errors",e); return errBadge(); }
  if(ERR.off) return; ERR.queue.push(e); if(ERR.queue.length>30) ERR.queue.shift(); flushErr();
}
async function flushErr(){
  while(ERR.queue.length){ const e=ERR.queue[0];
    try{ const r=await fetch("/api/errors",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(e)});
      if(r.status===404){ ERR.queue=[]; ERR.off=true; pollHealth(); return; }   // phần mềm đang chạy bản cũ chưa có sổ lỗi: không gửi lặp lại
      if(!r.ok) break; ERR.queue.shift(); }
    catch(x){ break; } }
  errBadge();
}
async function api(path, method="GET", body){  // thanh tiến trình khi thao tác lâu hơn 0,25 giây (trừ các lần tự cập nhật nền)
  const bg=method==="GET"&&/^\/(agents|dashboard|health|meetings|errors|ceo\/chat)/.test(path);
  if(!bg&&typeof UX!=="undefined") UX.busy(1);
  try{ return await _api(path,method,body); } finally{ if(!bg&&typeof UX!=="undefined") UX.busy(-1); } }
async function _api(path, method="GET", body){
  const act=`${method} ${path}`;
  if(DEMO){ try{ return await Demo.handle(method, "/api"+path, body||{}); }
    catch(e){ if(!path.startsWith("/errors")) reportUi(`Thao tác lỗi ở màn hình ${VIEW_NAME[ST.view]||ST.view}`,e.message,"",act); throw e; } }
  let r;
  try{ r = await fetch("/api"+path, {method, headers:{"content-type":"application/json","x-screen":ST.view||"","x-action":encodeURIComponent(act)}, body: body?JSON.stringify(body):undefined}); setOffline(false); if(ERR.queue.length) flushErr(); }
  catch(e){ setOffline(true); if(method!=="GET") reportUi("Mất kết nối với phần mềm trên máy","Mất kết nối với phần mềm trên máy khi thao tác ở màn hình "+(VIEW_NAME[ST.view]||ST.view),"",act); throw new Error("Mất kết nối với phần mềm trên máy"); }
  if(!r.ok){ const t=await r.text(); let m=t, eid=null; try{ const j=JSON.parse(t); m=j.detail||t; eid=j.error_id; }catch(e){}
    m=typeof m==="string"?m:JSON.stringify(m);
    if(eid){ ERR.lastAt=Date.now(); errBadge(); }   // lỗi phần mềm: máy chủ đã ghi sẵn
    else if(!path.startsWith("/errors")&&(method!=="GET"||r.status>=500)) reportUi(`Thao tác lỗi ở màn hình ${VIEW_NAME[ST.view]||ST.view}`,m,`${act} → HTTP ${r.status}`,act);
    throw new Error(String(m).slice(0,300)); }
  return r.json();
}
addEventListener("error",e=>{ if(e.message) reportUi("Lỗi hiển thị ở màn hình "+(VIEW_NAME[ST.view]||ST.view||""),e.message,`${e.filename||""}:${e.lineno||""}:${e.colno||""}\n${e.error&&e.error.stack||""}`); });
addEventListener("unhandledrejection",e=>{ const r=e.reason; const m=r&&r.message||String(r); if(/Mất kết nối/.test(m)) return; reportUi("Lỗi xử lý ở màn hình "+(VIEW_NAME[ST.view]||ST.view||""),m,r&&r.stack||""); });
async function detect(){
  try{
    const ctl=new AbortController(); const t=setTimeout(()=>ctl.abort(),2500);
    const r=await fetch("/api/health",{signal:ctl.signal}); clearTimeout(t);
    const j=await r.json(); if(!j.ok) throw 0; return j;
  }catch(e){
    if(window.__BACKEND__){ setOffline(true); await new Promise(r=>setTimeout(r,3000)); return detect(); }
    DEMO=true; return Demo.handle("GET","/api/health");
  }
}
function setOffline(off){ const b=$("#offline"); if(b) b.hidden=!off; }

