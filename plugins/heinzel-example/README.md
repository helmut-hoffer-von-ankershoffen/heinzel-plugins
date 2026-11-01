# heinzel-example

Show how a Heinzelmännchen plugin is built: one module with an operation, settings, a health check and a submodule.

A plugin for [Heinzelmännchen](https://github.com/helmut-hoffer-von-ankershoffen/heinzel), the open-source, AI-driven
operating system for product development teams. It lives in
[heinzel-plugins](https://github.com/helmut-hoffer-von-ankershoffen/heinzel-plugins).

## Install

Start Heinzelmännchen with `uvx heinzel@latest`. In another terminal, add this plugin:

```sh
hz system plugin add example --confirm
```

`hz system update` updates the app and its plugins; `hz system plugin remove heinzel-example` removes this one.

## Use

```bash
hz example info                 # this plugin, its version and the Heinzelmännchen it runs on
hz example hello --name Ada     # a submodule collapsed into a command
hz example info --json          # every command speaks JSON, for scripts and agents
hz system info                  # includes a section contributed by this plugin
```

## Develop

From the repository root: `make check-fast NAME=example` runs this plugin's edit loop; `make check NAME=example`
runs its full checks. `make build NAME=example` and `make acceptance NAME=example` verify its installed artifact.
The modules live in
`src/heinzel_example/`; read the root [AGENTS.md](../../AGENTS.md) before changing them.

Development and release commands: [repository guide](../../README.md).


<!-- screenshots:start -->
## Screenshots

<img src="docs/assets/screenshots/widget-and-status.png" alt="Demo data: the constant 42 appears in both the Today widget and sidebar status." width="960">

Demo data: the constant 42 appears in both the Today widget and sidebar status.

<img src="docs/assets/screenshots/inspector.png" alt="Demo data: open the plugin-owned inspector to see the same constant value, 42." width="960">

Demo data: open the plugin-owned inspector to see the same constant value, 42.

<img src="docs/assets/screenshots/greeting-terminal.png" alt="Demo data: greet fictional Mira with structured JSON in the app&#x27;s native terminal." width="960">

Demo data: greet fictional Mira with structured JSON in the app&#x27;s native terminal.

<img src="docs/assets/screenshots/plugin-notice.png" alt="Demo data: a seeded Example is ready notice appears in the shared in-app notification panel." width="960">

Demo data: a seeded Example is ready notice appears in the shared in-app notification panel.

<details>
<summary>Command line</summary>

<img src="docs/assets/screenshots/greeting-cli.png" alt="Demo data: the typed hello operation greets fictional Mira from the CLI." width="960">

Demo data: the typed hello operation greets fictional Mira from the CLI.

<img src="docs/assets/screenshots/sample-json.png" alt="Demo data: sample returns 42 as JSON, the same constant used by the widget, status and inspector." width="960">

Demo data: sample returns 42 as JSON, the same constant used by the widget, status and inspector.

</details>

[Open the screenshot gallery](docs/assets/screenshots/index.html).
<!-- screenshots:end -->
