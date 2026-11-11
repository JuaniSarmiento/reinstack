"""Aceptación HU-OS7: CI verde en Linux y macOS.

Escrita por el orquestador ANTES de implementar; criterios aprobados por Juani el 11/11/2026. El constructor no la modifica.
Motivo: en macOS /tmp y /var/folders cuelgan de /var, que es un enlace simbólico a /private/var; Rein rechazaba toda ruta con
un enlace en CUALQUIER directorio padre ("Ruta con enlace simbólico: /var") y el CI dio 64 fallas.
Contrato:
  C01 Un proyecto cuya ruta tiene un enlace simbólico en un directorio PADRE se acepta: install, doctor, update y uninstall
      funcionan y escriben en el directorio real. `global` funciona igual con un HOME bajo un padre enlazado.
      Siguen rechazándose: un proyecto que es él mismo un enlace simbólico, y enlaces dentro del proyecto (test_installer).
  C02 El workflow instala setuptools y wheel antes de correr las pruebas (en el runner de Python 3.12 no vienen).
  C03 (se verifica fuera de esta prueba) La suite completa pasa con TMPDIR bajo un padre enlazado, y el CI de GitHub da verde
      en ubuntu y macos con 3.11 y 3.12.
Correr: python3 -m unittest tests.test_rutas_enlazadas -v
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


class RutasEnlazadasTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        (base / "private" / "var").mkdir(parents=True)
        (base / "var").symlink_to(base / "private" / "var", target_is_directory=True)
        self.real = base / "private" / "var"
        self.alias = base / "var"

    def cli(self, *args, home=None, ok=True):
        env = {**os.environ, "HOME": str(home or self.alias / "home")}
        r = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True, env=env, timeout=60)
        if ok:
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def test_c01_proyecto_bajo_padre_enlazado(self):
        (self.real / "proyecto").mkdir()
        p = self.alias / "proyecto"
        self.cli("install", p, "--agent", "both", "--lang", "es")
        self.assertTrue((self.real / "proyecto" / ".rein" / "METODO.md").is_file(), "escribió en el directorio real")
        self.cli("doctor", p)
        self.cli("update", p)
        self.cli("uninstall", p)
        self.assertFalse((self.real / "proyecto" / ".rein" / "METODO.md").exists())

    def test_c01_global_con_home_bajo_padre_enlazado(self):
        for d in (".claude", ".codex"):
            (self.real / "home" / d).mkdir(parents=True)
        self.cli("global", "--lang", "es")
        self.assertIn("<!-- rein:global -->", (self.real / "home" / ".claude" / "CLAUDE.md").read_text(encoding="utf-8"))
        self.cli("global", "--quitar")

    def test_c01_proyecto_enlace_sigue_rechazado(self):
        (self.real / "destino").mkdir()
        enlace = self.real / "proyecto-enlace"
        enlace.symlink_to(self.real / "destino", target_is_directory=True)
        r = self.cli("install", enlace, "--lang", "es", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("proyecto-enlace", r.stderr)
        self.assertEqual(list((self.real / "destino").iterdir()), [], "no escribió nada")

    def test_c02_workflow_instala_setuptools(self):
        flujo = (RAIZ / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        m = re.search(r"pip install[^\n]*setuptools[^\n]*", flujo)
        self.assertIsNotNone(m, "instala setuptools")
        self.assertIn("wheel", m.group(0))
        self.assertLess(flujo.index(m.group(0)), flujo.index("unittest discover"), "antes de las pruebas")


if __name__ == "__main__":
    unittest.main()
