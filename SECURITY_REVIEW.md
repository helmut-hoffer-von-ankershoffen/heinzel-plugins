# Developer tooling security review

The toolkit is a local developer CLI, separate from installed plugin operations. Its commands deliberately select
local files, interpreters and output directories. This does not remove command-option boundaries: an argument
vector prevents shell interpolation, but a tool can still interpret an operand beginning with `-` as an option.

## Fixed boundaries

- The confidentiality scanner rejects option-shaped revision ranges and uses Git's `--end-of-options` plus a path
  separator. Integration tests cover an injected output option and real commit-range scanning with redaction.
- The planner rejects an option-shaped `--base` and places the revision after `--end-of-options`. Tests invoke real
  Git in a temporary repository and prove both malicious output rejection and normal changed-plugin selection.
- SDK candidate files are normalized to absolute paths before `uv pip install`, both for development environments
  and installed-wheel acceptance. A relative `--target=.../wheel.whl` cannot become an installation option. Both
  paths have regression coverage. Explicit HTTPS candidate URLs remain supported.
- CI and direct PR/publisher helper runs use frozen root dependencies and disable dependency source builds. The
  project also sets `no-build = true`. Plugin runtime lock installation uses hashes and disables source builds;
  Toolkit environment preparation and installed-wheel acceptance disable source builds too. Intentional local plugin builds and editable
  development builds remain explicit. This policy is not a sandbox for the programs invoked by developer commands.
- Native actionlint 1.7.12 replaces the source-only Python wrapper for the same version. The existing installer
  verifies official binary SHA-256 values for each supported platform before execution.

## Reviewed analysis findings

An independent security review inspected complete source-to-sink flows before resolving these false positives.
No rules were disabled and no real vulnerability was accepted to change the badge. The original Git-option and
SDK-install findings above required code fixes; installation findings require a fresh analysis of those fixes.

| Surface | Evidence for the reviewed false-positive disposition |
| --- | --- |
| `tools.pin` | Manifest **content** flows to `write_text`'s data argument. The CLI destination is fixed `scripts/tools.toml`. |
| `audit.main` | The owning prepared `.venv` supplies the interpreter and validated project metadata supplies the package name. Inspection code is fixed; no shell or remote operation supplies these inputs. |
| Compatibility and frontend wrappers, `tools.run` | Developer argv follows a fixed toolkit command/module or deliberately selected pinned tool. Automated frontend callers use fixed build/test commands. These interfaces have no remote or privileged entry point. |
| Candidate metadata, locks and profiles | Local wheel inputs and output paths are intentionally chosen by the developer. This is separate from the fixed SDK install-option boundary. |
| Publication and restoration | Repository, distribution, tag prefix and canonical version are validated. API endpoints begin with fixed `repos/`; download tags cannot become options. Output is local, with separate basename and size checks for downloaded assets. |
| Git commit-message hook | Git supplies a local filename, legitimately outside a linked checkout. The scanner reports term numbers rather than file contents. |
| Managed-profile acceptance | Artifact paths originate in a locally generated profile and feed integrity checks, without a remotely callable filesystem oracle or returned file content. |
| App composition download | Initial URL is restricted to HTTPS official GitHub release path and matching core identity. The final response URL must be HTTPS; official attestation and source digest are verified before execution. |
| Google Docs HTTP strings | Preserved Markdown link text; the converter makes no HTTP request. |
| Tailscale HTTP | Parsed loopback endpoint or Unix-domain socket, with no inherited proxy or redirects. The socket transport does not cross the network. |
| Weather fake HTTP | Local test fixture bound to the constant `127.0.0.1`; the printed URL is not a production remote transport. |

Revisit these conclusions if the toolkit is exposed through HTTP/MCP, consumes remote paths or runs with higher
privileges. A passing new-code quality gate does not establish overall security A: verify `security_rating`, zero
unresolved vulnerabilities and the main-branch badge after merging and reanalysis.
