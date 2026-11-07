"""Issues: report a problem or request something, and see whether it is received, being worked on or done.

Behind it is any tracker with a connector for the task-tracking contract (`heinzel_issues._contract`); a local Beads
database is built in. The tracker's statuses, ids and workflow stay behind the three plain states; the release that
shipped a fix is read from local git clones. Off until a tracker is set up.
"""

from pathlib import Path

from heinzel import (
    Check,
    ConfigEditor,
    HeinzelError,
    Kernel,
    ListEntry,
    ListWidget,
    Module,
    Navigate,
    Notifications,
    Prompter,
    RunCommand,
    Status,
)
from pydantic import JsonValue
from rich.table import Table
from rich.text import Text

from heinzel_issues._beads import BeadsSettings, BeadsTracker, state_of
from heinzel_issues._contract import (
    ENTRY_POINTS,
    STATE_LABELS,
    Attachment,
    Task,
    TaskState,
    TaskTracker,
    TrackerError,
)
from heinzel_issues._releases import Release, ReleaseResolver, ReleaseSource, released_text
from heinzel_issues._service import (
    NONE,
    NOT_SET_UP,
    ROUTE,
    SETUP,
    IssuesService,
    IssuesSettings,
    Report,
    Reports,
    Watched,
)

module = Module("issues", "Report a problem or request something, and see when it is done and released.")
module.settings(IssuesSettings)
module.service(IssuesService)
module.nav(title="Issues", icon="inbox", sidebar=Navigate(path=ROUTE), order=650)
module.action("requests", label="Issues", icon="inbox", effect=Navigate(path=ROUTE), order=650)
module.view(
    Path(__file__).parent / "views",
    abi=1,
    name="requests",
    source="list",
    title="Issues",
    fallback="Issues cannot be shown here; run hz issues list.",
    order=650,
    refresh=60,
    actions={
        "setup": RunCommand(command=SETUP),
        "report": RunCommand(command="hz issues submit"),
    },
)


def _render(result: Reports) -> Table | Text:
    if not result.ready:
        problem = str(result.problem)
        return Text(f"{problem} Run {result.fix}." if result.fix and result.fix not in problem else problem)
    if not result.reports:
        return Text('Nothing reported yet. Send something with hz issues submit "what happened".')
    table = Table("Report or request", "Status", "Sent")
    for report in result.reports:
        table.add_row(Text(report.title), Text(report.status), f"{report.submitted_at:%d %b %Y}")
    return table


def _render_one(report: Report) -> Text:
    return Text(f"{report.title}\n{report.status}")


def _fail(error: TrackerError) -> HeinzelError:
    return HeinzelError(str(error))


@module.operation(name="list", render=_render, audience="everyday")
def list_(service: IssuesService) -> Reports:
    """Show what you reported or requested: received, being worked on, or done and in which release."""
    return service.overview()


@module.operation(read_only=False, private=True, render=_render_one, audience="everyday")
def submit(service: IssuesService, text: str, attachment: list[Path] | None = None) -> Report:
    """Report a problem or request something; optional attachments are PNG, JPEG or text files.

    Raises:
        HeinzelError: If it cannot be sent; the message says why.
    """
    try:
        return service.submit(text, attachment or [])
    except TrackerError as error:
        raise _fail(error) from None


@module.operation(render=_render_one)
def show(service: IssuesService, id: str) -> Report:  # noqa: A002 - the tracker's word for it
    """Show one report or request by its tracker id, with the tracker's details.

    Raises:
        HeinzelError: If it cannot be read.
    """
    try:
        return service.get(id)
    except TrackerError as error:
        raise _fail(error) from None


@module.job(schedule="*/5 * * * *", name="watch", timeout="2m")
def watch(service: IssuesService, kernel: Kernel) -> JsonValue:
    """Every five minutes, notice when a report is being worked on, is done, or is released."""
    notifications = kernel.resolve(Notifications) if kernel.provides(Notifications) else None
    try:
        return service.watch(notifications).model_dump(mode="json")
    except TrackerError as error:
        raise _fail(error) from None


@module.widget(source="list", order=650)
def today(result: Reports) -> ListWidget | None:
    """Your open reports and requests on Today; nothing while issue tracking is off or all is done."""
    if not result.ready:
        return None
    open_ = [report for report in result.reports if report.state != TaskState.DONE]
    if not open_:
        return None
    return ListWidget(
        title="Your reports and requests",
        items=[
            ListEntry(
                text=report.title,
                detail=report.status,
                tone="ok" if report.state == TaskState.WORKING else "neutral",
                effect=Navigate(path=ROUTE),
            )
            for report in open_[:8]
        ],
    )


@module.health
def tracking(service: IssuesService) -> list[Check]:
    """Off is fine; a chosen tracker must answer."""
    if not service.enabled:
        return [Check(name="tracker", status=Status.UP, detail="off; turn it on with hz setup issues")]
    result = service.overview()
    if not result.ready:
        return [Check(name="tracker", status=Status.DOWN, detail=str(result.problem), fix=SETUP)]
    detail = f"{service.settings.tracker}: {len(result.reports)} reports and requests"
    return [Check(name="tracker", status=Status.UP, detail=detail)]


@module.setup(required=False)
def setup(settings: IssuesSettings, prompter: Prompter, editor: ConfigEditor) -> None:
    """Choose where reports and requests go, and where releases are found."""
    choice = prompter.choice("Where should reports and requests go?", [NONE, "beads"], default=settings.tracker)
    if choice == NONE:
        editor.write("issues.tracker", NONE)
        prompter.say("Issue tracking is off.")
        return
    folder = settings.beads.path or Path.cwd()
    while True:
        answer = prompter.text("The folder with the .beads database", default=str(folder))
        folder = Path(answer).expanduser()
        if (folder / ".beads").is_dir():
            break
        prompter.say(f"{folder} has no .beads database; run bd init there first, or pick another folder.")
    clones = [str(source.path) for source in settings.releases]
    clone = prompter.text("A git clone whose tags are releases, empty to skip", default=clones[0] if clones else "")
    if not prompter.confirm(f"Send reports and requests to the Beads database in {folder}?"):
        prompter.say("Nothing was saved.")
        return
    editor.write("issues.beads", {**settings.beads.model_dump(mode="json"), "path": str(folder)})
    if clone:
        editor.write("issues.releases", [{"path": str(Path(clone).expanduser())}])
    path = editor.write("issues.tracker", "beads")
    prompter.say(f"Saved to {path}.")


__all__ = [
    "ENTRY_POINTS",
    "NOT_SET_UP",
    "STATE_LABELS",
    "Attachment",
    "BeadsSettings",
    "BeadsTracker",
    "IssuesService",
    "IssuesSettings",
    "Release",
    "ReleaseResolver",
    "ReleaseSource",
    "Report",
    "Reports",
    "Task",
    "TaskState",
    "TaskTracker",
    "TrackerError",
    "Watched",
    "module",
    "released_text",
    "state_of",
]
