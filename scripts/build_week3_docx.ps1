param(
    [Parameter(Mandatory = $false)]
    [string]$ProjectRoot = ''
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectRoot = Split-Path -Parent $scriptDir
}

$projectFull = [IO.Path]::GetFullPath($ProjectRoot)
$docsDir = Join-Path $projectFull 'docs'
$sourcePath = Join-Path $docsDir 'week3_project_documentation.md'
$outputPath = Join-Path $docsDir 'WealthPlan2.0_Week3_Project_Documentation.docx'
$buildDir = Join-Path $projectFull '.docx-build-week3'

$images = @{
    'WealthPlan2.0.png' = @{ Id = 'rId8'; Target = 'image1.png'; Caption = 'Figure 1. WealthPlan2.0 supervised multi-agent project architecture.'; Alt = 'WealthPlan2.0 multi-agent workflow infographic.' }
    'week3_workflow_infographic.png' = @{ Id = 'rId9'; Target = 'image2.png'; Caption = 'Figure 2. Technical LangGraph control flow: supervisor fan-out, specialist fan-in, review, and human decision.'; Alt = 'Technical WealthPlan LangGraph workflow diagram.' }
    'week3_state_safety_infographic.png' = @{ Id = 'rId10'; Target = 'image3.png'; Caption = 'Figure 3. State boundaries, error recovery, and the approval-gated write path.'; Alt = 'WealthPlan state, safety, and error recovery diagram.' }
}

foreach ($path in @($sourcePath, (Join-Path $docsDir 'WealthPlan2.0.png'))) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Required file not found: $path" }
}

function Escape-Xml {
    param([AllowEmptyString()][string]$Text)
    if ($null -eq $Text) { return '' }
    return [Security.SecurityElement]::Escape($Text)
}

function Clean-Markdown {
    param([string]$Text)
    $clean = $Text
    $clean = [regex]::Replace($clean, '!\[([^\]]*)\]\([^\)]*\)', '$1')
    $clean = [regex]::Replace($clean, '\[([^\]]+)\]\([^\)]*\)', '$1')
    $clean = $clean.Replace('**', '').Replace('__', '').Replace('`', '')
    $clean = $clean.Replace([char]0x2014, '-').Replace([char]0x2013, '-')
    $clean = $clean.Replace([char]0x2018, "'").Replace([char]0x2019, "'")
    $clean = $clean.Replace([char]0x201C, '"').Replace([char]0x201D, '"')
    $clean = $clean.Replace([char]0x00B7, '|').Replace([char]0x00A0, ' ')
    return $clean.Trim()
}

function New-RunXml {
    param(
        [string]$Text,
        [int]$Size = 22,
        [string]$Color = '24324A',
        [bool]$Bold = $false,
        [bool]$Italic = $false,
        [string]$Font = 'Calibri'
    )
    $boldXml = if ($Bold) { '<w:b/><w:bCs/>' } else { '' }
    $italicXml = if ($Italic) { '<w:i/><w:iCs/>' } else { '' }
    $escaped = Escape-Xml $Text
    return "<w:r><w:rPr><w:rFonts w:ascii=`"$Font`" w:hAnsi=`"$Font`"/><w:color w:val=`"$Color`"/><w:sz w:val=`"$Size`"/><w:szCs w:val=`"$Size`"/>$boldXml$italicXml</w:rPr><w:t xml:space=`"preserve`">$escaped</w:t></w:r>"
}

function New-ParagraphXml {
    param(
        [string]$Text = '',
        [string]$Style = 'Normal',
        [ValidateSet('left', 'center', 'right', 'both')][string]$Align = 'left',
        [int]$Before = 0,
        [int]$After = 120,
        [int]$Line = 300,
        [bool]$KeepNext = $false,
        [bool]$PageBreakBefore = $false,
        [int]$Size = 22,
        [string]$Color = '24324A',
        [bool]$Bold = $false,
        [bool]$Italic = $false,
        [string]$Font = 'Calibri',
        [int]$NumId = 0
    )
    $keepXml = if ($KeepNext) { '<w:keepNext/>' } else { '' }
    $pageBreakXml = if ($PageBreakBefore) { '<w:pageBreakBefore/>' } else { '' }
    $numXml = if ($NumId -gt 0) { "<w:numPr><w:ilvl w:val=`"0`"/><w:numId w:val=`"$NumId`"/></w:numPr>" } else { '' }
    $run = New-RunXml -Text $Text -Size $Size -Color $Color -Bold $Bold -Italic $Italic -Font $Font
    return "<w:p><w:pPr><w:pStyle w:val=`"$Style`"/>$keepXml$pageBreakXml$numXml<w:jc w:val=`"$Align`"/><w:spacing w:before=`"$Before`" w:after=`"$After`" w:line=`"$Line`" w:lineRule=`"auto`"/></w:pPr>$run</w:p>"
}

function New-PageBreakXml {
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
}

function New-CellXml {
    param([string]$Text, [int]$Width, [bool]$Header = $false, [string]$Fill = '')
    $shade = if ($Fill) { "<w:shd w:val=`"clear`" w:color=`"auto`" w:fill=`"$Fill`"/>" } else { '' }
    $size = if ($Header) { 19 } else { 18 }
    $color = if ($Header) { '10213D' } else { '24324A' }
    $run = New-RunXml -Text (Clean-Markdown $Text) -Size $size -Color $color -Bold $Header
    return "<w:tc><w:tcPr><w:tcW w:w=`"$Width`" w:type=`"dxa`"/><w:vAlign w:val=`"center`"/>$shade</w:tcPr><w:p><w:pPr><w:spacing w:before=`"0`" w:after=`"40`" w:line=`"240`" w:lineRule=`"auto`"/></w:pPr>$run</w:p></w:tc>"
}

function Get-ColumnWidthsDxa {
    param([string[]]$Headers)
    $first = $Headers[0]
    if ($Headers.Count -eq 2) {
        switch -Regex ($first) {
            '^Field$' { return @(3000, 6360) }
            '^Layer$' { return @(2760, 6600) }
            '^Topic$' { return @(2900, 6460) }
            default { return @(3000, 6360) }
        }
    }
    if ($Headers.Count -eq 3) {
        switch -Regex ($first) {
            '^Data or corpus$' { return @(2100, 2600, 4660) }
            '^Prompt$' { return @(1880, 2520, 4960) }
            '^Iteration$' { return @(1840, 2360, 5160) }
            '^State layer$' { return @(1960, 3480, 3920) }
            '^Failure$' { return @(2240, 3800, 3320) }
            '^Requirement$' { return @(3000, 1560, 4800) }
            default { return @(2400, 3000, 3960) }
        }
    }
    $each = [int](9360 / $Headers.Count)
    return @(0..($Headers.Count - 1) | ForEach-Object { $each })
}

function New-TableXml {
    param([object[]]$Rows)
    if ($Rows.Count -eq 0) { return '' }
    $headers = [string[]]$Rows[0]
    $widths = Get-ColumnWidthsDxa -Headers $headers
    $grid = ($widths | ForEach-Object { "<w:gridCol w:w=`"$_`"/>" }) -join ''
    $rowXml = New-Object System.Collections.Generic.List[string]
    for ($r = 0; $r -lt $Rows.Count; $r++) {
        $cells = New-Object System.Collections.Generic.List[string]
        for ($c = 0; $c -lt $headers.Count; $c++) {
            $text = if ($c -lt $Rows[$r].Count) { [string]$Rows[$r][$c] } else { '' }
            $cellFill = if ($r -eq 0) { 'E8EEF5' } else { '' }
            $cells.Add((New-CellXml -Text $text -Width $widths[$c] -Header ($r -eq 0) -Fill $cellFill))
        }
        $headerProperty = if ($r -eq 0) { '<w:tblHeader/>' } else { '' }
        $rowXml.Add("<w:tr><w:trPr>$headerProperty<w:cantSplit w:val=`"0`"/></w:trPr>$($cells -join '')</w:tr>")
    }
    return "<w:tbl><w:tblPr><w:tblStyle w:val=`"TableGrid`"/><w:tblW w:w=`"9360`" w:type=`"dxa`"/><w:tblInd w:w=`"120`" w:type=`"dxa`"/><w:tblLayout w:type=`"fixed`"/><w:tblCellMar><w:top w:w=`"80`" w:type=`"dxa`"/><w:start w:w=`"120`" w:type=`"dxa`"/><w:bottom w:w=`"80`" w:type=`"dxa`"/><w:end w:w=`"120`" w:type=`"dxa`"/></w:tblCellMar><w:tblBorders><w:top w:val=`"single`" w:sz=`"6`" w:color=`"C9D3E1`"/><w:left w:val=`"single`" w:sz=`"6`" w:color=`"C9D3E1`"/><w:bottom w:val=`"single`" w:sz=`"6`" w:color=`"C9D3E1`"/><w:right w:val=`"single`" w:sz=`"6`" w:color=`"C9D3E1`"/><w:insideH w:val=`"single`" w:sz=`"4`" w:color=`"D7DFEA`"/><w:insideV w:val=`"single`" w:sz=`"4`" w:color=`"D7DFEA`"/></w:tblBorders></w:tblPr><w:tblGrid>$grid</w:tblGrid>$($rowXml -join '')</w:tbl><w:p><w:pPr><w:spacing w:after=`"80`"/></w:pPr></w:p>"
}

function New-CalloutXml {
    param([string]$Text, [ValidateSet('blue', 'teal', 'gold')][string]$Tone = 'blue')
    $fill = switch ($Tone) { 'teal' { 'E8F4F1' } 'gold' { 'FFF7DF' } default { 'E8EEF5' } }
    $border = if ($Tone -eq 'teal') { '278878' } else { '2E74B5' }
    $run = New-RunXml -Text (Clean-Markdown $Text) -Size 22 -Color '10213D' -Bold $true
    return "<w:tbl><w:tblPr><w:tblW w:w=`"9360`" w:type=`"dxa`"/><w:tblInd w:w=`"120`" w:type=`"dxa`"/><w:tblLayout w:type=`"fixed`"/><w:tblCellMar><w:top w:w=`"180`" w:type=`"dxa`"/><w:start w:w=`"240`" w:type=`"dxa`"/><w:bottom w:w=`"180`" w:type=`"dxa`"/><w:end w:w=`"240`" w:type=`"dxa`"/></w:tblCellMar><w:tblBorders><w:top w:val=`"single`" w:sz=`"8`" w:color=`"$border`"/><w:left w:val=`"single`" w:sz=`"12`" w:color=`"$border`"/><w:bottom w:val=`"single`" w:sz=`"8`" w:color=`"$border`"/><w:right w:val=`"single`" w:sz=`"8`" w:color=`"$border`"/></w:tblBorders></w:tblPr><w:tblGrid><w:gridCol w:w=`"9360`"/></w:tblGrid><w:tr><w:tc><w:tcPr><w:tcW w:w=`"9360`" w:type=`"dxa`"/><w:shd w:val=`"clear`" w:color=`"auto`" w:fill=`"$fill`"/><w:vAlign w:val=`"center`"/></w:tcPr><w:p><w:pPr><w:spacing w:after=`"0`" w:line=`"280`" w:lineRule=`"auto`"/></w:pPr>$run</w:p></w:tc></w:tr></w:tbl><w:p><w:pPr><w:spacing w:after=`"120`"/></w:pPr></w:p>"
}

function New-CodeBlockXml {
    param([string[]]$Lines)
    $paragraphs = ($Lines | ForEach-Object { New-ParagraphXml -Text $_ -Style 'Code' -After 0 -Line 240 -Size 18 -Color '10213D' -Font 'Consolas' }) -join ''
    return "<w:tbl><w:tblPr><w:tblW w:w=`"9360`" w:type=`"dxa`"/><w:tblInd w:w=`"120`" w:type=`"dxa`"/><w:tblLayout w:type=`"fixed`"/><w:tblCellMar><w:top w:w=`"120`" w:type=`"dxa`"/><w:start w:w=`"160`" w:type=`"dxa`"/><w:bottom w:w=`"120`" w:type=`"dxa`"/><w:end w:w=`"160`" w:type=`"dxa`"/></w:tblCellMar><w:tblBorders><w:top w:val=`"single`" w:sz=`"4`" w:color=`"C9D3E1`"/><w:left w:val=`"single`" w:sz=`"4`" w:color=`"C9D3E1`"/><w:bottom w:val=`"single`" w:sz=`"4`" w:color=`"C9D3E1`"/><w:right w:val=`"single`" w:sz=`"4`" w:color=`"C9D3E1`"/></w:tblBorders></w:tblPr><w:tblGrid><w:gridCol w:w=`"9360`"/></w:tblGrid><w:tr><w:tc><w:tcPr><w:tcW w:w=`"9360`" w:type=`"dxa`"/><w:shd w:val=`"clear`" w:color=`"auto`" w:fill=`"F4F6F9`"/></w:tcPr>$paragraphs</w:tc></w:tr></w:tbl><w:p><w:pPr><w:spacing w:after=`"120`"/></w:pPr></w:p>"
}

function Get-PngDimensions {
    param([string]$Path)
    $bytes = [IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 24) { throw "Invalid PNG: $Path" }
    $width = [Net.IPAddress]::NetworkToHostOrder([BitConverter]::ToInt32($bytes, 16))
    $height = [Net.IPAddress]::NetworkToHostOrder([BitConverter]::ToInt32($bytes, 20))
    return @($width, $height)
}

function New-FigureXml {
    param([string]$ImagePath, [string]$RelationshipId, [string]$Caption, [string]$AltText, [int]$DocPrId)
    $dims = Get-PngDimensions -Path $ImagePath
    $cx = [int64](6.20 * 914400)
    $cy = [int64]($cx * $dims[1] / $dims[0])
    $safeAlt = Escape-Xml $AltText
    $drawing = "<w:p><w:pPr><w:jc w:val=`"center`"/><w:spacing w:before=`"80`" w:after=`"80`"/><w:keepNext/></w:pPr><w:r><w:drawing><wp:inline distT=`"0`" distB=`"0`" distL=`"0`" distR=`"0`"><wp:extent cx=`"$cx`" cy=`"$cy`"/><wp:effectExtent l=`"0`" t=`"0`" r=`"0`" b=`"0`"/><wp:docPr id=`"$DocPrId`" name=`"Figure $DocPrId`" descr=`"$safeAlt`"/><wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a=`"http://schemas.openxmlformats.org/drawingml/2006/main`" noChangeAspect=`"1`"/></wp:cNvGraphicFramePr><a:graphic xmlns:a=`"http://schemas.openxmlformats.org/drawingml/2006/main`"><a:graphicData uri=`"http://schemas.openxmlformats.org/drawingml/2006/picture`"><pic:pic xmlns:pic=`"http://schemas.openxmlformats.org/drawingml/2006/picture`"><pic:nvPicPr><pic:cNvPr id=`"$DocPrId`" name=`"Figure $DocPrId`" descr=`"$safeAlt`"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed=`"$RelationshipId`"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x=`"0`" y=`"0`"/><a:ext cx=`"$cx`" cy=`"$cy`"/></a:xfrm><a:prstGeom prst=`"rect`"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>"
    $captionXml = New-ParagraphXml -Text $Caption -Style 'Caption' -Align 'center' -After 200 -Line 240 -Size 18 -Color '667085' -Italic $true
    return $drawing + $captionXml
}

$body = New-Object System.Collections.Generic.List[string]

# Editorial cover using the compact-reference-guide token system.
$body.Add((New-ParagraphXml -Text 'WEEK 3 PROJECT DOCUMENTATION' -Align 'center' -Before 1520 -After 360 -Line 260 -Size 21 -Color '278878' -Bold $true))
$body.Add((New-ParagraphXml -Text 'WealthPlan2.0' -Align 'center' -After 160 -Line 720 -Size 62 -Color '10213D' -Bold $true))
$body.Add((New-ParagraphXml -Text 'Supervised Multi-Agent Financial Research & Planning' -Align 'center' -After 480 -Line 380 -Size 32 -Color '1F4D78'))
$body.Add((New-ParagraphXml -Text 'Bring your own use case | Python | LangChain | LangGraph | Streamlit' -Align 'center' -After 720 -Line 260 -Size 21 -Color '667085' -Bold $true))
$body.Add((New-CalloutXml -Text 'Plans. Delegates. Remembers. Recovers. Pauses for human approval.' -Tone 'teal'))
$body.Add((New-ParagraphXml -Text 'A complete implementation record covering the project primer, control flow, data sources, prompts, iterations, state, safety, error recovery, and demonstration evidence.' -Align 'center' -Before 480 -After 880 -Line 310 -Size 23 -Color '24324A'))
$body.Add((New-ParagraphXml -Text 'Mastering Agentic AI Certification - Week 3' -Align 'center' -After 80 -Line 240 -Size 21 -Color '667085' -Bold $true))
$body.Add((New-ParagraphXml -Text 'August 2026 | Educational prototype - not financial advice' -Align 'center' -After 0 -Line 220 -Size 19 -Color '667085' -Italic $true))
$body.Add((New-PageBreakXml))

$body.Add((New-ParagraphXml -Text 'Contents' -Style 'Heading1' -After 240 -Line 560 -Size 48 -Color '10213D' -Bold $true))
$body.Add((New-ParagraphXml -Text 'This Word edition follows the same substantive order as the Markdown source and is optimized for review, presentation, and submission.' -After 240 -Line 280 -Size 21 -Color '667085'))
$contents = @(
    '1. The Primer: the one-liner', '2. Workflow infographic', '3. The Week 3 framework',
    '4. What we built', '5. Data and datasets used', '6. Prompts', '7. Iterations tried',
    '8. State, safety, and error-handling infographic', '9. Error handling - separate from the happy path',
    '10. Human-in-the-loop and authorization', '11. Learnings and observations',
    '12. Week 3 requirement scorecard', '13. Known limitations and next work',
    '14. Setup, startup, and demo checklist', '15. Evidence map'
)
foreach ($item in $contents) {
    $body.Add((New-ParagraphXml -Text $item -After 100 -Line 250 -Size 21 -Color '1F4D78' -Bold $true))
}
$body.Add((New-PageBreakXml))

$lines = Get-Content -LiteralPath $sourcePath -Encoding utf8
$startIndex = 0
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^##\s+1\.\s+') { $startIndex = $i; break }
}

$paragraphBuffer = New-Object System.Collections.Generic.List[string]
$codeLines = New-Object System.Collections.Generic.List[string]
$inCode = $false
$numberContinue = $false
$currentNumberId = 0
$nextNumberId = 2
$numberIds = New-Object System.Collections.Generic.List[int]
$figureId = 1

function Flush-BodyParagraph {
    if ($paragraphBuffer.Count -gt 0) {
        $text = Clean-Markdown ($paragraphBuffer -join ' ')
        if ($text) { $body.Add((New-ParagraphXml -Text $text)) }
        $paragraphBuffer.Clear()
    }
}

$i = $startIndex
while ($i -lt $lines.Count) {
    $line = $lines[$i]
    $trimmed = $line.Trim()

    if ($trimmed -match '^```') {
        Flush-BodyParagraph
        if (-not $inCode) { $inCode = $true; $codeLines.Clear() }
        else { $body.Add((New-CodeBlockXml -Lines $codeLines.ToArray())); $inCode = $false }
        $i++; continue
    }
    if ($inCode) { $codeLines.Add($line); $i++; continue }

    if (-not $trimmed) {
        Flush-BodyParagraph
        $numberContinue = $false
        $i++; continue
    }

    if ($trimmed -match '^\|') {
        Flush-BodyParagraph
        $tableRows = New-Object System.Collections.Generic.List[object]
        while ($i -lt $lines.Count -and $lines[$i].Trim() -match '^\|') {
            $parts = $lines[$i].Trim().Trim('|').Split('|') | ForEach-Object { $_.Trim() }
            $separator = $true
            foreach ($part in $parts) { if ($part -notmatch '^:?-{3,}:?$') { $separator = $false; break } }
            if (-not $separator) { $tableRows.Add([string[]]$parts) }
            $i++
        }
        $body.Add((New-TableXml -Rows $tableRows.ToArray()))
        $numberContinue = $false
        continue
    }

    if ($trimmed -match '^!\[([^\]]*)\]\(([^\)]+)\)') {
        Flush-BodyParagraph
        $alt = $Matches[1]
        $relative = $Matches[2]
        $fileName = [IO.Path]::GetFileName($relative)
        if ([IO.Path]::GetExtension($fileName) -eq '.svg') { $fileName = [IO.Path]::ChangeExtension($fileName, '.png') }
        if ($images.ContainsKey($fileName)) {
            $meta = $images[$fileName]
            $path = Join-Path $docsDir $fileName
            if (Test-Path -LiteralPath $path) {
                $body.Add((New-FigureXml -ImagePath $path -RelationshipId $meta.Id -Caption $meta.Caption -AltText $meta.Alt -DocPrId $figureId))
                $figureId++
            }
        }
        $i++; continue
    }

    if ($trimmed -match '^###\s+(.+)$') {
        Flush-BodyParagraph
        $body.Add((New-ParagraphXml -Text (Clean-Markdown $Matches[1]) -Style 'Heading2' -Before 280 -After 140 -Line 300 -Size 26 -Color '2E74B5' -Bold $true -KeepNext $true))
        $numberContinue = $false
        $i++; continue
    }
    if ($trimmed -match '^##\s+(.+)$') {
        Flush-BodyParagraph
        $heading = Clean-Markdown $Matches[1]
        if ($heading -match '^(2|8)\.') { $body.Add((New-PageBreakXml)) }
        $body.Add((New-ParagraphXml -Text $heading -Style 'Heading1' -Before 360 -After 200 -Line 360 -Size 32 -Color '2E74B5' -Bold $true -KeepNext $true))
        $numberContinue = $false
        $i++; continue
    }
    if ($trimmed -match '^>\s*(.+)$') {
        Flush-BodyParagraph
        $body.Add((New-CalloutXml -Text (Clean-Markdown $Matches[1]) -Tone 'blue'))
        $i++; continue
    }
    if ($trimmed -match '^[-*]\s+(.+)$') {
        Flush-BodyParagraph
        $body.Add((New-ParagraphXml -Text (Clean-Markdown $Matches[1]) -After 80 -Line 300 -NumId 1))
        $numberContinue = $false
        $i++; continue
    }
    if ($trimmed -match '^\d+\.\s+(.+)$') {
        Flush-BodyParagraph
        if (-not $numberContinue) {
            $currentNumberId = $nextNumberId
            $nextNumberId++
            $numberIds.Add($currentNumberId)
        }
        $body.Add((New-ParagraphXml -Text (Clean-Markdown $Matches[1]) -After 80 -Line 300 -NumId $currentNumberId))
        $numberContinue = $true
        $i++; continue
    }

    $paragraphBuffer.Add($trimmed)
    $i++
}
Flush-BodyParagraph

$body.Add((New-CalloutXml -Text 'Submission note: the four-of-five success target is defined but not yet formally measured. Full-suite automated testing remains deferred because the prior pytest run hung; bounded quick validation is the documented limit.' -Tone 'gold'))

$sectPr = '<w:sectPr><w:headerReference w:type="default" r:id="rId6"/><w:footerReference w:type="default" r:id="rId7"/><w:titlePg/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/><w:cols w:space="720"/><w:docGrid w:linePitch="360"/></w:sectPr>'
$documentXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><w:body>' +
    ($body -join '') + $sectPr + '</w:body></w:document>'

$stylesXml = @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:color w:val="24324A"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="300" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="120" w:line="300" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:color w:val="24324A"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:uiPriority w:val="9"/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="360" w:after="200"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="2E74B5"/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:uiPriority w:val="9"/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="280" w:after="140"/><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:color w:val="2E74B5"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:uiPriority w:val="9"/><w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="200" w:after="100"/><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:color w:val="1F4D78"/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="Caption"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:jc w:val="center"/><w:spacing w:after="200"/></w:pPr><w:rPr><w:i/><w:color w:val="667085"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/><w:basedOn w:val="Normal"/><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:color w:val="10213D"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>
  <w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/><w:uiPriority w:val="99"/></w:style>
  <w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:basedOn w:val="TableNormal"/><w:uiPriority w:val="59"/></w:style>
</w:styles>
'@

$numInstances = '<w:num w:numId="1"><w:abstractNumId w:val="1"/></w:num>'
foreach ($numId in $numberIds) {
    $numInstances += "<w:num w:numId=`"$numId`"><w:abstractNumId w:val=`"2`"/><w:lvlOverride w:ilvl=`"0`"><w:startOverride w:val=`"1`"/></w:lvlOverride></w:num>"
}
$numberingXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' +
    '<w:abstractNum w:abstractNumId="1"><w:multiLevelType w:val="singleLevel"/><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="&#x2022;"/><w:lvlJc w:val="left"/><w:pPr><w:tabs><w:tab w:val="num" w:pos="540"/></w:tabs><w:ind w:left="540" w:hanging="270"/><w:spacing w:after="80" w:line="300" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/></w:rPr></w:lvl></w:abstractNum>' +
    '<w:abstractNum w:abstractNumId="2"><w:multiLevelType w:val="singleLevel"/><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/><w:lvlJc w:val="left"/><w:pPr><w:tabs><w:tab w:val="num" w:pos="540"/></w:tabs><w:ind w:left="540" w:hanging="270"/><w:spacing w:after="80" w:line="300" w:lineRule="auto"/></w:pPr></w:lvl></w:abstractNum>' + $numInstances + '</w:numbering>'

$headerXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:b/><w:color w:val="667085"/><w:sz w:val="17"/><w:szCs w:val="17"/></w:rPr><w:t>WEALTHPLAN2.0  |  WEEK 3 PROJECT DOCUMENTATION</w:t></w:r></w:p></w:hdr>'
$footerXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:pPr><w:tabs><w:tab w:val="right" w:pos="9360"/></w:tabs><w:spacing w:before="0" w:after="0"/></w:pPr><w:r><w:rPr><w:color w:val="667085"/><w:sz w:val="17"/></w:rPr><w:t>Educational prototype - not financial advice</w:t></w:r><w:r><w:tab/></w:r><w:r><w:rPr><w:color w:val="667085"/><w:sz w:val="17"/></w:rPr><w:t>Page </w:t></w:r><w:fldSimple w:instr="PAGE"><w:r><w:rPr><w:color w:val="667085"/><w:sz w:val="17"/></w:rPr><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>'

$settingsXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:zoom w:percent="100"/><w:defaultTabStop w:val="720"/><w:updateFields w:val="true"/></w:settings>'

$documentRels = @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
  <Relationship Id="rId6" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>
  <Relationship Id="rId7" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/>
  <Relationship Id="rId8" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
  <Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image2.png"/>
  <Relationship Id="rId10" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image3.png"/>
</Relationships>
'@

$rootRels = @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
'@

$contentTypes = @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
  <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
  <Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>
  <Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
'@

$coreXml = @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>WealthPlan2.0 - Week 3 Project Documentation</dc:title><dc:subject>Supervised, stateful, multi-agent educational wealth-planning workflow</dc:subject><dc:creator>WealthPlan Project</dc:creator><cp:keywords>LangGraph, LangChain, Streamlit, multi-agent, human-in-the-loop, SEC, RAG</cp:keywords><dcterms:created xsi:type="dcterms:W3CDTF">2026-08-29T00:00:00Z</dcterms:created><dcterms:modified xsi:type="dcterms:W3CDTF">2026-08-29T00:00:00Z</dcterms:modified></cp:coreProperties>
'@
$appXml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>Microsoft Office Word</Application><DocSecurity>0</DocSecurity><ScaleCrop>false</ScaleCrop><Company>WealthPlan</Company><AppVersion>16.0000</AppVersion></Properties>'

# Recreate only the task-local package directory; verify it stays inside the project.
$buildFull = [IO.Path]::GetFullPath($buildDir)
if (-not $buildFull.StartsWith($projectFull, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe DOCX build path.' }
if (Test-Path -LiteralPath $buildFull) { Remove-Item -LiteralPath $buildFull -Recurse -Force }

foreach ($dir in @('_rels', 'docProps', 'word', 'word\_rels', 'word\media')) {
    New-Item -ItemType Directory -Path (Join-Path $buildFull $dir) -Force | Out-Null
}

$utf8NoBom = New-Object Text.UTF8Encoding($false)
function Write-Utf8NoBom { param([string]$Path, [string]$Content) [IO.File]::WriteAllText($Path, $Content, $utf8NoBom) }

Write-Utf8NoBom -Path (Join-Path $buildFull '[Content_Types].xml') -Content $contentTypes
Write-Utf8NoBom -Path (Join-Path $buildFull '_rels\.rels') -Content $rootRels
Write-Utf8NoBom -Path (Join-Path $buildFull 'docProps\core.xml') -Content $coreXml
Write-Utf8NoBom -Path (Join-Path $buildFull 'docProps\app.xml') -Content $appXml
Write-Utf8NoBom -Path (Join-Path $buildFull 'word\document.xml') -Content $documentXml
Write-Utf8NoBom -Path (Join-Path $buildFull 'word\styles.xml') -Content $stylesXml
Write-Utf8NoBom -Path (Join-Path $buildFull 'word\numbering.xml') -Content $numberingXml
Write-Utf8NoBom -Path (Join-Path $buildFull 'word\settings.xml') -Content $settingsXml
Write-Utf8NoBom -Path (Join-Path $buildFull 'word\header1.xml') -Content $headerXml
Write-Utf8NoBom -Path (Join-Path $buildFull 'word\footer1.xml') -Content $footerXml
Write-Utf8NoBom -Path (Join-Path $buildFull 'word\_rels\document.xml.rels') -Content $documentRels

Copy-Item -LiteralPath (Join-Path $docsDir 'WealthPlan2.0.png') -Destination (Join-Path $buildFull 'word\media\image1.png')
Copy-Item -LiteralPath (Join-Path $docsDir 'week3_workflow_infographic.png') -Destination (Join-Path $buildFull 'word\media\image2.png')
Copy-Item -LiteralPath (Join-Path $docsDir 'week3_state_safety_infographic.png') -Destination (Join-Path $buildFull 'word\media\image3.png')

Add-Type -AssemblyName System.IO.Compression.FileSystem
if (Test-Path -LiteralPath $outputPath) { Remove-Item -LiteralPath $outputPath -Force }
[IO.Compression.ZipFile]::CreateFromDirectory($buildFull, $outputPath, [IO.Compression.CompressionLevel]::Optimal, $false)

# Structural validation of the final package.
$archive = [IO.Compression.ZipFile]::OpenRead($outputPath)
try {
    $requiredEntries = @('[Content_Types].xml', '_rels/.rels', 'word/document.xml', 'word/styles.xml', 'word/numbering.xml', 'word/_rels/document.xml.rels', 'word/media/image1.png')
    $names = $archive.Entries | ForEach-Object { $_.FullName.Replace('\', '/') }
    foreach ($entry in $requiredEntries) {
        if ($names -notcontains $entry) { throw "DOCX package is missing $entry" }
    }
} finally {
    $archive.Dispose()
}

Remove-Item -LiteralPath $buildFull -Recurse -Force
Write-Output $outputPath
