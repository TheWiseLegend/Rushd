# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Rushd — a self-hosted web app for a personal self-discovery tool. Module 1 is a
partner-selection self-assessment for Muslims, grounded in Islamic-psychology
course content, delivered as a conversation.

## Architecture

These decisions are fixed for the project; don't re-litigate them in later steps.

- **Claude API** runs the assessment conversation (content/system prompt ported over in a later step).
- **Self-hosted DB** (Postgres or SQLite) stores each person's structured profile — no managed/cloud DB services.
- **Trivial invite-link/passcode auth**, not full user accounts.
- **Docker deployment** on the owner's own infrastructure.
- **Small scale**: 2-5 users total, used occasionally (every few months) — do not over-engineer for scale this project doesn't have.
