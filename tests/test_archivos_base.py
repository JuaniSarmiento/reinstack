"""Aceptación HU-OS2: los archivos base sin depender de Obsidian (CONTEXTO.md + ORQUESTADOR.md como "Obsidian local").

Escrita por el orquestador ANTES de implementar; criterios aprobados por Juani el 11/11/2026. El constructor no la modifica.
Contrato:
  C01 `install` siembra CONTEXTO.md si no existe, con las secciones «## Problema», «## Para quién», «## Qué es y qué no»,
      «## Reglas del dominio», «## Glosario» y «## Stack y decisiones». Si ya existe, no lo toca.
  C02 `install --estado <ruta>` crea ORQUESTADOR.md como enlace simbólico a esa ruta (absoluta) sin escribir en la nota.
      Si la ruta no existe: código != 0 y el proyecto queda sin tocar. Sin `--estado`, ORQUESTADOR.md es un archivo común.
  C03 (compatibilidad) con obsidian.md, `install --estado` también se niega (ya hay archivo de estado) sin tocar nada;
      el resto lo cubre tests/test_obsidian.py, que tiene que seguir pasando.
  C04 METODO.md, los perfiles de orquestador y constructor y el bloque puente nombran CONTEXTO.md; METODO.md dice que se
      escribe en la «historia 0» y que ORQUESTADOR.md puede ser un enlace a una nota externa. obsidian.md queda sólo como
      compatibilidad: METODO.md lo nombra a lo sumo dos veces.
  C05 VERSION es la de pyproject.toml (HU-OS8, con OK de Juani: sin números fijos; fue 0.3.0, 0.4.0 y 1.0.0; HU-OS5 la sube a 1.0.0 con OK de Juani. Era 0.3.0; cambiado el 11/11 con OK de Juani porque HU-OS4 agrega el idioma al manifiesto). `update` sobre una instalación hecha con la 0.2.0 (commit 82992b8) agrega CONTEXTO.md sin tocar
      README.md, HISTORIAS.md ni ORQUESTADOR.md; y no lo crea si el proyecto ya tenía uno.
Correr: python3 -m unittest tests.test_archivos_base -v
"""
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import unittest

RAIZ = Path(__file__).resolve().parents[1]
VERSION_ACTUAL = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]  # HU-OS8: sin números fijos
SCRIPT = RAIZ / "reinstack.py"
SECCIONES = ["## Problema", "## Para quién", "## Qué es y qué no", "## Reglas del dominio", "## Glosario", "## Stack y decisiones"]
VIEJO = "0.2.0"  # tests/fixtures/<versión>: la 0.2.0 congelada (antes `git archive 82992b8`)


class ArchivosBaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name).resolve()  # HU-OS7: los scripts viejos de tests/fixtures rechazan padres enlazados (/var en macOS)
        self.root = base / "proyecto"
        self.root.mkdir()
        self.home = base / "home"
        self.home.mkdir()
        self.nota = base / "vault" / "Proyecto.md"
        self.nota.parent.mkdir()
        self.nota.write_text("# Mi nota\n", encoding="utf-8")

    def cli(self, *args, script=SCRIPT, ok=True):
        r = subprocess.run([sys.executable, str(script), *map(str, args)], capture_output=True, text=True,
                           env={**os.environ, "HOME": str(self.home)}, timeout=60)
        if ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def foto(self):
        return {str(p.relative_to(self.root)): (p.is_symlink(), p.read_bytes() if p.is_file() and not p.is_symlink() else None)
                for p in sorted(self.root.rglob("*"))}

    def test_c01_siembra_contexto(self):
        self.cli("install", self.root, "--agent", "both")
        ctx = self.root / "CONTEXTO.md"
        self.assertTrue(ctx.is_file(), "install crea CONTEXTO.md")
        titulos = [l.strip() for l in ctx.read_text(encoding="utf-8").splitlines() if l.startswith("## ")]
        self.assertEqual(titulos, SECCIONES)

    def test_c01_no_pisa_contexto(self):
        (self.root / "CONTEXTO.md").write_text("mío\n", encoding="utf-8")
        r = self.cli("install", self.root, "--agent", "claude")
        self.assertEqual((self.root / "CONTEXTO.md").read_text(encoding="utf-8"), "mío\n")
        self.assertIn("CONTEXTO.md", (self.root / "CLAUDE.md").read_text(encoding="utf-8"), "instaló la versión con CONTEXTO.md")

    def test_c02_estado_como_enlace(self):
        self.cli("install", self.root, "--agent", "both", "--estado", self.nota)
        orq = self.root / "ORQUESTADOR.md"
        self.assertTrue(orq.is_symlink(), "ORQUESTADOR.md es un enlace")
        self.assertEqual(Path(os.readlink(orq)), self.nota.resolve())
        self.assertEqual(self.nota.read_text(encoding="utf-8"), "# Mi nota\n", "la nota no se toca")
        self.cli("doctor", self.root)

    def test_c02_estado_inexistente_no_toca_nada(self):
        antes = self.foto()
        r = self.cli("install", self.root, "--agent", "both", "--estado", self.nota.parent / "no-existe.md", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Error:", r.stderr, "error propio del instalador, no de uso")
        self.assertIn("no-existe.md", r.stderr, "el error nombra la ruta que falta")
        self.assertEqual(self.foto(), antes, "el proyecto queda igual")

    def test_c02_sin_estado_archivo_comun(self):
        self.cli("install", self.root, "--agent", "codex")
        orq = self.root / "ORQUESTADOR.md"
        self.assertTrue(orq.is_file() and not orq.is_symlink())
        self.assertTrue((self.root / "CONTEXTO.md").is_file(), "con la versión nueva")

    def test_c03_con_obsidian_se_niega(self):
        (self.root / "obsidian.md").symlink_to(self.nota)
        antes = self.foto()
        r = self.cli("install", self.root, "--agent", "both", "--estado", self.nota, ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("obsidian.md", r.stderr, "el error explica que ya hay archivo de estado")
        self.assertEqual(self.foto(), antes)

    def test_c04_metodo_y_perfiles(self):
        t = RAIZ / "templates"
        metodo = (t / "METODO.md").read_text(encoding="utf-8")
        for clave in ("CONTEXTO.md", "historia 0", "ORQUESTADOR.md", "enlace"):
            self.assertIn(clave, metodo)
        self.assertLessEqual(metodo.count("obsidian.md"), 2, "obsidian.md sólo como compatibilidad")
        for perfil in ("orchestrator.md", "constructor.md"):
            self.assertIn("CONTEXTO.md", (t / perfil).read_text(encoding="utf-8"), perfil)
        self.cli("install", self.root, "--agent", "claude")
        self.assertIn("CONTEXTO.md", (self.root / "CLAUDE.md").read_text(encoding="utf-8"), "bloque puente")

    def viejo(self) -> Path:
        destino = Path(self.tmp.name) / "viejo"
        destino.mkdir()
        __import__("shutil").copytree(RAIZ / "tests" / "fixtures" / VIEJO, destino, dirs_exist_ok=True)
        return destino / "reinstack.py"

    def test_c05_version_y_update(self):
        r = self.cli("--version")
        self.assertEqual(r.stdout.strip(), VERSION_ACTUAL)
        self.cli("install", self.root, "--agent", "both", script=self.viejo())
        self.assertFalse((self.root / "CONTEXTO.md").exists(), "la 0.2.0 no conocía CONTEXTO.md")
        docs = {n: (self.root / n).read_bytes() for n in ("README.md", "HISTORIAS.md", "ORQUESTADOR.md")}
        self.cli("update", self.root)
        self.assertTrue((self.root / "CONTEXTO.md").is_file(), "update agrega CONTEXTO.md")
        for n, b in docs.items():
            self.assertEqual((self.root / n).read_bytes(), b, f"{n} sin tocar")
        self.cli("doctor", self.root)

    def test_c05_update_respeta_contexto_propio(self):
        self.cli("install", self.root, "--agent", "codex", script=self.viejo())
        (self.root / "CONTEXTO.md").write_text("mío\n", encoding="utf-8")
        self.cli("update", self.root)
        self.assertEqual((self.root / "CONTEXTO.md").read_text(encoding="utf-8"), "mío\n")
        self.assertIn(f'"version": "{VERSION_ACTUAL}"', (self.root / ".rein" / "manifest.json").read_text(encoding="utf-8"), "quedó en la versión actual")


if __name__ == "__main__":
    unittest.main()
