import type { ButtonHTMLAttributes, ComponentType } from "react";
export type ViewProps = { data: unknown; loading: boolean; visible: boolean; onClose: () => void; flowing: boolean; compact: boolean };
export type PluginSDK = {
  abi: number;
  Button: ComponentType<ButtonHTMLAttributes<HTMLButtonElement> & { variant?: string; size?: string }>;
  SettingsShortcut: ComponentType<{ section: string; label: string; onClick?: () => void; className?: string }>;
};
const sdk = Reflect.get(globalThis, Symbol.for("heinzel.plugin-sdk.1")) as PluginSDK;
export const Button = sdk.Button;
export const SettingsShortcut = sdk.SettingsShortcut;
