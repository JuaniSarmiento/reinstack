"""Aceptación HU-OS6: un README que venda, contado por Rein, en español e inglés.

Escrita por el orquestador ANTES de implementar; criterios aprobados por Juani el 11/11/2026. El constructor no la modifica.
La comparación con BMAD y Spec Kit (C03) y que la salida mostrada sea real (C02) los revisa el orquestador a mano.
Contrato:
  C01 Primera pantalla (primeras 40 líneas) de README.md y README.en.md: la imagen assets/rein.png, badges de CI
      (actions/workflows/tests.yml/badge.svg), licencia MIT y la versión actual (HU-OS8: la de pyproject.toml), e instalación con
      `uvx --from git+https://github.com/JuaniSarmiento/reinstack reinstack` y `reinstack global`.
  C08 Lo cuenta Rein: el primer párrafo de texto dice «Soy Rein» (es) / «I'm Rein» (en).
  C02 Una sección «… de punta a punta» / «… end to end» con bloques de código y que nombra el SHA y Terminada / Done.
  C03 Una tabla que compara con BMAD y Spec Kit, con la fecha de la comparación (2026).
  C04 Una sección que presenta a Rein con un ejemplo de cómo habla (cita con «>»).
  C05 GUIA.en.md existe con la misma cantidad de títulos que GUIA.md.
  C06 Los dos README tienen la misma cantidad de secciones «## »; todo enlace o imagen relativa existe; cada línea de un
      bloque ```sh que empieza con `reinstack ` corre bien (como `python3 reinstack.py …`) en un proyecto y HOME temporales.
  C07 assets/demo.gif es un GIF real de menos de 5 MB, enlazado desde los dos README.
  La imagen assets/rein.png es PNG de menos de 300 KB y no queda assets/rein-v1.png.
Correr: python3 -m unittest tests.test_readme -v
"""
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import tomllib
import unittest

RAIZ = Path(__file__).resolve().parents[1]
VERSION_ACTUAL = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]  # HU-OS8: sin números fijos
READMES = {"es": RAIZ / "README.md", "en": RAIZ / "README.en.md"}
FIRMA = {"es": "Soy Rein", "en": "I'm Rein"}
PUNTA = {"es": re.compile(r"^## .*punta a punta", re.M | re.I), "en": re.compile(r"^## .*end to end", re.M | re.I)}
CIERRE = {"es": "Terminada", "en": "Done"}


def leer(lang):
    p = READMES[lang]
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def seccion(texto: str, patron: re.Pattern) -> str:
    m = patron.search(texto)
    if not m:
        return ""
    resto = texto[m.end():]
    fin = re.search(r"^## ", resto, re.M)
    return resto[: fin.start()] if fin else resto


class ReadmeTests(unittest.TestCase):
    def test_c01_primera_pantalla(self):
        for lang in READMES:
            with self.subTest(lang=lang):
                top = "\n".join(leer(lang).splitlines()[:40])
                for clave in ("assets/rein.png", "actions/workflows/tests.yml/badge.svg", "MIT", VERSION_ACTUAL,
                              "uvx --from git+https://github.com/JuaniSarmiento/reinstack reinstack", "reinstack global"):
                    self.assertIn(clave, top, clave)

    def test_c08_lo_cuenta_rein(self):
        for lang in READMES:
            with self.subTest(lang=lang):
                parrafos = [b.strip() for b in re.split(r"\n\s*\n", leer(lang))]
                texto = [b for b in parrafos if b and not b.startswith(("#", "<", "!", "[", "|", "```", ">"))]
                self.assertTrue(texto, "hay texto")
                self.assertIn(FIRMA[lang], texto[0])

    def test_c02_punta_a_punta(self):
        for lang in READMES:
            with self.subTest(lang=lang):
                s = seccion(leer(lang), PUNTA[lang])
                self.assertTrue(s, "existe la sección")
                self.assertIn("```", s)
                self.assertIn("SHA", s)
                self.assertIn(CIERRE[lang], s)

    def test_c03_comparacion(self):
        for lang in READMES:
            with self.subTest(lang=lang):
                filas = [l for l in leer(lang).splitlines() if l.startswith("|")]
                tabla = "\n".join(filas)
                self.assertIn("BMAD", tabla)
                self.assertIn("Spec Kit", tabla)
                self.assertIn("2026", leer(lang))

    def test_c04_presenta_a_rein(self):
        for lang in READMES:
            with self.subTest(lang=lang):
                t = leer(lang)
                self.assertRegex(t, r"(?m)^## .*Rein")
                self.assertRegex(t, r"(?m)^> ")

    def test_c05_guia_en(self):
        en = RAIZ / "GUIA.en.md"
        self.assertTrue(en.is_file(), "existe GUIA.en.md")
        titulos = lambda p: sum(1 for l in p.read_text(encoding="utf-8").splitlines() if l.startswith("#"))
        self.assertEqual(titulos(en), titulos(RAIZ / "GUIA.md"))

    def test_c06_paridad_y_enlaces(self):
        cuenta = {lang: len(re.findall(r"(?m)^## ", leer(lang))) for lang in READMES}
        self.assertGreater(cuenta["es"], 3)
        self.assertEqual(cuenta["es"], cuenta["en"])
        for lang in READMES:
            for destino in re.findall(r"\]\(([^)\s]+)\)|src=\"([^\"]+)\"", leer(lang)):
                d = next(x for x in destino if x)
                if re.match(r"^(https?:|mailto:|#)", d):
                    continue
                with self.subTest(lang=lang, enlace=d):
                    self.assertTrue((RAIZ / d.split("#")[0]).exists(), d)

    def test_c06_comandos_corren(self):
        comandos = []
        for lang in READMES:
            for bloque in re.findall(r"```(?:sh|bash|shell)\n(.*?)```", leer(lang), re.S):
                comandos += [l.strip() for l in bloque.splitlines() if l.strip().startswith("reinstack ")]
        self.assertTrue(comandos, "hay comandos reinstack en los README")
        for cmd in comandos:
            with self.subTest(cmd=cmd):
                self.assertNotRegex(cmd, r"<[^>]+>", "sin marcadores para completar")
                tmp = tempfile.TemporaryDirectory()
                self.addCleanup(tmp.cleanup)
                base = Path(tmp.name)
                home, proyecto = base / "home", base / "proyecto"
                (home / ".claude").mkdir(parents=True)
                (home / ".codex").mkdir(parents=True)
                proyecto.mkdir()
                (base / "nota.md").write_text("# nota\n", encoding="utf-8")
                args = [a.replace("~", str(home)) for a in shlex.split(cmd)[1:]]
                env = {k: v for k, v in os.environ.items() if k not in ("LC_ALL", "LC_MESSAGES", "LANGUAGE")}
                r = subprocess.run([sys.executable, str(RAIZ / "reinstack.py"), *args], cwd=proyecto, capture_output=True, text=True,
                                   env={**env, "HOME": str(home), "LANG": "es_AR.UTF-8"}, timeout=60)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_c07_demo_gif(self):
        gif = RAIZ / "assets" / "demo.gif"
        self.assertTrue(gif.is_file(), "existe assets/demo.gif")
        self.assertTrue(gif.read_bytes()[:6] in (b"GIF87a", b"GIF89a"))
        self.assertLess(gif.stat().st_size, 5 * 1024 * 1024)
        for lang in READMES:
            self.assertIn("assets/demo.gif", leer(lang), lang)

    def test_imagen_de_rein(self):
        png = RAIZ / "assets" / "rein.png"
        self.assertTrue(png.is_file())
        self.assertEqual(png.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        self.assertLess(png.stat().st_size, 300 * 1024)
        self.assertFalse((RAIZ / "assets" / "rein-v1.png").exists())


if __name__ == "__main__":
    unittest.main()
