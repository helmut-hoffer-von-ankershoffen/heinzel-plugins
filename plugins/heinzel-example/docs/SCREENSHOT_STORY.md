# One tiny plugin, visible throughout the app.

The example sells extensibility: one small typed value appears as a Today widget, sidebar status and real plugin
panel, while an ordinary command greets someone and a notice uses the host notification policy. Show those
contributions working together. A help listing or installed-plugin card cannot explain this plugin's purpose.

## Required scenes, in gallery order

| Scene | Surface and actual action | Visible result and caption | Why it matters |
| --- | --- | --- | --- |
| A widget without a core edit | UI: home `/` with the Example Today widget and sidebar status visible | Actual “Example value” widget with 42 and “Example: 42” status. Caption: “One plugin contributes a Today widget and sidebar status from the same value.” | Makes the extension mechanism visible in one glance. |
| Open its own panel | UI: click the sidebar link “Example” or the “Example: 42” status | Actual region “Example”, status “The value is 42.”, and “Close example” button. Caption: “Open the plugin-owned inspector from navigation — the same live value.” | Shows a plugin can own a focused interface instead of just commands. |
| A useful command shape | CLI: `hz example hello --name Mira` | Actual greeting using the configured greeting setting; no version metadata. Caption: “A typed plugin operation greets Mira from the command line.” | A newcomer understands what an operation does and how to call it. |
| The same command in the app | UI: open the app terminal and run `hz example hello --name Mira --json` | Complete typed JSON greeting beneath the real command. Caption: “The same operation produces structured output in the app terminal.” | Shows CLI and UI coexist without inventing another plugin screen. |
| A plugin notice | UI: enable only the shared in-app plugin-notice channel in the temporary profile, then execute the real `hz example notify` operation and open the host notifications panel | Actual “Example is ready” notice, with its “hz example sample” action or route visible. Caption: “A plugin notice follows the app's notification policy — isolated demonstration.” | Shows a plugin can get attention through standard host controls. |
| Small result for scripts | CLI: `hz example sample --json` | The actual value 42 with the command visible, optionally alongside the greeting JSON in one narrow demonstration command. Caption: “A small typed result powers the plugin's widget, status and view.” | Closes the loop from returned data to all three visual contributions. |

Keep the compact sample image secondary to the richer widget/panel scenes. If the notice channel cannot be exercised
without OS prompts, keep it in-app only; do not request notifications permission on the developer's desktop.
`notify` is declared `read_only=False`; the local CLI command has no generic `--confirm` flag. Agent or web callers
use the host's ordinary operation-confirmation policy.
Do not imply an emitted notice means an operating-system notification was delivered.

## Fixture and accessible entry points

No fake business data is necessary. `sample()` really returns 42, `today()` renders “Example value”, and `status()`
renders “Example: 42” with navigation to `/?panel=example:inspector`. The source of truth is
[the public declarations](../src/heinzel_example/__init__.py) and
[the actual view](../src/heinzel_example/views/index.js); the service's `greet` uses the `example.greeting` setting.
Use a fictional Mira profile and a fresh isolated plugin installation, with no sibling plugins required.

- Wait for actual text “Example value” and value “42” on Today. Click `link` **Example** using its exact accessible
  name; wait for `region` **Example** and text “The value is 42.”. Confirm **Close example** works after capture.
- Open `button` **Open a terminal**, then **Full screen**, for the greeting scene. Wait for actual command completion
  and “Mira”, not an arbitrary delay. The greeting must be returned by `ExampleService.greet`.
- The notice capture uses the host's actual accessible notifications control and expected notice text; discover the
  installed host's exact translated label instead of guessing a CSS selector. Test the actual emit result first.

## Acceptance and privacy

The gallery has distinct widget, panel, shell, structured-output and notice evidence, including both UI and CLI.
All three visual data contributions agree on 42; the panel is reached through a real contributed action and can be
closed. The notice is rendered by the ordinary host policy and no OS delivery is claimed. Commands return normally.

Only fictional Mira identity is present. No hostname, absolute home path, session token, real notification text,
credential or signed-in account may appear in screenshots, terminal scrollback or capture metadata. Disable unrelated
onboarding, update and health warnings in the isolated profile so the result is legible without hiding real failures
of the plugin itself. Review both thumbnail usefulness and full-size text before accepting the gallery.
