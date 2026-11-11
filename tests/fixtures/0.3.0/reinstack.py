#!/usr/bin/env python3
"""ReinStack: install a local working agreement and two native agent profiles.

Only Python's standard library is required. No client, shell hook, network call or
package installation is executed. Only `global` writes under the user's HOME, and only what it lists.
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

VERSION = "0.3.0"
MANIFEST = ".rein/manifest.json"
PENDING = ".rein/manifest.pending.json"
START = "<!-- REINSTACK BEGIN -->"
END = "<!-- REINSTACK END -->"
BRIDGE = (
    f"{START}\n"
    "## ReinStack\n\n"
    "Leé `.rein/METODO.md`, `CONTEXTO.md`, `HISTORIAS.md` y el archivo de estado (`ORQUESTADOR.md`,\n"
    "que puede ser un enlace a una nota externa; `obsidian.md` si el proyecto lo tiene) antes de trabajar.\n"
    "Si `CONTEXTO.md` está vacío, el orquestador lo escribe primero (historia 0).\n"
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
    "CONTEXTO.md": (
        "# Contexto\n\n"
        "Es estable: se escribe en la historia 0 y se cambia sólo cuando cambia una decisión.\n\n"
        "## Problema\nQué duele hoy y a quién, en pocas líneas.\n\n"
        "## Para quién\nQuiénes lo usan y en qué situación.\n\n"
        "## Qué es y qué no\nEl alcance en una frase y lo que queda afuera.\n\n"
        "## Reglas del dominio\nLas reglas del negocio que el código no puede violar.\n\n"
        "## Glosario\nTérminos del dominio con su significado en este proyecto.\n\n"
        "## Stack y decisiones\nTecnologías elegidas y cada decisión con su porqué.\n"
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


def profile_bytes(client: str, role: str, instructions: str) -> tuple[str, bytes]:
    """Relative path (under the client's directory root) and content of one role profile."""
    description = ROLES[role]
    if client == "claude":
        content = f"---\nname: rein-{role}\ndescription: {description}\nmodel: inherit\n---\n\n{instructions}"
        return f".claude/agents/rein-{role}.md", content.encode("utf-8")
    # JSON's escaped basic strings are also valid TOML basic strings.
    fields = {"name": f"rein-{role}", "description": description, "developer_instructions": instructions}
    content = "\n".join(f"{key} = {json.dumps(value, ensure_ascii=False)}" for key, value in fields.items()) + "\n"
    return f".codex/agents/rein-{role}.toml", content.encode("utf-8")


def render(agent: str) -> dict[str, bytes]:
    templates = Path(__file__).resolve().parent / "templates"
    result = {".rein/METODO.md": (templates / "METODO.md").read_bytes()}
    for role in ROLES:
        instructions = (templates / f"{role}.md").read_text(encoding="utf-8")
        for client in clients(agent):
            name, content = profile_bytes(client, role, instructions)
            result[name] = content
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


def resolve_estado(root: Path, estado: str | None) -> Path | None:
    """Preflight of --estado: the external note must exist and the project must have no state file yet."""
    if estado is None:
        return None
    note = Path(os.path.abspath(os.path.expanduser(estado)))
    note = Path(os.path.realpath(note))
    if not note.is_file():
        raise ReinError(f"La ruta de --estado no existe o no es un archivo: {note}")
    for name in ("obsidian.md", "ORQUESTADOR.md"):
        if os.path.lexists(root / name):
            raise ReinError(f"El proyecto ya tiene {name}, que es su archivo de estado; "
                            "no se crea otro con --estado. No se modificó nada.")
    return note


def install(root: Path, agent: str, dry_run: bool, estado: str | None = None) -> None:
    link = resolve_estado(root, estado)
    current = load_manifest(root)
    if current is not None:
        if estado is not None:
            raise ReinError("Ya hay una instalación; --estado sólo se usa al instalar por primera vez.")
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
        if name == "ORQUESTADOR.md" and link is not None:
            continue
        if not target(root, name).exists():
            writes[name] = seed.encode("utf-8")
    if link is not None:
        target(root, "ORQUESTADOR.md")
    writes[MANIFEST] = manifest_bytes(data)
    for name in writes:
        target(root, name)
    listed = sorted(writes) + (["ORQUESTADOR.md -> " + str(link)] if link is not None else [])
    print(("Simulación; se instalarían" if dry_run else "Instalando") + f" {len(listed)} archivos en {root}:")
    for name in listed:
        print(f"  {name}")
    if dry_run:
        return
    for name, content in writes.items():
        write_atomic(target(root, name), content)
    if link is not None:
        # Documento del proyecto, fuera del manifiesto: ni update ni uninstall lo tocan ni lo siguen.
        os.symlink(link, root / "ORQUESTADOR.md")
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
    # CONTEXTO.md es un documento del proyecto: se siembra si falta y nunca se pisa.
    if not os.path.lexists(root / "CONTEXTO.md"):
        writes["CONTEXTO.md"] = SEEDS["CONTEXTO.md"].encode("utf-8")
    target(root, "CONTEXTO.md")
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
    print("Listo. README.md, HISTORIAS.md y el archivo de estado (obsidian.md u ORQUESTADOR.md) no se modificaron. CONTEXTO.md se siembra sólo si falta.")


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


def tono_block(lang: str) -> str:
    text = (Path(__file__).resolve().parent / "templates" / "estilo" / f"rein.{lang}.md").read_text(encoding="utf-8")
    body = text.split("\n---\n", 1)[1] if text.startswith("---\n") else text
    return f"{TONO_INI}\n{body.strip()}\n{TONO_FIN}"


def tono(lang: str) -> None:
    print(tono_block(lang))


# --- Instalación global (nivel usuario) ---
GLOBAL_INI, GLOBAL_FIN = "<!-- rein:global -->", "<!-- /rein:global -->"
TONO_INI, TONO_FIN = "<!-- rein:tono -->", "<!-- /rein:tono -->"
GLOBAL_STATE = ".rein/global.json"
PROJECT_LINE = "Aplicá .rein/METODO.md y las instrucciones del proyecto."
GLOBAL_LINE = (
    "Aplicá el método Rein de las instrucciones globales y, si el proyecto tiene `.rein/METODO.md`, "
    "ese archivo manda; seguí también las instrucciones del proyecto. Si todavía no existen "
    "README.md, CONTEXTO.md, HISTORIAS.md o el archivo de estado, proponé crearlos o instalar el método "
    "con `reinstack install <proyecto>`."
)
DELETE = None


def block_span(text: str, ini: str, fin: str, name: str) -> tuple[int, int] | None:
    """Locate a marked block; broken or duplicated marks are an error, never a guess."""
    opens, closes = text.count(ini), text.count(fin)
    if opens == 0 and closes == 0:
        return None
    if opens != 1 or closes != 1 or text.index(ini) > text.index(fin):
        raise ReinError(f"Marcas {ini} / {fin} rotas o duplicadas en {name}: arreglalas a mano; no se escribió nada.")
    return text.index(ini), text.index(fin) + len(fin)


def put_block(text: str, ini: str, fin: str, block: str, name: str, after: tuple[str, str] | None = None) -> str:
    span = block_span(text, ini, fin, name)
    if span:
        return text[: span[0]] + block + text[span[1]:]
    anchor = block_span(text, *after, name) if after else None
    if anchor:
        return text[: anchor[1]] + "\n\n" + block + text[anchor[1]:]
    return block + ("\n\n" + text if text.strip() else "\n")


def drop_block(text: str, ini: str, fin: str, name: str) -> str:
    span = block_span(text, ini, fin, name)
    if not span:
        return text
    before, after = text[: span[0]], text[span[1]:]
    if after.startswith("\n\n"):
        after = after[2:]
    elif after.strip() == "":
        after = ""
        before = before.rstrip("\n") + "\n" if before.strip() else ""
    return before + after


def global_profiles(client: str) -> dict[str, bytes]:
    templates = Path(__file__).resolve().parent / "templates"
    result = {}
    for role in ROLES:
        instructions = (templates / f"{role}.md").read_text(encoding="utf-8")
        if PROJECT_LINE not in instructions:
            raise ReinError(f"templates/{role}.md no tiene la línea esperada para el perfil global.")
        name, content = profile_bytes(client, role, instructions.replace(PROJECT_LINE, GLOBAL_LINE, 1))
        result[name] = content
    return result


def read_text(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.exists() else None


def parse_settings(path: Path) -> dict:
    text = read_text(path)
    if text is None:
        return {}
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ReinError(f"{path} no es JSON válido ({exc}); no se escribió nada.") from exc
    if not isinstance(data, dict):
        raise ReinError(f"{path} no es un objeto JSON; no se escribió nada.")
    return data


def dump_settings(data: dict, original: str | None) -> bytes:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    return (text + ("\n" if original is None or original.endswith("\n") else "")).encode("utf-8")


def load_global_state(path: Path) -> dict:
    text = read_text(path)
    if text is None:
        return {"schema": 1, "created": [], "files": {}}
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("no es un objeto")
    except ValueError as exc:
        raise ReinError(f"{path} está dañado ({exc}); no se escribió nada.") from exc
    data.setdefault("created", [])
    data.setdefault("files", {})
    return data


def global_install(home: Path, agent: str, tone: bool, dry_run: bool, remove: bool) -> None:
    state_path = target(home, GLOBAL_STATE)
    state = load_global_state(state_path)
    original_state = json.dumps(state, indent=2, sort_keys=True)
    templates = Path(__file__).resolve().parent / "templates"
    method = f"{GLOBAL_INI}\n{(templates / 'global.md').read_text(encoding='utf-8').strip()}\n{GLOBAL_FIN}"
    tone_text = tono_block("es")
    plan: dict[Path, bytes | None] = {}
    created: set[str] = set(state["created"])
    originals: set[Path] = set()  # instruction files and settings: the ones a user may have written

    def current(path: Path) -> str | None:
        return read_text(path)

    def stage(rel: str, content: bytes | None, is_created: bool = False) -> Path:
        path = target(home, rel)
        plan[path] = content
        if is_created:
            created.add(rel)
        return path

    def instructions_file(rel: str, edit) -> None:
        path = target(home, rel)
        originals.add(path)
        text = current(path)
        new = edit(text if text is not None else "", rel)
        if remove and rel in created and new.strip() == "":
            stage(rel, DELETE)
            created.discard(rel)
        elif new != (text or "") or (text is None and not remove):
            stage(rel, new.encode("utf-8"), text is None and not remove)

    def managed(rel: str, content: bytes) -> None:
        """Our own files: write when absent, equal, or untouched since we wrote them; otherwise refuse."""
        path = target(home, rel)
        existing = path.read_bytes() if path.exists() else None
        mine = {digest(content), state["files"].get(rel)}
        if remove:
            if existing is None:
                state["files"].pop(rel, None)
            elif digest(existing) in mine:
                stage(rel, DELETE)
                state["files"].pop(rel, None)
            else:
                print(f"Se conserva {path}: no coincide con lo que instaló ReinStack.")
        else:
            if existing is not None and digest(existing) not in mine:
                raise ReinError(f"{path} ya existe y no es de ReinStack; no se escribió nada.")
            if existing != content:
                stage(rel, content)
            state["files"][rel] = digest(content)

    for client in clients(agent):
        if client == "claude":
            ctx, base = ".claude/CLAUDE.md", ".claude"
        else:
            ctx, base = ".codex/AGENTS.md", ".codex"

        def edit(text: str, name: str, client=client) -> str:
            if remove:
                text = drop_block(text, GLOBAL_INI, GLOBAL_FIN, name)
                return drop_block(text, TONO_INI, TONO_FIN, name) if client == "codex" else text
            text = put_block(text, GLOBAL_INI, GLOBAL_FIN, method, name)
            if client == "codex" and tone:
                text = put_block(text, TONO_INI, TONO_FIN, tone_text, name, after=(GLOBAL_INI, GLOBAL_FIN))
            return text

        instructions_file(ctx, edit)
        for rel, content in global_profiles(client).items():
            managed(rel, content)
        if client == "claude" and (tone or remove):
            managed(".claude/output-styles/rein.md", (templates / "estilo" / "rein.es.md").read_bytes())
            settings_rel = ".claude/settings.json"
            settings_path = target(home, settings_rel)
            original = current(settings_path)
            originals.add(settings_path)
            data = parse_settings(settings_path)
            before = json.loads(json.dumps(data))
            saved = state.setdefault("claude", {})
            if remove:
                if data.get("outputStyle") == "Rein":
                    if "previous" in saved:
                        data["outputStyle"] = saved["previous"]
                    else:
                        del data["outputStyle"]
                saved.pop("previous", None)
                saved.pop("had_previous", None)
                if original is not None and data != before:
                    if settings_rel in created and not data:
                        stage(settings_rel, DELETE)
                        created.discard(settings_rel)
                    else:
                        stage(settings_rel, dump_settings(data, original))
            else:
                if "had_previous" not in saved:
                    saved["had_previous"] = "outputStyle" in data
                    if "outputStyle" in data:
                        saved["previous"] = data["outputStyle"]
                if data.get("outputStyle") != "Rein":
                    data["outputStyle"] = "Rein"
                    stage(settings_rel, dump_settings(data, original), original is None)

    if remove:
        state.get("claude", {}).pop("had_previous", None)
        if not state.get("claude"):
            state.pop("claude", None)
    state["created"] = sorted(created)
    new_state = json.dumps(state, indent=2, sort_keys=True)
    if remove and not state["files"] and not state["created"] and not state.get("claude"):
        if state_path.exists():
            plan[state_path] = DELETE
    elif new_state != original_state or not state_path.exists():
        plan[state_path] = (new_state + "\n").encode("utf-8")

    for path, content in list(plan.items()):
        backup = path.with_name(path.name + ".rein-bak")
        if (path in originals and not backup.exists() and not remove
                and str(path.relative_to(home)) not in created):
            if backup.is_symlink():
                raise ReinError(f"No se siguen enlaces simbólicos: {backup}")
            plan[backup] = path.read_bytes()

    if not plan:
        print("Sin cambios: la instalación global ya está al día." if not remove else "Nada que quitar.")
        return
    for path, content in plan.items():
        print(f"{'borraría' if content is DELETE else 'escribiría'}: {path}" if dry_run
              else f"{'borrado' if content is DELETE else 'escrito'}: {path}")
    if dry_run:
        return
    for path, content in plan.items():
        if content is DELETE:
            path.unlink(missing_ok=True)
        else:
            write_atomic(path, content)
    if remove and state_path in plan and plan[state_path] is DELETE:
        try:
            state_path.parent.rmdir()
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ReinStack: metodología liviana y dos roles por proyecto.")
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("install", help="Instalar sin sobrescribir configuración ajena")
    setup.add_argument("path", help="Directorio existente del proyecto")
    setup.add_argument("--agent", choices=("claude", "codex", "both"), default="both")
    setup.add_argument("--estado", help="Nota externa (ruta existente) a la que enlazar ORQUESTADOR.md")
    setup.add_argument("--dry-run", action="store_true", help="Mostrar cambios sin escribir")
    upgrade = commands.add_parser("update", help="Llevar una instalación íntegra a esta versión")
    upgrade.add_argument("path", help="Directorio del proyecto instalado")
    upgrade.add_argument("--dry-run", action="store_true", help="Mostrar cambios sin escribir")
    for command in ("doctor", "uninstall"):
        subparser = commands.add_parser(command)
        subparser.add_argument("path")
    voice = commands.add_parser("tono", help="Imprimir el personaje Rein para pegar en AGENTS.md (no toca disco)")
    voice.add_argument("--lang", choices=("es", "en"), default="es")
    glob = commands.add_parser("global", help="Instalar el método (y el tono) a nivel usuario en Claude Code y Codex")
    glob.add_argument("--agent", choices=("claude", "codex", "both"), default="both")
    glob.add_argument("--sin-tono", action="store_true", help="Instalar sólo el método, sin estilo ni bloque de tono")
    glob.add_argument("--dry-run", action="store_true", help="Listar los archivos que tocaría sin escribir")
    glob.add_argument("--quitar", action="store_true", help="Retirar lo que instaló y devolver el outputStyle anterior")
    args = parser.parse_args(argv)
    if args.command == "global":
        try:
            global_install(Path.home(), args.agent, not args.sin_tono, args.dry_run, args.quitar)
            return 0
        except (ReinError, OSError, UnicodeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
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
            install(root, args.agent, args.dry_run, args.estado)
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
