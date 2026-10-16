import json
from pathlib import Path
from opportunity_platform.main import app
root = Path(__file__).resolve().parents[1]
(root / "packages/contracts/openapi.json").write_text(json.dumps(app.openapi(), indent=2) + "\n")

# Backend owns this declarative specification; web and parity tests consume its generated copy.
(root / "apps/web/src/features/profiles/semantics.generated.json").write_text(
    (root / "apps/api/src/opportunity_platform/profiles/semantics.json").read_text()
)
