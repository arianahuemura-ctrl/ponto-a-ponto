const results = document.getElementById('results');
const summary = document.getElementById('summary');
let passed = 0;
let failed = 0;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function assertEqual(actual, expected, message) {
  assert(actual === expected, `${message}: esperado ${expected}, recebido ${actual}`);
}

function assertSetEqual(actual, expected, message) {
  const received = [...actual].sort();
  const wanted = [...expected].sort();
  assert(JSON.stringify(received) === JSON.stringify(wanted), `${message}: esperado [${wanted}], recebido [${received}]`);
}

function resetState() {
  state.stops.clear();
  state.routes.clear();
  state.selectedStops = [];
  state.compatibleRouteIds.clear();
  state.markers.clear();
  state.location = null;
}

function stop(key, lat, lon, routeIds, nearby = true) {
  const [type, id] = key.split(':');
  return {key, type, id: Number(id), lat, lon, tags: {name: key}, routeIds: new Set(routeIds), nearby};
}

function addRoute(id, orderedStops, geometry = []) {
  state.routes.set(id, {id, tags: {ref: id}, orderedStops, geometry});
}

function test(name, callback) {
  try {
    resetState();
    callback();
    passed++;
    results.insertAdjacentHTML('beforeend', `<span class="pass">PASS</span> ${name}\n`);
  } catch (error) {
    failed++;
    results.insertAdjacentHTML('beforeend', `<span class="fail">FAIL</span> ${name}: ${error.message}\n`);
  }
}

test('normaliza pontos e relações do Overpass', () => {
  normalizeData({elements: [
    {type: 'node', id: 1, lat: -23, lon: -46, tags: {highway: 'bus_stop', name: 'A'}},
    {type: 'node', id: 2, lat: -23, lon: -45.999, tags: {highway: 'bus_stop', name: 'B'}},
    {type: 'relation', id: 10, tags: {route: 'bus', ref: '10'}, members: [
      {type: 'node', ref: 1, role: 'stop', lat: -23, lon: -46},
      {type: 'node', ref: 2, role: 'stop', lat: -23, lon: -45.999}
    ]}
  ]});
  assertEqual(state.stops.size, 2, 'quantidade de pontos');
  assertEqual(state.routes.size, 1, 'quantidade de linhas');
  assert(state.stops.get('node:1').routeIds.has(10), 'ponto A deve pertencer à linha 10');
  assertEqual(state.routes.get(10).orderedStops.join(','), 'node:1,node:2', 'ordem dos pontos');
});

test('descobre todas as linhas que passam pelo primeiro ponto', () => {
  state.stops.set('node:1', stop('node:1', 0, 0, [10, 20]));
  state.stops.set('node:2', stop('node:2', 0, .001, [10]));
  state.stops.set('node:3', stop('node:3', 0, .002, [20]));
  addRoute(10, ['node:1', 'node:2']);
  addRoute(20, ['node:1', 'node:3']);
  assertSetEqual(compatibleRoutesForStop(state.stops.get('node:1')), new Set([10, 20]), 'linhas do ponto');
});

test('respeita a ordem dos pontos no trajeto', () => {
  state.stops.set('node:1', stop('node:1', 0, 0, [10]));
  state.stops.set('node:2', stop('node:2', 0, .001, [10]));
  state.stops.set('node:3', stop('node:3', 0, .002, [10]));
  addRoute(10, ['node:1', 'node:2', 'node:3']);
  assert(routeContainsSelectionInOrder(state.routes.get(10), ['node:1', 'node:3']), 'A -> C deve ser válido');
  assert(!routeContainsSelectionInOrder(state.routes.get(10), ['node:3', 'node:1']), 'C -> A não deve ser válido em linha linear');
});

test('encontra somente destinos possíveis da linha selecionada', () => {
  state.stops.set('node:1', stop('node:1', 0, 0, [10, 20]));
  state.stops.set('node:2', stop('node:2', 0, .001, [10]));
  state.stops.set('node:3', stop('node:3', 0, .002, [20]));
  state.stops.set('node:4', stop('node:4', 0, .003, [10]));
  addRoute(10, ['node:1', 'node:2', 'node:4']);
  addRoute(20, ['node:1', 'node:3']);
  state.selectedStops = ['node:1'];
  state.compatibleRouteIds = new Set([10, 20]);
  assertSetEqual(getPossibleNextStops(), new Set(['node:2', 'node:3', 'node:4']), 'destinos possíveis');
});

test('compara e refina linhas progressivamente', () => {
  state.stops.set('node:1', stop('node:1', 0, 0, [10, 20]));
  state.stops.set('node:2', stop('node:2', 0, .001, [10]));
  state.stops.set('node:3', stop('node:3', 0, .002, [20]));
  addRoute(10, ['node:1', 'node:2']);
  addRoute(20, ['node:1', 'node:3']);
  state.selectedStops = ['node:1', 'node:2'];
  computeCompatibleRoutes();
  assertSetEqual(state.compatibleRouteIds, new Set([10]), 'linhas após refinar A -> B');
});

test('não aceita ponto próximo pertencente a outra linha', () => {
  state.stops.set('node:1', stop('node:1', 0, 0, [10]));
  state.stops.set('node:2', stop('node:2', 0, .001, [10]));
  state.stops.set('node:3', stop('node:3', 0, .00101, [20]));
  addRoute(10, ['node:1', 'node:2']);
  state.selectedStops = ['node:1'];
  state.compatibleRouteIds = new Set([10]);
  assert(!getPossibleNextStops().has('node:3'), 'ponto da linha 20 não deve virar destino da linha 10');
});

test('preserva segmentos OSM desconectados sem achatá-los em uma linha artificial', () => {
  const route = {geometry: [
    [[0, 0], [0, .001]],
    [[0, .02], [0, .021]]
  ]};
  const segments = buildRouteSegments(route);
  assertEqual(segments.length, 2, 'quantidade de segmentos');
  assertEqual(segments[0].length, 2, 'primeiro segmento');
  assertEqual(segments[1].length, 2, 'segundo segmento');
});

summary.textContent = `${passed + failed} testes executados: ${passed} aprovados, ${failed} falhos.`;
summary.className = failed ? 'fail' : 'pass';
