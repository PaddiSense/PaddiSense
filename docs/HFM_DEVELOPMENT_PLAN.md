# Hey Farmer (HFM) - Development Plan

## Overview
Hey Farmer (HFM) is a voice-assisted guided recording module for farmers. It enables hands-free recording of farm events while working in the field.

## Core Concept
- **Trigger:** Voice activation with "Hey Farmer"
- **Purpose:** Record nutrient, chemical, irrigation events and key crop stages
- **Fallback:** Form-based input for offline use or desktop entry
- **Future:** Opt-in anonymized data sharing to central server for industry reporting

## Event Types
1. **Nutrient** - fertilizer applications
2. **Chemical** - pesticide/herbicide applications
3. **Irrigation** - watering events
4. **Crop Stage** - key growth milestones

## Voice Wizard Flow

### 1. Activation
- Farmer says "Hey Farmer"
- System responds and asks: "What type of event are you recording?"

### 2. Event Type Selection
- User responds: nutrient / chemical / irrigation / crop stage

### 3. Product Recording (Nutrient/Chemical) - Tank Mix Support
- "What was the first product applied?"
- Product names sourced from IPM module
- For each product:
  - "What rate was applied?" (wait for response)
  - "How was it applied?" (boom / broadcast / aerial)
  - Application method options contextual to product type (e.g., no "seed treatment" for herbicides)
- **Tank mix loop:**
  - "Any additional products in the mix?"
  - If yes → "What was the next product?" → repeat rate/method questions
  - If no → proceed to timing
- Support for unlimited products per event (typical tank mix: 2-5 products)

### 4. Timing
- Date/time auto-recorded when event logged
- Wizard asks: "When did this take place?"
- Options: today / yesterday / specific date

### 5. Confirmation
- System reads back summary of recorded data
- User confirms or requests edit
- Edit commands: "change product" / "change rate" / "change method"

## Multi-User Support
- Track which user recorded each event
- User identification required

## Offline-First Design
- Must work without internet connection
- Form fallback for:
  - Offline environments
  - Desktop use
  - Manual entry preference
- Form must support:
  - "Add product" button for building tank mix list
  - Edit/remove individual products from mix
  - Reorder products if needed

## Data Architecture Considerations

### Local Storage
- Lightweight JSON format
- Stored in `local_data/hfm/`
- Follows PaddiSense module conventions

### Future Central Server Integration
- Opt-in only
- De-identified data for industry reporting
- Low data intensity for transfer (minimal bandwidth)
- Central server not yet implemented - design for future compatibility

## Current State
- No voice setup in Home Assistant yet
- IPM module exists (source for product names)
- No central server infrastructure

## Technical Requirements (TBD)
- Voice recognition integration for HA
- Wake word detection ("Hey Farmer")
- Text-to-speech for wizard responses
- Form-based UI fallback
- Data sync mechanism (future)

## Open Questions
- Voice recognition approach in HA?
- Wake word implementation options?
- User identification method?
- Crop stage definitions?
- Irrigation event details needed?
- Data schema design?
- Integration with existing modules (IPM, Registry)?

---
*Document created: 2026-02-07*
*Status: Initial capture - pending detailed planning*
