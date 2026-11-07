# setup.sh é o ponto de entrada público; as dependências usam a procedência dos bancos.
# As verificações PHONY são intencionais: datas de modificação não validam os metadados SQLite.
.DEFAULT_GOAL := help
.PHONY: help _graph _direct _walks _components _all
help:
	@printf '%s\n' 'Use ./setup.sh --all or ./setup.sh --artifacts-only.'
_direct: _graph
_walks: _direct
_components: _walks
_all: _components
_graph _direct _walks _components _all:
	@test -n "$${PAP_SETUP_PYTHON:-}" || { echo 'Execute pelo setup.sh.' >&2; exit 1; }
	@set -eu; set --; \
	if [ -n "$${PAP_SETUP_OSM_PBF:-}" ]; then set -- "$$@" --osm-pbf "$$PAP_SETUP_OSM_PBF"; fi; \
	if [ '$@' = '_graph' ] && [ "$${PAP_SETUP_FORCE:-0}" = 1 ]; then set -- "$$@" --force; fi; \
	if [ -n "$${PAP_SETUP_SECONDS:-}" ]; then set -- "$$@" --seconds "$$PAP_SETUP_SECONDS"; fi; \
	if [ -n "$${PAP_SETUP_MIN_FREE_GIB:-}" ]; then set -- "$$@" --min-free-gib "$$PAP_SETUP_MIN_FREE_GIB"; fi; \
	if [ "$${PAP_SETUP_HEURISTICS:-0}" = 1 ]; then set -- "$$@" --experimental; fi; \
	"$$PAP_SETUP_PYTHON" backend/manage.py prepare_sptrans_artifacts \
	  --until '$(patsubst _%,%,$@)' "$$@"
