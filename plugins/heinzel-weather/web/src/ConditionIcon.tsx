import { Cloud, CloudDrizzle, CloudFog, CloudLightning, CloudRain, CloudSnow, Moon, Sun, Thermometer, Wind } from "lucide-react";
import type { ComponentType } from "react";
import type { Condition } from "./model";

type Glyph = ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
const day: Record<Condition, Glyph> = {
  clear: Sun, clouds: Cloud, rain: CloudRain, drizzle: CloudDrizzle, thunder: CloudLightning,
  snow: CloudSnow, fog: CloudFog, wind: Wind, heat: Thermometer, cold: Thermometer,
};

/** The sky as one line icon. The words always sit beside it, so the icon is never the only signal. */
export function ConditionIcon({ condition, night = false, className }: { condition: Condition; night?: boolean; className?: string }) {
  const Icon = night && condition === "clear" ? Moon : day[condition];
  return <Icon aria-hidden className={className} />;
}
