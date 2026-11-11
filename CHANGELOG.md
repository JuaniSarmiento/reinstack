# Changelog

## 1.0.1 (sin publicar)

- Corrige macOS: se aceptan enlaces simbólicos en directorios padres del proyecto (`/tmp` y `/var/folders` cuelgan de `/var`, enlace a `/private/var`). Siguen rechazados el proyecto que es un enlace y los enlaces dentro del proyecto.
- CI: el workflow instala `setuptools` y `wheel` antes de las pruebas (el runner de Python 3.12 no los trae).
- La versión en `reinstack.py` y `pyproject.toml` sigue en 1.0.0 hasta publicar: las aceptaciones congeladas la fijan.

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
