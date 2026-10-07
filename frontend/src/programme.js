// Adjacent minute-based GTFS windows may end at :45 and resume at :46.
export function mergeProgramme(windows=[]) {
  return windows.reduce((result, window)=>{
    const previous=result.at(-1);
    const gap=Date.parse(window.start)-Date.parse(previous?.end);
    if(previous?.kind==='frequency'&&window.kind==='frequency'
      &&previous.interval_minutes===window.interval_minutes&&gap>=0&&gap<=60000) {
      previous.end=window.end;
    } else result.push({...window});
    return result;
  },[]);
}
