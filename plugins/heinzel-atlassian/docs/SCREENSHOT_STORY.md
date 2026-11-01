**Audience**
People building Heinzel workflows that need Jira progress and Confluence context through their existing Atlassian access.

**Outcome**
Follow a small Widget launch: see what changed, read the plan, inspect structured issue data, and understand how a workflow declares both inputs. Production reads use the user's authenticated acli; these screenshots demonstrate real adapter parsing with fictional local replies.

**Scenes**
1. **jira-issues** — The native app terminal shows October changes: WID-3 is In Progress with Wilma Widget; WID-4 is Done and Unassigned.
2. **confluence-plan** — Read the fictional launch scope and next milestone, with the source URL and revision 3 visible.
3. **issues-json** — Show structured issue results for workflow authors, including timestamps and labels.
4. **confluence-cli** — Show the same readable document result through the CLI.
5. **workflow-context** — Preserve the existing contract-detail scene. Its declared Jira and Confluence inputs explain the connection; no report has been generated.
6. **jira-parameters** — Add a native-terminal case using lowercase `wid` and `--json`. Together with the first scene, this demonstrates project-key normalization and two useful argument combinations.

**Fictional fixtures**
Use only the existing `docs/screenshot_fixture.py`. It supplies the WID issues, Widget plan, and local Weekly work review contract. Its documentation-only `showcase issues` and `showcase page` requesters call the real adapters through `DemoAcli`; the placeholder executable path is never run. The issue window is October 2026. Freeze browser time at its upper boundary.

The installed Atlassian module exposes parameterless `atlassian info`; `showcase` commands belong to the capture fixture and must not be presented as installed product commands. Preserve the existing five scenes and append only the additional native-terminal parameter case.

**Privacy pitfalls**
Capture only an isolated fictional profile through the existing bootstrap during explicit capture. Keep real accounts, tenant names, credentials, local paths, and unrelated terminal history out of frames. Treat the example source links as display data. Do not imply a successful login or live Atlassian verification: the README says signed-in acli response shapes remain unverified, and browser-login replies cannot confirm the configured tenant. Installation requires acli 1.3.39 or later, appropriate product logins, site configuration, and capability bindings.

**Acceptance criteria**
- Six scenes retain the existing useful views and CLI results; both native-terminal parameter cases complete successfully.
- Every caption explicitly identifies demo data and stays within 180 characters.
- Issue states and owners, document content, source and revision, and structured issue fields remain readable.
- The inherited contract route resolves to the fixture's Weekly work review heading and shows declaration context without implying an executed workflow.
- Commands use argument arrays; terminal actions rely on their completion behavior without individual-cell waits.
- TOML structure, allowed fields, unique names, captions, fixture commands, and bootstrap provenance were checked statically against the supplied files and requirements. No imports, runtime validation, captures, or network calls were performed; rendered behavior remains an explicit capture acceptance check.
