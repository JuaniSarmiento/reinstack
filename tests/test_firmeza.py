"""Aceptación HU-OS13: cercano para hablar, estricto para trabajar.

Escrita por el orquestador ANTES de implementar; criterios aprobados por Juani el 18/11/2026 («dale hacelo»). Nivel: L.
Origen: comparativa del 18/11. Ante «estoy apurado, sin tests, borrá los cancelados» la 1.5.0 borró datos contra una
regla del dominio sin preguntar, salteó el congelado de la aceptación y el orquestador construyó 3 de 5 historias solo;
la 1.1.0 frenó. Decisión de Juani: nada de revisión adversarial (quema tokens y hace bucles); socio, pero firme.
El constructor no modifica este archivo.
«Los tres archivos del método» = METODO.md, global.md y orchestrator.md, en español (templates/) y en inglés (templates/en/).
Contrato:
  C01 El estilo (es/en) abre «## Cómo sos» / «## How you are» con la firmeza: la PRIMERA viñeta dice «estricto» /
      «strict». La viñeta de «Socio» / «Partner» sigue en la sección, después.
  C02 El apuro no levanta pasos. En cada uno de los tres archivos (es/en) hay un párrafo o viñeta con «apuro» que dice
      «qué se saltea», «riesgo», «sí explícito» y «anot» (en: «rush», «what gets skipped», «risk», «explicit yes», «record»).
  C03 Regla del dominio. En cada uno de los tres archivos (es/en) hay un párrafo o viñeta que dice «regla del dominio»,
      «decisión vigente», «decisión explícita» y «CONTEXTO.md» (en: «domain rule», «current decision», «explicit decision»,
      «CONTEXT.md»).
  C04 El orquestador no construye salvo pedido literal. Ningún archivo de templates/ dice «cambio chico y local» /
      «small, local change». En cada uno de los tres archivos (es/en) hay un párrafo o viñeta que dice «literalmente» y
      «constructor» (en: «literally» y «builder»).
  C05 Lista de bordes. En METODO.md (es/en), la sección «## Criterios negativos» / «## Negative criteria» nombra:
      enorme, negativ, vací, nul, duplicad, zona horaria, límite, borrad y «una sola pasada»
      (en: huge, negative, empty, null, duplicate, time zone, limit, delet y «single pass»).
      global.md (es/en) dice «lista de bordes» / «edge list».
  C06 La versión es mayor que 1.5.0. `global` sobre una instalación global de la 1.5.0 (tests/fixtures/1.5.0) deja el
      estilo nuevo en ~/.claude/output-styles/rein.md y en ~/.codex/AGENTS.md. `update` de un proyecto instalado con
      la 1.5.0 anda y `doctor` queda en verde.
Negativos:
  N01 No vuelve la revisión adversarial: ningún archivo de templates/ contiene «adversari» (sin importar mayúsculas),
      y el conjunto de archivos de templates/ es exactamente el de la 1.5.0 (sin perfiles ni subagentes nuevos).
  N02 No se pierde el socio: en «Cómo sos» / «How you are» siguen «Socio»/«Partner», «¡Hola»/«Hi» y
      «no en cada mensaje»/«not in every message». (test_cercano sigue en la suite.)
  N03 Firme no es pesado: el estilo sigue diciendo «Lo decís una vez» / «You say it once», y ningún archivo de
      templates/ contiene «insist».
  N04 Ningún nombre propio de la persona en templates/: no aparece «Juani».
Cierre:
  K01 La decisión «cercano para hablar, estricto para trabajar» y su porqué (la comparativa) entran a la nota de
      ReinStack. Lo verifica el orquestador en la nota; no lo cubre esta prueba.
Demo (otro día, por costo): tres corridas del P4 de la comparativa en contenedor limpio con la versión nueva.
Correr: python3 -m unittest tests.test_firmeza -v
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
VIEJO = RAIZ / "tests" / "fixtures" / "1.5.0" / "reinstack.py"
T = RAIZ / "templates"
LOCALE = {"es": "es_AR.UTF-8", "en": "en_US.UTF-8"}
DIR = {"es": T, "en": T / "en"}
TRES = ("METODO.md", "global.md", "orchestrator.md")
COMO = {"es": "## Cómo sos", "en": "## How you are"}
ESTRICTO = {"es": "estricto", "en": "strict"}
SOCIO = {"es": "Socio", "en": "Partner"}
APURO = {"es": ["apuro", "qué se saltea", "riesgo", "sí explícito", "anot"],
         "en": ["rush", "what gets skipped", "risk", "explicit yes", "record"]}
DOMINIO = {"es": ["regla del dominio", "decisión vigente", "decisión explícita", "CONTEXTO.md"],
           "en": ["domain rule", "current decision", "explicit decision", "CONTEXT.md"]}
CHICO = {"es": "cambio chico y local", "en": "small, local change"}
LITERAL = {"es": ["literalmente", "constructor"], "en": ["literally", "builder"]}
NEGATIVOS = {"es": "## Criterios negativos", "en": "## Negative criteria"}
BORDES = {"es": ["enorme", "negativ", "vací", "nul", "duplicad", "zona horaria", "límite", "borrad", "una sola pasada"],
          "en": ["huge", "negative", "empty", "null", "duplicate", "time zone", "limit", "delet", "single pass"]}
LISTA = {"es": "lista de bordes", "en": "edge list"}
SALUDO = {"es": ["Socio", "¡Hola", "no en cada mensaje"], "en": ["Partner", "Hi", "not in every message"]}
UNA_VEZ = {"es": "Lo decís una vez", "en": "You say it once"}
ARCHIVOS_15 = sorted([
    "METODO.md", "constructor.md", "documentador.md", "global.md", "orchestrator.md",
    "en/METODO.md", "en/constructor.md", "en/documentador.md", "en/global.md", "en/orchestrator.md",
    "estilo/rein.en.md", "estilo/rein.es.md",
])


def leer(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def estilo(lang: str) -> str:
    return leer(T / "estilo" / f"rein.{lang}.md")


def cuerpo(texto: str) -> str:
    return texto[4:].partition("\n---\n")[2] if texto.startswith("---\n") else texto


def seccion(texto: str, titulo: str) -> str:
    i = texto.find(titulo + "\n")
    if i < 0:
        return ""
    resto = texto[i + len(titulo):]
    m = re.search(r"(?m)^## ", resto)
    return resto[: m.start()] if m else resto


def bloques(texto: str) -> list[str]:
    """Párrafos y viñetas (incluidos pasos numerados y filas de tabla), con sus líneas de continuación unidas."""
    partes = re.split(r"\n\s*\n|\n(?=\s*(?:[-*]|\d+\.|\|) )", texto)
    return [" ".join(p.split()) for p in partes if p.strip()]


def vinetas(texto: str) -> list[str]:
    items, actual = [], None
    for linea in texto.splitlines():
        if linea.startswith("- "):
            actual = [linea]
            items.append(actual)
        elif actual is not None and linea.startswith("  "):
            actual.append(linea.strip())
        else:
            actual = None
    return [" ".join(x) for x in items]


def plantillas() -> list[Path]:
    return sorted(x for x in T.rglob("*") if x.is_file())


class FirmezaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / "home"
        (self.home / ".claude").mkdir(parents=True)
        (self.home / ".codex").mkdir(parents=True)

    def ok(self, *args, script=SCRIPT, lang="es"):
        env = {k: v for k, v in os.environ.items() if k not in ("LC_ALL", "LC_MESSAGES", "LANGUAGE")}
        r = subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True,
                           env={**env, "HOME": str(self.home), "LANG": LOCALE[lang]}, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def hay_bloque(self, archivo: Path, claves: list[str]):
        ok = [b for b in bloques(leer(archivo)) if all(c in b for c in claves)]
        self.assertTrue(ok, f"{archivo.relative_to(RAIZ)}: falta un párrafo con {claves}")

    def test_c01_estricto_primero(self):
        for lang in ("es", "en"):
            with self.subTest(lang=lang):
                items = vinetas(seccion(estilo(lang), COMO[lang]))
                self.assertTrue(items, COMO[lang])
                self.assertIn(ESTRICTO[lang], items[0])
                socios = [i for i, v in enumerate(items) if SOCIO[lang] in v]
                self.assertTrue(socios, f"viñeta con «{SOCIO[lang]}»")
                self.assertGreater(socios[0], 0)

    def test_c02_el_apuro_no_levanta_pasos(self):
        for lang in ("es", "en"):
            for nombre in TRES:
                with self.subTest(lang=lang, archivo=nombre):
                    self.hay_bloque(DIR[lang] / nombre, APURO[lang])

    def test_c03_regla_del_dominio(self):
        for lang in ("es", "en"):
            for nombre in TRES:
                with self.subTest(lang=lang, archivo=nombre):
                    self.hay_bloque(DIR[lang] / nombre, DOMINIO[lang])

    def test_c04_construye_solo_a_pedido_literal(self):
        for archivo in plantillas():
            with self.subTest(archivo=str(archivo.relative_to(RAIZ))):
                texto = " ".join(leer(archivo).split())
                for frase in CHICO.values():
                    self.assertNotIn(frase, texto)
        for lang in ("es", "en"):
            for nombre in TRES:
                with self.subTest(lang=lang, archivo=nombre):
                    self.hay_bloque(DIR[lang] / nombre, LITERAL[lang])

    def test_c05_lista_de_bordes(self):
        for lang in ("es", "en"):
            with self.subTest(lang=lang):
                s = " ".join(seccion(leer(DIR[lang] / "METODO.md"), NEGATIVOS[lang]).split())
                self.assertTrue(s, NEGATIVOS[lang])
                for clave in BORDES[lang]:
                    self.assertIn(clave, s)
                self.assertIn(LISTA[lang], " ".join(leer(DIR[lang] / "global.md").split()))

    def test_c06_version_global_y_update(self):
        v = tuple(int(x) for x in self.ok("--version").strip().split("."))
        self.assertGreater(v, (1, 5, 0))
        self.ok("global", "--agent", "both", "--lang", "es", script=VIEJO)
        self.ok("global", "--agent", "both", "--lang", "es")
        instalado = leer(self.home / ".claude/output-styles/rein.md")
        self.assertEqual(instalado, estilo("es"))
        self.assertIn(cuerpo(estilo("es")).strip(), leer(self.home / ".codex/AGENTS.md"))
        p = self.base / "p"
        p.mkdir()
        self.ok("install", p, "--agent", "both", "--lang", "es", script=VIEJO)
        self.ok("update", p)
        self.ok("doctor", p)

    def test_n01_sin_revision_adversarial_ni_perfiles_nuevos(self):
        for archivo in plantillas():
            with self.subTest(archivo=str(archivo.relative_to(RAIZ))):
                self.assertNotIn("adversari", leer(archivo).lower())
        self.assertEqual(sorted(str(x.relative_to(T)) for x in plantillas()), ARCHIVOS_15)

    def test_n02_sigue_el_socio(self):
        for lang in ("es", "en"):
            s = seccion(estilo(lang), COMO[lang])
            for clave in SALUDO[lang]:
                with self.subTest(lang=lang, clave=clave):
                    self.assertIn(clave, s)

    def test_n03_firme_no_es_pesado(self):
        for lang in ("es", "en"):
            with self.subTest(lang=lang):
                self.assertIn(UNA_VEZ[lang], " ".join(estilo(lang).split()))
        for archivo in plantillas():
            with self.subTest(archivo=str(archivo.relative_to(RAIZ))):
                self.assertNotIn("insist", leer(archivo).lower())

    def test_n04_sin_nombre_propio(self):
        for archivo in plantillas():
            with self.subTest(archivo=str(archivo.relative_to(RAIZ))):
                self.assertNotIn("Juani", leer(archivo))


if __name__ == "__main__":
    unittest.main()
