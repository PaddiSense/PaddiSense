# GitHub Organization Setup Guide

**Date:** 2026-02-12
**Target Org Name:** PaddiSense
**Target Email:** paddisense@outlook.com

---

## Phase 1: Create the GitHub Organization

### Step 1.1: Create Organization
1. Log into GitHub with your `PKmac78` account
2. Click your profile picture (top right) → **Settings**
3. Left sidebar → **Organizations**
4. Click **New organization**
5. Choose **Free** plan (sufficient for public repos)
6. **Organization name:** `PaddiSense`
7. **Contact email:** `paddisense@outlook.com`
8. Select: "This organization belongs to my personal account"
9. Complete CAPTCHA and create

### Step 1.2: Configure Organization Profile
1. Go to `github.com/PaddiSense`
2. Click **Settings** (org settings)
3. **Profile:**
   - Display name: `PaddiSense`
   - Email: `paddisense@outlook.com`
   - Description: "Modular farm management platform for Home Assistant"
   - URL: (your website if you have one)
4. Upload organization avatar/logo if available

---

## Phase 2: Transfer Existing Repository

### Step 2.1: Pre-Transfer Checklist
- [ ] Ensure you have admin access to `PKmac78/PaddiSense`
- [ ] No pending pull requests that would break
- [ ] Notify any current collaborators

### Step 2.2: Transfer Repository
1. Go to `github.com/PKmac78/PaddiSense`
2. Click **Settings** (repo settings)
3. Scroll to bottom → **Danger Zone**
4. Click **Transfer repository**
5. Type `PaddiSense` as the new owner (the org)
6. Type repo name to confirm: `PaddiSense`
7. Click **I understand, transfer this repository**

### Step 2.3: Post-Transfer
- New URL: `github.com/PaddiSense/PaddiSense`
- GitHub will redirect old URLs automatically (temporary)
- Update any bookmarks, documentation, CI/CD references

---

## Phase 3: Update Local Git Configuration

### Step 3.1: Update Git Identity (Run on HAOS)
```bash
# Set identity for this repo specifically
cd /config
git config user.name "PaddiSense"
git config user.email "paddisense@outlook.com"

# Verify
git config user.name
git config user.email
```

### Step 3.2: Update Remote URL
```bash
# Remove old remote (contains exposed token)
git remote remove origin

# Add new remote (clean URL)
git remote add origin https://github.com/PaddiSense/PaddiSense.git

# Verify
git remote -v
```

### Step 3.3: Set Up Authentication (Choose One)

**Option A: GitHub CLI (Recommended)**
```bash
# Install gh CLI and authenticate
gh auth login
```

**Option B: Personal Access Token (New)**
1. Go to GitHub → Settings → Developer Settings → Personal Access Tokens → Fine-grained tokens
2. Create new token for `PaddiSense` org repos only
3. Configure git credential helper:
```bash
git config credential.helper store
git push origin dev  # Will prompt for credentials once
```

**Option C: SSH Key**
```bash
# Generate key
ssh-keygen -t ed25519 -C "paddisense@outlook.com"

# Add to GitHub: Settings → SSH Keys → New
# Update remote to SSH
git remote set-url origin git@github.com:PaddiSense/PaddiSense.git
```

---

## Phase 4: Set Up Teams & Permissions

### Step 4.1: Create Teams
1. Go to `github.com/orgs/PaddiSense/teams`
2. Create teams:

| Team Name | Permission Level | Purpose |
|-----------|-----------------|---------|
| `core-devs` | Maintain | Main developers (you + 2 others) |
| `contributors` | Write | External contributors if needed |
| `growers` | Read | (Optional) For private beta access |

### Step 4.2: Invite Developers
1. Go to `github.com/orgs/PaddiSense/people`
2. Click **Invite member**
3. Enter their GitHub username or email
4. Assign to `core-devs` team
5. They receive email invitation to join

### Step 4.3: Set Repository Permissions
1. Go to `github.com/PaddiSense/PaddiSense/settings/access`
2. Add `core-devs` team with **Maintain** access
3. This grants: push, merge PRs, manage issues, but not delete repo

---

## Phase 5: Create Additional Repositories

### Recommended Repo Structure

| Repository | Visibility | Purpose |
|------------|------------|---------|
| `PaddiSense` | Public | Main codebase (packages, dashboards) |
| `registrations` | Private | License requests, grower registration issues |
| `paddisense.github.io` | Public | (Optional) Documentation site |
| `license-tools` | Private | License generation scripts |

### Step 5.1: Create Registrations Repo
1. Go to `github.com/organizations/PaddiSense/repositories/new`
2. Name: `registrations`
3. Visibility: **Private**
4. Initialize with README
5. Create issue templates for:
   - Basic registration
   - PWM license request
   - WSS license request

---

## Phase 6: Protect Main Branch

### Step 6.1: Branch Protection Rules
1. Go to `github.com/PaddiSense/PaddiSense/settings/branches`
2. Click **Add branch protection rule**
3. Branch name pattern: `main`
4. Enable:
   - [x] Require pull request before merging
   - [x] Require approvals: 1
   - [x] Dismiss stale PR approvals when new commits pushed
   - [x] Require status checks to pass (if you have CI)
   - [x] Do not allow bypassing the above settings
5. Save changes

---

## Verification Checklist

After completing all phases:

- [ ] Organization visible at `github.com/PaddiSense`
- [ ] Repo accessible at `github.com/PaddiSense/PaddiSense`
- [ ] Local git shows correct remote (`git remote -v`)
- [ ] Local git identity correct (`git config user.name && git config user.email`)
- [ ] Can push to repo: `git push origin dev`
- [ ] Other developers can access repo
- [ ] Branch protection active on `main`

---

## Security Notes

1. **Revoke old token:** After updating remote URL, revoke the old PAT that was embedded
2. **Never embed tokens in URLs:** Use credential helper or SSH instead
3. **Fine-grained tokens:** Use tokens scoped to specific repos/permissions
4. **2FA:** Enable two-factor authentication on the org

---

## Next Steps After Org Setup

1. Set up registration/licensing system
2. Configure HACS for grower installation
3. Create installer automation
4. Document grower onboarding flow
