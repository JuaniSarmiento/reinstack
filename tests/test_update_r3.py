"""Aceptación ronda 3 de update (origen: rompedor, verify-2).

R3_01 (G1): una actualización interrumpida que dejó un pendiente de OTRA versión o contenido
se completa con la versión que corre ahora, si cada archivo está en el estado viejo o en el
pendiente. R3_02 (B03): reanudar después de un corte que ya reescribió un bloque.
Decisión del orquestador (2026-11-09): completar con la versión actual; no abandonar el pendiente
ni pedir otra copia de ReinStack.
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
OLD_BLOCK = f"{START}\n## ReinStack\n\nViejo.\n<!-- REINSTACK END -->\n"


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = {**os.environ, "HOME": self.tmp.name}

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                              capture_output=True, text=True, env=self.env)

    def old_project(self, name):
        """Instalación íntegra de una versión anterior, con CLAUDE.md ajeno."""
        root = Path(self.tmp.name) / name
        root.mkdir()
        (root / "CLAUDE.md").write_text("Reglas propias\n")
        self.assertEqual(self.cli("install", root).returncode, 0)
        manifest = root / ".rein/manifest.json"
        data = json.loads(manifest.read_text())
        data["version"] = "0.0.1"
        (root / ".rein/METODO.md").write_bytes(b"# viejo\n")
        data["files"][".rein/METODO.md"] = sha(b"# viejo\n")
        for bridge, entry in data["bridges"].items():
            path = root / bridge
            separator = entry["segment"][: entry["segment"].index(START)]
            path.write_text(path.read_text().replace(entry["segment"], separator + OLD_BLOCK, 1))
            entry["segment"] = separator + OLD_BLOCK
        manifest.write_text(json.dumps(data, indent=2))
        return root, data

    def fresh(self):
        root = Path(self.tmp.name) / "referencia"
        root.mkdir()
        (root / "CLAUDE.md").write_text("Reglas propias\n")
        self.assertEqual(self.cli("install", root).returncode, 0)
        return root

    def assert_current(self, root):
        reference = self.fresh()
        for name in (".rein/METODO.md", "CLAUDE.md", "AGENTS.md"):
            self.assertEqual((root / name).read_bytes(), (reference / name).read_bytes(), name)
        self.assertFalse((root / ".rein/manifest.pending.json").exists(), "el pendiente debe borrarse")
        doctor = self.cli("doctor", root)
        self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)

    def test_R3_01_pending_from_another_version_completes_with_current(self):
        root, old = self.old_project("proyecto")
        pending = json.loads(json.dumps(old))
        pending["version"] = "0.1.5"
        pending["files"][".rein/METODO.md"] = sha(b"# intermedio\n")
        (root / ".rein/manifest.pending.json").write_text(json.dumps(pending, indent=2))
        (root / ".rein/METODO.md").write_bytes(b"# intermedio\n")  # el corte fue después de este archivo
        result = self.cli("update", root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_current(root)

    def test_R3_02_resume_after_cut_that_already_rewrote_a_bridge(self):
        target_root, _ = self.old_project("destino")
        self.assertEqual(self.cli("update", target_root).returncode, 0)
        target = json.loads((target_root / ".rein/manifest.json").read_text())
        root, old = self.old_project("proyecto")
        (root / ".rein/manifest.pending.json").write_text(json.dumps(target, indent=2))
        claude = root / "CLAUDE.md"
        claude.write_text(claude.read_text().replace(old["bridges"]["CLAUDE.md"]["segment"],
                                                     target["bridges"]["CLAUDE.md"]["segment"], 1))
        result = self.cli("update", root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_current(root)


if __name__ == "__main__":
    unittest.main()
