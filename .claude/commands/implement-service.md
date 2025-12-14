---
name: implement-service
description: Implement a service class following project patterns
args:
  - name: service_name
  - name: protocol
---

Implement the {{service_name}} class that implements {{protocol}}.

1. Read the protocol in `packages/core/src/medanki/services/protocols.py`
2. Check test specification for expected behavior
3. Create implementation with full typing
4. Add comprehensive docstrings
5. Write unit tests
6. Verify with `uv run pytest tests/unit -v -k {{service_name}}`
