/* =========================================================== tiện ích */
const $ = (s, el = document) => el.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const TZ_LIST=[{id:"Asia/Ho_Chi_Minh",label:"Việt Nam (GMT+7)"},{id:"Asia/Bangkok",label:"Thái Lan, Lào, Campuchia (GMT+7)"},{id:"Asia/Singapore",label:"Singapore, Malaysia (GMT+8)"},{id:"Asia/Shanghai",label:"Trung Quốc, Đài Loan (GMT+8)"},{id:"Asia/Seoul",label:"Hàn Quốc (GMT+9)"},{id:"Asia/Tokyo",label:"Nhật Bản (GMT+9)"},{id:"Australia/Sydney",label:"Sydney (GMT+10/+11)"},{id:"Europe/London",label:"Anh (GMT+0/+1)"},{id:"Europe/Berlin",label:"Đức, Pháp (GMT+1/+2)"},{id:"America/New_York",label:"New York (GMT-5/-4)"},{id:"America/Los_Angeles",label:"California (GMT-8/-7)"},{id:"UTC",label:"UTC (GMT+0)"}];
const TZ={name:"Asia/Ho_Chi_Minh",label:"Việt Nam (GMT+7)",choices:TZ_LIST};
/* giờ hiện tại theo múi giờ của phần mềm (mặc định giờ Việt Nam), dạng "YYYY-MM-DD HH:MM:SS" */
const tzNow=(z=TZ.name)=>{ try{ const p=Object.fromEntries(new Intl.DateTimeFormat("en-GB",{timeZone:z,year:"numeric",month:"2-digit",day:"2-digit",hour:"2-digit",minute:"2-digit",second:"2-digit",hourCycle:"h23"}).formatToParts(new Date()).map(x=>[x.type,x.value]));
  return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}:${p.second}`; }catch(e){ return new Date().toISOString().replace("T"," ").slice(0,19); } };
const setTz=t=>{ if(t&&t.tz){ TZ.name=t.tz; TZ.label=t.label||t.tz; if(t.choices) TZ.choices=t.choices; } };
const fmtTime = s => s ? s.slice(11, 16) : "";
const fmtDate = s => s ? `${s.slice(8,10)}/${s.slice(5,7)}` : "—";
function toast(t){ const el=$("#toast"); const isErr=Date.now()-(ERR.lastAt||0)<2500&&ST.view!=="errors";
  el.textContent=t; if(isErr){ const a=document.createElement("a"); a.href="#errors"; a.textContent="Xem lỗi"; el.appendChild(a); }
  el.hidden=false; clearTimeout(toast._t); toast._t=setTimeout(()=>el.hidden=true,isErr?6000:2600); }
async function copyText(t){ try{ await navigator.clipboard.writeText(t); toast("Đã sao chép nội dung"); }catch(e){ toast("Không sao chép được, hãy bôi đen và sao chép thủ công"); } }
const STATUS_TXT = {idle:"Rảnh", working:"Đang làm", meeting:"Đang họp", talking:"Đang nói", learning:"Đang học"};
const LOST_R = {no_answer:"Không nghe máy / sai số",wrong_fit:"Sai tệp (không bán online, chỉ mua lẻ)",has_supplier:"Đã có nguồn hàng",moq:"Chê số lượng nhập tối thiểu",price:"Chê giá",product:"Không hợp sản phẩm",later:"Hẹn để sau",other:"Lý do khác"};
const LEAD_ST = {new:"Mới", contacted:"Đã liên hệ", sample:"Đã gửi mẫu", ordered:"Đã nhập hàng", lost:"Không mua"};
const PHASE = {open:"Mở đầu", report:"Báo cáo", debate:"Tranh luận", close:"Chốt", boss:"Sếp"};
const TARGET = {group:"Hội nhóm", profile:"Trang cá nhân", page:"Fanpage"};

