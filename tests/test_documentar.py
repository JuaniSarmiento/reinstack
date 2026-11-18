"""Aceptación HU-OS11: base de conocimiento viva. Rol rein-documentador, cierre K01 y explicación simple.

Escrita por el orquestador ANTES de implementar; criterios aceptados por adelantado por Juani el 11/11/2026. Nivel: M.
El constructor no la modifica.
Origen: la migración de PropTech (opsx + Active Stack v2) a Rein. Juani: la base de conocimiento es buena, lo caro eran los
agentes que corrían en cada historia. El documentador corre sólo a pedido.
Contrato:
  C01 Perfil `rein-documentador` (templates/documentador.md y templates/en/documentador.md) instalado por `install` y por
      `global`, en Claude (.md) y Codex (.toml). Dice: corre sólo a pedido (al subir de modo o documentar lo que falta),
      lee código y Git con un tope, propone la base archivo por archivo separando evidencia de supuestos, la persona
      confirma cada archivo, y nunca modifica código ni pruebas.
  C02 `update` sobre una instalación 1.3.0 (tests/fixtures/1.3.0) agrega el perfil del documentador sin tocar nada más
      de la persona.
  C03 El método (es y en) tiene «## Cierre de la base» / «## Knowledge close»: cada historia trae K01… (qué entra a la
      base: una regla, una decisión, una lección, o «nada, porque…»); si algo salió mal, la lección es obligatoria; la
      persona puede sacar el K y queda anotado; una historia no pasa a Lista con un K sin cumplir. Y nombra al
      rein-documentador con «a pedido» / «on request».
  C04 La plantilla de historias tiene «Cierre de la base (K01…» / «Knowledge close (K01…»; el bloque global nombra K01;
      el orquestador pide escribir K01 y el constructor cumplirlo.
  C05 El tono de Rein (templates/estilo/rein.es.md y rein.en.md) le pide cerrar cada explicación técnica con un párrafo
      simple («párrafo simple» / «plain paragraph»).
  C06 El método y el bloque global (es y en) ya no piden «revisión adversarial» / «adversarial review»: en L van
      criterios negativos por lista (decisión del 11/11). La versión es mayor que 1.3.0.
Negativos:
  N01 Sólo tres roles: install instala orchestrator, constructor y documentador, y ningún otro perfil.
  N02 `update` desde 1.3.0 no toca HISTORIAS.md, CONTEXTO.md ni la base (conocimiento/) de la persona.
  N03 Deshacer: `uninstall` quita el perfil del documentador y `global --quitar` también.
  N04 Sin mezclar idiomas: las plantillas inglesas nuevas no dicen «Cierre de la base», «párrafo» ni «a pedido», y las
      españolas no dicen «Knowledge close», «plain paragraph» ni «on request».
Cambio de criterio registrado: tests/test_negativos.py N01 (HU-OS9) pasa a aceptar exactamente un perfil más,
rein-documentador, por decisión de Juani del 11/11/2026 (mismo commit que esta aceptación).
Correr: python3 -m unittest tests.test_documentar -v
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
VIEJO = RAIZ / "tests" / "fixtures" / "1.3.0" / "reinstack.py"
T = RAIZ / "templates"
LOCALE = {"es": "es_AR.UTF-8", "en": "en_US.UTF-8"}
PERFILES = [".claude/agents/rein-orchestrator.md", ".claude/agents/rein-constructor.md", ".claude/agents/rein-documentador.md",
            ".codex/agents/rein-orchestrator.toml", ".codex/agents/rein-constructor.toml", ".codex/agents/rein-documentador.toml"]
DOC = {"es": ["a pedido", "código", "Git", "tope", "evidencia", "supuesto", "confirma", "nunca", "pruebas"],
       "en": ["on request", "code", "Git", "limit", "evidence", "assumption", "confirm", "never", "tests"]}
CIERRE = {"es": ("## Cierre de la base", ["K01", "regla", "decisión", "lección", "nada, porque", "obligatoria", "sacar", "Lista",
                                          "rein-documentador", "a pedido"]),
          "en": ("## Knowledge close", ["K01", "rule", "decision", "lesson", "nothing, because", "mandatory", "remove", "Ready",
                                        "rein-documentador", "on request"])}
PROPIAS = {"es": ["Cierre de la base", "párrafo", "a pedido"], "en": ["Knowledge close", "plain paragraph", "on request"]}


def plantilla(lang: str, nombre: str) -> Path:
    return T / nombre if lang == "es" else T / "en" / nombre


def seccion(texto: str, titulo: str) -> str:
    i = texto.find(titulo + "\n")
    if i < 0:
        return ""
    resto = texto[i + len(titulo):]
    m = re.search(r"(?m)^## ", resto)
    return resto[: m.start()] if m else resto


def foto(raiz: Path) -> dict:
    return {str(x.relative_to(raiz)): x.read_bytes() for x in sorted(raiz.rglob("*")) if x.is_file()}


class DocumentarTests(unittest.TestCase):
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

    def proyecto(self, nombre="p") -> Path:
        p = self.base / nombre
        p.mkdir()
        return p

    def test_c01_perfil_documentador(self):
        for lang in ("es", "en"):
            with self.subTest(lang=lang):
                archivo = plantilla(lang, "documentador.md")
                self.assertTrue(archivo.is_file(), archivo)
                texto = archivo.read_text(encoding="utf-8")
                for clave in DOC[lang]:
                    self.assertIn(clave, texto)
                p = self.proyecto("doc-" + lang)
                self.ok("install", p, "--agent", "both", "--lang", lang, lang=lang)
                for rel in (".claude/agents/rein-documentador.md", ".codex/agents/rein-documentador.toml"):
                    self.assertTrue((p / rel).is_file(), rel)
        self.ok("global", "--lang", "es")
        for rel in (".claude/agents/rein-documentador.md", ".codex/agents/rein-documentador.toml"):
            self.assertTrue((self.home / rel).is_file(), rel)

    def test_c02_update_agrega_el_perfil(self):
        p = self.proyecto()
        self.ok("install", p, "--agent", "both", "--lang", "es", script=VIEJO)
        self.assertFalse((p / ".claude/agents/rein-documentador.md").exists())
        self.ok("update", p)
        for rel in (".claude/agents/rein-documentador.md", ".codex/agents/rein-documentador.toml"):
            self.assertTrue((p / rel).is_file(), rel)
        self.ok("doctor", p)

    def test_c03_metodo_cierre(self):
        for lang in ("es", "en"):
            with self.subTest(lang=lang):
                titulo, claves = CIERRE[lang]
                s = seccion(plantilla(lang, "METODO.md").read_text(encoding="utf-8"), titulo)
                self.assertTrue(s, titulo)
                for clave in claves:
                    self.assertIn(clave, s)

    def test_c04_plantilla_global_y_perfiles(self):
        for lang, nombre, campo in (("es", "HISTORIAS.md", "Cierre de la base (K01"), ("en", "STORIES.md", "Knowledge close (K01")):
            with self.subTest(lang=lang):
                p = self.proyecto("h-" + lang)
                self.ok("install", p, "--agent", "claude", "--lang", lang, lang=lang)
                self.assertIn(campo, (p / nombre).read_text(encoding="utf-8"))
                for archivo in ("global.md", "orchestrator.md", "constructor.md"):
                    self.assertIn("K01", plantilla(lang, archivo).read_text(encoding="utf-8"), archivo)

    def test_c05_tono_parrafo_simple(self):
        for lang, frase in (("es", "párrafo simple"), ("en", "plain paragraph")):
            with self.subTest(lang=lang):
                self.assertIn(frase, (T / "estilo" / f"rein.{lang}.md").read_text(encoding="utf-8"))

    def test_c06_sin_revision_adversarial_y_version(self):
        for lang, frase in (("es", "revisión adversarial"), ("en", "adversarial review")):
            for archivo in ("METODO.md", "global.md"):
                with self.subTest(lang=lang, archivo=archivo):
                    self.assertNotIn(frase, plantilla(lang, archivo).read_text(encoding="utf-8").lower())
        v = tuple(int(x) for x in self.ok("--version").strip().split("."))
        self.assertGreater(v, (1, 3, 0))

    def test_n01_solo_tres_roles(self):
        p = self.proyecto()
        self.ok("install", p, "--agent", "both", "--lang", "es")
        agentes = sorted(str(x.relative_to(p)) for d in (".claude/agents", ".codex/agents") for x in (p / d).iterdir())
        self.assertEqual(agentes, sorted(PERFILES))

    def test_n02_update_no_toca_lo_de_la_persona(self):
        p = self.proyecto()
        self.ok("install", p, "--agent", "both", "--lang", "es", "--contexto", "media", script=VIEJO)
        (p / "HISTORIAS.md").write_text("# Historias\n\n| HU-1 | mía | S | baja | Pendiente |\n", encoding="utf-8")
        (p / "conocimiento" / "reglas.md").write_text("# Reglas\n\nR01 mía.\n", encoding="utf-8")
        texto = (p / "CONTEXTO.md").read_text(encoding="utf-8")
        (p / "CONTEXTO.md").write_text("Mío arriba.\n\n" + texto, encoding="utf-8")
        antes = {k: v for k, v in foto(p).items() if k in ("HISTORIAS.md", "CONTEXTO.md") or k.startswith("conocimiento/")}
        self.ok("update", p)
        despues = {k: v for k, v in foto(p).items() if k in antes}
        self.assertEqual(despues, antes)

    def test_n03_deshacer(self):
        p = self.proyecto()
        self.ok("install", p, "--agent", "both", "--lang", "es")
        self.ok("uninstall", p)
        for rel in (".claude/agents/rein-documentador.md", ".codex/agents/rein-documentador.toml"):
            self.assertFalse((p / rel).exists(), rel)
        self.ok("global", "--lang", "es")
        self.assertTrue((self.home / ".claude/agents/rein-documentador.md").is_file())
        self.ok("global", "--quitar")
        for rel in (".claude/agents/rein-documentador.md", ".codex/agents/rein-documentador.toml"):
            self.assertFalse((self.home / rel).exists(), rel)

    def test_n04_sin_mezclar_idiomas(self):
        for lang, otro in (("es", "en"), ("en", "es")):
            archivos = [plantilla(lang, n) for n in ("documentador.md", "METODO.md", "global.md", "orchestrator.md", "constructor.md")]
            archivos.append(T / "estilo" / f"rein.{lang}.md")
            for archivo in archivos:
                with self.subTest(lang=lang, archivo=archivo.name):
                    self.assertTrue(archivo.is_file(), archivo)
                    texto = archivo.read_text(encoding="utf-8")
                    for frase in PROPIAS[otro]:
                        self.assertNotIn(frase, texto)


if __name__ == "__main__":
    unittest.main()
