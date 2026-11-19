/* --------------------------------------------- Bảo trả lời khách hỏi mua trong nhóm */
const RP_ST={draft:"Chờ sếp duyệt",approved:"Đã duyệt, chờ gửi",sent:"Đã gửi",failed:"Gửi lỗi",skipped:"Bỏ qua"};
const rpTime=t=>t?`${t.slice(11,16)} ${t.slice(8,10)}/${t.slice(5,7)}`:"";
async function loadRp(quiet){ const st=$("#rpSt").value;
  try{ [ST.rp,ST.fd]=await Promise.all([api("/replies"+(st?"?status="+st:"")),api("/feed")]); }catch(e){ if(!quiet) toast(e.message); return; } renderRp(); }
const fdOf=id=>((ST.fd||{}).nicks||[]).find(n=>n.id===id);
function renderRp(){ const d=ST.rp, st=d.stats;
  const b=$("#rpBadge"); b.hidden=!st.draft; b.textContent=st.draft||""; b.title=st.draft?`${st.draft} câu trả lời chờ sếp duyệt`:"";
  $("#rpStats").innerHTML=[[st.draft,"Chờ sếp duyệt"],[st.approved,"Đã duyệt, chờ gửi"],[st.today,"Đã gửi hôm nay"],[st.sent,"Đã gửi tất cả"]].map(([v,l])=>`<div class="pr-stat"><b>${v}</b><span>${l}</span></div>`).join("");
  $("#rpNicks").innerHTML=d.nicks.length?d.nicks.map(n=>{ const f=fdOf(n.id); return `<li><span><b>${esc(n.name)}</b></span><span class="act small muted">${n.left?`còn ${n.left} lượt`:"hết lượt hôm nay"}</span>
      <span class="meter" role="img" aria-label="Đã dùng ${n.used}/${n.limit} lượt bình luận hôm nay"><i style="width:${n.limit?Math.min(100,n.used/n.limit*100):100}%"></i></span>
      <span class="small muted">Hôm nay ${n.used}/${n.limit} câu, trong đó chào người bán ${n.seller_used??0}/${n.seller_limit??0}</span>
      ${f?`<span class="fd-line">Lướt bảng tin ${f.scans} lượt (tự động tối đa ${f.plan.scans}/ngày) · đọc ${f.read} bài · ${f.buyers} hỏi mua, ${f.sellers} người bán · ${esc(f.plan.why)}</span>`:""}</li>`; }).join("")
    :`<li class="muted small">Chưa có nick nào đăng nhập và đang làm việc.</li>`;
  const k=d.skill; $("#rpSkill").innerHTML=`<div class="rp-lv"><b>${esc(k.name)}</b><span class="small muted">${k.samples} mẫu đã học · chấm ${k.graded} câu tự viết${k.graded?`, đạt ${k.pass_rate}%`:""} · gọi Claude ${k.calls} lần${k.master?` · tiết kiệm ${k.saved} lần`:""}</span>
      <button type="button" class="btn sm ghost" id="rpRelearn" title="Bảo gọi Claude và chấm lại câu tự viết từ đầu">Cho học lại</button></div>
    ${k.next?`<p class="small muted" style="margin:0">Lên ${esc(k.next.name)} cần ${k.next.samples} mẫu, ${k.next.graded} câu được chấm, đạt từ ${k.next.pass_rate}%.</p>`:`<p class="small" style="margin:0">Bảo tự viết câu trả lời, không gọi Claude nữa.</p>`}
    ${d.samples.length?`<ul class="rp-samples">${d.samples.slice(0,5).map(x=>`<li><span>${esc(x.text)}</span><span class="chip${x.source==="claude"?"":x.score>=8?" ok":" warn"}">${x.source==="claude"?"Mẫu":"Bảo · "+(x.score??"?")+"/10"}</span></li>`).join("")}</ul>`:`<p class="muted small" style="margin:0">Chưa có mẫu. Câu Claude viết và câu sếp sửa khi duyệt sẽ được lưu ở đây.</p>`}`;
  const stop=(ST.fd||{}).no_pitch||[]; $("#fdStop").hidden=!stop.length; $("#fdStop").textContent=stop.length?`Ngừng chào người bán ở ${stop.length} nhóm vì nhóm đã xóa bình luận chào: ${stop.map(g=>`${g.name} (tới ${g.no_pitch_until.slice(8,10)}/${g.no_pitch_until.slice(5,7)})`).join("; ")}`:"";
  const kf=$("#rpKind").value, items=d.items.filter(x=>!kf||(x.kind||"buyer")===kf);
  $("#rpList").innerHTML=items.length?items.map(it=>{ const edit=["draft","failed"].includes(it.status), sell=it.kind==="seller", fn=(it.image||"").split(/[\\/]/).pop();
    return `<article class="rp-item ${it.status}"><span class="fr-ava" aria-hidden="true">${esc((it.author||"?").trim().charAt(0).toUpperCase())}</span>
      <div class="who">${it.author_url?`<a href="${esc(it.author_url)}" target="_blank" rel="noopener">${esc(it.author)}</a>`:`<b>${esc(it.author)}</b>`}<span class="small muted">${esc(it.group_name||"")} · nick ${esc(it.nick||"")}</span><span class="chip ${sell?"seller":it.kind==="general"?"":"buyer"}">${sell?"Người bán online":it.kind==="general"?(/mời sỉ/i.test(it.reason||"")?"Mời sỉ":"Bình luận theo nhóm"):"Hỏi mua"}</span><span class="chip ${it.status==="sent"?"ok":it.status==="failed"?"bad":it.status==="draft"?"warn":""}">${RP_ST[it.status]||it.status}</span></div>
      ${it.score!=null||it.reason?`<div class="rp-why">${it.score!=null?`<span class="sc">Điểm ${it.score}</span>`:""}${it.reason?`<span>${esc(it.reason)}</span>`:""}${it.origin==="feed"?`<span>· từ bảng tin nhóm</span>`:""}</div>`:""}
      <p class="rp-q"><b>${sell||it.kind==="general"?"Người đăng viết":"Khách hỏi"}${it.post_url?` · <a href="${esc(it.post_url)}" target="_blank" rel="noopener">mở bài</a>`:""}</b>${esc((it.post_text||"").slice(0,400))}</p>
      <div class="rp-a">${edit?`<label class="small muted" for="rpT${it.id}">Câu trả lời ${it.source==="claude"?"(Claude viết)":"(Bảo tự viết)"}</label><textarea id="rpT${it.id}" data-rptext="${it.id}" maxlength="600">${esc(it.reply||"")}</textarea>`
        :`<p class="said">${esc(it.reply||"")}</p>`}
        ${it.image&&!sell?`<span class="rp-img">${DEMO?"":`<img src="/api/image?path=${encodeURIComponent(it.image)}" alt="" loading="lazy">`}Kèm 1 ảnh: ${esc(fn)}</span>`:sell?`<span class="rp-img">Chỉ chữ, không ảnh</span>`:""}</div>
      <div class="acts">${edit?`<button type="button" class="btn sm primary" data-rp="approve" data-id="${it.id}">${it.status==="failed"?"Duyệt gửi lại":"Duyệt và gửi"}</button><button type="button" class="btn sm ghost" data-rp="skip" data-id="${it.id}">Bỏ qua</button><button type="button" class="btn sm ghost danger" data-rp="junk" data-id="${it.id}" title="Người bán khác / không hợp: ghi nhớ data rác">Không hợp</button>`:""}
        ${it.status==="approved"?`<span class="meta">Nick gửi lúc ${rpTime(it.scheduled_for)}</span><button type="button" class="btn sm ghost" data-rp="skip" data-id="${it.id}">Hủy gửi</button>`:""}
        ${it.status==="sent"?`<span class="meta">Đã gửi ${rpTime(it.sent_at)}</span>${it.shot?`<a class="btn sm ghost" href="${esc(it.shot)}" target="_blank" rel="noopener">Ảnh chụp</a>`:""}`:""}
        ${it.status==="failed"&&it.error?`<span class="meta" style="color:var(--danger)">${esc(it.error)}</span>`:""}</div></article>`; }).join("")
    :`<p class="muted small">${$("#rpSt").value||kf?"Không có câu nào ở mục này.":"Chưa có bài nào chờ bình luận. Bấm “Lướt bảng tin ngay”, hoặc nhắn CEO: “cho các nick lướt bảng tin nhóm và comment”."}</p>`;
  const F=(ST.fd||{}).settings; if(F) $("#fdSetF").innerHTML=`<div class="fr-set"><label class="row small"><input type="checkbox" id="fdsOn"${F.feed_enabled!=="0"?" checked":""}> Mọi nick tự lướt bảng tin nhóm mỗi ngày</label>
    <label class="f" for="fdsN">Bài đọc mỗi lượt (ít nhất)<input type="number" id="fdsN" min="10" max="60" value="${esc(F.feed_min_posts||"20")}"></label>
    <label class="f" for="fdsS">Lượt lướt tối đa / nick / ngày<input type="number" id="fdsS" min="1" max="4" value="${esc(F.feed_scans_day||"2")}"></label>
    <label class="f" for="fdsM">Điểm tối thiểu để bình luận<input type="number" id="fdsM" min="40" max="95" value="${esc(F.feed_min_score||"70")}"></label>
    <label class="row small"><input type="checkbox" id="fdsImg"${F.feed_buyer_image!=="0"?" checked":""}> Bình luận người hỏi mua kèm 1 ảnh</label>
    <h4 class="rp-set-h">Bình luận đều mọi nhóm</h4>
    <label class="row small" style="grid-column:1/-1"><input type="checkbox" id="fdsAll"${F.feed_comment_all!=="0"?" checked":""}> Bình luận cả bài không có từ khóa liên quan (Claude viết câu đúng nội dung bài, kèm Zalo)</label>
    <label class="f" for="fdsSty" style="grid-column:1/-1">Kiểu bình luận ở bài không liên quan<select id="fdsSty"><option value="invite"${F.feed_general_style!=="natural"?" selected":""}>Mời sỉ: đáp một câu đúng bài rồi mời nhập sỉ, làm đại lý (bỏ qua nhóm cấm bán hàng)</option><option value="natural"${F.feed_general_style==="natural"?" selected":""}>Tự nhiên: góp chuyện, giới thiệu nhẹ là xưởng (nhóm cấm bán hàng thì không kèm Zalo)</option></select></label>
    <label class="f" for="fdsPG">Bình luận tối đa / nhóm / ngày<input type="number" id="fdsPG" min="1" max="3" value="${esc(F.feed_per_group_day||"2")}"></label>
    <label class="f" for="fdsGap">Giãn cách tối thiểu giữa 2 bình luận của 1 nick (phút)<input type="number" id="fdsGap" min="30" max="240" value="${esc(F.reply_gap_min||"60")}"></label>
    <h4 class="rp-set-h">Chào người bán online</h4>
    <label class="row small"><input type="checkbox" id="fdsSel"${F.feed_seller_enabled!=="0"?" checked":""}> Chào nhẹ người đang bán hàng online (chỉ chữ, kèm Zalo)</label>
    <label class="f" for="fdsSD">Câu chào tối đa / nick / ngày<input type="number" id="fdsSD" min="0" max="3" value="${esc(F.feed_seller_per_nick_day||"2")}"></label>
    <label class="f" for="fdsW" style="grid-column:1/-1">Dấu hiệu người bán thêm (cách nhau dấu phẩy)<input type="text" id="fdsW" maxlength="300" value="${esc(F.feed_seller_words||"")}" placeholder="VD: tích xanh, nuôi tài khoản, ngân sách ads"></label></div>
    <p class="small muted" style="margin:8px 0">Số lượt lướt thật mỗi ngày còn tùy nick: nick mới hoặc vừa bị chặn 1 lượt, nick đã có đủ câu chờ gửi thì không lướt thêm, lượt sau cách lượt trước khoảng 3 giờ, chỉ trong giờ làm.</p>
    <button class="btn sm primary" type="submit">Lưu cài đặt</button>`;
  const S2=d.settings; $("#rpSetF").innerHTML=`<div class="fr-set"><label class="row small"><input type="checkbox" id="rpsOn"${S2.replies_enabled!=="0"?" checked":""}> Bảo tự tìm bài hỏi mua mỗi ngày</label>
    <label class="f" for="rpsTime">Giờ tìm<input type="time" id="rpsTime" value="${esc(S2.replies_time||"09:20")}"></label>
    <label class="f" for="rpsDay">Câu trả lời tối đa / nick / ngày<input type="number" id="rpsDay" min="0" max="10" value="${esc(S2.replies_per_nick_day||"5")}"></label>
    <label class="f" for="rpsG">Số nhóm đọc mỗi lượt<input type="number" id="rpsG" min="1" max="6" value="${esc(S2.replies_groups_per_run||"3")}"></label>
    <label class="f" for="rpsP">Bài tối đa / nhóm<input type="number" id="rpsP" min="1" max="10" value="${esc(S2.replies_per_group||"4")}"></label>
    <label class="f" for="rpsC" style="grid-column:1/-1">Dòng liên hệ cuối câu (trống thì dùng dòng của Up bài)<input type="text" id="rpsC" maxlength="120" value="${esc(S2.reply_contact||"")}" placeholder="${esc(d.contact||"")}"></label></div>
    <p class="small muted" style="margin:8px 0">Tối đa 10 câu mỗi nick mỗi ngày. Câu chỉ được gửi trong giờ làm của nick (Nhân viên sale → giờ làm việc), cách nhau 45–90 phút.</p>
    <button class="btn sm primary" type="submit">Lưu cài đặt</button>`; }
$("#rpSt").onchange=()=>loadRp(); $("#rpKind").onchange=()=>renderRp();
$("#fdRun").onclick=async()=>{ try{ const r=await api("/feed/run","POST",{}); toast(r.queued.length?`${r.queued.length} nick đang lướt bảng tin nhóm: ${r.queued.join(", ")}. Xong Bảo báo ở Văn phòng`:`Chưa nick nào lướt được: ${r.skipped.join("; ")}`); setTimeout(()=>loadRp(true),4000); }catch(e){ toast(e.message); } };
$("#fdSetF").addEventListener("submit",async e=>{ e.preventDefault(); try{ ST.fd=await api("/feed-settings","PUT",{feed_enabled:$("#fdsOn").checked?"1":"0",feed_min_posts:$("#fdsN").value,feed_scans_day:$("#fdsS").value,feed_min_score:$("#fdsM").value,feed_buyer_image:$("#fdsImg").checked?"1":"0",feed_seller_enabled:$("#fdsSel").checked?"1":"0",feed_seller_per_nick_day:$("#fdsSD").value,feed_seller_words:$("#fdsW").value,feed_comment_all:$("#fdsAll").checked?"1":"0",feed_general_style:$("#fdsSty").value,feed_per_group_day:$("#fdsPG").value,reply_gap_min:$("#fdsGap").value}); loadRp(true); toast("Đã lưu cài đặt lướt bảng tin"); }catch(err){ toast(err.message); } });
$("#rpRun").onclick=async()=>{ try{ const r=await api("/replies/scan","POST",{}); toast(`Nick ${r.account} đang mở các nhóm sôi nổi cho Bảo đọc. Xong Bảo báo ở Văn phòng`); setTimeout(()=>loadRp(true),4000); }catch(e){ toast(e.message); } };
$("#rpAll").onclick=async()=>{ try{ const r=await api("/replies/approve-all","POST",{}); toast(r.approved?`Đã duyệt ${r.approved} câu${r.later?`, ${r.later} câu dời sang mai vì nick hết lượt hôm nay`:""}`:"Không có câu nào chờ duyệt"); loadRp(true); }catch(e){ toast(e.message); } };
$("#v-replies").addEventListener("click",async e=>{
  if(e.target.id==="rpRelearn"){ try{ await api("/replies/relearn","POST",{}); toast("Bảo sẽ gọi Claude và chấm lại câu tự viết từ đầu"); loadRp(true); }catch(err){ toast(err.message); } return; }
  const bt=e.target.closest("[data-rp]"); if(!bt) return; const rid=bt.dataset.id, a=bt.dataset.rp; const ta=$(`[data-rptext="${rid}"]`);
  try{ const r=await api(`/replies/${rid}`,"PUT",{action:a,reply:ta?ta.value:null});
    toast(a==="approve"?(r.later?"Đã duyệt. Nick hết lượt hôm nay nên gửi sáng mai":`Đã duyệt. Nick gửi lúc ${rpTime(r.scheduled_for)}`):a==="junk"?"Đã bỏ và ghi nhớ đây là data rác":"Đã bỏ qua"); loadRp(true); }catch(err){ toast(err.message); } });
$("#rpSetF").addEventListener("submit",async e=>{ e.preventDefault(); try{ ST.rp=await api("/replies-settings","PUT",{replies_enabled:$("#rpsOn").checked?"1":"0",replies_time:$("#rpsTime").value,replies_per_nick_day:$("#rpsDay").value,replies_groups_per_run:$("#rpsG").value,replies_per_group:$("#rpsP").value,reply_contact:$("#rpsC").value}); loadRp(true); toast("Đã lưu cài đặt trả lời khách"); }catch(err){ toast(err.message); } });
setInterval(()=>{ if(!UX.idle()&&ST.view==="replies"&&!document.querySelector("#v-replies :focus")) loadRp(true); },15000);

