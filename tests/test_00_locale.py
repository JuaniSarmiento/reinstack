"""Con `discover -s tests` no se importa tests/__init__.py: se aplica igual la fijación de locale (ver ese archivo)."""
import importlib.util
import os
from pathlib import Path
import unittest

_ruta = Path(__file__).with_name("__init__.py")
_spec = importlib.util.spec_from_file_location("_rein_locale", _ruta)
_spec.loader.exec_module(importlib.util.module_from_spec(_spec))


class LocaleTests(unittest.TestCase):
    def test_locale_efectiva_es_espanola(self):
        valor = next((os.environ[n] for n in ("LC_ALL", "LC_MESSAGES", "LANG") if os.environ.get(n)), "")
        self.assertTrue(valor.lower().startswith("es"), valor)


if __name__ == "__main__":
    unittest.main()
