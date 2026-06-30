/* ============================================================================
   FALCON // HOLO-LIB — Biblioteca de modelos 3D holográficos CFE (reutilizable)
   Requiere THREE (r128). OrbitControls y GLTFLoader son opcionales.
   Expone window.Holo = { build, createViewer, MODELS, TYPE2MODEL, ... }
   NOTA: los builders son copia del código aprobado en holo-models/index.html.
   ============================================================================ */
(function(){
  if(typeof THREE==='undefined'){ console.error('Holo: THREE no está cargado'); return; }
  const HUD=0x22d3ee, GLOW=0x67e8f9;

  // ---- estado de animación (un visor activo a la vez) ----
  const spin=[], steam=[];
  function clearSpin(){ spin.length=0; steam.length=0; }

  // ---------- Helpers holográficos ----------
  function holo(geo,{color=HUD,wire=false,fill=0.05,edge=0.9,thr=20}={}){
    const g=new THREE.Group();
    if(fill>0){
      g.add(new THREE.Mesh(geo,new THREE.MeshBasicMaterial({color,transparent:true,opacity:fill,
        blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide})));
    }
    if(edge>0){
      const lg = wire ? new THREE.WireframeGeometry(geo) : new THREE.EdgesGeometry(geo,thr);
      g.add(new THREE.LineSegments(lg,new THREE.LineBasicMaterial({color,transparent:true,opacity:edge})));
    }
    return g;
  }
  function segs(list,color=HUD,op=0.85){
    const geo=new THREE.BufferGeometry();
    geo.setAttribute('position',new THREE.Float32BufferAttribute(list,3));
    return new THREE.LineSegments(geo,new THREE.LineBasicMaterial({color,transparent:true,opacity:op}));
  }
  function ring(r,y=0.05,color=HUD,op=0.5,seg=64){
    const pts=[];for(let i=0;i<=seg;i++){const a=i/seg*Math.PI*2;pts.push(new THREE.Vector3(Math.cos(a)*r,y,Math.sin(a)*r));}
    return new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts),
      new THREE.LineBasicMaterial({color,transparent:true,opacity:op}));
  }
  function addSteam(x,y,z,r,n){
    const pts=[]; for(let i=0;i<n;i++) pts.push(x+(Math.random()-0.5)*r, y+Math.random()*3.6, z+(Math.random()-0.5)*r);
    const gg=new THREE.BufferGeometry(); gg.setAttribute('position',new THREE.Float32BufferAttribute(pts,3));
    const m=new THREE.Points(gg,new THREE.PointsMaterial({color:GLOW,size:0.26,transparent:true,opacity:0.35,
      blending:THREE.AdditiveBlending,depthWrite:false}));
    steam.push({m,baseY:y,top:y+3.8,r}); return m;
  }
  function latticeColumn(x,z,h,half,levels){
    levels=levels||6; const s=[], C=[[1,1],[1,-1],[-1,-1],[-1,1]], lv=[];
    for(let i=0;i<=levels;i++) lv.push(i/levels*h);
    const cor=(y,sx,sz)=>[x+sx*half,y,z+sz*half];
    for(let c=0;c<4;c++)for(let i=0;i<levels;i++)s.push(...cor(lv[i],...C[c]),...cor(lv[i+1],...C[c]));
    for(const y of lv)for(let c=0;c<4;c++)s.push(...cor(y,...C[c]),...cor(y,...C[(c+1)%4]));
    for(let i=0;i<levels;i++)for(let c=0;c<4;c++){const c2=(c+1)%4;
      if(i%2===0) s.push(...cor(lv[i],...C[c]),...cor(lv[i+1],...C[c2]));
      else        s.push(...cor(lv[i+1],...C[c]),...cor(lv[i],...C[c2]));}
    return s;
  }
  function insulator(x,z,y0,h){
    const grp=new THREE.Group();
    grp.add(holo(new THREE.CylinderGeometry(0.07,0.07,h,8),{fill:0.04,edge:0.4}).translateX(x).translateY(y0+h/2).translateZ(z));
    const n=Math.max(3,Math.round(h/0.22));
    for(let i=1;i<n;i++){const rr=ring(0.15,y0+i*h/n,GLOW,0.45,14); rr.position.x=x; rr.position.z=z; grp.add(rr);}
    return grp;
  }
  function transformer(cx,cz){
    const t=new THREE.Group();
    const tank=holo(new THREE.BoxGeometry(1.7,1.5,1.2)); tank.position.set(cx,0.85,cz); t.add(tank);
    const cons=holo(new THREE.CylinderGeometry(0.24,0.24,1.5,14)); cons.rotation.z=Math.PI/2; cons.position.set(cx,2.0,cz-0.5); t.add(cons);
    [-0.5,0,0.5].forEach(bx=>{const b=holo(new THREE.CylinderGeometry(0.08,0.13,1.0,8)); b.position.set(cx+bx,2.25,cz+0.3); b.rotation.x=-0.3; t.add(b);
      const rr=ring(0.18,0,GLOW,0.5,12); rr.position.set(cx+bx,2.75,cz+0.45); t.add(rr);});
    const rad=[];
    [-1,1].forEach(side=>{ const xf=cx+side*1.0;
      for(let f=0;f<=7;f++){const zz=cz-0.55+f*0.157; rad.push(xf,0.3,zz, xf,1.4,zz);}
      rad.push(xf,0.3,cz-0.55, xf,0.3,cz+0.55,  xf,1.4,cz-0.55, xf,1.4,cz+0.55);
      rad.push(cx+side*0.85,0.85,cz-0.4, xf,0.85,cz-0.4,  cx+side*0.85,0.85,cz+0.4, xf,0.85,cz+0.4);
    });
    t.add(segs(rad,GLOW,0.55));
    return t;
  }
  function bladeLines(){
    const L=4.5, N=18, th=0.10, le=[], te=[];
    const chord=t=> t<0.16 ? 0.07+(t/0.16)*0.45 : 0.52*Math.pow((1-t)/0.84,0.85)+0.03;
    for(let i=0;i<=N;i++){const t=i/N, y=t*L, c=chord(t), sweep=0.12*t*t;
      le.push([-c*0.42+sweep,y]); te.push([c*0.58+sweep,y]);}
    const g=new THREE.Group();
    const shape=new THREE.Shape(); shape.moveTo(le[0][0],le[0][1]);
    for(let i=1;i<=N;i++) shape.lineTo(le[i][0],le[i][1]);
    for(let i=N;i>=0;i--) shape.lineTo(te[i][0],te[i][1]);
    g.add(new THREE.Mesh(new THREE.ShapeGeometry(shape),
      new THREE.MeshBasicMaterial({color:HUD,transparent:true,opacity:0.06,blending:THREE.AdditiveBlending,depthWrite:false,side:THREE.DoubleSide})));
    const s=[];
    [th/2,-th/2].forEach(z=>{
      for(let i=0;i<N;i++){ s.push(le[i][0],le[i][1],z, le[i+1][0],le[i+1][1],z);
        s.push(te[i][0],te[i][1],z, te[i+1][0],te[i+1][1],z); }
      s.push(le[0][0],le[0][1],z, te[0][0],te[0][1],z);  s.push(le[N][0],le[N][1],z, te[N][0],te[N][1],z); });
    for(let i=0;i<=N;i+=3){ s.push(le[i][0],le[i][1],th/2, le[i][0],le[i][1],-th/2);
      s.push(te[i][0],te[i][1],th/2, te[i][0],te[i][1],-th/2); }
    g.add(segs(s,HUD,0.8));
    return g;
  }
  function makeTurbine(){
    const t=new THREE.Group();
    const tower=holo(new THREE.CylinderGeometry(0.16,0.34,9,16)); tower.position.y=4.5; t.add(tower);
    const base=holo(new THREE.CylinderGeometry(0.55,0.8,0.45,18)); base.position.y=0.22; t.add(base);
    const nacGrp=new THREE.Group();
    const nac=holo(new THREE.CylinderGeometry(0.30,0.26,1.5,8),{fill:0.06,edge:0.6});
    nac.rotation.x=Math.PI/2; nacGrp.add(nac);
    nacGrp.scale.set(1.25,0.82,1); nacGrp.position.set(0,9,-0.15); t.add(nacGrp);
    t.add(holo(new THREE.BoxGeometry(0.12,0.12,0.12)).translateY(9.3).translateZ(-0.5));
    t.add(segs([0,9.3,-0.55, 0,9.75,-0.55],GLOW,0.6));
    const hub=new THREE.Group(); hub.position.set(0,9,0.55);
    const cube=holo(new THREE.CylinderGeometry(0.26,0.28,0.4,14)); cube.rotation.x=Math.PI/2; hub.add(cube);
    const nose=holo(new THREE.ConeGeometry(0.27,0.5,16)); nose.rotation.x=Math.PI/2; nose.position.z=0.42; hub.add(nose);
    for(let k=0;k<3;k++){const arm=new THREE.Group(); arm.add(bladeLines()); arm.rotation.z=k*2*Math.PI/3; hub.add(arm);}
    t.add(hub); spin.push({obj:hub,axis:'z',speed:0.8});
    return t;
  }
  function mAerogenerador(){
    const g=new THREE.Group(); clearSpin();
    g.add(makeTurbine());
    const t2=makeTurbine(); t2.scale.setScalar(0.6); t2.position.set(-6.5,0,-6); g.add(t2);
    const t3=makeTurbine(); t3.scale.setScalar(0.5); t3.position.set(7,0,-8); g.add(t3);
    const rr=ring(3,0,HUD,0.25,48); rr.rotation.x=Math.PI/2; rr.position.set(0,9,0.55); g.add(rr);
    return g;
  }
  function txTower(){ // un solo pilón (cuerpo + crucetas + aisladores), sin conductores
    const g=new THREE.Group();
    const H=11, baseHalf=1.9, waistHalf=0.5, waistY=6.5;
    const w=y=> y<=waistY ? baseHalf+(waistHalf-baseHalf)*(y/waistY) : waistHalf;
    const C=[[1,1],[1,-1],[-1,-1],[-1,1]];
    const cor=(y,c)=>[C[c][0]*w(y), y, C[c][1]*w(y)];
    const lv=[]; const NP=11; for(let i=0;i<=NP;i++) lv.push(i/NP*H);
    const s=[];
    for(let c=0;c<4;c++) for(let i=0;i<lv.length-1;i++) s.push(...cor(lv[i],c),...cor(lv[i+1],c));
    for(const y of lv) for(let c=0;c<4;c++) s.push(...cor(y,c),...cor(y,(c+1)%4));
    for(let i=0;i<lv.length-1;i++) for(let c=0;c<4;c++){ const c2=(c+1)%4;
      s.push(...cor(lv[i],c),...cor(lv[i+1],c2)); s.push(...cor(lv[i],c2),...cor(lv[i+1],c)); }
    g.add(segs(s,HUD,0.8));
    const arms=[7.4,8.7,10.0], armS=[], tips=[];
    arms.forEach((y,idx)=>{ const reach=2.7-idx*0.25;
      [-1,1].forEach(side=>{ const xTip=side*(w(y)+reach);
        armS.push(side*w(y),y,0.3, xTip,y,0);  armS.push(side*w(y),y,-0.3, xTip,y,0);
        armS.push(side*w(y),y-0.75,0, xTip,y,0);
        const NB=4; for(let b=1;b<NB;b++){const xb=side*w(y)+(xTip-side*w(y))*b/NB;
          armS.push(xb,y,0, xb,y-0.75*(1-b/NB),0);}
        tips.push([xTip,y]); });
    });
    g.add(segs(armS,HUD,0.8));
    const peak=[], ytop=H+1.0; for(let c=0;c<4;c++) peak.push(...cor(H,c), 0,ytop,0);
    g.add(segs(peak,HUD,0.7));
    const ins=[]; tips.forEach(([x,y])=>{ for(let k=0;k<5;k++) ins.push(x,y-k*0.18,0, x,y-(k+1)*0.18,0); });
    g.add(segs(ins,GLOW,0.7));
    return {g, tips, ytop};
  }
  function mTorreTransmision(){ // LÍNEA de transmisión: varias torres + conductores entre ellas
    clearSpin(); const g=new THREE.Group();
    const span=12, towersZ=[-span,0,span], sag=1.7;
    const data=towersZ.map(z=>{ const t=txTower(); t.g.position.z=z; g.add(t.g); return {z,tips:t.tips,ytop:t.ytop}; });
    const cond=[];
    function vano(z0,z1,x,y0){ const mid=(z0+z1)/2, half=(z1-z0)/2, N=18;
      for(let k=0;k<N;k++){ const za=z0+(k/N)*(z1-z0), zb=z0+((k+1)/N)*(z1-z0);
        const ya=y0 - sag*(1-Math.pow((za-mid)/half,2)), yb=y0 - sag*(1-Math.pow((zb-mid)/half,2));
        cond.push(x,ya,za, x,yb,zb); } }
    for(let i=0;i<data.length-1;i++){ const z0=data[i].z, z1=data[i+1].z;
      data[i].tips.forEach(([x,y])=> vano(z0,z1,x,y-0.9));   // conductores de fase
      vano(z0,z1,0,data[i].ytop-0.15);                        // cable de guarda (pico)
    }
    // la línea continúa más allá de las torres extremas (se pierde a lo lejos)
    const ext=11;
    function stub(zEnd,dir,tips){ const N=12; tips.forEach(([x,y])=>{ const ny=y-0.9;
      for(let k=0;k<N;k++){ const za=zEnd+dir*(k/N)*ext, zb=zEnd+dir*((k+1)/N)*ext;
        const ya=ny - sag*(Math.abs(za-zEnd)/ext), yb=ny - sag*(Math.abs(zb-zEnd)/ext);
        cond.push(x,ya,za, x,yb,zb); } }); }
    stub(towersZ[0],-1,data[0].tips); stub(towersZ[towersZ.length-1],1,data[data.length-1].tips);
    g.add(segs(cond,GLOW,0.4));
    return g;
  }
  function mTorreUnica(){ // UNA sola torre (para inspeccionar cada poste de la línea)
    clearSpin(); const g=new THREE.Group();
    const t=txTower(); g.add(t.g);
    g.add(ring(3,0.05,HUD,0.3,64));
    return g;
  }
  function mTorreEnfriamiento(){
    clearSpin(); const g=new THREE.Group();
    const H=13, baseR=4.2, throatR=2.3, throatY=H*0.80;
    const c=throatY/Math.sqrt(Math.pow(baseR/throatR,2)-1);
    const rAt=y=>throatR*Math.sqrt(1+Math.pow((y-throatY)/c,2));
    const NV=40;
    const prof=[]; for(let i=0;i<=NV;i++){const y=i/NV*H; prof.push(new THREE.Vector2(rAt(y),y));}
    g.add(holo(new THREE.LatheGeometry(prof,64),{fill:0.05,edge:0}));
    const ribs=[]; const MER=30;
    for(let m=0;m<MER;m++){const a=m/MER*Math.PI*2, ca=Math.cos(a), sa=Math.sin(a);
      for(let i=0;i<NV;i++){const y0=i/NV*H,y1=(i+1)/NV*H;
        ribs.push(ca*rAt(y0),y0,sa*rAt(y0), ca*rAt(y1),y1,sa*rAt(y1));}}
    g.add(segs(ribs,HUD,0.5));
    for(let i=0;i<=11;i++){const y=i/11*H; g.add(ring(rAt(y),y,GLOW,0.3,72));}
    const legs=[], NL=30, rb=rAt(0), yL=1.6;
    for(let i=0;i<NL;i++){
      const a0=i/NL*Math.PI*2, a1=(i+1)/NL*Math.PI*2, am=(i+0.5)/NL*Math.PI*2;
      const x0=Math.cos(a0)*rb, z0=Math.sin(a0)*rb, x1=Math.cos(a1)*rb, z1=Math.sin(a1)*rb;
      const xm=Math.cos(am)*rb, zm=Math.sin(am)*rb;
      legs.push(x0,yL,z0, xm,0,zm,  xm,0,zm, x1,yL,z1);
    }
    g.add(segs(legs,HUD,0.7));
    g.add(ring(rb,yL,HUD,0.6,72));
    g.add(addSteam(0,H,0,throatR*1.5,90));
    return g;
  }
  function mSubestacion(){
    clearSpin(); const g=new THREE.Group();
    const s=[]; const gx=[-5,0,5], gh=5.2, gw=2.4;
    gx.forEach(cx=>{
      s.push(...latticeColumn(cx-gw,0,gh,0.26,7));
      s.push(...latticeColumn(cx+gw,0,gh,0.26,7));
      s.push(cx-gw,gh,0, cx+gw,gh,0,  cx-gw,gh+0.55,0, cx+gw,gh+0.55,0);
      const n=12; for(let i=0;i<n;i++){const x0=cx-gw+i/n*2*gw, x1=cx-gw+(i+1)/n*2*gw;
        s.push(x0,(i%2?gh+0.55:gh),0, x1,(i%2?gh:gh+0.55),0);}
    });
    [gh-0.35,gh-0.95,gh-1.55].forEach(y=>s.push(gx[0]-gw,y,0, gx[2]+gw,y,0));
    gx.forEach(cx=>{ for(let k=0;k<6;k++) s.push(cx,gh-k*0.16,0, cx,gh-(k+1)*0.16,0); });
    g.add(segs(s,HUD,0.8));
    [-5,-2.5,2.5,5].forEach(x=> g.add(insulator(x,1.6,0,2.2)) );
    [-4,0,4].forEach(cx=> g.add(transformer(cx,4.6)) );
    const house=holo(new THREE.BoxGeometry(3,1.6,2)); house.position.set(8.2,0.8,3); g.add(house);
    const s2=[]; for(let f=1;f<3;f++) s2.push(6.7,0.8*f,4, 9.7,0.8*f,4, 6.7,0.8*f,2, 9.7,0.8*f,2);
    g.add(segs(s2,GLOW,0.4));
    g.add(ring(10,0.05,HUD,0.35,84));
    return g;
  }
  function solarTable(cx,cz,len){
    const tbl=new THREE.Group();
    const surf=new THREE.Group();
    surf.add(holo(new THREE.BoxGeometry(len,0.06,1.8),{edge:0.7}));
    const grid=[], cols=Math.round(len/0.55);
    for(let i=0;i<=cols;i++){const x=-len/2+i/cols*len; grid.push(x,0.05,-0.9, x,0.05,0.9);}
    for(let j=0;j<=3;j++){const z=-0.9+j/3*1.8; grid.push(-len/2,0.05,z, len/2,0.05,z);}
    surf.add(segs(grid,GLOW,0.5));
    surf.rotation.x=-0.5; surf.position.y=1.25; tbl.add(surf);
    const post=[], np=Math.round(len/1.8);
    for(let i=0;i<=np;i++){const x=-len/2+i/np*len; post.push(x,0,0, x,1.25,0);}
    post.push(-len/2,1.25,0, len/2,1.25,0);
    tbl.add(segs(post,HUD,0.8));
    tbl.position.set(cx,0,cz); return tbl;
  }
  function mSolar(){
    clearSpin(); const g=new THREE.Group();
    [-5.4,-1.8,1.8,5.4].forEach(z=> g.add(solarTable(0,z,11)) );
    const inv=holo(new THREE.BoxGeometry(1.8,1.3,1.3)); inv.position.set(7.5,0.65,0); g.add(inv);
    g.add(segs([6.6,1.3,0, 6.6,2.0,0, 8.4,1.3,0, 8.4,2.0,0],GLOW,0.5));
    g.add(ring(9,0.05,HUD,0.3,80));
    return g;
  }
  function building(cx,cz,w,d,floors,fh){
    const b=new THREE.Group(); const H=floors*fh;
    b.add(holo(new THREE.BoxGeometry(w,H,d),{edge:0.6,fill:0.05}).translateX(cx).translateY(H/2).translateZ(cz));
    const s=[];
    for(let f=1;f<floors;f++){const y=f*fh;
      s.push(cx-w/2,y,cz+d/2, cx+w/2,y,cz+d/2);  s.push(cx-w/2,y,cz-d/2, cx+w/2,y,cz-d/2);
      s.push(cx-w/2,y,cz-d/2, cx-w/2,y,cz+d/2);  s.push(cx+w/2,y,cz-d/2, cx+w/2,y,cz+d/2);}
    const cw=Math.round(w/0.7); for(let i=1;i<cw;i++){const x=cx-w/2+i/cw*w;
      s.push(x,0,cz+d/2, x,H,cz+d/2);  s.push(x,0,cz-d/2, x,H,cz-d/2);}
    const cd=Math.round(d/0.7); for(let i=1;i<cd;i++){const z=cz-d/2+i/cd*d;
      s.push(cx-w/2,0,z, cx-w/2,H,z);  s.push(cx+w/2,0,z, cx+w/2,H,z);}
    b.add(segs(s,HUD,0.55));
    return {grp:b,H:H};
  }
  function mEdificio(){
    clearSpin(); const g=new THREE.Group();
    const main=building(0,0,3.4,3.0,7,0.95); g.add(main.grp);
    g.add(holo(new THREE.BoxGeometry(1.9,0.9,1.7),{edge:0.6}).translateY(main.H+0.45));
    g.add(holo(new THREE.BoxGeometry(0.7,0.45,0.7)).translateX(0.8).translateY(main.H+0.22).translateZ(-0.5));
    g.add(segs([-0.8,main.H+0.9,0.4, -0.8,main.H+2.3,0.4],GLOW,0.7));
    const wing=building(3.9,0.5,2.4,2.6,3,0.95); g.add(wing.grp);
    g.add(holo(new THREE.BoxGeometry(1.8,0.5,0.7)).translateY(0.25).translateZ(1.7));
    g.add(ring(6,0.05,HUD,0.35,80));
    return g;
  }
  function mAlmacenes(){
    clearSpin(); const g=new THREE.Group();
    const w=9, d=5.5, h=3.0, pp=h+0.4;
    g.add(holo(new THREE.BoxGeometry(w,h,d),{edge:0.6,fill:0.05}).translateY(h/2));
    const s=[];
    [d/2,-d/2].forEach(z=>{ s.push(-w/2,h,z, -w/2,pp,z); s.push(w/2,h,z, w/2,pp,z); s.push(-w/2,pp,z, w/2,pp,z); });
    s.push(-w/2,pp,d/2,-w/2,pp,-d/2);  s.push(w/2,pp,d/2, w/2,pp,-d/2);
    s.push(-w/2,h*0.55,d/2, w/2,h*0.55,d/2);
    const cols=Math.round(w/1.1); for(let i=1;i<cols;i++){const x=-w/2+i/cols*w; s.push(x,h*0.55,d/2, x,h,d/2);}
    g.add(segs(s,HUD,0.65));
    const bays=6, zf=d/2+0.02, dw=1.0, dh=h*0.5, dy=0.1, door=[];
    for(let b=0;b<bays;b++){const xc=-w/2+(b+0.5)*w/bays;
      door.push(xc-dw/2,dy,zf, xc-dw/2,dh,zf);  door.push(xc+dw/2,dy,zf, xc+dw/2,dh,zf);
      door.push(xc-dw/2,dh,zf, xc+dw/2,dh,zf);  door.push(xc-dw/2,dy,zf, xc+dw/2,dy,zf);
      for(let k=1;k<3;k++) door.push(xc-dw/2,dy+(dh-dy)*k/3,zf, xc+dw/2,dy+(dh-dy)*k/3,zf);}
    g.add(segs(door,GLOW,0.6));
    const can=[], cy=h*0.6, cz2=d/2+1.1;
    can.push(-w/2,cy,d/2, w/2,cy,d/2);  can.push(-w/2,cy,cz2, w/2,cy,cz2);
    can.push(-w/2,cy,d/2,-w/2,cy,cz2);  can.push(w/2,cy,d/2, w/2,cy,cz2);
    for(let b=0;b<=bays;b++){const xc=-w/2+b*w/bays; can.push(xc,0,cz2, xc,cy,cz2);}
    g.add(segs(can,HUD,0.55));
    [[-2.6,0.6],[0,-0.8],[2.6,0.8]].forEach(([x,z])=> g.add(holo(new THREE.BoxGeometry(0.9,0.45,0.9)).translateX(x).translateY(pp+0.22).translateZ(z)) );
    const sky=[]; for(let i=-2;i<=2;i++) sky.push(i*1.6,pp+0.02,-d/2+0.7, i*1.6,pp+0.02,d/2-0.7); g.add(segs(sky,GLOW,0.35));
    g.add(holo(new THREE.BoxGeometry(2.8,1.4,1.1)).translateX(-w/2+1.4).translateY(0.7).translateZ(cz2+0.95));
    g.add(holo(new THREE.BoxGeometry(0.75,0.95,1.0)).translateX(-w/2+3.05).translateY(0.48).translateZ(cz2+0.95));
    g.add(ring(8.5,0.05,HUD,0.3,84));
    return g;
  }
  function mPresa(){
    clearSpin(); const g=new THREE.Group();
    const Hd=6, W=6.5, nx=18, ny=8, curve=1.7;
    const zMid=x=>curve*(1-(x/W)*(x/W));
    const zU=x=>zMid(x)+0.3;
    const thick=y=>0.5+2.2*(1-y/Hd);
    const zD=(x,y)=>zMid(x)-thick(y);
    const X=i=>-W+i/nx*2*W, Y=j=>j/ny*Hd;
    const up=[], dn=[], cr=[], side=[];
    for(let i=0;i<=nx;i++){const x=X(i); up.push(x,0,zU(x), x,Hd,zU(x));}
    for(let j=0;j<=ny;j++){const y=Y(j); for(let i=0;i<nx;i++) up.push(X(i),y,zU(X(i)), X(i+1),y,zU(X(i+1)));}
    for(let i=0;i<=nx;i++){const x=X(i); for(let j=0;j<ny;j++) dn.push(x,Y(j),zD(x,Y(j)), x,Y(j+1),zD(x,Y(j+1)));}
    for(let j=0;j<=ny;j++){const y=Y(j); for(let i=0;i<nx;i++) dn.push(X(i),y,zD(X(i),y), X(i+1),y,zD(X(i+1),y));}
    for(let i=0;i<=nx;i++){const x=X(i); cr.push(x,Hd,zU(x), x,Hd,zD(x,Hd)); cr.push(x,0,zU(x), x,0,zD(x,0));}
    for(let j=0;j<=ny;j++){[0,nx].forEach(i=>{const x=X(i); side.push(x,Y(j),zU(x), x,Y(j),zD(x,Y(j)));});}
    g.add(segs(up,HUD,0.75)); g.add(segs(dn,HUD,0.7)); g.add(segs(cr,GLOW,0.6)); g.add(segs(side,HUD,0.7));
    const fall=[]; for(let s=0;s<11;s++){const x=-1.6+s/10*3.2;
      for(let j=ny;j>0;j--){const y0=Y(j),y1=Y(j-1); fall.push(x,y0,zD(x,y0)-0.05, x,y1,zD(x,y1)-0.05);} }
    g.add(segs(fall,GLOW,0.45));
    g.add(addSteam(0,0.4, zD(0,0)-0.4, 3.4, 80));
    const water=holo(new THREE.PlaneGeometry(26,15),{fill:0.07,edge:0,color:GLOW});
    water.rotation.x=-Math.PI/2; water.position.set(0,Hd-0.4, zU(0)+7.5); g.add(water);
    const wg=[]; for(let i=-6;i<=6;i++){ wg.push(i*2,Hd-0.4,zU(0)+0.6, i*2,Hd-0.4,zU(0)+15);
      wg.push(-12,Hd-0.4,zU(0)+0.6+(i+6)*1.2, 12,Hd-0.4,zU(0)+0.6+(i+6)*1.2); }
    g.add(segs(wg,0x0e6b85,0.3));
    [-3.2,3.2].forEach(x=>{ const th=Hd+0.9;
      g.add(holo(new THREE.CylinderGeometry(0.42,0.42,th,16),{fill:0.05,edge:0.5}).translateX(x).translateY(th/2).translateZ(zU(x)+1.4));
      const rr=ring(0.58,0,GLOW,0.55,18); rr.position.set(x,th,zU(x)+1.4); g.add(rr);
      g.add(segs([x,Hd,zU(x)+1.4, x,Hd,zU(x)],GLOW,0.55)); });
    const ph=holo(new THREE.BoxGeometry(9,1.6,2.4)); ph.position.set(0,0.8, zD(0,0)-1.6); g.add(ph);
    const phr=[]; for(let i=1;i<6;i++){const x=-4.5+i*1.5; phr.push(x,0,zD(0,0)-2.8, x,1.6,zD(0,0)-2.8);} g.add(segs(phr,GLOW,0.4));
    g.add(ring(12,0.05,HUD,0.3,90));
    return g;
  }
  function mNuclear(){
    clearSpin(); const g=new THREE.Group();
    const R=2.6, ch=3.4, cx=-4.0;
    g.add(holo(new THREE.CylinderGeometry(R,R,ch,44),{fill:0.05,edge:0}).translateX(cx).translateY(ch/2));
    const ribs=[], MER=24;
    for(let m=0;m<MER;m++){const a=m/MER*Math.PI*2, x=Math.cos(a)*R, z=Math.sin(a)*R; ribs.push(cx+x,0,z, cx+x,ch,z);}
    g.add(segs(ribs,HUD,0.45));
    for(let i=0;i<=4;i++) g.add(ring(R,i/4*ch,HUD,0.4,44).translateX(cx));
    g.add(holo(new THREE.SphereGeometry(R,44,22,0,Math.PI*2,0,Math.PI/2),{fill:0.06,edge:0}).translateX(cx).translateY(ch));
    const dr=[]; for(let m=0;m<MER;m++){const a=m/MER*Math.PI*2, ca=Math.cos(a), sa=Math.sin(a);
      for(let i=0;i<8;i++){const p0=i/8*Math.PI/2, p1=(i+1)/8*Math.PI/2;
        dr.push(cx+ca*R*Math.cos(p0),ch+R*Math.sin(p0),sa*R*Math.cos(p0), cx+ca*R*Math.cos(p1),ch+R*Math.sin(p1),sa*R*Math.cos(p1));}}
    g.add(segs(dr,GLOW,0.35));
    const hall=holo(new THREE.BoxGeometry(4.5,2.4,2.8)); hall.position.set(0.6,1.2,2.4); g.add(hall);
    const hr=[]; for(let i=1;i<6;i++){const x=-1.65+i*0.66; hr.push(x+0.6,0,3.8, x+0.6,2.4,3.8);} g.add(segs(hr,HUD,0.4));
    const ct=mTorreEnfriamiento(); ct.scale.setScalar(0.62); ct.position.set(5.2,0,-1.2); g.add(ct);
    return g;
  }

  const MODELS={
    aerogenerador:{f:mAerogenerador,name:"Aerogenerador",type:"Central Eólica",glb:"aerogenerador.glb"},
    transmision:{f:mTorreTransmision,name:"Torre de Transmisión",type:"Líneas / Pilón",glb:"torre-transmision.glb"},
    torre1:{f:mTorreUnica,name:"Torre de Transmisión",type:"Torre / Pilón",glb:""},
    enfriamiento:{f:mTorreEnfriamiento,name:"Torre de Enfriamiento",type:"Termoeléctrica",glb:"torre-enfriamiento.glb"},
    subestacion:{f:mSubestacion,name:"Subestación",type:"Transformación",glb:"subestacion.glb"},
    solar:{f:mSolar,name:"Planta Solar",type:"Fotovoltaica",glb:"planta-solar.glb"},
    presa:{f:mPresa,name:"Presa / Hidroeléctrica",type:"Generación Hidráulica",glb:"presa.glb"},
    edificio:{f:mEdificio,name:"Oficinas CFE",type:"Administrativo",glb:"oficinas.glb"},
    almacen:{f:mAlmacenes,name:"Almacenes",type:"Logística / Bodegas",glb:"almacenes.glb"},
    nuclear:{f:mNuclear,name:"Central Nuclear",type:"Reactor + Enfriamiento",glb:"central-nuclear.glb"},
  };

  // mapeo de tipo de activo del mapa Falcon -> clave de modelo
  const TYPE2MODEL={ subestacion:'subestacion', torre:'transmision', hidro:'presa',
    eolica:'aerogenerador', solar:'solar', termo:'enfriamiento', oficina:'edificio',
    almacen:'almacen', nuclear:'nuclear' };

  function applyHolo(obj){
    obj.traverse(o=>{ if(o.isMesh){
      o.material=new THREE.MeshBasicMaterial({color:HUD,wireframe:true,transparent:true,opacity:0.55});
    }});
  }
  function fitModel(obj,target){
    let box=new THREE.Box3().setFromObject(obj); const size=new THREE.Vector3(); box.getSize(size);
    const s=target/Math.max(size.y,0.001); obj.scale.setScalar(s);
    box=new THREE.Box3().setFromObject(obj); const cc=new THREE.Vector3(); box.getCenter(cc);
    obj.position.x-=cc.x; obj.position.z-=cc.z; obj.position.y-=box.min.y;
  }

  // construye el grupo del modelo a partir de la clave (resetea spin/steam)
  function build(key){
    clearSpin();
    const m=MODELS[key]||MODELS.subestacion;
    return { group:m.f(), info:m };
  }

  // ---------- escenografía reutilizable ----------
  function buildTerrain(){
    const terrain=new THREE.Group();
    const N=44, S=80, pts=[], seg=[];
    const Hf=(x,z)=>Math.sin(x*0.25)*0.6+Math.cos(z*0.22)*0.6+Math.sin((x+z)*0.13)*0.5;
    const grid=[];
    for(let i=0;i<=N;i++){grid[i]=[];for(let j=0;j<=N;j++){
      const x=(i/N-0.5)*S, z=(j/N-0.5)*S, y=Hf(x,z)-1.8;
      grid[i][j]=new THREE.Vector3(x,y,z); pts.push(x,y,z);
    }}
    for(let i=0;i<=N;i++)for(let j=0;j<=N;j++){
      if(i<N){const a=grid[i][j],b=grid[i+1][j];seg.push(a.x,a.y,a.z,b.x,b.y,b.z);}
      if(j<N){const a=grid[i][j],b=grid[i][j+1];seg.push(a.x,a.y,a.z,b.x,b.y,b.z);}
    }
    terrain.add(segs(seg,0x0e6b85,0.35));
    const pg=new THREE.BufferGeometry(); pg.setAttribute('position',new THREE.Float32BufferAttribute(pts,3));
    terrain.add(new THREE.Points(pg,new THREE.PointsMaterial({color:GLOW,size:0.18,transparent:true,opacity:0.7})));
    return terrain;
  }
  function buildBaseRings(){
    const baseRings=new THREE.Group();
    baseRings.add(ring(4.2,-0.04,HUD,0.5)); baseRings.add(ring(5.6,-0.06,GLOW,0.25)); baseRings.add(ring(3.1,-0.02,HUD,0.35));
    return baseRings;
  }
  function buildMotes(){
    const n=120,p=[];for(let i=0;i<n;i++)p.push((Math.random()-0.5)*16,Math.random()*14-2,(Math.random()-0.5)*16);
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(p,3));
    return new THREE.Points(g,new THREE.PointsMaterial({color:GLOW,size:0.1,transparent:true,opacity:0.5}));
  }

  // ---------- visor reutilizable ----------
  function createViewer(container, opts){
    opts=opts||{};
    const scene=new THREE.Scene();
    if(opts.background!==null) scene.background=new THREE.Color(opts.background!==undefined?opts.background:0x040810);
    if(opts.fog!==false) scene.fog=new THREE.FogExp2(opts.fogColor!==undefined?opts.fogColor:0x040810, opts.fogDensity||0.02);
    const W=container.clientWidth||window.innerWidth, Hh=container.clientHeight||window.innerHeight;
    const camera=new THREE.PerspectiveCamera(50, W/Hh, 0.1, 1000);
    const cp=opts.cameraPos||[9,7,13]; camera.position.set(cp[0],cp[1],cp[2]);
    const renderer=new THREE.WebGLRenderer({antialias:true, alpha:!!opts.alpha});
    renderer.setPixelRatio(window.devicePixelRatio); renderer.setSize(W,Hh);
    container.appendChild(renderer.domElement);
    let controls=null;
    if(THREE.OrbitControls){
      controls=new THREE.OrbitControls(camera,renderer.domElement);
      controls.enableDamping=true; controls.dampingFactor=0.08;
      const tg=opts.target||[0,3,0]; controls.target.set(tg[0],tg[1],tg[2]);
      controls.maxPolarAngle=Math.PI*0.49; controls.minDistance=opts.minDistance||5; controls.maxDistance=opts.maxDistance||40;
      controls.autoRotate=!!opts.autoRotate; controls.autoRotateSpeed=opts.autoRotateSpeed||0.7;
      controls.enablePan=opts.enablePan!==false;
    }
    if(opts.terrain!==false) scene.add(buildTerrain());
    let baseRings=null;
    if(opts.rings!==false){ baseRings=buildBaseRings(); scene.add(baseRings); }
    let motes=null;
    if(opts.motes!==false){ motes=buildMotes(); scene.add(motes); }

    let current=null, token=0;
    function setCurrent(obj){ if(current) scene.remove(current); current=obj; scene.add(obj); }
    function setModel(key){
      token++; const my=token; const b=build(key); setCurrent(b.group);
      if(opts.modelsPath && MODELS[key] && MODELS[key].glb && THREE.GLTFLoader){
        new THREE.GLTFLoader().load(opts.modelsPath+MODELS[key].glb,
          (gltf)=>{ if(my!==token)return; clearSpin(); applyHolo(gltf.scene); fitModel(gltf.scene, opts.fitTarget||9); setCurrent(gltf.scene); },
          undefined, ()=>{});
      }
      return b.info;
    }
    let raf=null, running=false;
    function loop(){
      if(!running) return;
      raf=requestAnimationFrame(loop);
      const t=performance.now()*0.001;
      spin.forEach(s=>{ s.obj.rotation[s.axis]+=s.speed*0.016; });
      steam.forEach(s=>{ const p=s.m.geometry.attributes.position;
        for(let i=0;i<p.count;i++){let y=p.getY(i)+0.03; if(y>s.top)y=s.baseY; p.setY(i,y);} p.needsUpdate=true; });
      if(baseRings) baseRings.rotation.y=t*0.15;
      if(motes){ const pos=motes.geometry.attributes.position;
        for(let i=0;i<pos.count;i++){let y=pos.getY(i)+0.02; if(y>12)y=-2; pos.setY(i,y);} pos.needsUpdate=true; }
      if(controls) controls.update();
      renderer.render(scene,camera);
    }
    function resize(){
      const w=container.clientWidth||window.innerWidth, h=container.clientHeight||window.innerHeight;
      camera.aspect=w/h; camera.updateProjectionMatrix(); renderer.setSize(w,h);
    }
    function start(){ if(!running){ running=true; loop(); } }
    function stop(){ running=false; if(raf) cancelAnimationFrame(raf); }
    function dispose(){ stop(); renderer.dispose(); if(renderer.domElement.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement); }
    start();
    return { scene, camera, renderer, controls, setModel, resize, start, stop, dispose };
  }

  window.Holo={ build, createViewer, MODELS, TYPE2MODEL, applyHolo, fitModel, HUD, GLOW,
    buildTerrain, buildBaseRings, buildMotes, _spin:spin, _steam:steam };
})();
