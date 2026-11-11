"""Aceptación: obsidian.md reemplaza a ORQUESTADOR.md cuando el proyecto lo tiene.

Escrita por el orquestador ANTES de implementar (pedido de Juani, 10/11/2026). El constructor no la modifica.
Contrato:
  C01 Con `obsidian.md` en el proyecto (archivo o symlink), `install` no crea ORQUESTADOR.md y no toca obsidian.md.
  C02 Sin `obsidian.md`, `install` sigue creando ORQUESTADOR.md como siempre.
  C03 El método, los dos agentes de cada cliente y el bloque puente nombran `obsidian.md` como fuente del estado.
  C04 `update` y `uninstall` con obsidian.md tampoco crean ORQUESTADOR.md ni tocan obsidian.md; `doctor` da OK.
Correr: python3 -m unittest tests.test_obsidian -v
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "reinstack.py"
NOTA = "---\nestado: activo\nultimo: 10/11\n---\n# Proyecto\n\n## Estado actual\nAlgo.\n"


class ObsidianTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        base = Path(self.scratch.name)
        self.root = base / "proyecto"
        self.root.mkdir()
        self.home = base / "home"
        self.home.mkdir()
        self.vault_nota = base / "vault" / "Proyecto.md"
        self.vault_nota.parent.mkdir()
        self.vault_nota.write_text(NOTA, encoding="utf-8")

    def cli(self, *args):
        r = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                           env={**os.environ, "HOME": str(self.home)})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def con_symlink(self):
        (self.root / "obsidian.md").symlink_to(self.vault_nota)

    def test_c01_symlink_sin_orquestador(self):
        self.con_symlink()
        self.cli("install", self.root, "--agent", "both")
        self.assertFalse((self.root / "ORQUESTADOR.md").exists(), "con obsidian.md no se crea ORQUESTADOR.md")
        self.assertTrue((self.root / "HISTORIAS.md").is_file())
        self.assertTrue((self.root / "obsidian.md").is_symlink(), "obsidian.md sigue siendo symlink")
        self.assertEqual(self.vault_nota.read_text(encoding="utf-8"), NOTA, "la nota no se toca")

    def test_c01_archivo_comun_sin_orquestador(self):
        (self.root / "obsidian.md").write_text(NOTA, encoding="utf-8")
        self.cli("install", self.root, "--agent", "claude")
        self.assertFalse((self.root / "ORQUESTADOR.md").exists())
        self.assertEqual((self.root / "obsidian.md").read_text(encoding="utf-8"), NOTA)

    def test_c02_sin_obsidian_crea_orquestador(self):
        self.cli("install", self.root, "--agent", "both")
        self.assertTrue((self.root / "ORQUESTADOR.md").is_file(), "sin Obsidian, ORQUESTADOR.md como siempre")

    def test_c03_textos_nombran_obsidian(self):
        self.con_symlink()
        self.cli("install", self.root, "--agent", "both")
        for rel in [".rein/METODO.md", ".claude/agents/rein-orchestrator.md", ".claude/agents/rein-constructor.md",
                    ".codex/agents/rein-orchestrator.toml", ".codex/agents/rein-constructor.toml",
                    "CLAUDE.md", "AGENTS.md"]:
            self.assertIn("obsidian.md", (self.root / rel).read_text(encoding="utf-8"), f"{rel} nombra obsidian.md")

    def test_c04_update_doctor_uninstall(self):
        self.con_symlink()
        self.cli("install", self.root, "--agent", "both")
        self.cli("update", self.root)
        self.assertFalse((self.root / "ORQUESTADOR.md").exists(), "update no crea ORQUESTADOR.md")
        self.assertIn("OK", self.cli("doctor", self.root).stdout)
        self.cli("uninstall", self.root)
        self.assertFalse((self.root / "ORQUESTADOR.md").exists())
        self.assertTrue((self.root / "obsidian.md").is_symlink())
        self.assertEqual(self.vault_nota.read_text(encoding="utf-8"), NOTA)


if __name__ == "__main__":
    unittest.main()
