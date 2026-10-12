import json
from pathlib import Path
from opportunity_platform.main import app
root = Path(__file__).resolve().parents[1]
(root / "packages/contracts/openapi.json").write_text(json.dumps(app.openapi(), indent=2) + "\n")
