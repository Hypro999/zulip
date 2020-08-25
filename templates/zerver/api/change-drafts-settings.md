# Change drafts settings

{generate_api_description(/settings/drafts:patch)}

## Usage examples

{start_tabs}

{tab|curl}

{generate_code_example(curl)|/settings/drafts:patch|example}

{end_tabs}

## Parameters

Right now the only draft setting that exists is to either enable or
disable sync.

{generate_api_arguments_table|zulip.yaml|/settings/drafts:patch}

## Response

#### Return values

{generate_return_values_table|zulip.yaml|/settings/drafts:patch}

#### Example response

A typical successful JSON response may look like:

{generate_code_example|/settings/drafts:patch|fixture(200)}
