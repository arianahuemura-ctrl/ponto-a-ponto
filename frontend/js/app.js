$('load').addEventListener('click',loadNearby);
$('reset').addEventListener('click',resetSelection);
$('address-form').addEventListener('submit',searchAddress);
$('mobile-handle').addEventListener('click',()=>setMobilePanel($('sidebar').classList.contains('collapsed')));
addEventListener('resize',syncResponsivePanel);
syncResponsivePanel();
