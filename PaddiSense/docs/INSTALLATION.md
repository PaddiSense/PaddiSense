# PaddiSense Installation Guide

This guide walks you through installing PaddiSense on Home Assistant OS (HAOS) using HACS.

---

## Prerequisites

Before you begin, make sure you have:

- Home Assistant OS running (version 2025.1.0 or later)
- HACS installed (see Step 1 if not)
- Access to your Home Assistant web interface

---

## Step 1: Install HACS (if not already installed)

HACS (Home Assistant Community Store) is required to install PaddiSense from GitHub.

### Check if HACS is installed

1. Look in your Home Assistant sidebar for "HACS"
2. If you see it, skip to Step 2
3. If not, follow the instructions below

### Install HACS

1. Go to https://hacs.xyz/docs/use/download/download
2. Follow the official HACS installation guide
3. After installation, restart Home Assistant
4. Complete the HACS setup wizard (requires GitHub account)

---

## Step 2: Add PaddiSense Repository to HACS

Since PaddiSense is a custom repository, you need to add it manually to HACS.

1. Open **HACS** from the sidebar
2. Click on **Integrations**
3. Click the **three dots menu** (⋮) in the top right corner
4. Click **Custom repositories**
5. In the dialog that appears:
   - **Repository**: Enter `https://github.com/paddisense/paddisense-ha`
   - **Category**: Select **Integration**
6. Click **Add**
7. Close the dialog

---

## Step 3: Download PaddiSense

1. In HACS → Integrations, click **+ Explore & Download Repositories**
2. Search for "**PaddiSense**"
3. Click on **PaddiSense Farm Management**
4. Click **Download** (bottom right)
5. Select the latest version
6. Click **Download**
7. **Restart Home Assistant**:
   - Go to **Settings** → **System** → **Restart**
   - Click **Restart**
   - Wait for Home Assistant to come back online

---

## Step 4: Add the PaddiSense Integration

After restart, add the integration to Home Assistant.

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration** (bottom right corner)
3. Search for "**PaddiSense**"
4. Click on **PaddiSense Farm Management**

### Setup Wizard

The wizard will guide you through configuration:

#### If you have existing data:

If you previously used PaddiSense, the wizard detects your data:
- Shows how many paddocks, bays, and seasons were found
- Choose **"Import existing data"** to keep your setup
- Click **Submit**

#### Fresh installation:

1. **Farm Setup**
   - Enter your **Grower / Server Name** (e.g., "Smith Farm")
   - Enter your **Farm Name** (e.g., "Main Farm")
   - Click **Submit**

2. **Add First Paddock** (optional)
   - Enter a **Paddock Name** (e.g., "SW6") or leave blank to skip
   - Set **Number of Bays** (default: 5)
   - Set **Bay Prefix** (default: "B-")
   - Click **Submit**

3. **Done!**
   - The integration is now configured
   - You'll see "PaddiSense" in your integrations list

---

## Step 5: Add the Dashboard Card Resource

To use the custom PaddiSense card, register it as a Lovelace resource.

1. Go to **Settings** → **Dashboards**
2. Click the **three dots menu** (⋮) in the top right
3. Click **Resources**
4. Click **+ Add Resource** (bottom right)
5. Enter:
   - **URL**: `/paddisense/paddisense-registry-card.js`
   - **Resource type**: JavaScript Module
6. Click **Create**
7. **Refresh your browser** (press Ctrl+F5 or Cmd+Shift+R)

---

## Step 6: Add the Card to Your Dashboard

1. Go to your dashboard
2. Click the **pencil icon** (Edit Dashboard) in the top right
3. Click **+ Add Card**
4. Search for "**paddisense**"
5. Click **PaddiSense Registry Card**
6. Click **Save**

### Manual YAML Method

If you prefer YAML, add this to your dashboard:

```yaml
type: custom:paddisense-registry-card
entity: sensor.paddisense_registry
```

---

## Step 7: Verify Installation

### Check the Integration

1. Go to **Settings** → **Devices & Services**
2. Find **PaddiSense** in the list
3. Click on it - you should see:
   - 1 device (PaddiSense)
   - 2 entities (Registry sensor, Version sensor)

### Check the Sensors

1. Go to **Developer Tools** → **States**
2. Search for "paddisense"
3. You should see:
   - `sensor.paddisense_registry` - Shows "ready"
   - `sensor.paddisense_version` - Shows version number

### Check the Card

Your dashboard should show:
- Farm name in the header
- Paddock and bay counts
- List of paddocks (if any)
- "Add Paddock" and "Add Season" buttons

---

## Using PaddiSense

### Adding a Paddock

1. Click **Add Paddock** on the card
2. Enter the paddock name (e.g., "SW7")
3. Set the number of bays
4. Click **Add**

### Adding a Season

1. Click **Add Season** on the card
2. Enter season name (e.g., "CY26")
3. Set start and end dates
4. Click **Add**

### Other Actions

- **Toggle season status**: Click the ⇄ icon next to a paddock
- **Delete paddock**: Click the 🗑 icon, then confirm

---

## Updating PaddiSense

When updates are available:

1. Open **HACS** → **Integrations**
2. Find **PaddiSense Farm Management**
3. If an update is available, you'll see a notification
4. Click **Update**
5. Restart Home Assistant

---

## Troubleshooting

### PaddiSense not showing in HACS search

1. Make sure you added the custom repository (Step 2)
2. Try refreshing HACS: three dots menu → **Reload**
3. Check the repository URL is correct

### Integration not showing after restart

1. Check Home Assistant logs: **Settings** → **System** → **Logs**
2. Look for errors containing "paddisense"
3. Verify HACS downloaded the files: check `/config/custom_components/paddisense/` exists

### Card not appearing

1. Verify you added the resource (Step 5)
2. Clear browser cache: Ctrl+F5 (Windows) or Cmd+Shift+R (Mac)
3. Check browser console for errors: press F12 → Console tab

### "Entity not found" error

1. Verify integration is set up: Settings → Devices & Services → PaddiSense
2. Check sensor exists: Developer Tools → States → search "paddisense"
3. Use correct entity: `sensor.paddisense_registry`

---

## Uninstalling

If you need to remove PaddiSense:

1. Go to **Settings** → **Devices & Services**
2. Find **PaddiSense**, click the three dots menu
3. Click **Delete**
4. Go to **HACS** → **Integrations**
5. Find **PaddiSense**, click the three dots menu
6. Click **Remove**
7. Restart Home Assistant

Your data in `/config/local_data/registry/` is preserved unless you manually delete it.

---

## Getting Help

1. Check Home Assistant logs for error details
2. Review this guide for missed steps
3. See `FARM_REGISTRY.md` for technical reference
