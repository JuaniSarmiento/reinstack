"""Behavioral tests; every target is a disposable temporary project."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "reinstack.py"
START = "<!-- REINSTACK BEGIN -->"
END = "<!-- REINSTACK END -->"


class InstallerTests(unittest.TestCase):
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

    def install(self, agent="both"):
        return self.cli("install", self.root, "--agent", agent)

    def test_install_both_native_roles_and_methodology(self):
        self.install()
        self.assertTrue((self.root / ".rein/METODO.md").is_file())
        for role in ("orchestrator", "constructor"):
            claude = self.root / f".claude/agents/rein-{role}.md"
            self.assertTrue(claude.read_text().startswith("---\nname: rein-"))
            self.assertIn("model: inherit", claude.read_text())
            native = tomllib.loads((self.root / f".codex/agents/rein-{role}.toml").read_text())
            self.assertEqual(native["name"], f"rein-{role}")
            self.assertTrue(native["description"])
            self.assertTrue(native["developer_instructions"])
            self.assertNotIn("model", native)
        self.cli("doctor", self.root)

    def test_install_preserves_existing_text_and_is_idempotent(self):
        originals = {"AGENTS.md": b"Regla privada sin salto", "CLAUDE.md": b"# Proyecto\n\nReglas\n"}
        for name, content in originals.items():
            (self.root / name).write_bytes(content)
        self.install()
        first = self.snapshot()
        self.install()
        self.assertEqual(first, self.snapshot())
        for name, content in originals.items():
            self.assertTrue((self.root / name).read_bytes().startswith(content))
        self.cli("uninstall", self.root)
        for name, content in originals.items():
            self.assertEqual((self.root / name).read_bytes(), content)

    def test_seed_documents_are_kept_after_uninstall(self):
        existing = b"# Mi backlog\nUna historia propia\n"
        (self.root / "HISTORIAS.md").write_bytes(existing)
        self.install()
        self.assertEqual((self.root / "HISTORIAS.md").read_bytes(), existing)
        (self.root / "ORQUESTADOR.md").write_text("Contexto actualizado por persona\n")
        self.cli("uninstall", self.root)
        self.assertEqual((self.root / "HISTORIAS.md").read_bytes(), existing)
        self.assertIn("actualizado", (self.root / "ORQUESTADOR.md").read_text())
        self.assertTrue((self.root / "README.md").exists())
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertFalse((self.root / "CLAUDE.md").exists())
        self.assertFalse((self.root / ".rein/manifest.json").exists())

    def test_dry_run_does_not_create_anything(self):
        self.cli("install", self.root, "--dry-run")
        self.assertEqual(self.snapshot(), {})
        self.assertEqual(list(self.root.iterdir()), [])

    def test_single_agent_does_not_touch_other_client_or_global_home(self):
        settings = self.home / ".claude/settings.json"
        settings.parent.mkdir()
        settings.write_bytes(b'{"hooks": "ajenos"}\n')
        config = self.home / ".codex/config.toml"
        config.parent.mkdir()
        config.write_bytes(b'model = "mi-modelo"\n')
        originals = {p: p.read_bytes() for p in (settings, config)}
        self.install("codex")
        self.assertEqual({p: p.read_bytes() for p in originals}, originals)
        self.assertEqual({p for p in self.home.rglob("*") if p.is_file()}, set(originals))
        self.assertFalse((self.root / "CLAUDE.md").exists())
        self.assertFalse((self.root / ".claude").exists())
        self.assertTrue((self.root / "AGENTS.md").exists())
        self.assertFalse((self.root / ".codex/config.toml").exists())

    def test_collision_is_refused_before_any_write(self):
        conflict = self.root / ".codex/agents/rein-constructor.toml"
        conflict.parent.mkdir(parents=True)
        conflict.write_text("contenido ajeno\n")
        before = self.snapshot()
        self.cli("install", self.root, success=False)
        self.assertEqual(self.snapshot(), before)

    def test_edited_owned_file_blocks_reinstall_and_uninstall(self):
        self.install()
        (self.root / ".rein/METODO.md").write_text("Cambio humano\n")
        before = self.snapshot()
        self.cli("doctor", self.root, success=False)
        self.cli("install", self.root, success=False)
        self.cli("uninstall", self.root, success=False)
        self.assertEqual(self.snapshot(), before)

    def test_uninstall_preserves_edits_outside_managed_block(self):
        (self.root / "AGENTS.md").write_text("Inicio\n")
        self.install()
        with (self.root / "AGENTS.md").open("a") as stream:
            stream.write("\nNueva regla humana\n")
        self.cli("uninstall", self.root)
        self.assertEqual((self.root / "AGENTS.md").read_text(), "Inicio\n\nNueva regla humana\n")

    def test_modified_bridge_blocks_uninstall_without_partial_deletion(self):
        self.install()
        bridge = self.root / "AGENTS.md"
        bridge.write_text(bridge.read_text().replace("METODO.md", "OTRO.md"))
        before = self.snapshot()
        self.cli("uninstall", self.root, success=False)
        self.assertEqual(self.snapshot(), before)

    def test_symlink_directory_is_rejected_without_external_writes(self):
        outside = Path(self.scratch.name) / "fuera"
        outside.mkdir()
        (self.root / ".claude").symlink_to(outside, target_is_directory=True)
        self.cli("install", self.root, success=False)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.root / ".rein").exists())

    def test_corrupt_manifest_is_an_error_without_writes(self):
        self.install()
        (self.root / ".rein/manifest.json").write_text('{"schema": 1, "files": {"../fuera": "x"}}')
        before = self.snapshot()
        self.cli("uninstall", self.root, success=False)
        self.assertEqual(self.snapshot(), before)

    def test_uninstall_preserves_preexisting_empty_directories(self):
        codex = self.root / ".codex"
        claude_agents = self.root / ".claude/agents"
        codex.mkdir()
        claude_agents.mkdir(parents=True)
        self.install("claude")
        self.cli("uninstall", self.root)
        self.assertTrue(codex.is_dir(), "No quitar el directorio ajeno de otro cliente")
        self.assertTrue(claude_agents.is_dir(), "No quitar padres preexistentes")

    def age_install(self, block):
        """Rewrite the manifest and bridges as an intact install of an earlier version."""
        path = self.root / ".rein/manifest.json"
        data = json.loads(path.read_text())
        data["version"] = "0.0.1"
        for name, entry in data["bridges"].items():
            separator = entry["segment"][: entry["segment"].index(START)]
            bridge = self.root / name
            bridge.write_text(bridge.read_text().replace(entry["segment"], separator + block, 1))
            entry["segment"] = separator + block
        path.write_text(json.dumps(data))

    def test_structurally_invalid_bridge_segment_is_rejected(self):
        self.install("claude")
        path = self.root / ".rein/manifest.json"
        valid = json.loads(path.read_text())
        segment = valid["bridges"]["CLAUDE.md"]["segment"]
        self.assertTrue(segment.startswith(START))
        for bad in ("x" + segment, "\n\n\n" + segment, segment.replace(END, ""), segment[:-1],
                    segment.replace("\n", f"\n{START}\n", 1), segment.replace(END, f"{END}\n{END}"),
                    segment + "texto ajeno\n", ""):
            data = json.loads(json.dumps(valid))
            data["bridges"]["CLAUDE.md"]["segment"] = bad
            path.write_text(json.dumps(data))
            result = self.cli("doctor", self.root, success=False)
            self.assertIn("contenido del bloque inválido", result.stderr, repr(bad))

    def test_update_single_agent_does_not_add_other_client(self):
        self.install("claude")
        self.age_install(f"{START}\nviejo\n{END}\n")
        self.cli("update", self.root)
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertFalse((self.root / ".codex").exists())
        data = json.loads((self.root / ".rein/manifest.json").read_text())
        self.assertEqual(data["agent"], "claude")
        self.assertNotIn("viejo", (self.root / "CLAUDE.md").read_text())

    def test_update_then_uninstall_removes_created_bridges(self):
        self.install()
        self.age_install(f"{START}\nviejo\n{END}\n")
        self.cli("update", self.root)
        self.cli("uninstall", self.root)
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertFalse((self.root / "CLAUDE.md").exists())

    def test_update_refuses_modified_bridge_without_writing(self):
        self.install()
        self.age_install(f"{START}\nviejo\n{END}\n")
        bridge = self.root / "AGENTS.md"
        bridge.write_text(bridge.read_text().replace("viejo", "editado"))
        before = self.snapshot()
        result = self.cli("update", self.root, success=False)
        self.assertIn("AGENTS.md", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_install_over_other_bridge_or_version_points_to_update(self):
        self.install()
        path = self.root / ".rein/manifest.json"
        data = json.loads(path.read_text())
        data["version"] = "0.0.1"
        path.write_text(json.dumps(data))
        before = self.snapshot()
        result = self.cli("install", self.root, success=False)
        self.assertIn("reinstack update", result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.age_install(f"{START}\nviejo\n{END}\n")
        data = json.loads(path.read_text())
        data["version"] = self.cli("--version").stdout.strip()
        path.write_text(json.dumps(data))
        before = self.snapshot()
        result = self.cli("install", self.root, success=False)
        self.assertIn("reinstack update", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_update_on_current_install_does_not_rewrite_any_file(self):
        self.install()
        stamps = {p: (p.stat().st_ino, p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
        result = self.cli("update", self.root)
        self.assertIn("ya está actualizado", result.stdout)
        self.assertEqual({p: (p.stat().st_ino, p.stat().st_mtime_ns) for p in stamps}, stamps)

    def forge_old_files(self, version="0.0.1"):
        """Rewrite an intact install so METODO and a Codex profile belong to an older version."""
        path = self.root / ".rein/manifest.json"
        data = json.loads(path.read_text())
        data["version"] = version
        for name, content in ((".rein/METODO.md", b"# viejo\n"),
                              (".codex/agents/rein-orchestrator.toml", b'name = "viejo"\n')):
            (self.root / name).write_bytes(content)
            data["files"][name] = hashlib.sha256(content).hexdigest()
        path.write_text(json.dumps(data))

    def interrupted_update(self):
        """Old install whose update failed after writing METODO, before the Codex profile."""
        self.install()
        self.forge_old_files()
        agents = self.root / ".codex/agents"
        agents.chmod(0o555)
        try:
            self.cli("update", self.root, success=False)
        finally:
            agents.chmod(0o755)

    def test_interrupted_update_keeps_old_manifest_and_records_pending(self):
        self.install()
        self.forge_old_files()
        manifest = (self.root / ".rein/manifest.json").read_bytes()
        agents = self.root / ".codex/agents"
        agents.chmod(0o555)
        try:
            self.cli("update", self.root, success=False)
        finally:
            agents.chmod(0o755)
        self.assertEqual((self.root / ".rein/manifest.json").read_bytes(), manifest)
        path = self.root / ".rein/manifest.pending.json"
        self.assertTrue(path.is_file(), "falta el registro de la actualización pendiente")
        pending = json.loads(path.read_text())
        self.assertEqual(pending["version"], self.cli("--version").stdout.strip())

    def test_doctor_reports_interrupted_update(self):
        self.interrupted_update()
        result = self.cli("doctor", self.root, success=False)
        self.assertIn("interrumpida", result.stderr)
        self.assertIn("reinstack update", result.stderr)

    def test_install_and_uninstall_with_pending_point_to_update(self):
        self.interrupted_update()
        before = self.snapshot()
        for args in (("install", self.root), ("uninstall", self.root)):
            result = self.cli(*args, success=False)
            self.assertIn("reinstack update", result.stderr, args)
        self.assertEqual(self.snapshot(), before)

    def test_human_edit_during_pending_update_still_blocks(self):
        self.interrupted_update()
        (self.root / ".codex/agents/rein-orchestrator.toml").write_text('name = "humano"\n')
        before = self.snapshot()
        result = self.cli("update", self.root, success=False)
        self.assertIn("rein-orchestrator.toml", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_human_edit_of_bridge_during_pending_update_still_blocks(self):
        self.interrupted_update()
        bridge = self.root / "AGENTS.md"
        bridge.write_text(bridge.read_text().replace("METODO.md", "OTRO.md"))
        before = self.snapshot()
        result = self.cli("update", self.root, success=False)
        self.assertIn("AGENTS.md", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_retry_completes_update_and_removes_pending(self):
        self.interrupted_update()
        self.cli("update", self.root)
        self.assertFalse((self.root / ".rein/manifest.pending.json").exists())
        data = json.loads((self.root / ".rein/manifest.json").read_text())
        self.assertEqual(data["version"], self.cli("--version").stdout.strip())
        self.assertIn("ya está actualizado", self.cli("update", self.root).stdout)

    def foreign_pending(self, version, toml):
        """Old install interrupted by another ReinStack after it wrote the Codex profile."""
        self.install()
        self.forge_old_files()
        data = json.loads((self.root / ".rein/manifest.json").read_text())
        data["version"] = version
        data["files"][".codex/agents/rein-orchestrator.toml"] = hashlib.sha256(toml).hexdigest()
        (self.root / ".rein/manifest.pending.json").write_text(json.dumps(data))
        (self.root / ".codex/agents/rein-orchestrator.toml").write_bytes(toml)

    def test_second_interruption_while_completing_foreign_pending_is_recoverable(self):
        self.foreign_pending("0.1.5", b'name = "intermedio"\n')
        agents = self.root / ".codex/agents"
        agents.chmod(0o555)
        try:
            self.cli("update", self.root, success=False)
        finally:
            agents.chmod(0o755)
        self.cli("update", self.root)
        self.cli("doctor", self.root)
        self.assertFalse((self.root / ".rein/manifest.pending.json").exists())

    def test_foreign_pending_with_rewritten_block_completes_to_current(self):
        self.install()
        self.age_install(f"{START}\nviejo\n{END}\n")
        data = json.loads((self.root / ".rein/manifest.json").read_text())
        pending = json.loads(json.dumps(data))
        pending["version"] = "0.1.5"
        old = data["bridges"]["CLAUDE.md"]["segment"]
        middle = old.replace("viejo", "intermedio")
        pending["bridges"]["CLAUDE.md"]["segment"] = middle
        (self.root / ".rein/manifest.pending.json").write_text(json.dumps(pending))
        claude = self.root / "CLAUDE.md"
        claude.write_text(claude.read_text().replace(old, middle, 1))
        self.cli("update", self.root)
        self.cli("doctor", self.root)
        self.assertNotIn("intermedio", claude.read_text())

    def test_newer_pending_is_refused_without_writes(self):
        self.foreign_pending("9.9.9", b'name = "futuro"\n')
        before = self.snapshot()
        result = self.cli("update", self.root, success=False)
        self.assertIn("más nueva", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_incoherent_pending_is_a_manifest_error_without_traceback(self):
        self.install()
        self.forge_old_files()
        pending = json.loads((self.root / ".rein/manifest.json").read_text())
        pending["agent"] = "codex"
        pending["files"] = {k: v for k, v in pending["files"].items() if not k.startswith(".claude/")}
        pending["bridges"].pop("CLAUDE.md")
        (self.root / ".rein/manifest.pending.json").write_text(json.dumps(pending))
        before = self.snapshot()
        for command in ("update", "doctor", "install", "uninstall"):
            result = self.cli(command, self.root, success=False)
            self.assertIn("Manifiesto inválido", result.stderr, command)
            self.assertNotIn("Traceback", result.stderr, command)
        self.assertEqual(self.snapshot(), before)

    def test_install_over_newer_version_does_not_point_to_update(self):
        self.install()
        self.forge_old_files("9.9.9")
        before = self.snapshot()
        result = self.cli("install", self.root, success=False)
        self.assertIn("más nueva", result.stderr)
        self.assertNotIn("reinstack update", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_update_refuses_newer_version_with_clear_message(self):
        self.install()
        self.forge_old_files("9.9.9")  # era 0.10.0: con la 1.0.0 (HU-OS5) dejó de ser más nueva
        before = self.snapshot()
        result = self.cli("update", self.root, success=False)
        self.assertIn("más nueva", result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_unparseable_version_is_a_manifest_error(self):
        self.install()
        for version in ("", "abc", "1.x", "1..2", "v1.0"):
            self.forge_old_files(version)
            result = self.cli("doctor", self.root, success=False)
            self.assertIn("Manifiesto inválido", result.stderr, repr(version))

    def test_update_dry_run_on_current_install_reports_up_to_date(self):
        self.install()
        before = self.snapshot()
        result = self.cli("update", self.root, "--dry-run")
        self.assertIn("ya está actualizado", result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_manifest_hashes_match_installed_owned_files(self):
        self.install("claude")
        data = json.loads((self.root / ".rein/manifest.json").read_text())
        for path, digest in data["files"].items():
            self.assertEqual(hashlib.sha256((self.root / path).read_bytes()).hexdigest(), digest)
        self.assertNotIn("HISTORIAS.md", data["files"])


if __name__ == "__main__":
    unittest.main()
