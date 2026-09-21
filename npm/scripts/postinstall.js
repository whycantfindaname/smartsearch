const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const { t } = require("../i18n").localize([], process.env);

const packageRoot = path.resolve(__dirname, "..", "..");
const venvDir = path.join(packageRoot, ".smart-search-python");

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: packageRoot,
    stdio: options.stdio || "inherit",
    encoding: "utf8",
    windowsHide: true
  });

  if (result.error) {
    return { ok: false, error: result.error };
  }
  return { ok: result.status === 0, status: result.status, stdout: result.stdout || "" };
}

function pythonCandidates() {
  if (process.env.SMART_SEARCH_PYTHON) {
    // The App can select an independent interpreter without changing global Python.
    return [{ command: process.env.SMART_SEARCH_PYTHON, args: [] }];
  }
  if (process.platform === "win32") {
    return [
      { command: "py", args: ["-3"] },
      { command: "python", args: [] },
      { command: "python3", args: [] }
    ];
  }
  return [
    { command: "python3", args: [] },
    { command: "python", args: [] }
  ];
}

function findPython() {
  const probe = [
    "-c",
    "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
  ];

  for (const candidate of pythonCandidates()) {
    const result = run(candidate.command, [...candidate.args, ...probe], { stdio: "pipe" });
    if (result.ok) {
      return candidate;
    }
  }
  return null;
}

function venvPython() {
  return process.platform === "win32"
    ? path.join(venvDir, "Scripts", "python.exe")
    : path.join(venvDir, "bin", "python");
}

const python = findPython();
if (!python) {
  console.error(t("smart-search requires Python 3.10 or newer."));
  console.error(t("Install Python, then run: npm install -g @konbakuyomu/smart-search@latest"));
  process.exit(1);
}

if (!fs.existsSync(venvPython())) {
  console.log(t("Creating smart-search Python runtime..."));
  const created = run(python.command, [...python.args, "-m", "venv", venvDir]);
  if (!created.ok) {
    console.error(t("Failed to create the smart-search Python virtual environment."));
    process.exit(created.status || 1);
  }
}

const py = venvPython();

console.log(t("Installing smart-search Python package..."));
const install = run(py, [
  "-m",
  "pip",
  "install",
  "--disable-pip-version-check",
  packageRoot
]);

if (!install.ok) {
  console.error(t("Failed to install the bundled smart-search Python package."));
  process.exit(install.status || 1);
}
