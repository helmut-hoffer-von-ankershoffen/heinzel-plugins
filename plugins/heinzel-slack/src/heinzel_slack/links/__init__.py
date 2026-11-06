"""Source-captured reviewed-link transport in its own module record, separate from the Slack bot channel."""

import heinzel
import heinzel.kernel as kernel_contracts
from heinzel import Module

module = Module("links", "Send one approved document link through the selected SlackCLI profile.")
if (
    hasattr(kernel_contracts, "ReviewedLinkChannel")
    and callable(getattr(heinzel, "captured_source_active", None))
    and heinzel.captured_source_active()
):
    from heinzel_slack.links._reviewed_link import SlackReviewedLinks

    module.service(SlackReviewedLinks)
