"""Aceptación HU-OS4 ronda 2: en inglés, los archivos y las opciones se llaman en inglés.

Escrita por el orquestador ANTES de implementar; criterios aprobados por Juani el 11/11/2026 (demo de OS4). El constructor no la modifica.
Nombres: CONTEXTO.md → CONTEXT.md · ORQUESTADOR.md → ORCHESTRATOR.md · HISTORIAS.md → STORIES.md · .rein/METODO.md → .rein/METHOD.md
         tono → tone · --estado → --state · --sin-tono → --no-tone · --quitar → --remove
Contrato:
  C09 `install --lang en` crea CONTEXT.md, ORCHESTRATOR.md, STORIES.md y .rein/METHOD.md y ningún archivo con nombre español;
      el método, el bloque puente, los perfiles y el bloque global en inglés nombran los archivos en inglés y no los españoles.
  C10 `--state` en inglés: enlaza ORCHESTRATOR.md a la nota; nota inexistente → error sin tocar nada; con obsidian.md o
      ORCHESTRATOR.md ya presentes → se niega sin tocar nada. `update` de una instalación inglesa conserva los nombres ingleses
      y siembra CONTEXT.md si falta (nunca CONTEXTO.md).
  C11 Los dos nombres funcionan en cualquier idioma (tone/tono, --state/--estado, --no-tone/--sin-tono, --remove/--quitar);
      `--help` muestra el del idioma de la locale y no el otro.
  C12 (cubierto por test_idiomas C07) el español instalado es el de las plantillas en español.
Correr: python3 -m unittest tests.test_nombres_en -v
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "reinstack.py"
EN = ["CONTEXT.md", "ORCHESTRATOR.md", "STORIES.md", ".rein/METHOD.md"]
ES = ["CONTEXTO.md", "ORQUESTADOR.md", "HISTORIAS.md", "METODO.md"]


class NombresEnTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base / "home"
        (self.home / ".claude").mkdir(parents=True)
        (self.home / ".codex").mkdir(parents=True)
        self.nota = self.base / "vault" / "Project.md"
        self.nota.parent.mkdir()
        self.nota.write_text("# My note\n", encoding="utf-8")

    def cli(self, *args, lang="en_US.UTF-8", ok=True):
        env = {k: v for k, v in os.environ.items() if k not in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG")}
        r = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                           env={**env, "HOME": str(self.home), "LANG": lang}, timeout=60)
        if ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def proyecto(self, nombre="p") -> Path:
        p = self.base / nombre
        p.mkdir()
        return p

    def foto(self, raiz: Path):
        return {str(x.relative_to(raiz)): (x.is_symlink(), x.read_bytes() if x.is_file() and not x.is_symlink() else None)
                for x in sorted(raiz.rglob("*"))}

    def sin_espanol(self, texto: str, donde: str):
        for nombre in ES:
            self.assertNotIn(nombre, texto, f"{donde} nombra {nombre}")

    def test_c09_archivos_en_ingles(self):
        p = self.proyecto()
        self.cli("install", p, "--agent", "both", "--lang", "en")
        for n in EN:
            self.assertTrue((p / n).is_file(), f"existe {n}")
        nombres = {x.name for x in p.rglob("*")}
        for n in ES:
            self.assertNotIn(n, nombres, f"no existe {n}")
        for rel in (".rein/METHOD.md", "CLAUDE.md", "AGENTS.md", ".claude/agents/rein-orchestrator.md",
                    ".claude/agents/rein-constructor.md", ".codex/agents/rein-orchestrator.toml", ".codex/agents/rein-constructor.toml"):
            texto = (p / rel).read_text(encoding="utf-8")
            self.sin_espanol(texto, rel)
        self.assertIn("CONTEXT.md", (p / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertIn("ORCHESTRATOR.md", (p / ".rein/METHOD.md").read_text(encoding="utf-8"))
        self.cli("global", "--lang", "en")
        for rel in (".claude/CLAUDE.md", ".codex/AGENTS.md", ".claude/agents/rein-orchestrator.md"):
            texto = (self.home / rel).read_text(encoding="utf-8")
            self.sin_espanol(texto, rel)
        self.assertIn("STORIES.md", (self.home / ".claude/CLAUDE.md").read_text(encoding="utf-8"))

    def test_c10_state_y_update(self):
        p = self.proyecto()
        self.cli("install", p, "--agent", "both", "--lang", "en", "--state", self.nota)
        orq = p / "ORCHESTRATOR.md"
        self.assertTrue(orq.is_symlink())
        self.assertEqual(Path(os.readlink(orq)), self.nota.resolve())
        self.assertEqual(self.nota.read_text(encoding="utf-8"), "# My note\n")
        q = self.proyecto("q")
        antes = self.foto(q)
        r = self.cli("install", q, "--lang", "en", "--state", self.base / "missing.md", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("missing.md", r.stderr)
        self.assertEqual(self.foto(q), antes)
        for previo in ("obsidian.md", "ORCHESTRATOR.md"):
            with self.subTest(previo=previo):
                o = self.proyecto("o-" + previo)
                (o / previo).write_text("x\n", encoding="utf-8")
                antes = self.foto(o)
                r = self.cli("install", o, "--lang", "en", "--state", self.nota, ok=False)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn(previo, r.stderr)
                self.assertEqual(self.foto(o), antes)
        u = self.proyecto("u")
        self.cli("install", u, "--agent", "codex", "--lang", "en")
        (u / "CONTEXT.md").unlink()
        historias = (u / "STORIES.md").read_bytes()
        self.cli("update", u, lang="es_AR.UTF-8")
        self.assertTrue((u / "CONTEXT.md").is_file(), "update siembra CONTEXT.md")
        self.assertFalse((u / "CONTEXTO.md").exists())
        self.assertEqual((u / "STORIES.md").read_bytes(), historias)
        self.assertTrue((u / ".rein/METHOD.md").is_file())
        self.assertFalse((u / ".rein/METODO.md").exists())
        self.cli("doctor", u)

    def test_c11_alias_y_ayuda(self):
        for cmd in ("tone", "tono"):
            for lang in ("en_US.UTF-8", "es_AR.UTF-8"):
                with self.subTest(cmd=cmd, lang=lang):
                    self.assertIn("rein:tono", self.cli(cmd, "--lang", "en", lang=lang).stdout)
        a, b = self.proyecto("a"), self.proyecto("b")
        self.cli("install", a, "--lang", "en", "--estado", self.nota, lang="en_US.UTF-8")
        self.cli("install", b, "--lang", "es", "--state", self.nota, lang="es_AR.UTF-8")
        self.assertTrue((a / "ORCHESTRATOR.md").is_symlink())
        self.assertTrue((b / "ORQUESTADOR.md").is_symlink())
        self.cli("global", "--lang", "en", "--sin-tono", lang="en_US.UTF-8")
        self.assertFalse((self.home / ".claude/output-styles/rein.md").exists())
        self.cli("global", "--remove", lang="es_AR.UTF-8")
        self.cli("global", "--lang", "es", "--no-tone", lang="es_AR.UTF-8")
        self.assertFalse((self.home / ".claude/output-styles/rein.md").exists())
        self.cli("global", "--quitar", lang="en_US.UTF-8")
        en = self.cli("--help", lang="en_US.UTF-8").stdout + self.cli("install", "--help", lang="en_US.UTF-8").stdout \
            + self.cli("global", "--help", lang="en_US.UTF-8").stdout
        for nombre in ("tone", "--state", "--no-tone", "--remove"):
            self.assertIn(nombre, en)
        for nombre in ("tono", "--estado", "--sin-tono", "--quitar"):
            self.assertNotIn(nombre, en)
        es = self.cli("--help", lang="es_AR.UTF-8").stdout + self.cli("install", "--help", lang="es_AR.UTF-8").stdout \
            + self.cli("global", "--help", lang="es_AR.UTF-8").stdout
        for nombre in ("tono", "--estado", "--sin-tono", "--quitar"):
            self.assertIn(nombre, es)
        for nombre in ("--state", "--no-tone", "--remove"):
            self.assertNotIn(nombre, es)
        self.assertNotRegex(es, r"\btone\b")


if __name__ == "__main__":
    unittest.main()
