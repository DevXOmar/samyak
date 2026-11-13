import json
from pathlib import Path
from samyak.api import app

path = Path(__file__).resolve().parents[1] / "frontend/openapi.json"
path.write_text(json.dumps(app.openapi(), indent=2))
print(path)
