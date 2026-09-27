[Guide](../README.md) · [简体中文](../zh-CN/app.md)

# Set up and use the App

## Install and open

Download the package for your operating system and architecture from [Releases](https://github.com/konbakuyomu/smartsearch/releases/latest). Windows installs for the current user. The App includes its own runtime; using the App does not require a separate Python, Node.js, or CLI installation.

Environment preparation and full App/CLI language switching are available from v0.1.21; the Update Skills page is available from v0.1.22. Windows self-signing and the new transparent icon are available from v0.1.23. Windows `-signed.exe` packages use a self-signed certificate that Windows does not trust by default, so SmartScreen may still appear. Check the official release source and [public certificate fingerprint](../../windows-signing.md), then decide whether to use the options allowed by your system. This does not permanently trust the certificate or require disabling security protection. Older `-unsigned-test.exe` packages remain unsigned, as does macOS (also unnotarized). Complete macOS/Windows ARM64 device use, clean-machine operation and the DPI matrix still require manual validation.

Open **Smart Search** from the Start menu or Applications. Existing configuration is reused. Overview shows whether you have providers for main search, documentation lookup, and page reading.

## Configure services

1. Open **Providers** and select a service for each missing capability. The page links to the provider's documentation and key registration page. See [Providers and configuration](configuration.md) for the choices.
2. Enter the address, API key and model that your provider supplies. Leave optional settings at their defaults unless your provider requires otherwise.
3. Test the draft if you want to check the connection, then preview and save the changes. Testing and searches can consume paid provider quota; simply opening the App does not run them.

Edits stay in a draft until saved. An empty key field keeps the saved key; select the explicit clear option to remove it. Fields overridden by environment variables show their effective source, and saving does not replace those environment values. Tasks already running keep their original configuration snapshot.

## Update Agent Skills

1. Open **Update Skills** and select **Check latest Skills**. The page downloads instruction files from the latest official stable npm package and shows the source version and check time. It does not run package code.
2. Review the Agents, target paths and changed filenames, then select your targets. Status describes the Smart Search Skill, not the Agent application's installation, version or successful invocation.
3. Select **Update selected Skills**, review the source and paths, then confirm. Changed content is backed up first; the result shows backup paths. Extra files, unselected targets and legacy copies are kept.
4. Reopen the Agent session; Gemini can use `/skills reload`. Ask the Agent to run `smart-search --version` first, then test a search when needed.

Daily automatic checks are enabled by default and can be turned off. They notify without writing Agent directories. Offline or integrity failures show an error and label cached data; check successfully again before updating. App and CLI upgrades do not automatically sync Skills.

Codex, Claude Code, Cursor, Copilot, Gemini, OpenCode, Cline, Roo Code and the other listed targets use the same Skill. Codex uses `~/.agents/skills/smart-search-cli`; other compatible Agents may read that shared directory too. Historical `.codex/skills` copies are kept. Claude respects an absolute `CLAUDE_CONFIG_DIR`. OpenCode uses `~/.config/opencode/skills` and reports old `.opencode/skills` copies. WSL, remote hosts and Cloud Agents need their own setup; local files are not automatically synced there.

## Prepare the shared independent CLI

Under **Update Skills → Shared independent CLI environment**, detect the environment, review the plan, install missing components and verify availability. Healthy Node.js, Python and independent Smart Search CLI installations are reused. Missing components go into user-writable directories separate from the App. The App does not install or sign into Agent applications, and does not require mise.

A Skills update refreshes the local independent CLI invocation path. Prepare or verify the CLI first; if it is older than the Skills source, update it in Settings before syncing Skills. Agents share this runtime, but loading the Skill and making real calls still require verification in the Agent. Configure missing provider keys rather than reinstalling the runtime.

Failed installation keeps completed components; detect again and retry the missing work. Wait for installation or Skills writes before quitting. Local checks and version verification do not make paid requests.

## Everyday pages

| Page | Use it to |
| --- | --- |
| Overview | Check missing capabilities and the next setup step |
| Providers | Edit, test, preview and save provider settings |
| Search & research | Search, read URLs, map sites, look up docs, plan offline research or run online research; copy/export results |
| Activity | See actual stages, providers, models and elapsed time; cancel tasks started by this App |
| Update Skills | Check stable Skills, back up and sync selected Agent targets; prepare the shared independent CLI |
| Settings & about | Choose the configuration directory, observe additional activity directories, set theme/language, reset health status and check updates |

Search results need source checking. A hit or snippet is a candidate source, not proof that its page was read. See [Search, research and evidence](research.md).

## Language

Use **Settings & about → Language** to select automatic, 简体中文 or English. Automatic uses Chinese for a Chinese system language and English otherwise. The choice is saved for this App. Switching retains unsaved provider drafts and running searches; protected installation or update writes must finish first.

The independent CLI saves its own preference. Changing the App does not change that preference, provider configuration, AI language, queries, answers or source pages. Third-party installation logs may remain in their original language.

For a manual check, switch to English, visit each page, then switch to Chinese and restart the App. Confirm that the choice persists, the draft remains intact, buttons wrap at the minimum window size and keyboard navigation works. Check an invalid local setting and its error as well; no paid request is needed for these checks.

## App and CLI independence

The App's private engine serves the App. An independently installed npm CLI runs separately and remains available after the App closes or is uninstalled. App upgrades do not replace that CLI; its update uses the original installation manager.

Both can share provider settings by selecting the same configuration directory. Windows defaults to `%LOCALAPPDATA%\smart-search`, with the legacy home directory supported. `SMART_SEARCH_CONFIG_DIR` or the App's directory selector can isolate configurations. Different inherited environment variables can still produce different effective settings.

The private engine's absolute path also works while the App is closed, but uninstalling the App removes that engine. Use the independent CLI for lasting AI integration. External activity requires CLI 0.1.19 or newer; older CLI versions still work but do not emit the new activity events.

## Activity, updates and removal

Activity refreshes every two seconds and observes only the current or explicitly added directories. By default it records metadata rather than queries, answers, headers or keys. Completed entries are retained for at most seven days / 1,000 entries by default. Clearing activity does not delete configuration, research evidence or exports. An expired heartbeat means the status is stale, not that the task succeeded.

Closing the window with a running App task offers continuing in the background, cancelling App tasks and exiting, or returning. Restore the background App from its tray/menu icon; launching it again restores the same window. Independent CLI tasks started by a terminal or AI are not cancelled by the App.

Use the update page or download a new installer from Releases. Finish protected writes and close the App before replacing its files. The Windows installer refuses to overwrite private resources while the App is still running. Uninstalling preserves shared configuration, independent CLI data, research evidence and exported results.

Build and protocol details: [desktop README](../../../desktop/README.md), [desktop protocol](../../../desktop/PROTOCOL.md). Problems: [Troubleshooting](troubleshooting.md).
