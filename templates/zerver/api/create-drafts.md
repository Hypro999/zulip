# Create drafts

{generate_api_description(/drafts:post)}

## Usage examples

{start_tabs}

{tab|curl}

{generate_code_example(curl)|/drafts:post|example}

{end_tabs}

## Parameters

{generate_api_arguments_table|zulip.yaml|/drafts:post}

## Response

#### Return values

This endpoint will return a list of dictionary objects in order of last edit time
(with the most recently edited draft being first).

{generate_return_values_table|zulip.yaml|/drafts:post}

#### Example response

A typical successful JSON response may look like:

{generate_code_example|/drafts:post|fixture(200)}
