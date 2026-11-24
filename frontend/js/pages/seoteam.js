// Website → tab Đội SEO: Vy (SEO Leader), Hương (Content), Khải (Technical), kết nối Google
const SEO_SEV={high:["bad","Nặng"],med:["warn","Vừa"],low:["","Nhẹ"]}, SEO_WHO={khai:"Khải",huong:"Hương",sep:"Sếp",vy:"Vy"};
const SEO_PST={approved:["ok","Đã lên website"],review:["warn","Chờ sếp duyệt"],rejected:["bad","Sếp bỏ"],none:["","Chưa viết"]};
async function loadSeo(){ try{ ST.seo=await api("/seo"); }catch(e){ toast(e.message); return; } renderSeo(); }
function seoDelta(a,b,lowGood){ if(b==null||a==null||!b) return ""; const d=a-b; if(!d) return ""; const good=lowGood?d<0:d>0; return ` <span class="${good?"ok":"err"} small">${d>0?"+":""}${Math.round(d*10)/10}</span>`; }
function renderSeo(){
  const d=ST.seo; if(!d) return; const c=d.summary.cur, p=d.summary.prev, g=d.google, a=d.audit;
  $("#seoStats").innerHTML=[[c.clicks,"Lượt bấm từ Google · 28 ngày",seoDelta(c.clicks,p.clicks)],[c.impressions,"Lượt hiển thị trên Google",seoDelta(c.impressions,p.impressions)],
    [c.position??"—","Vị trí trung bình",seoDelta(c.position,p.position,true)],[c.contacts,"Bấm Zalo / Gọi trên web (GA4)",seoDelta(c.contacts,p.contacts)],
    [a?a.score:"—","Sức khỏe kỹ thuật (Khải)",a?seoDelta(a.score,a.prev):""]].map(([v,l,x])=>`<div class="pr-stat" style="cursor:default"><b>${esc(String(v))}${x}</b><span>${l}</span></div>`).join("");
  const last=t=>t?`${fmtTime(t)} ${fmtDate(t)}`:"chưa chạy";
  const opps=d.opps.length?`<div class="tbl-wrap"><table class="seo-t"><thead><tr><th>Từ khóa khách tìm</th><th class="num">Vị trí</th><th class="num">Hiển thị</th><th>Việc</th></tr></thead><tbody>${d.opps.map(o=>`<tr><td>${esc(o.query)}<br><span class="small muted">${esc((o.page||"").replace(/^https?:\/\/[^/]+/,""))}</span></td><td class="num">${o.position}${o.prev_position?seoDelta(o.position,o.prev_position,true):""}</td><td class="num">${o.impressions}</td><td class="small">${esc(o.kind)}</td></tr>`).join("")}</tbody></table></div>`
    :`<p class="small muted">${g.configured?"Chưa có từ khóa nào ở vị trí 4–20 hoặc ít người bấm.":"Kết nối Google bên dưới để Vy đọc từ khóa, thứ hạng thật."}</p>`;
  const rk=d.ranks.length?`<details><summary class="small">Thứ hạng ${d.ranks.length} từ khóa đang theo dõi</summary><div class="tbl-wrap"><table class="seo-t"><tbody>${d.ranks.map(r=>`<tr><td>${esc(r.keyword)}</td><td class="num">${r.position}${r.prev?seoDelta(r.position,r.prev,true):""}</td><td class="num small">${r.clicks} bấm</td></tr>`).join("")}</tbody></table></div></details>`:"";
  const km=`<details><summary class="small">Từ khóa → trang đích (${d.kwmap.length})</summary><div class="tbl-wrap"><table class="seo-t"><tbody>${d.kwmap.map(k=>`<tr><td>${esc(k.keyword)}<br><span class="small muted">${esc(k.cluster||"")}</span></td><td class="small">${esc(k.kind)}${k.url?`<br><code>${esc(k.url)}</code>`:""}</td></tr>`).join("")}</tbody></table></div></details>`;
  $("#seoVy").innerHTML=`<div class="row wrap"><h3 style="margin:0">Vy · SEO Leader</h3><button class="btn sm" type="button" data-seorun="leader" ${d.busy.leader?"disabled":""}>${d.busy.leader?"Đang phân tích…":"Vy phân tích ngay"}</button></div>
    <p class="small muted">Lần cuối: ${last(d.last.leader)} · báo cáo tuần thứ Hai qua Telegram</p><h4>Cơ hội trên Google</h4>${opps}${rk}${km}`;
  const iss=a?a.issues:[];
  $("#seoKhai").innerHTML=`<div class="row wrap"><h3 style="margin:0">Khải · Technical SEO</h3><button class="btn sm" type="button" data-seorun="audit" ${d.busy.audit?"disabled":""}>${d.busy.audit?"Đang kiểm tra…":"Khải kiểm tra ngay"}</button></div>
    <p class="small muted">Lần cuối: ${last(a&&a.at)}${a&&a.index?` · Google đã index ${a.index.indexed}/${a.index.checked} trang đã kiểm`:""}</p>
    ${a&&a.psi&&a.psi.length?`<div class="row wrap small">${a.psi.map(x=>x.error?`<span class="chip" title="${esc(x.error)}">PageSpeed lỗi</span>`:`<span class="chip ${x.score>=90?"ok":x.score>=50?"warn":"bad"}" title="${esc(x.url)}">📱 ${x.score} · LCP ${x.lcp}s</span>`).join("")}</div>`:""}
    ${a?(iss.length?`<ul class="seo-iss">${iss.map(i=>`<li><span class="chip ${SEO_SEV[i.sev][0]}">${SEO_SEV[i.sev][1]}</span> <b>${esc(i.area)}</b>: ${esc(i.msg)}<br><span class="small muted">Cách sửa: ${esc(i.fix)} · ${SEO_WHO[i.who]||esc(i.who)}${i.url?` · <code>${esc(i.url)}</code>`:""}</span></li>`).join("")}</ul>`:`<p class="ok">Không có lỗi kỹ thuật.</p>`):`<p class="small muted">Chưa kiểm tra lần nào.</p>`}`;
  const tasks=d.tasks.filter(t=>t.status==="todo");
  $("#seoHuong").innerHTML=`<div class="row wrap"><h3 style="margin:0">Hương · SEO Content: trang sản phẩm</h3><button class="btn sm" type="button" data-seorun="content" ${d.busy.content?"disabled":""}>${d.busy.content?"Đang viết…":"Hương làm việc ngay"}</button></div>
    <p class="small muted">Mỗi ngày Hương viết nội dung SEO cho trang sản phẩm (tiêu đề, mô tả, thân trang, câu hỏi thường gặp) và làm việc Vy giao. Nội dung đạt chuẩn, không có số liệu lạ thì Vy duyệt lên website; còn lại chờ sếp. Lần cuối: ${last(d.last.content)}</p>
    ${tasks.length?`<p class="small"><b>Việc Vy giao (${tasks.length}):</b> ${tasks.map(t=>esc(t.reason||t.query)).join(" · ")}</p>`:""}
    <div class="tbl-wrap"><table class="seo-t"><thead><tr><th>Sản phẩm</th><th>Từ khóa</th><th class="num">Điểm</th><th>Tình trạng</th><th></th></tr></thead><tbody>${d.products.map(p=>{ const [cl,lb]=SEO_PST[p.status]||["",p.status]; const open=ST.seoOpen===p.id;
      return `<tr><td>${esc(p.name)}</td><td class="small">${esc(p.keyword||"")}</td><td class="num">${p.score??""}</td><td><span class="chip ${cl}" title="${esc(p.note||"")}">${lb}</span>${p.note&&p.status==="review"?`<br><span class="small muted">${esc(p.note)}</span>`:""}</td>
        <td><button class="btn sm" type="button" data-seowrite="${p.id}">${p.status==="none"?"Hương viết":"Viết lại"}</button>${p.status!=="none"?` <button class="btn sm ghost" type="button" data-seoopen="${p.id}">${open?"Đóng":"Xem / duyệt"}</button>`:""}</td></tr>`
        +(open?`<tr><td colspan="5"><div class="stack seo-ed" data-pid="${p.id}">
          <div class="grid2"><label class="f">Từ khóa<input type="text" data-f="keyword" value="${esc(p.keyword||"")}"></label><label class="f">Tiêu đề (≤ 60 ký tự)<input type="text" data-f="title" value="${esc(p.title||"")}"></label></div>
          <label class="f">Mô tả (120–160 ký tự)<input type="text" data-f="meta" value="${esc(p.meta||"")}"></label>
          <label class="f">Nội dung trang (<code>## Mục</code>, <code>- ý</code>)<textarea data-f="body" rows="10">${esc(p.body||"")}</textarea></label>
          <label class="f">Câu hỏi thường gặp (mỗi dòng: câu hỏi | trả lời)<textarea data-f="faq" rows="3">${esc((JSON.parse(p.faq||"[]")).map(q=>`${q.q} | ${q.a}`).join("\n"))}</textarea></label>
          <div class="row wrap"><button class="btn primary sm" type="button" data-seook="${p.id}">Duyệt &amp; lên website</button><button class="btn ghost danger sm" type="button" data-seorej="${p.id}">Bỏ</button></div></div></td></tr>`:""); }).join("")
      ||`<tr><td colspan="5"><div class="empty">Chưa có sản phẩm nào hiện trên website (tab Sản phẩm).</div></td></tr>`}</tbody></table></div>`;
  $("#seoGEmail").innerHTML=g.configured?`Đã kết nối: <code>${esc(g.email)}</code>${g.gsc_site?` · Search Console: <code>${esc(g.gsc_site)}</code>`:""}`:"Chưa kết nối Google.";
  if(document.activeElement!==$("#seoGsc")) $("#seoGsc").value=g.gsc_site||""; if(document.activeElement!==$("#seoGa4")) $("#seoGa4").value=g.ga4||"";
  $("#seoPsi").value=g.psi_key_set?"••••••":""; $("#seoSa").placeholder=g.configured?"Đã lưu khóa (dán khóa mới nếu muốn đổi)":'{"type": "service_account", "client_email": "...", "private_key": "..."}';
}
$("#wpanel-seo").addEventListener("click",async e=>{ const b=e.target.closest("button"); if(!b) return; const ds=b.dataset;
  try{
    if(ds.seorun){ b.disabled=true; ST.seo=await api("/seo/run","POST",{job:ds.seorun}); renderSeo(); toast({leader:"Vy đang đọc Search Console, GA4",audit:"Khải đang kiểm tra website (PageSpeed mất 1–2 phút)",content:"Hương đang viết nội dung trang sản phẩm"}[ds.seorun]); [8000,30000,90000].forEach(t=>setTimeout(()=>{ if(ST.wsTab==="seo") loadSeo(); },t)); }
    if(ds.seowrite){ b.disabled=true; b.textContent="Hương đang viết…"; const r=await api(`/seo/products/${ds.seowrite}/write`,"POST"); ST.seo=r; ST.seoOpen=+ds.seowrite; renderSeo(); toast(r.result.status==="approved"?"Vy đã duyệt, trang sản phẩm lên website":"Hương viết xong, chờ sếp duyệt"); }
    if(ds.seoopen){ ST.seoOpen=ST.seoOpen===+ds.seoopen?null:+ds.seoopen; renderSeo(); }
    if(ds.seook){ const box=b.closest(".seo-ed"), v=k=>box.querySelector(`[data-f="${k}"]`).value;
      const faq=v("faq").split("\n").map(l=>l.split("|")).filter(x=>x[0].trim()).map(x=>({q:x[0].trim(),a:(x[1]||"").trim()}));
      ST.seo=await api(`/seo/products/${ds.seook}`,"PUT",{keyword:v("keyword"),title:v("title"),meta:v("meta"),body:v("body"),faq}); ST.seoOpen=null; renderSeo(); toast("Đã duyệt, trang sản phẩm lên website sau ít phút"); }
    if(ds.seorej){ ST.seo=await api(`/seo/products/${ds.seorej}/reject`,"POST"); ST.seoOpen=null; renderSeo(); toast("Đã bỏ nội dung này"); }
  }catch(err){ toast(err.message); b.disabled=false; } });
$("#seoGoogle").addEventListener("submit",async e=>{ e.preventDefault(); const body={gsc_site:$("#seoGsc").value,ga4:$("#seoGa4").value,psi_key:$("#seoPsi").value}; if($("#seoSa").value.trim()) body.sa=$("#seoSa").value;
  try{ ST.seo=await api("/seo/google","PUT",body); $("#seoSa").value=""; renderSeo(); toast("Đã lưu. Bấm Kiểm tra kết nối"); }catch(err){ toast(err.message); } });
$("#seoTest").onclick=async e=>{ e.target.disabled=true; const o=$("#seoTestOut"); o.hidden=false; o.innerHTML='<li class="muted">Đang hỏi Google…</li>';
  try{ const r=await api("/seo/google/test","POST"); o.innerHTML=r.steps.map(x=>`<li class="${x.ok?"ok":"bad"}"><b>${x.ok?"✓":"✗"} ${esc(x.name)}</b> ${esc(x.msg||"")}</li>`).join("")+(r.ok?'<li class="ok"><b>Kết nối tốt.</b> Bấm “Vy phân tích ngay”.</li>':""); loadSeo(); }
  catch(err){ o.innerHTML=`<li class="bad">${esc(err.message)}</li>`; } e.target.disabled=false; };
$("#seoDel").onclick=async e=>{ if(e.target.dataset.c!=="1"){ e.target.dataset.c="1"; e.target.textContent="Bấm lần nữa để gỡ"; return; } try{ ST.seo=await api("/seo/google","DELETE"); renderSeo(); toast("Đã gỡ kết nối Google"); }catch(err){ toast(err.message); } e.target.dataset.c=""; e.target.textContent="Gỡ kết nối"; };
