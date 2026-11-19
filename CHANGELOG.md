# Changelog

## 1.6.0

- Firmeza: cercano para hablar, estricto para trabajar. El tono de socio se queda, pero la primera línea de «Cómo sos» pasa a ser la firmeza: no se saltean pasos por apuro, se dice una vez y con el porqué. Sin revisores, perfiles ni subagentes nuevos.
- El apuro no levanta pasos: si la persona pide saltear criterios, aceptación congelada, pruebas o verificación, el orquestador dice qué se saltea y qué riesgo trae, pide un sí explícito y lo anota en la historia.
- Un pedido que contradice una regla del dominio o una decisión vigente de CONTEXTO.md pide siempre una decisión explícita, aunque haya apuro; si cambia, se actualiza CONTEXTO.md con el porqué.
- El orquestador sólo construye si la persona se lo pide literalmente; se quita «un cambio chico y local puede hacerlo el orquestador».
- Lista de bordes en los criterios negativos (números enormes o negativos, vacíos y nulos, duplicados, fechas y zonas horarias, límites, borrados), recorrida en una sola pasada. Llega con `reinstack update` y `reinstack global`.

## 1.5.0

- Tono de socio: Rein deja de sonar a supervisor y habla como un compañero cercano y directo. Saluda por su nombre a la persona (si lo sabe) al arrancar la conversación y cuando vuelve después de una pausa, una vez y no en cada mensaje, y festeja lo que sale bien con el dato. Firme con el método desde el mismo lado, sin halagos vacíos. El método no cambia: llega con `reinstack global` (estilo de Claude y bloque de tono de Codex).

## 1.4.0

- Tercer rol `rein-documentador` (a pedido, nunca por historia): llena la base de conocimiento desde el código y Git, propone archivo por archivo separando evidencia de supuestos y no escribe nada sin confirmación. Se instala con `install` y `global`, y `update` lo suma a instalaciones 1.3.0 y anteriores (el manifiesto viejo, sin ese perfil, se acepta; un archivo ajeno en su ruta sigue siendo error).
- Cierre de la base: cada historia trae K01… (qué regla, decisión o lección entra a la base, o «nada, porque…»), con campo nuevo en la plantilla de historias. Si algo salió mal, la lección es obligatoria; una historia no pasa a Lista con un K sin cumplir.
- Tono: cada explicación técnica cierra con un párrafo simple.
- Se quita la revisión adversarial: la búsqueda del error va en los criterios negativos (en L, por lista).

## 1.3.0

- Base de conocimiento: `install` y `update` aceptan `--contexto` (`--context`) con `simple` (por defecto, como hasta ahora), `media` (`conocimiento/` con reglas, decisiones y lecciones), `completa` (además problema, alcance, modelo, arquitectura y glosario) o la ruta de una base existente. El índice vive en CONTEXTO.md dentro de un bloque `<!-- rein:base -->`; Rein sólo escribe ahí. Los archivos se siembran si faltan, nunca se pisan y `uninstall` no los borra. Se puede subir de modo con `update --contexto`; bajar lo hace la persona a mano. El modo queda en el manifiesto (sin clave, `simple`). Sección «Base de conocimiento» en el método.

## 1.2.0

- Criterios negativos: cada historia trae, además de los C01…, criterios N01… (lo que no tiene que pasar: entrada inválida, algo que debe negarse, datos que no se tocan, correr dos veces, un caso borde). Se escriben y se congelan junto con los C, se ven fallar igual, y el orquestador se pregunta «¿qué implementación mala pasaría esto?». Escala por nivel: S al menos 1, M 2 o 3, L una lista corta. Sección «Criterios negativos» en el método, mención en el bloque global y en los perfiles, y campo nuevo en la plantilla de `HISTORIAS.md`. Sin agentes ni archivos nuevos.

## 1.1.0

- Niveles de historia S, M y L: el nivel es el mayor entre dificultad y riesgo y decide la ceremonia (aceptación, quién construye, verificación y demo). Sección «Niveles» en el método y en el bloque global, columna «Nivel» y campo «Nivel y porqué» en `HISTORIAS.md`, y el orquestador propone el nivel con su porqué. Sube si la historia crece, nunca baja.
- Corrige macOS: se aceptan enlaces simbólicos en directorios padres del proyecto (`/tmp` y `/var/folders` cuelgan de `/var`, enlace a `/private/var`). Siguen rechazados el proyecto que es un enlace y los enlaces dentro del proyecto.
- CI: el workflow instala `setuptools` y `wheel` antes de las pruebas (el runner de Python 3.12 no los trae).

## 1.0.0

- Primera versión pública, licencia MIT.
- Paquete instalable con el comando `reinstack` (`pipx`, `uvx`); las plantillas viajan en el paquete.
- CI en Linux y macOS, Python 3.11 y 3.12, también con `LANG=C`.
- Windows no está soportado (la opción `--estado`/`--state` usa enlaces simbólicos).

## 0.4.0

- Nombres de archivo y opciones en inglés para instalaciones en inglés, con alias en los dos idiomas.

## 0.3.0

- Español e inglés completos: plantillas, mensajes, ayuda; el idioma queda en el manifiesto.

## 0.2.0

- Archivos base (`CONTEXTO.md`, `HISTORIAS.md`), `update`, `doctor`, `global` y estilo de tono.
