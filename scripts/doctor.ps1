#requires -Version 7.2
[CmdletBinding()]
param([string]$GeminiConfigDir=$env:GEMINI_CONFIG_DIR)
. (Join-Path $PSScriptRoot 'windows-common.ps1')
if (-not $IsWindows) { throw 'Use doctor.sh on Linux/macOS' }
if (-not $GeminiConfigDir) { $GeminiConfigDir=Join-Path $HOME '.gemini\config' }
$config=Resolve-AlcPath $GeminiConfigDir
$console=Join-Path $config 'plugins\codex-console'
$mcpFile=Join-Path $console 'mcp_config.json'
Assert-AlcPlainPath $mcpFile
$server=(Get-Content -LiteralPath $mcpFile -Raw | ConvertFrom-Json -AsHashtable).mcpServers.codex_console
$entry=Join-Path $console 'server\index.mjs'
if ($server.args.Count -ne 4 -or $server.args[0] -ne '--no-warnings' -or $server.args[1] -ine $entry -or $server.args[2] -ne '--data-dir') { throw 'Unexpected installed MCP command; refusing to execute' }
$fullMode=Test-Path -LiteralPath (Join-Path $config 'skills\multi-agent-dispatch\scripts\dispatch.py') -PathType Leaf
$runtime=Get-AlcRuntime $server.command ($server.env.PYTHON_BIN) ($server.env.GIT_BIN) $server.env.CODEX_BIN (-not $fullMode)
foreach ($file in @('plugin.json','dist\app.html','node_modules\@modelcontextprotocol\sdk\package.json','server\index.mjs')) {
    if (-not (Test-Path -LiteralPath (Join-Path $console $file) -PathType Leaf)) { throw "Installed component incomplete: $file" }
}
# Only initialize/list on an isolated synthetic database; no quota or worker calls.
$smoke=Join-Path $PSScriptRoot 'mcp-smoke.mjs'
$answer=Invoke-AlcProbe $runtime.Node @('--no-warnings',$smoke,$entry) 'Isolated MCP initialize'
$verified=$answer | ConvertFrom-Json
if ($verified.status -ne 'PASS') { throw 'MCP handshake failed' }
[pscustomobject]@{Status='PASS';Runtime=$runtime;Handshake=$verified;Config=$config;PluginData=$server.args[3];CodexStatePresent=(Test-Path -LiteralPath (Join-Path $server.env.CODEX_HOME 'state_5.sqlite') -PathType Leaf);Note='Local synthetic handshake only; Antigravity desktop integration must be verified separately.'}
