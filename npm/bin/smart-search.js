#!/usr/bin/env node

const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const { localize } = require("../i18n");
const { language, t } = localize(process.argv.slice(2), process.env);

const packageRoot = path.resolve(__dirname, "..", "..");
const callerCwd = process.env.INIT_CWD || process.cwd();
const venvDir = path.join(packageRoot, ".smart-search-python");
const pythonPath =
  process.platform === "win32"
    ? path.join(venvDir, "Scripts", "python.exe")
    : path.join(venvDir, "bin", "python");

function printReinstallHint() {
  console.error(t("Repair it by reinstalling the package:"));
  console.error("  npm install -g @konbakuyomu/smart-search");
}

if (!fs.existsSync(pythonPath)) {
  const postinstall = path.join(packageRoot, "npm", "scripts", "postinstall.js");
  console.error(t("smart-search Python runtime is missing; attempting repair..."));
  const repaired = spawnSync(process.execPath, [postinstall], {
    cwd: packageRoot,
    stdio: ["inherit", 2, 2],
    env: { ...process.env, SMART_SEARCH_LANGUAGE: language },
    windowsHide: true
  });
  if (repaired.error) {
    console.error(t("smart-search runtime repair failed: {0}", repaired.error.message));
    printReinstallHint();
    process.exit(5);
  }
  if (repaired.status !== 0 || !fs.existsSync(pythonPath)) {
    console.error(t("smart-search npm wrapper could not find its Python runtime."));
    console.error(t("Expected: {0}", pythonPath));
    printReinstallHint();
    process.exit(repaired.status || 5);
  }
}

const child = spawn(
  pythonPath,
  ["-m", "smart_search.cli", ...process.argv.slice(2)],
  {
    cwd: callerCwd,
    stdio: "inherit",
    env: {
      ...process.env,
      SMART_SEARCH_PACKAGE_ROOT: packageRoot,
      SMART_SEARCH_NODE_PATH: process.execPath,
      PYTHONIOENCODING: process.env.PYTHONIOENCODING || "utf-8",
      PYTHONUTF8: process.env.PYTHONUTF8 || "1"
    },
    windowsHide: true
  }
);

child.on("error", (error) => {
  console.error(t("Failed to start smart-search: {0}", error.message));
  process.exit(5);
});

child.on("close", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 5);
});
