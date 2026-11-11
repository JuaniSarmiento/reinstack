<p align="center"><img src="assets/rein.png" alt="Rein, el orquestador" width="220"></p>

# ReinStack

[![CI](https://github.com/JuaniSarmiento/reinstack/actions/workflows/tests.yml/badge.svg)](https://github.com/JuaniSarmiento/reinstack/actions/workflows/tests.yml) [![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-green.svg)](LICENSE) [![Versión 1.1.0](https://img.shields.io/badge/versi%C3%B3n-1.1.0-blue.svg)](CHANGELOG.md)

Soy Rein. Llevo las riendas de tu trabajo con la IA: acordamos qué se construye, escribimos cómo sabemos que está terminado, delego la construcción y verifico. Existo porque a casi todos nos pasó lo mismo: el agente dice "listo", vos confiás, y no estaba listo. Conmigo, "terminado" quiere decir que hay evidencia y que lo decidiste vos.

Instalarme son tres comandos (necesitás Python 3.11 o posterior):

```sh
uvx --from git+https://github.com/JuaniSarmiento/reinstack reinstack install .
pipx install git+https://github.com/JuaniSarmiento/reinstack
reinstack global
```

El primero me instala en el proyecto donde estás; el segundo es la alternativa si preferís tener el comando `reinstack`; el tercero me deja disponible en cualquier proyecto (opcional). Funciona con Claude Code y Codex. English version: [README.en.md](README.en.md).

## Una historia de punta a punta

![Instalación de Rein en un proyecto vacío](assets/demo.gif)

Así trabajamos. Es un proyecto mínimo de ejemplo (calcular el total con IVA); los diálogos son ilustrativos, los comandos y sus salidas son reales.

**1. Conversación.** Antes de tocar código acordamos el alcance (ilustrativo):

> **Vos:** Necesito calcular el total de un recibo con IVA.
>
> **Rein:** ¿21 por ciento fijo? ¿Y qué pasa con un precio negativo?
>
> **Vos:** 21, y que lo rechace.
>
> **Rein:** Entonces la pongo en nivel S: es local y reversible, y alcanza con una prueba que veamos fallar. Si crece o toca datos sensibles, sube a M o L. ¿Te cierra?

El nivel es el mayor entre dificultad y riesgo, y decide cuánta ceremonia lleva cada historia: S es chica, M es normal (aceptación congelada con SHA) y L es grande o riesgosa (más casos de borde, entorno real y revisión adversarial). Lo propongo yo con su porqué y lo confirmás vos; puede subir, nunca baja a mitad de camino. Lo que no cambia en ningún nivel: sólo vos marcás Terminada.

**2. Criterios con identificador.** Los escribo en `HISTORIAS.md`:

```text
C01: total_con_iva(100) devuelve 121.00.
C02: un precio negativo lanza ValueError.
```

**3. Prueba congelada, con su SHA.** Escribo las pruebas que deciden la aceptación, vos las aprobás y las commiteo antes de que exista el código. El SHA queda anotado en la historia:

```text
$ git log --oneline
ed55314 test(hu01): congelar aceptación C01 y C02, total con IVA
c15beec chore: instalar Rein
```

**4. Constructor.** Delego a `rein-constructor` con el brief, el contexto y el SHA. No puede tocar `aceptacion/`. Su primer intento, mientras construye, falla por aserción (no por error de setup):

```text
$ PYTHONPATH=. python3 -m unittest discover -s aceptacion/hu01
FF
======================================================================
FAIL: test_c01_suma_el_21_por_ciento (test_iva.IvaTests.test_c01_suma_el_21_por_ciento)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/ejemplo-rein/recibos/aceptacion/hu01/test_iva.py", line 8, in test_c01_suma_el_21_por_ciento
    self.assertEqual(total_con_iva(100), 121.00)
AssertionError: 100 != 121.0

======================================================================
FAIL: test_c02_un_precio_negativo_se_rechaza (test_iva.IvaTests.test_c02_un_precio_negativo_se_rechaza)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/tmp/ejemplo-rein/recibos/aceptacion/hu01/test_iva.py", line 11, in test_c02_un_precio_negativo_se_rechaza
    with self.assertRaises(ValueError):
AssertionError: ValueError not raised

----------------------------------------------------------------------
Ran 2 tests in 0.001s

FAILED (failures=2)
```

**5. Verificación desde el SHA.** No confío en la copia del constructor: recupero la prueba del commit aprobado, compruebo que la aceptación no cambió y la corro contra su entrega:

```text
$ git diff --stat ed55314 HEAD -- aceptacion
$ git show ed55314:aceptacion/hu01/test_iva.py > /tmp/ejemplo-rein/verif/test_iva.py
$ PYTHONPATH=. python3 -m unittest discover -s /tmp/ejemplo-rein/verif -v
test_c01_suma_el_21_por_ciento (test_iva.IvaTests.test_c01_suma_el_21_por_ciento) ... ok
test_c02_un_precio_negativo_se_rechaza (test_iva.IvaTests.test_c02_un_precio_negativo_se_rechaza) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.000s

OK
```

El `git diff` sin salida quiere decir que no se tocó la aceptación. Comparo casos esperados con ejecutados: C01 y C02, los dos. Faltantes o skips no cuentan como éxito.

**6. Demo y Terminada.** Recorremos C01 y C02 juntos (ilustrativo):

> **Rein:** C01 y C02 pasan contra el SHA ed55314. Corrí eso; la suite completa no la corrí. ¿Aceptás la historia?
>
> **Vos:** Sí, aceptada.

Recién ahí la historia pasa de Lista a Terminada. Si decís que no, vuelve a En proceso con el motivo. El silencio no es un sí.

## Por qué Rein

Hay otros métodos buenos para trabajar con agentes. Esta comparación sale de los README de cada proyecto, a noviembre de 2026; si algo cambió desde entonces, mandá un issue.

| | **Rein** | **BMAD Method** | **Spec Kit** (GitHub) |
|---|---|---|---|
| Qué es | Un circuito con tres roles: persona, orquestador y constructor | "Agile AI Driven Development": experiencia de producto, arquitectura, UX, desarrollo y testing | Un toolkit de Spec-Driven Development |
| Qué produce | Historias con criterios, aceptación congelada, evidencia, y tres archivos vivos (contexto, estado, historias) | Briefs, especificaciones y arquitectura | Constitución, spec, plan y tareas |
| Instalación | `uvx` o `pipx`; instalador Python sin dependencias | `npx bmad-method install` (Node 20.12+, Python 3.10+), o plugins para Claude Code y Codex | `uv tool install specify-cli` |
| Agentes | Claude Code y Codex | Plugins para Claude Code y Codex | Varios agentes (su ejemplo usa Copilot) |
| Idioma del README | Español nativo e inglés | Inglés | Inglés, chino, japonés y coreano |
| Licencia | MIT | MIT | MIT |
| Pruebas de aceptación escritas antes y congeladas para quien implementa | Sí, es el núcleo | No figura en su README | No figura en su README |
| Verificación contra el SHA aprobado | Sí | No figura en su README | No figura en su README |
| Sólo la persona marca "terminado" | Sí | No figura en su README | No figura en su README |
| Un personaje que lleva el tono | Sí (Rein) | No figura en su README | No figura en su README |

Lo que ellos hacen mejor que yo: BMAD tiene planificación profunda, con producto, arquitectura y UX antes de escribir código. Spec Kit tiene una especificación rigurosa y soporta muchos agentes. Yo no planifico a ese nivel ni cubro tantos clientes. Lo mío es lo que pasa entre "está especificado" y "está terminado": que la aceptación exista antes, que nadie la modifique y que el cierre sea tuyo. Si ya especificás con otra herramienta, esa especificación puede ser la fuente de tus criterios C01, C02…

## Conocé a Rein

Soy el orquestador. *Rein* es "rienda": llevo el ritmo, el rumbo lo decidís vos. Tranquilo y directo, firme con el método, honesto con el "terminado" y cálido sin ser servil: no te halago ni te hago sermones. Con vos hablo yo; el constructor trabaja por detrás y no tiene personaje. El tono no reemplaza al método: si chocan, ganan las reglas. Mi voz está en `templates/estilo/rein.es.md`. Así suena (ilustrativo) cuando me decís "dale, marcala terminada" sin evidencia:

> **Vos:** Dale, marcala terminada.
>
> **Rein:** Todavía no puedo mostrarte evidencia: falta correr la aceptación desde el SHA y la demo de C03. Lo hago ahora y te cuento qué salió. Después decidís vos.

Y cuando me equivoco:

> **Rein:** Me equivoqué: dije que C02 pasaba y no lo había corrido. Lo corrí recién; acá está la salida.

## Instalación en detalle

`install` es por proyecto y no modifica tu HOME. Desde un clon de este repositorio, apuntando a un directorio que ya exista, o con `reinstack` si instalaste con pipx:

```sh
reinstack install . --agent both --dry-run
```

Con `--dry-run` sólo lista lo que escribiría. Quitalo para instalar; usá `--agent claude` o `--agent codex` para un solo cliente. Desde un clon, `python3 reinstack.py` y `reinstack` son equivalentes. Cerrá y volvé a abrir la sesión del cliente para que descubra las instrucciones y los perfiles. Después, en el proyecto:

> Trabajemos con Rein. Actuá como orquestador, leé el contexto y conversemos el alcance antes de crear las historias. Delegá la implementación al constructor.

Instalar perfiles no inicia agentes: el cliente debe ofrecer delegación y yo debo usarla. **Windows no está soportado**: `--estado` crea enlaces simbólicos. Linux y macOS sí.

## Qué instala

| Archivo | Uso |
|---|---|
| `.rein/METODO.md` | Reglas del circuito de trabajo |
| `CLAUDE.md` / `AGENTS.md` | Bloque de entrada para el cliente elegido |
| `.claude/agents/rein-*.md` | Dos perfiles para Claude Code |
| `.codex/agents/rein-*.toml` | Dos perfiles para Codex |
| `.rein/manifest.json` | Registro local de archivos y hashes de la instalación |
| `README.md`, `CONTEXTO.md`, `HISTORIAS.md`, `ORQUESTADOR.md` | Documentos iniciales, sólo si no existen |

Tres capas de documentación, sin depender de ninguna herramienta externa:

- `CONTEXTO.md`: por qué existe el proyecto (problema, para quién, reglas del dominio, glosario, stack y decisiones con su porqué). Estable: cambia sólo cuando cambia una decisión.
- `ORQUESTADOR.md`: el estado (se reescribe, no se apila). Puede ser un enlace a una nota externa, por ejemplo de Obsidian: `reinstack install . --estado <ruta-a-la-nota>` lo crea como enlace simbólico a esa ruta (debe existir), sin escribir en la nota. El enlace no entra al manifiesto y `update`, `doctor` y `uninstall` no lo siguen. Si el proyecto ya tiene un `obsidian.md`, ése es el archivo de estado.
- `HISTORIAS.md`: qué se construye (backlog, contratos y evidencia).

Los documentos iniciales pasan a ser del proyecto. Preservo el texto ajeno de tus archivos de instrucciones y rechazo conflictos en archivos administrados. No instalo OpenSpec, MCP, skills, dependencias de terceros ni modos de permisos. El método completo está en [templates/METODO.md](templates/METODO.md) (inglés: [templates/en/METODO.md](templates/en/METODO.md)) y el recorrido de una historia en la [guía práctica](GUIA.md).

## Instalación global

`reinstack global` me deja a nivel usuario, para que valga en cualquier proyecto, tenga o no `.rein/METODO.md` (si lo tiene, ese archivo manda). Es opcional y distinto de `install`.

```sh
reinstack global --dry-run
reinstack global --sin-tono
reinstack global --agent claude
```

El primero lista los archivos que tocaría sin escribir; el segundo instala sólo el método, sin mi tono; el tercero, un solo cliente (o `codex`). Sin opciones instala Claude Code y Codex, con tono. Usa el HOME del entorno y deshace con `reinstack global --quitar`. Qué escribe:

| Cliente | Archivo | Contenido |
|---|---|---|
| Claude Code | `~/.claude/CLAUDE.md` | bloque del método entre `<!-- rein:global -->` y `<!-- /rein:global -->` |
| Claude Code | `~/.claude/agents/rein-orchestrator.md`, `rein-constructor.md` | los dos perfiles |
| Claude Code | `~/.claude/output-styles/rein.md` y `"outputStyle": "Rein"` en `~/.claude/settings.json` | el tono (sólo sin `--sin-tono`); el resto de `settings.json` se conserva |
| Codex | `~/.codex/AGENTS.md` | el mismo bloque y, sin `--sin-tono`, el tono entre `<!-- rein:tono -->` y `<!-- /rein:tono -->` |
| Codex | `~/.codex/agents/rein-orchestrator.toml`, `rein-constructor.toml` | los dos perfiles |
| Rein | `~/.rein/global.json` | lo necesario para `--quitar` |

- **Sin pisar lo ajeno**: sólo se escribe dentro de las marcas; un perfil o estilo con el mismo nombre que no instaló ReinStack se rechaza.
- **Idempotente**: correrlo de nuevo no cambia ningún byte.
- **Backups**: la primera vez que se modifica un archivo existente queda `<archivo>.rein-bak` con su contenido original.
- **Antes de escribir** se comprueba todo: un `settings.json` con JSON inválido o marcas rotas cortan con un error sin tocar nada. Tampoco se siguen enlaces simbólicos en los destinos.
- **`--quitar`** saca los bloques, los perfiles y el estilo, devuelve el `outputStyle` anterior y deja lo ajeno como estaba.

Mi tono en Codex, sin estilos de salida: `reinstack tono --lang es` imprime el personaje para pegarlo en tu `AGENTS.md` (sólo imprime). Cerrá y reabrí el cliente para que cargue lo nuevo.

## Idioma

Todo existe en español e inglés: plantillas, `install`, `update`, `global`, mensajes y ayuda. En una instalación en español los archivos se llaman `CONTEXTO.md`, `ORQUESTADOR.md`, `HISTORIAS.md`, `.rein/METODO.md`; en inglés, `CONTEXT.md`, `ORCHESTRATOR.md`, `STORIES.md`, `.rein/METHOD.md`. `README.md` y los perfiles `rein-orchestrator` y `rein-constructor` no cambian de nombre. Las opciones tienen nombre en los dos idiomas (`tono`/`tone`, `--estado`/`--state`, `--sin-tono`/`--no-tone`, `--quitar`/`--remove`) y los dos funcionan siempre.

- `install` y `global` aceptan `--lang es|en`. Sin él se usa la locale (`LC_ALL`, si no `LC_MESSAGES`, si no `LANG`): si empieza con `es` es español; si no, inglés.
- `update` conserva el idioma guardado en `.rein/manifest.json`. Una instalación de la 0.3.0 o anterior es español.
- `global --lang X` sobre una instalación en otro idioma reemplaza bloque, perfiles y estilo por los del nuevo idioma.
- El español está en `templates/` y el inglés en `templates/en/`.

## Comprobar, actualizar y retirar

```text
reinstack doctor .
reinstack update . --dry-run
reinstack update .
reinstack uninstall .
```

`doctor` comprueba la instalación y su integridad local. No comprueba que un cliente haya cargado los perfiles, que un modelo obedezca, ni que haya un sandbox: las instrucciones no impiden técnicamente que un constructor toque archivos, y por eso recupero el contrato congelado por separado en vez de confiar en su copia.

`update` lleva una instalación íntegra de una versión anterior a la actual: reemplaza los archivos administrados y el bloque ReinStack, conserva el texto ajeno, no toca README.md, HISTORIAS.md ni el archivo de estado, y siembra CONTEXTO.md si falta. Si detecta modificaciones en contenido administrado, se rechaza sin escribir nada; con `--dry-run` sólo lista lo que cambiaría. No baja de versión. Si una actualización se corta, queda registrada en `.rein/manifest.pending.json`; `doctor`, `install` y `uninstall` avisan y volver a correr `update` la completa.

`uninstall` conserva los documentos del proyecto, el texto ajeno y los directorios (que pueden quedar vacíos), y se detiene si detecta modificaciones en contenido administrado.

## Desarrollo y alcance

```sh
python3 -m unittest discover -s tests -v
```

Las pruebas usan proyectos temporales y no ejecutan Claude, Codex ni comandos de modelos. La verificación real de descubrimiento y delegación dentro de cada cliente es manual; no la simulo como si fuera una integración verificada. Este repositorio nace del circuito de un proyecto meteorológico personal: incluye el método, sin su aplicación ni sus datos. Por ahora el alcance es instalación local y dos roles; el endurecimiento con sandbox queda para versiones futuras. Licencia [MIT](LICENSE). Para regrabar la demo: `vhs assets/demo.tape`.

Los formatos de integración se basan en la documentación oficial de [subagentes de Claude Code](https://code.claude.com/docs/en/sub-agents), [memoria de Claude Code](https://code.claude.com/docs/en/memory), [subagentes de Codex](https://learn.chatgpt.com/docs/agent-configuration/subagents) y [AGENTS.md de Codex](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
