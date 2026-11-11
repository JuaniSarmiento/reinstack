"""Aceptación HU-OS1: Rein, el personaje (tono del orquestador), en español e inglés, para Claude y Codex.

Escrita por el orquestador ANTES de implementar (pedido de Juani, 11/11/2026: "que rein sea un personaje").
El texto en español es el que Juani aprobó en la conversación. El constructor no modifica este archivo.
Contrato:
  C01 `templates/estilo/rein.es.md` y `templates/estilo/rein.en.md` son estilos de salida de Claude Code:
      frontmatter con `name: Rein`, `description` no vacía y `keep-coding-instructions: true`; título `# Rein`;
      las mismas tres secciones: es «## Cómo sos», «## Cómo hablás», «## Límites» / en «## How you are»,
      «## How you speak», «## Limits». El español abre con «Sos Rein» y dice que, si el tono choca con las reglas,
      «ganan las reglas»; el inglés abre con «You are Rein» y dice «the rules win». Los dos nombran al constructor.
  C02 Codex no tiene estilos: `python3 reinstack.py tono --lang es|en` imprime el mismo personaje SIN frontmatter,
      entre `<!-- rein:tono -->` y `<!-- /rein:tono -->`, listo para pegar en AGENTS.md aparte del bloque del método.
      Un idioma desconocido sale con código distinto de 0 y sin imprimir bloque.
Correr: python3 -m unittest tests.test_estilo -v
"""
from pathlib import Path
import subprocess
import sys
import unittest

RAIZ = Path(__file__).resolve().parents[1]
SCRIPT = RAIZ / "reinstack.py"
ESTILO = RAIZ / "templates" / "estilo"
SECCIONES = {"es": ["## Cómo sos", "## Cómo hablás", "## Límites"], "en": ["## How you are", "## How you speak", "## Limits"]}
CLAVES = {"es": ["Sos Rein", "ganan las reglas", "constructor"], "en": ["You are Rein", "the rules win", "builder"]}


def partes(texto: str) -> tuple[dict, str]:
    if not texto.startswith("---\n"):
        return {}, texto
    cabeza, _, cuerpo = texto[4:].partition("\n---\n")
    campos = {}
    for linea in cabeza.splitlines():
        clave, _, valor = linea.partition(":")
        campos[clave.strip()] = valor.strip()
    return campos, cuerpo


class EstiloTests(unittest.TestCase):
    def leer(self, lang: str) -> str:
        ruta = ESTILO / f"rein.{lang}.md"
        self.assertTrue(ruta.is_file(), f"existe {ruta.relative_to(RAIZ)}")
        return ruta.read_text(encoding="utf-8")

    def test_c01_estilo_en_dos_idiomas(self):
        for lang in ("es", "en"):
            with self.subTest(lang=lang):
                campos, cuerpo = partes(self.leer(lang))
                self.assertEqual(campos.get("name"), "Rein")
                self.assertTrue(campos.get("description"), "description no vacía")
                self.assertEqual(campos.get("keep-coding-instructions"), "true")
                self.assertIn("\n# Rein\n", "\n" + cuerpo)
                titulos = [l.strip() for l in cuerpo.splitlines() if l.startswith("## ")]
                self.assertEqual(titulos, SECCIONES[lang])
                for clave in CLAVES[lang]:
                    self.assertIn(clave, cuerpo)

    def correr(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=30)

    def test_c02_bloque_para_codex(self):
        for lang in ("es", "en"):
            with self.subTest(lang=lang):
                r = self.correr("tono", "--lang", lang)
                self.assertEqual(r.returncode, 0, r.stderr)
                salida = r.stdout.strip()
                self.assertTrue(salida.startswith("<!-- rein:tono -->"), salida[:80])
                self.assertTrue(salida.endswith("<!-- /rein:tono -->"), salida[-80:])
                self.assertNotIn("keep-coding-instructions", salida)
                self.assertNotIn("name: Rein", salida)
                _, cuerpo = partes(self.leer(lang))
                self.assertIn(cuerpo.strip(), salida, "el mismo texto del estilo, sin frontmatter")
        malo = self.correr("tono", "--lang", "fr")
        self.assertNotEqual(malo.returncode, 0)
        self.assertNotIn("rein:tono", malo.stdout)


if __name__ == "__main__":
    unittest.main()
