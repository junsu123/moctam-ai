/* --------------------------------------------- phong cách viết của Lan */
const ST_SRC={claude:["","Claude viết"],self:["ok","Lan tự viết"],boss:["talking","Sếp sửa"]};
function ZALO(){ try{ return ST.zalo||"0386992326"; }catch(e){ return "0386992326"; } }
const tplShow=t=>esc(t).replace(/\{name\}/g,"<i>[tên SP]</i>").replace(/\{wp\}/g,"<i>[giá sỉ]</i>").replace(/\{rp\}/g,"<i>[giá lẻ]</i>").replace(/\{moq\}/g,"<i>[nhập tối thiểu]</i>").replace(/\{cat\}/g,"<i>[dòng SP]</i>").replace(/\{contact\}/g,"<i>[liên hệ]</i>");
async function loadStyle(){
  let d; try{ d=await api("/content-style"); }catch(e){ return; }
  const lib=d.counts.library||{}, sn=d.counts.snippets||{}; const learned=(lib.claude||0)+(lib.boss||0);
  $("#stState").className="chip "+(d.ready?"ok":"warn"); $("#stState").textContent=d.ready?"Đã tự viết được":"Đang học";
  $("#stStats").innerHTML=[[lib.claude||0,"Bài Claude viết đã lưu"],[lib.boss||0,"Bài sếp sửa đã học"],[lib.self||0,"Bài Lan tự viết"],[(sn.hook||0)+(sn.cta||0)+(sn.point||0)+(sn.price||0)+(sn.service||0)+(sn.story||0),"Câu chữ đã học"],[Math.round((d.share||0)*100)+"%","Tỉ lệ tự viết lúc này"]].map(([v,l])=>`<div><b>${typeof v==="number"?num(v):v}</b><span>${l}</span></div>`).join("");
  $("#stReadyTxt").textContent=d.ready_text; $("#stShareTxt").textContent=d.mode==="off"?"Đang tắt tự viết":d.mode==="always"?"Luôn tự viết":"Tự động";
  $("#stBar").style.width=Math.min(100,learned/d.min*100)+"%";
  const pr=d.profile||{};
  $("#stProfile").innerHTML=pr.posts?[`Độ dài khoảng <b>${pr.avg_words} chữ</b>, ${pr.avg_lines} dòng`,`Emoji hay dùng: ${(pr.top_emoji||[]).slice(0,6).join(" ")} (${String(pr.emoji_per_post).replace(".",",")}/bài)`,pr.bullet_share>=50?`Gạch đầu dòng: ${pr.bullet_share}% số bài`:"Ít dùng gạch đầu dòng",`Hashtag: ${esc((pr.top_tags||[]).slice(0,5).join(" "))}`].map(x=>`<li>${x}</li>`).join(""):'<li class="muted">Chưa có bài Claude viết nào được lưu.</li>';
  const q=d.quality||{}; const qr=(x,l)=>x&&x.judged?`<li><b>${l}</b>: sếp/CEO duyệt ${x.approve_rate}% (${x.judged} bài đã xét), TB ${String(x.leads_avg).replace(".",",")} khách/bài${x.edited?`, ${x.edited} bài bị sửa`:""}</li>`:`<li class="muted">${l}: chưa có bài được xét</li>`;
  $("#stQuality").innerHTML=qr(q.claude,"Claude viết")+qr(q.self,"Lan tự viết");
  const sl=a=>a.length?a.map(x=>`<li>${tplShow(x.text)} <span class="muted">· ${String(x.score).replace(".",",")} điểm${x.uses?` · dùng ${x.uses} lần`:""}</span></li>`).join(""):'<li class="muted">Chưa có</li>';
  $("#stHooks").innerHTML=sl(d.top.hook||[]); $("#stCtas").innerHTML=sl(d.top.cta||[]);
  if(document.activeElement!==$("#stMode")) $("#stMode").value=d.mode;
  if(!$("#stProd").options.length){ const ps=ST.products||await api("/products"); $("#stProd").innerHTML='<option value="">Sản phẩm bất kỳ</option>'+ps.map(p=>`<option value="${p.id}">${esc(p.name)}</option>`).join(""); }
  $("#stTry").disabled=!d.ready; $("#stTry").title=d.ready?"Xem Lan tự viết thế nào (không lưu, không gọi Claude)":d.ready_text;
  $("#stLib").innerHTML=d.recent.length?d.recent.map(r=>{ const [c,t]=ST_SRC[r.source]||["",r.source]; return `<li><div><b>${esc(r.title||"(không tiêu đề)")}</b><div class="meta"><span class="chip ${c}">${t}</span><span class="chip">${esc(r.product_name||"")}</span>${r.status&&r.status!=="draft"?`<span class="chip ${r.status==="rejected"?"bad":"ok"}">${r.status==="rejected"?"Bị loại":"Được duyệt"}</span>`:""}${r.leads?`<span class="chip ok">${r.leads} khách</span>`:""}<span class="small muted">${fmtDate(r.created_at)}</span></div><div class="small" style="white-space:pre-wrap">${esc(r.content)}${r.content.length>=400?"…":""}</div></div></li>`; }).join(""):'<li class="muted small">Kho trống.</li>';
}
$("#stMode").onchange=async e=>{ await api("/content-style","PUT",{mode:e.target.value}); toast({auto:"Tự động: Lan tự viết tăng dần theo số bài đã học",always:"Lan luôn tự viết khi đủ vốn",off:"Đã tắt tự viết, Lan nhờ Claude viết mọi bài"}[e.target.value]); loadStyle(); };
$("#stTry").onclick=async()=>{ const b=$("#stTry"); b.disabled=true; try{ const r=await api("/content-style/preview","POST",{product_id:+$("#stProd").value||null,target:"group"});
    $("#stPreview").innerHTML=`<div class="st-post"><span class="chip ok">Lan tự viết · ${esc(r.product)} · ${esc(r.angle)} · không gọi Claude</span>

${esc(r.content)}

${esc(r.hashtags)}</div>`; }
  catch(err){ toast(err.message); } b.disabled=false; };

