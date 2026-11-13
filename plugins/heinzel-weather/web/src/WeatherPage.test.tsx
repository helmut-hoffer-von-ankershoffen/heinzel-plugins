import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { expect, it, vi } from "vitest";
import { needsLocation, ready, unavailable } from "./fixture";
import { WeatherPage } from "./WeatherPage";

vi.mock("./sdk", () => ({
  Button: ({ children, variant: _variant, size: _size, ...props }: any) => <button {...props}>{children}</button>,
  SettingsShortcut: ({ label }: { label: string }) => <a href="/?settings=weather" aria-label={label}>Settings</a>,
}));
const props = { loading: false, visible: true, compact: false, flowing: false, onClose: vi.fn() };
const show = (data: unknown) => render(<WeatherPage {...props} data={data} />);

it("shows the conditions, 24 hours and 7 days for the place, with settings one button away", async () => {
  const { container } = show(ready);
  expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Weather in Berlin, DE");
  expect(screen.getAllByText("2°", { exact: false })[0]).toHaveTextContent("2°°C");
  expect(screen.getByText("Feels like 0° · High 4° · Low -1°")).toBeInTheDocument();
  expect(screen.getByText("12 km/h")).toBeInTheDocument();
  expect(screen.getByText("87%")).toBeInTheDocument();
  const hourly = screen.getByRole("heading", { name: "Next 24 hours" }).parentElement!;
  expect(within(hourly).getAllByRole("listitem")).toHaveLength(24);
  const daily = screen.getByRole("heading", { name: "Next 7 days" }).parentElement!;
  expect(within(daily).getAllByRole("listitem")).toHaveLength(7);
  expect(within(daily).getByText("Tomorrow")).toBeInTheDocument();
  expect(screen.getByText(/Updated \d\d:\d\d/)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Change location" })).toHaveAttribute("href", "/?settings=weather");
  await userEvent.click(screen.getByRole("button", { name: "Close Weather" }));
  expect(props.onClose).toHaveBeenCalled();
  expect((await axe.run(container)).violations).toEqual([]);
});
it("is a main-area page: one h1, section h2s, no close button, and the credit stays behind its info button", async () => {
  const { container } = render(<WeatherPage {...props} flowing data={ready} />);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Weather in Berlin, DE");
  expect(screen.getByRole("heading", { level: 2, name: "Next 24 hours" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { level: 2, name: "Next 7 days" })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Close Weather" })).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Data source" }));
  expect(screen.getByRole("status")).toHaveTextContent("Open-Meteo.com (CC BY 4.0)");
  expect((await axe.run(container)).violations).toEqual([]);
});
it("says when the report is the last one", () => {
  show({ ...ready, stale: true });
  expect(screen.getByRole("status")).toHaveTextContent(/last report from \d\d:\d\d; the refresh failed/);
});
it("lists alerts as text, not colour alone", () => {
  const report = { ...ready.report!, alerts: [{ event: "Storm warning", sender: "DWD", start: "2026-11-07T10:00:00+01:00", end: "2026-11-07T20:00:00+01:00", description: "" }] };
  show({ ...ready, report });
  expect(screen.getByRole("list", { name: "Weather alerts" })).toHaveTextContent("Storm warning · until 20:00 · DWD");
});
it("asks for a location with one button that opens Settings", async () => {
  const push = vi.spyOn(window.history, "pushState");
  const { container } = show(needsLocation);
  expect(screen.getByRole("heading", { name: "Set up your location" })).toBeInTheDocument();
  expect(screen.getAllByRole("button").filter((b) => b.textContent === "Choose location")).toHaveLength(1);
  await userEvent.click(screen.getByRole("button", { name: "Choose location" }));
  expect(push).toHaveBeenCalledWith({}, "", "/?settings=weather");
  expect((await axe.run(container)).violations).toEqual([]);
});
it("explains an unavailable weather in words", () => {
  show(unavailable);
  expect(screen.getByRole("heading", { name: "The weather is not available" })).toBeInTheDocument();
  expect(screen.getByText("Open-Meteo can't be reached.")).toBeInTheDocument();
});
it("shows loading while there is no answer yet", () => {
  render(<WeatherPage {...props} data={undefined} loading />);
  expect(screen.getByRole("status")).toHaveTextContent("Loading the weather…");
});
it("credits the data once, behind an info button with the link, and not as standing text", async () => {
  show(ready);
  expect(screen.queryByText(/Open-Meteo/)).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Data source" }));
  expect(screen.getByRole("status")).toHaveTextContent("Open-Meteo.com (CC BY 4.0)");
  expect(screen.getByRole("link", { name: "Open the data provider's page" })).toHaveAttribute("href", "https://open-meteo.com/");
});
