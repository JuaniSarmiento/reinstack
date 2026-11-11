"""Aceptación HU-OS3: instalación global (`reinstack global`), método y tono en Claude y Codex sin pisar lo ajeno.

Escrita por el orquestador ANTES de implementar; criterios aprobados por Juani el 11/11/2026. El constructor no la modifica.
Todo corre con HOME temporal. Archivos globales:
  Claude: ~/.claude/CLAUDE.md (bloque), ~/.claude/agents/rein-orchestrator.md y rein-constructor.md,
          ~/.claude/output-styles/rein.md, ~/.claude/settings.json ("outputStyle": "Rein").
  Codex:  ~/.codex/AGENTS.md (bloque método + bloque tono), ~/.codex/agents/rein-orchestrator.toml y rein-constructor.toml.
  Marcas: <!-- rein:global --> … <!-- /rein:global -->  y  <!-- rein:tono --> … <!-- /rein:tono -->.
Contrato:
  C01 `global --dry-run` lista lo que escribiría y no toca nada.
  C02 `global` escribe el bloque del método en los dos clientes (idéntico en ambos) sin tocar un byte fuera del bloque,
      instala los dos perfiles de cada cliente, el estilo Rein con outputStyle "Rein" conservando el resto de settings.json,
      y el bloque de tono en AGENTS.md.
  C03 Correrlo dos veces no cambia nada; un bloque viejo se reemplaza sólo dentro de sus marcas.
  C04 `--sin-tono` instala sólo el método: ni estilo, ni outputStyle, ni bloque de tono.
  C05 `--agent claude|codex` toca sólo los archivos de ese cliente.
  C06 `global --quitar` saca bloques, perfiles y estilo y devuelve el outputStyle anterior (o quita la clave si no había);
      lo ajeno queda exactamente igual.
  C07 Antes de modificar un archivo que ya existía, deja `<archivo>.rein-bak` con su contenido original.
  C08 El bloque es genérico (sin nombres de la persona ni de sus herramientas privadas, ni obsidian) y nombra CONTEXTO.md, ORQUESTADOR.md, HISTORIAS.md,
      «Cerrar antes de abrir», «Documentación al día» y que `.rein/METODO.md` del proyecto manda.
Correr: python3 -m unittest tests.test_global -v
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "reinstack.py"
INI, FIN = "<!-- rein:global -->", "<!-- /rein:global -->"
TINI, TFIN = "<!-- rein:tono -->", "<!-- /rein:tono -->"
MIO_CLAUDE = "# Mis reglas\n\n- Respondé corto.\n"
MIO_CODEX = "# Codex mío\n\nNada de emojis.\n"
SETTINGS = {"outputStyle": "Gentleman", "model": "opus", "permissions": {"deny": ["Read(.env)"]}}


def bloque(texto: str, ini=INI, fin=FIN) -> str | None:
    m = re.search(re.escape(ini) + r"(.*?)" + re.escape(fin), texto, re.S)
    return m.group(1) if m else None


def sin_bloques(texto: str) -> str:
    for ini, fin in ((INI, FIN), (TINI, TFIN)):
        texto = re.sub(r"\n*" + re.escape(ini) + r".*?" + re.escape(fin) + r"\n*", "\n", texto, flags=re.S)
    return texto.strip()


class GlobalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "home"
        (self.home / ".claude").mkdir(parents=True)
        (self.home / ".codex").mkdir(parents=True)
        self.claude = self.home / ".claude" / "CLAUDE.md"
        self.codex = self.home / ".codex" / "AGENTS.md"
        self.settings = self.home / ".claude" / "settings.json"
        self.claude.write_text(MIO_CLAUDE, encoding="utf-8")
        self.codex.write_text(MIO_CODEX, encoding="utf-8")
        self.settings.write_text(json.dumps(SETTINGS, indent=2), encoding="utf-8")

    def cli(self, *args, ok=True):
        r = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                           env={**os.environ, "HOME": str(self.home)}, timeout=60)
        if ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def foto(self):
        return {str(p.relative_to(self.home)): p.read_bytes() for p in sorted(self.home.rglob("*")) if p.is_file()}

    def leer(self, p: Path) -> str:
        return p.read_text(encoding="utf-8")

    def test_c01_dry_run(self):
        antes = self.foto()
        r = self.cli("global", "--dry-run")
        self.assertIn("CLAUDE.md", r.stdout)
        self.assertIn("AGENTS.md", r.stdout)
        self.assertEqual(self.foto(), antes, "dry-run no escribe")

    def test_c02_instala_todo(self):
        self.cli("global")
        c, x = self.leer(self.claude), self.leer(self.codex)
        self.assertIsNotNone(bloque(c), "bloque en CLAUDE.md")
        self.assertIsNotNone(bloque(x), "bloque en AGENTS.md")
        self.assertEqual(bloque(c), bloque(x), "mismo método en los dos clientes")
        self.assertEqual(sin_bloques(c), MIO_CLAUDE.strip(), "lo ajeno de CLAUDE.md intacto")
        self.assertEqual(sin_bloques(x), MIO_CODEX.strip(), "lo ajeno de AGENTS.md intacto")
        for rel in (".claude/agents/rein-orchestrator.md", ".claude/agents/rein-constructor.md",
                    ".codex/agents/rein-orchestrator.toml", ".codex/agents/rein-constructor.toml"):
            self.assertTrue((self.home / rel).is_file(), rel)
        self.assertIn("name: rein-constructor", self.leer(self.home / ".claude/agents/rein-constructor.md"))
        estilo = self.home / ".claude/output-styles/rein.md"
        self.assertTrue(estilo.is_file(), "estilo instalado")
        self.assertIn("name: Rein", self.leer(estilo))
        s = json.loads(self.leer(self.settings))
        self.assertEqual(s["outputStyle"], "Rein")
        self.assertEqual({k: v for k, v in s.items() if k != "outputStyle"}, {k: v for k, v in SETTINGS.items() if k != "outputStyle"})
        tono = bloque(x, TINI, TFIN)
        self.assertIsNotNone(tono, "bloque de tono en Codex")
        self.assertIn("Rein", tono)
        self.assertIsNone(bloque(c, TINI, TFIN), "Claude usa el estilo, no el bloque de tono")

    def test_c03_idempotente_y_reemplazo(self):
        self.cli("global")
        una = self.foto()
        self.cli("global")
        self.assertEqual(self.foto(), una, "segunda corrida sin cambios")
        viejo = self.leer(self.claude).replace(bloque(self.leer(self.claude)), "\nmétodo viejo\n")
        self.claude.write_text(viejo, encoding="utf-8")
        self.cli("global")
        c = self.leer(self.claude)
        self.assertNotIn("método viejo", c)
        self.assertEqual(c.count(INI), 1, "un solo bloque")
        self.assertEqual(sin_bloques(c), MIO_CLAUDE.strip())

    def test_c04_sin_tono(self):
        self.cli("global", "--sin-tono")
        self.assertIsNotNone(bloque(self.leer(self.claude)))
        self.assertFalse((self.home / ".claude/output-styles/rein.md").exists())
        self.assertEqual(json.loads(self.leer(self.settings))["outputStyle"], "Gentleman")
        self.assertIsNone(bloque(self.leer(self.codex), TINI, TFIN))

    def test_c05_un_cliente(self):
        codex_antes = self.leer(self.codex)
        self.cli("global", "--agent", "claude")
        self.assertIsNotNone(bloque(self.leer(self.claude)))
        self.assertEqual(self.leer(self.codex), codex_antes)
        self.assertFalse((self.home / ".codex/agents").exists())
        self.tmp.cleanup(); self.setUp()
        claude_antes, settings_antes = self.leer(self.claude), self.leer(self.settings)
        self.cli("global", "--agent", "codex")
        self.assertIsNotNone(bloque(self.leer(self.codex)))
        self.assertEqual(self.leer(self.claude), claude_antes)
        self.assertEqual(self.leer(self.settings), settings_antes)
        self.assertFalse((self.home / ".claude/agents").exists())
        self.assertFalse((self.home / ".claude/output-styles/rein.md").exists())

    def test_c06_quitar(self):
        self.cli("global")
        self.cli("global", "--quitar")
        self.assertEqual(self.leer(self.claude).strip(), MIO_CLAUDE.strip())
        self.assertEqual(self.leer(self.codex).strip(), MIO_CODEX.strip())
        self.assertEqual(json.loads(self.leer(self.settings)), SETTINGS, "outputStyle anterior devuelto")
        for rel in (".claude/agents/rein-orchestrator.md", ".claude/agents/rein-constructor.md",
                    ".codex/agents/rein-orchestrator.toml", ".codex/agents/rein-constructor.toml", ".claude/output-styles/rein.md"):
            self.assertFalse((self.home / rel).exists(), rel)

    def test_c06_quitar_sin_estilo_previo(self):
        sin = {k: v for k, v in SETTINGS.items() if k != "outputStyle"}
        self.settings.write_text(json.dumps(sin), encoding="utf-8")
        self.cli("global")
        self.cli("global", "--quitar")
        self.assertEqual(json.loads(self.leer(self.settings)), sin, "sin outputStyle previo, la clave se va")

    def test_c07_backup(self):
        self.cli("global")
        for p, original in ((self.claude, MIO_CLAUDE), (self.codex, MIO_CODEX), (self.settings, json.dumps(SETTINGS, indent=2))):
            bak = p.with_name(p.name + ".rein-bak")
            self.assertTrue(bak.is_file(), bak.name)
            self.assertEqual(self.leer(bak), original)
        self.assertFalse((self.home / ".claude/output-styles/rein.md.rein-bak").exists(), "sin backup de lo que no existía")

    def test_c08_bloque_generico(self):
        self.cli("global")
        b = bloque(self.leer(self.claude))
        for prohibido in ("juani", "jarvis", "cerebro", "obsidian"):
            self.assertNotIn(prohibido, b.lower(), prohibido)
        for clave in ("CONTEXTO.md", "ORQUESTADOR.md", "HISTORIAS.md", "Cerrar antes de abrir", "Documentación al día", ".rein/METODO.md"):
            self.assertIn(clave, b)


if __name__ == "__main__":
    unittest.main()
