# PaddiSense GitHub & Licensing Strategy

**Date:** 2026-02-12
**Status:** Implemented

---

## Completed Setup

### 1. GitHub Organization
- **Organization:** https://github.com/PaddiSense
- **Main Repo:** https://github.com/PaddiSense/PaddiSense (public)
- **Registrations:** https://github.com/PaddiSense/registrations (private)

### 2. Git Identity
- **Name:** PaddiSense
- **Email:** paddisense@outlook.com
- Old tokens revoked, new fine-grained token configured

### 3. Branch Protection
- `main` branch protected
- Requires PR with 1 approval
- Enforcement: Active

### 4. Team
- 3 developers invited to organization

---

## Module Tiers & Licensing

### PaddiSense Basic (Free - Email Registration Only)
**Modules included:**
- Weather
- IPM (Integrated Pest Management)
- RTR (Real-Time Reporting)
- Hey Farmer
- Asset Service Manager (ASM)
- Stock Tracker

**Registration Process:**
1. Grower submits issue via template: [Basic Registration](https://github.com/PaddiSense/registrations/issues/new?template=basic-registration.yml)
2. Admin reviews and approves
3. No license key required

### Precision Water Management (PWM) - Licensed
**Process:**
1. Grower submits issue: [PWM License Request](https://github.com/PaddiSense/registrations/issues/new?template=pwm-license-request.yml)
2. Admin contacts grower to discuss requirements
3. Admin generates license: `python generate_license.py --module pwm --email "..." --farm "..."`
4. License key emailed to grower
5. Grower enters key in Home Assistant

### WSS (Water Supply System) - Case-by-Case Licensed
**Process:**
1. Grower submits issue: [WSS License Request](https://github.com/PaddiSense/registrations/issues/new?template=wss-license-request.yml)
2. Admin reviews regulatory/legal considerations
3. Admin contacts grower for discussion
4. If approved: generate license with `--module wss`
5. License key emailed with compliance documentation

---

## License System

### Technology
- **Algorithm:** Ed25519 digital signatures
- **Validation:** Offline-capable (no internet required)
- **Format:** Base64-encoded signed JSON

### Tools (in registrations repo)
| File | Purpose |
|------|---------|
| `license-tools/generate_keys.py` | One-time key generation |
| `license-tools/generate_license.py` | Create signed licenses |
| `license-tools/validate_license.py` | Validate licenses (distribute with PaddiSense) |
| `license-tools/keys/private.pem` | Signing key (NEVER distribute) |
| `license-tools/keys/public.pem` | Validation key (distributed with code) |

### Generate a License
```bash
cd /config/registrations/license-tools

# PWM license (perpetual)
python3 generate_license.py --module pwm --email "grower@example.com" --farm "My Farm" --issue 15

# WSS license with expiry
python3 generate_license.py --module wss --email "grower@example.com" --farm "My Farm" --expires 2027-02-12

# License with features
python3 generate_license.py --module pwm --email "..." --farm "..." --features basic advanced
```

### Validate a License (testing)
```bash
python3 validate_license.py "LICENSE_KEY_HERE" pwm
```

---

## Security Notes

1. **Private key** is in `/config/registrations/license-tools/keys/private.pem`
   - NEVER commit to git (protected by .gitignore)
   - NEVER share or distribute
   - Back up securely

2. **Public key** is embedded in `validate_license.py`
   - Safe to distribute with PaddiSense
   - Used for offline validation

3. **License keys** are tamper-proof but readable
   - Contents (email, farm, module) visible in base64
   - Signature prevents modification

---

## Remaining Tasks

- [ ] Integrate `validate_license.py` into PWM module
- [ ] Integrate `validate_license.py` into WSS module
- [ ] Create grower installation workflow
- [ ] Set up email automation (optional)
- [ ] HACS integration (if desired)
