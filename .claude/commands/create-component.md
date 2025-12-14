---
name: create-component
description: Create a React component with tests
args:
  - name: component_name
---

Create the {{component_name}} React component:

1. Create `web/src/components/{{component_name}}.tsx`
2. Use TypeScript strict mode
3. Add Tailwind classes
4. Create test file `web/src/components/__tests__/{{component_name}}.test.tsx`
5. Verify with `cd web && npm test -- --run`
