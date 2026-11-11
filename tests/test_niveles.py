"""Aceptación HU-OS8: niveles de historia (S, M, L) que deciden cuánta ceremonia lleva cada una.

Escrita por el orquestador ANTES de implementar; criterios aprobados por Juani el 11/11/2026. Nivel de esta historia: M.
El constructor no la modifica.
Contrato:
  C01 El método (templates/METODO.md y templates/en/METODO.md) tiene una sección «## Niveles» / «## Levels» que dice:
      el nivel es el mayor entre dificultad y riesgo; qué cambia en S, M y L (aceptación, quién construye, verificación, demo);
      lo que no cambia en ningún nivel (sólo la persona marca Terminada/Done, una prueba cuenta si se la vio fallar por
      aserción, todo va al tablero/board); el orquestador propone y la persona confirma; sube si crece y nunca baja.
  C02 El bloque global (templates/global.md y templates/en/global.md) tiene una sección de niveles que nombra S, M y L.
  C03 HISTORIAS.md instalado tiene la columna «Nivel» y el campo «Nivel y porqué»; STORIES.md, «Level» y «Level and why».
  C04 El perfil del orquestador (es y en) le pide proponer el nivel con su porqué al acordar cada historia.
  C05 La versión es mayor que 1.0.0 y `update` sobre una instalación 1.0.0 (tests/fixtures/1.0.0) deja el método con los niveles.
  (Publicar en el repo público con el CI verde se verifica fuera de esta prueba.)
Correr: python3 -m unittest tests.test_niveles -v
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "reinstack.py"
T = RAIZ / "templates"
CLAVES = {
    "es": ("## Niveles", ["dificultad", "riesgo", "mayor", "Terminada", "aserción", "tablero", "propone", "confirma", "sube", "nunca baja"]),
    "en": ("## Levels", ["difficulty", "risk", "higher", "Done", "assertion", "board", "proposes", "confirms", "goes up", "never goes down"]),
}


def seccion(texto: str, titulo: str) -> str:
    i = texto.find(titulo + "\n")
    if i < 0:
        return ""
    resto = texto[i + len(titulo):]
    m = re.search(r"(?m)^## ", resto)
    return resto[: m.start()] if m else resto


def version(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


class NivelesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / "home"
        (self.home / ".claude").mkdir(parents=True)
        (self.home / ".codex").mkdir(parents=True)

    def cli(self, *args, script=SCRIPT, lang="es_AR.UTF-8"):
        env = {k: v for k, v in os.environ.items() if k not in ("LC_ALL", "LC_MESSAGES", "LANGUAGE")}
        r = subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True,
                           env={**env, "HOME": str(self.home), "LANG": lang}, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def test_c01_metodo(self):
        for lang, archivo in (("es", T / "METODO.md"), ("en", T / "en" / "METODO.md")):
            with self.subTest(lang=lang):
                titulo, claves = CLAVES[lang]
                s = seccion(archivo.read_text(encoding="utf-8"), titulo)
                self.assertTrue(s, f"existe {titulo}")
                for nivel in ("S", "M", "L"):
                    self.assertRegex(s, rf"\b{nivel}\b")
                for clave in claves:
                    self.assertIn(clave, s)

    def test_c02_global(self):
        for lang, archivo in (("es", T / "global.md"), ("en", T / "en" / "global.md")):
            with self.subTest(lang=lang):
                titulo = CLAVES[lang][0]
                s = seccion(archivo.read_text(encoding="utf-8"), titulo)
                self.assertTrue(s, f"existe {titulo}")
                for nivel in ("S", "M", "L"):
                    self.assertRegex(s, rf"\b{nivel}\b")

    def test_c03_plantilla_de_historias(self):
        for lang, nombre, columna, campo in (("es", "HISTORIAS.md", "Nivel", "Nivel y porqué"), ("en", "STORIES.md", "Level", "Level and why")):
            with self.subTest(lang=lang):
                p = self.base / lang
                p.mkdir()
                self.cli("install", p, "--agent", "claude", "--lang", lang)
                texto = (p / nombre).read_text(encoding="utf-8")
                encabezado = next((l for l in texto.splitlines() if l.startswith("|") and "|---" not in l), "")
                self.assertIn(columna, [c.strip() for c in encabezado.strip("|").split("|")], encabezado)
                self.assertIn(campo, texto)

    def test_c04_orquestador(self):
        for lang, archivo, palabra in (("es", T / "orchestrator.md", "nivel"), ("en", T / "en" / "orchestrator.md", "level")):
            with self.subTest(lang=lang):
                self.assertIn(palabra, archivo.read_text(encoding="utf-8").lower())

    def test_c05_version_y_update(self):
        actual = self.cli("--version").strip()
        self.assertGreater(version(actual), (1, 0, 0))
        p = self.base / "viejo"
        p.mkdir()
        self.cli("install", p, "--agent", "both", "--lang", "es", script=RAIZ / "tests" / "fixtures" / "1.0.0" / "reinstack.py")
        self.assertNotIn("## Niveles", (p / ".rein" / "METODO.md").read_text(encoding="utf-8"))
        self.cli("update", p)
        self.assertIn("## Niveles", (p / ".rein" / "METODO.md").read_text(encoding="utf-8"))
        self.assertEqual(json.loads((p / ".rein" / "manifest.json").read_text(encoding="utf-8"))["version"], actual)


if __name__ == "__main__":
    unittest.main()
