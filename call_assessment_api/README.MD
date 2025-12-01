# call asseessment git actions workflow
## request validation (Previous Step)
- **workflow trigger**
```yaml
      - name: Validate Request
        uses: drewpypro/drewpy-actions/request_validation@gamesv1
        id: request_validation
        with:
          game_name: ${{ steps.pre_process_validation.outputs.game_name }}
```
- **workflow example output**
```sh
Run drewpypro/drewpy-actions/request_validation@gamesv1
  with:
    game_name: curtain fun
  env:
    pythonLocation: /opt/hostedtoolcache/Python/3.10.19/x64
    PKG_CONFIG_PATH: /opt/hostedtoolcache/Python/3.10.19/x64/lib/pkgconfig
    Python_ROOT_DIR: /opt/hostedtoolcache/Python/3.10.19/x64
    Python2_ROOT_DIR: /opt/hostedtoolcache/Python/3.10.19/x64
    Python3_ROOT_DIR: /opt/hostedtoolcache/Python/3.10.19/x64
    LD_LIBRARY_PATH: /opt/hostedtoolcache/Python/3.10.19/x64/lib
Run actions/setup-python@v4
Installed versions
Run python3 "/home/runner/work/_actions/drewpypro/drewpy-actions/gamesv1/request_validation/request_validation.py" \
 Validation Okay
   Original: curtain fun
   Slug: curtain-fun
```
## call assessment api workflow
  * where assessment instructions, context and persona are stored. 
  * generates game assessment json db. 
  * docs are built from output json using jinja template.
  * PR is generated for review.

## post call assessment workflow
- **docs-sync workflow**
    * pushes assessment files to drewpypro docs repo which auto-generates new page.

## **drewpy-actions/call_assessment_api.py**
### high-level
- This script takes an input to AI generate an assessment for a video game based on pre-built instructions and output schema.
- A JSON DB is returned from the AI endpoint and translated to markdown using a jinja template.

## Script Logic
- Defines classes for results and output used by the pipeline and various script steeps. 
- Defines error messages as variables provided as output to return back to the users git issue. 
- **set_github_output** - sets the $GITHUB_OUTPUT variable to write the resulting files. 
  - Sets the github-action-runners root path or $GITHUB_WORKSPACE path to the runner root or if available the $GITHUB_WORKSPACE variable.
- **slugify** - takes user input and converts to script friendly format used for creating files and other tasks. 
- **load_schema** - set the schema requirements that is provided to the AI model as an input. 
- **load_instructions** - load all instruction files in order to be provided as input to the AI model. 
- **get_slug_from_data** - loads slug from **slugify** else fallback to assessment which is used to determine the markdown filename. 
  - In future use of "target" will set the domain if the script needs to support multiple domains (games, finances, etc. )
- **make_default_json_path** - generates the output path based on the provided game name and replaces characters as necessary. 
- **generate_assessment_json** - loads instructions, schema and builds payload to call gpt-5.1 using OpenAI responses API. 
- **generate_markdown_from_json** - generates the markdown from the output assessment JSON using Jinja2 template. 
- **main** - sets arguments for script operation.
