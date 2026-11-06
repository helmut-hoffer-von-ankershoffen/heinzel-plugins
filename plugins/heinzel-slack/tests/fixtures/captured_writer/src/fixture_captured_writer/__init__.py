"""A source-captured offline document writer; only the real host decides when its fixture write may occur."""

import hashlib

from heinzel import (
    CapturedWriteAcknowledgement,
    CapturedWriteLease,
    CapturedWriteReview,
    CapturedWriteService,
    ChannelReplyConsumer,
    Document,
    Module,
)

STATE = {"revision": "one", "writes": 0}
module = Module("fixturewrite", "Offline captured writer for installed channel acceptance.")


class Documents:
    def read(self, ref: str) -> Document:
        return Document(ref=ref, title="Synthetic fixture", text="")


class Writes(CapturedWriteService):
    supported_operations = frozenset({"insert-draft"})

    def open_lease(self, draft):
        class Lease(CapturedWriteLease):
            def review(self):
                return CapturedWriteReview(
                    owner=draft.owner,
                    session=draft.session,
                    provider=draft.provider,
                    binding_id=draft.binding_id,
                    account=draft.account,
                    source=draft.source,
                    reference=draft.reference,
                    operation=draft.operation,
                    section=draft.section,
                    base_revision=STATE["revision"],
                    content_sha256=hashlib.sha256(draft.content.get_secret_value().encode()).hexdigest(),
                    write_scope=draft.write_scope,
                    conditional_mutation=True,
                )

            def write(self):
                if STATE["revision"] != draft.base_revision:
                    raise ValueError("Synthetic revision conflict")
                STATE["writes"] += 1
                STATE["revision"] = "two"
                return CapturedWriteAcknowledgement(reference=draft.reference, revision="two")

            def close(self):
                pass

        return Lease()


module.service(Writes)
module.provides("documents", name="fixturewrite", modes={"read"}, hosts=["fixture.invalid"])(Documents)


@module.operation(private=True, read_only=False)
def consume_replies(consumer: ChannelReplyConsumer) -> int:
    """Invoke the real host consumer under this ordinary authenticated web request."""
    return consumer.apply_channel_replies()
