/* --------------------------------------------- kết bạn trong nhóm */
const FR_ST={suggested:"Chờ gửi",opened:"Đã mở hồ sơ",sent:"Đã gửi lời mời",accepted:"Đã đồng ý",skipped:"Bỏ qua"};
async function loadFr(quiet){ const q=new URLSearchParams(); if($("#frAcc").value) q.set("account_id",$("#frAcc").value); if($("#frSt").value) q.set("status",$("#frSt").value);
  try{ ST.fr=await api("/friends"+(q.toString()?"?"+q:"")); }catch(e){ if(!quiet) toast(e.message); return; } renderFr(); }
function renderFr(){ const d=ST.fr, st=d.stats;
  const b=$("#frBadge"), w=d.nicks.reduce((s,n)=>s+(n.opened||0),0); b.hidden=!w; b.textContent=w||""; b.title=w?`${w} hồ sơ đã mở chờ sale đánh dấu đã gửi`:"";
  $("#frStats").innerHTML=[[st.found,"Người Tuấn gợi ý"],[st.today,"Lời mời hôm nay"],[st.sent,"Đã gửi tất cả"],[st.accepted+(st.accept_rate!=null?` <small class="muted" style="font-size:13px">${st.accept_rate}%</small>`:""),"Đã đồng ý kết bạn"]]
    .map(([v,l])=>`<div class="pr-stat"><b>${v}</b><span>${l}</span></div>`).join("");
  const acc=$("#frAcc"), cur=acc.value; acc.innerHTML=`<option value="">Mọi nick</option>`+d.nicks.map(n=>`<option value="${n.id}">${esc(n.name)}</option>`).join(""); acc.value=cur;
  $("#frRank").innerHTML=d.groups.length?d.groups.map((g,i)=>{ const mt=g.known?[g.per_day?`${vn1(g.per_day)} bài/ngày`:"",g.avg_comments!=null?`${vn1(g.avg_comments)} bình luận/bài`:"",g.growth?`+${vn1(g.growth)}% thành viên/tuần`:"",g.members?`${(+g.members).toLocaleString("vi-VN")} thành viên`:""].filter(Boolean).join(" · "):"Chưa có chỉ số: Tuấn đọc khi rà soát nhóm";
      return `<li><span class="no">${i+1}</span><span class="nm" title="${esc(g.name)}">${g.focus?"★ ":""}${esc(g.name)}${g.target==="exclude"?' <span class="chip bad">Sếp tránh</span>':""}</span>
        <span class="act"><button type="button" class="btn sm" data-frscan="${g.id}" data-acc="${g.nicks[0]?g.nicks[0].id:""}" title="Mở nhóm bằng nick ${esc(g.nicks.map(n=>n.name).join(", "))}">Tìm người</button></span>
        <span class="fr-score"><span class="meter" role="img" aria-label="Điểm sôi nổi ${g.score}/100"><i style="width:${Math.max(3,g.score)}%"></i></span><b>${g.score}/100</b></span>
        <span class="mt">${esc(mt)}${g.focus?" · xếp trên vì sếp chọn tập trung":""}${g.found?` · đã gợi ý ${g.found}, gửi ${g.sent}, đồng ý ${g.accepted}`:""}${g.scanned_at?` · đọc ${fmtDate(g.scanned_at)}`:""}</span></li>`; }).join("")
    :`<li class="muted small">Nick chưa ở nhóm nào có link. Vào <a href="#groups">Hội nhóm</a> → Tuấn rà soát nhóm của nick.</li>`;
  $("#frNicks").innerHTML=d.nicks.length?d.nicks.map(n=>`<li><span><b>${esc(n.name)}</b> <span class="small muted">${esc(n.sale||"")}</span>${n.resting?' <span class="chip bad">Đang nghỉ</span>':n.factor<1?' <span class="chip warn" title="Nick mới hoặc vừa bị chặn">Nửa trần</span>':""}</span>
      <span class="act"><button type="button" class="btn sm primary" data-fropen="${n.id}"${!n.left||!n.wait?" disabled":""}>Mở ${Math.min(5,n.left,n.wait)||""} hồ sơ</button></span>
      <span class="meter" role="img" aria-label="Đã gửi ${n.used}/${n.limit} lời mời hôm nay"><i style="width:${n.limit?Math.min(100,n.used/n.limit*100):100}%"></i></span>
      <span class="small muted">Hôm nay ${n.used}/${n.limit} lời mời · chờ gửi ${n.wait}${n.opened?` · <b style="color:var(--honey)">${n.opened} đã mở chờ đánh dấu</b>`:""} · đồng ý ${n.accepted}/${n.sent_all}</span></li>`).join("")
    :`<li class="muted small">Chưa có nick nào đang làm việc.</li>`;
  $("#frList").innerHTML=d.items.length?d.items.map(it=>`<article class="fr-item${it.status==="opened"?" opened":""}"><span class="fr-ava" aria-hidden="true">${esc((it.name||"?").trim().charAt(0).toUpperCase())}</span>
      <div class="who"><a href="${esc(it.profile_url)}" target="_blank" rel="noopener">${esc(it.name)}</a><span class="small muted">${esc(it.group_name||"")} · nick ${esc(it.nick||"")}</span>${it.status!=="suggested"?`<span class="chip ${it.status==="accepted"?"ok":it.status==="skipped"?"":"warn"}">${FR_ST[it.status]}</span>`:""}<span class="sc" title="Điểm hợp tệp khách">${it.score} điểm</span></div>
      <div class="why">${(it.reason||"").split("; ").filter(Boolean).map(r=>`<span class="chip">${esc(r)}</span>`).join("")}</div>
      ${it.snippet?`<p class="snip">“${esc(it.snippet)}”</p>`:""}
      <div class="acts">${["suggested","opened"].includes(it.status)?`<button type="button" class="btn sm primary" data-frmark="sent" data-id="${it.id}">Đã gửi lời mời</button><button type="button" class="btn sm ghost" data-frmark="skipped" data-id="${it.id}">Bỏ qua</button><button type="button" class="btn sm ghost danger" data-frmark="junk" data-id="${it.id}" title="Không hợp tệp khách: Mai ghi nhớ là data rác">Không hợp</button>`
        :it.status==="sent"?`<button type="button" class="btn sm" data-frmark="accepted" data-id="${it.id}">Họ đã đồng ý</button><button type="button" class="btn sm ghost" data-frmark="suggested" data-id="${it.id}">Chưa gửi</button>`:`<button type="button" class="btn sm ghost" data-frmark="suggested" data-id="${it.id}">Đưa lại danh sách chờ</button>`}</div></article>`).join("")
    :`<p class="muted small">${$("#frSt").value?"Không có ai ở trạng thái này.":"Chưa có ai chờ gửi. Bấm “Tuấn tìm người ngay” hoặc “Tìm người” ở một nhóm."}</p>`;
  const S2=d.settings; $("#frSetF").innerHTML=`<div class="fr-set"><label class="row small"><input type="checkbox" id="frsOn"${S2.friends_enabled==="1"?" checked":""}> Tuấn tự tìm người mỗi ngày</label>
    <label class="f" for="frsTime">Giờ tìm<input type="time" id="frsTime" value="${esc(S2.friends_time||"10:40")}"></label>
    <label class="f" for="frsDay">Lời mời tối đa / nick / ngày<input type="number" id="frsDay" min="0" max="30" value="${esc(S2.fbp_friends_day||"10")}"></label>
    <label class="f" for="frsG">Số nhóm đọc mỗi lượt<input type="number" id="frsG" min="1" max="5" value="${esc(S2.friends_groups_per_run||"2")}"></label>
    <label class="f" for="frsP">Gợi ý tối đa / nhóm<input type="number" id="frsP" min="1" max="40" value="${esc(S2.friends_per_group||"12")}"></label></div>
    <p class="small muted" style="margin:8px 0">Nên giữ dưới 10–15 lời mời mỗi nick mỗi ngày, gửi rải rác trong ngày. Tỷ lệ đồng ý dưới 30% là dấu hiệu gửi nhầm người: giảm lời mời và nhờ Tuấn chọn kỹ hơn.</p>
    <button class="btn sm primary" type="submit">Lưu cài đặt</button>`; }
$("#frAcc").onchange=()=>loadFr(); $("#frSt").onchange=()=>loadFr();
$("#frRun").onclick=async()=>{ try{ const r=await api("/friends/scan","POST",{}); toast(`Nick ${r.account} đang mở nhóm cho Tuấn đọc. Xong Tuấn báo ở Văn phòng`); setTimeout(()=>loadFr(true),4000); }catch(e){ toast(e.message); } };
$("#v-friends").addEventListener("click",async e=>{
  const sc=e.target.closest("[data-frscan]"); if(sc){ try{ const r=await api("/friends/scan","POST",{account_id:+sc.dataset.acc||null,group_ids:[+sc.dataset.frscan]}); toast(`Nick ${r.account} đang mở nhóm cho Tuấn đọc`); setTimeout(()=>loadFr(true),4000); }catch(err){ toast(err.message); } return; }
  const op=e.target.closest("[data-fropen]"); if(op){ try{ const r=await api("/friends/open","POST",{account_id:+op.dataset.fropen,n:5}); toast(`Chrome của nick đang mở ${r.names.length} trang: ${r.names.join(", ")}. Bấm Thêm bạn bè trên từng trang rồi đánh dấu Đã gửi. Cửa sổ tự đóng sau 15 phút`); loadFr(true); }catch(err){ toast(err.message); } return; }
  const mk=e.target.closest("[data-frmark]"); if(mk){ try{ const r=await api(`/friends/${mk.dataset.id}`,"PUT",{status:mk.dataset.frmark}); if(r.over) toast(`Nick đã gửi ${r.quota.used}/${r.quota.limit} lời mời hôm nay, quá trần an toàn. Dừng gửi tới mai`); else if(mk.dataset.frmark==="junk") toast("Đã bỏ. Mai ghi nhớ đây là data rác, lần sau không gợi ý lại"); loadFr(true); }catch(err){ toast(err.message); } } });
$("#frSetF").addEventListener("submit",async e=>{ e.preventDefault(); try{ ST.fr=await api("/friends-settings","PUT",{friends_enabled:$("#frsOn").checked?"1":"0",friends_time:$("#frsTime").value,fbp_friends_day:$("#frsDay").value,friends_groups_per_run:$("#frsG").value,friends_per_group:$("#frsP").value}); loadFr(true); toast("Đã lưu cài đặt kết bạn"); }catch(err){ toast(err.message); } });
setInterval(()=>{ if(!UX.idle()&&ST.view==="friends"&&!document.querySelector("#v-friends :focus")) loadFr(true); },15000);
