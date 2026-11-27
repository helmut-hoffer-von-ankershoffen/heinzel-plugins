#!/bin/sh
# Trusted local controller. Provision only in the isolated clone's hooks directory.
# The ordinary prek-generated pre-commit runner remains beside this shim.
set -eu
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
stock="$here/pre-commit.gallery-stock"
if [ "${HZ_TRUSTED_GALLERY_PRECOMMIT+x}" != x ]; then
    exec "$stock" "$@"
fi
if [ "$HZ_TRUSTED_GALLERY_PRECOMMIT" != 1 ] || [ -n "${SKIP-}${PREK_SKIP-}" ]; then
    echo "Trusted gallery pre-commit request or hook skip refused." >&2
    exit 1
fi
launcher="$here/gallery-precommit"
"$launcher" "$PWD" before
"$stock" "$@"
exec "$launcher" "$PWD" after
