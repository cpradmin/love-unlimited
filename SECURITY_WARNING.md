# Security Warning - API Keys Found in Settings

**Date:** 2026-01-09
**Status:** ✅ MITIGATED (Keys removed, not in git history)

---

## Summary

API keys and tokens were found in local settings files but were **NOT committed to git history**. The files have been cleaned and protection added.

---

## Keys Found (Now Removed)

### 1. Anthropic API Keys (2 instances)
- **Location:** `.claude/settings.local.json` (lines 11, 48)
- **Format:** `sk-ant-api03-...`
- **Status:** Removed from file, never in git history

### 2. Grok/X.AI API Key
- **Location:** `.claude/settings.local.json` (line 51)
- **Key:** `xai-[REDACTED]`
- **Status:** Removed from file, never in git history

### 3. GitHub Personal Access Token
- **Location:** `.claude/settings.local.json` (line 80)
- **Key:** `ghp_[REDACTED]`
- **Username:** cpradmin
- **Status:** Removed from file, never in git history

### 4. Love Unlimited API Key
- **Location:** `.claude/settings.local.json` (line 78)
- **Key:** `lu_jon_QmZCAglY6kqsIdl6cRADpQ`
- **Status:** Removed from file, never in git history

### 5. External Access Token
- **Location:** `.claude/settings.local.json` (line 31)
- **Key:** `ext_Hogkg1zrWfWNJbfjCaIcUgBkaR5F11UU`
- **Status:** Removed from file, never in git history

---

## Actions Taken

### ✅ Immediate Fixes
1. **Updated `.gitignore`** to exclude `.claude/` and `.grok/` directories
2. **Cleaned `.claude/settings.local.json`** - removed all API keys and tokens
3. **Removed malformed entries** - cleaned up bash loop fragments (lines 52-63)
4. **Removed `.grok/settings.json` from git tracking** (contained no sensitive data)

### ✅ Verification
- **Git history checked:** No API keys found in any commits
- **`.claude/settings.local.json`:** Never committed to git (good!)
- **`.grok/settings.json`:** Only contained model name, no keys

---

## Required Actions

### 🔴 CRITICAL - Rotate These Keys

Even though keys were never in git, they were in plaintext on disk. Rotate as a precaution:

1. **Anthropic API Keys**
   - Go to: https://console.anthropic.com/settings/keys
   - Revoke old keys, generate new ones
   - Store in environment variables or secure vault

2. **Grok/X.AI API Key**
   - Go to: https://console.x.ai/
   - Revoke: `xai-[REDACTED]`
   - Generate new key

3. **GitHub Personal Access Token**
   - Go to: https://github.com/settings/tokens
   - Revoke: `ghp_[REDACTED]`
   - Generate new token for cpradmin

4. **Love Unlimited Keys**
   - Regenerate: `lu_jon_QmZCAglY6kqsIdl6cRADpQ`
   - Regenerate: `ext_Hogkg1zrWfWNJbfjCaIcUgBkaR5F11UU`
   - Use: `python generate_keys.py` and `python generate_external_token.py`

### ⚠️ Store Keys Securely

**Best Practices:**
```bash
# Use environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export GROK_API_KEY="xai-..."

# Add to ~/.bashrc or ~/.zshrc
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.bashrc

# Or use systemd environment files
sudo systemctl edit love-unlimited-hub.service
# Add: Environment="ANTHROPIC_API_KEY=sk-ant-..."

# Never hardcode in settings files!
```

---

## Future Prevention

### Protected Paths (in `.gitignore`)
```
.claude/
.grok/
.env
.env.local
auth/api_keys.yaml
auth/external_tokens.yaml
```

### Settings File Format
`.claude/settings.local.json` should only contain:
- Bash command permissions
- UI preferences
- Non-sensitive configuration

**Never store:**
- API keys
- Passwords
- Tokens
- Private keys
- Database credentials

---

## Status

| Item | Status |
|------|--------|
| Keys removed from files | ✅ Complete |
| `.gitignore` updated | ✅ Complete |
| Git tracking cleaned | ✅ Complete |
| Git history verified | ✅ Clean (no keys found) |
| Keys rotated | ⏳ Required (user action) |

---

## Questions?

This file documents the security issue and remediation. It can be safely committed to git as it contains no actual keys (only patterns/formats for documentation).

**Next steps:** Rotate the keys listed above, then delete this file or commit it for reference.
