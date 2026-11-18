"""Aceptación HU-OS12: Rein más cercano. Tono de socio, saludo por nombre al arrancar y al volver, festejo con el dato.

Escrita por el orquestador ANTES de implementar; criterios aprobados por Juani el 15/11/2026 («dale»). Nivel: M.
Pedido de Juani: «un hola juani cómo va, qué pasó, qué querés: más cercano, más socio, más personal».
Uso personal: la 1.5.0 no se publica en el repo público. El constructor no modifica este archivo.
Contrato:
  C01 El estilo en español (templates/estilo/rein.es.md), en «## Cómo sos», presenta a Rein como «Socio»; dice que saluda
      a la persona por su «nombre» al «arrancar» y cuando «vuelve» después de una pausa, con un ejemplo que empieza «¡Hola».
  C02 Lo mismo en inglés (rein.en.md), en «## How you are»: «Partner», «name», «start», «comes back», ejemplo con «Hi».
  C03 Festeja lo que sale bien con el dato: en español una viñeta con «Festej» que dice «dato»; en inglés una con «elebrat»
      que dice «evidence», «number» o «result».
  C04 No se pierde lo que ya estaba (es/en): una pregunta a la vez, nunca «listo» sin evidencia, la decisión es de la
      persona, el párrafo simple y «ganan las reglas».
  C05 La versión es mayor que 1.4.0 (la coherencia pyproject/--version/CHANGELOG ya la cuida test_distribucion). Correr
      `global` sobre una instalación global hecha con la 1.4.0 (tests/fixtures/1.4.0) deja en ~/.claude/output-styles/rein.md
      el estilo nuevo y en ~/.codex/AGENTS.md el bloque de tono nuevo. `update` de un proyecto instalado con la 1.4.0 anda
      y `doctor` queda en verde.
Negativos:
  N01 Ningún nombre propio de la persona en las plantillas: «Juani» no aparece en ningún archivo de templates/.
  N02 No saluda en cada mensaje: el español dice «no en cada mensaje» y el inglés «not in every message».
  N03 Cercano no es chamuyo: sigue «Sin halagos» / «No flattery».
Correr: python3 -m unittest tests.test_cercano -v
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
VIEJO = RAIZ / "tests" / "fixtures" / "1.4.0" / "reinstack.py"
T = RAIZ / "templates"
LOCALE = {"es": "es_AR.UTF-8", "en": "en_US.UTF-8"}
COMO = {"es": "## Cómo sos", "en": "## How you are"}
SALUDO = {"es": ["Socio", "nombre", "arrancar", "vuelve", "¡Hola"], "en": ["Partner", "name", "start", "comes back", "Hi"]}
FESTEJO = {"es": ("Festej", ["dato"]), "en": ("elebrat", ["evidence", "number", "result"])}
QUEDA = {"es": ["Una pregunta a la vez", "sin evidencia", "La decisión es de la persona", "párrafo simple", "ganan las reglas"],
         "en": ["One question at a time", "without evidence", "The decision belongs to the person", "plain paragraph",
                "the rules win"]}
UNA_VEZ = {"es": "no en cada mensaje", "en": "not in every message"}
SIN_CHAMUYO = {"es": "Sin halagos", "en": "No flattery"}


def estilo(lang: str) -> str:
    return (T / "estilo" / f"rein.{lang}.md").read_text(encoding="utf-8")


def cuerpo(texto: str) -> str:
    return texto[4:].partition("\n---\n")[2] if texto.startswith("---\n") else texto


def seccion(texto: str, titulo: str) -> str:
    i = texto.find(titulo + "\n")
    if i < 0:
        return ""
    resto = texto[i + len(titulo):]
    m = re.search(r"(?m)^## ", resto)
    return resto[: m.start()] if m else resto


def vinetas(texto: str) -> list[str]:
    """Cada viñeta «- …» con sus líneas de continuación, en una sola cadena."""
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


class CercanoTests(unittest.TestCase):
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

    def saludo(self, lang: str):
        s = seccion(estilo(lang), COMO[lang])
        self.assertTrue(s, COMO[lang])
        for clave in SALUDO[lang]:
            self.assertIn(clave, s)

    def test_c01_socio_y_saludo_es(self):
        self.saludo("es")

    def test_c02_socio_y_saludo_en(self):
        self.saludo("en")

    def test_c03_festeja_con_el_dato(self):
        for lang in ("es", "en"):
            with self.subTest(lang=lang):
                marca, datos = FESTEJO[lang]
                items = [v for v in vinetas(estilo(lang)) if marca in v]
                self.assertTrue(items, f"una viñeta con «{marca}»")
                self.assertTrue(any(d in v for v in items for d in datos), items)

    def test_c04_no_se_pierde_nada(self):
        for lang in ("es", "en"):
            texto = estilo(lang)
            for frase in QUEDA[lang]:
                with self.subTest(lang=lang, frase=frase):
                    self.assertIn(frase, texto)

    def test_c05_version_global_y_update(self):
        v = tuple(int(x) for x in self.ok("--version").strip().split("."))
        self.assertGreater(v, (1, 4, 0))
        self.ok("global", "--agent", "both", "--lang", "es", script=VIEJO)
        self.ok("global", "--agent", "both", "--lang", "es")
        instalado = (self.home / ".claude/output-styles/rein.md").read_text(encoding="utf-8")
        self.assertEqual(instalado, estilo("es"))
        self.assertIn(cuerpo(estilo("es")).strip(), (self.home / ".codex/AGENTS.md").read_text(encoding="utf-8"))
        p = self.base / "p"
        p.mkdir()
        self.ok("install", p, "--agent", "both", "--lang", "es", script=VIEJO)
        self.ok("update", p)
        self.ok("doctor", p)

    def test_n01_sin_nombre_propio(self):
        for archivo in sorted(x for x in T.rglob("*") if x.is_file()):
            with self.subTest(archivo=str(archivo.relative_to(RAIZ))):
                self.assertNotIn("Juani", archivo.read_text(encoding="utf-8", errors="replace"))

    def test_n02_no_saluda_en_cada_mensaje(self):
        for lang in ("es", "en"):
            with self.subTest(lang=lang):
                self.assertIn(UNA_VEZ[lang], estilo(lang))

    def test_n03_sin_chamuyo(self):
        for lang in ("es", "en"):
            with self.subTest(lang=lang):
                self.assertIn(SIN_CHAMUYO[lang], estilo(lang))


if __name__ == "__main__":
    unittest.main()
