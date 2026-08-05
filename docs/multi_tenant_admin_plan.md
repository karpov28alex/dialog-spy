# Multi-bot and scoped admin architecture

## Goals

- Register multiple Telegram bot tokens from the super-admin panel.
- Run every registered bot against the shared platform database while preserving strict tenant isolation.
- Create super-admin and bot-owner admin accounts.
- Restrict bot owners to data and analytics belonging to assigned bots.
- Keep financial operations, global settings, broadcasts, system health, and admin management available only to super-admins.

## Required data model

### bot_instances

- id
- name
- telegram_bot_id
- telegram_username
- encrypted_token
- webhook_secret
- enabled
- created_by_admin_id
- created_at / updated_at

### admin_accounts

- id
- login
- password_hash
- role: super_admin | bot_owner | analyst | support
- enabled
- last_login_at
- created_by_admin_id

### admin_bot_access

- admin_id
- bot_instance_id
- permissions JSON

## Tenant keys

The following entities must receive `bot_instance_id` before additional bots can process updates safely:

- users
- business_connections
- dialogs
- messages
- processed_updates
- failed_updates
- jobs
- referrals
- subscriptions
- payments
- broadcasts

All unique constraints that currently assume one bot must include `bot_instance_id`.

## Security requirements

- Tokens are encrypted at rest; they are never returned to the browser after creation.
- Passwords use a password hash, never reversible encryption.
- Every admin API query applies server-side tenant filters derived from the authenticated admin token.
- Super-admin-only routes reject scoped admins independently of the frontend.
- Bot creation validates the token with Telegram before storage.
- Every bot receives an independent webhook path and secret.
- Audit records are created for bot, admin, access, charge, refund, and settings changes.

## Delivery order

1. Admin accounts, roles, permissions, audit log.
2. Bot registry and encrypted token storage.
3. Add `bot_instance_id` columns and backfill the current bot.
4. Tenant-aware repositories and admin API filters.
5. Dynamic webhook dispatch and bot runtime registry.
6. Scoped owner dashboard.
7. Migration verification, isolation tests, and staged rollout.
