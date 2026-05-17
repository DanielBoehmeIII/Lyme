"""Shared text cleanup for model-generated output.

Strips trailing structural markers and template artifacts that models
sometimes append after generating their actual response (typically
because ``max_new_tokens`` cuts off mid-template).

Both the subprocess worker path and the persistent server path use
this same function so cleanup is consistent regardless of execution mode.
"""

import re


def clean_generated_output(output: str) -> str:
    """Strip trailing structural markers and template artifacts from model output.

    Removes suffixes like:
    - ``Context:Repository:...`` (start of context template block)
    - Bare ``Context:``, ``User:``, ``Assistant:`` at the end
    - Unfinished section headers (word followed by colon with nothing after)

    The function loops until no further cleanup occurs, so patterns like
    ``Hello.\\nContext:\\nUser:`` are stripped one layer at a time.
    """
    result = output.strip()

    while True:
        original = result

        # Context:Repository:... suffix (structural template artifact)
        result = re.sub(r'\s*Context:\s*Repository:.*$', '', result)

        # Trailing bare structural markers
        result = re.sub(r'\s*(?:Context:|User:|Assistant:)\s*$', '', result)

        # Unfinished section header on its own line at the end
        result = re.sub(r'\n\s*\w[\w\s]*:\s*$', '', result)

        if result == original:
            break
        result = result.strip()

    return result.strip()
