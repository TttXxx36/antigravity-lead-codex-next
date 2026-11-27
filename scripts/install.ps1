#requires -Version 7.2
[CmdletBinding()]
param(
    [ValidateSet('All','ConsoleOnly','Uninstall','Restore')][string]$Mode='All',
    [string]$SourceDir=(Join-Path $PSScriptRoot '..'),
    [string]$GeminiConfigDir=$env:GEMINI_CONFIG_DIR,
    [string]$CodexHome=$env:CODEX_HOME,
    [string]$DispatchStateDir=$env:AGY_DISPATCH_STATE_DIR,
    [string]$PluginDataDir,
    [string]$NodeBin=$env:NODE_BIN,
    [string]$PythonBin=$env:PYTHON_BIN,
    [string]$GitBin=$env:GIT_BIN,
    [string]$CodexBin=$env:CODEX_BIN,
    [string]$RestoreFrom
)
. (Join-Path $PSScriptRoot 'windows-common.ps1')
if (-not $IsWindows) { throw 'Use install.sh on Linux/macOS; this installer targets native Windows' }
if (-not $GeminiConfigDir) { $GeminiConfigDir=Join-Path $HOME '.gemini\config' }
if (-not $CodexHome) { $CodexHome=Join-Path $HOME '.codex' }
if (-not $DispatchStateDir) { $DispatchStateDir=Join-Path $HOME '.local\state\multi-agent-dispatch' }
if (-not $PluginDataDir) { $PluginDataDir=Join-Path $HOME '.gemini\antigravity\plugin_data\codex-console' }
$config=Resolve-AlcPath $GeminiConfigDir
$source=Resolve-AlcPath $SourceDir
$codexHomePath=Resolve-AlcPath $CodexHome
$statePath=Resolve-AlcPath $DispatchStateDir
$dataPath=Resolve-AlcPath $PluginDataDir
if ($config.TrimEnd('\') -eq ([IO.Path]::GetPathRoot($config)).TrimEnd('\')) { throw 'Config cannot be a volume root' }
Assert-AlcPlainPath $config
$managed=@(
    @{Id='codex-console';Relative='plugins\codex-console'},
    @{Id='codex-auto-router';Relative='plugins\codex-auto-router'},
    @{Id='multi-agent-dispatch';Relative='skills\multi-agent-dispatch'}
)
$backupRoot=Join-Path $config '.alc-backups'
foreach ($entry in $managed) {
    $target=Join-Path $config $entry.Relative
    Assert-AlcPlainPath $target
    foreach ($data in @($codexHomePath,$statePath,$dataPath)) {
        if ((Test-AlcWithin $data $target) -or (Test-AlcWithin $target $data)) { throw 'Data and managed plugin directories must be disjoint' }
    }
    if ((Test-AlcWithin $source $target) -or (Test-AlcWithin $target $source)) { throw 'Source and installed component must be disjoint' }
}
foreach ($data in @($codexHomePath,$statePath,$dataPath)) {
    if (Test-AlcWithin $data $backupRoot) { throw 'Data cannot be inside backup directory' }
}
$runtime=$null
if ($Mode -in @('All','ConsoleOnly')) {
    $runtime=Get-AlcRuntime $NodeBin $PythonBin $GitBin $CodexBin ($Mode -eq 'ConsoleOnly')
    $console=Join-Path $source 'plugins\codex-console'
    foreach ($file in @('plugin.json','dist\app.html','server\index.mjs','package-lock.json','node_modules\@modelcontextprotocol\sdk\package.json','node_modules\zod\package.json')) {
        if (-not (Test-Path -LiteralPath (Join-Path $console $file) -PathType Leaf)) { throw "Source dependency/file missing: $file. Prepare locked runtime dependencies separately (npm ci --omit=dev --ignore-scripts)." }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $source 'LICENSE') -PathType Leaf)) { throw 'Source license missing' }
}
[void][IO.Directory]::CreateDirectory($config)
Assert-AlcPlainPath $backupRoot
[void][IO.Directory]::CreateDirectory($backupRoot)
$lockPath=Join-Path $config '.alc-install.lock'
Assert-AlcPlainPath $lockPath
$lock=[IO.File]::Open($lockPath,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
    $transaction=Join-Path $backupRoot ((Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')+'-'+[guid]::NewGuid().ToString('N'))
    $stage=Join-Path $transaction 'staged'
    [void][IO.Directory]::CreateDirectory($stage)
    $entries=@()
    $restoreRoot=$null
    if ($Mode -eq 'Restore') {
        if (-not $RestoreFrom) { throw 'Restore requires -RestoreFrom transaction path' }
        $restoreRoot=Resolve-AlcPath $RestoreFrom
        if (-not (Test-AlcWithin $restoreRoot $backupRoot) -or [IO.Path]::GetDirectoryName($restoreRoot) -ine $backupRoot) { throw 'Restore must select one direct backup transaction' }
        Assert-AlcPlainPath $restoreRoot
        $oldJournal=Get-Content -LiteralPath (Join-Path $restoreRoot 'journal.json') -Raw | ConvertFrom-Json
        if ($oldJournal.status -ne 'committed') { throw 'Only a committed backup may be restored automatically; inspect incomplete journal manually' }
    }
    foreach ($item in $managed) {
        if ($Mode -eq 'ConsoleOnly' -and $item.Id -ne 'codex-console') { continue }
        $target=Join-Path $config $item.Relative
        $staged=$null
        if ($Mode -eq 'Restore') {
            $old=Join-Path (Join-Path $restoreRoot 'original') $item.Id
            if (-not (Test-Path -LiteralPath $old -PathType Container)) { continue }
            $staged=Join-Path $stage $item.Id
            Copy-AlcTree $old $staged
        } elseif ($Mode -ne 'Uninstall') {
            $staged=Join-Path $stage $item.Id
            Copy-AlcTree (Join-Path $source $item.Relative) $staged
            Copy-Item -LiteralPath (Join-Path $source 'LICENSE') -Destination (Join-Path $staged 'ALC-LICENSE') -Force
            if ($item.Id -eq 'codex-console') {
                $envMap=[ordered]@{CODEX_HOME=$codexHomePath;AGY_DISPATCH_STATE_DIR=$statePath;GEMINI_CONFIG_DIR=$config;NODE_BIN=$runtime.Node;CODEX_BIN=$runtime.Codex;PYTHONUTF8='1';PYTHONIOENCODING='utf-8'}
                if ($runtime.Python) { $envMap.PYTHON_BIN=$runtime.Python }
                if ($runtime.Git) { $envMap.GIT_BIN=$runtime.Git }
                $mcp=[ordered]@{mcpServers=@{codex_console=@{command=$runtime.Node;args=@('--no-warnings',(Join-Path $target 'server\index.mjs'),'--data-dir',$dataPath);env=$envMap}}}
                [IO.File]::WriteAllText((Join-Path $staged 'mcp_config.json'),($mcp | ConvertTo-Json -Depth 10),[Text.UTF8Encoding]::new($false))
            }
        }
        $entries+=@{Id=$item.Id;Target=$target;Staged=$staged}
    }
    if (-not $entries.Count) { throw 'No components to restore' }
    $backup=Invoke-AlcTransaction $config $transaction $entries
    [pscustomobject]@{Mode=$Mode;Config=$config;Backup=$backup;Runtime=$runtime;PluginData=$dataPath;StateDir=$statePath;Note='Restart Antigravity manually. Data directories are not modified.'}
} finally { $lock.Dispose() }
