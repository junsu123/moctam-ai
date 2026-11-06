(function(){
  // lọc sản phẩm theo nhóm (không có JS thì vẫn thấy đủ sản phẩm)
  var cats=document.querySelector('.cats');
  if(cats){cats.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;
    cats.querySelectorAll('button').forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});
    var c=b.getAttribute('data-cat');document.querySelectorAll('.pgrid .pc').forEach(function(p){p.hidden=!!c&&p.getAttribute('data-cat')!==c});
    if(history.replaceState)history.replaceState(null,'',c?'#'+encodeURIComponent(c):location.pathname);});
    var h=decodeURIComponent(location.hash.slice(1));if(h){var hb=cats.querySelector('button[data-cat="'+h.replace(/"/g,'')+'"]');if(hb)hb.click();}}
  // thư viện ảnh sản phẩm: vuốt, nút trước/sau, ảnh nhỏ, phóng to
  var g=document.querySelector('.gal');if(!g)return;
  var main=g.querySelector('.gal-main'),figs=[].slice.call(main.querySelectorAll('figure')),th=[].slice.call(g.querySelectorAll('.gal-thumbs a')),
      ctr=g.querySelector('.gal-ctr'),i=0,n=figs.length;
  function go(k,smooth){i=(k+n)%n;main.scrollTo({left:figs[i].offsetLeft-main.offsetLeft,behavior:smooth===false?'auto':'smooth'});mark();}
  function mark(){th.forEach(function(t,k){t.setAttribute('aria-current',k===i?'true':'false')});if(ctr)ctr.textContent=(i+1)+' / '+n;}
  var tm;main.addEventListener('scroll',function(){clearTimeout(tm);tm=setTimeout(function(){var k=Math.round(main.scrollLeft/main.clientWidth);if(k!==i){i=k;mark();}},80)});
  th.forEach(function(t,k){t.addEventListener('click',function(e){e.preventDefault();go(k)})});
  var pv=g.querySelector('.prev'),nx=g.querySelector('.next');if(pv)pv.onclick=function(){go(i-1)};if(nx)nx.onclick=function(){go(i+1)};
  var lb=document.querySelector('dialog.lb');
  if(lb&&lb.showModal){var li=lb.querySelector('img'),lc=lb.querySelector('.c');
    function show(){var im=figs[i].querySelector('img');li.src=im.getAttribute('data-full')||im.src;li.alt=im.alt;lc.textContent=(i+1)+' / '+n;}
    figs.forEach(function(f,k){f.querySelector('img').addEventListener('click',function(){i=k;show();lb.showModal();})});
    lb.querySelector('.x').onclick=function(){lb.close()};
    lb.querySelector('.p').onclick=function(){i=(i-1+n)%n;show()};lb.querySelector('.n').onclick=function(){i=(i+1)%n;show()};
    lb.addEventListener('click',function(e){if(e.target===lb)lb.close()});
    lb.addEventListener('close',function(){go(i,false)});
    document.addEventListener('keydown',function(e){if(!lb.open)return;if(e.key==='ArrowLeft'){i=(i-1+n)%n;show()}if(e.key==='ArrowRight'){i=(i+1)%n;show()}});}
  mark();
})();
