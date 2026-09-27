#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash desktop/scripts/build-macos.sh --architecture arm64|x86_64 [--python PATH] [--output-root PATH]

Builds a fresh unsigned test .app and DMG. The Python interpreter and host must
match the requested architecture because PyInstaller does not cross-compile.
EOF
}

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
architecture=""
python_command="${PYTHON:-python3}"
output_root="$repository_root/.desktop-artifacts"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --architecture)
      architecture="${2:-}"
      shift 2
      ;;
    --python)
      python_command="${2:-}"
      shift 2
      ;;
    --output-root)
      output_root="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$architecture" != "arm64" && "$architecture" != "x86_64" ]]; then
  echo "--architecture must be arm64 or x86_64" >&2
  exit 2
fi
if [[ "$output_root" != /* ]]; then
  output_root="$repository_root/$output_root"
fi
if [[ "$python_command" == */* ]]; then
  python_bin="$python_command"
else
  python_bin="$(command -v "$python_command")"
fi
if [[ ! -x "$python_bin" ]]; then
  echo "Python executable is not available: $python_command" >&2
  exit 1
fi
if ! command -v swift >/dev/null 2>&1 || ! command -v hdiutil >/dev/null 2>&1; then
  echo "Swift and hdiutil are required on macOS to build the desktop test package." >&2
  exit 1
fi

normalize_architecture() {
  case "$1" in
    arm64|aarch64) printf 'arm64' ;;
    x86_64|amd64) printf 'x86_64' ;;
    *) printf '%s' "$1" ;;
  esac
}

python_arch="$(normalize_architecture "$("$python_bin" -c 'import platform; print(platform.machine())')")"
host_arch="$(normalize_architecture "$(uname -m)")"
if [[ "$python_arch" != "$architecture" || "$host_arch" != "$architecture" ]]; then
  echo "Requested $architecture, but host=$host_arch and Python=$python_arch. Build on a matching architecture runner or Mac." >&2
  exit 1
fi

mkdir -p "$output_root"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
run_directory="$output_root/macos-$architecture-$stamp-$$-$RANDOM"
if [[ -e "$run_directory" ]]; then
  echo "Refusing to reuse build directory: $run_directory" >&2
  exit 1
fi
mkdir "$run_directory"

backend_manifest="$run_directory/backend.json"
"$python_bin" "$repository_root/desktop/scripts/build_backend.py" \
  --output-root "$run_directory" \
  --result-file "$backend_manifest" \
  --smoke
backend_directory="$("$python_bin" -c 'import json, sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["bundle_directory"])' "$backend_manifest")"

macos_directory="$repository_root/desktop/macos"
if [[ ! -f "$macos_directory/Package.swift" ]]; then
  echo "SwiftPM package is not available: $macos_directory/Package.swift" >&2
  exit 1
fi
scratch_directory="$run_directory/swift-build"
if swift build --package-path "$macos_directory" --configuration release --product SmartSearchDesktop --arch "$architecture" --scratch-path "$scratch_directory"; then
  bin_directory="$(swift build --package-path "$macos_directory" --configuration release --arch "$architecture" --scratch-path "$scratch_directory" --show-bin-path)"
  desktop_binary="$bin_directory/SmartSearchDesktop"
else
  if swift package dump-package --package-path "$macos_directory" >/dev/null 2>&1; then
    echo "SwiftPM source build failed after a valid manifest; refusing the direct swiftc fallback." >&2
    exit 1
  fi
  echo "SwiftPM manifest is unavailable; falling back to direct swiftc compilation." >&2
  desktop_binary="$run_directory/SmartSearchDesktop"
  swiftc -O -target "${architecture}-apple-macosx13.0" \
    -o "$desktop_binary" \
    "$macos_directory/Sources/SmartSearchDesktop"/*.swift
fi
if [[ ! -f "$desktop_binary" ]]; then
  echo "SwiftPM did not create the expected desktop executable: $desktop_binary" >&2
  exit 1
fi

version="$("$python_bin" - "$repository_root/pyproject.toml" <<'PY'
import re
import sys
from pathlib import Path

match = re.search(r'^\s*version\s*=\s*"([^"]+)"', Path(sys.argv[1]).read_text(encoding="utf-8"), re.MULTILINE)
if not match:
    raise SystemExit("project version is missing from pyproject.toml")
print(match.group(1))
PY
)"
app_directory="$run_directory/Smart Search.app"
mkdir -p "$app_directory/Contents/MacOS" "$app_directory/Contents/Resources"
cp "$desktop_binary" "$app_directory/Contents/MacOS/SmartSearchDesktop"
cp "$repository_root/desktop/packaging/macos/Info.plist" "$app_directory/Contents/Info.plist"
cp "$repository_root/desktop/packaging/macos/SmartSearch.icns" "$app_directory/Contents/Resources/SmartSearch.icns"
cp "$repository_root/src/smart_search/assets/i18n/messages.json" "$app_directory/Contents/Resources/Localization.json"
cmp "$repository_root/src/smart_search/assets/i18n/messages.json" "$app_directory/Contents/Resources/Localization.json"
plutil -replace CFBundleShortVersionString -string "$version" "$app_directory/Contents/Info.plist"
plutil -replace CFBundleVersion -string "$version" "$app_directory/Contents/Info.plist"
cp -R "$backend_directory" "$app_directory/Contents/Resources/backend"
chmod +x "$app_directory/Contents/MacOS/SmartSearchDesktop" "$app_directory/Contents/Resources/backend/smart-search"
plutil -lint "$app_directory/Contents/Info.plist"
if [[ ! -x "$app_directory/Contents/Resources/backend/smart-search" ]]; then
  echo "The app bundle is missing an executable backend." >&2
  exit 1
fi

dmg="$run_directory/SmartSearch-$version-macos-$architecture-unsigned-test.dmg"
hdiutil create -volname "Smart Search" -srcfolder "$app_directory" -format UDZO "$dmg"
echo "macOS unsigned, unnotarized test artifact: $dmg"
