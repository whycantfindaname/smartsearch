# Smart Search icon

`source.png` is the owner's original transparent artwork, supplied on 2026-09-20.
The magnifying glass and cyan command prompt are kept unchanged. Generated assets
remove transparent outer margins (ignoring near-transparent export noise) and fit
the artwork within 88% of a square, retaining its antialiased edges.

Regenerate on Windows with PowerShell 7 and the .NET drawing library:

```powershell
./desktop/scripts/Build-Icons.ps1
```

This updates the project PNG, Windows PNG/ICO, macOS ICNS and inline Web UI icons.
The original source is never overwritten. Packaged builds consume the committed
assets and do not require the conversion script or the original download path.
