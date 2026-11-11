"""Aceptación ronda 2 de update: B01 (reintento tras fallo de escritura) y B02 (no bajar de versión). Origen: rompedor, verify-1."""
import hashlib, json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "reinstack.py"

def sha(b): return hashlib.sha256(b).hexdigest()

class BreakerUpdate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "p"; self.root.mkdir()
        self.home = Path(self.tmp.name) / "h"; self.home.mkdir()

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                              env={**os.environ, "HOME": str(self.home)})

    def forge(self, version, metodo):
        self.assertEqual(self.cli("install", self.root).returncode, 0)
        m = self.root / ".rein/manifest.json"; data = json.loads(m.read_text())
        data["version"] = version
        (self.root / ".rein/METODO.md").write_bytes(metodo)
        data["files"][".rein/METODO.md"] = sha(metodo)
        toml = self.root / ".codex/agents/rein-orchestrator.toml"
        toml.write_bytes(b'name = "viejo"\n')
        data["files"][".codex/agents/rein-orchestrator.toml"] = sha(b'name = "viejo"\n')
        m.write_text(json.dumps(data, indent=2))

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_B01_update_retry_recovers_after_write_failure(self):
        self.forge("0.0.1", b"# viejo\n")
        agents = self.root / ".codex/agents"
        agents.chmod(0o555)
        try:
            self.assertNotEqual(self.cli("update", self.root).returncode, 0)
        finally:
            agents.chmod(0o755)
        retry = self.cli("update", self.root)
        self.assertEqual(retry.returncode, 0, retry.stderr)
        self.assertEqual(self.cli("doctor", self.root).returncode, 0)

    def test_B02_update_refuses_newer_installed_version(self):
        self.forge("9.9.9", b"# metodo de una version futura\n")
        before = self.snapshot()
        result = self.cli("update", self.root)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.snapshot(), before)

if __name__ == "__main__":
    unittest.main()
