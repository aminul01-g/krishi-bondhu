
from app.main import app
import json

routes = []
for route in app.routes:
    # Get methods and path
    methods = list(route.methods) if hasattr(route, "methods") else []
    path = route.path if hasattr(route, "path") else ""
    name = route.name if hasattr(route, "name") else ""
    routes.append({
        "path": path,
        "methods": methods,
        "name": name
    })

# Output as JSON for the agent to read
print(json.dumps(routes, indent=2))
