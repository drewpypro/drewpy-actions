# Dimension: Community Sentiment (v1)

## Goal

- Retrieve a simple view of Steam Community sentiment. 

## How to research

- Preferred sources:
    - Steam store page for the game
    - SteamDB page for the game

## Questions to answer

1. What is the current Steam user review summary label?
2. What is the approximate overall positive review percentage, if available?

## Output fields

- Populate these fields in `results.community_sentiment`:
- `steam_label` (string, e.g., "Mostly Positive", "Mixed", "Overwhelmingly Negative", "unknown")
- `steam_percentage` (string, e.g., "78%", or "unknown")
- `sources` (array of URLs used for this dimension)

- Provide a one-paragraph summary describing overall community sentiment and any common themes.
