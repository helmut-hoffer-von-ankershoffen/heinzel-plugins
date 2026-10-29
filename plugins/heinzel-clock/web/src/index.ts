import type { PluginSDK } from "./sdk";
import { WorldClock } from "./ClockPanel";
import "./style.css";
export default function createView(sdk: PluginSDK) {
  if (sdk.abi !== 1) throw new Error("World Clock requires Heinzel plugin SDK 1");
  return WorldClock;
}
