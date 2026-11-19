/* =========================================================== 3D: văn phòng hoạt hình */
const World = (() => {
  const stage=$("#stage"), canvas=$("#cv"), overlay=$("#overlay");
  const renderer=new THREE.WebGLRenderer({canvas,antialias:true});
  renderer.setPixelRatio(Math.min(Math.max(devicePixelRatio,1.25),2)); // vẽ dày điểm ảnh hơn cho nét sắc renderer.shadowMap.enabled=true; renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.outputEncoding = THREE.sRGBEncoding;
  const scene=new THREE.Scene();
  const camera=new THREE.PerspectiveCamera(38,1,0.1,200);
  const controls=new THREE.OrbitControls(camera,canvas);
  controls.enableDamping=true; controls.maxPolarAngle=Math.PI*0.44; controls.minDistance=6; controls.maxDistance=46; controls.enablePan=false;
  const VIEWS={office:{pos:[-2.5,28,33],tgt:[-1.5,0.5,4.5]},meeting:{pos:[7.4,9,11.5],tgt:[7.4,0.9,-0.4]}};
  let camGoal=null;
  function setCam(v){ camGoal={pos:new THREE.Vector3(...VIEWS[v].pos),tgt:new THREE.Vector3(...VIEWS[v].tgt)}; }
  camera.position.set(...VIEWS.office.pos); controls.target.set(...VIEWS.office.tgt); controls.maxDistance=46;
  controls.addEventListener("start",()=>camGoal=null);

  function applyTheme(){ const c=getComputedStyle(document.documentElement).getPropertyValue("--stage").trim()||"#dbe5d3"; scene.background=new THREE.Color(c); scene.fog=new THREE.Fog(c,30,60); }
  applyTheme(); matchMedia("(prefers-color-scheme: dark)").addEventListener("change",applyTheme);
  new MutationObserver(applyTheme).observe(document.documentElement,{attributes:true,attributeFilter:["data-theme"]});

  // ánh sáng
  scene.add(new THREE.HemisphereLight(0xffffff,0x9aa48f,0.75));
  const sun=new THREE.DirectionalLight(0xfff3dc,0.85); sun.position.set(-6,16,10); sun.castShadow=true;
  sun.shadow.mapSize.set(2048,2048); Object.assign(sun.shadow.camera,{left:-16,right:16,top:12,bottom:-12,near:1,far:50}); sun.shadow.bias=-0.0005; scene.add(sun);
  const rim=new THREE.DirectionalLight(0xd6ecff,0.35); rim.position.set(8,10,-14); scene.add(rim); // đèn ngược tạo viền sáng cho nhân vật nổi khối

  // vật liệu kiểu hoạt hình
  const grad=(()=>{const t=new THREE.DataTexture(new Uint8Array([95,160,215,255]),4,1,THREE.LuminanceFormat); t.minFilter=t.magFilter=THREE.NearestFilter; t.needsUpdate=true; return t;})();
  const mats={}; const toon=c=>mats[c]||(mats[c]=new THREE.MeshToonMaterial({color:new THREE.Color(c).convertSRGBToLinear(),gradientMap:grad}));
  const lineMat=new THREE.MeshBasicMaterial({color:0x1b2620,side:THREE.BackSide});
  const outline=(m,s=1.07)=>{const o=new THREE.Mesh(m.geometry,lineMat); o.scale.setScalar(s); m.add(o); return m;};
  function mesh(geo,color,{x=0,y=0,z=0,shadow=true,parent}={}){ const m=new THREE.Mesh(geo,toon(color)); m.position.set(x,y,z); m.castShadow=shadow; m.receiveShadow=true; (parent||scene).add(m); return m; }
  const box=(w,h,d)=>new THREE.BoxGeometry(w,h,d);
  function textTex(lines,{w=512,h=256,bg="#ffffff",fg="#1b2620",font="700 44px 'Baloo 2', sans-serif",sub="500 26px 'Be Vietnam Pro', sans-serif"}={}){
    const c=document.createElement("canvas"); c.width=w; c.height=h; const g=c.getContext("2d");
    g.fillStyle=bg; g.fillRect(0,0,w,h); g.fillStyle=fg; g.textAlign="center"; g.textBaseline="middle";
    g.font=font; g.fillText(lines[0],w/2,h*0.33);
    if(lines[1]){ g.font=sub; wrap(g,lines[1],w/2,h*0.62,w-50,32); }
    const t=new THREE.CanvasTexture(c); t.encoding=THREE.sRGBEncoding; return t;
  }
  function wrap(g,text,x,y,maxW,lh){ const words=text.split(" "); let line="",lines=[]; for(const w of words){ const tl=line?line+" "+w:w; if(g.measureText(tl).width>maxW&&line){lines.push(line);line=w;}else line=tl; } lines.push(line); lines=lines.slice(0,3); lines.forEach((l,i)=>g.fillText(l,x,y+(i-(lines.length-1)/2)*lh)); }

  // sàn, tường
  mesh(box(26,0.3,25),"#c9a679",{y:-0.15,z:4.5});
  for(let i=-12;i<=12;i+=2){ mesh(box(0.04,0.01,25),"#b8946a",{x:i,y:0.005,z:4.5,shadow:false}); }
  mesh(box(9,0.02,10),"#9fc4a7",{x:7.2,y:0.01,shadow:false}); // thảm phòng họp
  mesh(box(26,4,0.3),"#e9e4d6",{y:2,z:-8}); mesh(box(0.3,4,25),"#e3ddcd",{x:-13,y:2,z:4.5});
  // cửa sổ
  for(const x of [-9,-4,1]){ mesh(box(3,1.8,0.1),"#a8d4e8",{x,y:2.3,z:-7.82,shadow:false}); mesh(box(3.2,0.12,0.2),"#f7f3e8",{x,y:1.35,z:-7.8}); }
  // biển công ty
  const signMat=new THREE.MeshBasicMaterial({map:textTex(["Phòng Kinh doanh","Trà túi lọc · Bột ngũ cốc · Bột thiên nhiên · Cà phê"],{bg:"#2f5d3a",fg:"#f6efd8",w:768,h:192})});
  const sign=new THREE.Mesh(new THREE.PlaneGeometry(5.2,1.3),signMat); sign.position.set(-13+0.17,2.6,-1); sign.rotation.y=Math.PI/2; scene.add(sign);

  // phòng họp kính
  const glass=new THREE.MeshPhysicalMaterial({color:0xcfe9f2,transparent:true,opacity:0.22,roughness:0.1});
  const gw=(w,x,z,ry)=>{ const m=new THREE.Mesh(box(w,2.6,0.06),glass); m.position.set(x,1.3,z); m.rotation.y=ry; scene.add(m); mesh(box(w,0.12,0.12),"#6c7f74",{x,y:2.62,z,parent:scene}).rotation.y=ry; };
  gw(5.6,3,-4.6,Math.PI/2); gw(5.6,3,4.6,Math.PI/2); gw(9.8,7.9,6.5+0.9,0);
  // bảng trắng
  const board=new THREE.Mesh(new THREE.PlaneGeometry(3.6,1.8),new THREE.MeshBasicMaterial({map:textTex(["Họp giao ban","Chưa có chủ đề"])}));
  board.position.set(7.4,2.1,-7.82); scene.add(board); mesh(box(3.8,2,0.08),"#7b8a80",{x:7.4,y:2.1,z:-7.88});
  let boardTopic="";
  function setBoard(topic){ if(topic===boardTopic) return; boardTopic=topic; board.material.map=textTex(["Họp giao ban",topic||"Chưa có chủ đề"]); board.material.needsUpdate=true; }
  document.fonts&&document.fonts.ready.then(()=>{ signMat.map=textTex(["Phòng Kinh doanh","Trà túi lọc · Bột ngũ cốc · Bột thiên nhiên · Cà phê"],{bg:"#2f5d3a",fg:"#f6efd8",w:768,h:192}); signMat.needsUpdate=true; const t=boardTopic; boardTopic=null; setBoard(t); });

  // bàn họp tròn
  const MC=new THREE.Vector3(7.4,0,0);
  mesh(new THREE.CylinderGeometry(1.75,1.75,0.12,40),"#8a5a36",{x:MC.x,y:0.78,z:MC.z});
  mesh(new THREE.CylinderGeometry(0.25,0.4,0.75,16),"#5d3d25",{x:MC.x,y:0.38,z:MC.z});
  // cốc trà trên bàn
  for(let i=0;i<6;i++){ const a=i/6*Math.PI*2+0.3; mesh(new THREE.CylinderGeometry(0.09,0.07,0.16,12),"#f4efe2",{x:MC.x+Math.sin(a)*1.25,y:0.92,z:MC.z+Math.cos(a)*1.25}); }
  let SEATS={}; const seatGroup=new THREE.Group(); scene.add(seatGroup);
  function layoutSeats(ids){ // ghế sếp luôn ở giữa phía trước, các agent xếp vòng quanh bàn
    seatGroup.clear(); SEATS={}; const order=[...ids]; order.splice(Math.floor((ids.length+1)/2),0,"boss");
    const N=order.length, R=Math.min(4.15,Math.max(2.6,N*1.4/(Math.PI*2))); // nhân vật to hơn: ghế giãn ra
    order.forEach((id,i)=>{ const a=Math.PI+i*(Math.PI*2/N); const x=MC.x+Math.sin(a)*R, z=MC.z+Math.cos(a)*R;
      SEATS[id]={x,z,ry:Math.atan2(MC.x-x,MC.z-z)}; seatGroup.add(chair(x,z,SEATS[id].ry,id==="boss"?"#c9962d":"#3d4b44",true)); }); }
  function chair(x,z,ry,color,detached){ const g=new THREE.Group(); g.position.set(x,0,z); g.rotation.y=ry; if(!detached) scene.add(g);
    mesh(box(0.62,0.1,0.6),color,{y:0.47,parent:g}); mesh(box(0.62,0.7,0.1),color,{y:0.85,z:-0.3,parent:g}); mesh(new THREE.CylinderGeometry(0.05,0.05,0.45,8),"#2a2f2c",{y:0.22,parent:g}); return g; }
  // tên ghế sếp
  // khu bàn làm việc
  // 5 bàn của đội lõi + 8 bàn cho nhân viên sale (2 dãy phía trước)
  const DESKS=[[-1.4,-2.8],[-9.4,-2.8],[-5.4,-2.8],[-9.4,2.6],[-5.4,2.6],
    [-11,6.2],[-8,6.2],[-5,6.2],[-2,6.2],[-11,9.6],[-8,9.6],[-5,9.6],[-2,9.6],
    [-1.4,2.6], // 13: bàn CEO (Phòng Giám đốc, cạnh bàn Khoa)
    [0.9,6.2], // 14: bàn Mai (tìm khách sỉ)
    [-1.6,13.4], // 15: bàn Vy (trưởng phòng Website)
    [-9.2,13.4], // 16: bàn Bảo (Phòng Hội nhóm)
    [6.2,13.4], // 17: bàn Nhi (trưởng phòng Trang Facebook)
    [-6.8,13.4],[-4.4,13.4], // 18-19: nhân viên tuyển thêm Phòng Hội nhóm
    [0.8,13.4],[3.2,13.4], // 20-21: nhân viên Phòng Website
    [8.6,13.4],[11,13.4]]; // 22-23: nhân viên Phòng Trang Facebook
  // phòng ban có vách ngăn và cửa: Giám đốc, Kinh doanh (bàn trưởng phòng + chuyên viên), khu Sale, Hội nhóm, Website, Trang Facebook
  Object.assign(DESKS,{0:[-3.8,-6.4],1:[-0.8,-6.4],3:[-3.8,-3.6],14:[-0.8,-3.6],4:[-8,-4.6],13:[-10.6,-4.6],2:[-11.6,13.4]});
  const ROOMS=[
    {k:"gd",name:"Phòng Giám đốc",x0:-13,x1:-6.3,z0:-8,z1:-1.6,door:["s",-9.4],node:"A",rug:"#efe1b5",walls:"es"},
    {k:"kd",name:"Phòng Kinh doanh",x0:-6.3,x1:2.95,z0:-8,z1:-1.6,door:["s",-2.3],node:"B",rug:"#cfe0cf",walls:"s"},
    {k:"sale",name:"Phòng Kinh doanh · Sale",x0:-13,x1:-0.4,z0:4.8,z1:11.4,door:["e",8],node:"E",rug:"#e3ecd9",walls:"nes"},
    {k:"hn",name:"Phòng Hội nhóm",x0:-13,x1:-3.1,z0:12.6,z1:17,door:["n",-8],node:"G",rug:"#f6d7b6",walls:"ne"},
    {k:"web",name:"Phòng Website",x0:-3.1,x1:4.7,z0:12.6,z1:17,door:["n",0.8],node:"H",rug:"#cfdcf6",walls:"ne"},
    {k:"tf",name:"Phòng Trang Facebook",x0:4.7,x1:13,z0:12.6,z1:17,door:["n",8.8],node:"I",rug:"#f6d0e3",walls:"n"}];
  const partGlass=new THREE.MeshPhysicalMaterial({color:0xdfeee6,transparent:true,opacity:0.28,roughness:0.15});
  function wallRun(x0,z0,x1,z1){ const len=Math.hypot(x1-x0,z1-z0); if(len<0.05) return; const g=new THREE.Group(); g.position.set((x0+x1)/2,0,(z0+z1)/2); g.rotation.y=-Math.atan2(z1-z0,x1-x0); scene.add(g);
    const pane=new THREE.Mesh(box(len,1.9,0.05),partGlass); pane.position.y=1.2; g.add(pane);
    mesh(box(len,0.25,0.1),"#a7835c",{parent:g,y:0.125}); mesh(box(len,0.07,0.08),"#6c7f74",{parent:g,y:2.18,shadow:false}); }
  function doorFrame(x,z,alongX){ const g=new THREE.Group(); g.position.set(x,0,z); if(!alongX) g.rotation.y=Math.PI/2; scene.add(g);
    for(const dx of [-0.82,0.82]) mesh(box(0.1,2.2,0.12),"#6c4f33",{parent:g,x:dx,y:1.1});
    mesh(box(1.74,0.12,0.12),"#6c4f33",{parent:g,y:2.2}); const leaf=new THREE.Group(); leaf.position.set(-0.78,0,0); leaf.rotation.y=-1.25; g.add(leaf); // cửa mở hé
    mesh(box(1.5,2.05,0.05),"#b98a5a",{parent:leaf,x:0.75,y:1.05}); mesh(new THREE.SphereGeometry(0.05,8,6),"#d4af37",{parent:leaf,x:1.35,y:1.05,z:0.05}); }
  function side(r,sd){ const D=r.door[0]===sd?r.door[1]:null, W=0.85; // một cạnh phòng, chừa lỗ cửa
    const seg=(a0,a1,f)=>{ if(D===null){ f(a0,a1); return; } f(a0,D-W); f(D+W,a1); };
    if(sd==="n") seg(r.x0,r.x1,(a,b)=>wallRun(a,r.z0,b,r.z0)); if(sd==="s") seg(r.x0,r.x1,(a,b)=>wallRun(a,r.z1,b,r.z1));
    if(sd==="e") seg(r.z0,r.z1,(a,b)=>wallRun(r.x1,a,r.x1,b));
    if(D!==null) doorFrame(sd==="e"?r.x1:D, sd==="n"?r.z0:sd==="s"?r.z1:D, sd!=="e"); }
  for(const r of ROOMS){ mesh(box(r.x1-r.x0,0.02,r.z1-r.z0),r.rug,{x:(r.x0+r.x1)/2,y:0.012,z:(r.z0+r.z1)/2,shadow:false}); [...r.walls].forEach(sd=>side(r,sd));
    const t=new THREE.Mesh(new THREE.PlaneGeometry(3.8,0.62),new THREE.MeshBasicMaterial({map:textTex([r.name],{w:576,h:96,bg:"#fffaf0",fg:"#1b2620",font:"700 44px 'Baloo 2', sans-serif"}),transparent:true}));
    t.rotation.x=-Math.PI/2; t.position.set((r.x0+r.x1)/2,0.03,Math.min(r.z1,16.6)-0.45); scene.add(t);
    const [sd,at]=r.door; r.in=sd==="e"?[r.x1-0.7,at]:sd==="s"?[at,r.z1-0.7]:[at,r.z0+0.7]; r.out=sd==="e"?[r.x1+0.8,at]:sd==="s"?[at,r.z1+0.7]:[at,r.z0-0.6]; }
  // lối đi chung giữa các phòng (đồ thị điểm), D = trước cửa phòng họp
  const NAV={A:[-9.4,0.3],B:[-2.3,0.3],D:[1.4,0.3],E:[1.4,8],F:[1.4,12],G:[-8,12],H:[0.8,12],I:[8.8,12]};
  const EDGES=[["A","B"],["B","D"],["D","E"],["E","F"],["F","H"],["H","G"],["F","I"]];
  const deskObjs={};
  function buildDesk(i,color,isSale){ const [x,z]=DESKS[i]; const g=new THREE.Group(); scene.add(g); const P={parent:g};
    mesh(box(2,0.1,0.95),"#d8b48a",{...P,x,y:0.76,z:z+0.95}); for(const dx of [-0.9,0.9]) mesh(box(0.08,0.74,0.85),"#a7835c",{...P,x:x+dx,y:0.37,z:z+0.95});
    mesh(box(0.95,0.6,0.06),"#2a2f2c",{...P,x,y:1.2,z:z+1.25}); const scr=new THREE.Mesh(new THREE.PlaneGeometry(0.85,0.5),new THREE.MeshBasicMaterial({color:isSale?0x4a7fd6:i===0?0x6fb4ff:0x8fe0a8})); scr.position.set(x,1.2,z+1.215); scr.rotation.y=Math.PI; g.add(scr);
    mesh(box(0.12,0.3,0.08),"#2a2f2c",{...P,x,y:0.95,z:z+1.25});
    mesh(box(0.6,0.03,0.2),"#e8e8e8",{...P,x,y:0.82,z:z+0.75});
    mesh(new THREE.CylinderGeometry(0.08,0.06,0.15,12),color,{...P,x:x+0.7,y:0.88,z:z+0.7});
    if(isSale){ mesh(box(0.34,0.6,0.04),"#1877f2",{...P,x:x-0.75,y:1.12,z:z+1.25}); } // biểu tượng nick Facebook trên bàn
    g.add(chair(x,z-0.05,0,"#3d4b44",true)); return g; }
  for(let i=0;i<5;i++) buildDesk(i,["#2f4b8f","#e2557a","#2e9e6b","#f08a24","#7a4fc9"][i]);
  { const g=buildDesk(15,"#3c6fd8"); const [x,z]=DESKS[15]; mesh(new THREE.SphereGeometry(0.12,14,10),"#3c6fd8",{parent:g,x:x-0.7,y:0.95,z:z+0.75}); } // quả địa cầu trên bàn Vy
  { const g=buildDesk(16,"#2f9e6a"); const [x,z]=DESKS[16]; mesh(box(0.28,0.2,0.04),"#f4efe2",{parent:g,x:x-0.7,y:0.92,z:z+0.75}); mesh(box(0.2,0.12,0.045),"#2f9e6a",{parent:g,x:x-0.7,y:0.93,z:z+0.75}); } // khung ảnh trên bàn Bảo
  { const g=buildDesk(17,"#e0559b"); const [x,z]=DESKS[17]; [0.12,0.2,0.3].forEach((h,i)=>mesh(box(0.06,h,0.06),"#e0559b",{parent:g,x:x-0.82+i*0.09,y:0.82+h/2,z:z+0.75})); } // biểu đồ xu hướng trên bàn Nhi
  { const g=buildDesk(14,"#0f8b8d"); const [x,z]=DESKS[14]; mesh(new THREE.TorusGeometry(0.13,0.03,8,18),"#0f8b8d",{parent:g,x:x-0.7,y:1.02,z:z+0.75}); } // kính lúp trên bàn Mai
  { const g=buildDesk(13,"#d4af37"); const [x,z]=DESKS[13]; // bàn CEO: biển tên mạ vàng + cờ nhỏ
    mesh(box(0.7,0.18,0.05),"#d4af37",{parent:g,x:x-0.55,y:0.9,z:z+0.5}); mesh(box(0.66,0.12,0.02),"#1f2a3a",{parent:g,x:x-0.55,y:0.9,z:z+0.47,shadow:false});
    mesh(new THREE.CylinderGeometry(0.015,0.015,0.5,6),"#888",{parent:g,x:x+0.55,y:1.05,z:z+0.6}); mesh(box(0.28,0.18,0.01),"#c0392b",{parent:g,x:x+0.69,y:1.2,z:z+0.6}); }
  // kệ hàng mẫu (hộp trà, hũ ngũ cốc)
  const shelf=new THREE.Group(); shelf.position.set(-12.4,0,-5.5); shelf.rotation.y=Math.PI/2; scene.add(shelf);
  mesh(box(3.4,2.6,0.6),"#8d6a48",{y:1.3,parent:shelf});
  const prodCols=["#d9534f","#5b8def","#e9b949","#4caf7a","#9b6bd6","#8a5a36"];
  for(let r=0;r<3;r++) for(let c=0;c<6;c++){ const tall=(r+c)%3===0; mesh(tall?new THREE.CylinderGeometry(0.17,0.17,0.45,14):box(0.38,0.4,0.28),prodCols[(c+r)%6],{x:-1.35+c*0.54,y:0.45+r*0.82,z:0.25,parent:shelf}); }
  // cây xanh
  function plant(x,z,s=1){ const g=new THREE.Group(); g.position.set(x,0,z); g.scale.setScalar(s); scene.add(g); mesh(new THREE.CylinderGeometry(0.32,0.25,0.55,14),"#c8643b",{y:0.28,parent:g});
    for(let i=0;i<5;i++){ const l=mesh(new THREE.IcosahedronGeometry(0.42,0),"#4f9a5a",{x:Math.sin(i*1.3)*0.25,y:0.85+i*0.18,z:Math.cos(i*1.3)*0.25,parent:g}); l.rotation.set(i,i*2,0); } return g; }
  plant(-12.3,11.3,1.1); plant(2.2,-7.2); plant(11.8,-7.2,1.2); plant(11.8,6.6); plant(0.8,11.2,0.9); plant(-12.3,-1.2,0.9);
  // bình nước + sofa nhỏ
  mesh(box(0.5,1.1,0.5),"#e9efe9",{x:-12.3,y:0.55,z:3}); mesh(new THREE.CylinderGeometry(0.2,0.2,0.5,14),"#7cc4e8",{x:-12.3,y:1.35,z:3});

  /* --------------------------------------------- nhân vật chibi */
  const CH=1.4; // độ to nhân vật so với bàn ghế
  const blobMat=new THREE.MeshBasicMaterial({color:0x1b2620,transparent:true,opacity:0.2,depthWrite:false});
  const cheekMat=new THREE.MeshBasicMaterial({color:0xf59a9e,transparent:true,opacity:0.75});
  const hairShine=new THREE.MeshBasicMaterial({color:0xffffff,transparent:true,opacity:0.28,depthWrite:false});
  const eyeSpark=m=>{ m.material=new THREE.MeshBasicMaterial({color:0xffffff}); return m; };
  function makeChar(a){
    const L=a.look, root=new THREE.Group(); root.scale.setScalar(CH); scene.add(root);
    const shade=new THREE.Mesh(new THREE.CircleGeometry(0.5,28),blobMat); shade.rotation.x=-Math.PI/2; shade.position.y=0.012; shade.renderOrder=1; root.add(shade); // bóng mềm dưới chân
    const body=new THREE.Group(); root.add(body);
    const legs=[-1,1].map(s=>{ const p=new THREE.Group(); p.position.set(0.15*s,0.55,0); body.add(p);
      outline(mesh(new THREE.CylinderGeometry(0.115,0.1,0.5,16),L.pants,{y:-0.25,parent:p}),1.09);
      const shoe=outline(mesh(new THREE.SphereGeometry(0.135,18,12),"#2b2b2b",{y:-0.5,z:0.06,parent:p}),1.1); shoe.scale.set(1,0.6,1.45); return p; });
    outline(mesh(new THREE.CylinderGeometry(0.31,0.37,0.62,28),L.shirt,{y:0.86,parent:body}),1.05);
    outline(mesh(new THREE.SphereGeometry(0.31,28,16),L.shirt,{y:1.16,parent:body}),1.05).scale.set(1,0.45,1);
    mesh(new THREE.CylinderGeometry(0.1,0.12,0.08,10),L.skin,{y:1.27,parent:body});
    const arms=[-1,1].map(s=>{ const p=new THREE.Group(); p.position.set(0.39*s,1.1,0); body.add(p);
      const arm=outline(mesh(new THREE.CylinderGeometry(0.08,0.072,0.46,14),L.shirt,{y:-0.22,parent:p}),1.12); arm.rotation.z=0.12*s;
      outline(mesh(new THREE.SphereGeometry(0.09,16,12),L.skin,{x:0.03*s,y:-0.47,parent:p}),1.12); return p; });
    const head=new THREE.Group(); head.position.y=1.72; head.scale.setScalar(1.12); body.add(head); // đầu to kiểu chibi
    outline(mesh(new THREE.SphereGeometry(0.44,44,32),L.skin,{parent:head}),1.045);
    const eyes=[-1,1].map(s=>{ const e=new THREE.Group(); e.position.set(0.16*s,0.02,0.37); head.add(e);
      outline(mesh(new THREE.SphereGeometry(0.1,22,16),"#ffffff",{parent:e,shadow:false}),1.12).scale.set(1,1.2,0.5);
      mesh(new THREE.SphereGeometry(0.072,20,14),L.eye||"#4a2e1f",{z:0.03,y:-0.012,parent:e,shadow:false}).scale.set(1,1.22,0.6);
      mesh(new THREE.SphereGeometry(0.04,14,10),"#0e0e12",{z:0.06,y:-0.012,parent:e,shadow:false}).scale.set(1,1.2,0.5);
      eyeSpark(mesh(new THREE.SphereGeometry(0.024,10,8),"#ffffff",{x:0.026,y:0.034,z:0.082,parent:e,shadow:false}));
      eyeSpark(mesh(new THREE.SphereGeometry(0.012,8,6),"#ffffff",{x:-0.024,y:-0.036,z:0.08,parent:e,shadow:false})); return e; });
    [-1,1].forEach(s=>{ const b=mesh(new THREE.CylinderGeometry(0.016,0.016,0.11,8),L.hair,{x:0.16*s,y:0.155,z:0.405,parent:head,shadow:false}); b.rotation.z=Math.PI/2-0.12*s; }); // lông mày
    const cheeks=[]; [-1,1].forEach(s=>{ const c=mesh(new THREE.CircleGeometry(0.065,16),"#f39a9a",{x:0.27*s,y:-0.1,z:0.355,parent:head,shadow:false}); c.rotation.y=0.6*s; c.scale.set(1.25,0.85,1); c.material=cheekMat; cheeks.push(c); });
    const mouth=mesh(new THREE.TorusGeometry(0.065,0.019,10,20,Math.PI),"#7a2b2b",{y:-0.15,z:0.42,parent:head,shadow:false}); mouth.rotation.z=Math.PI;
    // tóc
    const capGeo=new THREE.SphereGeometry(0.47,40,20,0,Math.PI*2,0,Math.PI*0.52);
    const cap=outline(mesh(capGeo,L.hair,{y:0.04,parent:head}),1.035); cap.rotation.x=-0.28;
    const shine=new THREE.Mesh(new THREE.TorusGeometry(0.3,0.025,6,24,Math.PI*0.6),hairShine); shine.position.set(0,0.3,0.2); shine.rotation.set(-0.95,0,Math.PI*0.2); head.add(shine); // vệt bóng tóc
    if(L.hairStyle==="side"){ const f=mesh(box(0.55,0.13,0.18),L.hair,{x:0.1,y:0.3,z:0.33,parent:head}); f.rotation.z=-0.35; }
    if(L.hairStyle==="long"){ const b=outline(mesh(new THREE.SphereGeometry(0.47,32,20),L.hair,{y:-0.2,z:-0.12,parent:head}),1.035); b.scale.set(1.02,1.15,0.75);
      [-1,1].forEach(s=>mesh(box(0.14,0.55,0.2),L.hair,{x:0.4*s,y:-0.18,z:0.08,parent:head})); }
    if(L.hairStyle==="bun"){ outline(mesh(new THREE.SphereGeometry(0.19,24,16),L.hair,{y:0.45,z:-0.2,parent:head}),1.08); }
    if(L.hairStyle==="spiky"){ for(let i=0;i<7;i++){ const a=i/7*Math.PI*2; const c=mesh(new THREE.ConeGeometry(0.11,0.3,8),L.hair,{x:Math.sin(a)*0.24,y:0.45,z:Math.cos(a)*0.2-0.05,parent:head}); c.rotation.set(Math.cos(a)*0.6,0,-Math.sin(a)*0.6); } }
    // phụ kiện
    if(L.accessory==="glasses"){ [-1,1].forEach(s=>mesh(new THREE.TorusGeometry(0.11,0.018,8,20),"#1b1b1b",{x:0.16*s,y:0.02,z:0.43,parent:head,shadow:false})); mesh(box(0.1,0.02,0.02),"#1b1b1b",{y:0.04,z:0.45,parent:head,shadow:false}); }
    if(L.accessory==="beret"){ const b=mesh(new THREE.SphereGeometry(0.36,20,12),"#b8325a",{x:0.08,y:0.43,parent:head}); b.scale.set(1.15,0.38,1.15); b.rotation.z=-0.25; }
    if(L.accessory==="cap"){ const c=mesh(new THREE.SphereGeometry(0.49,24,12,0,Math.PI*2,0,Math.PI*0.5),"#2e7d57",{y:0.08,parent:head}); c.rotation.x=-0.15;
      const br=mesh(new THREE.CylinderGeometry(0.3,0.3,0.035,24,1,false,-Math.PI/2,Math.PI),"#26664a",{y:0.17,z:0.33,parent:head}); br.rotation.x=0.15; }
    if(L.accessory==="headset"){ mesh(new THREE.TorusGeometry(0.49,0.03,8,28,Math.PI),"#333",{y:0.02,parent:head});
      [-1,1].forEach(s=>{ const e=mesh(new THREE.CylinderGeometry(0.11,0.11,0.08,16),"#333",{x:0.48*s,parent:head}); e.rotation.z=Math.PI/2; });
      const mic=mesh(new THREE.CylinderGeometry(0.015,0.015,0.38,6),"#333",{x:-0.4,y:-0.2,z:0.2,parent:head}); mic.rotation.set(1.1,0,0.4); mesh(new THREE.SphereGeometry(0.04,8,6),"#333",{x:-0.27,y:-0.3,z:0.36,parent:head}); }
    if(L.tie){ mesh(box(0.1,0.36,0.03),L.tie,{y:0.9,z:0.345,parent:body}); mesh(box(0.13,0.08,0.04),L.tie,{y:1.1,z:0.33,parent:body});
      [-1,1].forEach(s=>{ const c=mesh(box(0.14,0.1,0.02),"#f4f4f4",{x:0.07*s,y:1.13,z:0.31,parent:body}); c.rotation.z=0.5*s; }); }
    root.traverse(o=>o.userData.agent=a.id);
    const c={shade,id:a.id,a,root,body,legs,arms,head,mouth,eyes,cheeks,path:[],mode:"desk",state:"idle",talk:0,blink:Math.random()*4,phase:Math.random()*10};
    if(a.face) setFace(c,a.face);
    return c;
  }
  // ảnh mặt sếp tải lên: dán thành mặt tròn phía trước đầu, ẩn mắt / miệng / má vẽ sẵn
  function setFace(c,url){
    if(c.faceUrl===url) return; c.faceUrl=url||"";
    if(c.facePlane){ c.head.remove(c.facePlane); c.facePlane.geometry.dispose(); c.facePlane.material.map?.dispose(); c.facePlane.material.dispose(); c.facePlane=null; }
    const show=!url; c.eyes.forEach(e=>e.visible=show); c.mouth.visible=show; (c.cheeks||[]).forEach(x=>x.visible=show);
    if(!url) return;
    new THREE.TextureLoader().load(url,tex=>{ if(c.faceUrl!==url) return;
      const m=new THREE.Mesh(new THREE.CircleGeometry(0.33,40),new THREE.MeshBasicMaterial({map:tex}));
      m.position.set(0,-0.03,0.452); m.userData.agent=c.id; c.head.add(m); c.facePlane=m; },
      undefined,()=>{ c.eyes.forEach(e=>e.visible=true); c.mouth.visible=true; (c.cheeks||[]).forEach(x=>x.visible=true); });
  }

  const chars={}, tags={}, bubbles={};
  const DOOR_O=new THREE.Vector3(2.0,0,0), DOOR_I=new THREE.Vector3(4.0,0,0);
  const deskSpot=id=>{ const [x,z]=DESKS[AGENT[id].desk]; return {x,z,ry:0}; };
  function addAgent(a){ AGENT[a.id]=a; const c=makeChar(a); chars[a.id]=c; const d=deskSpot(a.id); c.root.position.set(d.x,0,d.z);
    if(a.kind==="sale") deskObjs[a.id]=buildDesk(a.desk,a.look.shirt,true);
    if(a.kind==="staff"&&DESKS[a.desk]) deskObjs[a.id]=buildDesk(a.desk,a.look.shirt,false); addTag(a.id,a.name); }
  function removeAgent(id){ const c=chars[id]; if(!c) return; scene.remove(c.root); if(deskObjs[id]) scene.remove(deskObjs[id]);
    delete chars[id]; delete deskObjs[id]; tags[id]?.remove(); bubbles[id]?.remove(); delete tags[id]; delete bubbles[id]; }

  // đường đi: lách cạnh bàn -> lối đi giữa -> cửa kính -> vòng quanh bàn họp -> ghế
  const V=(x,z)=>new THREE.Vector3(x,0,z);
  const roomAt=(x,z)=>ROOMS.find(r=>x>r.x0&&x<r.x1&&z>r.z0&&z<r.z1);
  const nearNode=(x,z)=>Object.keys(NAV).reduce((m,k)=>Math.hypot(NAV[k][0]-x,NAV[k][1]-z)<Math.hypot(NAV[m][0]-x,NAV[m][1]-z)?k:m,"D");
  function navPath(a,b){ if(a===b) return [a]; const prev={[a]:null}, q=[a]; while(q.length){ const n=q.shift(); if(n===b) break;
      for(const [u,v] of EDGES){ const m=u===n?v:v===n?u:null; if(m&&!(m in prev)){ prev[m]=n; q.push(m); } } }
    const out=[]; for(let n=b;n!==null&&n!==undefined;n=prev[n]) out.unshift(n); return out; }
  function route(x0,z0,x1,z1){ // đi từ điểm này sang điểm khác: ra cửa phòng mình → lối đi chung → vào cửa phòng kia
    const ra=roomAt(x0,z0), rb=roomAt(x1,z1); if(ra&&ra===rb) return [V(x1,z1)];
    const pts=[]; if(ra) pts.push(V(...ra.in),V(...ra.out)); const na=ra?ra.node:nearNode(x0,z0), nb=rb?rb.node:nearNode(x1,z1);
    navPath(na,nb).forEach(k=>pts.push(V(...NAV[k]))); if(rb) pts.push(V(...rb.out),V(...rb.in)); pts.push(V(x1,z1)); return pts; }
  const beside=id=>{ const d=deskSpot(id); return [d.x+1.15,d.z]; };
  function deskLeg(id){ const [bx,bz]=beside(id); return [V(bx,bz),...route(bx,bz,...NAV.D)]; }
  function seatLeg(id){ const s=SEATS[id]; const r=[DOOR_O.clone(),DOOR_I.clone()];
    if(s.x>MC.x+0.5) r.push(V(MC.x,(s.z>=0?1:-1)*(Math.hypot(s.x-MC.x,s.z-MC.z)+0.7))); r.push(V(s.x,s.z)); return r; }
  function goMeeting(id){ const c=chars[id]; if(!SEATS[id]||c.mode==="meeting"||c.mode==="toMeeting") return; const p=c.root.position;
    c.path=c.mode==="desk"? [...deskLeg(id),...seatLeg(id)] : [...route(p.x,p.z,...NAV.D),...seatLeg(id)]; c.final=SEATS[id]; c.mode="toMeeting"; }
  // sang bàn đồng nghiệp trao đổi công việc rồi về chỗ
  const busyMeet=c=>c.mode==="meeting"||c.mode==="toMeeting";
  const QUEUE=[[0,0],[0,0.95],[0,-0.95],[-0.9,0.5],[-0.9,-0.5]];
  function standAt(to,c){ const d=deskSpot(to), n=Object.values(chars).filter(x=>x!==c&&x.visit&&x.visit.to===to&&(x.mode==="toVisit"||x.mode==="visiting")).length, [ox,oz]=QUEUE[n%5]; // nhiều người cùng đến: đứng xếp hàng
    return [d.x-1.1+ox, d.z-0.2+oz]; }
  function visit(from,to,text){ const c=chars[from], o=chars[to]; if(!c||!o||from===to||c.mode!=="desk"||busyMeet(o)) return false;
    const d=deskSpot(to), [sx,sz]=standAt(to,c), [bx,bz]=beside(from);
    c.path=[V(bx,bz),...route(bx,bz,sx,sz)]; c.visit={text,back:[...route(sx,sz,bx,bz),V(deskSpot(from).x,deskSpot(from).z)],ry:Math.atan2(d.x-sx,d.z-sz),to};
    c.final={x:sx,z:sz,ry:c.visit.ry}; c.mode="toVisit"; return true; }
  // CEO gọi một người (bất kỳ ai, đang đi đâu cũng bỏ dở) lên bàn mình nhận việc, nhận xong về chỗ
  function summon(by,who,text){ const c=chars[who], o=chars[by]; if(!c||!o||by===who||busyMeet(c)) return false;
    const d=deskSpot(by), [sx,sz]=standAt(by,c), p=c.root.position, h=deskSpot(who), [bx,bz]=beside(who);
    c.path=c.mode==="desk"?[V(bx,bz),...route(bx,bz,sx,sz)]:route(p.x,p.z,sx,sz);
    c.visit={text,back:[...route(sx,sz,bx,bz),V(h.x,h.z)],ry:Math.atan2(d.x-sx,d.z-sz),to:by}; c.final={x:sx,z:sz,ry:c.visit.ry}; c.mode="toVisit";
    if(!busyMeet(o)) say(by,`${AGENT[who].name} ơi, lên phòng anh nhận việc nhé!`,4000); return true; }
  function goDesk(id){ const c=chars[id]; if(c.mode==="desk"||c.mode==="toDesk") return; const d=deskSpot(id);
    const back=[...deskLeg(id)].reverse();
    c.path = c.mode==="toMeeting"&&c.root.position.x<3 ? [...back,V(d.x,d.z)] : [...[...seatLeg(id)].reverse().slice(1),...back,V(d.x,d.z)]; c.final=d; c.mode="toDesk"; }

  /* --------------------------------------------- nhãn tên + bong bóng thoại */
  function addTag(id,name){ const t=document.createElement("div"); t.className="tag"; t.textContent=name; overlay.appendChild(t); tags[id]=t;
    const b=document.createElement("div"); b.className="bubble"; b.hidden=true; overlay.appendChild(b); bubbles[id]=b; }
  addTag("boss","Ghế Sếp");
  AGENT_DEFS.forEach(addAgent); layoutSeats(AGENT_DEFS.map(a=>a.id));
  let speech={id:null,text:"",until:0}; const v3=new THREE.Vector3();
  function say(id,text,ms=9000){ speech={id,text,until:performance.now()+ms}; }

  /* --------------------------------------------- vòng lặp */
  const clock=new THREE.Clock();
  function resize(){ const w=stage.clientWidth,h=stage.clientHeight; if(!w||!h) return; renderer.setSize(w,h,false); camera.aspect=w/h; camera.updateProjectionMatrix(); }
  new ResizeObserver(resize).observe(stage);
  const lerpA=(a,b,t)=>{ let d=((b-a+Math.PI)%(Math.PI*2)+Math.PI*2)%(Math.PI*2)-Math.PI; return a+d*t; };
  let lastF=0, lastIn=performance.now(), nF=0;
  ["pointerdown","pointermove","wheel"].forEach(ev=>stage.addEventListener(ev,()=>{ lastIn=performance.now(); },{passive:true}));
  renderer.shadowMap.autoUpdate=false;
  function tick(now){
    if(document.hidden||!stage.offsetParent){ clock.getDelta(); setTimeout(()=>requestAnimationFrame(tick),600); return; }  // không ai xem: không vẽ
    // có người đi lại / nói / sếp đang xoay cảnh: ~30 hình/giây; còn lại mọi người ngồi làm việc: ~10 hình/giây cho đỡ tốn máy
    const lively=camGoal||performance.now()<speech.until||now-lastIn<15000||Object.values(chars).some(c=>c.mode!=="desk"&&c.mode!=="meeting"||c.mode==="meeting");
    if(now-lastF<(lively?32:95)){ requestAnimationFrame(tick); return; } lastF=now||0;
    if(lively||++nF%3===0) renderer.shadowMap.needsUpdate=true;  // bóng đổ: vẽ lại thưa hơn khi cảnh đứng yên
    const dt=Math.min(clock.getDelta(),0.2), t=clock.elapsedTime;
    if(camGoal){ camera.position.lerp(camGoal.pos,0.06); controls.target.lerp(camGoal.tgt,0.06); if(camera.position.distanceTo(camGoal.pos)<0.05) camGoal=null; }
    controls.update();
    for(const c of Object.values(chars)){
      if(c.mode==="visiting"&&performance.now()>c.visitEnd){ c.path=c.visit.back; c.final=deskSpot(c.id); c.mode="toDesk"; }
      const talking = speech.id===c.id && performance.now()<speech.until;
      if(c.path.length){
        const p=c.root.position, tgt=c.path[0], dx=tgt.x-p.x, dz=tgt.z-p.z, dist=Math.hypot(dx,dz);
        if(dist<0.08){ c.path.shift(); if(!c.path.length){ if(c.mode==="toVisit"){ c.mode="visiting"; c.visitEnd=performance.now()+6500; say(c.id,c.visit.text,6200); } else c.mode=c.mode==="toMeeting"?"meeting":"desk"; } }
        else { const sp=2.4*dt; p.x+=dx/dist*Math.min(sp,dist); p.z+=dz/dist*Math.min(sp,dist); c.root.rotation.y=lerpA(c.root.rotation.y,Math.atan2(dx,dz),0.2); }
        const sw=Math.sin(t*11); c.legs[0].rotation.x=sw*0.6; c.legs[1].rotation.x=-sw*0.6; c.arms[0].rotation.x=-sw*0.5; c.arms[1].rotation.x=sw*0.5;
        c.body.position.y=Math.abs(Math.sin(t*11))*0.06; c.shade.scale.setScalar(1-c.body.position.y*2);
      } else {
        const f=c.final||deskSpot(c.id); c.root.rotation.y=lerpA(c.root.rotation.y,f.ry,0.12);
        c.legs.forEach(l=>l.rotation.x+=(-1.45-l.rotation.x)*0.2); c.body.position.y+=(-0.04-c.body.position.y)*0.2;
        if((c.state==="working"||c.state==="learning") && c.mode==="desk"){ c.arms.forEach((a,i)=>a.rotation.x=-1.15+Math.sin(t*22+i*2)*0.12); c.head.rotation.x=0.12; }
        else if(talking){ c.arms[1].rotation.x=-0.9+Math.sin(t*4)*0.4; c.arms[0].rotation.x+=( -0.2-c.arms[0].rotation.x)*0.1; c.head.rotation.x=Math.sin(t*5)*0.08; c.body.position.y=-0.04+Math.abs(Math.sin(t*6))*0.05; }
        else { c.arms.forEach(a=>a.rotation.x+=(-0.15-a.rotation.x)*0.1); c.head.rotation.x=0; c.head.rotation.y=Math.sin(t*0.6+c.phase)*0.25; c.body.position.y=-0.04+Math.sin(t*2+c.phase)*0.015; }
      }
      c.mouth.scale.y = talking ? 0.6+Math.abs(Math.sin(t*14))*1.6 : 1; c.mouth.scale.x = talking?1.2:1;
      c.blink-=dt; const bl=c.blink<0.12; c.eyes.forEach(e=>e.scale.y=bl?0.12:1); if(c.blink<0) c.blink=2+Math.random()*4;
    }
    renderer.render(scene,camera);
    // vị trí nhãn
    const w=stage.clientWidth,h=stage.clientHeight;
    const place=(id,pos)=>{ v3.copy(pos).project(camera); const x=(v3.x*0.5+0.5)*w, y=(-v3.y*0.5+0.5)*h; const vis=v3.z<1&&x>-50&&x<w+50; return {x,y,vis}; };
    for(const id of Object.keys(tags)){
      if(id!=="boss"&&!chars[id]) continue;
      const base = id==="boss" ? new THREE.Vector3(SEATS.boss.x,0,SEATS.boss.z) : chars[id].root.position;
      const top=place(id,new THREE.Vector3(base.x,id==="boss"?1.5:3.45,base.z));
      const tg=tags[id]; tg.hidden=!top.vis||(id==="boss"&&!Object.values(chars).some(c=>c.mode==="meeting")); tg.style.left=top.x+"px"; tg.style.top=top.y+"px";
      top.y-=24;
      const b=bubbles[id]; const showMain = speech.id===id && performance.now()<speech.until;
      const st = id!=="boss" && chars[id].statusText && chars[id].state==="working" && chars[id].mode==="desk";
      if(showMain||st){ b.hidden=!top.vis; b.className = showMain?"bubble":"bubble mini"; const nm=id==="boss"?"Sếp":AGENT[id].name;
        const txt = showMain?speech.text:chars[id].statusText; const html = showMain?`<b>${esc(nm)}:</b> ${esc(txt.length>170?txt.slice(0,167)+"…":txt)}`:esc(txt);
        if(b._h!==html){ b.innerHTML=html; b._h=html; } const half=Math.min(b.offsetWidth/2+8,w/2); b.style.left=Math.max(half,Math.min(w-half,top.x))+"px"; b.style.top=Math.max(b.offsetHeight+8,top.y-6)+"px"; }
      else b.hidden=true;
    }
    requestAnimationFrame(tick);
  }
  tick();

  // bấm vào nhân vật
  const ray=new THREE.Raycaster(), mv=new THREE.Vector2(); let down=null;
  canvas.addEventListener("pointerdown",e=>down=[e.clientX,e.clientY]);
  canvas.addEventListener("pointerup",e=>{ if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>5) return; const r=canvas.getBoundingClientRect();
    mv.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1); ray.setFromCamera(mv,camera);
    const hit=ray.intersectObjects(Object.values(chars).map(c=>c.root),true)[0]; if(hit&&hit.object.userData.agent) openAgent(hit.object.userData.agent); });
  canvas.addEventListener("pointermove",e=>{ const r=canvas.getBoundingClientRect(); mv.set((e.clientX-r.left)/r.width*2-1,-(e.clientY-r.top)/r.height*2+1); ray.setFromCamera(mv,camera);
    canvas.style.cursor=ray.intersectObjects(Object.values(chars).map(c=>c.root),true).length?"pointer":"grab"; });

  function sync(agents, meetingRunning){
    const ids=new Set(agents.map(a=>a.id)); let changed=false;
    for(const a of agents) if(!chars[a.id]){ addAgent(a); changed=true; }
    for(const id of Object.keys(chars)) if(!ids.has(id)){ removeAgent(id); changed=true; }
    for(const a of agents){ if(chars[a.id]&&(chars[a.id].faceUrl||"")!==(a.face||"")) setFace(chars[a.id],a.face||""); if(AGENT[a.id]&&(AGENT[a.id].name!==a.name||AGENT[a.id].face!==a.face)) AGENT[a.id]={...AGENT[a.id],name:a.name,face:a.face||""}; }
    for(const a of agents){ const label=(a.level?`${a.name} · Cấp ${a.level}`:a.name)+(a.status?.state==="learning"?" · đang học":""); if(chars[a.id] && tags[a.id] && tags[a.id].textContent!==label){ tags[a.id].textContent=label; AGENT[a.id]={...AGENT[a.id],...a}; } }
    if(changed){ layoutSeats(agents.map(a=>a.id)); for(const c of Object.values(chars)) if(c.mode==="meeting"){ const s=SEATS[c.id]; c.root.position.set(s.x,0,s.z); c.final=s; } }
    for(const a of agents){ const c=chars[a.id]; if(!c) continue; const st=a.status||{}; c.state=st.state||"idle"; c.statusText=st.text||"";
      if(st.state==="meeting"||st.state==="talking"||meetingRunning) goMeeting(a.id); else if(c.mode!=="toVisit"&&c.mode!=="visiting") goDesk(a.id); }
  }
  function mount(slot){ if(stage.parentNode!==slot){ slot.appendChild(stage); resize(); } }
  return {setCam,sync,say,setBoard,mount,visit,summon};
})();

