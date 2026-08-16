# RiftSense Roadmap

## Before 1.0

### 1. Visual polish

- Standardize spacing, card heights, typography, and section hierarchy
- Refine sidebar/header branding and logo sizing
- Normalize button, entry, combobox, tab, tooltip, and dialog styling
- Reduce remaining duplicate/low-value explanatory text
- Improve empty/loading/error states
- Check layouts at 1200×700, 1600×900, 1920×1080, and scaled Windows displays

### 2. Windows application packaging

- Build `RiftSense.exe`
- Use the RiftSense multi-size `.ico`
- Add Windows metadata: product name, version, company/author, description
- Create an installer with Start Menu / Desktop shortcuts and clean uninstall
- Keep user data outside the installation directory

### 3. Update system

- Check GitHub Releases at startup without blocking the UI
- Compare semantic versions
- Show a small `Update available` notification only when a newer stable release exists
- Display release notes
- Provide `Download Update` and `Later`
- Never overwrite user data during updates

### 4. Reliability

- Add rotating application logs
- Add a friendly crash/error dialog with log location
- Detect corrupted JSON and recover safely
- Add explicit schema versions and migrations for persistent data
- Improve Riot API states: connected, expired key, rate limited, offline, unavailable
- Handle Riot patch/data changes gracefully

### 5. First-run experience

- Add a short setup screen for Riot ID / region
- Explain Riot API key requirements and expiration
- Explain which features work without an API key
- Add Privacy / Local Data information
- Add quick links to History, Draft, Live Overview, and Settings

### 6. GitHub / release presentation

- Add screenshots or GIFs to README
- Add a feature overview image
- Add installation instructions for the `.exe`
- Add release notes / changelog
- Add GitHub Actions build workflow
- Publish signed/tagged releases when practical

## After 1.0

- AI Coach using structured Player Memory as read-only evidence context
- Deeper long-term performance comparisons
- More champion profiles and curated loadouts
- Optional automatic updater process
