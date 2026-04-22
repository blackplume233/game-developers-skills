# Privacy Audit Guide

This document explains the AI-driven privacy audit that runs before every
skill upload. The audit is performed by the AI agent itself — not a regex
script — enabling semantic-level judgment that catches issues regex cannot.

## Why AI-driven?

| Capability | Regex Script | AI Agent |
|------------|-------------|----------|
| Distinguish real key vs. example placeholder | No | Yes |
| Detect business logic leakage | No | Yes |
| Judge if a hardcoded path is a convention | No | Yes |
| Identify composite inference risk | No | Yes |
| Understand context (comment vs. code) | No | Yes |

## Five Review Dimensions

### 1. Secrets & Credentials (CRITICAL)

Real API keys, tokens, passwords, private keys. The AI checks entropy,
known formats (sk-, ghp_, AKIA), and whether values appear in assignment
context vs. documentation examples.

**Blocks upload. Must fix before proceeding.**

### 2. Identity Information (HIGH)

Usernames, emails, phone numbers, real names. Author attribution in YAML
frontmatter is acceptable; user data in instruction bodies is not.

**Pauses upload. Requires user confirmation.**

### 3. Hardcoded Paths & Environments (HIGH)

Absolute paths containing user-specific segments (e.g. `C:\Users\black\`).
Internal network URLs. Convention paths like `~/.cursor/skills/` are safe.

**Pauses upload. Requires user confirmation.**

### 4. Business Sensitive (MEDIUM)

Internal product names, undisclosed APIs, architecture details. Would this
give a competitor useful information?

**Shows suggestion. Does not block.**

### 5. Generalization (LOW)

Project-specific references in universal skills. Internal jargon.

**Shows note. Does not block.**

## Extra Observations

The AI also watches for:
- Base64-encoded credentials
- Environment variables with hardcoded fallbacks
- Residual secrets in comments/TODOs
- Composite identity inference from multiple harmless fields

## Custom Rules

Edit `.privacy-rules.yaml` in the repository root to add organization-
specific patterns, exclude paths, or mark known-safe values.
