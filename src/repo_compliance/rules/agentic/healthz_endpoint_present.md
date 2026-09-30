# Rule

The HTTP application must expose a health-check endpoint at `/healthz`. It returns HTTP status 200 when the application is available and usable. The default successful response body contains the case-sensitive text `Healthy`.

## Pass

- The effective HTTP route is `/healthz`, including any route prefixes.
- Its health-check implementation returns HTTP 200 when the application is available and usable.
- The default successful response body contains `Healthy`; it need not equal that text exactly.

Framework health-check defaults count when the registration and framework behaviour establish all criteria. Trace route registration, health checks, status mapping, and response writing.

## Fail

- The HTTP application has no `/healthz` health-check endpoint, or exposes it only at a different path.
- The available and usable application receives a successful health response with a status other than 200.
- The default successful response body does not contain `Healthy`, including an empty body or different casing.
- The endpoint can report HTTP 200 despite health checks showing the application is unavailable or unusable.

## Uncertain

- Inspected source does not establish whether the repository contains an HTTP application.
- Route registration, health behaviour, status mapping, or the default response body depends on unavailable code or unresolved framework behaviour.

## Evidence

- Pass: cite the effective route registration and code or framework configuration establishing the healthy status and default body.
- Fail: cite the conflicting path, status, body, or health behaviour; for a missing endpoint, cite inspected HTTP entry points and route registration.
- Uncertain: cite the unresolved application, route, health, or response path.
