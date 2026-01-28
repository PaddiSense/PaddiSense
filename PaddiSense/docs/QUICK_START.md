# PaddiSense Quick Start

Get PaddiSense running in 5 minutes.

---

## 1. Add Repository to HACS

1. Open **HACS** from the sidebar
2. Go to **Integrations**
3. Click **⋮** (three dots, top right) → **Custom repositories**
4. Enter:
   - **Repository**: `https://github.com/paddisense/paddisense-ha`
   - **Category**: Integration
5. Click **Add**

---

## 2. Download & Install

1. In HACS, click **+ Explore & Download Repositories**
2. Search "**PaddiSense**"
3. Click **Download**
4. **Restart Home Assistant**: Settings → System → Restart

---

## 3. Add the Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search "**PaddiSense**"
4. Follow the wizard (enter farm name, optionally add first paddock)

---

## 4. Add the Dashboard Card

### Register the resource:
1. **Settings** → **Dashboards** → **⋮** menu → **Resources**
2. Click **+ Add Resource**
3. URL: `/paddisense/paddisense-registry-card.js`
4. Type: JavaScript Module
5. **Refresh your browser** (Ctrl+F5)

### Add the card:
1. Edit your dashboard (pencil icon)
2. **+ Add Card** → search "paddisense"
3. Click **PaddiSense Registry Card**

---

## Done!

You should now see:
- Farm name at the top
- Paddock and bay counts
- Buttons to add paddocks and seasons

---

## Quick Reference

| To do this... | Do this... |
|---------------|------------|
| Add a paddock | Click "Add Paddock" button |
| Add a season | Click "Add Season" button |
| Toggle paddock season | Click ⇄ icon |
| Delete a paddock | Click 🗑 icon |
| Access services | Developer Tools → Services → "paddisense" |
| View sensor data | Developer Tools → States → "paddisense" |

---

## Need Help?

See the full guide: `INSTALLATION.md`
