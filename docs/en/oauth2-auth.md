# Authentication and Project Permissions

NiceTool can run without authentication for local demos, or with local accounts, OIDC or OAuth2 authentication for shared deployments.

## Authentication switch

`AUTH_ENABLED=false` keeps the instance open for local development and demos. For shared environments, enable authentication. External provider settings are needed only when using external login.

## Required production settings

- `AUTH_ENABLED=true`
- `AUTH_JWT_SECRET` with a strong secret value
- `AUTH_REQUIRE_HTTPS_COOKIE=true` when serving over HTTPS

## Project access

Users can be assigned access to projects. The tool center shows tools according to the current user's project permissions. Administrators can enter the admin console from the user menu.

## Notes

Keep OAuth client secrets and JWT secrets out of source control. Use `.env` or your deployment platform's secret manager.

## Local accounts and session lifecycle

When no local password account exists, `/auth/login` offers administrator initialization. Administrators create subsequent accounts; temporary passwords must be changed on first login. Web sessions use short-lived JWTs in HttpOnly cookies; there is no refresh token. CLI clients use revocable personal Bearer tokens or browser device authorization.

## Provider and operation scopes

Use `AUTH_PROVIDER_PROFILE=oidc` with issuer discovery and JWKS, or `oauth2` with explicit authorization, token and userinfo endpoints. Callback URLs must include `PROJECT_PATH`. Claim mapping and verified-email settings determine external account binding. See `core/settings.py` for field names.

Project access and operation scopes are separate. Ordinary users default to read and preview on assigned projects; administrators can also publish, roll back and delete. A token is further restricted by its issued scopes. Project access alone does not grant publication rights.

Device authorization starts at `/api/auth/device/start` and polls `/api/auth/device/token`. Include both in custom `AUTH_PUBLIC_PATHS`; the browser confirmation page `/auth/device/authorize` requires login. Preview pages under `/client/tool` are public by default and should not be treated as private data isolation.
