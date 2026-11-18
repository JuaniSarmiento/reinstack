"""Aceptación HU-OS9: criterios negativos (N01, N02…) dentro de cada historia, buscando el error desde el contrato.

Escrita por el orquestador ANTES de implementar; criterios aprobados por Juani el 11/11/2026. Nivel de esta historia: M.
El constructor no la modifica.
Idea: en lugar de agregar revisores o agentes (caros en tokens), cada historia trae, junto a sus C, criterios negativos:
lo que NO tiene que pasar. Se escriben y congelan con los C, antes de construir, y se ven fallar igual.
Contrato:
  C01 El método (es y en) tiene una sección «## Criterios negativos» / «## Negative criteria» que dice: identificadores N01;
      lo que no tiene que pasar (entrada inválida, algo que debe negarse, datos que no se tocan, correr dos veces, borde);
      cuántos según el nivel (S al menos 1, M 2 o 3, L recorre una lista: entradas inválidas, permisos, datos sensibles,
      idempotencia, deshacer); se congelan con los C y se ven fallar; la pregunta «¿qué implementación mala pasaría esto?».
  C02 El bloque global (es y en) nombra los criterios negativos con N01.
  C03 HISTORIAS.md instalado tiene el campo «Criterios negativos»; STORIES.md, «Negative criteria».
  C04 El perfil del orquestador (es y en) le pide escribir criterios negativos N01…; el del constructor (es y en) le dice
      que también tiene que cumplirlos.
  C05 La versión es mayor que 1.1.0 y `update` sobre una instalación 1.1.0 (tests/fixtures/1.1.0) deja el método con la sección.
Negativos:
  N01 Sin agentes nuevos: `install --agent both` instala exactamente los mismos archivos que la 1.1.0 (nada de revisores).
      Cambio de criterio (HU-OS11, Juani 11/11/2026): más exactamente el perfil rein-documentador, que corre sólo a pedido.
  N02 Sin mezclar idiomas: el método, el bloque global y los perfiles en inglés no dicen «Criterios negativos», y los
      españoles no dicen «Negative criteria».
  N03 `update` sobre una instalación 1.1.0 no toca HISTORIAS.md de la persona (sus historias son suyas).
  N04 Los niveles siguen: la tabla de Niveles conserva S, M y L y la regla «nunca baja».
Correr: python3 -m unittest tests.test_negativos -v
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
VIEJO = RAIZ / "tests" / "fixtures" / "1.1.0" / "reinstack.py"
T = RAIZ / "templates"
TITULO = {"es": "## Criterios negativos", "en": "## Negative criteria"}
OTRO = {"es": "Negative criteria", "en": "Criterios negativos"}
CLAVES = {
    "es": ["N01", "no tiene que pasar", "inválid", "negarse", "dos veces", "S", "M", "L", "permisos", "sensibles",
           "idempotencia", "deshacer", "congel", "fallar", "implementación mala"],
    "en": ["N01", "must not happen", "invalid", "refuse", "twice", "S", "M", "L", "permissions", "sensitive",
           "idempoten", "undo", "frozen", "fail", "bad implementation"],
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


def plantilla(lang: str, nombre: str) -> Path:
    return T / nombre if lang == "es" else T / "en" / nombre


class NegativosTests(unittest.TestCase):
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

    def proyecto(self, nombre: str) -> Path:
        p = self.base / nombre
        p.mkdir()
        return p

    def test_c01_metodo(self):
        for lang in ("es", "en"):
            with self.subTest(lang=lang):
                s = seccion(plantilla(lang, "METODO.md").read_text(encoding="utf-8"), TITULO[lang])
                self.assertTrue(s, f"existe {TITULO[lang]}")
                for clave in CLAVES[lang]:
                    if len(clave) == 1:
                        self.assertRegex(s, rf"\b{clave}\b", clave)
                    else:
                        self.assertIn(clave, s)

    def test_c02_global(self):
        for lang in ("es", "en"):
            with self.subTest(lang=lang):
                texto = plantilla(lang, "global.md").read_text(encoding="utf-8")
                self.assertIn("N01", texto)
                self.assertIn("negativ" if lang == "es" else "negative", texto.lower())

    def test_c03_plantilla_de_historias(self):
        for lang, nombre, campo in (("es", "HISTORIAS.md", "Criterios negativos"), ("en", "STORIES.md", "Negative criteria")):
            with self.subTest(lang=lang):
                p = self.proyecto(lang)
                self.cli("install", p, "--agent", "claude", "--lang", lang)
                self.assertIn(campo, (p / nombre).read_text(encoding="utf-8"))

    def test_c04_perfiles(self):
        for lang, palabra in (("es", "negativ"), ("en", "negative")):
            with self.subTest(lang=lang):
                orq = plantilla(lang, "orchestrator.md").read_text(encoding="utf-8")
                self.assertIn("N01", orq)
                self.assertIn(palabra, orq.lower())
                self.assertIn(palabra, plantilla(lang, "constructor.md").read_text(encoding="utf-8").lower())

    def test_c05_version_y_update(self):
        actual = self.cli("--version").strip()
        self.assertGreater(version(actual), (1, 1, 0))
        p = self.proyecto("viejo")
        self.cli("install", p, "--agent", "both", "--lang", "es", script=VIEJO)
        self.assertNotIn(TITULO["es"], (p / ".rein" / "METODO.md").read_text(encoding="utf-8"))
        self.cli("update", p)
        self.assertIn(TITULO["es"], (p / ".rein" / "METODO.md").read_text(encoding="utf-8"))
        self.assertEqual(json.loads((p / ".rein" / "manifest.json").read_text(encoding="utf-8"))["version"], actual)

    def test_n01_sin_agentes_nuevos(self):
        for lang in ("es", "en"):
            with self.subTest(lang=lang):
                a, b = self.proyecto("nuevo-" + lang), self.proyecto("previo-" + lang)
                self.cli("install", a, "--agent", "both", "--lang", lang)
                self.cli("install", b, "--agent", "both", "--lang", lang, script=VIEJO)
                archivos = lambda r: sorted(str(x.relative_to(r)) for x in r.rglob("*") if x.is_file())
                # HU-OS11 (Juani, 11/11/2026): exactamente un perfil más, rein-documentador, que corre sólo a pedido.
                documentador = [".claude/agents/rein-documentador.md", ".codex/agents/rein-documentador.toml"]
                self.assertEqual(archivos(a), sorted(archivos(b) + documentador))

    def test_n02_sin_mezclar_idiomas(self):
        for lang in ("es", "en"):
            for nombre in ("METODO.md", "global.md", "orchestrator.md", "constructor.md"):
                with self.subTest(lang=lang, archivo=nombre):
                    self.assertNotIn(OTRO[lang], plantilla(lang, nombre).read_text(encoding="utf-8"))

    def test_n03_update_no_toca_historias(self):
        p = self.proyecto("con-historias")
        self.cli("install", p, "--agent", "both", "--lang", "es", script=VIEJO)
        h = p / "HISTORIAS.md"
        h.write_text(h.read_text(encoding="utf-8") + "\n| HU-1 | algo mío | S | baja | Pendiente |\n", encoding="utf-8")
        antes = h.read_bytes()
        self.cli("update", p)
        self.assertEqual(h.read_bytes(), antes)

    def test_n04_niveles_siguen(self):
        for lang, titulo, regla in (("es", "## Niveles", "nunca baja"), ("en", "## Levels", "never goes down")):
            with self.subTest(lang=lang):
                s = seccion(plantilla(lang, "METODO.md").read_text(encoding="utf-8"), titulo)
                for nivel in ("S", "M", "L"):
                    self.assertRegex(s, rf"\b{nivel}\b")
                self.assertIn(regla, s)


if __name__ == "__main__":
    unittest.main()
