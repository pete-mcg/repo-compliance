# Rule

A HTTP application must expose a health-check endpoint that satisfies **all** of the following conditions:
- The HTTP route is `/healthz`, including any route prefixes
- It returns HTTP status 200 when the application is available and usable.
- The default successful response body contains the case-sensitive text `Healthy`.
