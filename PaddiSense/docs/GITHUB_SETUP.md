# Publishing PaddiSense to GitHub for HACS

This guide explains how to publish PaddiSense to GitHub so users can install it via HACS.

---

## Repository Structure

The `github-repo` folder contains the complete HACS-compatible repository structure:

```
github-repo/
├── hacs.json                              # HACS metadata
├── LICENSE                                # MIT license
├── README.md                              # Repository documentation
└── custom_components/
    └── paddisense/
        ├── __init__.py                    # Integration setup
        ├── config_flow.py                 # Setup wizard
        ├── const.py                       # Constants
        ├── helpers.py                     # Utility functions
        ├── manifest.json                  # HA integration metadata
        ├── sensor.py                      # Sensor platform
        ├── services.yaml                  # Service definitions
        ├── strings.json                   # UI strings
        ├── registry/
        │   ├── __init__.py
        │   ├── backend.py                 # Registry operations
        │   └── sensor.py                  # Registry sensors
        ├── translations/
        │   └── en.json                    # English translations
        └── www/
            └── paddisense-registry-card.js  # Lovelace card
```

---

## Step 1: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `paddisense-ha`
3. Description: "PaddiSense Farm Management for Home Assistant"
4. Set to **Public** (required for HACS)
5. Check "Add a README file" - **NO** (we have one)
6. Click **Create repository**

---

## Step 2: Push Files to GitHub

### Option A: From Home Assistant (SSH Terminal)

If you have SSH access to Home Assistant:

```bash
# Navigate to the github-repo folder
cd /config/PaddiSense/github-repo

# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial release v2026.1.0"

# Add your GitHub repository as remote
# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/paddisense-ha.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Option B: Upload via GitHub Web Interface

1. Go to your new repository on GitHub
2. Click **"uploading an existing file"** link
3. Drag and drop all files from `github-repo/` folder
4. Make sure the folder structure is preserved:
   - `hacs.json` at root level
   - `README.md` at root level
   - `LICENSE` at root level
   - `custom_components/paddisense/...` folder structure
5. Click **Commit changes**

### Option C: Download and Upload from Computer

1. Copy files from `/config/PaddiSense/github-repo/` to your computer
2. Use GitHub Desktop or git on your computer to push

---

## Step 3: Create a Release

HACS requires at least one release:

1. Go to your repository on GitHub
2. Click **Releases** (right sidebar)
3. Click **Create a new release**
4. Click **Choose a tag** → type `v2026.1.0` → **Create new tag**
5. Release title: `v2026.1.0`
6. Description:
   ```
   ## Initial Release

   - Farm Registry module with full CRUD operations
   - 16 services for paddock, bay, season, and farm management
   - Custom Lovelace card with mobile-friendly design
   - Config flow setup wizard
   - Automatic import of existing PaddiSense data
   ```
7. Click **Publish release**

---

## Step 4: Verify HACS Compatibility

1. Go to https://hacs.xyz/docs/publish/include#repository-structure
2. Verify your repository meets all requirements:
   - [x] `hacs.json` at root
   - [x] `custom_components/paddisense/manifest.json` exists
   - [x] `custom_components/paddisense/__init__.py` exists
   - [x] At least one release exists
   - [x] Repository is public

---

## Step 5: Test Installation

On a Home Assistant instance:

1. Open **HACS** → **Integrations**
2. Click **⋮** → **Custom repositories**
3. Add: `https://github.com/YOUR_USERNAME/paddisense-ha`
4. Category: **Integration**
5. Search for "PaddiSense" and download
6. Restart Home Assistant
7. Add the integration via Settings → Devices & Services

---

## Updating the Integration

When you make changes:

1. Update version in `manifest.json`
2. Commit and push changes to GitHub
3. Create a new release with the new version tag
4. Users will see the update available in HACS

---

## Repository URL

After setup, users install using:

```
https://github.com/YOUR_USERNAME/paddisense-ha
```

Replace `YOUR_USERNAME` with your actual GitHub username.

---

## Optional: Add to Default HACS

To get into the default HACS repository list (no custom repo needed):

1. Meet all requirements at https://hacs.xyz/docs/publish/include
2. Submit PR to https://github.com/hacs/default
3. Wait for review and approval

This is optional - custom repository method works fine.
