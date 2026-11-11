---
description: "Use when editing project configuration, JSON, TOML, PowerShell, shell scripts, dependencies, or CI."
applyTo: "**/*.{json,toml,ps1,sh}"
---
# Configuration and scripts

- Preserve the file's schema, existing settings and cross-platform behavior. Validate JSON or TOML syntax and any schema constraints; quote shell arguments and use explicit error handling.
- Pin or bound new dependencies, justify them, and update the existing manifest and relevant documentation. Do not install dependencies unless required by the task or a missing-dependency failure.
- Never embed secrets or local machine paths in committed configuration; do not log tokens. Use user-scoped storage and permissions required by the specification.
- Scripts must avoid destructive defaults, broad deletion, untrusted command interpolation and implicit privilege escalation. Verify changes with the narrowest available parser, test or dry run.
