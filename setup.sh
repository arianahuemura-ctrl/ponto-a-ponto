#!/usr/bin/env bash
# Instalação local do PaP. Execute como usuário normal, não com sudo.
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$ROOT"

usage() {
  cat <<'HELP'
Uso: ./setup.sh [opções]

Sem opções: prepara .venv e .env, instala dependências Python/JS, aplica
migrações, importa GTFS se o índice não existir e compila o frontend.
Requer Python >= 3.12 e Node.js da versão indicada em .nvmrc.

  --all            Instala todos os componentes abaixo na ordem das dependências.
                   Inclui administrador se ainda não houver superusuário.
  --artifacts-only Prepara/retoma artefatos usando a .venv existente, sem reinstalar.
  --rebuild-artifacts Preserva backup e força reconstrução (combine com --artifacts-only).
  --route-heuristics Gera candidatos com heurísticas em banco separado.
  --route-seconds N Limite por categoria da materialização (padrão PAP_ROUTE_SECONDS).
  --min-free-gib N Reserva de disco (padrão PAP_MIN_FREE_GIB).
  --routes         Gera todos os artefatos de rotas (incluído em --all).
  --osm-pbf FILE   Extrato OSM local; sem ele baixa Sudeste/Geofabrik se necessário.
  --system         Instala requirements.system via APT (usa sudo).
  --node           Instala/carrega nvm e instala a versão de .nvmrc.
  --gtfs-source DIR Pasta dos arquivos GTFS (padrão: fonts/sptrans_gtfs).
  --skip-gtfs      Não importa GTFS nesta execução.
  --refresh-gtfs   Reimporta GTFS, mesmo com índice existente.
  --admin          Executa createsuperuser interativamente.
  --demo           Importa as fontes e a demonstração histórica de Mauá.
  --browser        Instala Chromium e dependências para testes Playwright.
  --walking        Instala dependências Python opcionais de pré-processamento OSM.
  --dev            Instala também ferramentas Python de teste/cobertura.
  -h, --help       Exibe esta ajuda, sem instalar nada.

PYTHON_BIN pode indicar outro Python (ex.: PYTHON_BIN=python3.14 ./setup.sh).
O .env existente é preservado; tokens nunca são solicitados nem impressos.
--all também gera os artefatos de rotas de toda a cidade; pode levar muito tempo.
O início do servidor é uma etapa separada.
HELP
}
fail() { printf 'Erro: %s\n' "$*" >&2; exit 1; }
progress() {
  local percent=$((completed * 100 / total)) filled=$((completed * 30 / total)) bar rest
  printf -v bar '%*s' "$filled" ''; bar=${bar// /#}
  printf -v rest '%*s' "$((30-filled))" ''; rest=${rest// /-}
  printf '\n[%s%s] %3d%% | %d/%d etapas concluídas | %ss | %s\n' "$bar" "$rest" "$percent" "$completed" "$total" "$SECONDS" "$*"
}
step() { progress "$*"; }
done_step() { completed=$((completed+1)); progress "$* — concluído"; }
trap 'printf "Instalação interrompida na linha %s. Corrija o erro acima e execute novamente.\n" "$LINENO" >&2' ERR
route_heuristics=0; artifacts_only=0; force_artifacts=0; route_seconds=""; min_free_gib=""
routes=0; osm_pbf=""; all=0; system=0; node_install=0; skip_gtfs=0; refresh_gtfs=0; admin=0; demo=0; browser=0; walking=0; dev=0
gtfs_source="$ROOT/fonts/sptrans_gtfs"
while (($#)); do
  case "$1" in
    --all) all=1 ;;
    --routes) routes=1 ;;
    --route-heuristics) route_heuristics=1; routes=1 ;;
    --artifacts-only) artifacts_only=1; routes=1 ;;
    --rebuild-artifacts) force_artifacts=1; routes=1 ;;
    --route-seconds|--min-free-gib)
      (($# >= 2)) && [[ "$2" =~ ^[0-9]+([.][0-9]+)?$ ]] || fail "Informe um número após $1."
      if [[ "$1" == --route-seconds ]]; then route_seconds="$2"; else min_free_gib="$2"; fi
      shift ;;
    --osm-pbf)
      (($# >= 2)) && [[ -n "$2" && "$2" != --* ]] || fail "Informe um arquivo após --osm-pbf."
      osm_pbf="$2"; shift ;;
    --system) system=1 ;;
    --node) node_install=1 ;;
    --skip-gtfs) skip_gtfs=1 ;;
    --refresh-gtfs) refresh_gtfs=1 ;;
    --admin) admin=1 ;;
    --demo) demo=1 ;;
    --browser) browser=1 ;;
    --walking) walking=1 ;;
    --dev) dev=1 ;;
    --gtfs-source)
      (($# >= 2)) && [[ -n "$2" && "$2" != --* ]] || fail 'Informe a pasta após --gtfs-source.'
      gtfs_source="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) fail "Opção desconhecida: $1. Use --help." ;;
  esac
  shift
done
# Expanda após interpretar as opções para que sua ordem não desative dependências.
if ((all)); then
  ((skip_gtfs == 0)) || fail '--all e --skip-gtfs são incompatíveis.'
  routes=1; system=1; node_install=1; admin=1; demo=1; browser=1; walking=1; dev=1
fi
if ((routes)); then walking=1; fi
((routes == 0 || skip_gtfs == 0)) || fail "--routes exige a etapa GTFS."
((skip_gtfs == 0 || refresh_gtfs == 0)) || fail '--skip-gtfs e --refresh-gtfs são incompatíveis.'
((EUID != 0)) || fail 'Execute sem sudo; somente a instalação de pacotes usa elevação.'

if ((artifacts_only && (all || node_install || admin || demo || browser || dev || refresh_gtfs))); then
  fail '--artifacts-only não pode ser combinado com opções de instalação; use --routes para instalar e gerar.'
fi
run_artifacts() {
  command -v make >/dev/null || fail 'make ausente; execute ./setup.sh --system --routes.'
  PAP_SETUP_PYTHON="$ROOT/.venv/bin/python" PAP_SETUP_OSM_PBF="$osm_pbf" \
  PAP_SETUP_SECONDS="$route_seconds" PAP_SETUP_MIN_FREE_GIB="$min_free_gib" \
  PAP_SETUP_HEURISTICS="$route_heuristics" PAP_SETUP_FORCE="$force_artifacts" make --no-print-directory -f Makefile _all
}
# Cinco etapas obrigatórias: ambiente de execução, Python, Django, frontend e verificação final.
# Etapas opcionais contam apenas quando selecionadas; artefatos reutilizados contam como verificados.
completed=0
total=$((5 + system + (1-skip_gtfs) + routes + demo + browser + admin))
if ((artifacts_only)); then total=$((system+1)); fi
SECONDS=0
printf 'Progresso por etapas; não representa tempo restante.\n'
if ((system)); then
  command -v apt-get >/dev/null || fail '--system requer Debian/Ubuntu com APT.'
  command -v sudo >/dev/null || fail 'sudo não encontrado.'
  step 'Pacotes do sistema'
  mapfile -t packages < <(sed 's/#.*//; s/^[[:space:]]*//; s/[[:space:]]*$//; /^[[:space:]]*$/d' requirements.system)
  if ((routes)); then
    packages+=(build-essential cmake pkg-config libboost-all-dev libtbb-dev liblua5.4-dev libbz2-dev libexpat1-dev zlib1g-dev)
  fi
  sudo apt-get update
  sudo apt-get install -y -- "${packages[@]}"
  done_step "Pacotes do sistema"
fi

if ((artifacts_only)); then
  [[ -x "$ROOT/.venv/bin/python" ]] || fail 'Execute ./setup.sh --walking antes de gerar artefatos.'
  step 'Preparação dos artefatos'
  run_artifacts
  done_step 'Artefatos'
  exit 0
fi

step "Verificação de Python e Node.js"
python_bin=${PYTHON_BIN:-python3}
command -v "$python_bin" >/dev/null || fail 'Python não encontrado. Instale Python >= 3.12 ou use --system.'
"$python_bin" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else "Python >= 3.12 é necessário.")'
node_major=$(tr -d '[:space:]' < .nvmrc)
# nvm é uma função de shell, portanto não é herdado automaticamente pelo script.
if ((node_install)) || ! command -v node >/dev/null || [[ $(node -p 'process.versions.node.split(".")[0]') != "$node_major" ]]; then
  export NVM_DIR="${NVM_DIR:-${XDG_CONFIG_HOME:+$XDG_CONFIG_HOME/}nvm}"
  # Sem XDG_CONFIG_HOME, o diretório convencional é ~/.nvm.
  if [[ "$NVM_DIR" == nvm ]]; then export NVM_DIR="$HOME/.nvm"; fi
  if [[ ! -s "$NVM_DIR/nvm.sh" ]] && ((node_install)); then
    command -v curl >/dev/null || fail 'curl não encontrado; use --system.'
    step 'Instalação do nvm v0.40.8'
    installer=$(mktemp)
    trap 'rm -f -- "$installer"' EXIT
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.8/install.sh -o "$installer"
    PROFILE=/dev/null bash "$installer"
    rm -f -- "$installer"
    trap - EXIT
  fi
  [[ -s "$NVM_DIR/nvm.sh" ]] || fail "Node.js $node_major não encontrado. Execute novamente com --node."
  set +u
  source "$NVM_DIR/nvm.sh"
  if ((node_install)); then nvm install "$node_major"; fi
  nvm use "$node_major"
  set -u
fi
[[ $(node -p 'process.versions.node.split(".")[0]') == "$node_major" ]] || fail "Use Node.js $node_major."
command -v npm >/dev/null || fail 'npm não encontrado.'
done_step 'Python e Node.js'

step 'Ambiente Python e configuração local'
if [[ ! -d .venv ]]; then "$python_bin" -m venv .venv; fi
[[ -x .venv/bin/python ]] || fail '.venv existe, mas não contém um Python executável.'
py="$ROOT/.venv/bin/python"
"$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else "O Python de .venv precisa ser >= 3.12.")'
if ((dev)); then "$py" -m pip install -r requirements-dev.txt; else "$py" -m pip install -r requirements.txt; fi
if ((walking)); then "$py" -m pip install -r requirements-walking.txt; fi
if [[ ! -e .env ]]; then (umask 077; cp .env.example .env); fi
done_step "Ambiente Python e configuração local"

step 'Banco Django'
"$py" backend/manage.py migrate --noinput
done_step "Banco Django"
if ((!skip_gtfs)); then
  # Consulta settings do Django; não executa .env como código shell.
  exists=$("$py" -c 'import os,sys; sys.path.insert(0,"backend"); os.environ.setdefault("DJANGO_SETTINGS_MODULE","mbm.settings"); from transit.sptrans.store import database_path; print(int(database_path().is_file()))')
  if ((refresh_gtfs)) || [[ "$exists" == 0 ]]; then
    [[ -f "$gtfs_source/stops.txt" && -f "$gtfs_source/trips.txt" ]] || fail 'GTFS ausente: extraia os .txt em fonts/sptrans_gtfs, use --gtfs-source DIR ou --skip-gtfs.'
    step 'Importação do GTFS'
    "$py" backend/manage.py import_sptrans --source "$gtfs_source"
    if ((refresh_gtfs)); then printf 'GTFS reimportado. Regenere os artefatos de busca antes de reutilizá-los.\n'; fi
  else
    printf 'Índice GTFS existente preservado. Use --refresh-gtfs para reimportar.\n'
  fi
  done_step 'Índice GTFS'
fi
if ((routes)); then
  step 'Artefatos de rotas: grafo → diretas → caminhadas → componentes → materialização municipal'
  run_artifacts
  done_step "Artefatos de rotas"
fi
if ((demo)); then
  step 'Demonstração de Mauá'
  "$py" backend/manage.py import_sources --download --demo
  done_step 'Demonstração de Mauá'
fi

step 'Frontend'
export PATH="$ROOT/.venv/bin:$PATH"
npm --prefix frontend ci
npm --prefix frontend run build
done_step "Frontend"
if ((browser)); then
  step 'Chromium e dependências'
  (cd frontend && npx playwright install --with-deps chromium)
  done_step 'Chromium e dependências'
fi
step 'Verificação Django'
"$py" backend/manage.py check
done_step "Verificação Django"

# A interação ocorre por último, após preparar dependências e migrações.
if ((admin)); then
  has_admin=0
  if ((all)); then
    has_admin=$("$py" -c 'import os,sys; sys.path.insert(0,"backend"); os.environ.setdefault("DJANGO_SETTINGS_MODULE","mbm.settings"); import django; django.setup(); from django.contrib.auth import get_user_model; print(int(get_user_model().objects.filter(is_superuser=True).exists()))')
  fi
  if [[ "$has_admin" == 1 ]]; then
    printf 'Administrador existente preservado. Use --admin para criar outro.\n'
  else
    step 'Criação do administrador'
    "$py" backend/manage.py createsuperuser
  fi
  done_step 'Administrador'
fi
printf '\nInstalação concluída. Na raiz do projeto:\n  source .venv/bin/activate\n  python start_server.py\n\nAcesso: http://127.0.0.1:8000/\nConfigure SPTRANS_TOKEN no .env para habilitar consultas ao Olho Vivo.\n'
