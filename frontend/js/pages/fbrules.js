/* ---------- LUẬT FACEBOOK ---------- */
const FBP_LIMITS=[["fbp_posts_day","Bài / nick / ngày",1,20],["fbp_gap_minutes","Cách nhau tối thiểu (phút)",10,240],["fbp_bumps_day","Lượt up bài / nick / ngày",0,20],
  ["fbp_joins_day","Xin vào nhóm / nick / ngày",0,10],["fbp_friends_day","Lời mời kết bạn / nick / ngày (sale tự bấm)",0,30],["fbp_same_group_hours","1 nick đăng lại cùng nhóm sau (giờ)",6,168],["fbp_hashtags_max","Hashtag tối đa / bài",0,15],
  ["fbp_new_nick_days","Nick mới chạy nửa giới hạn (ngày)",0,60],["fbp_rest_days","Nick bị chặn nghỉ (ngày)",0,30],["fbp_after_days","Sau khi nghỉ chạy nửa giới hạn (ngày)",0,30]];
async function loadFbp(){ try{ ST.fbp=await api("/fb-policy"); }catch(e){ toast(e.message); return; } renderFbp(); }
function renderFbp(){
  const d=ST.fbp; if(!d) return; const st=d.settings;
  const nw=(d.changes||[]).filter(x=>x.status==="new");
  $("#fbpChanges").innerHTML=nw.map(x=>`<div class="fbp-chg"><b>⚠ Facebook đổi chính sách: ${esc(x.name)}</b> <span class="small muted">phát hiện ${fmtTime(x.detected_at)} ${fmtDate(x.detected_at)}</span><pre>${esc(x.summary||"")}</pre>
     <div class="row wrap"><a class="btn sm" href="${esc(x.url)}" target="_blank" rel="noopener">Đọc trang gốc</a><button class="btn sm" data-chg="${x.id}">Đã đọc</button></div></div>`).join("");
  $("#fbpNicks").innerHTML=d.nicks.length?d.nicks.map(n=>{ const L=n.limits,U=n.used; const st=n.rest_until?`<span class="chip bad">Nghỉ tới ${fmtTime(n.rest_until)} ${fmtDate(n.rest_until)}</span> <button class="btn sm ghost" data-lift="${n.id}">Cho làm lại</button>`:n.factor<1?`<span class="chip warn">Nửa giới hạn</span>`:`<span class="chip ok">Bình thường</span>`;
    const c=(u,l)=>`<span${u>=l?' style="color:var(--danger);font-weight:700"':""}>${u}/${l}</span>`;
    return `<tr><td>${esc((n.sale_name?n.sale_name+" · ":"")+n.name)}</td><td class="num">${c(U.posts,L.posts)}</td><td class="num">${c(U.bumps,L.bumps)}</td><td class="num">${c(U.joins,L.joins)}</td><td class="num">${L.gap}′</td><td>${st}</td></tr>`; }).join("")
    :`<tr><td colspan="6" class="muted small">Chưa có nick nào đang chạy.</td></tr>`;
  $("#fbpLimitFields").innerHTML=FBP_LIMITS.map(([k,l,mn,mx])=>`<label class="f" for="fl-${k}">${l}<input type="number" id="fl-${k}" data-k="${k}" min="${mn}" max="${mx}" value="${esc(st[k]||"")}"></label>`).join("");
  $("#fbpOn").checked=st.fbp_enabled!=="0"; $("#fbpTighten").checked=st.fbp_auto_tighten!=="0";
  const rules=d.rules||[], cats=d.cats||{}, how=d.how||{}, srcs=Object.fromEntries((d.sources||[]).map(s=>[s.key,s]));
  $("#fbpRuleStats").textContent=`${rules.length} luật · ${rules.filter(r=>r.how==="check").length} luật CEO và sale tự kiểm trong bài · ${rules.filter(r=>r.how==="limit").length} luật giữ bằng giới hạn · luật đã ghi vào sổ kiến thức của Lan, Tuấn, CEO, sale, Vy`;
  $("#fbpRules").innerHTML=Object.entries(cats).map(([ck,cn])=>{ const rs=rules.filter(r=>r.cat===ck); if(!rs.length) return "";
    return `<div class="fbp-cat">${esc(cn)}</div><div class="fbp-rules">${rs.map(r=>`<div class="fbp-rule ${r.level}"><div class="chips"><span class="chip">${esc(how[r.how]||r.how)}</span>${r.level==="high"?'<span class="chip bad">Nghiêm trọng</span>':""}${r.custom?'<span class="chip ok">Luật của sếp</span>':""}</div>
      <b>${esc(r.title)}</b><p>${esc(r.rule)}</p>${r.do?`<p class="do"><b style="font-size:13px">Đội làm:</b> ${esc(r.do)}</p>`:""}
      ${r.src&&srcs[r.src]?`<a class="src" href="${esc(srcs[r.src].url)}" target="_blank" rel="noopener">Nguồn: ${esc(srcs[r.src].name)}</a>`:""}${r.custom?`<div><button class="btn sm ghost" data-delrule="${esc(r.id)}">Xóa luật</button></div>`:""}</div>`).join("")}</div>`; }).join("");
  const inc=d.incidents||[];
  $("#fbpInc").innerHTML=inc.length?inc.slice(0,8).map(i=>`<li><b>${i.kind==="block"?"Nick bị chặn":"Bài bị gỡ"}</b>${i.account_name?` · ${esc(i.account_name)}`:""}${i.group_name?` · ${esc(i.group_name)}`:""} <span class="muted">${fmtTime(i.created_at)} ${fmtDate(i.created_at)}</span><br>${esc(i.detail||"")}${i.lesson?`<br><b>Bài học:</b> ${esc(i.lesson)}`:""}</li>`).join("")
    :`<li class="muted">Chưa có sự cố nào. Khi nick bị chặn hay bài bị gỡ, Tuấn ghi lại nick đã làm gì và tự điều chỉnh.</li>`;
  $("#fbpRested").innerHTML=(d.rested_groups||[]).length?`<p class="small" style="margin:8px 0 0"><b>Nhóm đang tạm ngừng đăng:</b> ${d.rested_groups.map(g=>`${esc(g.name)} (tới ${fmtDate(g.policy_rest_until)})`).join(", ")}</p>`:"";
  $("#fbpWatchOn").checked=st.fbp_watch_enabled!=="0"; $("#fbpWatchTime").value=st.fbp_watch_time||"06:40";
  $("#fbpWatchInfo").textContent=d.watch_last?`Tuấn đọc lần cuối ${fmtTime(d.watch_last)} ${fmtDate(d.watch_last)}. Trang có thay đổi thì Tuấn tóm tắt và báo sếp qua đây và Telegram.`:"Chưa đọc lần nào. Bấm “Đọc lại chính sách ngay” để Tuấn đọc lần đầu.";
  $("#fbpSources").innerHTML=(d.sources||[]).map(s=>`<tr><td><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.name)}</a></td><td class="small">${s.last_checked?fmtTime(s.last_checked)+" "+fmtDate(s.last_checked):"—"}</td><td class="small">${s.last_changed?fmtDate(s.last_changed):"—"}</td>
    <td>${s.status==="lỗi"?`<span class="chip bad" title="${esc(s.error||"")}">Không mở được</span>`:s.status==="có thay đổi"?'<span class="chip warn">Có thay đổi</span>':s.status==="đã đọc"?'<span class="chip ok">Đã đọc</span>':'<span class="chip">Chưa đọc</span>'}</td></tr>`).join("");
  const b=$("#fbpBadge"); if(b){ b.hidden=!nw.length; b.textContent=nw.length||""; }
}
$("#fbpLimits").addEventListener("submit",async e=>{ e.preventDefault(); const body={};
  e.target.querySelectorAll("[data-k]").forEach(i=>{ if(i.value!=="") body[i.dataset.k]=i.value; });
  body.fbp_enabled=$("#fbpOn").checked?"1":"0"; body.fbp_auto_tighten=$("#fbpTighten").checked?"1":"0";
  try{ ST.fbp=await api("/fb-policy/settings","PUT",body); renderFbp(); toast("Đã lưu giới hạn an toàn, Tuấn áp dụng từ lượt xếp lịch tới"); }catch(err){ toast(err.message); } });
$("#v-fbrules").addEventListener("change",async e=>{ if(e.target.id==="fbpWatchOn"||e.target.id==="fbpWatchTime"){
  try{ ST.fbp=await api("/fb-policy/settings","PUT",{fbp_watch_enabled:$("#fbpWatchOn").checked?"1":"0",fbp_watch_time:$("#fbpWatchTime").value||"06:40"}); renderFbp(); toast("Đã lưu lịch đọc chính sách"); }catch(err){ toast(err.message); } } });
$("#v-fbrules").addEventListener("click",async e=>{
  const c=e.target.closest("[data-chg]"), l=e.target.closest("[data-lift]"), d=e.target.closest("[data-delrule]");
  try{
    if(c){ ST.fbp=await api(`/fb-policy/changes/${c.dataset.chg}/read`,"POST"); renderFbp(); }
    if(l){ ST.fbp=await api(`/fb-policy/nicks/${l.dataset.lift}/lift`,"POST"); renderFbp(); toast("Nick làm lại, vẫn chạy nửa giới hạn tới hết hạn"); }
    if(d){ ST.fbp=await api(`/fb-policy/rules/${d.dataset.delrule}`,"DELETE"); renderFbp(); toast("Đã xóa luật"); }
  }catch(err){ toast(err.message); } });
$("#fbpRuleForm").addEventListener("submit",async e=>{ e.preventDefault();
  try{ ST.fbp=await api("/fb-policy/rules","POST",{title:$("#fbrTitle").value,text:$("#fbrText").value,phrases:$("#fbrPhr").value.split(/[,;\n]/).map(x=>x.trim()).filter(Boolean),level:$("#fbrLvl").value});
    e.target.reset(); renderFbp(); toast("Đã thêm luật. Cả đội học luật này và CEO, sale kiểm bài theo luật mới"); }catch(err){ toast(err.message); } });
$("#fbpCheck").onclick=async()=>{ const t=$("#fbpText").value.trim(); if(!t){ toast("Dán bài cần kiểm"); return; }
  try{ const r=await api("/fb-policy/check","POST",{text:t});
    $("#fbpCheckRes").innerHTML=r.issues.length?r.issues.map(i=>`<div class="fbp-issue"><span class="chip ${i.level==="high"?"bad":"warn"}">${i.level==="high"?"Chặn":"Nhắc"}</span><span>${esc(i.msg)}${i.hit?` (“${esc(i.hit)}”)`:""}</span></div>`).join("")
      +`<p class="small ${r.ok?"muted":"err"}">${r.ok?"Không có lỗi nghiêm trọng, bài vẫn được đăng nhưng CEO trừ điểm.":"Bài này sẽ bị chặn, không được đăng."}</p>`
      :`<p class="small" style="color:var(--accent)">✓ Không phạm luật nào.</p>`; }catch(err){ toast(err.message); } };
$("#fbpWatch").onclick=async e=>{ e.target.disabled=true; try{ await api("/fb-policy/watch","POST"); toast("Tuấn đang đọc lại các trang chính sách của Meta (khoảng 1 phút)"); setTimeout(loadFbp,6000); setTimeout(loadFbp,60000); }catch(err){ toast(err.message); } setTimeout(()=>e.target.disabled=false,8000); };

