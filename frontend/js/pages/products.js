/* --------------------------------------------- sản phẩm */
function folderBox(p){
  const f=p.folder||{}; const own=f.source==="product";
  const pct=f.count?Math.round(f.fresh/f.count*100):0;
  const st=!f.exists?(f.error?`<div class="err">${esc(f.error)}</div>`:'<span class="small muted">Chưa có thư mục ảnh. ${p.is_general?"Mọi bài sẽ không được đăng cho tới khi điền thư mục ảnh ở đây.":"Bài của sản phẩm này sẽ không được đăng (bắt buộc có ảnh)."}</span>')
    :`<div class="row small" style="justify-content:space-between"><span><b>${f.count}</b> ảnh · <b>${f.fresh}</b> ảnh chưa đăng lần nào${f.posts_left!=null?` · đủ cho khoảng ${f.posts_left} bài mới`:""}</span>${own?"":'<span class="chip warn">Đang dùng thư mục chung</span>'}</div>
      <div class="meter" title="Tỉ lệ ảnh chưa dùng"><i class="${pct<25?"low":""}" style="width:${pct}%"></i></div>
      ${f.error?`<span class="small" style="color:var(--honey)">${esc(f.error)}</span>`:""}
      ${f.samples&&f.samples.length&&!DEMO?`<div class="thumbs">${f.samples.slice(0,6).map(n=>`<figure><img src="/api/products/${p.id}/folder-image?name=${encodeURIComponent(n)}" alt="${esc(n)}" title="${esc(n)}" loading="lazy"></figure>`).join("")}</div>`:""}
      ${f.fresh<3&&f.count?'<span class="small" style="color:var(--honey)">Sắp hết ảnh mới. Bổ sung ảnh vào thư mục để tránh đăng trùng.</span>':""}`;
  return `<div class="imgfolder"><label class="f" for="pf-${p.id}">Thư mục ảnh
      <div class="row"><input type="text" class="grow" id="pf-${p.id}" value="${esc(p.image_folder||"")}" placeholder="VD: D:\\AnhSanPham\\${esc(p.name)}"><button type="button" class="btn sm" data-pfsave="${p.id}">Lưu</button></div></label>${st}</div>`;
}
const CATS=["Trà túi lọc","Bột ngũ cốc","Bột thiên nhiên","Cà phê hòa tan","Khác"];
function prodEdit(p){
  const cats=CATS.includes(p.category)?CATS:[p.category,...CATS];
  return `<form class="stack" data-pedit="${p.id}">
    <label class="f" for="en-${p.id}">Tên sản phẩm<input type="text" id="en-${p.id}" value="${esc(p.name)}" required></label>
    <div class="grid2"><label class="f" for="ec-${p.id}">Dòng<select id="ec-${p.id}">${cats.filter(Boolean).map(c=>`<option ${c===p.category?"selected":""}>${esc(c)}</option>`).join("")}</select></label>
      <label class="f" for="em-${p.id}">Nhập tối thiểu<input type="text" id="em-${p.id}" value="${esc(p.moq||"")}"></label>
</div>
    <label class="f" for="ed-${p.id}">Mô tả<textarea id="ed-${p.id}" rows="2">${esc(p.description||"")}</textarea></label>
    <label class="f" for="es-${p.id}">Điểm mạnh khi bán<textarea id="es-${p.id}" rows="2">${esc(p.selling_points||"")}</textarea></label>
    <label class="row small"><input type="checkbox" id="eh-${p.id}" ${p.hot?"checked":""}> 🔥 Đang bán chạy: cả đội tập trung chào mời</label>
    <label class="f" for="eo-${p.id}">Lưu ý khi chào (không bắt buộc)<input type="text" id="eo-${p.id}" value="${esc(p.hot_note||"")}" placeholder="VD: đang vào mùa, có quà cho đơn đầu"></label>
    <div class="actions"><button class="btn sm primary" type="submit">Lưu thay đổi</button><button class="btn sm ghost" type="button" data-pcancel>Hủy</button></div></form>`;
}
async function loadProducts(){
  if(!ST.zalo){ try{ const s=await api("/settings"); ST.zalo=s.price_zalo||"0386992326"; }catch(e){} }
  document.querySelectorAll(".zalo-num").forEach(x=>x.textContent=ZALO());
  ST.products=await api("/products");
  const hot=ST.products.filter(p=>p.hot);
  $("#hotBar").innerHTML=hot.length?`🔥 Cả đội đang tập trung chào: <b>${hot.map(p=>esc(p.name)).join(", ")}</b>. Lan viết phần lớn bài về các sản phẩm này, Hà chào các sản phẩm này trước khi tư vấn khách, Tuấn up bài của chúng trước.`
    :`Chưa có sản phẩm nào được tích <b>Đang bán chạy</b>. Bấm nút 🔥 ở sản phẩm muốn đẩy để cả đội tập trung chào mời.`;
  const gen=ST.products.find(p=>p.is_general);
  $("#genBar").className="gen-bar"+(gen?"":" off");
  $("#genBar").innerHTML=gen?`📷 <b>Mọi bài đăng đang lấy ảnh ngẫu nhiên trong “${esc(gen.name)}”</b> (${gen.folder&&gen.folder.exists?`${gen.folder.count} ảnh, ${gen.folder.fresh} ảnh chưa đăng`:"chưa có thư mục ảnh: bài sẽ không đăng cho tới khi điền thư mục"}). Ảnh của các sản phẩm khác không được dùng. Bỏ tích ô Ảnh tổng hợp để bài lấy ảnh theo từng sản phẩm.`
    :`Bài đăng đang lấy ảnh theo đúng sản phẩm của bài. Muốn mọi bài dùng chung ảnh tổng hợp các sản phẩm nhà máy: tạo một mục (VD “Tổng hợp sản phẩm nhà máy”), điền thư mục ảnh rồi tích ô <b>Ảnh tổng hợp nhà máy</b>.`;
  if(ST.editProd&&!ST.products.some(p=>p.id===ST.editProd)) ST.editProd=null;
  $("#prodGrid").innerHTML=ST.products.map(p=>`<div class="card prod${p.hot?" hot":""}${p.is_general?" gen":""}" data-prod="${p.id}"><div class="prod-h"><div class="cat">${esc(p.category)}${p.is_sample?' · <span class="chip warn">Mẫu</span>':""}</div>
     <button type="button" class="hot-btn" data-phot="${p.id}" aria-pressed="${p.hot?"true":"false"}" title="Tích để cả đội tập trung chào mời sản phẩm này">🔥 ${p.hot?"Đang bán chạy":"Đánh dấu bán chạy"}</button></div>
   ${ST.editProd===p.id?prodEdit(p):`<h3>${esc(p.name)}</h3>${p.hot&&p.hot_note?`<div class="hot-note">${esc(p.hot_note)}</div>`:""}<p class="small muted">${esc(p.description)}</p>
   <dl class="kv"><dt>Giá</dt><dd>Liên hệ Zalo ${esc(ZALO())}</dd><dt>Nhập tối thiểu</dt><dd>${esc(p.moq)}</dd><dt>Điểm mạnh</dt><dd>${esc(p.selling_points)}</dd></dl>`}
   <label class="gen-tick"><input type="checkbox" data-pgen="${p.id}" ${p.is_general?"checked":""}> <span><b>Ảnh tổng hợp nhà máy</b>: mọi bài đăng chỉ lấy ảnh ngẫu nhiên trong mục này</span></label>
   ${folderBox(p)}${gen&&!p.is_general?`<span class="small muted">Đang dùng ảnh tổng hợp “${esc(gen.name)}” khi đăng, ảnh của sản phẩm này tạm không dùng.</span>`:""}
   ${JSON.parse(p.images||"[]").length?`<div><span class="small muted">Ảnh tải lên (chỉ dùng khi chưa có thư mục ảnh)</span><div class="thumbs" style="margin-top:4px">${JSON.parse(p.images||"[]").map(src=>`<figure><img src="${src.startsWith("data:")?src:"/"+esc(src)}" alt="Ảnh ${esc(p.name)}"><button type="button" data-delimg="${esc(src)}" data-p="${p.id}" aria-label="Xóa ảnh">×</button></figure>`).join("")}</div></div>`:""}
   <div class="row"><label class="btn sm ghost" for="up-${p.id}">Tải ảnh lên</label><input type="file" id="up-${p.id}" data-up="${p.id}" accept="image/png,image/jpeg,image/webp" multiple hidden>${ST.editProd===p.id?"":`<button class="btn sm" type="button" data-pedit-open="${p.id}">Sửa thông tin</button>`}<button class="btn sm ghost danger" data-pr="${p.id}">Xóa sản phẩm</button></div></div>`).join("");
}
$("#prodGrid").addEventListener("change",async e=>{
  const g=e.target.dataset.pgen; if(g){ const on=e.target.checked, p=ST.products.find(x=>x.id==g); e.target.disabled=true;
    try{ const r=await api(`/products/${g}`,"PATCH",{is_general:on});
      toast(on?(r.folder&&r.folder.exists?`Từ giờ mọi bài đăng lấy ngẫu nhiên ${r.folder.count} ảnh trong “${p.name}”`:`Đã tích “${p.name}”. Điền thư mục ảnh cho mục này, chưa có ảnh thì bài sẽ không đăng`):"Bài đăng lấy ảnh theo đúng sản phẩm của bài"); }
    catch(err){ toast(err.message); } return loadProducts(); }
  const pid=e.target.dataset.up; if(!pid) return;
  for(const f of e.target.files){ const data=await new Promise(r=>{ const fr=new FileReader(); fr.onload=()=>r(fr.result); fr.readAsDataURL(f); });
    try{ await api(`/products/${pid}/images`,"POST",{filename:f.name,data}); }catch(err){ toast(err.message); } }
  toast("Đã thêm ảnh"); loadProducts(); });
$("#prodGrid").addEventListener("click",async e=>{ const fs=e.target.closest("[data-pfsave]");
  if(fs){ const id=fs.dataset.pfsave; fs.disabled=true; const r=await api(`/products/${id}`,"PATCH",{image_folder:$(`#pf-${id}`).value});
    toast(r.folder.exists&&r.folder.source==="product"?`Đã lưu: ${r.folder.count} ảnh, sale sẽ chọn ngẫu nhiên khi đăng`:(r.folder.error||"Đã lưu")); return loadProducts(); }
  const h=e.target.closest("[data-phot]"); if(h){ const p=ST.products.find(x=>x.id==h.dataset.phot); h.disabled=true;
    try{ await api(`/products/${p.id}`,"PATCH",{hot:!p.hot}); toast(!p.hot?`Đã đánh dấu ${p.name} đang bán chạy. Cả đội sẽ tập trung chào sản phẩm này.`:`Thôi ưu tiên ${p.name}`); }catch(err){ toast(err.message); } return loadProducts(); }
  const eo=e.target.closest("[data-pedit-open]"); if(eo){ ST.editProd=+eo.dataset.peditOpen; loadProducts(); setTimeout(()=>{ const i=$(`#en-${ST.editProd}`); i&&i.focus(); },50); return; }
  if(e.target.closest("[data-pcancel]")){ ST.editProd=null; return loadProducts(); }
  const d=e.target.closest("[data-delimg]"); if(d){ await api(`/products/${d.dataset.p}/images?path=${encodeURIComponent(d.dataset.delimg)}`,"DELETE"); return loadProducts(); }
  const b=e.target.closest("[data-pr]"); if(!b) return; if(b.dataset.confirm!=="1"){ b.dataset.confirm="1"; b.textContent="Bấm lần nữa để xóa"; return; } const r=await api(`/products/${b.dataset.pr}`,"DELETE"); toast(r.drafts_removed?`Đã xóa sản phẩm và ${r.drafts_removed} bài nháp/chờ đăng của nó`:"Đã xóa sản phẩm"); loadProducts(); });
$("#prodGrid").addEventListener("submit",async e=>{ const f=e.target.closest("[data-pedit]"); if(!f) return; e.preventDefault(); const id=+f.dataset.pedit;
  try{ await api(`/products/${id}`,"PATCH",{name:$(`#en-${id}`).value,category:$(`#ec-${id}`).value,moq:$(`#em-${id}`).value,description:$(`#ed-${id}`).value,selling_points:$(`#es-${id}`).value,hot:$(`#eh-${id}`).checked,hot_note:$(`#eo-${id}`).value});
    ST.editProd=null; toast("Đã lưu sản phẩm. Các agent dùng thông tin mới từ việc tiếp theo."); }catch(err){ toast(err.message); }
  loadProducts(); });
$("#prodForm").addEventListener("submit",async e=>{ e.preventDefault(); try{ await api("/products","POST",{name:$("#pName").value,category:$("#pCat").value,description:$("#pDesc").value,moq:$("#pMoq").value,selling_points:$("#pSell").value,image_folder:$("#pFolder").value,hot:$("#pHot").checked,hot_note:$("#pHotNote").value,is_general:$("#pGen").checked}); e.target.reset(); toast("Đã thêm sản phẩm. Lan và Hà dùng sản phẩm này từ việc tiếp theo."); }catch(err){ toast(err.message); } loadProducts(); });

