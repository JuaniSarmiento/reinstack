"""Apoyo HU-OS4: `global` sin --lang usa el idioma guardado; la locale sólo decide la primera instalación."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "reinstack.py"
VIEJO = "0.3.0"  # tests/fixtures/<versión>: la 0.3.0 congelada (antes `git archive 4bfc29c`)


class GlobalIdiomaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)

    def cli(self, *args, lang, script=SCRIPT):
        env = {k: v for k, v in os.environ.items() if k not in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG")}
        env.update(HOME=str(self.home), LANG=lang)
        r = subprocess.run([sys.executable, str(script), "global", *args], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def arbol(self):
        return {str(x.relative_to(self.home)): x.read_bytes() for x in sorted(self.home.rglob("*")) if x.is_file()}

    def test_sin_lang_conserva_el_idioma_guardado(self):
        self.cli("--lang", "en", lang="es_AR.UTF-8")
        antes = self.arbol()
        r = self.cli(lang="es_AR.UTF-8")
        self.assertEqual(self.arbol(), antes, "sin --lang no cambia nada")
        codex = (self.home / ".codex" / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("You are Rein", codex)
        self.assertIn("Rein: working method", (self.home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_global_de_la_030_sin_lang_es_espanol(self):
        destino = self.home.parent / (self.home.name + "-viejo")
        destino.mkdir()
        self.addCleanup(lambda: __import__("shutil").rmtree(destino, ignore_errors=True))
        __import__("shutil").copytree(RAIZ / "tests" / "fixtures" / VIEJO, destino, dirs_exist_ok=True)
        self.cli(lang="es_AR.UTF-8", script=destino / "reinstack.py")
        self.assertNotIn("lang", json.loads((self.home / ".rein" / "global.json").read_text(encoding="utf-8")))
        antes = self.arbol()
        self.cli(lang="C")
        despues = self.arbol()
        cambiados = [n for n in despues if despues[n] != antes.get(n)]
        self.assertEqual(cambiados, [".rein/global.json"])
        self.assertEqual(json.loads(despues[".rein/global.json"])["lang"], "es")
        self.assertIn("Rein: método de trabajo", (self.home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_lang_explicito_reemplaza(self):
        self.cli("--lang", "en", lang="es_AR.UTF-8")
        self.cli("--lang", "es", lang="en_US.UTF-8")
        self.assertIn("Rein: método de trabajo", (self.home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_primera_instalacion_usa_la_locale(self):
        self.cli(lang="en_US.UTF-8")
        self.assertIn("Rein: working method", (self.home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
