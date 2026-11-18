/* --------------------------------------------- nuôi Page (Chrome của nick quản trị, không dùng API) */
async function loadPg(){ try{ ST.pg=await api("/page-grow"); }catch(e){ toast(e.message); return; } renderPg(); }
function renderPg(){ const d=ST.pg, st=d.settings||{}, r=$("#pgReady");
  r.hidden=!d.ready; r.innerHTML=d.ready?`<b>Chưa chạy được:</b> ${esc(d.ready)}. Điền ở phần Cài đặt bên dưới.`:"";
  const fd=d.followers_7d; $("#pgStats").innerHTML=[[d.followers==null?"—":d.followers.toLocaleString("vi-VN"),"Người theo dõi"],[fd==null?"—":(fd>=0?"+":"")+fd,"7 ngày qua"],[d.posted.length,"Bài Trang 30 ngày"],[d.avg_eng==null?"—":d.avg_eng,"Tương tác trung bình / bài"]]
    .map(([v,l])=>`<div class="pr-stat"><b>${v}</b><span>${l}</span></div>`).join("");
  const T=Object.fromEntries(d.topics.map(t=>[t.topic,t.label])), hm=t=>t?`${t.slice(11,16)} ${t.slice(8,10)}/${t.slice(5,7)}`:"";
  $("#pgUp").innerHTML=d.upcoming.length?d.upcoming.map(p=>`<article class="cm-item st-scheduled" data-pg="${p.id}"><div class="top"><span class="chip ${p.status==="scheduled"?"warn":""}">${p.status==="scheduled"?"Đăng lúc "+hm(p.scheduled_for):"Chờ duyệt"}</span><b>${esc(T[p.page_topic]||"Bài Trang")}</b></div>
      <p class="tx">${esc((p.content||"").slice(0,260))}${(p.content||"").length>260?"…":""}</p><div class="acts"><button type="button" class="btn sm ghost" data-pgskip="${p.id}">Bỏ bài này</button></div></article>`).join("")
    :`<p class="muted small">Chưa có bài sắp đăng. Lan viết lúc 07:30 mỗi sáng, hoặc bấm <b>Lan viết 1 bài ngay</b>.</p>`;
  $("#pgStatAt").textContent=d.stats_at?`Số liệu đọc lúc ${hm(d.stats_at)} (mỗi ngày nick quản trị đọc một lần trong ca làm việc).`:"Chưa đọc số liệu: nick quản trị đọc trong ca làm việc đầu tiên mỗi ngày.";
  $("#pgPosted").innerHTML=d.posted.length?d.posted.slice(0,10).map(p=>`<li><span class="nm">${esc((p.content||"").split("\n")[0].slice(0,60))}</span><span class="small muted">${esc(T[p.page_topic]||"Bài Trang")} · ${hm(p.posted_at)} · ${p.reactions||0} cảm xúc · ${p.comments||0} bình luận · ${p.shares||0} chia sẻ${p.leads?` · ${p.leads} khách`:""}</span>${p.posted_url?`<a class="btn sm ghost" href="${esc(p.posted_url)}" target="_blank" rel="noopener">Mở bài</a>`:""}</li>`).join("")
    :'<li class="muted small">Chưa có bài Trang nào trong 30 ngày.</li>';
  const mx=Math.max(1,...d.topics.map(t=>t.eng));
  $("#pgTopics").innerHTML=d.topics.map(t=>`<li><label class="row small" style="gap:6px;min-width:0"><input type="checkbox" data-pgtopic="${t.topic}" ${t.on?"checked":""}><span class="nm">${esc(t.label)}</span></label><span class="small muted">${t.n} bài · tương tác TB ${t.eng}${t.leads?` · ${t.leads} khách`:""}</span><span class="meter" style="flex:1 1 80px;min-width:60px;height:6px;border-radius:5px;background:var(--panel-2);overflow:hidden"><i style="display:block;height:100%;width:${Math.round(t.eng/mx*100)}%;background:var(--accent)"></i></span></li>`).join("");
  $("#pgOn").checked=st.page_grow_on!=="0"; $("#pgUrl").value=st.page_url||""; $("#pgPer").value=st.page_grow_per_day||1; $("#pgTimes").value=st.page_grow_times||"08:30,20:30";
  $("#pgSale").value=st.page_grow_sale_pct||20; $("#pgReview").checked=st.page_grow_review==="1";
  $("#pgAdmin").innerHTML=`<option value="">Chọn nick</option>`+d.nicks.map(n=>`<option value="${n.id}">${esc(n.name)} (${esc(n.sale_name||"")})</option>`).join(""); $("#pgAdmin").value=st.page_admin_account||""; }
$("#pgForm").onsubmit=async e=>{ e.preventDefault(); const off=[...document.querySelectorAll("[data-pgtopic]")].filter(x=>!x.checked).map(x=>x.dataset.pgtopic).join(",");
  try{ ST.pg=await api("/page-grow/settings","PUT",{page_grow_on:$("#pgOn").checked?"1":"0",page_url:$("#pgUrl").value.trim(),page_admin_account:$("#pgAdmin").value,page_grow_per_day:$("#pgPer").value,
    page_grow_times:$("#pgTimes").value,page_grow_sale_pct:$("#pgSale").value,page_grow_review:$("#pgReview").checked?"1":"0",page_grow_off:off}); renderPg(); toast("Đã lưu cài đặt nuôi Page"); }catch(err){ toast(err.message); } };
$("#pgWrite").onclick=async e=>{ e.target.disabled=true; try{ const p=await api("/page-grow/write","POST",{}); toast(p.status==="draft"?"Lan đã viết bài, chờ sếp duyệt ở mục Bài đăng":`Lan đã viết bài, nick quản trị đăng lúc ${(p.scheduled_for||"").slice(11,16)}`); loadPg(); }catch(err){ toast(err.message); } e.target.disabled=false; };
$("#v-page").addEventListener("click",async e=>{ const b=e.target.closest("[data-pgskip]"); if(!b) return; try{ ST.pg=await api(`/page-grow/${b.dataset.pgskip}/skip`,"POST"); renderPg(); toast("Đã bỏ bài này"); }catch(err){ toast(err.message); } });
$("#v-page").addEventListener("change",async e=>{ if(!e.target.matches("[data-pgtopic]")) return; const off=[...document.querySelectorAll("[data-pgtopic]")].filter(x=>!x.checked).map(x=>x.dataset.pgtopic).join(",");
  try{ ST.pg=await api("/page-grow/settings","PUT",{page_grow_off:off}); renderPg(); }catch(err){ toast(err.message); } });

