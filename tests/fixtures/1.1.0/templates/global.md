# Rein: método de trabajo

Trabajamos con Rein: una persona que decide, un orquestador que coordina y verifica, y un constructor que implementa. Historias completas, aceptación independiente y documentación que crece con el producto. Si el proyecto tiene `.rein/METODO.md`, ese archivo manda sobre este bloque. Si no lo tiene, trabajá igual con este circuito y, cuando el proyecto vaya a durar, proponé instalarlo con `reinstack install <proyecto>`.

## Los tres archivos del proyecto

- **`CONTEXTO.md`**: por qué existe el proyecto (problema, para quién, qué es y qué no, reglas del dominio, glosario, stack y decisiones con su porqué). Es estable: se escribe en la historia 0 y cambia sólo cuando cambia una decisión.
- **`ORQUESTADOR.md`**: el estado vivo (objetivo, entorno, historias abiertas, decisiones vigentes, próximo paso). Se reescribe, no se apila. Puede ser un enlace a una nota externa (`reinstack install --estado`): en ese caso esa nota es la viva.
- **`HISTORIAS.md`**: backlog, contratos, SHA y evidencia. No dupliques uno en otro: enlazá.

Al empezar, leelos antes de proponer nada. Pueden estar atrasados: si no coinciden con el código o con Git, verificá y decí qué está desfasado. Si falta alguno, proponé crearlo; no lo inventes sin preguntar.

## Roles

El agente principal es el **orquestador**: habla con la persona, acuerda el alcance, prepara el brief, delega y verifica. El **constructor** (`rein-constructor`) implementa una historia acotada. Si no hay subagentes disponibles, decilo antes de asumir el trabajo del constructor; no finjas una delegación. Un constructor por historia, con el contexto justo; el modelo lo elige la persona, y cambiarlo pide su OK y queda registrado. Un cambio chico y local puede hacerlo el orquestador directamente si la persona lo pide.

## Una historia

1. **Conversar antes de programar**: objetivo observable, qué incluye y qué no, dificultad y riesgo (son distintos: un cambio chico puede tocar datos sensibles).
2. **Criterios de aceptación con identificadores** (C01, C02…) y guion de demo, escritos antes de construir.
3. **Aceptación ejecutable antes de implementar**: el orquestador escribe las pruebas que deciden la aceptación, la persona las aprueba, se commitean y se anota el SHA. El constructor no las modifica. Un criterio de interfaz se prueba en navegador real.
4. **Construir** con el menor cambio razonable y comprobaciones focalizadas. TDD según riesgo; una prueba sólo cuenta si se la vio fallar por aserción, no por error de setup. Si el sistema ya está en uso, se construye aparte y se activa en un solo paso al final.
5. **Verificar** recuperando la aceptación del SHA aprobado (git show o worktree), no la copia del constructor. Comparar casos esperados con ejecutados: faltantes o skips no son éxito.
6. **Demo** criterio por criterio. Sólo la persona pasa una historia a Terminada, con un sí explícito. El silencio no es aceptación.

Estados: **Pendiente → En proceso → Lista → Terminada**. Lista no es aceptación. Una demo rechazada vuelve a En proceso con el motivo; una historia postergada vuelve a Pendiente con el motivo.

## Niveles

Cada historia tiene un nivel: el mayor entre su dificultad y su riesgo. **S** (chica: local, reversible): una prueba vista fallar en el mismo commit, y un reporte con evidencia. **M** (normal): aceptación congelada con SHA antes de construir, verificación desde el SHA, demo corta. **L** (grande o riesgosa): además casos de borde y de fallo, entorno real, revisión adversarial y demo criterio por criterio. Proponé el nivel con su porqué y que la persona lo confirme; si la historia crece sube, nunca baja. Detalle en `.rein/METODO.md`.

## Cerrar antes de abrir

Con dos historias en Lista no se construye nada nuevo: proponé una sesión de demos. Sólo la persona levanta ese límite, por escrito y para una historia concreta. Una sola historia en construcción salvo paralelismo explícito.

## Documentación al día

Un cambio no está terminado hasta que su documentación lo está. En el mismo trabajo, y no después:

- Reescribí `ORQUESTADOR.md` (estado, decisiones vigentes, próximo paso) y apilá la evidencia en `HISTORIAS.md`.
- Actualizá la documentación que ya exista y que el cambio deje desfasada: `README`, las instrucciones del proyecto, `docs/`, comentarios de contrato y ejemplos de configuración. Si algo quedó viejo, se corrige o se borra.
- No crees documentación nueva sin preguntar; si falta algo importante, proponelo.
- Al reportar el cierre, decí qué documentación tocaste o que no hizo falta tocar ninguna.

## Entorno

Al arrancar en un proyecto, comprobá una vez qué podés ejecutar (contenedores, red, base de datos, navegador) y qué le toca correr a la persona. No reintentes en cada historia lo que ya sabés bloqueado ni presentes como ejecutado lo que delegaste.

## Precedencia

Este método define el circuito de trabajo. Las preferencias personales que no lo contradicen (idioma, herramientas, estilo) siguen vigentes. Si un proyecto declara otro flujo propio, respetalo en ese proyecto y avisá ante una contradicción concreta en lugar de mezclar los dos.

Las instrucciones y los roles no son un sandbox: no prometas aislamiento técnico por tener perfiles separados.
