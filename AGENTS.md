# Desarrollo de ReinStack

El repositorio contiene un instalador local, no la aplicación meteorológica de origen. Leer README.md y templates/METODO.md antes de cambiar su comportamiento.

- El agente principal orquesta; delegar implementación a un constructor cuando haya subagentes disponibles.
- Preservar texto y archivos ajenos. Rechazar conflictos antes de escribir y no atravesar enlaces simbólicos en destinos administrados.
- Ninguna prueba toca el HOME real ni ejecuta Claude, Codex u otros clientes. Usar directorios temporales.
- Para cambios del instalador, observar primero una prueba fallar por una aserción pertinente y después implementar la corrección.
- No confundir perfiles e instrucciones con permisos efectivos o aislamiento de seguridad.
- El remoto es github.com/JuaniSarmiento/reinstack. No subir sin que la persona lo pida.
