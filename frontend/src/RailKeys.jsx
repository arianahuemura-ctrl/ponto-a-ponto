import {railColor,railLabel,railKeys} from './railStyle.js';

export default function RailKeys({routes}){
  return railKeys(routes).map(line=><span key={railLabel(line)} className="sp-rail-key" style={{'--sp-line-color':railColor(line)}}>{railLabel(line)}</span>);
}
