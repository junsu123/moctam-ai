/* --------------------------------------------- chỉ đạo nơi đăng (trang Bài đăng) */
const TG_MODES=[["all","Mọi nhóm đủ điều kiện","Tuấn xếp lịch như thường, chỉ bỏ nhóm có từ khóa tránh"],["prefer","Ưu tiên nhóm chỉ định","Nhóm tập trung trước, rồi nhóm có từ khóa, còn bài thì đăng nhóm khác"],["only","Chỉ nhóm chỉ định","Chỉ đăng nhóm tập trung hoặc nhóm có từ khóa, không đăng nhóm khác"]];
const TG_TAG={focus:"Tập trung",match:"Có từ khóa",other:"Nhóm khác",exclude:"Tránh"};
async function loadTg(){ try{ ST.tg=await api("/post-target"); }catch(e){ return; } renderTgSum(); if(!$("#tgForm").hidden&&!$("#tgForm").contains(document.activeElement)) renderTgForm(); }
function renderTgSum(){ const t=ST.tg; if(!t) return; const pv=t.preview, mode=TG_MODES.find(m=>m[0]===t.mode);
  $("#tgSumTxt").textContent=`${mode[1]} · ${pv.will_post} nhóm sẽ được đăng`+(t.mode==="all"&&!t.exclude.length?" (chưa có chỉ đạo riêng)":"");
  $("#tgSum").innerHTML=t.focus.map(g=>`<span class="kw fo" title="Tập trung đăng">★ ${esc(g.name)}</span>`).join("")+t.include.map(k=>`<span class="kw" title="Đăng nhóm có từ khóa này">${esc(k)}</span>`).join("")+t.exclude.map(k=>`<span class="kw no" title="Không đăng nhóm có từ khóa này">✕ ${esc(k)}</span>`).join("")
    +(pv.warn?`<span class="chip warn" style="white-space:normal">${esc(pv.warn)}</span>`:""); }
function tgDraft(){ const f=$("#tgForm"); return {mode:(f.querySelector("input[name=tgMode]:checked")||{}).value||"all",include:$("#tgInc").value,exclude:$("#tgExc").value}; }
function renderTgForm(d){ const t=d?{...ST.tg,mode:d.mode,include:tgWordsUI(d.include),exclude:tgWordsUI(d.exclude)}:ST.tg, f=$("#tgForm");
  const focusIds=new Set(t.focus.map(g=>g.id)); const others=(t.preview.items||[]).filter(i=>!focusIds.has(i.id)&&!i.managed);
  f.innerHTML=`<fieldset class="tg-modes"><legend>Đăng ở đâu</legend>${TG_MODES.map(([v,l,d])=>`<label><input type="radio" name="tgMode" value="${v}"${t.mode===v?" checked":""}><span><b>${l}</b><span>${d}</span></span></label>`).join("")}</fieldset>
    <label class="f" for="tgInc">Đăng ở nhóm có từ khóa<input type="text" id="tgInc" value="${esc(t.include.join(", "))}" placeholder="VD: trà, ngũ cốc, nguồn hàng sỉ"><span class="small muted">So với tên, chủ đề nhóm; không phân biệt dấu. Cách nhau dấu phẩy.</span></label>
    <label class="f" for="tgExc">Không đăng nhóm có từ khóa<input type="text" id="tgExc" value="${esc(t.exclude.join(", "))}" placeholder="VD: quần áo, mỹ phẩm"><span class="small muted">Áp dụng cả khi chọn “Mọi nhóm”.</span></label>
    <div style="grid-column:1/-1"><label class="f" for="tgAdd">Nhóm tập trung đăng<span class="row wrap" style="gap:6px"><select id="tgAdd" style="flex:1;min-width:0"><option value="">Chọn nhóm…</option>${others.map(i=>`<option value="${i.id}">${esc(i.name)}</option>`).join("")}</select><button class="btn sm" type="button" id="tgAddBtn">Thêm</button></span></label>
      <div class="tg-focus">${t.focus.length?t.focus.map(g=>`<span class="kw fo">★ ${esc(g.name)}<button type="button" data-tgdel="${g.id}" aria-label="Bỏ tập trung ${esc(g.name)}">×</button></span>`).join(""):'<span class="small muted">Chưa chọn nhóm nào. Nhóm tập trung được xếp trước và đăng mỗi ngày 1 bài (nhóm khác giãn cách vài ngày).</span>'}</div></div>
    <div class="tg-prev" id="tgPrev" aria-live="polite"></div>
    <div class="row wrap" style="grid-column:1/-1"><button class="btn primary" type="submit">Lưu chỉ đạo</button><button class="btn ghost" type="button" id="tgCancel">Đóng</button><span class="small muted">Tuấn áp dụng từ lần xếp lịch tiếp theo. Bài đã xếp lịch giữ nguyên.</span></div>`;
  if(!d) renderTgPrev(t.preview); }
const tgWordsUI=v=>String(v||"").split(/[,;\n]+/).map(x=>x.trim()).filter(Boolean);
function renderTgPrev(pv){ const box=$("#tgPrev"); if(!box) return; const on=pv.items.filter(i=>i.will_post), off=pv.items.filter(i=>!i.will_post&&!i.managed);
  box.innerHTML=`<b>Xem trước: ${on.length} nhóm sẽ được đăng</b>${off.length?`<span class="small muted"> · ${off.length} nhóm không đăng</span>`:""}${pv.warn?`<p class="small" style="color:var(--danger);margin:4px 0 0">${esc(pv.warn)}</p>`:""}
    <ul>${on.slice(0,40).map(i=>`<li><span class="tg-tag ${i.kind}">${TG_TAG[i.kind]}</span><span class="n" title="${esc(i.why||"")}">${esc(i.name)}</span></li>`).join("")}${off.slice(0,12).map(i=>`<li class="off"><span class="tg-tag ${i.kind}">${i.ready?TG_TAG[i.kind]:"Thiếu link"}</span><span class="n" title="${esc(i.why||"")}">${esc(i.name)}</span></li>`).join("")}</ul>`; }
let tgT=null;
$("#tgEdit").onclick=()=>{ const f=$("#tgForm"), o=f.hidden; f.hidden=!o; $("#tgEdit").setAttribute("aria-expanded",o); $("#tgEdit").textContent=o?"Thu gọn":"Sửa chỉ đạo"; if(o&&ST.tg) renderTgForm(); };
$("#tgForm").addEventListener("input",()=>{ clearTimeout(tgT); tgT=setTimeout(async()=>{ try{ renderTgPrev(await api("/post-target/preview","POST",tgDraft())); }catch(e){} },300); });
$("#tgForm").addEventListener("click",async e=>{
  if(e.target.closest("#tgCancel")){ $("#tgEdit").click(); return; }
  const del=e.target.closest("[data-tgdel]"); const add=e.target.closest("#tgAddBtn");
  if(del||add){ const gid=del?+del.dataset.tgdel:+$("#tgAdd").value; if(!gid) return toast("Chọn một nhóm");
    try{ await api(`/groups/${gid}/focus`,"PUT",{focus:!del}); const d=tgDraft(); ST.tg=await api("/post-target"); renderTgSum(); renderTgForm(d); $("#tgInc").value=d.include; $("#tgExc").value=d.exclude; renderTgPrev(await api("/post-target/preview","POST",d)); }catch(err){ toast(err.message); } } });
$("#tgForm").addEventListener("submit",async e=>{ e.preventDefault(); try{ ST.tg=await api("/post-target","PUT",tgDraft()); renderTgSum(); renderTgForm(); toast("Đã lưu chỉ đạo nơi đăng. Tuấn áp dụng từ lần xếp lịch tiếp theo"); }catch(err){ toast(err.message); } });

