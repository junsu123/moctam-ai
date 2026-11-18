/* --------------------------------------------- tìm nhóm mới */
const num=n=>(+n||0).toLocaleString("vi-VN");
const PRIV={public:"Công khai",private:"Riêng tư"};
const VERD={join:["ok","Nên vào"],consider:["warn","Cân nhắc"],skip:["bad","Bỏ qua"]};
const vn1=x=>x==null||x===""?"?":(+x>=100||Number.isInteger(+x))?num(Math.round(+x)):String(Math.round(+x*10)/10).replace(".",",");
function candLi(c){
  const [vc,vt]=VERD[c.verdict]||["","Chưa khảo sát"];
  const ppd=c.posts_month!=null?c.posts_month/30:c.posts_today!=null?c.posts_today:c.posts_per_day;
  const m=[`${num(c.members)} thành viên`,PRIV[c.privacy]||"",ppd?`${vn1(ppd)} bài/ngày`:"",
    c.sampled_posts>=3?`TB ${vn1(c.avg_reactions)} cảm xúc · ${vn1(c.avg_comments)} bình luận`:"",
    c.new_members_week!=null?`+${vn1(c.new_members_week)} tv/tuần`:"",
    c.last_post_hours!=null?`bài mới nhất ${c.last_post_hours<1?"dưới 1 giờ":c.last_post_hours<48?vn1(c.last_post_hours)+" giờ":Math.round(c.last_post_hours/24)+" ngày"} trước`:""].filter(Boolean).join(" · ");
  return `<li><div><a href="${esc(c.url)}" target="_blank" rel="noopener"><b>${esc(c.name)}</b></a> <span class="chip ${vc}">${vt}${c.eng_score!=null?` · ${vn1(c.eng_score)} điểm`:""}</span>
    <div class="small muted">${m} · chủ đề “${esc(c.keyword)}”</div>${c.review_note?`<div class="small rv-note">${esc(c.review_note)}</div>`:""}</div>
    <div class="row" style="gap:4px;flex-wrap:nowrap"><button class="btn sm" type="button" data-gfadd="${c.id}">${c.status==="rejected"?"Vẫn thêm":"Thêm"}</button>${c.status==="rejected"?"":`<button class="btn sm ghost" type="button" data-gfign="${c.id}">Bỏ</button>`}</div></li>`;
}
async function loadFinder(){
  const box=$("#gfBody"); if(box.contains(document.activeElement)&&document.activeElement.matches("input,textarea")) return;
  let d; try{ d=await api("/group-finder"); }catch(e){ box.innerHTML=`<p class="err">${esc(e.message)}</p>`; return; }
  ST.gf=d; const st=d.settings, last=d.last||{};
  box.innerHTML=`<div class="gf-today"><b class="small">${d.today_by==="boss"?"Chủ đề sếp chọn hôm nay:":"CEO Đức chọn chủ đề hôm nay:"}</b>${(d.today||[]).map(k=>`<span class="kw">${esc(k)}</span>`).join("")}
      <button class="btn sm ghost" type="button" id="gfEdit">Sửa</button><button class="btn sm ghost" type="button" id="gfReroll" title="CEO chọn lại theo hiệu quả">CEO chọn lại</button></div>
    <p class="small muted" style="margin:6px 0 0">${st.discover_enabled==="1"?`Mỗi ngày lúc <b>${esc(st.discover_time||"10:30")}</b> một sale lướt Facebook ${esc(st.browse_minutes||2)} phút, tìm nhóm theo các chủ đề này, mở xem ${esc(st.scout_per_run||6)} nhóm hứa hẹn nhất để đọc chỉ số tương tác rồi báo Tuấn. Tuấn chỉ thêm nhóm đạt chuẩn tương tác (tối đa ${esc(st.discover_add_per_day)} nhóm/ngày); mỗi nick xin vào tối đa ${esc(st.join_per_nick_day)} nhóm/ngày${st.join_enabled==="1"?"":" (đang tắt xin vào nhóm)"}. Tuấn ưu tiên đăng vào nhóm hợp chủ đề hôm nay.`:"Đang tắt tự tìm nhóm mỗi ngày."}
      ${last.at?` Lần gần nhất ${fmtTime(last.at)} ${fmtDate(last.at)}: tìm được ${last.found} nhóm mới${last.scouted!=null?`, khảo sát ${last.scouted}, Tuấn đánh giá: nên vào ${(last.review||{}).join||0}, cân nhắc ${(last.review||{}).consider||0}, bỏ qua ${(last.review||{}).skip||0}`:""}, thêm ${last.added} nhóm${last.joins?`, vào ${(last.joins.joined||0)} nhóm, chờ duyệt ${(last.joins.requested||0)}`:""}.`:""}</p>
    ${d.pending_answers.length?`<div class="err" style="margin-top:8px"><b>${d.pending_answers.length} nhóm bắt trả lời câu hỏi khi xin vào</b>, sale không tự trả lời thay sếp. Mở Chrome của sale (trang Nhân viên sale) và tự xin vào: ${d.pending_answers.map(g=>`<a href="${esc(g.url)}" target="_blank" rel="noopener">${esc(g.name)}</a> (${esc(g.sale)})`).join(", ")}</div>`:""}
    <div class="gf-grid">
      <div><h4>Tuấn đánh giá nhóm sale tìm được (${d.candidates.length})</h4>
        <div class="bench small"><b>Chuẩn nhóm tương tác cao:</b> ${esc(d.benchmark_text||"")}. Nên vào khi đạt từ ${esc(st.review_join_score||60)} điểm và tương tác mỗi bài đạt 60% chuẩn.
          <button class="btn sm ghost" type="button" id="gfRev">Tuấn chấm lại</button></div>
        ${d.candidates.length?`<ul class="cand">${d.candidates.slice(0,20).map(candLi).join("")}</ul>`:'<p class="small muted">Chưa có. Nhóm “Nên vào” được tự thêm vào danh sách bên dưới; nhóm “Cân nhắc” hiện ở đây để sếp chọn.</p>'}
        ${(d.rejected||[]).length?`<details class="gf-rej"><summary class="small">Tuấn đã loại ${d.rejected.length} nhóm (xem lý do)</summary><ul class="cand">${d.rejected.map(candLi).join("")}</ul></details>`:""}
        <details><summary class="small">Sửa chuẩn nhóm tương tác cao</summary>
          <form id="gfRevForm" class="stack" style="margin-top:8px">
            <div class="grid2"><label class="f" for="rvP">Bài mới mỗi ngày<input type="number" id="rvP" min="0.5" step="0.5" value="${esc(st.review_posts_day)}"></label>
              <label class="f" for="rvR">Cảm xúc TB mỗi bài<input type="number" id="rvR" min="1" value="${esc(st.review_avg_reactions)}"></label>
              <label class="f" for="rvC">Bình luận TB mỗi bài<input type="number" id="rvC" min="0.5" step="0.5" value="${esc(st.review_avg_comments)}"></label>
              <label class="f" for="rvG">Thành viên mới/tuần (%)<input type="number" id="rvG" min="0.05" step="0.05" value="${esc(st.review_growth_week)}"></label>
              <label class="f" for="rvM">Thành viên tối thiểu<input type="number" id="rvM" min="0" step="100" value="${esc(st.review_min_members)}"></label>
              <label class="f" for="rvJ">Điểm để Nên vào<input type="number" id="rvJ" min="20" max="95" value="${esc(st.review_join_score)}"></label>
              <label class="f" for="rvS">Sale mở xem (nhóm/lần)<input type="number" id="rvS" min="0" max="15" value="${esc(st.scout_per_run)}"></label></div>
            <label class="row small"><input type="checkbox" id="rvBest" ${st.review_use_best_groups!=="0"?"checked":""}> Khi đã có nhóm mang về khách, lấy chỉ số của các nhóm đó làm chuẩn</label>
            <div><button class="btn sm primary" type="submit">Lưu và chấm lại</button></div></form></details></div>
      <div><h4>Kho chủ đề CEO chọn</h4>
        <ul class="recent">${d.stats.slice().sort((a,b)=>b.leads-a.leads||b.groups-a.groups).slice(0,8).map(k=>`<li><span>${esc(k.keyword)}</span><span class="muted small">${k.groups} nhóm · ${k.leads} khách${k.last_searched?` · tìm ${fmtDate(k.last_searched)}`:" · chưa tìm"}</span></li>`).join("")}</ul>
        <details><summary class="small">Sửa kho chủ đề và cài đặt</summary>
          <form id="gfForm" class="stack" style="margin-top:8px">
            <label class="f" for="gfPool">Chủ đề tìm nhóm (mỗi dòng một từ khóa)<textarea id="gfPool" rows="6">${esc(d.pool.join("\n"))}</textarea></label>
            <div class="grid2"><label class="f" for="gfTime">Giờ đi tìm<input type="time" id="gfTime" value="${esc(st.discover_time||"10:30")}"></label>
              <label class="f" for="gfK">Số chủ đề mỗi ngày<input type="number" id="gfK" min="1" max="6" value="${esc(st.discover_keywords_per_day)}"></label>
              <label class="f" for="gfAdd">Tự thêm tối đa (nhóm/ngày)<input type="number" id="gfAdd" min="0" max="30" value="${esc(st.discover_add_per_day)}"></label>
              <label class="f" for="gfJ">Xin vào tối đa (nhóm/nick/ngày)<input type="number" id="gfJ" min="0" max="5" value="${esc(st.join_per_nick_day)}"></label>
              <label class="f" for="gfB">Lướt bảng tin trước khi tìm (phút)<input type="number" id="gfB" min="0" max="10" step="0.5" value="${esc(st.browse_minutes)}"></label></div>
            <label class="row small"><input type="checkbox" id="gfOn" ${st.discover_enabled==="1"?"checked":""}> Tự tìm nhóm mỗi ngày</label>
            <label class="row small"><input type="checkbox" id="gfJOn" ${st.join_enabled==="1"?"checked":""}> Tự xin vào nhóm mới (nhóm bắt trả lời câu hỏi thì để sếp tự vào)</label>
            <div><button class="btn sm primary" type="submit">Lưu</button></div></form></details></div>
    </div>`;
}
$("#gfBody").addEventListener("click",async e=>{ const t=e.target; let b;
  try{
    if(t.closest("#gfEdit")){ const cur=(ST.gf.today||[]).join(", "); const wrap=t.closest(".gf-today");
      wrap.innerHTML=`<form class="row grow" id="gfTodayF" style="gap:6px;flex-wrap:nowrap;width:100%"><input type="text" class="grow" id="gfTodayIn" value="${esc(cur)}" aria-label="Chủ đề hôm nay, cách nhau bằng dấu phẩy" placeholder="VD hội chạy quảng cáo facebook, nguồn hàng sỉ"><button class="btn sm primary" type="submit">Lưu</button></form>`; $("#gfTodayIn").focus(); return; }
    if(t.closest("#gfReroll")){ await api("/group-finder/reroll","POST"); toast("CEO đã chọn lại chủ đề hôm nay"); return loadGroups(); }
    if((b=t.closest("[data-gfadd]"))){ await api(`/group-finder/candidates/${b.dataset.gfadd}/add`,"POST"); toast("Đã thêm nhóm vào danh sách, sale sẽ xin vào nhóm"); return loadGroups(); }
    if(t.closest("#gfRev")){ const r=await api("/group-finder/review","POST"); toast(`Tuấn chấm lại: nên vào ${r.result.join}, cân nhắc ${r.result.consider}, bỏ qua ${r.result.skip}; thêm ${r.result.added} nhóm`); return loadGroups(); }
    if((b=t.closest("[data-gfign]"))){ await api(`/group-finder/candidates/${b.dataset.gfign}/ignore`,"POST"); return loadGroups(); }
  }catch(err){ toast(err.message); } });
$("#gfBody").addEventListener("submit",async e=>{ e.preventDefault(); const f=e.target;
  try{
    if(f.id==="gfTodayF"){ await api("/group-finder/today","POST",{keywords:$("#gfTodayIn").value.split(/[,;\n]/)}); toast("Đã đổi chủ đề tìm nhóm hôm nay"); document.activeElement.blur(); return loadGroups(); }
    if(f.id==="gfRevForm"){ await api("/group-finder","PUT",{review_posts_day:+$("#rvP").value,review_avg_reactions:+$("#rvR").value,review_avg_comments:+$("#rvC").value,review_growth_week:+$("#rvG").value,review_min_members:+$("#rvM").value,review_join_score:+$("#rvJ").value,scout_per_run:+$("#rvS").value,review_use_best_groups:$("#rvBest").checked});
      const r=await api("/group-finder/review","POST"); toast(`Đã lưu chuẩn. Tuấn chấm lại: nên vào ${r.result.join}, cân nhắc ${r.result.consider}, bỏ qua ${r.result.skip}`); document.activeElement.blur(); return loadGroups(); }
    if(f.id==="gfForm"){ await api("/group-finder","PUT",{pool:$("#gfPool").value.split("\n"),discover_time:$("#gfTime").value,discover_keywords_per_day:+$("#gfK").value,discover_add_per_day:+$("#gfAdd").value,join_per_nick_day:+$("#gfJ").value,browse_minutes:+$("#gfB").value,discover_enabled:$("#gfOn").checked,join_enabled:$("#gfJOn").checked}); toast("Đã lưu cài đặt tìm nhóm"); document.activeElement.blur(); return loadGroups(); }
  }catch(err){ toast(err.message); } });
$("#gfRun").onclick=async()=>{ try{ const r=await api("/group-finder/run","POST",{}); const s=(ST.sales||[]).find(x=>x.id===r.sale_id); toast(`${s?s.name:"Sale"}${r.account?` (nick ${r.account})`:""} đang lướt Facebook rồi tìm nhóm: ${r.keywords.join(", ")}`); }catch(e){ toast(e.message); } };
$("#gfJoin").onclick=async()=>{ try{ const r=await api("/group-finder/join","POST",{}); toast(`${r.sales} nick đang xin vào các nhóm mới`); }catch(e){ toast(e.message); } };

