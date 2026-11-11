"""Aceptación de `reinstack update`: escrita por el orquestador antes de implementar.

Casos esperados: U01..U07. El constructor no modifica este archivo.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "reinstack.py"
START = "<!-- REINSTACK BEGIN -->"
END = "<!-- REINSTACK END -->"
OLD_BLOCK = f"{START}\n## ReinStack\n\nTexto de una versión anterior.\n{END}\n"


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name) / "proyecto"
        self.root.mkdir()
        self.home = Path(self.scratch.name) / "home"
        self.home.mkdir()

    def cli(self, *args, success=True):
        result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                                capture_output=True, text=True,
                                env={**os.environ, "HOME": str(self.home)})
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file() and not p.is_symlink()}

    def manifest(self):
        return json.loads((self.root / ".rein/manifest.json").read_text())

    def make_old_install(self, agent="both"):
        """Instala la versión actual y la reescribe como una instalación anterior íntegra."""
        self.cli("install", self.root, "--agent", agent)
        data = self.manifest()
        data["version"] = "0.0.1"
        metodo = self.root / ".rein/METODO.md"
        metodo.write_bytes(b"# Metodo viejo\n")
        data["files"][".rein/METODO.md"] = sha(b"# Metodo viejo\n")
        for name, entry in data["bridges"].items():
            path = self.root / name
            content = path.read_text()
            separator = entry["segment"][: entry["segment"].index(START)]
            old_segment = separator + OLD_BLOCK
            path.write_text(content.replace(entry["segment"], old_segment, 1))
            entry["segment"] = old_segment
        (self.root / ".rein/manifest.json").write_text(json.dumps(data, indent=2))
        return data

    def test_U01_update_brings_old_install_to_current_version(self):
        (self.root / "CLAUDE.md").write_text("# Reglas del proyecto\n")
        self.make_old_install()
        reference = Path(self.scratch.name) / "referencia"
        reference.mkdir()
        (reference / "CLAUDE.md").write_text("# Reglas del proyecto\n")
        subprocess.run([sys.executable, str(SCRIPT), "install", str(reference)],
                       check=True, capture_output=True, env={**os.environ, "HOME": str(self.home)})
        self.cli("update", self.root)
        for name in (".rein/METODO.md", "CLAUDE.md", "AGENTS.md", ".claude/agents/rein-constructor.md",
                     ".codex/agents/rein-orchestrator.toml"):
            self.assertEqual((self.root / name).read_bytes(), (reference / name).read_bytes(), name)
        self.assertEqual(self.manifest()["version"],
                         json.loads((reference / ".rein/manifest.json").read_text())["version"])
        self.cli("doctor", self.root)

    def test_U02_update_preserves_foreign_text_and_seed_documents(self):
        (self.root / "AGENTS.md").write_text("Regla humana\n")
        self.make_old_install()
        with (self.root / "AGENTS.md").open("a") as stream:
            stream.write("Regla agregada después\n")
        (self.root / "HISTORIAS.md").write_text("# Mi backlog\n")
        self.cli("update", self.root)
        agents = (self.root / "AGENTS.md").read_text()
        self.assertTrue(agents.startswith("Regla humana\n"))
        self.assertTrue(agents.endswith("Regla agregada después\n"))
        self.assertNotIn("Texto de una versión anterior", agents)
        self.assertEqual(agents.count(START), 1)
        self.assertEqual((self.root / "HISTORIAS.md").read_text(), "# Mi backlog\n")
        self.cli("uninstall", self.root)
        self.assertEqual((self.root / "AGENTS.md").read_text(), "Regla humana\nRegla agregada después\n")

    def test_U03_update_refuses_human_edits_without_writing(self):
        self.make_old_install()
        (self.root / ".rein/METODO.md").write_text("Cambio humano\n")
        before = self.snapshot()
        self.cli("update", self.root, success=False)
        self.assertEqual(self.snapshot(), before)

    def test_U04_update_dry_run_writes_nothing(self):
        self.make_old_install()
        before = self.snapshot()
        result = self.cli("update", self.root, "--dry-run")
        self.assertIn(".rein/METODO.md", result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_U05_update_on_current_install_changes_nothing(self):
        self.cli("install", self.root)
        before = self.snapshot()
        self.cli("update", self.root)
        self.assertEqual(self.snapshot(), before)

    def test_U06_update_without_install_fails(self):
        self.cli("update", self.root, success=False)
        self.assertEqual(self.snapshot(), {})

    def test_U07_install_over_old_version_points_to_update(self):
        self.make_old_install()
        before = self.snapshot()
        result = self.cli("install", self.root, success=False)
        self.assertIn("update", result.stderr)
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
