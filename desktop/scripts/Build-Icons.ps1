[CmdletBinding()]
param()

# Deterministic format conversion only: preserve the supplied artwork and colours.
$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$branding = Join-Path $repositoryRoot 'assets/branding'
$windowsAssets = Join-Path $repositoryRoot 'desktop/windows/Assets'
New-Item -ItemType Directory -Path $windowsAssets -Force | Out-Null
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing.Common,System.Drawing.Primitives -TypeDefinition @'
using System.Drawing;
public static class IconBounds {
    public static Rectangle Alpha(Bitmap image) {
        int left=image.Width, top=image.Height, right=-1, bottom=-1;
        for (int y=0;y<image.Height;y++) for (int x=0;x<image.Width;x++) {
            // Ignore near-transparent export noise when finding the outer margin.
            if (image.GetPixel(x,y).A < 16) continue;
            left=System.Math.Min(left,x); top=System.Math.Min(top,y);
            right=System.Math.Max(right,x); bottom=System.Math.Max(bottom,y);
        }
        if (right < 0) throw new System.ArgumentException("The source icon is empty.");
        return Rectangle.FromLTRB(System.Math.Max(0,left-2),System.Math.Max(0,top-2),
            System.Math.Min(image.Width,right+3),System.Math.Min(image.Height,bottom+3));
    }
}
'@
$source = [System.Drawing.Bitmap]::new((Join-Path $branding 'source.png'))
$bounds = [IconBounds]::Alpha($source)

function Get-IconPng([int]$Size) {
    $bitmap = [System.Drawing.Bitmap]::new($Size, $Size)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $stream = [IO.MemoryStream]::new()
    try {
        $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $scale = $Size * 0.88 / [Math]::Max($bounds.Width, $bounds.Height)
        $width = [int][Math]::Round($bounds.Width * $scale)
        $height = [int][Math]::Round($bounds.Height * $scale)
        $target = [System.Drawing.Rectangle]::new([int](($Size-$width)/2), [int](($Size-$height)/2), $width, $height)
        $graphics.DrawImage($source, $target, $bounds, [System.Drawing.GraphicsUnit]::Pixel)
        $bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png)
        return ,$stream.ToArray()
    } finally { $stream.Dispose(); $graphics.Dispose(); $bitmap.Dispose() }
}

try {
    [IO.File]::WriteAllBytes((Join-Path $branding 'smart-search.png'), (Get-IconPng 1024))
    Copy-Item -LiteralPath (Join-Path $branding 'smart-search.png') -Destination (Join-Path $windowsAssets 'smart-search.png')
    $sizes = @(16,20,24,32,40,48,64,128,256)
    $frames = @($sizes | ForEach-Object { ,(Get-IconPng $_) })
    $stream = [IO.MemoryStream]::new()
    $writer = [IO.BinaryWriter]::new($stream)
    $writer.Write([uint16]0); $writer.Write([uint16]1); $writer.Write([uint16]$sizes.Count)
    $offset = 6 + 16 * $sizes.Count
    for ($i=0; $i -lt $sizes.Count; $i++) {
        $dimension = if ($sizes[$i] -eq 256) { 0 } else { $sizes[$i] }
        $writer.Write([byte]$dimension); $writer.Write([byte]$dimension)
        $writer.Write([uint16]0); $writer.Write([uint16]1); $writer.Write([uint16]32)
        $writer.Write([uint32]$frames[$i].Length); $writer.Write([uint32]$offset)
        $offset += $frames[$i].Length
    }
    foreach ($frame in $frames) { $writer.Write([byte[]]$frame) }
    [IO.File]::WriteAllBytes((Join-Path $windowsAssets 'smart-search.ico'), $stream.ToArray())
    $writer.Dispose(); $stream.Dispose()

    $chunks = [IO.MemoryStream]::new()
    foreach ($entry in @(@('ic07',128),@('ic08',256),@('ic09',512),@('ic10',1024))) {
        $png = Get-IconPng $entry[1]
        $chunks.Write([Text.Encoding]::ASCII.GetBytes($entry[0]))
        $length = [BitConverter]::GetBytes([uint32]($png.Length + 8)); [Array]::Reverse($length)
        $chunks.Write($length); $chunks.Write($png)
    }
    $stream = [IO.MemoryStream]::new()
    $stream.Write([Text.Encoding]::ASCII.GetBytes('icns'))
    $length = [BitConverter]::GetBytes([uint32]($chunks.Length + 8)); [Array]::Reverse($length)
    $stream.Write($length); $stream.Write($chunks.ToArray())
    [IO.File]::WriteAllBytes((Join-Path $repositoryRoot 'desktop/packaging/macos/SmartSearch.icns'), $stream.ToArray())
    $stream.Dispose(); $chunks.Dispose()

    $dataUri = 'data:image/png;base64,' + [Convert]::ToBase64String((Get-IconPng 64))
    $pagePath = Join-Path $repositoryRoot 'src/smart_search/assets/ui/index.html'
    $page = [IO.File]::ReadAllText($pagePath)
    $page = [regex]::Replace($page, '(data-smart-search-icon (?:src|href)=")[^"]*(")', '${1}' + $dataUri + '${2}')
    [IO.File]::WriteAllText($pagePath, $page, [Text.UTF8Encoding]::new($false))
    Write-Output 'Generated PNG, nine-size Windows ICO, four-size macOS ICNS and embedded Web icons.'
} finally { $source.Dispose() }
