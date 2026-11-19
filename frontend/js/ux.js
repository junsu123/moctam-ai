/* --------------------------------------------- trải nghiệm: tải, tìm nhanh, mô tả gọn, ghi chú ẩn được, tiết kiệm CPU */
const UX=(()=>{
  let busyN=0, busyT=null;
  const busy=d=>{ busyN=Math.max(0,busyN+d); clearTimeout(busyT); if(busyN) busyT=setTimeout(()=>document.body.classList.add("busy"),250); else document.body.classList.remove("busy"); };
  const store={ get(k){ try{ return localStorage.getItem(k); }catch(e){ return null; } }, set(k,v){ try{ localStorage.setItem(k,v); }catch(e){} }, del(k){ try{ localStorage.removeItem(k); }catch(e){} } };
  const key=t=>"mt_tip_"+[...t.slice(0,60)].reduce((h,c)=>(h*31+c.charCodeAt(0))|0,7);
  function tidy(v){ const sec=document.getElementById("v-"+v); if(!sec) return;
    sec.querySelectorAll(".vh > div > p:not([data-ux])").forEach(p=>{ p.dataset.ux="1"; p.classList.add("clamp");
      requestAnimationFrame(()=>{ if(p.scrollHeight>p.clientHeight+4){ const b=document.createElement("button"); b.type="button"; b.className="more"; b.textContent="Xem thêm";
        b.onclick=()=>{ const o=p.classList.toggle("open"); b.textContent=o?"Thu gọn":"Xem thêm"; }; p.after(b); } else p.classList.remove("clamp"); }); });
    sec.querySelectorAll(".fr-note:not([id]):not([data-ux])").forEach(n=>{ n.dataset.ux="1"; const k=key(n.textContent.trim());
      if(store.get(k)){ n.hidden=true; return; }
      const x=document.createElement("button"); x.type="button"; x.className="x"; x.setAttribute("aria-label","Ẩn ghi chú này"); x.title="Đã hiểu, ẩn ghi chú"; x.textContent="×";
      x.onclick=()=>{ n.hidden=true; store.set(k,"1"); toast("Đã ẩn ghi chú. Hiện lại: Ctrl K → Hiện lại các ghi chú"); }; n.appendChild(x); }); }
  function showTips(){ try{ Object.keys(localStorage).filter(k=>k.startsWith("mt_tip_")).forEach(k=>store.del(k)); }catch(e){}
    document.querySelectorAll(".fr-note[data-ux]").forEach(n=>n.hidden=false); toast("Đã hiện lại các ghi chú"); }
  // tìm nhanh Ctrl/⌘ K
  let items=[], sel=0;
  function build(){ items=[]; let grp="";
    document.querySelectorAll("#nav > *").forEach(el=>{ if(el.classList.contains("nav-g")) grp=el.textContent.trim();
      else if(el.dataset&&el.dataset.v){ const c=el.cloneNode(true); c.querySelectorAll(".badge").forEach(b=>b.remove());
        items.push({v:el.dataset.v,name:c.textContent.trim(),grp,svg:(el.querySelector("svg")||{}).outerHTML||""}); } });
    items.push({act:showTips,name:"Hiện lại các ghi chú đã ẩn",grp:"Lệnh",svg:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v5h1"/></svg>'}); }
  const norm=s=>s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"").replace(/đ/g,"d");
  function render(){ const q=norm($("#qkIn").value.trim()); const list=items.filter(i=>!q||norm(i.name+" "+i.grp).includes(q)); sel=Math.min(sel,Math.max(0,list.length-1));
    $("#qkList").innerHTML=list.length?list.map((i,n)=>`<li role="option" data-n="${n}" class="${n===sel?"on":""}" aria-selected="${n===sel}">${i.svg}<span>${esc(i.name)}</span><small>${esc(i.grp)}</small></li>`).join(""):'<li class="muted">Không thấy trang nào</li>';
    render.list=list; const on=$("#qkList .on"); if(on) on.scrollIntoView({block:"nearest"}); }
  function go(n){ const i=(render.list||[])[n]; if(!i) return; close(); if(i.act) i.act(); else location.hash=i.v; }
  function open(){ build(); sel=0; $("#qk").hidden=false; $("#qkIn").value=""; render(); $("#qkIn").focus(); }
  function close(){ $("#qk").hidden=true; }
  function init(){
    document.body.insertAdjacentHTML("beforeend",`<div class="qk" id="qk" hidden role="dialog" aria-modal="true" aria-label="Tìm nhanh"><div class="qk-box"><input id="qkIn" placeholder="Tìm trang… (VD: bình luận, khách, cài đặt)" aria-label="Tìm trang" autocomplete="off"><ul class="qk-list" id="qkList" role="listbox"></ul><div class="qk-foot"><span>↑↓ chọn</span><span>Enter mở</span><span>Esc đóng</span></div></div></div>`);
    const nav=$("#nav"); if(nav) nav.insertAdjacentHTML("beforebegin",`<button type="button" class="qk-btn" id="qkBtn"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>Tìm nhanh<kbd>${/Mac/.test(navigator.platform)?"⌘":"Ctrl"} K</kbd></button>`);
    $("#qkBtn").onclick=open; $("#qk").onclick=e=>{ if(e.target.id==="qk") close(); };
    $("#qkIn").oninput=()=>{ sel=0; render(); };
    $("#qkIn").onkeydown=e=>{ const n=(render.list||[]).length; if(e.key==="ArrowDown"){ sel=(sel+1)%Math.max(1,n); render(); e.preventDefault(); } else if(e.key==="ArrowUp"){ sel=(sel-1+n)%Math.max(1,n); render(); e.preventDefault(); } else if(e.key==="Enter"){ go(sel); e.preventDefault(); } else if(e.key==="Escape") close(); };
    $("#qkList").onclick=e=>{ const li=e.target.closest("li[data-n]"); if(li) go(+li.dataset.n); };
    document.addEventListener("keydown",e=>{ if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){ e.preventDefault(); $("#qk").hidden?open():close(); } });
    document.addEventListener("visibilitychange",()=>{ if(!document.hidden&&typeof refresh==="function") refresh(); });
  }
  // tiết kiệm CPU: chỉ làm việc nền khi cửa sổ đang mở; trang không cần số liệu từng giây thì tải thưa hơn
  const idle=()=>document.hidden;
  return {busy,tidy,init,idle,open,close};
})();
UX.init();
{ const _show=show; show=function(v){ _show(v); setTimeout(()=>UX.tidy(ST.view||v),0); }; }
