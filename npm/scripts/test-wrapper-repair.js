const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const wrapperPath = path.resolve(__dirname, "..", "bin", "smart-search.js");
const wrapperSource = fs.readFileSync(wrapperPath, "utf8");

const { getLanguage, localize } = require("../i18n");
const languageRoot = fs.mkdtempSync(path.join(require("node:os").tmpdir(), "smart-search-language-"));
const languageConfig = path.join(languageRoot, "config.json");
fs.writeFileSync(languageConfig, JSON.stringify({ SMART_SEARCH_LANGUAGE: "zh", XAI_API_KEY: "test-only" }));
const languageEnv = { SMART_SEARCH_CONFIG_DIR: languageRoot };
assert.strictEqual(getLanguage([], languageEnv), "zh");
assert.strictEqual(getLanguage([], { ...languageEnv, SMART_SEARCH_LANGUAGE: "en" }), "en");
assert.strictEqual(getLanguage(["search", "q", "--lang=zh-CN"], { ...languageEnv, SMART_SEARCH_LANGUAGE: "en" }), "zh");
assert.strictEqual(getLanguage(["--lang", "en", "--", "--lang=zh"], languageEnv), "en");
assert.strictEqual(getLanguage([], { ...languageEnv, SMART_SEARCH_LANGUAGE: "auto", LANG: "de_DE.UTF-8" }), "en");
assert.strictEqual(getLanguage([], { ...languageEnv, SMART_SEARCH_LANGUAGE: "auto", LC_ALL: "zh_TW.UTF-8" }), "zh");
assert.strictEqual(localize(["--lang=zh"], languageEnv).t("Failed to start smart-search: {0}", "upstream {0}"), "无法启动 smart-search：upstream {0}");
assert.deepStrictEqual(JSON.parse(fs.readFileSync(languageConfig)), { SMART_SEARCH_LANGUAGE: "zh", XAI_API_KEY: "test-only" });
fs.unlinkSync(languageConfig);

function runWrapper({ runtimeExists, repairStatus = 0, repairCreatesRuntime = true, language = "en" }) {
  let repairedRuntimeExists = runtimeExists;
  const spawnSyncCalls = [];
  const spawnCalls = [];
  const exits = [];
  const stderr = [];

  const fakeFs = {
    existsSync(filePath) {
      const normalized = filePath.replaceAll("\\", "/");
      if (
        normalized.endsWith("/.smart-search-python/Scripts/python.exe") ||
        normalized.endsWith("/.smart-search-python/bin/python")
      ) {
        return repairedRuntimeExists;
      }
      return fs.existsSync(filePath);
    }
  };

  const fakeProcess = {
    ...process,
    argv: ["node", wrapperPath, "--version", "--lang", language],
    env: { SMART_SEARCH_LANGUAGE: "en" },
    cwd: () => "C:\\caller",
    exit(code) {
      exits.push(code);
      throw new Error(`process.exit(${code})`);
    },
    kill() {}
  };

  const fakeChildProcess = {
    spawnSync(command, args, options) {
      spawnSyncCalls.push({ command, args, options });
      if (repairStatus instanceof Error) {
        return { error: repairStatus };
      }
      if (repairCreatesRuntime) {
        repairedRuntimeExists = true;
      }
      return { status: repairStatus };
    },
    spawn(command, args, options) {
      spawnCalls.push({ command, args, options });
      return {
        on() {
          return this;
        }
      };
    }
  };

  const context = {
    __dirname: path.dirname(wrapperPath),
    console: { error(message = "") { stderr.push(String(message)); }, log() {} },
    process: fakeProcess,
    require(moduleName) {
      if (moduleName === "node:child_process") {
        return fakeChildProcess;
      }
      if (moduleName === "node:fs") {
        return fakeFs;
      }
      if (moduleName === "node:path") {
        return path;
      }
      return require(moduleName);
    }
  };

  try {
    vm.runInNewContext(wrapperSource, context, { filename: wrapperPath });
  } catch (error) {
    if (!String(error.message).startsWith("process.exit(")) {
      throw error;
    }
  }

  return { spawnSyncCalls, spawnCalls, exits, stderr };
}

const healthy = runWrapper({ runtimeExists: true });
assert.strictEqual(healthy.spawnSyncCalls.length, 0);
assert.strictEqual(healthy.spawnCalls.length, 1);

const repaired = runWrapper({ runtimeExists: false });
assert.strictEqual(repaired.spawnSyncCalls.length, 1);
assert(
  repaired.spawnSyncCalls[0].args[0].replaceAll("\\", "/").endsWith("/npm/scripts/postinstall.js"),
  "missing runtime should invoke package postinstall repair"
);
assert.strictEqual(repaired.spawnCalls.length, 1);
assert.deepStrictEqual(Array.from(repaired.spawnCalls[0].args.slice(0, 2)), ["-m", "smart_search.cli"]);
assert.strictEqual(repaired.exits.length, 0);
assert.deepStrictEqual(Array.from(repaired.spawnSyncCalls[0].options.stdio), ["inherit", 2, 2]);
const chineseRepair = runWrapper({ runtimeExists: false, language: "zh" });
assert(chineseRepair.stderr.some(message => message.includes("缺少 Python 运行环境")));
assert.strictEqual(chineseRepair.spawnSyncCalls[0].options.env.SMART_SEARCH_LANGUAGE, "zh");

const failedRepair = runWrapper({
  runtimeExists: false,
  repairStatus: 1,
  repairCreatesRuntime: false
});
assert.strictEqual(failedRepair.spawnSyncCalls.length, 1);
assert.strictEqual(failedRepair.spawnCalls.length, 0);
assert.deepStrictEqual(failedRepair.exits, [1]);
assert(
  failedRepair.stderr.includes("  npm install -g @konbakuyomu/smart-search"),
  "failed repair should recommend reinstalling the stable package"
);
assert(
  !failedRepair.stderr.some((message) => message.includes("@next")),
  "failed repair should not recommend the next release tag"
);

const repairSpawnError = runWrapper({
  runtimeExists: false,
  repairStatus: new Error("postinstall unavailable"),
  repairCreatesRuntime: false
});
assert.strictEqual(repairSpawnError.spawnSyncCalls.length, 1);
assert.strictEqual(repairSpawnError.spawnCalls.length, 0);
assert.deepStrictEqual(repairSpawnError.exits, [5]);
assert(
  repairSpawnError.stderr.includes("  npm install -g @konbakuyomu/smart-search"),
  "repair spawn errors should recommend reinstalling the stable package"
);
assert(
  !repairSpawnError.stderr.some((message) => message.includes("@next")),
  "repair spawn errors should not recommend the next release tag"
);

// App-selected Python must win over a global py launcher, and a bad explicit
// selection must fail instead of silently installing against another runtime.
const postinstallPath = path.resolve(__dirname, "postinstall.js");
const postinstallSource = fs.readFileSync(postinstallPath, "utf8");
for (const valid of [true, false]) {
  const selected = path.resolve("independent tools", "python.exe");
  const calls = [];
  const exits = [];
  const context = {
    __dirname,
    console: { log() {}, error() {} },
    process: { platform: process.platform, env: { SMART_SEARCH_PYTHON: selected }, exit(code) { exits.push(code); throw new Error("exit"); } },
    require(name) {
      if (name === "node:child_process") return { spawnSync(command, args) {
        calls.push({ command, args });
        return { status: valid ? 0 : 1, stdout: "" };
      } };
      if (name === "node:fs") return { existsSync: () => false };
      return require(name);
    }
  };
  try { vm.runInNewContext(postinstallSource, context, { filename: postinstallPath }); }
  catch (error) { if (error.message !== "exit") throw error; }
  assert.strictEqual(calls[0].command, selected);
  if (valid) {
    assert.strictEqual(calls[1].command, selected);
    assert.strictEqual(calls[1].args[1], "venv");
    assert.strictEqual(calls[2].args[1], "pip");
    assert.deepStrictEqual(exits, []);
  } else {
    assert.strictEqual(calls.length, 1);
    assert.deepStrictEqual(exits, [1]);
  }
}
