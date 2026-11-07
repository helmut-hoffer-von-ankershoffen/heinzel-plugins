import type { PluginSDK } from "./sdk";
import { WeatherPage } from "./WeatherPage";
import "./style.css";
export default function createView(sdk: PluginSDK) {
  if (sdk.abi !== 1) throw new Error("Weather requires Heinzel plugin SDK 1");
  return WeatherPage;
}
