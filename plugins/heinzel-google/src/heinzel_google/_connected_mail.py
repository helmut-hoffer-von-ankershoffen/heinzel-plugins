"""Owner-bound Gmail metadata read for an independently approved connected capability."""

import json
from collections.abc import Mapping, Sequence
from typing import Never, SupportsIndex

from heinzel import ConnectedReadLease, ConnectedReadReview, HeinzelError, MailQuery, Window, capability_read_schema
from pydantic import JsonValue

from heinzel_google._captured_mail import CapturedGmailRead
from heinzel_google._connected_calendar import _check_binding, _OwnerBinding, _source_revision
from heinzel_google._connected_items import with_item_identity
from heinzel_google._existing_lease import ReadWindow
from heinzel_google._gws import GoogleSession, Gws, Process
from heinzel_google._mail import Gmail

_OPERATION = "capability-method:mail.messages"
_MAX_QUERY = 1000
_DISCLOSURE = (
    "Gmail may return candidate metadata outside the exact sender, subject or time window; the adapter filters "
    "results locally. "
    "The token has gmail.readonly scope, which can access message content, while this read requests only message "
    "IDs, timestamps, labels and From, To, Cc and Subject headers. "
    "This read accepts at most 100 distinct listed messages; narrow the query or window if it finds more. "
    "Message IDs do not establish a revision, complete history, or whether a message needs attention."
)


class _MailGuard(Gws):
    def __init__(self, lease: CapturedGmailRead, version: str, source: str, binding: _OwnerBinding) -> None:
        self._lease, self._version, self._source, self._binding = lease, version, source, binding

    def run(self, executable: str, arguments: Sequence[str], timeout: float) -> Process:
        _check_binding(self._binding, "mail")
        if _source_revision(self._lease, self._version) != self._source:
            msg = "The Google read implementation changed"
            raise HeinzelError(msg)
        return self._lease.run(executable, arguments, timeout)


class MailReadLease(ConnectedReadLease):
    """One owner, account, query and window; observing the connection is not a grant."""

    def __init__(
        self, binding: _OwnerBinding, session: GoogleSession, session_id: str, fixed: dict[str, JsonValue]
    ) -> None:
        self._binding, self._session, self._session_id = binding, session, session_id
        self._owner = binding.current.principal().id
        self._version = binding.record.origin.version
        self._fixed = json.loads(json.dumps(fixed, ensure_ascii=True, allow_nan=False))
        try:
            if set(fixed) != {"query", "window"} or not isinstance(fixed["query"], str):
                raise ValueError  # noqa: TRY301
            self._query = fixed["query"]
            if len(self._query) > _MAX_QUERY:
                raise ValueError  # noqa: TRY301
            MailQuery.parse(self._query)
            window = Window.model_validate(fixed["window"])
            if window.model_dump(mode="json") != fixed["window"]:
                raise ValueError  # noqa: TRY301
            self._window = ReadWindow(window.since, window.until)
        except (ValueError, TypeError, KeyError):
            msg = "The reviewed Google mail query or window is invalid"
            raise HeinzelError(msg) from None
        self._lease = CapturedGmailRead(binding.current, session)
        try:
            self._identity = self._lease.inspect_identity()
            self._scopes = self._lease.observed_scopes()
            self._lease.bind_mail_review(self._identity, self._window, self._scopes, self._query)
            self._source = _source_revision(self._lease, self._version)
        except BaseException:
            self._lease.discard()
            raise

    def __repr__(self) -> str:
        return "<GmailReadLease private>"

    def __reduce_ex__(self, _protocol: SupportsIndex) -> Never:
        msg = "A private Google connection lease cannot be serialized"
        raise TypeError(msg)

    def review(self) -> ConnectedReadReview:
        """Describe the exact owner/account/source and metadata query for human review.

        Raises:
            HeinzelError: If the account, source or owner changes.
        """
        _check_binding(self._binding, "mail")
        if (
            self._binding.current.principal().id != self._owner
            or _source_revision(self._lease, self._version) != self._source
        ):
            msg = "The Google connection source changed"
            raise HeinzelError(msg)
        if self._lease.inspect_identity() != self._identity or self._lease.observed_scopes() != self._scopes:
            msg = "The Google connection account or scopes changed"
            raise HeinzelError(msg)
        _, schema_sha256 = capability_read_schema("mail", "messages")
        review = ConnectedReadReview(
            owner=self._owner,
            session=self._session_id,
            operation=_OPERATION,
            schema_sha256=schema_sha256,
            source_revision=self._source,
            account_identity=self._identity.permission_id,
            account_display=self._identity.email,
            provider_scopes=self._scopes,
            fixed_arguments=self._fixed,
            candidate_read_disclosure=_DISCLOSURE,
        )
        return with_item_identity(review)

    def read(self, arguments: Mapping[str, JsonValue]) -> JsonValue:
        """Read metadata matching the reviewed query, never message bodies or writes.

        Raises:
            HeinzelError: If dynamic arguments or changed authority are supplied.
        """
        if arguments:
            msg = "The approved Google mail read accepts no dynamic arguments"
            raise HeinzelError(msg)
        self.review()
        guarded = _MailGuard(self._lease, self._version, self._source, self._binding)
        session = GoogleSession(self._session.settings, guarded)
        return [
            item.model_dump(mode="json")
            for item in Gmail(session).messages(self._query, Window(since=self._window.since, until=self._window.until))
        ]

    def close(self) -> None:
        """Discard the captured token and private process state."""
        self._lease.close()
