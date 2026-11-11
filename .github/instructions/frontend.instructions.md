---
description: "Use when creating or reviewing HTML, CSS, browser JavaScript, dashboard charts, accessibility, or frontend tests."
applyTo: "**/*.{html,css,js,mjs,cjs}"
---
# Frontend

- Keep the dashboard in plain HTML, CSS and modern JavaScript unless a requirement explicitly justifies another framework. Use semantic HTML, labels, keyboard-operable controls, visible focus, sufficient contrast and accessible status/error announcements.
- Render untrusted data using text-safe DOM APIs; never inject network identifiers, error text or API values with `innerHTML`. Do not log or persist the session token beyond the specified session storage; remove the fragment after handoff.
- Treat loading, unavailable, degraded, disconnected and empty states explicitly. Do not fabricate values; honor the API units, rounding and Wi-Fi roaming policy in `SPEC.md`.
- Clean up event listeners, timers, charts and sockets. Bound client-side buffering and handle reconnects without duplicating subscriptions or presenting stale data as live.
- Test meaningful interactions and edge cases, including keyboard use, malicious text, missing telemetry and WebSocket disconnects. Use existing browser tooling if available; clearly state when browser or accessibility checks could not run.
