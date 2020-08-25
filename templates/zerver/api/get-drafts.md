# Fetch drafts

{generate_api_description(/drafts:get)}

## Usage examples

{start_tabs}

{tab|curl}

{generate_code_example(curl)|/drafts:get|example}

{end_tabs}

## Parameters

{generate_api_arguments_table|zulip.yaml|/drafts:get}

## Response

#### Return values

This endpoint will return a list of dictionary objects in order of last edit time
(with the most recently edited draft being first).

{generate_return_values_table|zulip.yaml|/drafts:get}

#### Example response

A typical successful JSON response may look like:

{generate_code_example|/drafts:get|fixture(200)}
