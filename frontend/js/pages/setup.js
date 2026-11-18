/* --------------------------------------------- cài đặt */
const MODEL_NAME={"claude-haiku-5-5":"Haiku 5.5 (rẻ nhất)","claude-sonnet-5-5":"Sonnet 5.5 (cân bằng)","claude-opus-5-5":"Opus 5.5 (cao cấp)"};
const DAY_NAME=["T2","T3","T4","T5","T6","T7","CN"];
const usd=v=>"$"+(v<1?Number(v).toFixed(v<0.1?3:2):Number(v).toFixed(2));
async function loadCosts(){
  const [c,s]=await Promise.all([api("/costs"),api("/settings")]);
  const opts=v=>(s.models||Object.keys(MODEL_NAME)).map(m=>`<option value="${m}" ${m===v?"selected":""}>${MODEL_NAME[m]||m}</option>`).join("");
  $("#mPosts").innerHTML=opts(s.model_posts); $("#mReplies").innerHTML=opts(s.model_replies); $("#mMeeting").innerHTML=opts(s.model_meeting); $("#mCeo").innerHTML=opts(s.model_ceo||"claude-sonnet-5-5"); $("#mReview").innerHTML=opts(s.model_review||"claude-haiku-5-5");
  $("#cBatch").checked=s.use_batch==="1"; $("#cBudget").value=s.monthly_budget_usd||0; $("#cRounds").value=s.debate_rounds||"2";
  const days=(s.meeting_weekdays||"").split(",");
  $("#cDays").innerHTML=DAY_NAME.map((d,i)=>`<label><input type="checkbox" value="${i+1}" ${days.includes(String(i+1))?"checked":""}>${d}</label>`).join("");
  document.querySelectorAll("#presets .preset").forEach(b=>b.classList.toggle("on",b.dataset.preset===s.cost_preset));
  $("#costSpent").textContent=usd(c.spent);
  $("#costBudgetTxt").textContent=c.budget?`/ ${usd(c.budget)} ngân sách`:"(chưa đặt ngân sách)";
  const pct=c.budget?Math.min(100,c.spent/c.budget*100):0; const bar=$("#costBar"); bar.style.width=pct+"%"; bar.className=pct>=100?"bad":pct>=80?"warn":"";
  $("#costProj").textContent=!c.live&&!DEMO?"Đang chạy mô phỏng nên chưa tốn tiền. Thêm API key để bắt đầu đo chi phí thật.":`Dự báo cả tháng: ${usd(c.projected)}. Viết theo lô đã tiết kiệm ${usd(c.batch_saved)} tháng này.${c.pending_batches?` Đang có ${c.pending_batches} lô bài chờ xong.`:""}`;
  const st={ok:["ok","Trong ngân sách"],economy:["warn","Đã chuyển sang Haiku"],stop:["bad","Tạm ngừng AI"]}[c.state]||["",""]; $("#costState").className="chip "+st[0]; $("#costState").textContent=st[1];
  const mx=Math.max(0.0001,...c.daily.map(d=>d.cost));
  $("#costSpark").innerHTML=c.daily.length?c.daily.map(d=>`<div style="height:${Math.max(4,d.cost/mx*100)}%" title="${fmtDate(d.day)}: ${usd(d.cost)}"></div>`).join(""):'<span class="small muted">Chưa có dữ liệu</span>';
  const fb=c.fallback||{total:0,by_task:[]};
  $("#costFallback").innerHTML=!fb.total?(c.live?'<p class="muted" style="margin-top:8px">30 ngày qua mọi kết quả đều do Claude làm, không phải dùng nội dung mẫu.</p>':'')
    :`<div class="note warn" style="margin-top:8px"><b>${fb.total} lần phải dùng nội dung mẫu thay Claude</b> trong ${fb.days} ngày (trên ${fb.calls} lượt gọi). Bài, tin nhắn ở các lần này là mẫu có sẵn, không phải Claude viết.
      <ul style="margin:6px 0 0 18px">${fb.by_task.map(t=>`<li>${esc(t.label)}: ${t.n} lần — ${Object.entries(t.reasons).map(([r,n])=>`${esc(r)} (${n})`).join(", ")}</li>`).join("")}</ul>
      <span class="muted">Chi tiết ở màn Lỗi. Lỗi gọi Claude: kiểm tra khóa và tín dụng; bị cắt hoặc sai khuôn lặp lại nhiều: báo người lập trình.</span></div>`;
  $("#costRows").innerHTML=c.by_task.length?c.by_task.map(r=>`<tr><td>${esc(r.label)}${r.batched?` <span class="chip ok">${r.batched} theo lô</span>`:""}</td><td class="num">${r.calls}</td><td class="num">${(r.tin/1000).toFixed(1)}k / ${(r.tout/1000).toFixed(1)}k</td><td class="num"><b>${usd(r.cost)}</b></td></tr>`).join(""):'<tr><td colspan="4" class="muted">Chưa có lượt gọi AI nào trong tháng.</td></tr>';
}
$("#presets").addEventListener("click",async e=>{ const b=e.target.closest("[data-preset]"); if(!b) return; await api("/costs/preset","POST",{name:b.dataset.preset}); toast(`Đã chuyển sang gói ${b.querySelector("b").textContent}`); loadCosts(); });
$("#costForm").addEventListener("submit",async e=>{ e.preventDefault();
  const days=[...document.querySelectorAll("#cDays input:checked")].map(x=>x.value).join(",");
  await api("/settings","PUT",{model_posts:$("#mPosts").value,model_replies:$("#mReplies").value,model_meeting:$("#mMeeting").value,model_ceo:$("#mCeo").value,model_review:$("#mReview").value,use_batch:$("#cBatch").checked?"1":"0",monthly_budget_usd:$("#cBudget").value||"0",debate_rounds:$("#cRounds").value,meeting_weekdays:days,cost_preset:"tuy_chinh"});
  toast("Đã lưu cấu hình chi phí"); loadCosts(); });
function showFolder(f){ const box=$("#bFolderInfo"); box.hidden=false;
  if(!f.exists){ box.innerHTML=f.path?`<b>Không tìm thấy thư mục</b> ${esc(f.path)} trên máy chạy phần mềm.`:"Chưa chọn thư mục ảnh."; return; }
  const own=f.products.filter(p=>p.count);
  box.innerHTML=`<b>${f.count} ảnh</b> trong thư mục (${f.root_count||0} ảnh dùng chung). `
    +(own.length?`Có ảnh riêng cho: ${own.map(p=>`${esc(p.name)} (${p.count})`).join(", ")}.`:"Chưa có thư mục con theo tên sản phẩm, mọi bài sẽ dùng ảnh chung.")
    +(DEMO?"":`<div class="thumbs" style="margin-top:8px">${f.samples.slice(0,8).map(n=>`<figure><img src="/api/bump/image?name=${encodeURIComponent(n)}" alt="${esc(n)}" title="${esc(n)}"></figure>`).join("")}</div>`); }
async function loadBump(s){
  $("#bEnabled").checked=s.bump_enabled==="1"; $("#bFolder").value=s.bump_folder||""; $("#bTime").value=s.bump_time||"19:30";
  $("#bAge").value=s.bump_max_age_days||7; $("#bPer").value=s.bump_max_per_nick||8; $("#bGap").value=s.bump_gap_minutes||6; $("#bTexts").value=s.bump_texts||""; $("#bContact").value=s.bump_contact??""; loadBaoSkill();
  const bm=document.querySelector(`input[name=bMode][value=${s.bump_text_mode==="list"?"list":"ai"}]`); if(bm) bm.checked=true; $("#bTextsL").hidden=s.bump_text_mode!=="list";
  const st=ST.dash?.stats; $("#bumpToday").textContent=`Hôm nay đã up ${st?.bumps_today||0} lượt`;
  if(s.bump_folder) showFolder(await api("/bump/folder"));
}
const bumpPayload=()=>({bump_enabled:$("#bEnabled").checked?"1":"0",bump_folder:$("#bFolder").value.trim(),bump_time:$("#bTime").value,bump_max_age_days:$("#bAge").value,bump_max_per_nick:$("#bPer").value,bump_gap_minutes:$("#bGap").value,bump_texts:$("#bTexts").value,bump_contact:$("#bContact").value.trim(),bump_text_mode:(document.querySelector("input[name=bMode]:checked")||{}).value||"ai"});
document.querySelectorAll("input[name=bMode]").forEach(r=>r.addEventListener("change",()=>{ $("#bTextsL").hidden=r.value!=="list"||!r.checked; }));
async function loadBaoSkill(){ let d; try{ d=await api("/post-care"); }catch(e){ return; } const k=d.skill, box=$("#bSkill"); if(!box) return;
  const LV=["Học việc","Thạo việc","Giỏi","Master"]; const nx=k.next;
  box.innerHTML=`<div class="bk-top"><b>Tay nghề viết câu của Bảo:</b><span class="chip ${k.master?"ok":""}">${esc(k.name)}</span><span class="small muted">${k.master?"Bảo tự viết, không gọi Claude nữa"+(k.saved?` · đã bớt ${k.saved} lần gọi`:""):`Đang học từ Claude · đã gọi ${k.calls} lần`}</span></div>
    <ol class="bk-steps">${LV.map((n,i)=>`<li class="${i<k.level?"done":i===k.level?"on":""}">${n}</li>`).join("")}</ol>
    <p class="small muted" style="margin:2px 0 0">${k.samples} câu mẫu Claude đã lưu · ${k.graded} câu Bảo tự viết đã được Claude chấm, ${k.pass_rate}% đạt từ ${8} điểm${k.avg!=null?` (trung bình ${String(k.avg).replace(".",",")})`:""}.${nx?` Lên <b>${nx.name}</b> cần ${nx.samples} mẫu, ${nx.graded} câu chấm, ${nx.pass_rate}% đạt.`:""}</p>
    ${d.samples.length?`<details style="margin-top:6px"><summary class="small">Câu mẫu gần đây</summary><ul class="bk-list">${d.samples.map(x=>`<li><span class="bk-src ${x.source}">${x.source==="claude"?"Claude":"Bảo"+(x.score!=null?` ${x.score}/10`:"")}</span><span>${esc(x.text)}</span></li>`).join("")}</ul></details>`:""}
    ${k.level>0?`<button type="button" class="btn sm ghost" id="bRelearn" style="margin-top:8px">Cho Bảo học lại</button><span class="small muted"> Câu tự viết chưa ổn: Bảo gọi Claude và được chấm lại từ đầu, mẫu đã học vẫn giữ.</span>`:""}`;
  const rl=$("#bRelearn"); if(rl) rl.onclick=async()=>{ try{ await api("/post-care/relearn","POST",{}); toast("Bảo học lại: từ lượt sau gọi Claude viết câu và chấm câu Bảo tự viết"); loadBaoSkill(); }catch(err){ toast(err.message); } }; }
$("#bPrev").onclick=async e=>{ e.target.disabled=true; try{ await api("/settings","PUT",bumpPayload()); const r=await api("/bump/preview-text?n=3"); const o=$("#bPrevOut"); o.hidden=false; loadBaoSkill(); o.innerHTML=r.texts.map(t=>`<li>${esc(t)}</li>`).join("")+(r.mode==="ai"&&!r.ai?'<li class="muted" style="list-style:none;margin-left:-18px">Chưa có khóa Claude: Bảo tự viết từ những câu đã học (chưa học thì dùng mẫu có sẵn). Nhập khóa ở Cài đặt để Bảo học từ Claude.</li>':""); }catch(err){ toast(err.message); } e.target.disabled=false; };
$("#bCheck").onclick=async()=>{ await api("/settings","PUT",{bump_folder:$("#bFolder").value.trim()}); showFolder(await api("/bump/folder")); };
$("#bumpForm").addEventListener("submit",async e=>{ e.preventDefault(); await api("/settings","PUT",bumpPayload()); toast("Đã lưu cài đặt up bài"); showFolder(await api("/bump/folder")); });
$("#bNow").onclick=async e=>{ e.target.disabled=true; await api("/settings","PUT",bumpPayload()); try{ const r=await api("/bump/plan-now","POST"); toast(r.scheduled?`Đã xếp ${r.scheduled} lượt bình luận, sale bắt đầu trong vài phút`:"Không có bài nào cần bình luận (bài quá cũ, vừa đăng, đã bình luận hôm nay, hoặc thư mục ảnh trống)"); }catch(err){ toast(err.message); } e.target.disabled=false; if(ST.view==="comments") loadCm(true); };
function showAi(s){
  const live=s.ai_live, src=s.ai_key_source;
  $("#aiState").className="chip "+(live?"ok":"warn"); $("#aiState").textContent=live?"Đang dùng Claude":"Chế độ mô phỏng";
  $("#aiBox").innerHTML = DEMO ? "Bản xem trước không gọi Claude thật. Khi chạy phần mềm trên máy bạn, dán khóa vào đây là cả đội dùng Claude ngay."
    : live ? `Khóa đang dùng: <b>${esc(s.ai_key_masked)}</b> ${src==="env"?"(từ file .env)":"(nhập trong phần mềm)"}. Mô hình theo từng việc chỉnh ở mục <b>Chi phí AI</b> phía trên.`
    : "Chưa có khóa API. Các agent đang dùng nội dung mẫu, chưa tốn tiền.";
  $("#aiDel").hidden=!(live&&src==="app"); $("#aiTest").hidden=!live;
  const mb=$("#modeBox"); if(!DEMO) mb.innerHTML = live?`<span class="dot live"></span><b>AI đang hoạt động</b><br>Khóa ${esc(s.ai_key_masked)}`:`<span class="dot sim"></span><b>Chế độ mô phỏng</b><br><a href="#setup">Nhập khóa API Claude</a>`;
}
$("#aiShow").onclick=()=>{ const i=$("#aiKey"); i.type=i.type==="password"?"text":"password"; $("#aiShow").textContent=i.type==="password"?"Hiện":"Ẩn"; };
$("#aiForm").addEventListener("submit",async e=>{ e.preventDefault(); const k=$("#aiKey").value.trim();
  if(!k){ toast("Dán khóa API vào ô trước"); return; }
  if(!k.startsWith("sk-ant-")){ toast("Khóa Claude bắt đầu bằng sk-ant-. Kiểm tra lại khóa vừa dán."); return; }
  const b=$("#aiSave"); b.disabled=true; b.textContent="Đang kiểm tra với Anthropic…";
  try{ const r=await api("/ai-key","POST",{key:k}); $("#aiKey").value=""; toast(r.warning||"Khóa hợp lệ. Cả đội đã chuyển sang dùng Claude."); }
  catch(err){ toast(err.message); }
  b.disabled=false; b.textContent="Kiểm tra và lưu"; showAi(await api("/settings")); loadCosts(); });
$("#aiTest").onclick=async e=>{ e.target.disabled=true; try{ const r=await api("/ai-key/test","POST"); toast(r.warning||"Khóa đang hoạt động tốt"); }catch(err){ toast(err.message); } e.target.disabled=false; };
$("#aiDel").onclick=async e=>{ const b=e.target; if(b.dataset.confirm!=="1"){ b.dataset.confirm="1"; b.textContent="Bấm lần nữa để xóa"; return; } b.dataset.confirm=""; b.textContent="Xóa khóa";
  const r=await api("/ai-key","DELETE"); toast(r.live?"Đã xóa khóa trong phần mềm, đang dùng khóa từ file .env":"Đã xóa khóa. Các agent chuyển về nội dung mẫu."); showAi(await api("/settings")); };
function showTgSet(t){
  const st=!t.has_token?["warn","Chưa có token"]:t.error?["bad","Lỗi kết nối"]:t.chats?["ok","Đã kết nối"]:["warn","Chờ ghép nối"];
  $("#tgsState").className="chip "+st[0]; $("#tgsState").textContent=st[1];
  $("#tgsBox").innerHTML = !t.has_token ? "Chưa có bot Telegram. Làm theo 3 bước dưới để sếp nhận báo cáo trên điện thoại."
    : t.error ? `<span class="err">${esc(t.error)}</span>`
    : `Bot <b>@${esc(t.bot||"?")}</b> · token <b>${esc(t.token_masked||"••••••")}</b> · ${t.chats?`đang gửi báo cáo tới ${t.chats} chat`:"chưa ghép nối chat nào, bấm Tạo mã ghép nối"}.`;
  $("#tgsPairBox").innerHTML = t.pair_code&&!t.chats ? `<div class="note">Mở <b>@${esc(t.bot||"bot của bạn")}</b> trên Telegram và gửi mã:<div class="tg-code" style="margin-top:6px">${esc(t.pair_code)}</div></div>` : "";
  $("#tgsDone").checked = t.report_done!==false;
  $("#tgsPair").hidden=!t.has_token; $("#tgsTest").hidden=!t.chats; $("#tgsDel").hidden=!t.has_token;
}
let tgsPoll=null;
const loadTgSet=async()=>{ const t=await api("/telegram"); showTgSet(t); return t; };
$("#tgsShow").onclick=()=>{ const i=$("#tgsToken"); i.type=i.type==="password"?"text":"password"; $("#tgsShow").textContent=i.type==="password"?"Hiện":"Ẩn"; };
$("#tgSetForm").addEventListener("submit",async e=>{ e.preventDefault(); const k=$("#tgsToken").value.trim();
  if(!k){ toast("Dán token bot Telegram vào ô trước"); return; }
  const b=$("#tgsSave"); b.disabled=true; b.textContent="Đang kiểm tra với Telegram…";
  try{ const t=await api("/telegram/token","POST",{token:k}); $("#tgsToken").value=""; showTgSet(t); toast(t.chats?`Đã lưu token bot @${t.bot}`:`Token đúng: bot @${t.bot}. Bấm Tạo mã ghép nối để nhận báo cáo.`); }
  catch(err){ toast(err.message); }
  b.disabled=false; b.textContent="Kiểm tra và lưu"; });
$("#tgsPair").onclick=async()=>{ try{ showTgSet(await api("/telegram/pair","POST")); toast("Gửi mã này cho bot trên Telegram");
    clearInterval(tgsPoll); let n=0; tgsPoll=setInterval(async()=>{ n++; const t=await loadTgSet().catch(()=>null); if((t&&t.chats)||n>40){ clearInterval(tgsPoll); if(t&&t.chats) toast("Đã ghép nối Telegram. Từ giờ việc xong sẽ báo về đây."); } },3000);
  }catch(err){ toast(err.message); } };
$("#tgsTest").onclick=async()=>{ try{ await api("/telegram/send","POST",{kind:"test"}); toast("Đã gửi tin thử. Kiểm tra Telegram."); }catch(err){ toast(err.message); } };
$("#tgsDone").onchange=async e=>{ showTgSet(await api("/telegram/report","PUT",{report_done:e.target.checked})); toast(e.target.checked?"Mọi việc xong sẽ được báo qua Telegram":"Đã tắt báo việc xong (báo cáo sáng/tối vẫn gửi)"); };
$("#tgsDel").onclick=async e=>{ const b=e.target; if(b.dataset.confirm!=="1"){ b.dataset.confirm="1"; b.textContent="Bấm lần nữa để xóa"; return; } b.dataset.confirm=""; b.textContent="Xóa token";
  showTgSet(await api("/telegram/token","DELETE")); toast("Đã xóa token. Phần mềm ngừng gửi Telegram."); };
const SAMPLE_NAME={sales:"sale",leads:"khách",groups:"hội nhóm",products:"sản phẩm"};
async function loadSamples(){
  const c=await api("/sample-data"); const parts=Object.entries(c).filter(([k,v])=>v).map(([k,v])=>`${v} ${SAMPLE_NAME[k]}`);
  $("#sampleCard").hidden=!parts.length; $("#sampleChip").textContent=parts.length?"Còn dữ liệu mẫu":""; $("#sampleTxt").textContent=parts.length?`Đang có ${parts.join(", ")} mẫu do phần mềm tạo sẵn để bạn xem thử.`:"";
}
$("#sampleDel").onclick=async e=>{ const b=e.target; if(b.dataset.confirm!=="1"){ b.dataset.confirm="1"; b.textContent="Bấm lần nữa để xóa vĩnh viễn"; return; }
  b.dataset.confirm=""; b.textContent="Xóa toàn bộ dữ liệu mẫu"; await api("/sample-data","DELETE"); toast("Đã xóa dữ liệu mẫu"); loadSamples(); refresh(); };
async function loadReset(){
  const r=await api("/reset"); const total=r.delete.reduce((a,x)=>a+x.count,0);
  $("#resetChip").className="chip "+(total?"warn":"ok"); $("#resetChip").textContent=total?"Còn dữ liệu thử nghiệm":"Sạch, sẵn sàng chạy thật";
  $("#resetPreview").innerHTML=(total?`<b>Sẽ xóa:</b><ul class="reset-list">${r.delete.map(x=>`<li>${x.count} ${esc(x.label)}</li>`).join("")}${r.shots?`<li>${r.shots} ảnh chụp màn hình</li>`:""}${r.samples.products?`<li>${r.samples.products} sản phẩm mẫu</li>`:""}${r.samples.groups?`<li>${r.samples.groups} hội nhóm mẫu</li>`:""}${r.samples.sales?`<li>${r.samples.sales} sale mẫu</li>`:""}</ul>`:"Không còn dữ liệu thử nghiệm.")
    +`<br><b>Giữ nguyên:</b> ${r.keep.sales} nhân viên sale (cả phiên đăng nhập Facebook), ${r.keep.products} sản phẩm và ${r.keep.groups} hội nhóm bạn đã nhập, khóa API, Telegram, KPI, thư mục ảnh, chi phí AI đã tiêu.`;
}
$("#rsConfirm").addEventListener("input",e=>{ $("#rsBtn").disabled=e.target.value.trim().toUpperCase()!=="CHAY THAT"; });
$("#resetForm").addEventListener("submit",async e=>{ e.preventDefault(); const b=$("#rsBtn"); b.disabled=true; b.textContent="Đang sao lưu và xóa…";
  try{ const r=await api("/reset","POST",{confirm:$("#rsConfirm").value,products:$("#rsProd").checked,groups:$("#rsGroup").checked,found_capital:$("#rsFound").checked?(parseVnd($("#rsCap").value)||0):0});
    toast("Đã xóa dữ liệu thử nghiệm. Đội sẵn sàng làm việc thật."); $("#rsConfirm").value=""; $("#rsProd").checked=false; $("#rsGroup").checked=false;
    if(r.backup) $("#resetPreview").insertAdjacentHTML("beforeend",`<br><span class="small">Bản sao lưu: ${esc(r.backup)}</span>`); }
  catch(err){ toast(err.message); }
  b.textContent="Xóa dữ liệu thử nghiệm"; ST.posts=[]; ST.leads=[]; ST.meetingId=null; ST.msgs=[]; setTimeout(loadReset,300); loadSamples(); refresh(); });
function showHk(h){ const z=h.sizes||{}, tot=(z.db_mb||0)+(z.shots_mb||0)+(z.backups_mb||0)+(z.profiles_mb||0), L=h.last;
  const mb=v=>v>=1024?(v/1024).toFixed(1)+" GB":(v||0)+" MB";
  $("#hkChip").className="chip "+(tot>8192?"warn":"ok"); $("#hkChip").textContent="Tổng "+mb(Math.round(tot*10)/10);
  $("#hkGrid").innerHTML=[["Cơ sở dữ liệu",z.db_mb],["Ảnh chụp màn hình",z.shots_mb,`${z.shots||0} ảnh`],["Bản sao lưu",z.backups_mb],["Hồ sơ Chrome các nick",z.profiles_mb]]
    .map(([k,v,n])=>`<div class="hk-i"><span class="small muted">${k}</span><b>${mb(v)}</b>${n?`<span class="small muted">${n}</span>`:""}</div>`).join("")
    +((z.tables||[]).length?`<div class="hk-t small muted">Bảng lớn nhất: ${z.tables.map(t=>`${esc(t.name)} ${mb(t.mb)}`).join(" · ")}</div>`:"");
  $("#hkLast").textContent=L?`Lần dọn gần nhất ${fmtDate(L.at)} ${String(L.at).slice(11,16)}: xóa ${Object.values(L.rows||{}).reduce((a,b)=>a+b,0)} dòng nhật ký cũ, ${(L.shots||{}).files||0} ảnh chụp, giải phóng ${L.freed_mb??0} MB.${L.later?" "+L.later+".":""}`:"Chưa dọn lần nào.";
}
async function loadHk(){ try{ showHk(await api("/housekeeping")); }catch(e){} }
$("#hkRun").onclick=async e=>{ const b=e.target; b.disabled=true; b.textContent="Đang dọn…";
  try{ const r=await api("/housekeeping","POST"); showHk(r); toast(r.text); }catch(err){ toast(err.message); } b.disabled=false; b.textContent="Dọn ngay"; };
async function loadSettings(){
  loadReset(); loadHk();
  loadSamples();
  loadCosts(); loadTeam();
  const s=await api("/settings");
  $("#sName").value=s.company_name||""; $("#sVoice").value=s.brand_voice||""; $("#sContact").value=s.contact_info||""; $("#sZalo").value=s.price_zalo||"0386992326"; $("#sPriceLine").value=s.price_contact||""; ST.zalo=s.price_zalo||"0386992326"; $("#sTime").value=s.meeting_time||"08:30";
  $("#sPer").value=s.posts_per_day||4; $("#sAutoM").checked=s.auto_meeting==="1"; $("#sAutoW").checked=s.auto_daily_work==="1"; $("#sPage").value=s.fb_page_id||""; $("#sToken").value=s.fb_page_token||""; loadBump(s); $("#sImgReq").checked=s.require_images!=="0"; $("#sGroupFit").checked=s.group_fit!=="0"; $("#sImg").checked=s.attach_images!=="0"||$("#sImgReq").checked; $("#sImg").disabled=$("#sImgReq").checked; $("#sImgMin").value=s.images_min||2; $("#sImgMax").value=s.images_max||4; $("#sImgDays").value=s.image_reuse_days||14; { const bm=s.browser_headless==="1"?"headless":(s.browser_mode||"background"); const r=document.querySelector(`input[name=sBrowser][value=${bm}]`); if(r) r.checked=true; }
  showAi(s);
  loadTgSet().catch(()=>{});
  try{ const h=await api("/health"); setTz(h.time); const t=h.time||{};
    $("#sTz").innerHTML=(TZ.choices||TZ_LIST).map(x=>`<option value="${x.id}" ${x.id===(s.app_tz||TZ.name)?"selected":""}>${esc(x.label)}</option>`).join("");
    const diff=t.pc_now&&t.now?Math.abs(new Date(t.pc_now.replace(" ","T"))-new Date(t.now.replace(" ","T")))/6e4:0;
    $("#sTzNote").innerHTML=`Giờ trên phần mềm lúc này: <b>${esc((t.now||tzNow()).slice(11,16))} ${esc(fmtDate(t.now||tzNow()))}</b> (${esc(t.label||TZ.label)}).`+(diff>=30?` Máy tính đang đặt múi giờ khác (máy báo ${esc(t.pc_now.slice(11,16))}); phần mềm vẫn chạy theo múi giờ đã chọn ở đây, không cần sửa máy.`:""); }catch(e){}
}
$("#sImgReq").onchange=e=>{ if(e.target.checked) $("#sImg").checked=true; $("#sImg").disabled=e.target.checked; };
$("#setForm").addEventListener("submit",async e=>{ e.preventDefault(); await api("/settings","PUT",{app_tz:$("#sTz").value,company_name:$("#sName").value,brand_voice:$("#sVoice").value,contact_info:$("#sContact").value,price_zalo:$("#sZalo").value.replace(/[^\d+]/g,"")||"0386992326",price_contact:$("#sPriceLine").value.trim(),meeting_time:$("#sTime").value,posts_per_day:$("#sPer").value,auto_meeting:$("#sAutoM").checked?"1":"0",auto_daily_work:$("#sAutoW").checked?"1":"0",fb_page_id:$("#sPage").value,fb_page_token:$("#sToken").value,attach_images:$("#sImg").checked||$("#sImgReq").checked?"1":"0",require_images:$("#sImgReq").checked?"1":"0",group_fit:$("#sGroupFit").checked?"1":"0",images_min:$("#sImgMin").value,images_max:String(Math.max(+$("#sImgMax").value||1,+$("#sImgMin").value||1)),image_reuse_days:$("#sImgDays").value,browser_mode:(document.querySelector("input[name=sBrowser]:checked")||{}).value||"background",browser_headless:(document.querySelector("input[name=sBrowser]:checked")||{}).value==="headless"?"1":"0"}); $("#coName").textContent=$("#sName").value; toast("Đã lưu cài đặt"); loadSettings(); });

/* Phát hiện phần mềm trên máy đang chạy bản cũ, chưa khởi động lại sau khi cập nhật, hoặc chạy 2 bản cùng lúc */
const HEALTH={pids:{},bad:""};
function staleBanner(msg){ const b=$("#staleBanner"); if(!b) return; b.hidden=!msg; if(msg) b.innerHTML=msg; HEALTH.bad=msg; }
function checkHealth(h){
  if(h&&h.time) setTz(h.time);
  if(DEMO||!h) return; const now=Date.now();
  if(h.pid) HEALTH.pids[h.pid]=now; else HEALTH.pids["cu"]=now;
  const recent=Object.entries(HEALTH.pids).filter(([,t])=>now-t<180000).map(([p])=>p);
  if(recent.length>1||!h.build) staleBanner(`<b>Đang có 2 phần mềm chạy cùng lúc${!h.build?" (một bản cũ)":""}.</b> Hai bản giành nhau việc nên sẽ lỗi: Chrome của sale tự đóng, mục Lỗi không hoạt động. Đóng <b>tất cả</b> cửa sổ đen run.bat (hoặc Task Manager → tắt python.exe), rồi chạy lại run.bat <b>một lần</b>.`);
  else if(h.restarting) staleBanner(`<b>Đang khởi động lại phần mềm với bản mới…</b> Trang sẽ tự tải lại khi xong (khoảng 10–60 giây).`);
  else if(h.stale) staleBanner(`<b>Đã có bản mới trên máy.</b> Phần mềm sẽ tự khởi động lại khi các sale làm xong việc đang dở${h.idle?"":" (đang có việc chạy)"}. <button type="button" class="btn sm" id="btnRestart" style="margin-left:6px">Khởi động lại ngay</button>`);
  else staleBanner("");
  // phần mềm đã chạy bản mới (khởi động lại xong): tải lại trang để dùng giao diện mới
  if(h.build){ if(!HEALTH.build0) HEALTH.build0=h.build;
    else if(h.build!==HEALTH.build0){ HEALTH.newSeen=(HEALTH.newSeen||0)+1; if(HEALTH.newSeen>=2) location.reload(); } }
}
document.addEventListener("click",async e=>{ if(!e.target.closest("#btnRestart")) return;
  const b=e.target.closest("#btnRestart"); b.disabled=true; b.textContent="Đang khởi động lại…";
  try{ await api("/admin/restart","POST"); }catch(err){ toast(err.message); b.disabled=false; b.textContent="Khởi động lại ngay"; return; }
  [3000,6000,10000,15000,20000,30000,45000,60000].forEach(t=>setTimeout(pollHealth,t)); });
async function pollHealth(){ try{ const r=await fetch("/api/health",{cache:"no-store"}); if(r.ok) checkHealth(await r.json()); }catch(e){} }

