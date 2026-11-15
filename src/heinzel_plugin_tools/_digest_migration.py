"""Pinned old-to-new gallery input digests of this repository's galleries at the ADR 0003 flip.

Each key is a digest a gallery or screenshot definition was reviewed under while the locks, the plugin version and its
dependency declarations were capture inputs; each value is the digest of the same source under the rule that leaves
them out, computed at the flip while the old digest still matched. An entry keeps exactly that reviewed source
current through a later relock, security floor or version bump; any change to what renders makes it stale.
"""

MIGRATED_DIGESTS: dict[str, str] = {}
