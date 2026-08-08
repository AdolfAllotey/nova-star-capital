import uiConfig from "../config/ui_version.json";

export function getUiVersion() {
  return uiConfig?.ui_version || "N/A";
}

export function getUiLabel() {
  return `UI v${getUiVersion()}`;
}
