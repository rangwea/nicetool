# Authentication and Project Permissions

NiceTool can run without authentication for local demos, or with OAuth2 authentication for shared deployments.

## Authentication switch

`AUTH_ENABLED=false` keeps the instance open for local development and demos. For shared environments, enable authentication and configure the OAuth2 settings.

## Required production settings

- `AUTH_ENABLED=true`
- `AUTH_JWT_SECRET` with a strong secret value
- `AUTH_REQUIRE_HTTPS_COOKIE=true` when serving over HTTPS

## Project access

Users can be assigned access to projects. The tool center shows tools according to the current user's project permissions. Administrators can enter the admin console from the user menu.

## Notes

Keep OAuth client secrets and JWT secrets out of source control. Use `.env` or your deployment platform's secret manager.
