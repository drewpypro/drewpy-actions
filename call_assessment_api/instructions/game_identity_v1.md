# Dimension: Identity & Ownership (v1)

## Goal

- Identify the developer, publisher, and primary country associated with the game. 

## How to research

- Preferred sources:
    - Steam store page for the game
    - Wikipedia article about the game or studio
    - Official website of the developer or publisher

## Questions to answer

1. Who is the developer of the game?
2. Who is the publisher of the game?
3. What is the primary country associated with the developer or publisher?

## Output fields

- Populate these fields in `results.identity`:
    - `developer` (string)
    - `publisher` (string)
    - `country` (string, e.g, "Sweden", "United States")
    - `sources` (array of URLs used for this dimension)
- If you cannot determine a field reliably, set it to `"unknown"`. 

- After researching, provide a one-paragraph summary describing whether the developer/publisher appears reputable, established, and aligned with user expectations. Place this in the `summary` field.
