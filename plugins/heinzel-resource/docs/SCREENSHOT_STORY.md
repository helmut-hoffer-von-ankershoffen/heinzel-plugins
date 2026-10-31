# Understand what is slowing this computer down

The installation story is a compact resource monitor that stays available while working: CPU, memory and queued
load in the footer, a readable detail pane, and a quick Today summary. A CPU-only Today card does not demonstrate
the full plugin; the expanded pane is the primary catalog image.

## Demonstration profile

Use the owning `docs/screenshot_fixture.py` bootstrap before starting the installed application or CLI. It supplies
one internally consistent fictional `Resources` sample: host **demo-workstation**, CPU **36%**, memory **62%**,
one-minute load **0.65**, **8** logical cores, no problems, sampled at **2026-10-31 10:00 UTC**. Never sample the
operator's machine for publishable images. The fixture replaces this plugin's sampler only; it does not change
production behavior or substitute a hand-drawn interface.

The current fixture runs the real command after installing the sample:

```sh
python docs/screenshot_fixture.py resource
python docs/screenshot_fixture.py resource --json
python docs/screenshot_fixture.py ui --no-browser --port 0
```

Run these from the owning plugin in its installed SDK environment and isolated profile. The capture runner should
use the bootstrap for both UI and CLI scenes. Normal public commands remain `hz resource` and `hz resource --json`.

## Scenes to publish

| Scene | Action and visible proof | Caption |
| --- | --- | --- |
| `resources-pane` | At `/`, click the footer button whose accessible name contains **CPU**, **Memory**, **Load**. Wait for region **Computer resources…** and **Host: demo-workstation**. Keep all three compact meters and the whole expanded pane visible: CPU 36%, Memory 62%, Load (1 min) 0.65, 8 logical cores, and the explanation that load measures queued work. | “Inspect CPU, memory and queued load from the compact resource monitor — demonstration workstation.” |
| `today-resources` | At `/`, wait for **Computer resources** and **CPU 36%**. Frame the Today card and the compact footer meters together, without the detail pane obscuring either. | “Keep a quick CPU summary on Today and all three resource meters in the footer.” |
| `phone-resources` | At 390×844, open **More status items** if the meters moved there; then open the same resource control. Show the complete detail pane above its trigger, inside the phone viewport. | “Read the same resource detail on a narrow screen.” |
| `cli-resources` | Execute `hz resource` through the fixture and capture its real Rich table. It must show the fictional hostname, CPU, memory, raw load and logical core count, matching the UI. | “Read the same demonstration measurements in the CLI.” |

Accessible actions and phone behavior are exercised in `tests/browser/meters.mjs`: locate the footer landmark,
the **More status items** button, the control matching `CPU.*Memory.*Load`, and the **Computer resources** region.
Use Escape to dismiss the pane. Do not invent a right-side resource workspace panel; the implemented detail is a
footer popover. Resource has no sidebar placement by default.

## Acceptance and privacy

All three measurements must be legible in the main image. The load meter is normalized to twice the logical-core
count: this fixture's **Load (scaled)** display value is about **4.06%**, while the detail and CLI show raw load **0.65**. Do not call
load a CPU percentage or label the normalized meter as raw load. The Today card intentionally shows CPU only.

Reject missing meters, real hostnames, changing native samples, **Unavailable** values, clipped popovers, loading
states and unrelated error cards. Check desktop and phone geometry, and compare UI and CLI values. Stage drafts
and transcripts privately; an agent must review every final image for personal names, machine identifiers, paths,
tokens and account data before promoting the gallery. The approved hostname is exactly **demo-workstation**.

The expanded detail scene uses a native browser crop with 48 pixels of surrounding context. Keep the complete
popover and its footer trigger visible; let its natural aspect ratio make the values readable on a phone.
