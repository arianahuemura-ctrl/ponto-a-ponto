export const NOTICE_VERSION='research-v6-voluntary';
export const CHOICE_KEY='pap.research.choice';
export function validChoice(value){
  return !!value&&value.version===NOTICE_VERSION&&['accepted','declined'].includes(value.state)&&typeof value.decidedAt==='string'&&Number.isFinite(Date.parse(value.decidedAt));
}
export function readChoice(){try{const value=JSON.parse(localStorage.getItem(CHOICE_KEY));return validChoice(value)?value:null;}catch{return null;}}
export function writeChoice(state){
  const choice={state,version:NOTICE_VERSION,decidedAt:new Date().toISOString()};
  let saved=false;try{localStorage.setItem(CHOICE_KEY,JSON.stringify(choice));saved=true;}catch{/* explicit decision remains in memory */}
  return {choice,saved};
}
