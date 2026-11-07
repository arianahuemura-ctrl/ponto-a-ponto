export function transferCostLabel(trip){
  const units=trip.transfer_cost_units??Math.round((trip.transfer_cost??trip.transfers??0)*3);
  const whole=Math.floor(units/3),fraction=['','⅓','⅔'][units%3];
  return `${whole||!fraction?whole:''}${fraction}`;
}

export function withinTransferPolicy(trip,policy){
  if(!trip||!policy||policy.maximum_allowed==null)return true;
  const units=trip.transfer_cost_units??Math.round((trip.transfer_cost??trip.transfers??0)*3);
  return units<=Math.round(policy.maximum_allowed*3);
}
