/* Restore the recorded root theme after rrweb rebuilds the document on seek. */
window.papReplayTheme = function(player, events) {
  const changes=[];let rootId=null;
  function root(node){if(node?.tagName==='html')return node;for(const child of node?.childNodes||[]){const found=root(child);if(found)return found;}return null;}
  for(const event of events){
    if(event.type===2){const html=root(event.data.node);rootId=html?.id;changes.push({time:event.timestamp,theme:html?.attributes?.['data-theme']??null});}
    if(event.type===3&&event.data.source===0){for(const item of event.data.attributes||[]){if(item.id===rootId&&Object.hasOwn(item.attributes,'data-theme'))changes.push({time:event.timestamp,theme:item.attributes['data-theme']});}}
  }
  const replayer=player.getReplayer();let frame;
  function apply(){
    const time=replayer.getMetaData().startTime+replayer.getCurrentTime();let theme;
    for(const change of changes){if(change.time>time)break;theme=change.theme;}
    const html=replayer.iframe?.contentDocument?.documentElement;
    if(!html||theme===undefined)return;
    if(theme===null)html.removeAttribute('data-theme');else if(html.getAttribute('data-theme')!==theme)html.setAttribute('data-theme',theme);
  }
  function schedule(){cancelAnimationFrame(frame);frame=requestAnimationFrame(apply);}
  player.addEventListener('ui-update-current-time',schedule);
  for(const event of ['fullsnapshot-rebuilded','event-cast','pause','start'])replayer.on(event,schedule);
  schedule();
};
