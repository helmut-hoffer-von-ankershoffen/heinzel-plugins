# Catalog screenshots

Captured from the running plugin with Heinzelmännchen 0.9.8 in an isolated demonstration profile.
The profile uses fictional identity data and has no connected accounts. Connector captures show configuration,
not authenticated service results. CLI images render the output of the commands below; they are not mock output.
Resource captures omit the machine hostname. Theme captures show the installed theme in light and dark modes.

| Surface | Capture |
| --- | --- |
| CLI | [hz resource --json \| jq 'del(.hostname)' — isolated demonstration profile](assets/cli.png) |
| UI | [Live computer resource widget in Today](assets/ui.png) |

Re-capture the running app or CLI after changing its interface, commit the raster files, and keep
`tool.heinzel.catalog.screenshots` in `pyproject.toml` current. Keep captures free of private data.
