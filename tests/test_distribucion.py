"""Aceptación HU-OS5: distribución (licencia, paquete instalable, CI, limpieza y 1.0.0).

Escrita por el orquestador ANTES de implementar; criterios aprobados por Juani el 11/11/2026. El constructor no la modifica.
Contrato:
  C01 LICENSE es MIT, a nombre de Juani Sarmiento, 2026.
  C02 pyproject.toml sin dependencias, Python >= 3.11, comando de consola `reinstack`, versión 1.0.0.
      `python3 reinstack.py` desde el clon sigue funcionando (lo cubren las demás aceptaciones).
  C03 Se construye el wheel (pip wheel --no-deps --no-build-isolation, sin red), se instala en un venv limpio sin red y,
      desde un directorio ajeno al repo, `reinstack --version`, `reinstack install`, `reinstack global` y `reinstack tone`
      funcionan con las plantillas del paquete (en español y en inglés).
  C04 .github/workflows/ tiene un workflow que corre `python -m unittest discover -s tests` en ubuntu-latest y macos-latest,
      con Python 3.11 y 3.12, y una corrida con LANG=C.
  C05 Limpieza: no existe informes/; CHANGELOG.md tiene la 1.0.0; README.md y README.en.md dicen que Windows no está soportado;
      ningún archivo versionado (salvo tests/fixtures y este archivo) contiene «/home/», «Cerebro» ni «Jarvis».
  C06 `reinstack.py --version` es 1.0.0 (también fijado en test_archivos_base C05 y test_idiomas C08).
Correr: python3 -m unittest tests.test_distribucion -v
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

RAIZ = Path(__file__).resolve().parents[1]


def versionados() -> list[Path]:
    r = subprocess.run(["git", "-C", str(RAIZ), "ls-files", "-co", "--exclude-standard"], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return [RAIZ / l for l in r.stdout.splitlines() if l and (RAIZ / l).is_file()]
    return [p for p in RAIZ.rglob("*") if p.is_file() and ".git" not in p.parts]


class DistribucionTests(unittest.TestCase):
    def test_c01_licencia(self):
        lic = RAIZ / "LICENSE"
        self.assertTrue(lic.is_file(), "existe LICENSE")
        t = lic.read_text(encoding="utf-8")
        for clave in ("MIT License", "Juani Sarmiento", "2026"):
            self.assertIn(clave, t)

    def test_c02_pyproject(self):
        p = RAIZ / "pyproject.toml"
        self.assertTrue(p.is_file(), "existe pyproject.toml")
        d = tomllib.loads(p.read_text(encoding="utf-8"))["project"]
        self.assertEqual(d["name"], "reinstack")
        self.assertEqual(d["version"], "1.0.0")
        self.assertEqual(d.get("dependencies", []), [])
        self.assertIn("3.11", d["requires-python"])
        self.assertIn("reinstack", d["scripts"])
        self.assertIn("MIT", str(d.get("license", "")))

    def test_c03_wheel_instalable(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.assertTrue((RAIZ / "pyproject.toml").is_file(), "existe pyproject.toml")
        r = subprocess.run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "-w", str(base / "dist"), str(RAIZ)],
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        wheels = list((base / "dist").glob("reinstack-1.0.0-*.whl"))
        self.assertEqual(len(wheels), 1, f"un wheel 1.0.0: {list((base / 'dist').iterdir())}")
        subprocess.run([sys.executable, "-m", "venv", str(base / "venv")], check=True, timeout=120)
        py = base / "venv" / "bin" / "python"
        r = subprocess.run([str(py), "-m", "pip", "install", "--no-index", "--no-deps", str(wheels[0])], capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        exe = base / "venv" / "bin" / "reinstack"
        self.assertTrue(exe.is_file(), "comando reinstack en el venv")
        home = base / "home"
        (home / ".claude").mkdir(parents=True)
        (home / ".codex").mkdir(parents=True)
        lejos = base / "lejos"
        lejos.mkdir()
        env = {k: v for k, v in os.environ.items() if k not in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "PYTHONPATH")}

        def correr(*args, lang="es_AR.UTF-8"):
            r = subprocess.run([str(exe), *map(str, args)], capture_output=True, text=True, cwd=lejos,
                               env={**env, "HOME": str(home), "LANG": lang}, timeout=60)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return r.stdout

        self.assertEqual(correr("--version").strip(), "1.0.0")
        es, en = base / "es", base / "en"
        es.mkdir(); en.mkdir()
        correr("install", es, "--lang", "es")
        correr("install", en, "--lang", "en")
        self.assertTrue((es / "CONTEXTO.md").is_file() and (es / ".rein" / "METODO.md").is_file())
        self.assertTrue((en / "CONTEXT.md").is_file() and (en / ".rein" / "METHOD.md").is_file())
        correr("global")
        self.assertIn("<!-- rein:global -->", (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertTrue((home / ".claude" / "output-styles" / "rein.md").is_file())
        self.assertIn("You are Rein", correr("tone", "--lang", "en", lang="en_US.UTF-8"))

    def test_c04_ci(self):
        flujos = list((RAIZ / ".github" / "workflows").glob("*.y*ml"))
        self.assertTrue(flujos, "hay workflow")
        t = "\n".join(f.read_text(encoding="utf-8") for f in flujos)
        for clave in ("ubuntu-latest", "macos-latest", "3.11", "3.12", "unittest discover -s tests"):
            self.assertIn(clave, t)
        self.assertRegex(t, r"LANG\s*[:=]\s*['\"]?C\b")

    def test_c05_limpieza(self):
        self.assertFalse((RAIZ / "informes").exists(), "sin informes/")
        ch = RAIZ / "CHANGELOG.md"
        self.assertTrue(ch.is_file(), "existe CHANGELOG.md")
        self.assertIn("1.0.0", ch.read_text(encoding="utf-8"))
        for readme in ("README.md", "README.en.md"):
            self.assertIn("Windows", (RAIZ / readme).read_text(encoding="utf-8"), readme)
        sucios = []
        for f in versionados():
            rel = f.relative_to(RAIZ)
            if rel.parts[:2] == ("tests", "fixtures") or rel == Path("tests/test_distribucion.py"):
                continue
            try:
                t = f.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for prohibido in ("/home/", "Cerebro", "Jarvis"):
                if prohibido in t:
                    sucios.append(f"{rel}: {prohibido}")
        self.assertEqual(sucios, [])

    def test_c06_version(self):
        r = subprocess.run([sys.executable, str(RAIZ / "reinstack.py"), "--version"], capture_output=True, text=True)
        self.assertEqual(r.stdout.strip(), "1.0.0")


if __name__ == "__main__":
    unittest.main()
