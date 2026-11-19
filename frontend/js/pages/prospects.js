/* --------------------------------------------- Mai: tìm khách sỉ */
const PR_EV={rule:"Điều kiện sếp",rule_fail:"Không đạt",ads:"Quảng cáo",demand:"Hỏi nguồn hàng",sell:"Bán hàng",live:"Livestream",import:"Nhập hàng",fit_core:"Ngành hàng",fit_food:"Ngành hàng",affiliate:"Affiliate",owner:"Chủ shop",ctv:"CTV",koc:"KOC",shared_live:"Chỉ chia sẻ live",contact:"Liên hệ",shop_link:"Gian hàng",found:"Kết quả tìm"};
const PR_PARTS=[["sales","Bán hàng",20],["live","Livestream",20],["fit","Hợp ngành",20],["import","Tự nhập hàng",15],["engage","Hoạt động",10],["contact","Liên hệ",10],["expand","Mở rộng",5]];
const PR_PF={facebook:"Facebook",tiktok:"TikTok",shopee:"Shopee"};
ST.prF={grade:"",platform:"",seller_type:"",status:"",phone:""};
function prCard(x,d){
  const man=x.status==="needs_manual", g=man?"M":(x.grade||"D");
  const tags=(x.tags||"").split(",").filter(t=>t&&t!==x.seller_type).map(t=>`<span class="chip">${esc(d.types[t]||t)}</span>`).join("");
  const meta=[PR_PF[x.platform]||x.platform,x.recent_activity,x.live_freq,x.followers?`${num(x.followers)} người theo dõi`:"",x.direction===6?`Tìm thấy khi đọc nhóm “${x.keyword||""}”`:x.direction===5?`Thư viện quảng cáo, từ khóa “${x.keyword||""}”`:x.direction?`Hướng ${x.direction}: “${x.keyword||""}”`:x.keyword==="dán link"?"Sếp dán link":""].filter(Boolean).map(v=>esc(v)).join(" · ");
  const ct=[x.zalo?`<a href="${esc(/^http/.test(x.zalo)?x.zalo:"https://zalo.me/"+x.zalo)}" target="_blank" rel="noopener">Zalo</a>`:"",x.email?`<a href="mailto:${esc(x.email)}">${esc(x.email)}</a>`:"",
    x.shop_url?`<a href="${esc(x.shop_url)}" target="_blank" rel="noopener">Gian hàng ↗</a>`:"",x.live_url?`<a href="${esc(x.live_url)}" target="_blank" rel="noopener">Livestream ↗</a>`:""].filter(Boolean).join("");
  const parts=x.parts&&Object.keys(x.parts).length?`<div class="pr-parts">${PR_PARTS.map(([k,l,mx])=>{ const v=x.parts[k]||0, pc=Math.round(v/mx*100);
    return `<span>${l}</span><div class="bar"><i class="${pc>=70?"":pc>=35?"warn":"bad"}" style="width:${pc}%"></i></div><b>${v}/${mx}</b>`; }).join("")}</div>`:"";
  const evs=(x.evidence||[]).slice(0,7).map(e=>`<li><span class="k">${esc(PR_EV[e.kind]||e.kind)}</span><span><q>${esc(e.text)}</q>${e.url&&e.url!==x.account_url?` <a href="${esc(e.url)}" target="_blank" rel="noopener" class="small">nguồn ↗</a>`:""}</span></li>`).join("");
  const sug=(x.suggested||[]).map(p=>`<li><b>${esc(p.name)}</b> <span class="muted small">${esc(p.why)}</span></li>`).join("");
  const crm=x.lead_id?`<span class="chip ok">Đã ở Khách hàng</span>`:man?"":`<button class="btn sm" type="button" data-prcrm="${x.id}">Vào Khách hàng</button>`;
  return `<article class="pr-card${man?" manual":""}" data-pr="${x.id}">
    <div class="pr-grade"><span class="g g-${g}">${man?"?":esc(x.grade||"–")}</span><small>${man?"xem tay":`${x.score||0} điểm`}</small></div>
    <div class="pr-head"><a class="nm" href="${esc(x.account_url)}" target="_blank" rel="noopener">${esc(x.shop_name||x.account_name||x.account_url)} ↗</a>
      ${x.phone?`<a class="pr-tel" href="${esc(zaloUrl(x.phone)||"tel:"+x.phone)}" target="_blank" rel="noopener" title="Mở Zalo với số này">💬 ${esc(x.phone)} · Zalo</a><a class="btn sm ghost" href="tel:${esc(x.phone)}" title="Gọi điện">Gọi</a><button class="btn sm ghost" type="button" data-prcopyph="${esc(x.phone)}">Chép số</button>`:man?"":`<span class="pr-nophone">Chưa có SĐT</span>`}
      ${x.seller_type&&!man?`<span class="chip ${x.seller_type==="affiliate"||x.seller_type==="koc"||x.seller_type==="store"?"warn":"ok"}">${esc(d.types[x.seller_type]||x.seller_type)}</span>`:""}${tags}
      <div class="pr-meta" style="flex-basis:100%">${meta}</div></div>
    <div class="pr-body">
      <div>${evs?`<h5>Bằng chứng</h5><ul class="pr-ev">${evs}</ul>`:""}
        ${x.products?`<p class="small" style="margin:8px 0 0"><b>Đang bán:</b> ${esc(x.products)}</p>`:""}
        ${ct?`<h5 style="margin-top:10px">Liên hệ công khai</h5><div class="pr-contact">${ct}</div>`:""}</div>
      <div>${parts?`<h5>Điểm tiềm năng</h5>${parts}`:man?`<p class="small">Nền tảng bắt đăng nhập hoặc xác minh nên Mai dừng, không vượt qua. Sếp mở link xem tay, nếu thấy hợp thì bấm “Kiểm tra lại” khi trang mở được hoặc ghi chú lại.</p>`:""}
        ${sug?`<h5 style="margin-top:10px">Nên giới thiệu</h5><ul class="recent" style="margin:0">${sug}</ul>`:""}
        ${x.approach?`<h5 style="margin-top:10px">Kịch bản tiếp cận (nhắn tay)</h5><div class="pr-script">${esc(x.approach)}</div>`:""}</div>
    </div>
    <div class="pr-next"><span class="act">${esc(x.next_action||"")}</span>
      <div class="row wrap" style="gap:6px">${x.approach?`<button class="btn sm ghost" type="button" data-prcopy="${x.id}">Chép kịch bản</button>`:""}${crm}
        ${x.status==="contacted"?`<span class="chip ok">Đã liên hệ</span>`:man||x.status==="rejected"?"":`<button class="btn sm ghost" type="button" data-prst="contacted" data-id="${x.id}">Đã liên hệ</button>`}
        <button class="btn sm ghost" type="button" data-prre="${x.id}">Kiểm tra lại</button>
        ${x.status==="rejected"?`<button class="btn sm ghost" type="button" data-prst="verified" data-id="${x.id}">Theo dõi lại</button>`:`<button class="btn sm ghost danger" type="button" data-prst="rejected" data-id="${x.id}">Loại</button>`}</div></div>
  </article>`;
}
function prSettings(d){
  const st=d.settings, on=k=>st["prospect_"+k]!=="0"?"checked":"";
  return `<div class="stack" style="margin-top:10px">
    <p class="small muted" style="margin:0">Mỗi ngày lúc ${esc(st.prospect_time||"14:30")}, Mai dùng Chrome của một nick sale: đọc bài và bình luận mới trong ${esc(st.prospect_groups_per_run||3)} nhóm (ai hỏi “tìm nguồn”, “cần nhập”, “xin giá sỉ” trà, ngũ cốc là khách nóng nhất; người chào bán sỉ thì bỏ qua), quét thư viện quảng cáo Facebook (Việt Nam, quảng cáo đang chạy) theo từ khóa sản phẩm, rồi tìm trang, shop theo 4 hướng (mỗi hướng ${esc(st.prospect_fb_keywords||2)} từ khóa, đổi vòng mỗi ngày), mở xem tối đa ${esc(st.prospect_inspect_per_run||10)} tài khoản, đọc giới thiệu và vài bài gần nhất (chỉ đọc). Chưa thấy SĐT thì Mai đọc thêm bài và mở trang Giới thiệu → Thông tin liên hệ; vẫn chưa có thì 3 ngày sau quay lại tìm (tối đa 3 lần). Chỉ lấy SĐT kinh doanh shop tự công khai. Chấm 100 điểm: bán hàng 20, livestream 20, hợp ngành 20, tự nhập hàng 15, hoạt động 10, liên hệ 10, mở rộng 5. Hạng A ≥ 80, B 60–79, C 40–59, D dưới 40. Không có bằng chứng thì không cho điểm; người chỉ xem hoặc chia sẻ livestream không tính là người bán; affiliate chưa có bằng chứng tự nhập thì không chào giá sỉ. TikTok, Shopee bắt đăng nhập hay captcha thì Mai dừng và ghi “cần sếp xem tay”.</p>
    <form id="prSetForm" class="stack">
      <div class="grid3"><label class="f" for="prTime">Giờ đi tìm<input type="time" id="prTime" value="${esc(st.prospect_time||"14:30")}"></label>
        <label class="f" for="prN">Tài khoản mở xem mỗi lượt<input type="number" id="prN" min="1" max="20" value="${esc(st.prospect_inspect_per_run||10)}"></label>
        <label class="f" for="prFk">Từ khóa Facebook mỗi hướng/lượt<input type="number" id="prFk" min="1" max="4" value="${esc(st.prospect_fb_keywords||2)}"></label>
        <label class="f" for="prGn">Nhóm đọc bình luận mỗi lượt<input type="number" id="prGn" min="0" max="10" value="${esc(st.prospect_groups_per_run||3)}"></label></div>
      <div class="row wrap" style="gap:14px"><label class="row small"><input type="checkbox" id="prOn" ${on("enabled")}> Tự đi tìm mỗi ngày</label>
        <label class="row small"><input type="checkbox" id="prCrm" ${on("auto_crm")}> Có SĐT thì tự vào Khách hàng và báo sếp qua Telegram</label><label class="row small"><input type="checkbox" id="prAi" ${on("ai_script")}> Nhờ Claude viết kịch bản (chỉ dựa trên bằng chứng)</label></div>
      <p class="small muted" style="margin:0">Từ khóa tìm kiếm và điều kiện chọn khách nằm ở mục “Điều kiện tìm khách sỉ của sếp” phía trên.</p>
      <div><button class="btn sm primary" type="submit">Lưu cài đặt</button></div></form></div>`;
}
const SG_LBL={keywords:"Từ khóa tìm",ads_keywords:"Từ khóa quảng cáo",must:"Phải có",exclude:"Loại",bonus:"Ưu tiên",fit:"Ngành hàng",regions:"Khu vực",groups:"Nhóm đọc bình luận",search_kinds:"Cách tìm"};
function prCrit(d){
  const c=d.criteria||{}, ta=(id,label,v,ph)=>`<label class="f" for="${id}">${label}<textarea id="${id}" rows="3" placeholder="${ph||""}">${esc((v||[]).join("\n"))}</textarea></label>`;
  const types=Object.entries(d.types||{}).filter(([k])=>!["unknown","ads"].includes(k));
  return `<form id="prCritF" class="stack">
    <div class="pr-crit-grid">
      ${ta("crMust","Bắt buộc phải có ít nhất 1 chữ (mỗi dòng 1 chữ)",c.must,"ship\ninbox")}
      ${ta("crEx","Loại ngay nếu có",c.exclude,"quần áo\nmỹ phẩm")}
      ${ta("crBonus","Ưu tiên (mỗi chữ khớp được cộng điểm)",c.bonus,"livestream\nzalo")}
      ${ta("crFit","Ngành hàng phù hợp thêm (đủ điểm phù hợp ngành)",c.fit,"trà sữa\nđồ uống healthy")}
      ${ta("crReg","Khu vực ưu tiên",c.regions,"Hà Nội\nTP.HCM")}
      <div class="stack"><label class="f" for="crPts">Điểm cộng cho mỗi chữ ưu tiên<input type="number" id="crPts" min="1" max="20" value="${esc(c.bonus_points||5)}"></label>
        <div class="grid2"><label class="f" for="crFmin">Người theo dõi từ<input type="number" id="crFmin" min="0" value="${esc(c.followers_min||0)}"></label>
        <label class="f" for="crFmax">đến (0 = không giới hạn)<input type="number" id="crFmax" min="0" value="${esc(c.followers_max||0)}"></label></div>
        <div class="grid2"><label class="f" for="crDays">Bài mới nhất trong (ngày, 0 = bỏ qua)<input type="number" id="crDays" min="0" max="365" value="${esc(c.recent_days||0)}"></label>
        <label class="f" for="crGrade">Vào mục Khách hàng từ hạng<select id="crGrade">${["A","B","C"].map(g=>`<option ${c.crm_min_grade===g?"selected":""}>${g}</option>`).join("")}</select></label></div></div>
    </div>
    <div><b class="small">Cách tìm trên Facebook</b><div class="pr-checks">${Object.entries(d.search_kinds||{}).map(([k,v])=>`<label class="row small"><input type="checkbox" name="crKind" value="${k}" ${(c.search_kinds||[]).includes(k)?"checked":""}> ${esc(v)}</label>`).join("")}</div></div>
    <div><b class="small">Bỏ qua các loại người bán</b><div class="pr-checks">${types.map(([k,v])=>`<label class="row small"><input type="checkbox" name="crSkip" value="${k}" ${(c.skip_types||[]).includes(k)?"checked":""}> ${esc(v)}</label>`).join("")}</div></div>
    <div><b class="small">Từ khóa gõ vào ô tìm kiếm (mỗi dòng 1 từ khóa)</b><div class="pr-dirs" style="margin-top:6px">${[1,2,3,4,5].map(i=>`<label class="f" for="prK${i}">Hướng ${i}: ${esc(d.directions[i])}<textarea id="prK${i}" rows="3">${esc(((d.keywords||{})[i]||[]).join("\n"))}</textarea></label>`).join("")}</div></div>
    <label class="f" for="crNote">Sếp dặn thêm Mai (Mai đọc khi tìm và khi viết kịch bản)<textarea id="crNote" rows="2">${esc(c.note||"")}</textarea></label>
    <div class="row wrap"><button class="btn sm primary" type="submit">Lưu và cho Mai chấm lại</button><span class="small muted">Mai ghi điều kiện vào sổ kiến thức và chấm lại các khách đã tìm.</span></div></form>`;
}
function prLessons(d){
  return (d.lessons||[]).map(l=>{ const sg=l.suggest||{}; const chips=Object.keys(SG_LBL).filter(k=>(sg[k]||[]).length).map(k=>`<span>${SG_LBL[k]}: ${esc((sg[k]||[]).map(x=>(d.search_kinds||{})[x]||x).join(", "))}</span>`).join("");
    return `<li><div class="txt">${esc(l.text)}</div><div class="mai"><b>Mai:</b> ${esc(sg.summary||"Em đã ghi vào sổ kiến thức.")}${chips?`<div class="sg">${chips}</div>`:""}</div>
      <div class="row" style="justify-content:space-between;margin-top:6px"><span class="small muted">${fmtTime(l.created_at)} ${fmtDate(l.created_at)}</span><span class="row" style="gap:4px">${chips?(l.applied?'<span class="chip ok">Đã áp dụng</span>':`<button class="btn sm primary" type="button" data-lapply="${l.id}">Áp dụng</button>`):""}<button class="btn sm ghost danger" type="button" data-ldel="${l.id}">Xóa</button></span></div></li>`; }).join("")||'<li class="small muted" style="border:0;padding:0">Chưa có bài dạy nào.</li>';
}
async function loadProspects(soft){
  const f=ST.prF, qs=new URLSearchParams(Object.entries(f).filter(([k,v])=>v)).toString();
  let d; try{ d=await api("/prospects"+(qs?"?"+qs:"")); }catch(e){ $("#prList").innerHTML=`<p class="err">${esc(e.message)}</p>`; return; }
  ST.pr=d; const c=d.counts||{};
  const stat=(k,lbl,cls,val)=>`<button type="button" class="pr-stat${(k==="M"?f.status==="needs_manual":f.grade===k)?" on":""}" data-prg="${k}"><b><span class="g ${cls}">${k==="M"?"?":k}</span>${val}</b><span>${lbl}</span></button>`;
  $("#prStats").innerHTML=`<button type="button" class="pr-stat pr-phone-stat${f.phone==="yes"?" on":""}" data-prph="yes"><b>${d.phones||0}</b><span><b style="font-size:14px;color:var(--ink)">số điện thoại đã tìm được</b><br>${d.phones_today||0} số hôm nay · ${d.no_phone||0} người đang bán chưa có SĐT, Mai sẽ quay lại tìm</span></button>`+stat("A","Liên hệ ngay","g-A",c.A||0)+stat("B","Theo dõi rồi tiếp cận","g-B",c.B||0)+stat("C","Lưu theo dõi","g-C",c.C||0)+stat("D","Không ưu tiên","g-D",c.D||0)+stat("M","Cần sếp xem tay","g-M",d.manual||0)
    +`<div class="pr-stat" style="cursor:default"><b>${d.crm||0}</b><span>Đã vào Khách hàng</span></div>`;
  const on=d.platforms_on||["facebook"];
  const sv=k=>d.settings["prospect_"+k]!=="0";
  const sw=(k,label,isOn)=>`<button type="button" class="src" data-prsrc="${k}" aria-pressed="${isOn}">${label} <span class="st">${isOn?"đang hoạt động":"không hoạt động"}</span><span class="sw"></span></button>`;
  $("#prSrc").innerHTML=`<b>Nguồn tìm:</b><button type="button" class="src" disabled aria-pressed="true">Facebook: trang, shop <span class="st">luôn bật</span><span class="sw"></span></button>`
    +sw("groups","Bình luận trong nhóm",sv("groups"))+sw("ads","Trang chạy quảng cáo",sv("ads"))
    +["tiktok","shopee"].map(k=>sw(k,PR_PF[k],on.includes(k))).join("");
  $("#prCh").innerHTML=(d.channels||[]).map(c=>`<div class="${c.phones?"":"zero"}" title="${c.total} người tìm được trong 7 ngày"><b>${c.phones}</b><span>SĐT · ${esc(c.label)}</span></div>`).join("");
  const ty=$("#prType"); if(ty.options.length<2) ty.insertAdjacentHTML("beforeend",Object.entries(d.types).map(([k,v])=>`<option value="${k}">${esc(v)}</option>`).join(""));
  $("#prLast").textContent=d.last?`${fmtTime(d.last.created_at)} ${fmtDate(d.last.created_at)}: ${d.last.detail}`:"Mai chưa đi tìm lần nào.";
  $("#prList").innerHTML=d.items.length?d.items.map(x=>prCard(x,d)).join(""):`<div class="card empty">${Object.values(f).some(Boolean)?"Không có tài khoản nào khớp bộ lọc.":"Chưa có khách nào. Bấm “Mai đi tìm ngay” hoặc dán link một shop để Mai phân tích."}</div>`;
  if(!soft||!$("#prSetBody").innerHTML) $("#prSetBody").innerHTML=prSettings(d);
  $("#prCritSum").textContent=d.criteria_text||"";
  if(!soft||!$("#prCritBody").innerHTML) $("#prCritBody").innerHTML=prCrit(d);
  if(!$("#prTeach").contains(document.activeElement)) $("#prLessons").innerHTML=prLessons(d);
}
$("#prSrc").addEventListener("click",async e=>{ const b=e.target.closest("[data-prsrc]"); if(!b) return; const k=b.dataset.prsrc, v=b.getAttribute("aria-pressed")!=="true";
  const nm={groups:"Đọc bình luận trong nhóm",ads:"Quét trang chạy quảng cáo"}[k]||PR_PF[k];
  try{ await api("/prospects/settings","PUT",{[k]:v}); toast(`${nm}: ${v?(PR_PF[k]?"đã bật, Mai tìm thêm ở đây (gặp đăng nhập/captcha thì dừng)":"đã bật"):"đã tắt, Mai không tìm ở đây nữa"}`); loadProspects(true); }catch(err){ toast(err.message); } });
$("#prStats").addEventListener("click",e=>{ const ph=e.target.closest("[data-prph]"); if(ph){ ST.prF.phone=ST.prF.phone==="yes"?"":"yes"; $("#prPh").value=ST.prF.phone; return loadProspects(true); }
  const b=e.target.closest("[data-prg]"); if(!b) return; const k=b.dataset.prg, f=ST.prF;
  if(k==="M"){ f.status=f.status==="needs_manual"?"":"needs_manual"; f.grade=""; } else { f.grade=f.grade===k?"":k; if(f.status==="needs_manual") f.status=""; }
  $("#prSt").value=f.status; loadProspects(true); });
$("#prFilters").addEventListener("change",()=>{ Object.assign(ST.prF,{platform:$("#prPf").value,seller_type:$("#prType").value,status:$("#prSt").value,phone:$("#prPh").value}); if(ST.prF.status==="needs_manual") ST.prF.grade=""; loadProspects(true); });
$("#prRun").addEventListener("click",async e=>{ const b=e.currentTarget; b.disabled=true; try{ const r=await api("/prospects/run","POST",{}); toast(`Mai bắt đầu tìm khách, dùng Chrome của nick ${r.account}. Xong Mai báo lại`); refresh(); }catch(err){ toast(err.message); } b.disabled=false; });
$("#prPaste").addEventListener("submit",async e=>{ e.preventDefault(); const v=$("#prUrls").value.trim(); if(!v) return;
  try{ const r=await api("/prospects/analyze","POST",{urls:v.split(/\s+/)}); $("#prUrls").value=""; toast(`Mai đang mở ${(r.urls||[]).length} link bằng Chrome của nick ${r.account}`); refresh(); }catch(err){ toast(err.message); } });
$("#prList").addEventListener("click",async e=>{ const t=e.target; let b;
  try{
    if((b=t.closest("[data-prcopyph]"))){ try{ await navigator.clipboard.writeText(b.dataset.prcopyph); toast("Đã chép số "+b.dataset.prcopyph); }catch(_){ toast("Trình duyệt chặn chép, hãy bôi đen số để chép"); } return; }
    if((b=t.closest("[data-prcopy]"))){ const x=ST.pr.items.find(z=>z.id==b.dataset.prcopy); try{ await navigator.clipboard.writeText(x.approach); toast("Đã chép kịch bản. Nhớ đọc lại trước khi gửi"); }catch(_){ toast("Trình duyệt chặn chép, hãy bôi đen để chép"); } return; }
    if((b=t.closest("[data-prcrm]"))){ await api(`/prospects/${b.dataset.prcrm}/crm`,"POST"); toast("Đã đưa vào mục Khách hàng để Hà chăm sóc"); return loadProspects(true); }
    if((b=t.closest("[data-prst]"))){ await api(`/prospects/${b.dataset.id}`,"PATCH",{status:b.dataset.prst}); toast({contacted:"Đã ghi nhận đã liên hệ",rejected:"Đã loại khỏi danh sách",verified:"Đã đưa lại vào danh sách theo dõi"}[b.dataset.prst]); return loadProspects(true); }
    if((b=t.closest("[data-prre]"))){ const r=await api(`/prospects/${b.dataset.prre}/recheck`,"POST"); toast(`Mai sẽ mở lại trang này bằng Chrome của nick ${r.account}`); return; }
  }catch(err){ toast(err.message); } });
$("#prCritBody").addEventListener("submit",async e=>{ e.preventDefault(); const L=id=>$("#"+id).value.split("\n").map(s=>s.trim()).filter(Boolean);
  const kw={}; [1,2,3,4,5].forEach(i=>kw[i]=L("prK"+i)); const btn=e.target.querySelector("button[type=submit]"); btn.disabled=true;
  try{ const r=await api("/prospects/criteria","PUT",{must:L("crMust"),exclude:L("crEx"),bonus:L("crBonus"),bonus_points:+$("#crPts").value,fit:L("crFit"),regions:L("crReg"),
      followers_min:+$("#crFmin").value,followers_max:+$("#crFmax").value,recent_days:+$("#crDays").value,crm_min_grade:$("#crGrade").value,
      search_kinds:[...document.querySelectorAll("[name=crKind]:checked")].map(x=>x.value),skip_types:[...document.querySelectorAll("[name=crSkip]:checked")].map(x=>x.value),note:$("#crNote").value,keywords:kw});
    const rs=r.rescore||{}; toast(`Mai đã học điều kiện mới, chấm lại ${rs.checked||0} khách: ${rs.fail||0} không đạt${rs.crm?`, ${rs.crm} khách mới vào mục Khách hàng`:""}`); loadProspects(); }catch(err){ toast(err.message); }
  btn.disabled=false; });
$("#prTeachF").addEventListener("submit",async e=>{ e.preventDefault(); const v=$("#prTeachIn").value.trim(); if(v.length<10) return toast("Sếp viết dài hơn một chút để Mai hiểu");
  const btn=e.target.querySelector("button"); btn.disabled=true; btn.textContent="Mai đang đọc…";
  try{ await api("/prospects/lessons","POST",{text:v}); $("#prTeachIn").value=""; toast("Mai đã học bài này và ghi vào sổ kiến thức"); document.activeElement.blur(); loadProspects(true); }catch(err){ toast(err.message); }
  btn.disabled=false; btn.textContent="Dạy Mai"; });
$("#prLessons").addEventListener("click",async e=>{ let b;
  try{
    if((b=e.target.closest("[data-lapply]"))){ const r=await api(`/prospects/lessons/${b.dataset.lapply}/apply`,"POST"); toast(`Đã cài vào điều kiện tìm khách${r.groups_added?`, thêm ${r.groups_added} nhóm để Mai đọc bình luận`:""}. Mai chấm lại ${(r.rescore||{}).checked||0} khách`); return loadProspects(); }
    if((b=e.target.closest("[data-ldel]"))){ if(b.dataset.confirm!=="1"){ b.dataset.confirm="1"; b.textContent="Bấm lần nữa để xóa"; return; } await api(`/prospects/lessons/${b.dataset.ldel}`,"DELETE"); return loadProspects(); }
  }catch(err){ toast(err.message); } });
$("#prSetBody").addEventListener("submit",async e=>{ e.preventDefault();
  try{ await api("/prospects/settings","PUT",{time:$("#prTime").value,inspect_per_run:+$("#prN").value,fb_keywords:+$("#prFk").value,groups_per_run:+$("#prGn").value,enabled:$("#prOn").checked,auto_crm:$("#prCrm").checked,ai_script:$("#prAi").checked});
    toast("Đã lưu cài đặt tìm khách"); loadProspects(); }catch(err){ toast(err.message); } });

