param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"

$assetDirectory = Join-Path $ProjectRoot "assets\demos"
$captureDirectory = Join-Path $assetDirectory "captures-16x9"
$buildDirectory = Join-Path $ProjectRoot "tmp\technical-demo"
$audioDirectory = Join-Path $buildDirectory "audio"
$deckPath = Join-Path $assetDirectory "wealthplan-technical-demo.pptx"
$videoPath = Join-Path $assetDirectory "wealthplan-technical-demo.mp4"
$captionPath = Join-Path $assetDirectory "wealthplan-technical-demo.vtt"
$cursorPath = Join-Path $assetDirectory "cursor.svg"

New-Item -ItemType Directory -Path $assetDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $audioDirectory -Force | Out-Null

function Get-Color([int]$Red, [int]$Green, [int]$Blue) {
    return $Red + ($Green * 256) + ($Blue * 65536)
}

$navy = Get-Color 19 35 63
$white = Get-Color 255 255 255
$softWhite = Get-Color 232 239 248
$muted = Get-Color 164 181 204

$scenes = @(
    [ordered]@{
        Image = "01-input.png"
        CursorX = 589
        CursorY = 278
        Transition = 3849
        Title = "1. Configure the request"
        Kicker = "REAL STREAMLIT WALKTHROUGH"
        Narration = "This is WealthPlan, our bring-your-own Week 3 use case. In Streamlit, an investor supplies a profile, chooses a company, sets risk and time horizon, and asks a research question. The one-line job is to turn that context into a grounded educational plan that combines company research, portfolio analysis, goal scenarios, review, and a human decision. This is the actual application, not a mockup."
    },
    [ordered]@{
        Image = "02-configured.png"
        CursorX = 590
        CursorY = 266
        Transition = 3855
        Title = "2. Choose bounded specialists"
        Kicker = "USER INTENT BECOMES ROUTING INPUT"
        Narration = "This is a multi-agent workflow, not one model calling every tool. A supervisor agent receives the request and selects three bounded specialists: a company research agent, a portfolio analysis agent, and a goal planning agent. Each specialist owns a focused task, bounded tools, and a structured result. Shared typed WealthPlan state carries routing, outputs, review findings, approval responses, audit events, and write authorization without giving any specialist unrestricted control."
    },
    [ordered]@{
        Image = "03-workflow.png"
        CursorX = 714
        CursorY = 145
        Transition = 3855
        Title = "3. Watch LangGraph execute"
        Kicker = "SUPERVISION, FAN-OUT, AND FAN-IN"
        Narration = "Generate WealthPlan invokes the LangGraph supervisor. After normalization and Pydantic validation, it fans work out with LangGraph Send. The research, portfolio, and goal agents run independently and may complete in parallel. Each writes a structured result into shared state. LangGraph fans those results back in at report assembly, sends the combined draft to risk review, and pauses at human approval. That supervisor-specialist fan-out and fan-in is the core multi-agent pattern. The badges identify checkpoint memory and the retrieval services."
    },
    [ordered]@{
        Image = "05-company.png"
        CursorX = 374
        CursorY = 270
        Transition = 3849
        Title = "4. Ground the answer in SEC evidence"
        Kicker = "SEC FACTS AND FILING RETRIEVAL ARE SEPARATE"
        Narration = "The company screen shows two data paths. Historical fundamentals come from the SEC Company Facts XBRL API, independent of Pinecone. Filing questions use an indexed ten-K corpus: embeddings search the LangGraph Pinecone namespace with a ticker filter, then Cohere reranks candidates. The five Microsoft passages retain filing section, accession, date, ticker, and source URL."
    },
    [ordered]@{
        Image = "06-portfolio.png"
        CursorX = 480
        CursorY = 270
        Transition = 3849
        Title = "5. Keep financial arithmetic deterministic"
        Kicker = "PORTFOLIO SPECIALIST"
        Narration = "The portfolio specialist calculates position value, allocation, gains, sector exposure, and concentration from fixed holdings and illustrative prices. Those numbers are produced by deterministic tools, not invented in model prose. The model may explain the result, but it does not own the arithmetic. The application labels the price basis and highlights concentration so the output remains auditable and educational."
    },
    [ordered]@{
        Image = "07-goals.png"
        CursorX = 570
        CursorY = 270
        Transition = 3849
        Title = "6. Make assumptions visible"
        Kicker = "GOAL AND SCENARIO SPECIALIST"
        Narration = "The goal specialist projects the retirement target and compares four, six, and eight percent return assumptions. Inputs such as savings, contribution, inflation, withdrawal rate, and retirement age remain visible. The tool explicitly warns that these are scenarios, not forecasts, and that taxes, fees, volatility, and sequence-of-returns risk are outside this deterministic prototype."
    },
    [ordered]@{
        Image = "08-review.png"
        CursorX = 660
        CursorY = 270
        Transition = 3849
        Title = "7. Stop at a human approval gate"
        Kicker = "POLICY REVIEW BEFORE ANY APPROVED WRITE"
        Narration = "After report assembly, policy checks verify specialist completion, narrative presence, deterministic calculations, data labels, and no write before approval. LangGraph interrupt then pauses. Reads and calculations are autonomous, but a consequential approved record requires a human choice. Approve can authorize one PostgreSQL transaction. Edit loops through policy review. Reject must stop without an approved write. The prototype never executes a trade."
    },
    [ordered]@{
        Image = "09-history.png"
        CursorX = 728
        CursorY = 270
        Transition = 3849
        Title = "8. Separate checkpoint memory from records"
        Kicker = "STATE HAS PURPOSE AND LIFETIME"
        Narration = "Memory has three roles. Typed graph state exists for the run. A thread checkpointer supports pause and resume by thread ID. Approved profiles, holdings, decisions, and reports live in the repository and appear in History. Pinecone stores filing chunks only; it is evidence storage, not conversation memory. Service failures retry or use labeled cache, while missing evidence remains explicit."
    },
    [ordered]@{
        Image = "08-review.png"
        CursorX = 660
        CursorY = 270
        Transition = 3849
        Title = "9. Reviewer edits re-enter the graph"
        Kicker = "RECOVERY IS CONTROL FLOW"
        Narration = "Request edits resumes the interrupted thread, applies reviewer instructions, reruns risk review, and returns to the same human gate. Failures have deliberate paths: missing inputs request clarification, model failures use deterministic fallbacks, specialist errors become structured warnings, and persistence failures display as failed rather than false success."
    },
    [ordered]@{
        Image = "10-outcome.png"
        CursorX = 835
        CursorY = 282
        Transition = 3855
        Title = "10. Reject ends safely with no write"
        Kicker = "END-TO-END COMPLETION, NOT ONE-SHOT ACCURACY"
        Narration = "The final decision is Reject. The navigator records rejected without a write, and the workspace confirms that no write was authorized. This demonstrates the Week 3 framework end to end: a supervisor coordinating specialized agents, parallel delegation, typed state, bounded tools, visible recovery, and human control of the durable action. Success means a reviewable, grounded result with correct calculations and zero unapproved writes, not simply a convincing model response."
    }
)

function Add-Text {
    param(
        $Slide,
        [string]$Text,
        [double]$Left,
        [double]$Top,
        [double]$Width,
        [double]$Height,
        [double]$Size,
        [int]$Color,
        [bool]$Bold = $false,
        [int]$Align = 1
    )
    $shape = $Slide.Shapes.AddTextbox(1, $Left, $Top, $Width, $Height)
    $shape.TextFrame.MarginLeft = 0
    $shape.TextFrame.MarginRight = 0
    $shape.TextFrame.MarginTop = 0
    $shape.TextFrame.MarginBottom = 0
    $shape.TextFrame.WordWrap = -1
    $range = $shape.TextFrame.TextRange
    $range.Text = $Text
    $range.Font.Name = "Aptos"
    $range.Font.Size = $Size
    $range.Font.Color.RGB = $Color
    $range.Font.Bold = if ($Bold) { -1 } else { 0 }
    $range.ParagraphFormat.Alignment = $Align
    return $shape
}

function Get-WavDurationSeconds([string]$Path) {
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $byteRate = [System.BitConverter]::ToInt32($bytes, 28)
    $dataIndex = -1
    for ($index = 36; $index -le $bytes.Length - 8; $index++) {
        if ($bytes[$index] -eq 100 -and $bytes[$index + 1] -eq 97 -and $bytes[$index + 2] -eq 116 -and $bytes[$index + 3] -eq 97) {
            $dataIndex = $index
            break
        }
    }
    if ($dataIndex -lt 0 -or $byteRate -le 0) {
        throw "Could not read WAV duration for $Path"
    }
    $dataSize = [System.BitConverter]::ToInt32($bytes, $dataIndex + 4)
    return [double]$dataSize / [double]$byteRate
}

function Format-VttTime([double]$Seconds) {
    $span = [TimeSpan]::FromSeconds($Seconds)
    return "{0:00}:{1:00}:{2:00}.{3:000}" -f [math]::Floor($span.TotalHours), $span.Minutes, $span.Seconds, $span.Milliseconds
}

function Add-VttCaptionCues {
    param(
        [System.Collections.Generic.List[string]]$Lines,
        [string]$Text,
        [double]$StartSeconds,
        [double]$SpeechDurationSeconds,
        [int]$WordsPerCue = 9
    )

    $words = @($Text -split '\s+' | Where-Object { $_ })
    if ($words.Count -eq 0) {
        return
    }

    $cursor = $StartSeconds
    for ($offset = 0; $offset -lt $words.Count; $offset += $WordsPerCue) {
        $count = [math]::Min($WordsPerCue, $words.Count - $offset)
        $chunk = $words[$offset..($offset + $count - 1)] -join " "
        $chunkDuration = $SpeechDurationSeconds * ($count / [double]$words.Count)
        $chunkEnd = if ($offset + $count -ge $words.Count) {
            $StartSeconds + $SpeechDurationSeconds
        }
        else {
            $cursor + $chunkDuration
        }
        $Lines.Add(("{0} --> {1}" -f (Format-VttTime $cursor), (Format-VttTime $chunkEnd)))
        $Lines.Add($chunk)
        $Lines.Add("")
        $cursor = $chunkEnd
    }
}

$powerpoint = $null
$presentation = $null
$voice = $null
try {
    $voice = New-Object -ComObject SAPI.SpVoice
    $zira = $voice.GetVoices() | Where-Object { $_.GetDescription() -like "Microsoft Zira Desktop*" } | Select-Object -First 1
    if (-not $zira) {
        throw "Microsoft Zira Desktop is not installed."
    }
    $voice.Voice = $zira
    $voice.Rate = 1
    $voice.Volume = 100

    $powerpoint = New-Object -ComObject PowerPoint.Application
    $powerpoint.Visible = -1
    $powerpoint.WindowState = 2
    $presentation = $powerpoint.Presentations.Add()
    $presentation.PageSetup.SlideWidth = 960
    $presentation.PageSetup.SlideHeight = 540

    $vttLines = [System.Collections.Generic.List[string]]::new()
    $vttLines.Add("WEBVTT")
    $vttLines.Add("")
    $videoTimeline = 0.0
    $renderPaddingSeconds = 2.0

    for ($index = 0; $index -lt $scenes.Count; $index++) {
        $scene = $scenes[$index]
        $imagePath = Join-Path $captureDirectory $scene.Image
        if (-not (Test-Path -LiteralPath $imagePath)) {
            throw "Missing captured app frame: $imagePath"
        }

        "BUILDING_SCENE=$($index + 1)|$($scene.Title)"
        $slide = $presentation.Slides.Add($index + 1, 12)
        [void]$slide.Shapes.AddPicture($imagePath, 0, -1, 0, 0, 960, 540)

        # Keep the application itself full-frame. A restrained cursor and click
        # ring provide the visual cue that this is a guided UI walkthrough.
        $ring = $slide.Shapes.AddShape(9, $scene.CursorX - 11, $scene.CursorY - 11, 30, 30)
        $ring.Fill.Visible = 0
        $ring.Line.ForeColor.RGB = Get-Color 255 78 86
        $ring.Line.Transparency = 0.12
        $ring.Line.Weight = 2.5
        [void]$slide.Shapes.AddPicture($cursorPath, 0, -1, $scene.CursorX, $scene.CursorY, 25, 32)

        $audioPath = Join-Path $audioDirectory ("scene-{0:00}.wav" -f ($index + 1))
        $audioStream = New-Object -ComObject SAPI.SpFileStream
        $audioStream.Open($audioPath, 3, $false)
        $voice.AudioOutputStream = $audioStream
        [void]$voice.Speak($scene.Narration, 0)
        $audioStream.Close()
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($audioStream)
        $speechDuration = Get-WavDurationSeconds $audioPath
        $duration = $speechDuration + 0.7
        $cueStart = $videoTimeline
        Add-VttCaptionCues $vttLines $scene.Narration $cueStart $speechDuration
        $videoTimeline = $cueStart + $duration + $renderPaddingSeconds

        $audioShape = $slide.Shapes.AddMediaObject2($audioPath, 0, -1, 930, 510, 10, 10)
        $audioShape.AnimationSettings.PlaySettings.PlayOnEntry = -1
        $audioShape.AnimationSettings.PlaySettings.HideWhileNotPlaying = -1
        $slide.SlideShowTransition.AdvanceOnClick = 0
        $slide.SlideShowTransition.AdvanceOnTime = -1
        $slide.SlideShowTransition.AdvanceTime = $duration
        $slide.SlideShowTransition.EntryEffect = $scene.Transition
    }

    if ($videoTimeline -ge 295) {
        throw "Rendered video is too long: $([math]::Round($videoTimeline, 1)) seconds"
    }

    if (Test-Path -LiteralPath $deckPath) {
        Remove-Item -LiteralPath $deckPath -Force
    }
    if (Test-Path -LiteralPath $videoPath) {
        Remove-Item -LiteralPath $videoPath -Force
    }
    $presentation.SaveAs($deckPath, 24)
    [System.IO.File]::WriteAllLines($captionPath, $vttLines, [System.Text.UTF8Encoding]::new($false))
    $presentation.CreateVideo($videoPath, -1, 5, 1080, 30, 85)

    $deadline = [DateTime]::UtcNow.AddMinutes(30)
    while ($presentation.CreateVideoStatus -in @(1, 2)) {
        if ([DateTime]::UtcNow -gt $deadline) {
            throw "PowerPoint video export exceeded 30 minutes"
        }
        Start-Sleep -Seconds 2
    }
    if ($presentation.CreateVideoStatus -ne 3 -or -not (Test-Path -LiteralPath $videoPath)) {
        throw "PowerPoint video export failed with status $($presentation.CreateVideoStatus)"
    }

    "VIDEO=$videoPath"
    "DECK=$deckPath"
    "CAPTIONS=$captionPath"
    "DURATION_SECONDS=$([math]::Round($videoTimeline, 1))"
    "VIDEO_BYTES=$((Get-Item -LiteralPath $videoPath).Length)"
}
finally {
    if ($presentation) { $presentation.Close() }
    if ($powerpoint) { $powerpoint.Quit() }
    if ($voice) { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($voice) }
    if ($presentation) { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($presentation) }
    if ($powerpoint) { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($powerpoint) }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
