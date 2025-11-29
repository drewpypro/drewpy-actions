# request validation
- **Workflow trigger**
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
- [request_validation@gamesv1](../reeuest_validation/request_validation.py)

- **drewpy-actions/call_assessment_api.py**
    - where assessment instructions, context and persona are stored. 
    - generates game assessment json db. 
    - takes input $game_name-assessment.json file and generates markdown report based on template. 
- **assessment workflow**
    * runs composite action from drewpy-actions/call_assessment_api.py to trigger researcher response and generate /assessments/$game_name-assessment.json and /assessments/$game_name-assessment.md files and outputs them to $GITHUB_OUTPUT
    * docs are built using jinja template. 


- **workflow output (next step-workinprogress)**
```md
- **drewpy-actions/doc_generator.py**
    - receives input pushed to staging branch and generates required npm and yarn commands required to build the site and deploy the docs on drewpypro.github.io through the gh-pages branch. 
```