## Audience
People deciding whether to bring Zoom meeting decisions and next steps into Heinzelmännchen workflows, especially those who already receive Zoom AI Companion summaries by email.

## Outcome
Show how a fictional mailbox becomes a browsable list of meetings and structured summaries with decisions and owners. Make clear that the plugin reads summary emails through a bound mail adapter; it does not need Zoom credentials, and the summaries are not verbatim transcripts.

## Scenes
1. **Weekly sync:** Open with a concrete decision and three next steps in the app’s native terminal.
2. **Recent meetings:** Show the two fictional October meetings and their participants, making the discovery step clear.
3. **Launch review:** Run the same single-summary operation with a second meeting argument to show a different decision and owners.
4. **Summary CLI:** Show the parsed Weekly sync sections and source link as a command-line result.
5. **Meeting list JSON:** Show typed meeting metadata for workflows that consume structured output.
6. **Workflow context:** Show the fictional Meeting notes contract as an example of a declared input and output, explicitly without implying that a report has run.

## Fictional fixtures
Use the existing documentation bootstrap and its isolated mailbox, requester and contract. Weekly sync and Launch review are fictional Zoom summary emails; the requester exercises the real Zoom adapter. The newsletter is ordinary fixture mail, not a meeting. The showcase commands and contract are documentation fixtures, not plugin features installed for users.

## Privacy pitfalls
Capture only the isolated fixture profile, never a connected mailbox. Avoid real names, addresses, meeting links, tokens and message content. The fixture uses example identities and a demo source link. The parser removes addresses from summary text, drops address-only names and strips link queries and fragments, but meeting titles, names and summary content can still be sensitive. Review each image and JSON output before publication.

## Acceptance criteria
- The app views visibly show both fictional meetings and the two distinct summary results; captions identify the fixture-only requester.
- The CLI captures show useful parsed content and typed metadata, with no claim of a verbatim transcript.
- The contract view is clearly a declaration, not a generated report.
- All captures use the existing bootstrap and local routes; no real account or external service is needed.
- The plan retains the existing six scenes. It has been reviewed for the requested structure and TOML syntax; capture behavior was not executed or verified.
