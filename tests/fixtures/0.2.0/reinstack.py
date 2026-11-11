#!/usr/bin/env python3
"""ReinStack: install a local working agreement and two native agent profiles.

Only Python's standard library is required. No client, shell hook, network call,
package installation, or global configuration is executed or changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

VERSION = "0.2.0"
MANIFEST = ".rein/manifest.json"
PENDING = ".rein/manifest.pending.json"
START = "<!-- REINSTACK BEGIN -->"
END = "<!-- REINSTACK END -->"
BRIDGE = (
    f"{START}\n"
    "## ReinStack\n\n"
    "Leé `.rein/METODO.md`, `HISTORIAS.md` y el archivo de estado (`obsidian.md` si el proyecto lo tiene,\n"
    "si no `ORQUESTADOR.md`) antes de trabajar.\n"
    "El agente principal actúa como\n"
    "orquestador Rein: acuerda el alcance con la persona y delega la implementación\n"
    "al perfil `rein-constructor`. El constructor no modifica la aceptación\n"
    "aprobada. Una historia sólo pasa a Terminada con verificación y aceptación\n"
    "explícita de la persona. Si no hay subagentes disponibles, informalo y acordá\n"
    "cómo seguir antes de asumir el trabajo del constructor.\n"
    f"{END}\n"
)
ROLES = {
    "orchestrator": "Acuerda historias con la persona, delega y verifica evidencia independiente.",
    "constructor": "Implementa una historia acotada sin modificar su aceptación aprobada.",
}
SEEDS = {
    "README.md": "# Proyecto\n\n## Objetivo y alcance\nPor acordar con la persona.\n\n## Stack y ejecución\nPor definir.\n",
    "HISTORIAS.md": (
        "# Historias\n\nEstados: Pendiente · En proceso · Lista · Terminada.\n\n"
        "| HU | Resultado esperado | Dificultad / riesgo | Estado |\n"
        "|---|---|---|---|\n\n"
        "## Plantilla de historia\n"
        "- Resultado para la persona:\n- Alcance y exclusiones:\n"
        "- Criterios de aceptación (identificadores y ejemplos):\n"
        "- Dificultad y riesgos:\n- Brief y archivos relevantes:\n"
        "- Aceptación aprobada: SHA, comando y casos esperados:\n"
        "- Evidencia, demo y aprobación humana:\n"
    ),
    "ORQUESTADOR.md": (
        "# Contexto de orquestación\n\n"
        "Máximo unas cuarenta líneas. Se reescribe, no se apila; la evidencia vive en HISTORIAS.md.\n\n"
        "## Objetivo\n\n## Entorno\n"
        "| Comprobación | El orquestador puede | La corre la persona |\n|---|---|---|\n\n"
        "## Historias abiertas\nUna línea por historia no Terminada: estado, qué falta, bloqueo, próximo paso.\n\n"
        "## Decisiones vigentes\n\n## Próximo paso\n"
    ),
}


class ReinError(Exception):
    """An expected, actionable failure without a traceback."""


def checked_root(value: str) -> Path:
    root = Path(os.path.abspath(os.path.expanduser(value)))
    for item in (root, *root.parents):
        if item.is_symlink():
            raise ReinError(f"Ruta con enlace simbólico: {item}")
    if not root.is_dir():
        raise ReinError(f"El proyecto debe ser un directorio existente: {root}")
    return root


def target(root: Path, relative: str) -> Path:
    """Validate every component before any read or mutation of a target."""
    parts = relative.split("/")
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ReinError(f"Ruta de instalación inválida: {relative}")
    item = root
    for index, part in enumerate(parts):
        item = item / part
        if item.is_symlink():
            raise ReinError(f"No se siguen enlaces simbólicos: {item}")
        if item.exists():
            if index < len(parts) - 1 and not item.is_dir():
                raise ReinError(f"Se esperaba un directorio: {item}")
            if index == len(parts) - 1 and not item.is_file():
                raise ReinError(f"Se esperaba un archivo: {item}")
    return item


def clients(agent: str) -> tuple[str, ...]:
    return ("claude", "codex") if agent == "both" else (agent,)


def file_names(agent: str) -> set[str]:
    names = {".rein/METODO.md"}
    for client in clients(agent):
        extension = "md" if client == "claude" else "toml"
        names.update(f".{client}/agents/rein-{role}.{extension}" for role in ROLES)
    return names


def bridge_names(agent: str) -> set[str]:
    return {"CLAUDE.md" if client == "claude" else "AGENTS.md" for client in clients(agent)}


def render(agent: str) -> dict[str, bytes]:
    templates = Path(__file__).resolve().parent / "templates"
    result = {".rein/METODO.md": (templates / "METODO.md").read_bytes()}
    for role, description in ROLES.items():
        instructions = (templates / f"{role}.md").read_text(encoding="utf-8")
        for client in clients(agent):
            if client == "claude":
                content = (
                    f"---\nname: rein-{role}\ndescription: {description}\nmodel: inherit\n---\n\n"
                    f"{instructions}"
                )
                name = f".claude/agents/rein-{role}.md"
            else:
                # JSON's escaped basic strings are also valid TOML basic strings.
                fields = {"name": f"rein-{role}", "description": description,
                          "developer_instructions": instructions}
                content = "\n".join(f"{key} = {json.dumps(value, ensure_ascii=False)}"
                                    for key, value in fields.items()) + "\n"
                name = f".codex/agents/rein-{role}.toml"
            result[name] = content.encode("utf-8")
    return result


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def valid_segment(segment: str) -> bool:
    """Structural check only: any version's block is accepted; verify() checks the file."""
    body = segment.lstrip("\n")
    return (segment[: len(segment) - len(body)] in ("", "\n", "\n\n")
            and body.startswith(START) and body.endswith(END + "\n")
            and body.count(START) == 1 and body.count(END) == 1)


def current_segment(segment: str) -> str:
    """Keep the recorded separator and replace the block with this version's."""
    return segment[: segment.index(START)] + BRIDGE


def version_key(value: str) -> tuple[int, ...]:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+(\.[0-9]+)*", value):
        raise ValueError("versión inválida")
    return tuple(int(part) for part in value.split("."))


def newer_than_current(value: str) -> bool:
    installed, current = version_key(value), version_key(VERSION)
    width = max(len(installed), len(current))
    return installed + (0,) * (width - len(installed)) > current + (0,) * (width - len(current))


def load_manifest(root: Path, relative: str = MANIFEST) -> dict | None:
    path = target(root, relative)
    if not path.exists():
        return None
    if path.stat().st_size > 1024 * 1024:
        raise ReinError("El manifiesto excede el tamaño permitido.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != {"schema", "version", "agent", "files", "bridges"}:
            raise ValueError("campos inesperados")
        if data["schema"] != 1:
            raise ValueError("versión no compatible")
        version_key(data["version"])
        agent = data["agent"]
        if agent not in ("claude", "codex", "both"):
            raise ValueError("cliente inválido")
        if not isinstance(data["files"], dict) or set(data["files"]) != file_names(agent):
            raise ValueError("archivos inesperados")
        for value in data["files"].values():
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("hash inválido")
        if not isinstance(data["bridges"], dict) or set(data["bridges"]) != bridge_names(agent):
            raise ValueError("instrucciones inesperadas")
        for entry in data["bridges"].values():
            if not isinstance(entry, dict) or set(entry) != {"segment", "created"}:
                raise ValueError("bloque inválido")
            if type(entry["created"]) is not bool:
                raise ValueError("propiedad inválida")
            if not isinstance(entry["segment"], str) or not valid_segment(entry["segment"]):
                raise ValueError("contenido del bloque inválido")
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ReinError(f"Manifiesto inválido; no se modificó el proyecto: {exc}") from exc
    return data


def load_pending(root: Path, data: dict) -> dict | None:
    """The target manifest of an interrupted update, recorded before its first write."""
    pending = load_manifest(root, PENDING)
    if pending is not None and (pending["agent"] != data["agent"] or any(
            pending["bridges"][name]["created"] != entry["created"]
            or current_segment(pending["bridges"][name]["segment"]) != current_segment(entry["segment"])
            for name, entry in data["bridges"].items())):
        raise ReinError("Manifiesto inválido; no se modificó el proyecto: actualización pendiente incoherente")
    return pending


def verify(root: Path, data: dict, pending: dict | None = None) -> None:
    """Every managed file and block matches the manifest, or, mid-update, the pending one."""
    states = [data] if pending is None else [data, pending]
    for name in data["files"]:
        path = target(root, name)
        if not path.exists() or digest(path.read_bytes()) not in {state["files"][name] for state in states}:
            raise ReinError(f"Archivo instalado ausente o modificado: {name}. No se sobrescribe.")
    for name in data["bridges"]:
        path = target(root, name)
        content = path.read_bytes() if path.exists() else b""
        segments = {state["bridges"][name]["segment"].encode("utf-8") for state in states}
        if (not any(content.count(segment) == 1 for segment in segments)
                or content.count(START.encode()) != 1 or content.count(END.encode()) != 1):
            raise ReinError(f"Bloque ReinStack ausente, duplicado o modificado: {name}.")


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".reinstack-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
        # Preserve existing file permission bits, rather than turning instructions executable.
        if path.exists():
            os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def manifest_bytes(data: dict) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def current_manifest(data: dict, files: dict[str, bytes]) -> dict:
    """The manifest this version would record for an intact install described by data."""
    return {"schema": 1, "version": VERSION, "agent": data["agent"],
            "files": {name: digest(content) for name, content in files.items()},
            "bridges": {name: {"segment": current_segment(entry["segment"]), "created": entry["created"]}
                        for name, entry in data["bridges"].items()}}


INTERRUPTED = "Actualización interrumpida: corré `reinstack update` para completarla."


def newer_message(version: str) -> str:
    return (f"La versión instalada ({version}) es más nueva que este ReinStack ({VERSION}); "
            "usá esa versión o una posterior. No se modificó nada.")


def install(root: Path, agent: str, dry_run: bool) -> None:
    current = load_manifest(root)
    if current is not None:
        if load_pending(root, current) is not None:
            raise ReinError(INTERRUPTED)
        verify(root, current)
        if current["agent"] != agent:
            raise ReinError("Ya hay otra selección instalada. Desinstalá antes de cambiar --agent.")
        if newer_than_current(current["version"]):
            raise ReinError(newer_message(current["version"]))
        if current != current_manifest(current, render(agent)):
            raise ReinError("La versión instalada difiere. Usá `reinstack update` para actualizarla.")
        print("ReinStack ya está instalado e íntegro; no se modificó nada.")
        return

    files = render(agent)
    writes = dict(files)
    data = {"schema": 1, "version": VERSION, "agent": agent,
            "files": {name: digest(content) for name, content in files.items()}, "bridges": {}}
    # Complete preflight: no writes until every target and collision is checked.
    for name in files:
        if target(root, name).exists():
            raise ReinError(f"Archivo ajeno ya existente: {name}. No se sobrescribe.")
    for name in bridge_names(agent):
        path = target(root, name)
        original = path.read_bytes() if path.exists() else b""
        if START.encode() in original or END.encode() in original:
            raise ReinError(f"Bloque ReinStack sin manifiesto en {name}; revisar manualmente.")
        separator = b"" if not original else (b"\n" if original.endswith(b"\n") else b"\n\n")
        segment = separator + BRIDGE.encode("utf-8")
        data["bridges"][name] = {"segment": segment.decode("utf-8"), "created": not path.exists()}
        writes[name] = original + segment
    # Con obsidian.md (archivo o symlink, aunque esté roto) la nota es el estado: no se siembra ORQUESTADOR.md.
    # Sólo se pregunta si existe; nunca se lee ni se escribe a través de él.
    has_obsidian = os.path.lexists(root / "obsidian.md")
    for name, seed in SEEDS.items():
        if name == "ORQUESTADOR.md" and has_obsidian:
            continue
        if not target(root, name).exists():
            writes[name] = seed.encode("utf-8")
    writes[MANIFEST] = manifest_bytes(data)
    for name in writes:
        target(root, name)
    print(("Simulación; se instalarían" if dry_run else "Instalando") + f" {len(writes)} archivos en {root}:")
    for name in sorted(writes):
        print(f"  {name}")
    if dry_run:
        return
    for name, content in writes.items():
        write_atomic(target(root, name), content)
    print("Listo. Abrí una sesión nueva de tu cliente en el proyecto y leé README.md.")


def observed_manifest(root: Path, data: dict, pending: dict) -> dict:
    """The manifest describing disk as found: each verified file or block, old or pending."""
    observed = json.loads(json.dumps(data))
    for name in data["files"]:
        observed["files"][name] = digest(target(root, name).read_bytes())
    for name, entry in data["bridges"].items():
        if target(root, name).read_bytes().count(entry["segment"].encode("utf-8")) != 1:
            observed["bridges"][name]["segment"] = pending["bridges"][name]["segment"]
    return observed


def update(root: Path, dry_run: bool) -> None:
    data = load_manifest(root)
    if data is None:
        raise ReinError("No hay una instalación ReinStack registrada en este proyecto.")
    pending = load_pending(root, data)
    for state in (data, pending):
        if state is not None and newer_than_current(state["version"]):
            raise ReinError(newer_message(state["version"]))
    # Any human edit to managed content aborts before computing or writing anything. While an
    # update is pending, each file may hold its old or its pending content, and nothing else.
    verify(root, data, pending)
    files = render(data["agent"])
    new = current_manifest(data, files)
    retarget = pending is not None and pending != new
    recorded = data
    if retarget:
        data = observed_manifest(root, data, pending)
    writes = {}
    # Complete preflight: every target is validated and every new content computed first.
    for name, content in files.items():
        if target(root, name).read_bytes() != content:
            writes[name] = content
    for name, entry in data["bridges"].items():
        old = entry["segment"].encode("utf-8")
        segment = new["bridges"][name]["segment"].encode("utf-8")
        content = target(root, name).read_bytes()
        if segment != old and content.count(old) == 1:
            writes[name] = content.replace(old, segment, 1)
    target(root, MANIFEST)
    target(root, PENDING)
    if not writes and new == data and pending is None:
        print("ReinStack ya está actualizado; no se modificó nada.")
        return
    listed = sorted(writes) + ([MANIFEST] if new != data else [])
    print(("Simulación; se actualizarían" if dry_run else "Actualizando") + f" {len(listed)} archivos en {root}:")
    for name in listed:
        print(f"  {name}")
    if dry_run:
        return
    if data != recorded:
        # A pending update from another ReinStack: first record what is on disk, so that after
        # retargeting the pending manifest every file still matches the manifest or the pending one.
        write_atomic(target(root, MANIFEST), manifest_bytes(data))
    # Record the target first, so an interrupted run can be told apart from a human edit and resumed.
    if writes and (pending is None or retarget):
        write_atomic(target(root, PENDING), manifest_bytes(new))
    for name, content in writes.items():
        write_atomic(target(root, name), content)
    if new != data:
        write_atomic(target(root, MANIFEST), manifest_bytes(new))
    if target(root, PENDING).exists():
        target(root, PENDING).unlink()
    print("Listo. README.md, HISTORIAS.md y el archivo de estado (obsidian.md u ORQUESTADOR.md) no se modificaron.")


def doctor(root: Path) -> None:
    data = load_manifest(root)
    if data is None:
        raise ReinError("No hay una instalación ReinStack registrada en este proyecto.")
    pending = load_pending(root, data)
    verify(root, data, pending)
    if pending is not None:
        raise ReinError(INTERRUPTED)
    print(f"OK: archivos y bloques íntegros; clientes: {data['agent']}.")
    print("Esta comprobación no demuestra que el cliente cargó los perfiles ni impone un sandbox.")


def uninstall(root: Path) -> None:
    data = load_manifest(root)
    if data is None:
        raise ReinError("No hay una instalación ReinStack registrada en este proyecto.")
    if load_pending(root, data) is not None:
        raise ReinError(INTERRUPTED)
    verify(root, data)
    # Preflight every bridge and owned file before removing any of them.
    replacements = {}
    for name, entry in data["bridges"].items():
        content = target(root, name).read_bytes()
        result = content.replace(entry["segment"].encode("utf-8"), b"", 1)
        replacements[name] = None if entry["created"] and not result else result
    for name, content in replacements.items():
        path = target(root, name)
        if content is None:
            path.unlink()
        else:
            write_atomic(path, content)
    for name in data["files"]:
        target(root, name).unlink()
    target(root, MANIFEST).unlink()
    # Directory ownership is not recorded; preserve even empty directories.
    print("ReinStack desinstalado. README.md, HISTORIAS.md y el archivo de estado (obsidian.md u ORQUESTADOR.md) se conservaron.")


def tono(lang: str) -> None:
    text = (Path(__file__).resolve().parent / "templates" / "estilo" / f"rein.{lang}.md").read_text(encoding="utf-8")
    body = text.split("\n---\n", 1)[1] if text.startswith("---\n") else text
    print(f"<!-- rein:tono -->\n{body.strip()}\n<!-- /rein:tono -->")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ReinStack: metodología liviana y dos roles por proyecto.")
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("install", help="Instalar sin sobrescribir configuración ajena")
    setup.add_argument("path", help="Directorio existente del proyecto")
    setup.add_argument("--agent", choices=("claude", "codex", "both"), default="both")
    setup.add_argument("--dry-run", action="store_true", help="Mostrar cambios sin escribir")
    upgrade = commands.add_parser("update", help="Llevar una instalación íntegra a esta versión")
    upgrade.add_argument("path", help="Directorio del proyecto instalado")
    upgrade.add_argument("--dry-run", action="store_true", help="Mostrar cambios sin escribir")
    for command in ("doctor", "uninstall"):
        subparser = commands.add_parser(command)
        subparser.add_argument("path")
    voice = commands.add_parser("tono", help="Imprimir el personaje Rein para pegar en AGENTS.md (no toca disco)")
    voice.add_argument("--lang", choices=("es", "en"), default="es")
    args = parser.parse_args(argv)
    if args.command == "tono":
        try:
            tono(args.lang)
            return 0
        except (OSError, UnicodeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
    try:
        root = checked_root(args.path)
        if args.command == "install":
            install(root, args.agent, args.dry_run)
        elif args.command == "update":
            update(root, args.dry_run)
        elif args.command == "doctor":
            doctor(root)
        else:
            uninstall(root)
        return 0
    except (ReinError, OSError, UnicodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
