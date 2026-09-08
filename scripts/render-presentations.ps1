param([string]$OutputDirectory = (Join-Path ([IO.Path]::GetTempPath()) 'foundry-slide-review'))
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$files = @('deliverables/air-canada-foundry-hosted-agents-decision.pptx', 'docs/assets/decks/foundry-hosted-agents-workshop-en.pptx', 'docs/assets/decks/foundry-hosted-agents-workshop-fr.pptx')
$powerPoint = New-Object -ComObject PowerPoint.Application
$findings = [Collections.Generic.List[object]]::new()
try {
    foreach ($file in $files) {
        $name = [IO.Path]::GetFileNameWithoutExtension($file)
        $directory = Join-Path $OutputDirectory $name
        [IO.Directory]::CreateDirectory($directory) | Out-Null
        $presentation = $powerPoint.Presentations.Open((Join-Path $root $file), -1, 0, 0)
        try {
            foreach ($slide in $presentation.Slides) {
                $slide.Export((Join-Path $directory ('slide-{0:D2}.png' -f $slide.SlideIndex)), 'PNG', 1600, 900)
                foreach ($shape in $slide.Shapes) {
                    if ($shape.HasTextFrame -and $shape.TextFrame.HasText) {
                        $text = $shape.TextFrame.TextRange
                        if ($text.BoundTop + $text.BoundHeight -gt 534 -or $text.BoundHeight -gt $shape.Height + 4 -or $text.BoundWidth -gt $shape.Width + 4) {
                            $findings.Add(@{ deck = $name; slide = $slide.SlideIndex; text = $text.Text; height = $text.BoundHeight; boxHeight = $shape.Height })
                        }
                    }
                }
            }
            $columns = 3
            $rows = [math]::Ceiling($presentation.Slides.Count / $columns)
            $sheet = [Drawing.Bitmap]::new(1200, [int]($rows * 249))
            $graphics = [Drawing.Graphics]::FromImage($sheet)
            $graphics.Clear([Drawing.Color]::White)
            $font = [Drawing.Font]::new('Segoe UI', 10)
            for ($index = 1; $index -le $presentation.Slides.Count; $index++) {
                $image = [Drawing.Image]::FromFile((Join-Path $directory ('slide-{0:D2}.png' -f $index)))
                $left = (($index - 1) % $columns) * 400
                $top = [math]::Floor(($index - 1) / $columns) * 249
                $graphics.DrawImage($image, [int]$left, [int]$top, 400, 225)
                $graphics.DrawString("$index", $font, [Drawing.Brushes]::Black, [single]($left + 8), [single]($top + 228))
                $image.Dispose()
            }
            $sheet.Save((Join-Path $OutputDirectory "$name.png"), [Drawing.Imaging.ImageFormat]::Png)
            $graphics.Dispose()
            $font.Dispose()
            $sheet.Dispose()
            Write-Output "$name : $($presentation.Slides.Count) slides rendered"
        } finally { $presentation.Close() }
    }
} finally { $powerPoint.Quit() }
$findings | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $OutputDirectory 'text-bounds.json')
Write-Output "Potential text-bound issues: $($findings.Count). Review: $OutputDirectory"