param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"

$items = @(
    @{
        Svg = "docs\week3_workflow_infographic.svg"
        Png = "docs\week3_workflow_infographic.png"
        Width = 1600
        Height = 1050
    },
    @{
        Svg = "docs\week3_state_safety_infographic.svg"
        Png = "docs\week3_state_safety_infographic.png"
        Width = 1600
        Height = 950
    }
)

$powerpoint = $null
try {
    $powerpoint = New-Object -ComObject PowerPoint.Application
    $powerpoint.Visible = -1
    $powerpoint.WindowState = 2

    foreach ($item in $items) {
        $presentation = $null
        try {
            $presentation = $powerpoint.Presentations.Add()
            $presentation.PageSetup.SlideWidth = 960
            $presentation.PageSetup.SlideHeight = 960 * $item.Height / $item.Width
            $slide = $presentation.Slides.Add(1, 12)
            $svgPath = Join-Path $ProjectRoot $item.Svg
            $pngPath = Join-Path $ProjectRoot $item.Png
            [void]$slide.Shapes.AddPicture(
                $svgPath,
                0,
                -1,
                0,
                0,
                $presentation.PageSetup.SlideWidth,
                $presentation.PageSetup.SlideHeight
            )
            if (Test-Path -LiteralPath $pngPath) {
                Remove-Item -LiteralPath $pngPath -Force
            }
            $slide.Export($pngPath, "PNG", $item.Width, $item.Height)
            "PNG=$pngPath|BYTES=$((Get-Item -LiteralPath $pngPath).Length)"
        }
        finally {
            if ($presentation) {
                $presentation.Close()
                [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject(
                    $presentation
                )
            }
        }
    }
}
finally {
    if ($powerpoint) {
        $powerpoint.Quit()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($powerpoint)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
