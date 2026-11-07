import boardingPointDarkIcon from './assets/boarding-point-dark.svg';
import boardingPointIcon from './assets/boarding-point.png';
import destinationPointIcon from './assets/destination-point.png';

export default function PointIcon({kind}) {
  return <><img className="sp-point-control-image" src={kind==='origin'?boardingPointIcon:destinationPointIcon} alt=""/><img className="sp-point-dark-image" src={boardingPointDarkIcon} alt="" hidden={kind!=='origin'}/></>;
}
