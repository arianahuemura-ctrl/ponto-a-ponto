// Recebe minutos; arredonda apenas na apresentação, preservando os cálculos.
export function humanDuration(minutes) {
  if (minutes == null || !Number.isFinite(Number(minutes))) return '—';
  const total = Math.max(0, Math.round(Number(minutes) * 60));
  const hours = Math.floor(total / 3600);
  const mins = Math.floor(total % 3600 / 60);
  const seconds = total % 60;
  return [hours && `${hours} h`, mins && `${mins} min`, seconds && `${seconds} s`].filter(Boolean).join(' ') || '0 min';
}
