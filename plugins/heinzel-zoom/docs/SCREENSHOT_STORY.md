**Audience.** People who receive Zoom summary emails and want meeting decisions and next actions available to Heinzelmännchen workflows.

**Outcome.** Answer “What did we decide, and who acts next?” using parsed summary emails. Installation requires a bound mail adapter and Zoom sending summaries to that mailbox; this plugin needs no Zoom credentials. These are summaries, not verbatim transcripts.

**Scenes.** Preserve the existing five scenes and add one supported parameter case:

1. **meeting-decisions:** In the native app terminal, read the fictional Weekly sync: ship Thursday after phone checks, with next steps for Jonas, Priya and Mira.
2. **recent-meetings:** Show the fictional October meeting table with Weekly sync and Launch review, UTC start times and participant names.
3. **launch-decisions:** Read Launch review using the second meeting argument. Show its ten-percent rollout decision and two named owners.
4. **summary-cli:** Retain the shell result showing Weekly sync’s parsed sections and source link.
5. **meeting-list-json:** Retain structured meeting metadata for workflow authors. Do not describe this output as transcript text.
6. **workflow-context:** Retain the existing Meeting notes contract view. It declares a summary input and Markdown output; it has not generated a report.

**Fictional fixtures.** Reuse only `docs/screenshot_fixture.py`. During explicit capture it supplies the local mailbox, `showcase` requester and demonstration contract. Its existing `sync`, `launch` and newsletter messages use fictional people and decisions. The requester calls the real installed Zoom adapter. `showcase` commands are documentation fixtures; the plugin’s own CLI operation is `hz zoom info`. Freeze browser time after the fixture meetings; the requester’s October window is already fixed.

**Privacy pitfalls.** Capture only the temporary fictional profile without connected accounts. Names, meeting identifiers, decisions and source URLs can remain visible, so real mailbox data must never replace these fixtures. Leave source links unopened. The supplied messages do not exercise address redaction or token removal, so screenshots cannot establish those protections. Treat the rollout and readiness statements as fictional meeting content.

**Acceptance criteria.**

- Six scenes retain all five existing subjects, with four useful app views and two CLI results. The native terminal demonstrates `one sync` and `one launch`.
- Weekly sync shows its decision and three owners; Launch review shows its different decision and two owners. The meeting table and JSON contain the two matching summaries and exclude the newsletter.
- Summary headings, actions and table columns are readable without clipping. The contract heading is visible, with no claim of generated notes.
- Every caption explicitly identifies fictional data and stays below 180 characters. Commands use argument arrays; terminal actions have no redundant cell waits.
- The plan was statically checked by inspection against the requested structure and supplied fixture. No code, imports, captures or runtime validator were executed; visual capture verification remains pending.
