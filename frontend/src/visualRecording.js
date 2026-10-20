import {record as rrrecord} from 'rrweb';
import {trace} from './usability.js';
let stop;
export function startVisualRecording(){
  if(stop)return;
  stop=rrrecord({emit:event=>trace('visual',event),recordCanvas:true,
    sampling:{canvas:5,mousemove:50,scroll:100},inlineStylesheet:true,inlineImages:true,
    maskInputOptions:{password:true},blockSelector:'[data-private],input[type="password"]',
    dataURLOptions:{type:'image/webp',quality:0.8}});
  trace('visual_config',{library:'rrweb',canvasFps:5,mouseIntervalMs:50,inlineImages:true});
}
export function stopVisualRecording(){stop?.();stop=null;}
