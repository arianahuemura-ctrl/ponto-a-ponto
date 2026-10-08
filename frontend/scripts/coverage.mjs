import {spawnSync} from 'node:child_process';

const run = (file, args, env) => spawnSync(process.execPath, [file, ...args], {stdio:'inherit', env});
const measured = run('node_modules/nyc/bin/nyc.js', ['playwright', 'test', ...process.argv.slice(2)],
  {...process.env, PAP_COVERAGE:'1'});
// Nunca deixe o frontend servido pelo Django instrumentado, mesmo após falhas nos testes.
const restored = run('node_modules/vite/bin/vite.js', ['build'], {...process.env, PAP_COVERAGE:'0'});
process.exitCode = measured.status ?? 1;
if (restored.status !== 0) process.exitCode = restored.status ?? 1;
