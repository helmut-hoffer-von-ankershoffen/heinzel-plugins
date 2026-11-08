import type { ButtonHTMLAttributes, ComponentType, ReactNode } from "react";
export type ViewProps = { data: unknown; loading: boolean; visible: boolean; onClose: () => void; flowing: boolean; compact: boolean };
export type PluginSDK = {
  abi: number;
  Button: ComponentType<ButtonHTMLAttributes<HTMLButtonElement> & { variant?: string; size?: string }>;
  SettingsShortcut: ComponentType<{ section: string; label: string; onClick?: () => void; className?: string }>;
  // Hosts before the pane-action row do not provide these two.
  PaneActions?: ComponentType<{ children?: ReactNode }>;
  PaneAction?: ComponentType<{ icon: ComponentType<{ "aria-hidden"?: boolean }>; to?: string; href?: string; onClick?: () => void; children: ReactNode }>;
};
const sdk = Reflect.get(globalThis, Symbol.for("heinzel.plugin-sdk.1")) as PluginSDK;
export const Button = sdk.Button;
export const PaneActions = sdk.PaneActions;
export const PaneAction = sdk.PaneAction;
export const SettingsShortcut = sdk.SettingsShortcut;
