"""Custos exatos em terços; não alteram tempos nem o número físico de trocas."""
RAIL_MODES = ('metro', 'rail')


def annotate(journey):
    legs = journey.get('legs', [])
    walks = journey.get('walks', journey.get('transfer_walks', []))
    internal = 0
    for i, (previous, following) in enumerate(zip(legs, legs[1:]), 1):
        between = [w for w in walks if w.get('before_leg') == i]
        same_stop = previous.get('destination', {}).get('id') == following.get('origin', {}).get('id')
        if (previous.get('mode') in RAIL_MODES and following.get('mode') in RAIL_MODES
                and (between or same_stop)
                and all(w.get('internal_transfer') for w in between)):
            internal += 1
    transfers = max(0, len(legs) - 1)
    units = 3 * transfers - 2 * internal
    return {**journey, 'transfers': transfers, 'transfer_cost_units': units,
            'transfer_cost': units / 3, 'internal_rail_transfers': internal}


def select(journeys, ceiling=4):
    annotated = [annotate(j) for j in journeys]
    transport = [j for j in annotated if j.get('legs') and j['transfer_cost_units'] <= ceiling * 3]
    minimum = min((j['transfer_cost_units'] for j in transport), default=None)
    maximum = min(ceiling * 3, minimum + 3) if minimum is not None else ceiling * 3
    walks = sorted((j for j in annotated if not j.get('legs')),
                   key=lambda j:(j.get('duration_minutes',float('inf')),j.get('walking_meters',0)))[:1]
    selected = sorted((j for j in transport if j['transfer_cost_units'] <= maximum),
                      key=lambda j:(j['transfer_cost_units'],j.get('duration_minutes',float('inf')),
                                    j.get('walking_meters',0),j.get('id','')))[:5-len(walks)]
    selected += walks
    return selected, {'unit': 'third', 'ceiling': ceiling, 'extra_over_minimum': 1, 'max_routes': 5,
                      'minimum_found': minimum / 3 if minimum is not None else None,
                      'maximum_allowed': maximum / 3, 'internal_rail_weight': 1 / 3}
