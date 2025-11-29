# request validation
- **Workflow trigger**
```yaml
      - name: Pre Processing
        id: pre_process_validation
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          echo "Extracting game name"
          jq -r '.issue.body' "$GITHUB_EVENT_PATH" > /tmp/game_name.txt

          echo "DEBUG: validate game_name"
          cat /tmp/game_name.txt

          
          # Take the last non-empty line as the game name
          GAME_NAME=$(grep -v '^[[:space:]]*$' /tmp/game_name.txt | tail -n1)
          echo "DEBUG: extracted GAME_NAME='$GAME_NAME'"

          echo "DEBUG: Pre GITHUB_OUTPUT"
          cat "$GITHUB_OUTPUT"

          echo "DEBUG: Load github output"
          echo "game_name=$GAME_NAME" >> "$GITHUB_OUTPUT"

          echo "DEBUG: PostTest"
          cat "$GITHUB_OUTPUT"

      - name: Validate Request
        uses: drewpypro/drewpy-actions/request_validation@gamesv1
        id: request_validation
        with:
          game_name: ${{ pre_process_validation.outputs.game_name }}

```
- **workflow example output**
```sh
0s
Run echo "Extracting game name"
Extracting game name
DEBUG: validate game_name
### Game Name

humans too
DEBUG: extracted GAME_NAME='humans too'
DEBUG: Pre GITHUB_OUTPUT
DEBUG: Load github output
DEBUG: PostTest
game_name=humans too
```

- **drewpy-actions/request_validation.py**
    - Accepts --input-file or --game-name to receive $game_name variable
    - takes issue request input and performs linting, validation, sanitization and rejection. 
        - if character count is over 69, then reject the request. **too long**
        - if non-standard unicode character is present, request the request right away and return back to user. **bad characters**
            - standard unicode acceppted for [A-Z],[a-z],[0-9]
            - accepted characters: spaces, "!", "?", ",", ":", "'", "-", "&", ".", "™" (Unicode: U+2122), "_", open/closed parenthesis.
                - "-" and "." do not get transformed.
                - "&" gets transformed to "-and-"
                - all other accepted characters get translated to "-"
        - if game_name="ARC Raiders", then it gets normalized to "arc-raiders", Insurgency: Sandstorm, is normalized into "insurgency-sandstorm"
        - game_name fuzzy matches "ARK*.*Survival" case-insensitive, then drop if match. **access denied**
    - if successful provide "Validation Okay" response, returns failure codes; 
        - **script error** - not returned back to issue, generated and output to pipeline excluding secrets/sensitive information. 
            - Output Message: Script has errored, please review logs and contact admin.
            - Output message is displayed in pipeline only. 
        - **too long** - starting with 69 characters or less, but need to assess common/longest game names in my library to make sure that works.
            - Output Message: Game name longer than 69 characters, please shorten and try again or contact the administrator.
            - Output message is emitted back to issue/user. 
        - **bad characters** - using non-standard unicode characters or unsupported special characters.
            - Output Message: Bad characters in your request, please try again by submitting again using a normal human keyboard.
            - output message is emitted back to issue/user. 
        - **access denied** - create a list of games and refuse assessment, or if a game pattern matches something nsfw for example.
            - Output Message: I refuse to assess this game, it sucks. 
        - If successful, generates empty json and md file to $GITHUB_OUTPUT.
            - $repo/json/$slug-assessment.json
            - $repo/docs/$slug-assessment.md

- **workflow output (next step)**
```yaml
      - name: Generate Approval PR
        id: pre_approval
        env:
          GIT_AUTHOR_NAME: github-actions
          GIT_AUTHOR_EMAIL: github-actions@github.com
          GIT_COMMITTER_NAME: github-actions
          GIT_COMMITTER_EMAIL: github-actions@github.com
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GAME_NAME: ${{ steps.pre_process_validation.outputs.game_name }}
        run: |
          echo "Generating PR for approval if necessary"
          AUTHOR=$(jq -r '.issue.user.login' "$GITHUB_EVENT_PATH")
          ISSUE_ID=${{ github.event.issue.number }}
          BRANCH="issue-${ISSUE_ID}"          

          if [ "$AUTHOR" = "drewpypro" ]; then
            echo "✅ Auto-approving" > /tmp/issue_comment.txt
            gh label create "drewpypro" --color DAE8FC --description "🍆"
            gh issue edit "$ISSUE_ID" --add-label "drewpypro"          
          else

            # Check if branch already exists
            if git ls-remote --heads origin | grep -q "refs/heads/$BRANCH"; then
              # Branch exists, create a unique branch name
              BRANCH="issue-${ISSUE_ID}-$(date +%s)"
            fi

            # Create and switch to the branch
            git checkout -b "$BRANCH"

            # Commit only if there are changes
            if ! git diff --staged --quiet; then
              git add "${{ steps.request_validation.outputs.md_path }}"
              git add "${{ steps.request_validation.outputs.json_path }}"
              git commit -m "Add ${GAME_NAME} from issue #${ISSUE_ID}"
              
              # Force push or push with lease to handle potential conflicts
              git push -f origin "$BRANCH"

              PR_URL=$(gh pr create \
                --title "[Auto] Review game assessment request submitted through #${ISSUE_ID}" \
                --body "This PR generates a request to review #${ISSUE_ID} for ${GAME_NAME} by ${AUTHOR}." \
                --head "$BRANCH" \
                --base main)
            fi

            echo "A PR has been submitted for review, please wait for approval" > /tmp/issue_comment.txt
            gh issue comment $ISSUE_ID --body-file /tmp/issue_comment.txt
            gh label create "pending-approval" --color FBCA04 --description "awaiting approval" || true
            gh issue edit "$ISSUE_ID" --add-label "pending-approval"
            gh issue edit "$ISSUE_ID" --title "[Games] Assessment for: ${GAME_NAME}"
```