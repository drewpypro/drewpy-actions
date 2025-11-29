# Dimension: Anti-Cheat & DRM (v1)

## Goal 

- Determine whether the game uses anti-cheat or DRM, and how invasive it is. 

## How to research 

- Preferred sources:
    - PCGamingWiki page for the game
    - Steam storeg page (DRM notices)
    - Official support/FAQ pages

## Questions to answer

1. Does the game use any anti-cheat or DRM system (e.g., Denuvo, kernel-level anti-cheat)?
2. If yes, is it considered kernel-level or highly invasive?

## Output fields

- Populate these fields in `results.anti_cheat`:
    - `type` (string, e.g., "Denuvo", "EAC", "none", "unknown")
    - `classification` (one of: "none", "standard", "invasive", "unknown")
    - `sources` (array of URLs used for this dimension)
- If no information is found, use `"unknown"`.
- Provide a one-paragraph summary describing how intrusive the anti-cheat appears, based on classification.
