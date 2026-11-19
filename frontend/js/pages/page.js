/* --------------------------------------------- nuôi nhiều Page (Chrome của nick quản trị từng Trang, không dùng API) */
async function loadPg(){ try{ ST.pg=await api("/page-grow"); }catch(e){ toast(e.message); return; } renderPg(); }
function pgNicks(sel){ return `<option value="">Chọn nick</option>`+ST.pg.nicks.map(n=>`<option value="${n.id}" ${sel==n.id?"selected":""}>${esc(n.name)} (${esc(n.sale_name||"")})</option>`).join(""); }
function renderPg(){ const d=ST.pg, st=d.settings||{}, r=$("#pgReady"), hm=t=>t?`${t.slice(11,16)} ${t.slice(8,10)}/${t.slice(5,7)}`:"", nf=v=>v==null?"—":Number(v).toLocaleString("vi-VN");
  r.hidden=!d.ready; r.innerHTML=d.ready?`<b>Chưa chạy được:</b> ${esc(d.ready)}.`:"";
  const act=d.pages.filter(p=>p.status==="active"), fd=d.followers_7d;
  $("#pgStats").innerHTML=[[act.length,"Trang đang nuôi"],[nf(d.followers),"Người theo dõi (mọi Trang)"],[fd==null?"—":(fd>=0?"+":"")+fd,"7 ngày qua"],[d.posted.length,"Bài Trang 30 ngày"]]
    .map(([v,l])=>`<div class="pr-stat"><b>${v}</b><span>${l}</span></div>`).join("");
  $("#pgStatAt").textContent=d.stats_at?`Số liệu đọc lần cuối ${hm(d.stats_at)} (mỗi ngày nick quản trị đọc một lần trong ca làm việc).`:"Nick quản trị đọc người theo dõi và tương tác trong ca làm việc đầu tiên mỗi ngày.";
  $("#pgPages").innerHTML=d.pages.length?d.pages.map(p=>`<article class="cm-item st-${p.status==="active"?(p.ready?"failed":"done"):"x"}" data-pgid="${p.id}"><div class="top"><span class="chip ${p.status==="active"?(p.ready?"bad":"ok"):""}">${p.status==="active"?(p.ready?"Chưa chạy được":"Đang nuôi"):"Tạm dừng"}</span><b>${esc(p.name)}</b>${p.niche?`<span>· ${esc(p.niche)}</span>`:""}</div>
      <p class="small muted" style="margin:0">${p.admin_name?`Nick ${esc(p.admin_name)}`:"Chưa chọn nick"} · ${p.posts_per_day} bài/ngày lúc ${esc(p.times||"")} · ${nf(p.followers)} người theo dõi${p.followers_7d!=null?` (${p.followers_7d>=0?"+":""}${p.followers_7d} 7 ngày)`:""}</p>
      ${p.keywords?`<p class="small" style="margin:2px 0"><b>Từ khóa:</b> ${esc(p.keywords)}</p>`:""}${p.ready?`<p class="er" style="margin:0">${esc(p.ready)}</p>`:""}
      <details class="small"><summary>Sửa Trang</summary><div style="display:grid;gap:6px;margin-top:6px">
        <label>Tên Trang<input data-f="name" value="${esc(p.name)}"></label><label>Link Trang<input type="url" data-f="url" value="${esc(p.url||"")}"></label>
        <label>Nick quản trị<select data-f="admin_account_id">${pgNicks(p.admin_account_id)}</select></label>
        <div class="row wrap" style="gap:6px"><label>Bài/ngày <input type="number" data-f="posts_per_day" min="1" max="3" value="${p.posts_per_day||1}" style="width:64px"></label><label>Giờ đăng <input data-f="times" value="${esc(p.times||"")}" style="width:130px"></label></div>
        <label>Ngành nghề<input data-f="niche" value="${esc(p.niche||"")}"></label><label>Từ khóa nội dung<input data-f="keywords" value="${esc(p.keywords||"")}"></label>
        <div><button type="button" class="btn sm primary" data-pga="save">Lưu</button></div></div></details>
      <div class="acts">${p.url?`<a class="btn sm ghost" href="${esc(p.url)}" target="_blank" rel="noopener">Mở Trang</a>`:""}${p.status==="active"?`<button type="button" class="btn sm" data-pga="write">Viết 1 bài ngay</button>`:""}<button type="button" class="btn sm ghost" data-pga="${p.status==="active"?"paused":"active"}">${p.status==="active"?"Tạm dừng":"Nuôi lại"}</button></div></article>`).join("")
    :'<p class="muted small">Chưa có Trang nào. Bấm <b>+ Thêm Trang</b> bên dưới: dán link Trang và chọn nick quản trị.</p>';
  if(!d.pages.length) $("#pgAddBox").open=true;
  $('#pgAdd [data-a="admin_account_id"]').innerHTML=pgNicks("");
  const T=Object.fromEntries(d.topics.map(t=>[t.topic,t.label]));
  $("#pgRevNote").innerHTML=d.review?'Bài chờ sếp duyệt ở mục <a href="#nhipages">Các Trang của Nhi</a>. Duyệt xong bài xếp đăng đúng giờ.':"Đang tắt duyệt: bài viết xong xếp đăng luôn.";
  $("#pgUp").innerHTML=d.upcoming.length?d.upcoming.map(p=>`<article class="cm-item st-scheduled"><div class="top"><span class="chip ${p.status==="scheduled"?"warn":""}">${p.status==="scheduled"?"Đăng lúc "+hm(p.scheduled_for):"Chờ sếp duyệt"}</span><b>${esc(p.page_name||"")}</b><span>· ${esc(T[p.page_topic]||"Bài Trang")}</span></div>
      <p class="tx">${esc((p.content||"").slice(0,260))}${(p.content||"").length>260?"…":""}</p><div class="acts"><button type="button" class="btn sm ghost" data-pgskip="${p.id}">Bỏ bài này</button></div></article>`).join("")
    :`<p class="muted small">Chưa có bài sắp đăng. Nhi viết lúc 07:30 mỗi sáng, hoặc bấm <b>Viết 1 bài ngay</b> ở Trang.</p>`;
  $("#pgPosted").innerHTML=d.posted.length?d.posted.slice(0,12).map(p=>`<li><span class="nm">${esc((p.content||"").split("\n")[0].slice(0,60))}</span><span class="small muted">${esc(p.page_name||"")} · ${esc(T[p.page_topic]||"Bài Trang")} · ${hm(p.posted_at)} · ${p.reactions||0} cảm xúc · ${p.comments||0} bình luận · ${p.shares||0} chia sẻ${p.leads?` · ${p.leads} khách`:""}</span>${p.posted_url?`<a class="btn sm ghost" href="${esc(p.posted_url)}" target="_blank" rel="noopener">Mở bài</a>`:""}</li>`).join("")
    :'<li class="muted small">Chưa có bài Trang nào trong 30 ngày.</li>';
  const mx=Math.max(1,...d.topics.map(t=>t.eng));
  $("#pgTopics").innerHTML=d.topics.map(t=>`<li><label class="row small" style="gap:6px;min-width:0"><input type="checkbox" data-pgtopic="${t.topic}" ${t.on?"checked":""}><span class="nm">${esc(t.label)}</span></label><span class="small muted">${t.n} bài · tương tác TB ${t.eng}${t.leads?` · ${t.leads} khách`:""}</span><span class="meter" style="flex:1 1 80px;min-width:60px;height:6px;border-radius:5px;background:var(--panel-2);overflow:hidden"><i style="display:block;height:100%;width:${Math.round(t.eng/mx*100)}%;background:var(--accent)"></i></span></li>`).join("");
  $("#pgOn").checked=st.page_grow_on!=="0"; $("#pgSale").value=st.page_grow_sale_pct||20; }
$("#pgForm").onsubmit=async e=>{ e.preventDefault(); const off=[...document.querySelectorAll("[data-pgtopic]")].filter(x=>!x.checked).map(x=>x.dataset.pgtopic).join(",");
  try{ ST.pg=await api("/page-grow/settings","PUT",{page_grow_on:$("#pgOn").checked?"1":"0",page_grow_sale_pct:$("#pgSale").value,page_grow_off:off}); renderPg(); toast("Đã lưu cài đặt nuôi Page"); }catch(err){ toast(err.message); } };
$("#pgAdd").onsubmit=async e=>{ e.preventDefault(); const b={}; e.target.querySelectorAll("[data-a]").forEach(x=>b[x.dataset.a]=x.value.trim());
  try{ ST.pg=await api("/page-grow/pages","POST",b); e.target.reset(); renderPg(); toast(`Đã thêm Trang ${b.name}: Nhi bắt đầu nuôi từ sáng mai, hoặc bấm Viết 1 bài ngay`); }catch(err){ toast(err.message); } };
const pgDone=p=>toast(p.status==="page_review"?`Nhi đã viết bài cho ${p.page_name||"Trang"}, chờ sếp duyệt ở mục Các Trang của Nhi`:`Nhi đã viết bài, nick quản trị đăng lúc ${(p.scheduled_for||"").slice(11,16)}`);
$("#pgWrite").onclick=async e=>{ e.target.disabled=true; try{ pgDone(await api("/page-grow/write","POST",{})); loadPg(); }catch(err){ toast(err.message); } e.target.disabled=false; };
$("#v-page").addEventListener("click",async e=>{ const sk=e.target.closest("[data-pgskip]"); if(sk){ try{ ST.pg=await api(`/page-grow/${sk.dataset.pgskip}/skip`,"POST"); renderPg(); toast("Đã bỏ bài này"); }catch(err){ toast(err.message); } return; }
  const b=e.target.closest("[data-pga]"); if(!b) return; const card=b.closest("[data-pgid]"), id=card.dataset.pgid, a=b.dataset.pga; b.disabled=true;
  try{ if(a==="write"){ const p=await api("/page-grow/write","POST",{page_id:+id}); pgDone(p); loadPg(); return; }
    if(a==="save"){ const body={}; card.querySelectorAll("[data-f]").forEach(x=>body[x.dataset.f]=x.value.trim()); ST.pg=await api(`/page-grow/pages/${id}`,"PUT",body); toast("Đã lưu Trang"); }
    else { ST.pg=await api(`/page-grow/pages/${id}/status`,"POST",{status:a}); toast(a==="paused"?"Đã tạm dừng Trang, bỏ các bài chưa đăng":"Nhi nuôi lại Trang này"); }
    renderPg(); }catch(err){ toast(err.message); b.disabled=false; } });
$("#v-page").addEventListener("change",async e=>{ if(!e.target.matches("[data-pgtopic]")) return; const off=[...document.querySelectorAll("[data-pgtopic]")].filter(x=>!x.checked).map(x=>x.dataset.pgtopic).join(",");
  try{ ST.pg=await api("/page-grow/settings","PUT",{page_grow_off:off}); renderPg(); }catch(err){ toast(err.message); } });
