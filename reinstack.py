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

VERSION = "1.0.0"
MANIFEST = ".rein/manifest.json"
PENDING = ".rein/manifest.pending.json"
START = "<!-- REINSTACK BEGIN -->"
END = "<!-- REINSTACK END -->"
LANGS = ("es", "en")
BRIDGES = {
    "es": (
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
    ),
    "en": (
        f"{START}\n"
        "## ReinStack\n\n"
        "Read `.rein/METHOD.md`, `CONTEXT.md`, `STORIES.md` and the state file (`ORCHESTRATOR.md`,\n"
        "which can be a link to an external note; `obsidian.md` if the project has one) before working.\n"
        "If `CONTEXT.md` is empty, the orchestrator writes it first (story 0).\n"
        "The main agent acts as the\n"
        "Rein orchestrator: it agrees on scope with the person and delegates the implementation\n"
        "to the `rein-constructor` profile. The builder does not modify the approved\n"
        "acceptance. A story only moves to Done with verification and explicit\n"
        "acceptance from the person. If no subagents are available, say so and agree\n"
        "how to proceed before taking over the builder's work.\n"
        f"{END}\n"
    ),
}
ROLES = {
    "es": {
        "orchestrator": "Acuerda historias con la persona, delega y verifica evidencia independiente.",
        "constructor": "Implementa una historia acotada sin modificar su aceptación aprobada.",
    },
    "en": {
        "orchestrator": "Agrees on stories with the person, delegates and verifies independent evidence.",
        "constructor": "Implements one bounded story without modifying its approved acceptance.",
    },
}
ROLE_NAMES = tuple(ROLES["es"])
# Names of the managed files and seeds per installation language.
NAMES = {
    "es": {"context": "CONTEXTO.md", "orch": "ORQUESTADOR.md", "stories": "HISTORIAS.md", "method": ".rein/METODO.md"},
    "en": {"context": "CONTEXT.md", "orch": "ORCHESTRATOR.md", "stories": "STORIES.md", "method": ".rein/METHOD.md"},
}
SEEDS = {
    "es": {
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
    },
    "en": {
        "README.md": "# Project\n\n## Goal and scope\nTo be agreed with the person.\n\n## Stack and how to run\nTo be defined.\n",
        "STORIES.md": (
            "# Stories\n\nStates: Pending · In progress · Ready · Done.\n\n"
            "| Story | Expected result | Difficulty / risk | Status |\n"
            "|---|---|---|---|\n\n"
            "## Story template\n"
            "- Result for the person:\n- Scope and exclusions:\n"
            "- Acceptance criteria (identifiers and examples):\n"
            "- Difficulty and risks:\n- Brief and relevant files:\n"
            "- Approved acceptance: SHA, command and expected cases:\n"
            "- Evidence, demo and human approval:\n"
        ),
        "CONTEXT.md": (
            "# Context\n\n"
            "It is stable: it is written in story 0 and changed only when a decision changes.\n\n"
            "## Problem\nWhat hurts today and for whom, in a few lines.\n\n"
            "## Who it's for\nWho uses it and in what situation.\n\n"
            "## What it is and isn't\nThe scope in one sentence and what stays out.\n\n"
            "## Domain rules\nThe business rules the code cannot break.\n\n"
            "## Glossary\nDomain terms with their meaning in this project.\n\n"
            "## Stack and decisions\nChosen technologies and each decision with its why.\n"
        ),
        "ORCHESTRATOR.md": (
            "# Orchestration context\n\n"
            "At most about forty lines. It is rewritten, not stacked; the evidence lives in STORIES.md.\n\n"
            "## Goal\n\n## Environment\n"
            "| Check | The orchestrator can | The person runs it |\n|---|---|---|\n\n"
            "## Open stories\nOne line per story that is not Done: status, what is missing, blocker, next step.\n\n"
            "## Current decisions\n\n## Next step\n"
        ),
    },
}


# --- Messages (es/en). The Spanish text is the original one and must not change.
UI = "es"
MESSAGES = {
    "es": {
        "symlink_path": "Ruta con enlace simbólico: {path}",
        "root_not_dir": "El proyecto debe ser un directorio existente: {path}",
        "bad_path": "Ruta de instalación inválida: {rel}",
        "no_symlinks": "No se siguen enlaces simbólicos: {path}",
        "expected_dir": "Se esperaba un directorio: {path}",
        "expected_file": "Se esperaba un archivo: {path}",
        "manifest_size": "El manifiesto excede el tamaño permitido.",
        "manifest_invalid": "Manifiesto inválido; no se modificó el proyecto: {why}",
        "mf_version": "versión inválida",
        "mf_fields": "campos inesperados",
        "mf_schema": "versión no compatible",
        "mf_client": "cliente inválido",
        "mf_files": "archivos inesperados",
        "mf_hash": "hash inválido",
        "mf_bridges": "instrucciones inesperadas",
        "mf_block": "bloque inválido",
        "mf_prop": "propiedad inválida",
        "mf_content": "contenido del bloque inválido",
        "mf_lang": "idioma inválido",
        "mf_pending": "actualización pendiente incoherente",
        "modified": "Archivo instalado ausente o modificado: {name}. No se sobrescribe.",
        "bridge_modified": "Bloque ReinStack ausente, duplicado o modificado: {name}.",
        "interrupted": "Actualización interrumpida: corré `reinstack update` para completarla.",
        "newer": ("La versión instalada ({version}) es más nueva que este ReinStack ({current}); "
                  "usá esa versión o una posterior. No se modificó nada."),
        "estado_missing": "La ruta de --estado no existe o no es un archivo: {path}",
        "estado_has_state": ("El proyecto ya tiene {name}, que es su archivo de estado; "
                             "no se crea otro con --estado. No se modificó nada."),
        "estado_first": "Ya hay una instalación; --estado sólo se usa al instalar por primera vez.",
        "other_agent": "Ya hay otra selección instalada. Desinstalá antes de cambiar --agent.",
        "other_lang": "Ya hay otro idioma instalado. Desinstalá antes de cambiar --lang.",
        "differs": "La versión instalada difiere. Usá `reinstack update` para actualizarla.",
        "already": "ReinStack ya está instalado e íntegro; no se modificó nada.",
        "foreign": "Archivo ajeno ya existente: {name}. No se sobrescribe.",
        "bridge_unmanaged": "Bloque ReinStack sin manifiesto en {name}; revisar manualmente.",
        "install_dry": "Simulación; se instalarían {n} archivos en {root}:",
        "install_real": "Instalando {n} archivos en {root}:",
        "install_done": "Listo. Abrí una sesión nueva de tu cliente en el proyecto y leé README.md.",
        "no_install": "No hay una instalación ReinStack registrada en este proyecto.",
        "up_to_date": "ReinStack ya está actualizado; no se modificó nada.",
        "update_dry": "Simulación; se actualizarían {n} archivos en {root}:",
        "update_real": "Actualizando {n} archivos en {root}:",
        "update_done": ("Listo. README.md, {stories} y el archivo de estado (obsidian.md u {orch}) no se "
                        "modificaron. {context} se siembra sólo si falta."),
        "doctor_ok": "OK: archivos y bloques íntegros; clientes: {agent}.",
        "doctor_note": "Esta comprobación no demuestra que el cliente cargó los perfiles ni impone un sandbox.",
        "uninstalled": ("ReinStack desinstalado. README.md, {stories} y el archivo de estado "
                        "(obsidian.md u {orch}) se conservaron."),
        "marks_broken": "Marcas {ini} / {fin} rotas o duplicadas en {name}: arreglalas a mano; no se escribió nada.",
        "profile_line": "templates/{role}.md no tiene la línea esperada para el perfil global.",
        "settings_json": "{path} no es JSON válido ({why}); no se escribió nada.",
        "settings_obj": "{path} no es un objeto JSON; no se escribió nada.",
        "state_damaged": "{path} está dañado ({why}); no se escribió nada.",
        "state_not_obj": "no es un objeto",
        "kept": "Se conserva {path}: no coincide con lo que instaló ReinStack.",
        "not_ours": "{path} ya existe y no es de ReinStack; no se escribió nada.",
        "global_nochange": "Sin cambios: la instalación global ya está al día.",
        "global_nothing": "Nada que quitar.",
        "would_delete": "borraría: {path}",
        "would_write": "escribiría: {path}",
        "deleted": "borrado: {path}",
        "written": "escrito: {path}",
        "error": "Error: {why}",
        "h_desc": "ReinStack: metodología liviana y dos roles por proyecto.",
        "h_install": "Instalar sin sobrescribir configuración ajena",
        "h_path": "Directorio existente del proyecto",
        "h_estado": "Nota externa (ruta existente) a la que enlazar {orch}",
        "h_dry": "Mostrar cambios sin escribir",
        "h_update": "Llevar una instalación íntegra a esta versión",
        "h_update_path": "Directorio del proyecto instalado",
        "h_tono": "Imprimir el personaje Rein para pegar en AGENTS.md (no toca disco)",
        "h_global": "Instalar el método (y el tono) a nivel usuario en Claude Code y Codex",
        "h_sin_tono": "Instalar sólo el método, sin estilo ni bloque de tono",
        "h_global_dry": "Listar los archivos que tocaría sin escribir",
        "h_quitar": "Retirar lo que instaló y devolver el outputStyle anterior",
        "h_lang": "Idioma de los textos instalados (por defecto, el de la locale)",
    },
    "en": {
        "symlink_path": "Path contains a symbolic link: {path}",
        "root_not_dir": "The project must be an existing directory: {path}",
        "bad_path": "Invalid install path: {rel}",
        "no_symlinks": "Symbolic links are not followed: {path}",
        "expected_dir": "A directory was expected: {path}",
        "expected_file": "A file was expected: {path}",
        "manifest_size": "The manifest exceeds the allowed size.",
        "manifest_invalid": "Invalid manifest; the project was not modified: {why}",
        "mf_version": "invalid version",
        "mf_fields": "unexpected fields",
        "mf_schema": "unsupported version",
        "mf_client": "invalid client",
        "mf_files": "unexpected files",
        "mf_hash": "invalid hash",
        "mf_bridges": "unexpected instructions",
        "mf_block": "invalid block",
        "mf_prop": "invalid property",
        "mf_content": "invalid block content",
        "mf_lang": "invalid language",
        "mf_pending": "inconsistent pending update",
        "modified": "Installed file missing or modified: {name}. It is not overwritten.",
        "bridge_modified": "ReinStack block missing, duplicated or modified: {name}.",
        "interrupted": "Interrupted update: run `reinstack update` to complete it.",
        "newer": ("The installed version ({version}) is newer than this ReinStack ({current}); "
                  "use that version or a later one. Nothing was modified."),
        "estado_missing": "The --state path does not exist or is not a file: {path}",
        "estado_has_state": ("The project already has {name}, which is its state file; "
                             "no other one is created with --state. Nothing was modified."),
        "estado_first": "There is already an installation; --state is only used on the first install.",
        "other_agent": "A different selection is already installed. Uninstall before changing --agent.",
        "other_lang": "A different language is already installed. Uninstall before changing --lang.",
        "differs": "The installed version differs. Use `reinstack update` to update it.",
        "already": "ReinStack is already installed and intact; nothing was modified.",
        "foreign": "Foreign file already exists: {name}. It is not overwritten.",
        "bridge_unmanaged": "ReinStack block without a manifest in {name}; review it manually.",
        "install_dry": "Dry run; would install {n} files in {root}:",
        "install_real": "Installing {n} files in {root}:",
        "install_done": "Done. Open a new session of your client in the project and read README.md.",
        "no_install": "There is no ReinStack installation registered in this project.",
        "up_to_date": "ReinStack is already up to date; nothing was modified.",
        "update_dry": "Dry run; would update {n} files in {root}:",
        "update_real": "Updating {n} files in {root}:",
        "update_done": ("Done. README.md, {stories} and the state file (obsidian.md or {orch}) were not "
                        "modified. {context} is only seeded if missing."),
        "doctor_ok": "OK: files and blocks intact; clients: {agent}.",
        "doctor_note": "This check does not prove that the client loaded the profiles, nor does it enforce a sandbox.",
        "uninstalled": ("ReinStack uninstalled. README.md, {stories} and the state file "
                        "(obsidian.md or {orch}) were kept."),
        "marks_broken": "Marks {ini} / {fin} broken or duplicated in {name}: fix them by hand; nothing was written.",
        "profile_line": "templates/en/{role}.md does not have the expected line for the global profile.",
        "settings_json": "{path} is not valid JSON ({why}); nothing was written.",
        "settings_obj": "{path} is not a JSON object; nothing was written.",
        "state_damaged": "{path} is damaged ({why}); nothing was written.",
        "state_not_obj": "not an object",
        "kept": "Keeping {path}: it does not match what ReinStack installed.",
        "not_ours": "{path} already exists and is not from ReinStack; nothing was written.",
        "global_nochange": "No changes: the global installation is already up to date.",
        "global_nothing": "Nothing to remove.",
        "would_delete": "would delete: {path}",
        "would_write": "would write: {path}",
        "deleted": "deleted: {path}",
        "written": "written: {path}",
        "error": "Error: {why}",
        "h_desc": "ReinStack: a lightweight method and two roles per project.",
        "h_install": "Install without overwriting foreign configuration",
        "h_path": "Existing project directory",
        "h_estado": "External note (existing path) to link {orch} to",
        "h_dry": "Show changes without writing",
        "h_update": "Bring an intact installation to this version",
        "h_update_path": "Installed project directory",
        "h_tono": "Print the Rein character to paste into AGENTS.md (does not touch disk)",
        "h_global": "Install the method (and the tone) at user level in Claude Code and Codex",
        "h_sin_tono": "Install only the method, without style or tone block",
        "h_global_dry": "List the files it would touch without writing",
        "h_quitar": "Remove what it installed and restore the previous outputStyle",
        "h_lang": "Language of the installed texts (default: the locale's)",
    },
}


def t(key: str, **values) -> str:
    return MESSAGES[UI][key].format(**values)


def names(lang: str) -> dict:
    return NAMES[lang]


def detect_lang(env=None) -> str:
    """Locale language: LC_ALL, else LC_MESSAGES, else LANG; "es..." is Spanish, anything else English."""
    env = os.environ if env is None else env
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = env.get(name)
        if value:
            return "es" if value.lower().startswith("es") else "en"
    return "en"


def templates_root() -> Path:
    """Templates next to the script in a clone; as package data (reinstack_templates) when installed."""
    here = Path(__file__).resolve().parent
    clone = here / "templates"
    return clone if clone.is_dir() else here / "reinstack_templates"


def templates_dir(lang: str) -> Path:
    base = templates_root()
    return base if lang == "es" else base / lang


class ReinError(Exception):
    """An expected, actionable failure without a traceback."""


def checked_root(value: str) -> Path:
    root = Path(os.path.abspath(os.path.expanduser(value)))
    if root.is_symlink():
        raise ReinError(t("symlink_path", path=root))
    # Los enlaces en directorios padres (p. ej. /var -> /private/var en macOS) son legítimos: se resuelven.
    root = root.parent.resolve() / root.name
    if not root.is_dir():
        raise ReinError(t("root_not_dir", path=root))
    return root


def target(root: Path, relative: str) -> Path:
    """Validate every component before any read or mutation of a target."""
    parts = relative.split("/")
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ReinError(t("bad_path", rel=relative))
    item = root
    for index, part in enumerate(parts):
        item = item / part
        if item.is_symlink():
            raise ReinError(t("no_symlinks", path=item))
        if item.exists():
            if index < len(parts) - 1 and not item.is_dir():
                raise ReinError(t("expected_dir", path=item))
            if index == len(parts) - 1 and not item.is_file():
                raise ReinError(t("expected_file", path=item))
    return item


def clients(agent: str) -> tuple[str, ...]:
    return ("claude", "codex") if agent == "both" else (agent,)


def file_names(agent: str, lang: str = "es") -> set[str]:
    managed = {NAMES[lang]["method"]}
    for client in clients(agent):
        extension = "md" if client == "claude" else "toml"
        managed.update(f".{client}/agents/rein-{role}.{extension}" for role in ROLE_NAMES)
    return managed


def bridge_names(agent: str) -> set[str]:
    return {"CLAUDE.md" if client == "claude" else "AGENTS.md" for client in clients(agent)}


def profile_bytes(client: str, role: str, instructions: str, lang: str = "es") -> tuple[str, bytes]:
    """Relative path (under the client's directory root) and content of one role profile."""
    description = ROLES[lang][role]
    if client == "claude":
        content = f"---\nname: rein-{role}\ndescription: {description}\nmodel: inherit\n---\n\n{instructions}"
        return f".claude/agents/rein-{role}.md", content.encode("utf-8")
    # JSON's escaped basic strings are also valid TOML basic strings.
    fields = {"name": f"rein-{role}", "description": description, "developer_instructions": instructions}
    content = "\n".join(f"{key} = {json.dumps(value, ensure_ascii=False)}" for key, value in fields.items()) + "\n"
    return f".codex/agents/rein-{role}.toml", content.encode("utf-8")


def render(agent: str, lang: str = "es") -> dict[str, bytes]:
    templates = templates_dir(lang)
    result = {NAMES[lang]["method"]: (templates / "METODO.md").read_bytes()}
    for role in ROLE_NAMES:
        instructions = (templates / f"{role}.md").read_text(encoding="utf-8")
        for client in clients(agent):
            name, content = profile_bytes(client, role, instructions, lang)
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


def current_segment(segment: str, lang: str = "es") -> str:
    """Keep the recorded separator and replace the block with this version's."""
    return segment[: segment.index(START)] + BRIDGES[lang]


def version_key(value: str) -> tuple[int, ...]:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]+(\.[0-9]+)*", value):
        raise ValueError(t("mf_version"))
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
        raise ReinError(t("manifest_size"))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        base = {"schema", "version", "agent", "files", "bridges"}
        if not isinstance(data, dict) or set(data) not in (base, base | {"lang"}):
            raise ValueError(t("mf_fields"))
        if data["schema"] != 1:
            raise ValueError(t("mf_schema"))
        # A manifest without "lang" (0.3.0 or earlier) is Spanish.
        data.setdefault("lang", "es")
        if data["lang"] not in LANGS:
            raise ValueError(t("mf_lang"))
        version_key(data["version"])
        agent = data["agent"]
        if agent not in ("claude", "codex", "both"):
            raise ValueError(t("mf_client"))
        if not isinstance(data["files"], dict) or set(data["files"]) != file_names(agent, data["lang"]):
            raise ValueError(t("mf_files"))
        for value in data["files"].values():
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError(t("mf_hash"))
        if not isinstance(data["bridges"], dict) or set(data["bridges"]) != bridge_names(agent):
            raise ValueError(t("mf_bridges"))
        for entry in data["bridges"].values():
            if not isinstance(entry, dict) or set(entry) != {"segment", "created"}:
                raise ValueError(t("mf_block"))
            if type(entry["created"]) is not bool:
                raise ValueError(t("mf_prop"))
            if not isinstance(entry["segment"], str) or not valid_segment(entry["segment"]):
                raise ValueError(t("mf_content"))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ReinError(t("manifest_invalid", why=exc)) from exc
    return data


def load_pending(root: Path, data: dict) -> dict | None:
    """The target manifest of an interrupted update, recorded before its first write."""
    pending = load_manifest(root, PENDING)
    if pending is not None and (pending["agent"] != data["agent"] or any(
            pending["bridges"][name]["created"] != entry["created"]
            or current_segment(pending["bridges"][name]["segment"]) != current_segment(entry["segment"])
            for name, entry in data["bridges"].items())):
        raise ReinError(t("manifest_invalid", why=t("mf_pending")))
    return pending


def verify(root: Path, data: dict, pending: dict | None = None) -> None:
    """Every managed file and block matches the manifest, or, mid-update, the pending one."""
    states = [data] if pending is None else [data, pending]
    for name in data["files"]:
        path = target(root, name)
        if not path.exists() or digest(path.read_bytes()) not in {state["files"][name] for state in states}:
            raise ReinError(t("modified", name=name))
    for name in data["bridges"]:
        path = target(root, name)
        content = path.read_bytes() if path.exists() else b""
        segments = {state["bridges"][name]["segment"].encode("utf-8") for state in states}
        if (not any(content.count(segment) == 1 for segment in segments)
                or content.count(START.encode()) != 1 or content.count(END.encode()) != 1):
            raise ReinError(t("bridge_modified", name=name))


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
    lang = data.get("lang", "es")
    return {"schema": 1, "version": VERSION, "agent": data["agent"], "lang": lang,
            "files": {name: digest(content) for name, content in files.items()},
            "bridges": {name: {"segment": current_segment(entry["segment"], lang), "created": entry["created"]}
                        for name, entry in data["bridges"].items()}}


def interrupted_message() -> str:
    return t("interrupted")


def newer_message(version: str) -> str:
    return t("newer", version=version, current=VERSION)


def resolve_estado(root: Path, estado: str | None, lang: str = "es") -> Path | None:
    """Preflight of --estado: the external note must exist and the project must have no state file yet."""
    if estado is None:
        return None
    note = Path(os.path.abspath(os.path.expanduser(estado)))
    note = Path(os.path.realpath(note))
    if not note.is_file():
        raise ReinError(t("estado_missing", path=note))
    for name in ("obsidian.md", NAMES[lang]["orch"]):
        if os.path.lexists(root / name):
            raise ReinError(t("estado_has_state", name=name))
    return note


def install(root: Path, agent: str, dry_run: bool, estado: str | None = None, lang: str | None = None) -> None:
    link = resolve_estado(root, estado, lang or detect_lang())
    current = load_manifest(root)
    if current is not None:
        if estado is not None:
            raise ReinError(t("estado_first"))
        if load_pending(root, current) is not None:
            raise ReinError(interrupted_message())
        verify(root, current)
        if current["agent"] != agent:
            raise ReinError(t("other_agent"))
        if lang is not None and lang != current["lang"]:
            raise ReinError(t("other_lang"))
        if newer_than_current(current["version"]):
            raise ReinError(newer_message(current["version"]))
        if current != current_manifest(current, render(agent, current["lang"])):
            raise ReinError(t("differs"))
        print(t("already"))
        return

    lang = lang or detect_lang()
    files = render(agent, lang)
    writes = dict(files)
    data = {"schema": 1, "version": VERSION, "agent": agent, "lang": lang,
            "files": {name: digest(content) for name, content in files.items()}, "bridges": {}}
    # Complete preflight: no writes until every target and collision is checked.
    for name in files:
        if target(root, name).exists():
            raise ReinError(t("foreign", name=name))
    for name in bridge_names(agent):
        path = target(root, name)
        original = path.read_bytes() if path.exists() else b""
        if START.encode() in original or END.encode() in original:
            raise ReinError(t("bridge_unmanaged", name=name))
        separator = b"" if not original else (b"\n" if original.endswith(b"\n") else b"\n\n")
        segment = separator + BRIDGES[lang].encode("utf-8")
        data["bridges"][name] = {"segment": segment.decode("utf-8"), "created": not path.exists()}
        writes[name] = original + segment
    # Con obsidian.md (archivo o symlink, aunque esté roto) la nota es el estado: no se siembra ORQUESTADOR.md.
    # Sólo se pregunta si existe; nunca se lee ni se escribe a través de él.
    has_obsidian = os.path.lexists(root / "obsidian.md")
    for name, seed in SEEDS[lang].items():
        if name == NAMES[lang]["orch"] and has_obsidian:
            continue
        if name == NAMES[lang]["orch"] and link is not None:
            continue
        if not target(root, name).exists():
            writes[name] = seed.encode("utf-8")
    if link is not None:
        target(root, NAMES[lang]["orch"])
    writes[MANIFEST] = manifest_bytes(data)
    for name in writes:
        target(root, name)
    listed = sorted(writes) + ([NAMES[lang]["orch"] + " -> " + str(link)] if link is not None else [])
    print(t("install_dry" if dry_run else "install_real", n=len(listed), root=root))
    for name in listed:
        print(f"  {name}")
    if dry_run:
        return
    for name, content in writes.items():
        write_atomic(target(root, name), content)
    if link is not None:
        # Documento del proyecto, fuera del manifiesto: ni update ni uninstall lo tocan ni lo siguen.
        os.symlink(link, root / NAMES[lang]["orch"])
    print(t("install_done"))


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
        raise ReinError(t("no_install"))
    pending = load_pending(root, data)
    for state in (data, pending):
        if state is not None and newer_than_current(state["version"]):
            raise ReinError(newer_message(state["version"]))
    # Any human edit to managed content aborts before computing or writing anything. While an
    # update is pending, each file may hold its old or its pending content, and nothing else.
    verify(root, data, pending)
    files = render(data["agent"], data["lang"])
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
    # El contexto es un documento del proyecto: se siembra si falta y nunca se pisa.
    context = NAMES[data["lang"]]["context"]
    if not os.path.lexists(root / context):
        writes[context] = SEEDS[data["lang"]][context].encode("utf-8")
    target(root, context)
    target(root, MANIFEST)
    target(root, PENDING)
    if not writes and new == data and pending is None:
        print(t("up_to_date"))
        return
    listed = sorted(writes) + ([MANIFEST] if new != data else [])
    print(t("update_dry" if dry_run else "update_real", n=len(listed), root=root))
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
    print(t("update_done", **NAMES[data["lang"]]))


def doctor(root: Path) -> None:
    data = load_manifest(root)
    if data is None:
        raise ReinError(t("no_install"))
    pending = load_pending(root, data)
    verify(root, data, pending)
    if pending is not None:
        raise ReinError(interrupted_message())
    print(t("doctor_ok", agent=data["agent"]))
    print(t("doctor_note"))


def uninstall(root: Path) -> None:
    data = load_manifest(root)
    if data is None:
        raise ReinError(t("no_install"))
    if load_pending(root, data) is not None:
        raise ReinError(interrupted_message())
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
    print(t("uninstalled", **NAMES[data["lang"]]))


def style_path(lang: str) -> Path:
    return templates_root() / "estilo" / f"rein.{lang}.md"


def tono_block(lang: str) -> str:
    text = style_path(lang).read_text(encoding="utf-8")
    body = text.split("\n---\n", 1)[1] if text.startswith("---\n") else text
    return f"{TONO_INI}\n{body.strip()}\n{TONO_FIN}"


def tono(lang: str) -> None:
    print(tono_block(lang))


# --- Instalación global (nivel usuario) ---
GLOBAL_INI, GLOBAL_FIN = "<!-- rein:global -->", "<!-- /rein:global -->"
TONO_INI, TONO_FIN = "<!-- rein:tono -->", "<!-- /rein:tono -->"
GLOBAL_STATE = ".rein/global.json"
PROJECT_LINES = {
    "es": "Aplicá .rein/METODO.md y las instrucciones del proyecto.",
    "en": "Apply .rein/METHOD.md and the project's instructions.",
}
GLOBAL_LINES = {
    "es": (
        "Aplicá el método Rein de las instrucciones globales y, si el proyecto tiene `.rein/METODO.md`, "
        "ese archivo manda; seguí también las instrucciones del proyecto. Si todavía no existen "
        "README.md, CONTEXTO.md, HISTORIAS.md o el archivo de estado, proponé crearlos o instalar el método "
        "con `reinstack install <proyecto>`."
    ),
    "en": (
        "Apply the Rein method from the global instructions and, if the project has `.rein/METHOD.md`, "
        "that file takes precedence; also follow the project's instructions. If README.md, CONTEXT.md, "
        "STORIES.md or the state file do not exist yet, propose creating them or installing the method "
        "with `reinstack install <project>`."
    ),
}
DELETE = None


def block_span(text: str, ini: str, fin: str, name: str) -> tuple[int, int] | None:
    """Locate a marked block; broken or duplicated marks are an error, never a guess."""
    opens, closes = text.count(ini), text.count(fin)
    if opens == 0 and closes == 0:
        return None
    if opens != 1 or closes != 1 or text.index(ini) > text.index(fin):
        raise ReinError(t("marks_broken", ini=ini, fin=fin, name=name))
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


def global_profiles(client: str, lang: str = "es") -> dict[str, bytes]:
    templates = templates_dir(lang)
    result = {}
    for role in ROLE_NAMES:
        instructions = (templates / f"{role}.md").read_text(encoding="utf-8")
        if PROJECT_LINES[lang] not in instructions:
            raise ReinError(t("profile_line", role=role))
        name, content = profile_bytes(client, role, instructions.replace(PROJECT_LINES[lang], GLOBAL_LINES[lang], 1), lang)
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
        raise ReinError(t("settings_json", path=path, why=exc)) from exc
    if not isinstance(data, dict):
        raise ReinError(t("settings_obj", path=path))
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
            raise ValueError(t("state_not_obj"))
    except ValueError as exc:
        raise ReinError(t("state_damaged", path=path, why=exc)) from exc
    data.setdefault("created", [])
    data.setdefault("files", {})
    return data


def global_install(home: Path, agent: str, tone: bool, dry_run: bool, remove: bool, lang: str | None = None) -> None:
    state_path = target(home, GLOBAL_STATE)
    state = load_global_state(state_path)
    # Explicit --lang wins; otherwise the saved language; the locale only decides the first install.
    # A global.json without "lang" (0.3.0 or earlier) is Spanish, like a manifest without it.
    if lang is None:
        lang = (state.get("lang") if state.get("lang") in LANGS else "es") if state_path.exists() else detect_lang()
    original_state = json.dumps(state, indent=2, sort_keys=True)
    templates = templates_dir(lang)
    method = f"{GLOBAL_INI}\n{(templates / 'global.md').read_text(encoding='utf-8').strip()}\n{GLOBAL_FIN}"
    tone_text = tono_block(lang)
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
                print(t("kept", path=path))
        else:
            if existing is not None and digest(existing) not in mine:
                raise ReinError(t("not_ours", path=path))
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
        for rel, content in global_profiles(client, lang).items():
            managed(rel, content)
        if client == "claude" and (tone or remove):
            managed(".claude/output-styles/rein.md", style_path(lang).read_bytes())
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
    if remove:
        state.pop("lang", None)
    else:
        state["lang"] = lang
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
                raise ReinError(t("no_symlinks", path=backup))
            plan[backup] = path.read_bytes()

    if not plan:
        print(t("global_nochange") if not remove else t("global_nothing"))
        return
    for path, content in plan.items():
        deleting = content is DELETE
        print(t(("would_delete" if deleting else "would_write") if dry_run else ("deleted" if deleting else "written"), path=path))
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


def requested_lang(argv: list[str]) -> str | None:
    """Value of --lang if given (before argparse, so that help and errors use it too)."""
    value = None
    for index, arg in enumerate(argv):
        if arg == "--lang" and index + 1 < len(argv):
            value = argv[index + 1]
        elif arg.startswith("--lang="):
            value = arg.split("=", 1)[1]
    return value if value in LANGS else None


# Alias pairs (Spanish, English): both work in any language; --help shows only the locale's.
OPTION_ALIASES = {"estado": ("--estado", "--state"), "sin_tono": ("--sin-tono", "--no-tone"), "quitar": ("--quitar", "--remove")}
COMMAND_ALIASES = {"tono": ("tono", "tone")}


def option(parser, dest: str, **kwargs) -> None:
    """Register both names of an option; the one of the UI language is shown, the other is hidden."""
    shown = 0 if UI == "es" else 1
    names = OPTION_ALIASES[dest]
    parser.add_argument(names[shown], dest=dest, **kwargs)
    hidden = {**kwargs, "help": argparse.SUPPRESS}
    parser.add_argument(names[1 - shown], dest=dest, **hidden)


def main(argv: list[str] | None = None) -> int:
    global UI
    argv = sys.argv[1:] if argv is None else list(argv)
    UI = requested_lang(argv) or detect_lang()
    shown = 0 if UI == "es" else 1
    parser = argparse.ArgumentParser(description=t("h_desc"))
    parser.add_argument("--version", action="version", version=VERSION)
    tone_name = COMMAND_ALIASES["tono"][shown]
    commands = parser.add_subparsers(dest="command", required=True,
                                     metavar="{install,update,doctor,uninstall," + tone_name + ",global}")
    setup = commands.add_parser("install", help=t("h_install"))
    setup.add_argument("path", help=t("h_path"))
    setup.add_argument("--agent", choices=("claude", "codex", "both"), default="both")
    setup.add_argument("--lang", choices=LANGS, default=None, help=t("h_lang"))
    option(setup, "estado", default=None, metavar="ESTADO" if UI == "es" else "STATE", help=t("h_estado", orch=NAMES[UI]["orch"]))
    setup.add_argument("--dry-run", action="store_true", help=t("h_dry"))
    upgrade = commands.add_parser("update", help=t("h_update"))
    upgrade.add_argument("path", help=t("h_update_path"))
    upgrade.add_argument("--dry-run", action="store_true", help=t("h_dry"))
    for command in ("doctor", "uninstall"):
        subparser = commands.add_parser(command)
        subparser.add_argument("path")
    voice = commands.add_parser(tone_name, help=t("h_tono"))
    voice.add_argument("--lang", choices=LANGS, default=None, help=t("h_lang"))
    # The other name is a hidden alias: no help entry, so it does not appear in the command list.
    commands.add_parser(COMMAND_ALIASES["tono"][1 - shown]).add_argument("--lang", choices=LANGS, default=None)
    glob = commands.add_parser("global", help=t("h_global"))
    glob.add_argument("--agent", choices=("claude", "codex", "both"), default="both")
    glob.add_argument("--lang", choices=LANGS, default=None, help=t("h_lang"))
    option(glob, "sin_tono", action="store_true", help=t("h_sin_tono"))
    glob.add_argument("--dry-run", action="store_true", help=t("h_global_dry"))
    option(glob, "quitar", action="store_true", help=t("h_quitar"))
    args = parser.parse_args(argv)
    try:
        if args.command == "global":
            global_install(Path.home(), args.agent, not args.sin_tono, args.dry_run, args.quitar, args.lang)
            return 0
        if args.command in COMMAND_ALIASES["tono"]:
            tono(args.lang or detect_lang())
            return 0
        root = checked_root(args.path)
        if args.command == "install":
            install(root, args.agent, args.dry_run, args.estado, args.lang)
        elif args.command == "update":
            update(root, args.dry_run)
        elif args.command == "doctor":
            doctor(root)
        else:
            uninstall(root)
        return 0
    except (ReinError, OSError, UnicodeError) as exc:
        print(t("error", why=exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
