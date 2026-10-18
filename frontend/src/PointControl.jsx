import PointIcon from './PointIcon.jsx';

export default function PointControl({kind,point,selecting=false,onClick,disabled=false}) {
  // A localização permite calcular o acesso a pé, mas não define uma parada.
  if(kind==='origin'&&point?.useLocation)point=null;
  const label=kind==='origin'?'Embarque':'Destino';
  const action=point?`Desmarcar ${label.toLowerCase()}`:`Selecionar ${label.toLowerCase()}`;
  const state=selecting?'Selecionando':point?'Definido':'Não definido';
  return <button type="button" className="icon-button sp-point-control" data-kind={kind} data-state={point?'set':'empty'} data-selecting={selecting}
    aria-label={action} aria-pressed={selecting} disabled={disabled} onClick={onClick}
    title={`${label}: ${point?.name||'não definido'} · ${state}`}>
    <span className="sp-point-symbol"><PointIcon kind={kind}/><span aria-hidden="true">{selecting?'…':point?'✓':'+'}</span></span>
    <span className="sp-point-description">{label}<small>{state}</small></span>
  </button>;
}
