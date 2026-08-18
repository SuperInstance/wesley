#!/usr/bin/env python3
"""Shared, testable logic for the Wesley night school pipeline.

The night school feeds pieces to Wesley (``granite3.1-dense:2b`` on local
Ollama), saves his responses, and sends one response up to the Cloudflare
Workers AI teacher for a single actionable critique.

This module holds the pure transformations — slugging, prompt building,
session-file rendering, and response-body extraction — so the thin runner
scripts (``wesley-session.py``, ``wesley-teacher.py``) stay I/O shells and
the logic can be regression-tested without a live GPU or network.

All functions are pure: no filesystem, no network, no clock. (The runners
own the real I/O.) Run the doctests with ``python3 -m doctest
wesley_night_school.py`` and the suite with ``pytest test_wesley_night_school.py``.
"""
import re

# Models, kept here so the runners have one place to change them.
WESLEY_MODEL = "granite3.1-dense:2b"
TEACHER_MODEL = "@cf/meta/llama-3.1-8b-instruct-fast"

# Standing curriculum (from wesley-journal/feedback.md):
# - num_predict 250 (truncation fix, raised from 150)
# - assignment: one image that is NOT in the original
# - start where the noticing starts, no throat-clearing wonder-words
PROMPT_TMPL = (
    "Read this and write a 3-sentence creative response. Be young. Be surprised. "
    "Include one image that is NOT in the original. Do not open with words like "
    "'whimsical,' 'fascinating,' or 'astonishing' - start where the noticing starts."
    "\n\n---\n\n{body}"
)


def slug(filename):
    """Strip a leading ``YYYY-MM-DD-HHMM-`` stamp and the ``.md`` extension.

    >>> slug("2026-08-13-1745-the-watch-that-never-ends.md")
    'the-watch-that-never-ends'
    >>> slug("the-shell.md")
    'the-shell'
    >>> slug("2026-08-11-0800-a-letter-from-the-quota-gate.md")
    'a-letter-from-the-quota-gate'
    """
    stripped = re.sub(r"^\d{4}-\d{2}-\d{2}-\d{4}-", "", filename)
    return stripped.replace(".md", "")


def build_prompt(body):
    """Wrap a piece's body in the standing night-school assignment prompt.

    >>> build_prompt("hello").endswith("---\\n\\nhello")
    True
    >>> "3-sentence creative response" in build_prompt("")
    True
    """
    return PROMPT_TMPL.format(body=body)


def render_session_file(slug, source, timestamp, eval_tokens, done_reason, text, body):
    """Render a Wesley response into the saved markdown session file.

    Produces the exact on-disk layout written by ``wesley-session.py``:

        # Wesley reads: <slug>
        *Night school, <timestamp> AKDT. Source: <source>*
        *Prompt: ... Generated <n> tokens, done_reason=<reason>.*
        ---
        <Wesley's response>
        ---
        *Reading time: <n> lines fed. Wesley is 2B parameters of pure earnestness.*
    """
    line_count = len(body.splitlines())
    return (
        f"# Wesley reads: {slug}\n\n"
        f"*Night school, {timestamp} AKDT. Source: {source}*\n\n"
        "*Prompt: 3-sentence creative response, be young, be surprised, one image NOT in the "
        "original, no stock wonder-words. temp 0.95, num_predict 250 (standing truncation fix). "
        f"Generated {eval_tokens} tokens, done_reason={done_reason}.*\n\n---\n\n"
        f"{text}\n\n---\n\n"
        f"*Reading time: {line_count} lines fed. "
        "Wesley is 2B parameters of pure earnestness.*\n"
    )


def extract_response_body(wesley_markdown):
    """Pull just Wesley's response out of a rendered session file.

    Session files lay the response between the first and last ``---``
    markers. We locate both markers rather than ``str.split``, so a response
    that itself contains a ``---`` separator is not truncated. Falls back to
    the whole (stripped) input when the markers are absent.

    >>> doc = "# header\\n\\n*meta*\\n\\n---\\n\\nThe answer.\\n\\n---\\n\\n*footer*\\n"
    >>> extract_response_body(doc)
    'The answer.'
    >>> extract_response_body("no markers here")
    'no markers here'
    """
    marker = "---"
    first = wesley_markdown.find(marker)
    if first == -1:
        return wesley_markdown.strip()
    last = wesley_markdown.rfind(marker)
    if last <= first:
        return wesley_markdown.strip()
    return wesley_markdown[first + len(marker):last].strip()
