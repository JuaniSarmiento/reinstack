"""Las aceptaciones de OS1-OS3 y obsidian heredan la locale y asumen español: se fija si la efectiva no lo es."""
import os

for _name in ("LC_ALL", "LC_MESSAGES", "LANG"):
    if os.environ.get(_name):
        _efectiva = os.environ[_name]
        break
else:
    _efectiva = ""
if not _efectiva.lower().startswith("es"):
    os.environ["LANG"] = "es_AR.UTF-8"
    os.environ.pop("LC_ALL", None)
    os.environ.pop("LC_MESSAGES", None)
