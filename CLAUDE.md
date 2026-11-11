# CLAUDE.md — ReinStack

Instalador del método Rein (Python 3.11+, sin dependencias). Guía para quien contribuya.

## Leé primero

1. `AGENTS.md`: reglas de desarrollo del instalador (valen igual para Claude y Codex).
2. `templates/METODO.md`: el método que distribuimos. `README.md` y `GUIA.md` lo explican para quien lo instala.

## Cómo trabajar acá

- Este proyecto usa el propio método Rein: orquestador y constructor, aceptación escrita y congelada antes de implementar, y una historia sólo se da por terminada con aceptación explícita de la persona.
- Tests: `python3 -m unittest discover -s tests` (también con `LANG=C`). Ninguno toca el HOME real ni ejecuta clientes; todo en directorios temporales. Las versiones viejas para probar `update` viven en `tests/fixtures/`: no se editan.
- No modifiques pruebas de aceptación ya congeladas para que pase una implementación; si el contrato está mal, proponé la corrección.
- `python3 reinstack.py ...` desde el clon debe seguir funcionando igual que el comando instalado `reinstack`.
- Los textos existen en español (`templates/`) e inglés (`templates/en/`): un cambio en uno se refleja en el otro. Las plantillas viajan en el paquete como `reinstack_templates` (ver `pyproject.toml`).
- Si cambia lo que se instala, subí `VERSION` en `reinstack.py` y en `pyproject.toml` para que `update` lo detecte, y anotalo en `CHANGELOG.md`.
- Commits: conventional commits.
