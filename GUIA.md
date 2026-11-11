# Una historia con Rein

## Conversación inicial

La persona cuenta qué necesita. El orquestador cuestiona ambigüedades, revisa restricciones reales y propone un primer alcance útil. Se acuerdan el stack y las historias principales sin diseñar cada detalle futuro. Esa conversación es la historia 0: el orquestador deja el porqué del proyecto en CONTEXTO.md (problema, para quién, qué es y qué no, reglas del dominio, glosario, stack y decisiones con su porqué). En un proyecto existente lo escribe leyendo el código y preguntando lo que no pueda deducir. El README guarda cómo ejecutar y las decisiones vigentes.

## Un brief suficiente

La historia vive en HISTORIAS.md, por ejemplo:

```md
### HU01 — Guardar mi primer lugar
Estado: Pendiente
Nivel y porqué: M; lógica nueva con persistencia, sin datos sensibles
Dificultad: Media
Riesgo: Bajo; datos personales locales

Objetivo: marcar un lugar en el mapa y recuperarlo al volver a entrar.
Incluye: mapa ejecutable, selección, nombre y persistencia.
No incluye: compartir, notificaciones ni múltiples usuarios.

C01: al marcar un punto y guardarlo con nombre, aparece ese lugar.
C02: al recargar, el lugar y su nombre siguen disponibles.
C03: un nombre vacío informa el problema y no crea un lugar.

Aceptación: pendiente de preparar y aprobar.
SHA aprobado: pendiente; no delegar todavía.
Casos esperados: C01, C02, C03.
Comando: pendiente según el stack.
Demo: marcar, nombrar, guardar, recargar y probar nombre vacío.
```

El nivel (S, M o L) es el mayor entre dificultad y riesgo y decide la ceremonia: el orquestador lo propone con su porqué y la persona lo confirma. Si la historia crece, sube; nunca baja.

Una historia inicial también incluye cómo arrancar el proyecto y cómo ejecutar su verificación. Las capas se construyen juntas en función del comportamiento; no son tres historias separadas.

## Preparar el contrato

El orquestador escribe pruebas desde C01–C03 sin mirar una implementación todavía inexistente. Se revisan con la persona. Después de aprobarlas, se hace un commit de aceptacion/hu01/ y se registra el SHA completo, comando y casos esperados.

La aprobación del alcance no sustituye la aprobación de un contrato que todavía no existe. El orquestador presenta lo concreto que necesita aprobación y continúa todo el trabajo independiente que pueda hacer.

## Delegar y construir

El constructor recibe la historia lista, rutas a contexto vigente, contrato y límites. Lee el código necesario, implementa, escribe pruebas de apoyo y verifica el cambio de forma focalizada. Si el problema exige cambiar el alcance o el contrato, lo devuelve al orquestador para decidirlo con la persona.

El constructor entrega evidencia, no un “listo” sin sustento. No ejecuta la suite completa ni determina que su propia historia quedó aceptada.

## Verificar y demostrar

El orquestador recupera la aceptación del SHA aprobado en otro entorno y la corre contra la entrega. Comprueba que se ejecutaron exactamente los casos acordados y las regresiones necesarias. Si hace falta una suite completa, la corre la persona y se registra su evidencia.

El estado Lista indica que hay una entrega para revisar; debe decir qué se verificó y qué falta. La demo recorre C01, C02 y C03. Con resultado objetivo correcto y un sí explícito de la persona, pasa a Terminada. Si dice que no, vuelve a En proceso con el motivo.

## Sesión de demos

Cuando hay dos historias en Lista, el orquestador frena la construcción nueva y propone revisarlas juntas. Por cada una muestra el guion, qué se verificó y qué falta, y la persona decide en el momento: Terminada, de vuelta a En proceso con motivo, o a Pendiente con motivo si prefiere postergarla. Así las entregas no se acumulan esperando un cierre que nunca llega.

## Instalación global

`reinstack global` deja Rein a nivel usuario, para que valga en cualquier proyecto, tenga o no `.rein/METODO.md` (si lo tiene, ese archivo manda). Es opcional y distinto de `install`, que es por proyecto.

```sh
python3 reinstack.py global --dry-run      # lista los archivos que tocaría, no escribe
python3 reinstack.py global                # Claude Code y Codex, con tono (idioma: --lang es|en)
python3 reinstack.py global --sin-tono     # sólo el método
python3 reinstack.py global --agent claude # o codex: sólo ese cliente
python3 reinstack.py global --quitar       # deshace lo que instaló
```

Usa el HOME del entorno. Qué escribe:

| Cliente | Archivo | Contenido |
|---|---|---|
| Claude Code | `~/.claude/CLAUDE.md` | bloque del método entre `<!-- rein:global -->` y `<!-- /rein:global -->` |
| Claude Code | `~/.claude/agents/rein-orchestrator.md`, `rein-constructor.md` | los dos perfiles |
| Claude Code | `~/.claude/output-styles/rein.md` y `"outputStyle": "Rein"` en `~/.claude/settings.json` | el tono (sólo sin `--sin-tono`); el resto de `settings.json` se conserva |
| Codex | `~/.codex/AGENTS.md` | el mismo bloque del método y, sin `--sin-tono`, el tono entre `<!-- rein:tono -->` y `<!-- /rein:tono -->` |
| Codex | `~/.codex/agents/rein-orchestrator.toml`, `rein-constructor.toml` | los dos perfiles |
| Rein | `~/.rein/global.json` | lo necesario para `--quitar` (outputStyle anterior, hashes de lo instalado) |

- **Sin pisar lo ajeno**: sólo se escribe dentro de las marcas. Si no hay bloque, se agrega al principio del archivo; si el archivo no existe, se crea. Un perfil o estilo con el mismo nombre que no instaló ReinStack se rechaza.
- **Idempotente**: correrlo de nuevo no cambia ningún byte; un bloque viejo se reemplaza sólo dentro de sus marcas.
- **Backups**: la primera vez que se modifica un archivo que ya existía (`CLAUDE.md`, `AGENTS.md`, `settings.json`) queda `<archivo>.rein-bak` con su contenido original. Nunca se pisa un backup existente ni se hace uno de lo que no existía.
- **Antes de escribir** se comprueba todo: un `settings.json` con JSON inválido o marcas rotas (abiertas sin cerrar o duplicadas) cortan con un error sin tocar nada. Tampoco se siguen enlaces simbólicos en los destinos.
- **`--quitar`** saca los bloques (y las líneas en blanco que agregó), los perfiles y el estilo, devuelve el `outputStyle` que había (o borra la clave si no había) y deja lo ajeno como estaba. Conserva los `.rein-bak`.

Cerrá y reabrí el cliente para que cargue lo nuevo.

## Idioma

`install` y `global` aceptan `--lang es|en`; sin él se usa la locale (`es...` da español, cualquier otra da inglés). `update` conserva el idioma instalado y una instalación 0.3.0 cuenta como español. En una instalación en inglés los archivos se llaman `CONTEXT.md`, `ORCHESTRATOR.md`, `STORIES.md` y `.rein/METHOD.md`, y las opciones tienen alias en inglés (`tone`, `--state`, `--no-tone`, `--remove`); los dos nombres funcionan siempre. Ver el README, sección Idioma.

## Retomar otro día

Tres archivos responden todo. CONTEXTO.md dice por qué existe el proyecto y cambia poco. ORQUESTADOR.md, el estado, dice qué se está trabajando, qué está bloqueado y cuál es el próximo paso, en sus cinco secciones; puede ser un enlace a una nota externa (por ejemplo de Obsidian) creado con `install --estado <ruta>`, y no es una copia del chat. HISTORIAS.md dice qué está aceptado y con qué evidencia. Se corrigen o eliminan las decisiones que ya no aplican. Un `obsidian.md` existente sigue valiendo como archivo de estado, por compatibilidad.

ReinStack instala este circuito como instrucciones. Recuperar el contrato y comprobar casos exige trabajo real del orquestador: el instalador no implementa un ejecutor universal de aceptación ni un sistema de permisos.
