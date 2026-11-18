"""Aceptación HU-OS10: modos de base de conocimiento (simple, media, completa o una ruta existente) y cambio de modo.

Escrita por el orquestador ANTES de implementar; criterios aceptados por adelantado por Juani el 11/11/2026. Nivel: L
(toca documentos de la persona en proyectos existentes: no se puede perder una línea). El constructor no la modifica.

Diseño:
  - `install` y `update` aceptan `--contexto` (alias inglés `--context`) con simple | media | completa | <ruta>.
    En inglés los valores son simple | medium | full; los dos juegos de valores valen en cualquier idioma.
  - media: carpeta `conocimiento/` (en: `knowledge/`) con reglas.md, decisiones.md, lecciones.md
    (en: rules.md, decisions.md, lessons.md).
  - completa: además problema.md, alcance.md, modelo.md, arquitectura.md, glosario.md
    (en: problem.md, scope.md, model.md, architecture.md, glossary.md). Ocho en total.
  - <ruta>: un directorio o archivo existente (relativo al proyecto o absoluto) que ya es la base. No se crea nada en él.
  - El índice vive en CONTEXTO.md (en: CONTEXT.md) dentro de un bloque `<!-- rein:base -->` … `<!-- /rein:base -->`,
    con un enlace markdown relativo por archivo (o a la ruta). Rein sólo escribe dentro del bloque; el resto es de la persona.
    En modo simple no hay bloque.
  - Los archivos de la base son documentos del proyecto: se siembran si faltan, nunca se pisan, `uninstall` no los borra.
  - Subir de modo vale (simple → media → completa, o saltando). Bajar no: lo hace la persona a mano. <ruta> sólo desde simple.
Contrato:
  C01 `install --contexto media` crea los 3 archivos y el bloque con 3 enlaces que existen; en inglés `--context medium`
      crea knowledge/ con los nombres ingleses.
  C02 `install --contexto completa` crea los 8 y el bloque con 8 enlaces que existen; en inglés `full`.
  C03 `install --contexto <ruta>` con una base existente: el bloque enlaza a la ruta; no crea conocimiento/.
  C04 Sobre una instalación simple con CONTEXTO.md escrito por la persona: `update --contexto media` crea los 3 y agrega el
      bloque; después `update --contexto completa` agrega los 5 que faltan y el bloque lista los 8. `update` sin la opción
      conserva el modo y vuelve a sembrar un archivo de la base que falte.
  C05 Una instalación hecha con la 1.2.0 (tests/fixtures/1.2.0): `update` sin la opción no crea nada de la base;
      `update --contexto media` sí.
  C06 La ayuda de install y update muestra `--contexto` y simple/media/completa en español, `--context` y
      simple/medium/full en inglés. Los valores ingleses valen con la locale española y al revés.
  C07 El método (es y en) tiene una sección «## Base de conocimiento» / «## Knowledge base» que nombra los modos, cómo
      subir de modo, y que el orquestador lee el índice y abre sólo el archivo que la historia necesita
      («sólo el archivo» / «only the file»). La versión es mayor que 1.2.0.
Negativos:
  N01 Entrada inválida: `--contexto mucha` y una ruta inexistente fallan con «Error:» de Rein, nombrando el valor, sin
      escribir nada.
  N02 Bajar no se puede: completa → media, media → simple y media → <ruta> fallan con «Error:» sin tocar nada.
  N03 No se pisa nada de la persona: al subir de modo, lo que la persona escribió en CONTEXTO.md fuera del bloque y un
      conocimiento/reglas.md que ya existía quedan byte a byte iguales.
  N04 Idempotencia: repetir `update --contexto media` no cambia ningún byte y deja un solo bloque.
  N05 Bloque roto (inicio sin fin, o dos bloques) en CONTEXTO.md: `update --contexto completa` falla con «Error:» sin tocar nada.
  N06 Deshacer: `uninstall` deja conocimiento/ y lo que la persona escribió; la base en <ruta> nunca se modifica.
  N07 Sin mezclar idiomas: en inglés no aparece conocimiento/ ni nombres españoles; en español no aparece knowledge/.
Correr: python3 -m unittest tests.test_contexto -v
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "reinstack.py"
VIEJO = RAIZ / "tests" / "fixtures" / "1.2.0" / "reinstack.py"
INI, FIN = "<!-- rein:base -->", "<!-- /rein:base -->"
MEDIA = {"es": ["reglas.md", "decisiones.md", "lecciones.md"], "en": ["rules.md", "decisions.md", "lessons.md"]}
EXTRA = {"es": ["problema.md", "alcance.md", "modelo.md", "arquitectura.md", "glosario.md"],
         "en": ["problem.md", "scope.md", "model.md", "architecture.md", "glossary.md"]}
CARPETA = {"es": "conocimiento", "en": "knowledge"}
CONTEXTO = {"es": "CONTEXTO.md", "en": "CONTEXT.md"}
VALOR = {"es": {"media": "media", "completa": "completa"}, "en": {"media": "medium", "completa": "full"}}
LOCALE = {"es": "es_AR.UTF-8", "en": "en_US.UTF-8"}
MIO = "# Contexto\n\nEscrito a mano por la persona: expensas de consorcios en Mendoza.\n"


def foto(raiz: Path) -> dict:
    return {str(x.relative_to(raiz)): (x.is_symlink(), x.read_bytes() if x.is_file() and not x.is_symlink() else None)
            for x in sorted(raiz.rglob("*"))}


def bloque(texto: str) -> str:
    i, j = texto.find(INI), texto.find(FIN)
    return texto[i + len(INI): j] if 0 <= i < j else ""


def enlaces(texto: str) -> list[str]:
    return [d for d in re.findall(r"\]\(([^)\s]+)\)", texto) if not re.match(r"^(https?:|#)", d)]


class ContextoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / "home"
        (self.home / ".claude").mkdir(parents=True)
        (self.home / ".codex").mkdir(parents=True)

    def run_cli(self, *args, script=SCRIPT, lang="es"):
        env = {k: v for k, v in os.environ.items() if k not in ("LC_ALL", "LC_MESSAGES", "LANGUAGE")}
        return subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True,
                              env={**env, "HOME": str(self.home), "LANG": LOCALE[lang]}, timeout=60)

    def ok(self, *args, **kw):
        r = self.run_cli(*args, **kw)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def falla(self, raiz: Path, *args, nombra=None, **kw):
        antes = foto(raiz)
        r = self.run_cli(*args, **kw)
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("Error:", r.stderr, "falla con el error de Rein, no con uno de argparse")
        if nombra:
            self.assertIn(nombra, r.stderr)
        self.assertEqual(foto(raiz), antes, "no tocó nada")

    def proyecto(self, nombre="p") -> Path:
        p = self.base / nombre
        p.mkdir()
        return p

    def indice(self, p: Path, lang="es") -> str:
        return bloque((p / CONTEXTO[lang]).read_text(encoding="utf-8"))

    def assert_base(self, p: Path, lang: str, archivos: list[str]):
        for n in archivos:
            self.assertTrue((p / CARPETA[lang] / n).is_file(), f"existe {CARPETA[lang]}/{n}")
        b = self.indice(p, lang)
        self.assertTrue(b, "hay bloque rein:base")
        destinos = enlaces(b)
        self.assertEqual(len(destinos), len(archivos), b)
        for d in destinos:
            self.assertTrue((p / d).exists(), d)

    def test_c01_media(self):
        for lang in ("es", "en"):
            with self.subTest(lang=lang):
                p = self.proyecto("media-" + lang)
                self.ok("install", p, "--agent", "claude", "--lang", lang,
                        "--contexto" if lang == "es" else "--context", VALOR[lang]["media"], lang=lang)
                self.assert_base(p, lang, MEDIA[lang])

    def test_c02_completa(self):
        for lang in ("es", "en"):
            with self.subTest(lang=lang):
                p = self.proyecto("completa-" + lang)
                self.ok("install", p, "--agent", "claude", "--lang", lang, "--contexto", VALOR[lang]["completa"], lang=lang)
                self.assert_base(p, lang, MEDIA[lang] + EXTRA[lang])

    def test_c03_ruta(self):
        p = self.proyecto()
        kb = p / "knowledge-base"
        kb.mkdir()
        (kb / "05_reglas.md").write_text("# Reglas\nR01\n", encoding="utf-8")
        self.ok("install", p, "--agent", "claude", "--lang", "es", "--contexto", "knowledge-base")
        destinos = enlaces(self.indice(p))
        self.assertTrue(destinos, "el bloque enlaza a la base")
        self.assertTrue(all((p / d).resolve() == kb.resolve() or kb.resolve() in (p / d).resolve().parents for d in destinos), destinos)
        self.assertFalse((p / "conocimiento").exists())

    def test_c04_subir_de_modo(self):
        p = self.proyecto()
        self.ok("install", p, "--agent", "claude", "--lang", "es")
        (p / "CONTEXTO.md").write_text(MIO, encoding="utf-8")
        self.ok("update", p, "--contexto", "media")
        self.assert_base(p, "es", MEDIA["es"])
        self.ok("update", p, "--contexto", "completa")
        self.assert_base(p, "es", MEDIA["es"] + EXTRA["es"])
        (p / "conocimiento" / "glosario.md").unlink()
        self.ok("update", p)
        self.assert_base(p, "es", MEDIA["es"] + EXTRA["es"])

    def test_c05_desde_la_1_2_0(self):
        p = self.proyecto()
        self.ok("install", p, "--agent", "both", "--lang", "es", script=VIEJO)
        self.ok("update", p)
        self.assertFalse((p / "conocimiento").exists())
        self.assertNotIn(INI, (p / "CONTEXTO.md").read_text(encoding="utf-8"))
        self.ok("update", p, "--contexto", "media")
        self.assert_base(p, "es", MEDIA["es"])

    def test_c06_ayuda_y_alias(self):
        for cmd in ("install", "update"):
            with self.subTest(cmd=cmd):
                es = self.ok(cmd, "--help", lang="es")
                en = self.ok(cmd, "--help", lang="en")
                for palabra in ("--contexto", "simple", "media", "completa"):
                    self.assertIn(palabra, es)
                for palabra in ("--context ", "simple", "medium", "full"):
                    self.assertIn(palabra, en)
                self.assertNotIn("--contexto", en)
        a, b = self.proyecto("a"), self.proyecto("b")
        self.ok("install", a, "--lang", "es", "--context", "medium", lang="es")
        self.assert_base(a, "es", MEDIA["es"])
        self.ok("install", b, "--lang", "en", "--contexto", "completa", lang="en")
        self.assert_base(b, "en", MEDIA["en"] + EXTRA["en"])

    def test_c07_metodo_y_version(self):
        for lang, archivo, titulo, solo, modos in (
                ("es", RAIZ / "templates" / "METODO.md", "## Base de conocimiento", "sólo el archivo", ("simple", "media", "completa")),
                ("en", RAIZ / "templates" / "en" / "METODO.md", "## Knowledge base", "only the file", ("simple", "medium", "full"))):
            with self.subTest(lang=lang):
                texto = archivo.read_text(encoding="utf-8")
                i = texto.find(titulo + "\n")
                self.assertGreaterEqual(i, 0, titulo)
                resto = texto[i + len(titulo):]
                m = re.search(r"(?m)^## ", resto)
                s = resto[: m.start()] if m else resto
                for palabra in (*modos, solo, "update"):
                    self.assertIn(palabra, s)
        v = tuple(int(x) for x in self.ok("--version").strip().split("."))
        self.assertGreater(v, (1, 2, 0))

    def test_n01_entrada_invalida(self):
        p = self.proyecto()
        self.falla(p, "install", p, "--lang", "es", "--contexto", "mucha", nombra="mucha")
        self.falla(p, "install", p, "--lang", "es", "--contexto", "no-existe/kb", nombra="no-existe")
        self.ok("install", p, "--lang", "es")
        self.falla(p, "update", p, "--contexto", "mucha", nombra="mucha")

    def test_n02_no_baja(self):
        p = self.proyecto()
        (p / "kb").mkdir()
        self.ok("install", p, "--lang", "es", "--contexto", "completa")
        self.falla(p, "update", p, "--contexto", "media")
        q = self.proyecto("q")
        (q / "kb").mkdir()
        self.ok("install", q, "--lang", "es", "--contexto", "media")
        self.falla(q, "update", q, "--contexto", "simple")
        self.falla(q, "update", q, "--contexto", "kb")

    def test_n03_no_pisa_nada(self):
        p = self.proyecto()
        self.ok("install", p, "--agent", "claude", "--lang", "es")
        (p / "CONTEXTO.md").write_text(MIO, encoding="utf-8")
        (p / "conocimiento").mkdir()
        mias = "# Reglas\n\nR01 La expensa vence el 10.\n"
        (p / "conocimiento" / "reglas.md").write_text(mias, encoding="utf-8")
        self.ok("update", p, "--contexto", "media")
        self.ok("update", p, "--contexto", "completa")
        texto = (p / "CONTEXTO.md").read_text(encoding="utf-8")
        fuera = texto[: texto.find(INI)] + texto[texto.find(FIN) + len(FIN):]
        self.assertEqual(fuera.strip(), MIO.strip())
        self.assertEqual((p / "conocimiento" / "reglas.md").read_text(encoding="utf-8"), mias)

    def test_n04_idempotente(self):
        p = self.proyecto()
        self.ok("install", p, "--lang", "es")
        self.ok("update", p, "--contexto", "media")
        antes = foto(p)
        self.ok("update", p, "--contexto", "media")
        self.assertEqual(foto(p), antes)
        self.assertEqual((p / "CONTEXTO.md").read_text(encoding="utf-8").count(INI), 1)

    def test_n05_bloque_roto(self):
        for roto in (f"{MIO}\n{INI}\n- [reglas](conocimiento/reglas.md)\n",
                     f"{MIO}\n{INI}\n{FIN}\n\n{INI}\n{FIN}\n"):
            with self.subTest(roto=roto[-30:]):
                p = self.proyecto("roto-" + str(len(roto)))
                self.ok("install", p, "--lang", "es", "--contexto", "media")
                (p / "CONTEXTO.md").write_text(roto, encoding="utf-8")
                self.falla(p, "update", p, "--contexto", "completa", nombra="CONTEXTO.md")

    def test_n06_deshacer(self):
        p = self.proyecto()
        self.ok("install", p, "--agent", "both", "--lang", "es", "--contexto", "media")
        (p / "conocimiento" / "decisiones.md").write_text("# Decisiones\nD-001 Postgres.\n", encoding="utf-8")
        self.ok("uninstall", p)
        for n in MEDIA["es"]:
            self.assertTrue((p / "conocimiento" / n).is_file(), n)
        self.assertIn("D-001", (p / "conocimiento" / "decisiones.md").read_text(encoding="utf-8"))
        q = self.proyecto("q")
        kb = q / "kb"
        kb.mkdir()
        (kb / "reglas.md").write_text("R01\n", encoding="utf-8")
        antes = foto(kb)
        self.ok("install", q, "--agent", "both", "--lang", "es", "--contexto", "kb")
        self.ok("update", q)
        self.ok("uninstall", q)
        self.assertEqual(foto(kb), antes)

    def test_n07_sin_mezclar_idiomas(self):
        en, es = self.proyecto("en"), self.proyecto("es")
        self.ok("install", en, "--lang", "en", "--context", "full", lang="en")
        self.ok("install", es, "--lang", "es", "--contexto", "completa")
        nombres_en = {x.name for x in en.rglob("*")}
        for n in ["conocimiento", "CONTEXTO.md"] + MEDIA["es"] + EXTRA["es"]:
            self.assertNotIn(n, nombres_en)
        self.assertNotIn("conocimiento/", self.indice(en, "en"))
        self.assertFalse((es / "knowledge").exists())
        self.assertNotIn("knowledge/", self.indice(es))


if __name__ == "__main__":
    unittest.main()
