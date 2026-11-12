## Audience

Someone considering a way to bring Zoom meeting decisions into Heinzelmännchen workflows without granting a Zoom API credential.

## Outcome

Show how fictional summary emails become a browsable list of meetings and readable decisions, then show the same information as structured CLI output. Make clear that the plugin reads Zoom’s emailed summaries through a bound mail adapter; the summaries are not verbatim transcripts.

## Scenes

1. **Meeting decisions:** Open the fictional Weekly sync in the app terminal, with its release decision, next steps, and source link.
2. **Recent meetings:** Show the fictional October meeting list, including Weekly sync and Launch review, with start times and participants.
3. **Another meeting:** Open Launch review in the app terminal to demonstrate a different meeting argument and its rollout decision.
4. **Summary in the CLI:** Show the parsed Weekly sync sections and source link in a standalone CLI capture.
5. **Structured meeting data:** Show the fictional meeting list as JSON for a workflow that consumes typed metadata.
6. **Workflow context:** Show the fictional Meeting notes contract declaring a meeting-summary input and Markdown output, without implying a report was generated.

## Fictional fixtures

Use the existing `docs/screenshot_fixture.py` bootstrap. It supplies a local fictional mailbox, a fixture-only `showcase` requester, and a demonstration contract while exercising the real Zoom adapter. The meeting titles, decisions, names, addresses, and source link are examples; no connected account is needed.

## Privacy pitfalls

Do not capture real mail, meeting names, participants, addresses, tokens, or account details. The example source link is fictional. Explain that the adapter removes addresses from summary text, drops participant names that are email addresses, and strips link query strings and fragments; do not suggest that this makes arbitrary real meeting content suitable for publication. Zoom-generated summaries can be inaccurate and should be checked.

## Acceptance criteria

- Preserve the existing six-scene plan: it demonstrates two useful app-terminal views, a second meeting argument, CLI results, and workflow context.
- Each caption identifies the material as fictional; the requester is described as fixture-only where applicable.
- Captures show the stated fictional decisions and meeting metadata, and the JSON scene shows structured meeting data.
- The contract scene is presented as a declaration, not a generated report.
- No screenshot implies a Zoom API connection or a verbatim transcript.
- Capture and inspect the images offline before publication. The TOML was checked against the supplied field rules by inspection; execution and capture validation were not performed.
