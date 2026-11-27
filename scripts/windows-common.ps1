#requires -Version 7.2
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-AlcPath([string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value) -or $Value.Contains([char]0)) { throw 'Empty/NUL path' }
    if ($Value.StartsWith('~\') -or $Value.StartsWith('~/')) { $Value = Join-Path $HOME $Value.Substring(2) }
    if ($Value.StartsWith('\\?\') -or $Value.StartsWith('\\.\')) { throw 'Device paths are not supported' }
    $full = [IO.Path]::GetFullPath($Value)
    $root = [IO.Path]::GetPathRoot($full)
    foreach ($part in $full.Substring($root.Length).Split([char[]]@('\','/'), [StringSplitOptions]::RemoveEmptyEntries)) {
        if ($part -match '[. ]$|[<>:"|?*\x00-\x1f]' -or $part.Split('.')[0].TrimEnd() -match '^(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³])$') {
            throw "Invalid Windows path component: $part"
        }
    }
    return $full
}

function Assert-AlcPlainPath([string]$Path) {
    $full = Resolve-AlcPath $Path
    $root = [IO.Path]::GetPathRoot($full)
    $current = $root
    foreach ($part in $full.Substring($root.Length).Split([char[]]@('\','/'), [StringSplitOptions]::RemoveEmptyEntries)) {
        $current = Join-Path $current $part
        $item = Get-Item -LiteralPath $current -Force -ErrorAction SilentlyContinue
        if ($null -ne $item -and ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "Reparse point refused: $current"
        }
    }
}

function Test-AlcWithin([string]$Path, [string]$Root) {
    $p = (Resolve-AlcPath $Path).TrimEnd('\','/')
    $r = (Resolve-AlcPath $Root).TrimEnd('\','/')
    return $p.Equals($r,[StringComparison]::OrdinalIgnoreCase) -or $p.StartsWith($r + '\',[StringComparison]::OrdinalIgnoreCase)
}

function Resolve-AlcExe([string]$Name, [string]$Override) {
    $candidates = @()
    if ($Override) {
        if (-not [IO.Path]::IsPathFullyQualified($Override)) { throw "$Name override must be an absolute native executable path" }
        $candidates = @($Override)
    }
    else {
        foreach ($dir in ($env:PATH -split [regex]::Escape([string][IO.Path]::PathSeparator))) {
            $dir = $dir.Trim('"')
            if ($dir -and [IO.Path]::IsPathFullyQualified($dir)) { $candidates += (Join-Path $dir ($Name + '.exe')) }
        }
    }
    foreach ($candidate in $candidates) {
        $full = Resolve-AlcPath $candidate
        if ([IO.Path]::GetExtension($full) -ieq '.exe' -and (Test-Path -LiteralPath $full -PathType Leaf)) { return $full }
    }
    throw "$Name native executable not found; configure an absolute .exe path (no cmd/bat fallback)"
}

function Invoke-AlcProbe([string]$Exe, [string[]]$Arguments, [string]$Label) {
    # No shell, no model execution, no background process left on timeout.
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $Exe
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    foreach ($key in @('NODE_OPTIONS','NODE_PATH','PYTHONPATH','PYTHONHOME')) { [void]$psi.Environment.Remove($key) }
    foreach ($arg in $Arguments) { [void]$psi.ArgumentList.Add($arg) }
    $p = [Diagnostics.Process]::new()
    $p.StartInfo = $psi
    try {
        if (-not $p.Start()) { throw "$Label failed to start" }
        $out = $p.StandardOutput.ReadToEndAsync()
        $err = $p.StandardError.ReadToEndAsync()
        if (-not $p.WaitForExit(15000)) { $p.Kill($true); $p.WaitForExit(); throw "$Label probe timed out" }
        if ($p.ExitCode -ne 0) { throw "$Label probe failed (exit $($p.ExitCode))" }
        return $out.GetAwaiter().GetResult().Trim()
    } finally { $p.Dispose() }
}

function Get-AlcRuntime([string]$NodeBin,[string]$PythonBin,[string]$GitBin,[string]$CodexBin,[bool]$ConsoleOnly) {
    $node = Resolve-AlcExe 'node' $NodeBin
    $nodeVersion = Invoke-AlcProbe $node @('--no-warnings','-e','const [a,b]=process.versions.node.split(".").map(Number); if(a<22||(a===22&&b<5))process.exit(1); require("node:sqlite"); console.log(process.versions.node)') 'Node >=22.5 with node:sqlite'
    $codex = Resolve-AlcExe 'codex' $CodexBin
    $codexVersion = Invoke-AlcProbe $codex @('--version') 'Codex CLI'
    if ($codexVersion -notmatch '(?i)\bcodex(?:-cli)?\b') { throw 'Codex executable did not identify itself via --version' }
    $python = $null; $pythonVersion = $null; $git = $null; $gitVersion = $null
    if (-not $ConsoleOnly) {
        $python = Resolve-AlcExe 'python' $PythonBin
        $pythonVersion = Invoke-AlcProbe $python @('-I','-c','import sys; print(sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3,10) else 1)') 'Python >=3.10'
        $git = Resolve-AlcExe 'git' $GitBin
        $gitVersion = Invoke-AlcProbe $git @('--version') 'Git'
        if ($gitVersion -notmatch '^git version ') { throw 'Unexpected Git version response' }
    }
    return [ordered]@{Node=$node; NodeVersion=$nodeVersion; Codex=$codex; CodexVersion=$codexVersion; Python=$python; PythonVersion=$pythonVersion; Git=$git; GitVersion=$gitVersion}
}

function Copy-AlcTree([string]$Source,[string]$Destination) {
    Assert-AlcPlainPath $Source
    if (-not (Test-Path -LiteralPath $Source -PathType Container)) { throw "Missing component: $Source" }
    if (Test-Path -LiteralPath $Destination) { throw "Stage already exists: $Destination" }
    # npm ci on Windows creates normal files; refuse links in trusted source/stage.
    foreach ($item in (Get-ChildItem -LiteralPath $Source -Recurse -Force)) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Reparse point in component: $($item.FullName)" }
    }
    Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
}

function Write-AlcJournal([string]$Directory,[object]$Journal) {
    $tmp = Join-Path $Directory ('journal.' + [guid]::NewGuid().ToString('N') + '.tmp')
    [IO.File]::WriteAllText($tmp, ($Journal | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
    [IO.File]::Move($tmp,(Join-Path $Directory 'journal.json'),$true)
}

function Invoke-AlcTransaction([string]$Config,[string]$Transaction,[object[]]$Entries,[scriptblock]$MoveAction = {
    param($From,$To) Move-Item -LiteralPath $From -Destination $To -ErrorAction Stop
}) {
    # Entries are generated internally from a fixed allowlist; stages are same-volume.
    $original = Join-Path $Transaction 'original'
    $failed = Join-Path $Transaction 'failed'
    [void][IO.Directory]::CreateDirectory($original)
    [void][IO.Directory]::CreateDirectory($failed)
    $journal = [ordered]@{status='applying';config=$Config;entries=@()}
    foreach ($e in $Entries) {
        if (-not (Test-AlcWithin $e.Target $Config) -or (Test-AlcWithin $e.Target $Transaction)) { throw 'Invalid transaction target' }
        Assert-AlcPlainPath $e.Target
        if ($e.Staged) {
            if (-not (Test-AlcWithin $e.Staged $Transaction)) { throw 'Stage outside transaction' }
            Assert-AlcPlainPath $e.Staged
            if (-not (Test-Path -LiteralPath $e.Staged -PathType Container)) { throw 'Missing staged component' }
        }
        if ((Test-Path -LiteralPath $e.Target) -and -not (Test-Path -LiteralPath $e.Target -PathType Container)) { throw 'Target is not a component directory' }
        $journal.entries += [ordered]@{id=$e.Id;target=$e.Target;staged=$e.Staged;backup=(Join-Path $original $e.Id);oldMoved=$false;newMoved=$false}
    }
    Write-AlcJournal $Transaction $journal
    try {
        foreach ($e in $journal.entries) {
            [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($e.target))
            if (Test-Path -LiteralPath $e.target) {
                & $MoveAction $e.target $e.backup
                $e.oldMoved = $true
                Write-AlcJournal $Transaction $journal
            }
            if ($e.staged) {
                & $MoveAction $e.staged $e.target
                $e.newMoved = $true
                Write-AlcJournal $Transaction $journal
            }
        }
        $journal.status='committed'
        Write-AlcJournal $Transaction $journal
    } catch {
        $cause = $_
        $rollbackErrors = @()
        for ($i=$journal.entries.Count-1; $i -ge 0; $i--) {
            $e = $journal.entries[$i]
            try {
                if ($e.newMoved) { Move-Item -LiteralPath $e.target -Destination (Join-Path $failed $e.id) -ErrorAction Stop }
                if ($e.oldMoved) { Move-Item -LiteralPath $e.backup -Destination $e.target -ErrorAction Stop }
            } catch { $rollbackErrors += $_.Exception.Message }
        }
        $journal.status = if ($rollbackErrors.Count) {'rollback_incomplete'} else {'rolled_back'}
        $journal.errors = $rollbackErrors
        Write-AlcJournal $Transaction $journal
        if ($rollbackErrors.Count) { throw "Install failed; rollback incomplete. Preserve and inspect $Transaction" }
        throw "Install failed; prior components restored, evidence retained in $Transaction. $($cause.Exception.Message)"
    }
    return $Transaction
}
