import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { afterEach, expect, it, vi } from "vitest";
import { WorldClock } from "./ClockPanel";

const {create, destroy, update} = vi.hoisted(() => ({create: vi.fn(), destroy: vi.fn(), update: vi.fn()}));
vi.mock("cobe", () => ({default: create}));
vi.mock("./sdk", () => ({
  Button: ({children, variant: _variant, size: _size, ...props}: any) => <button {...props}>{children}</button>,
  SettingsShortcut: ({label}: {label: string}) => <a href="/?settings=clock" aria-label={label}>Settings</a>,
}));
const zones = ["Europe/Berlin", "America/New_York", "UTC"].map(zone => ({zone, hours: [9,18], working: false, primary: zone === "Europe/Berlin", time: ""}));
const props = {data: zones, loading: false, visible: true, compact: false, flowing: false, onClose: vi.fn()};
function show() { return render(<WorldClock {...props} />); }
afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); });

it("keeps zone order, primary designation, 24-hour times and accessible static fallback", async () => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  const {container} = show();
  const list = screen.getByRole("list");
  expect(within(list).getByText("Primary")).toBeInTheDocument();
  expect(within(list).getAllByRole("listitem").map(row => row.textContent)).toEqual([
    expect.stringContaining("Berlin"), expect.stringContaining("New York"), expect.stringContaining("UTC"),
  ]);
  for (const time of container.querySelectorAll("time")) expect(time.textContent).toMatch(/^\d{2}:\d{2}:\d{2}$/);
  expect(screen.getByText(/Static map/)).toBeInTheDocument();
  expect((await axe.run(container)).violations).toEqual([]);
});
it("keeps unknown browser zones in place", () => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  render(<WorldClock {...props} data={[{...zones[0], zone: "Future/New_Zone"}, zones[1]]} />);
  expect(screen.getByText("New Zone")).toBeInTheDocument();
  expect(screen.getByText("Time unavailable in this browser")).toBeInTheDocument();
  expect(within(screen.getByText("New York").closest("li")!).queryByText("Primary")).not.toBeInTheDocument();
});
it("does not create WebGL under reduced motion", () => {
  const media = window.matchMedia("(prefers-reduced-motion: reduce)");
  vi.spyOn(window, "matchMedia").mockReturnValue({...media, matches: true});
  create.mockClear(); show();
  expect(create).not.toHaveBeenCalled();
  expect(screen.queryByRole("button", {name: "Rotate globe left"})).not.toBeInTheDocument();
});
it("updates rather than recreating the globe when rotated and destroys it on close", async () => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as WebGLRenderingContext);
  create.mockReturnValue({destroy, update});
  const {unmount} = show(); const count = create.mock.calls.length;
  await userEvent.click(screen.getByRole("button", {name: "Rotate globe right"}));
  expect(create).toHaveBeenCalledTimes(count);
  expect(update).toHaveBeenCalledWith(expect.objectContaining({phi: expect.any(Number)}));
  unmount(); expect(destroy).toHaveBeenCalled();
});
it("releases WebGL and stops refresh work when its retained panel becomes hidden", () => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as WebGLRenderingContext);
  create.mockReturnValue({destroy, update}); destroy.mockClear();
  const {rerender} = show();
  rerender(<WorldClock {...props} visible={false} />);
  expect(destroy).toHaveBeenCalled();
});
it("exposes projected markers to keyboard and pointer input", async () => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as WebGLRenderingContext);
  create.mockReturnValue({destroy, update}); show();
  const marker = screen.getByRole("button", {name:"Berlin"});
  await userEvent.hover(marker);
  expect(screen.getByRole("tooltip")).toHaveTextContent(/^Berlin$/);
  marker.focus(); expect(marker).toHaveAttribute("aria-describedby", expect.stringContaining("world-clock-marker"));
});
it("falls back if a WebGL context is lost", () => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as WebGLRenderingContext);
  create.mockReturnValue({destroy, update}); const {container} = show();
  fireEvent(container.querySelector("canvas")!, new Event("webglcontextlost"));
  expect(screen.getByText(/Static map/)).toBeInTheDocument();
});
it("repaints an asynchronously decoded map on the clock tick", async () => {
  vi.useFakeTimers({toFake:["setInterval","clearInterval"]});
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as WebGLRenderingContext);
  create.mockReturnValue({destroy, update}); show(); update.mockClear();
  await act(() => vi.advanceTimersByTimeAsync(1000));
  expect(update).toHaveBeenCalledWith({phi: expect.any(Number)});
});
it("closes through the declared host lifecycle callback", async () => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  props.onClose.mockClear(); show();
  await userEvent.click(screen.getByRole("button", {name:"Close World clock"}));
  expect(props.onClose).toHaveBeenCalledOnce();
});

it("paints visible markers above night shading with a contrasting outline", () => {
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({} as WebGLRenderingContext);
  create.mockReturnValue({destroy, update});
  const {container} = show();
  const marker = container.querySelector('[data-zone-marker="Europe/Berlin"]');
  expect(marker).toHaveAttribute("fill", "#ff9a3c");
  expect(marker).toHaveAttribute("stroke", "#ffffff");
  expect(marker?.closest("svg")?.previousElementSibling?.querySelector("path[clip-path]")).toBeInTheDocument();
});

it("shows the workday subline below each city in the sidebar panel", () => {
  vi.useFakeTimers({toFake:["Date"]});
  vi.setSystemTime(new Date("2026-10-26T06:00:00Z"));
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  show();
  const row = screen.getByText("Berlin").closest("li")!;
  expect(within(row).getByText(/^Starts in 2h/)).toBeVisible();
});
