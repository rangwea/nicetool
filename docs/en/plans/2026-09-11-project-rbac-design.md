# User Project Access Design

> Historical design note: the current implementation assigns project access by user. For operational usage, see [Authentication and Project Permissions](../oauth2-auth.md).

## Goal

Give administrators a simple way to decide which users can see and run tools for each project.

## Model

A user can be linked to one or more projects. Tool visibility is filtered by the user's project access. Administrators keep full access to management pages.

## Admin experience

The admin console should provide a compact user list, project assignment controls, and clear empty states. Permission changes should be explicit and easy to audit.

## Runtime behavior

When a user opens the tool center, the platform loads the user's project list and filters tools accordingly. Direct tool URLs should apply the same permission checks.

## Migration

Existing local or demo deployments can start with authentication disabled. Shared deployments should enable authentication, create administrators, and assign project access before inviting users.
