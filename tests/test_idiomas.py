"""Aceptación HU-OS4: todo en español e inglés (plantillas, instalación por proyecto, instalación global y mensajes).

Escrita por el orquestador ANTES de implementar; criterios aprobados por Juani el 11/11/2026. El constructor no la modifica.
Ronda 2 (11/11, pedido de Juani en la demo): en inglés los archivos instalados se llaman en inglés (CONTEXT.md, .rein/METHOD.md…); ver tests/test_nombres_en.py.
El español sigue en templates/ (raíz) y templates/estilo/rein.es.md; el inglés va en templates/en/ y templates/estilo/rein.en.md.
Idioma por defecto: el de la locale (LC_ALL, si no LC_MESSAGES, si no LANG): si empieza con "es" es español; si no, inglés.
Contrato:
  C01 templates/en/ tiene METODO.md, orchestrator.md, constructor.md y global.md, con la misma cantidad de títulos
      (líneas que empiezan con «#») que su par en español.
  C02 `install --lang en` instala .rein/METHOD.md igual a templates/en/METODO.md, CONTEXT.md con «## Problem»,
      «## Who it's for», «## What it is and isn't», «## Domain rules», «## Glossary», «## Stack and decisions», y el
      manifiesto guarda "lang": "en". Sin --lang, LANG=en_US.UTF-8 da inglés y LANG=es_AR.UTF-8 da español.
  C03 `update` conserva el idioma instalado (aunque la locale diga otro); una instalación 0.3.0 (commit 4bfc29c) queda en español.
  C04 `global --lang en` instala el bloque, los perfiles y el estilo en inglés (el bloque de tono de Codex dice «You are Rein»);
      repetirlo no cambia nada; `global --lang es` lo vuelve al español reemplazando sólo dentro de las marcas.
  C05 Con la locale en inglés, `--help` y los errores salen en inglés.
  C06 El inglés instalado no tiene restos de español (sin contar los nombres de archivo en mayúsculas).
  C07 Con `--lang es`, lo instalado es el texto de las plantillas en español (HU-OS8, con OK de Juani: antes exigía bytes iguales a la 0.3.0).
  C08 `--version` es la de pyproject.toml (HU-OS8: sin números fijos).
Correr: python3 -m unittest tests.test_idiomas -v   (la 0.3.0 vive en tests/fixtures/0.3.0).
"""
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import unittest

RAIZ = Path(__file__).resolve().parents[1]
VERSION_ACTUAL = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]  # HU-OS8: sin números fijos
SCRIPT = RAIZ / "reinstack.py"
VIEJO = "0.3.0"  # tests/fixtures/<versión>: la 0.3.0 congelada (antes `git archive 4bfc29c`)
CONTEXTO_EN = ["## Problem", "## Who it's for", "## What it is and isn't", "## Domain rules", "## Glossary", "## Stack and decisions"]
ESPANOL = re.compile(r"\b(que|el|los|las|para|historia|historias|con|una|del|según|también|sólo|orquestador|método)\b", re.I)
NOMBRES = re.compile(r"`?\.?[\w./-]*\b(CONTEXTO|ORQUESTADOR|HISTORIAS|METODO)\.md`?|rein-(constructor|orchestrator)")
INI, FIN = "<!-- rein:global -->", "<!-- /rein:global -->"


def restos(texto: str) -> list[str]:
    return sorted(set(m.group(0).lower() for m in ESPANOL.finditer(NOMBRES.sub(" ", texto))))


class IdiomasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()  # HU-OS7: los scripts viejos de tests/fixtures rechazan padres enlazados (/var en macOS)
        self.home = self.base / "home"
        (self.home / ".claude").mkdir(parents=True)
        (self.home / ".codex").mkdir(parents=True)

    def env(self, lang="es_AR.UTF-8"):
        e = {k: v for k, v in os.environ.items() if k not in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG")}
        return {**e, "HOME": str(self.home), "LANG": lang}

    def cli(self, *args, lang="es_AR.UTF-8", script=SCRIPT, ok=True):
        r = subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True, env=self.env(lang), timeout=60)
        if ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def proyecto(self, nombre="p") -> Path:
        p = self.base / nombre
        p.mkdir()
        return p

    def viejo(self) -> Path:
        destino = self.base / "viejo"
        if not destino.exists():
            destino.mkdir()
            __import__("shutil").copytree(RAIZ / "tests" / "fixtures" / VIEJO, destino, dirs_exist_ok=True)
        return destino / "reinstack.py"

    def manifiesto(self, p: Path) -> dict:
        return json.loads((p / ".rein" / "manifest.json").read_text(encoding="utf-8"))

    def arbol(self, raiz: Path, fuera=()) -> dict:
        return {str(x.relative_to(raiz)): x.read_bytes() for x in sorted(raiz.rglob("*"))
                if x.is_file() and str(x.relative_to(raiz)) not in fuera}

    def test_c01_plantillas_en(self):
        for nombre in ("METODO.md", "orchestrator.md", "constructor.md", "global.md"):
            with self.subTest(nombre=nombre):
                en = RAIZ / "templates" / "en" / nombre
                self.assertTrue(en.is_file(), f"existe templates/en/{nombre}")
                titulos = lambda t: sum(1 for l in t.splitlines() if l.startswith("#"))
                self.assertEqual(titulos(en.read_text(encoding="utf-8")), titulos((RAIZ / "templates" / nombre).read_text(encoding="utf-8")))

    def test_c02_install_en_y_locale(self):
        p = self.proyecto()
        self.cli("install", p, "--agent", "both", "--lang", "en")
        self.assertTrue((p / ".rein" / "METHOD.md").is_file(), "existe .rein/METHOD.md")
        self.assertEqual((p / ".rein" / "METHOD.md").read_bytes(), (RAIZ / "templates" / "en" / "METODO.md").read_bytes())
        titulos = [l.strip() for l in (p / "CONTEXT.md").read_text(encoding="utf-8").splitlines() if l.startswith("## ")]
        self.assertEqual(titulos, CONTEXTO_EN)
        self.assertEqual(self.manifiesto(p).get("lang"), "en")
        q = self.proyecto("q")
        self.cli("install", q, "--agent", "claude", lang="en_US.UTF-8")
        self.assertEqual(self.manifiesto(q).get("lang"), "en", "locale inglesa → inglés")
        r = self.proyecto("r")
        self.cli("install", r, "--agent", "claude", lang="es_AR.UTF-8")
        self.assertEqual(self.manifiesto(r).get("lang"), "es", "locale española → español")
        self.assertEqual((r / ".rein" / "METODO.md").read_bytes(), (RAIZ / "templates" / "METODO.md").read_bytes())

    def test_c03_update_conserva_idioma(self):
        p = self.proyecto()
        self.cli("install", p, "--agent", "both", "--lang", "en")
        self.cli("update", p, lang="es_AR.UTF-8")
        self.assertEqual(self.manifiesto(p).get("lang"), "en")
        self.assertTrue((p / ".rein" / "METHOD.md").is_file(), "existe .rein/METHOD.md")
        self.assertEqual((p / ".rein" / "METHOD.md").read_bytes(), (RAIZ / "templates" / "en" / "METODO.md").read_bytes())
        v = self.proyecto("v")
        self.cli("install", v, "--agent", "both", script=self.viejo())
        self.cli("update", v, lang="en_US.UTF-8")
        self.assertEqual(self.manifiesto(v).get("lang"), "es", "una 0.3.0 se toma como español")
        self.assertEqual((v / ".rein" / "METODO.md").read_bytes(), (RAIZ / "templates" / "METODO.md").read_bytes())

    def test_c04_global_en(self):
        self.cli("global", "--lang", "en")
        claude = (self.home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
        codex = (self.home / ".codex" / "AGENTS.md").read_text(encoding="utf-8")
        en_global = (RAIZ / "templates" / "en" / "global.md").read_text(encoding="utf-8").strip()
        self.assertIn(en_global, claude)
        self.assertIn(en_global, codex)
        self.assertIn("You are Rein", codex)
        self.assertIn("You are Rein", (self.home / ".claude" / "output-styles" / "rein.md").read_text(encoding="utf-8"))
        perfil = (self.home / ".claude" / "agents" / "rein-constructor.md").read_text(encoding="utf-8")
        self.assertEqual(restos(perfil.split("---", 2)[-1]), [], "perfil en inglés")
        una = self.arbol(self.home)
        self.cli("global", "--lang", "en")
        self.assertEqual(self.arbol(self.home), una, "repetir no cambia nada")
        self.cli("global", "--lang", "es")
        claude = (self.home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("Rein: método de trabajo", claude)
        self.assertNotIn(en_global, claude)
        self.assertEqual(claude.count(INI), 1)
        self.assertIn("Sos Rein", (self.home / ".claude" / "output-styles" / "rein.md").read_text(encoding="utf-8"))

    def test_c05_mensajes_en(self):
        ayuda = self.cli("--help", lang="en_US.UTF-8").stdout
        self.assertEqual(restos(ayuda), [], f"ayuda en inglés: {restos(ayuda)}")
        self.assertIn("install", ayuda)
        malo = self.cli("install", self.base / "no-existe", lang="en_US.UTF-8", ok=False)
        self.assertNotEqual(malo.returncode, 0)
        self.assertIn("Error", malo.stderr)
        self.assertEqual(restos(malo.stderr), [], f"error en inglés: {malo.stderr}")
        ok = self.cli("install", self.proyecto(), "--agent", "claude", lang="en_US.UTF-8").stdout
        self.assertEqual(restos(ok), [], f"salida en inglés: {ok}")

    def test_c06_ingles_sin_restos(self):
        p = self.proyecto()
        self.cli("install", p, "--agent", "both", "--lang", "en")
        for f in sorted(p.rglob("*")):
            if f.is_file() and f.name != "manifest.json":
                with self.subTest(archivo=str(f.relative_to(p))):
                    self.assertEqual(restos(f.read_text(encoding="utf-8")), [])
        for f in sorted((RAIZ / "templates" / "en").rglob("*")):
            if f.is_file():
                with self.subTest(plantilla=f.name):
                    self.assertEqual(restos(f.read_text(encoding="utf-8")), [])

    def test_c07_espanol_es_la_plantilla(self):
        p = self.proyecto("es")
        self.cli("install", p, "--agent", "both", "--lang", "es")
        self.assertEqual((p / ".rein" / "METODO.md").read_bytes(), (RAIZ / "templates" / "METODO.md").read_bytes())
        self.assertTrue((p / "CONTEXTO.md").is_file() and (p / "HISTORIAS.md").is_file())
        self.cli("global", "--lang", "es")
        bloque = (RAIZ / "templates" / "global.md").read_text(encoding="utf-8").strip()
        self.assertIn(bloque, (self.home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertIn(bloque, (self.home / ".codex" / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn("Sos Rein", (self.home / ".claude" / "output-styles" / "rein.md").read_text(encoding="utf-8"))

    def test_c08_version(self):
        self.assertEqual(self.cli("--version").stdout.strip(), VERSION_ACTUAL)


if __name__ == "__main__":
    unittest.main()
