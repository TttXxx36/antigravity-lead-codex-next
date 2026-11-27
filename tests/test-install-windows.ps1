#requires -Version 7.2
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$repo=Split-Path $PSScriptRoot -Parent
. (Join-Path $repo 'scripts\windows-common.ps1')
if (-not $IsWindows) { throw 'Native Windows lifecycle test requires Windows' }
function Check([bool]$condition,[string]$message) { if(-not $condition){throw $message} }
$root=Join-Path ([IO.Path]::GetTempPath()) ('alc-d05-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($root)
try {
    $config=Join-Path $root '中文 空格\config'
    $data=Join-Path $root '保留 数据'
    $state=Join-Path $root 'dispatch state'
    $codexHome=Join-Path $root 'codex home'
    foreach($dir in @($data,$state,$codexHome)){[void][IO.Directory]::CreateDirectory($dir);[IO.File]::WriteAllText((Join-Path $dir 'sentinel.txt'),'keep')}
    $csc=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
    if(-not (Test-Path -LiteralPath $csc)){throw 'Framework C# compiler unavailable; native mock cannot be built'}
    $cs=Join-Path $root 'Mock.cs';$mock=Join-Path $root 'mock-codex.exe'
    [IO.File]::WriteAllText($cs,'using System; class Mock { static int Main(string[] a) { if(a.Length==1 && a[0]=="--version"){ Console.WriteLine("codex-cli 0.0.0-mock"); return 0; } return 99; } }')
    & $csc '/nologo' '/target:exe' ("/out:$mock") $cs
    if($LASTEXITCODE -ne 0){throw 'Native mock compilation failed'}
    $install=Join-Path $repo 'scripts\install.ps1'
    $doctor=Join-Path $repo 'scripts\doctor.ps1'
    $params=@{SourceDir=$repo;GeminiConfigDir=$config;PluginDataDir=$data;DispatchStateDir=$state;CodexHome=$codexHome;
      NodeBin=(Get-Command node.exe -CommandType Application | Select-Object -First 1).Source;
      PythonBin=(Get-Command python.exe -CommandType Application | Select-Object -First 1).Source;
      GitBin=(Get-Command git.exe -CommandType Application | Select-Object -First 1).Source;CodexBin=$mock}
    # Verify actual disposable SQLite files, not just sentinel text.
    $dbProbe=Join-Path $root 'db-probe.mjs'
    [IO.File]::WriteAllText($dbProbe, @'
import {DatabaseSync} from 'node:sqlite';
const [mode,...files]=process.argv.slice(2);
for(const file of files){
 const db=new DatabaseSync(file,{readOnly:mode==='check'});
 try {
  if(mode==='create'){db.exec("CREATE TABLE sentinel(value TEXT); INSERT INTO sentinel VALUES ('keep');");}
  else if(db.prepare("SELECT value FROM sentinel").get()?.value!=='keep')throw new Error('SQLite fixture changed');
 } finally{db.close();}
}
'@)
    $dbs=@((Join-Path $data 'console.sqlite'),(Join-Path $codexHome 'state_5.sqlite'))
    & $params.NodeBin --no-warnings $dbProbe create @dbs
    Check ($LASTEXITCODE -eq 0) 'SQLite fixture setup failed'
    $hashes=@($dbs | ForEach-Object { (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash })
    $first=& $install @params -Mode All
    $console=Join-Path $config 'plugins\codex-console'
    Check (Test-Path -LiteralPath (Join-Path $console 'mcp_config.json')) 'Install missing config'
    $m=(Get-Content -LiteralPath (Join-Path $console 'mcp_config.json') -Raw | ConvertFrom-Json).mcpServers.codex_console
    Check ($m.command -ieq $params.NodeBin) 'Expected native node.exe'
    Check ($m.args[3] -ieq $data) 'Data directory mismatch'
    $diag=& $doctor -GeminiConfigDir $config
    Check ($diag.Status -eq 'PASS') 'Installed MCP initialize failed'
    [IO.File]::WriteAllText((Join-Path $console 'custom-marker.txt'),'old')
    $bad=$params.Clone();$bad.PythonBin=Join-Path $root 'missing.exe'
    $rejected=$false
    try { & $install @bad -Mode All | Out-Null } catch { $rejected=$true }
    Check $rejected 'Missing dependency not rejected'
    Check (Test-Path -LiteralPath (Join-Path $console 'custom-marker.txt')) 'Failed preflight modified live install'
    $upgrade=& $install @params -Mode All
    Check (Test-Path -LiteralPath (Join-Path $upgrade.Backup 'original\codex-console\custom-marker.txt')) 'Upgrade backup missing'
    $restored=& $install @params -Mode Restore -RestoreFrom $upgrade.Backup
    Check (Test-Path -LiteralPath (Join-Path $console 'custom-marker.txt')) 'Restore did not recover old component'
    $uninstall=& $install @params -Mode Uninstall
    Check (-not (Test-Path -LiteralPath $console)) 'Uninstall retained live plugin'
    Check (Test-Path -LiteralPath (Join-Path $uninstall.Backup 'original\codex-console')) 'Uninstall did not preserve plugin backup'
    $again=& $install @params -Mode All
    $diag=& $doctor -GeminiConfigDir $config
    Check ($diag.Status -eq 'PASS') 'Reinstall handshake failed'
    foreach($dir in @($data,$state,$codexHome)){Check ((Get-Content -LiteralPath (Join-Path $dir 'sentinel.txt') -Raw) -eq 'keep') 'Persistent data changed'}
    # Console-only install must not require Python or Git and must not install the skill.
    $consoleOnlyParams=$params.Clone()
    $consoleOnlyParams.GeminiConfigDir=Join-Path $root 'console-only config'
    $consoleOnlyParams.PythonBin=Join-Path $root 'unused-python.exe'
    $consoleOnlyParams.GitBin=Join-Path $root 'unused-git.exe'
    $only=& $install @consoleOnlyParams -Mode ConsoleOnly
    Check (-not (Test-Path -LiteralPath (Join-Path $consoleOnlyParams.GeminiConfigDir 'skills\multi-agent-dispatch'))) 'ConsoleOnly installed skill'
    $onlyDoctor=& $doctor -GeminiConfigDir $consoleOnlyParams.GeminiConfigDir
    Check ($onlyDoctor.Status -eq 'PASS') 'ConsoleOnly diagnostic failed'
    & $install @consoleOnlyParams -Mode Uninstall | Out-Null
    foreach($dir in @($data,$state,$codexHome)){Check ((Get-Content -LiteralPath (Join-Path $dir 'sentinel.txt') -Raw) -eq 'keep') 'ConsoleOnly changed persistent data'}
    & $params.NodeBin --no-warnings $dbProbe check @dbs
    Check ($LASTEXITCODE -eq 0) 'SQLite fixture not readable'
    for($i=0;$i -lt $dbs.Count;$i++){Check ((Get-FileHash -LiteralPath $dbs[$i] -Algorithm SHA256).Hash -eq $hashes[$i]) 'SQLite fixture bytes changed'}
    # Fault-inject the second staged move, exercising real first move, backup and rollback.
    $synthetic=Join-Path $root 'rollback-config';$txn=Join-Path $synthetic '.alc-backups\test'
    $one=Join-Path $synthetic 'one';$two=Join-Path $synthetic 'two'
    $s1=Join-Path $txn 'staged\one';$s2=Join-Path $txn 'staged\two'
    foreach($dir in @($one,$two,$s1,$s2)){[void][IO.Directory]::CreateDirectory($dir)}
    [IO.File]::WriteAllText((Join-Path $one 'old.txt'),'one')
    [IO.File]::WriteAllText((Join-Path $two 'old.txt'),'two')
    $entries=@(@{Id='one';Target=$one;Staged=$s1},@{Id='two';Target=$two;Staged=$s2})
    $fault={param($From,$To) if($From.EndsWith('staged\two')){throw 'injected failure'};Move-Item -LiteralPath $From -Destination $To -ErrorAction Stop}
    $rolled=$false
    try{Invoke-AlcTransaction $synthetic $txn $entries $fault | Out-Null}catch{$rolled=$true}
    Check $rolled 'Injected failure not surfaced'
    Check ((Get-Content -LiteralPath (Join-Path $one 'old.txt') -Raw) -eq 'one') 'First old component not restored'
    Check ((Get-Content -LiteralPath (Join-Path $two 'old.txt') -Raw) -eq 'two') 'Second old component not restored'
    Check ((Get-Content -LiteralPath (Join-Path $txn 'journal.json') -Raw | ConvertFrom-Json).status -eq 'rolled_back') 'Rollback journal incorrect'
    Write-Host 'PASS: install, upgrade, restore, uninstall, reinstall, native MCP initialize, missing dependency, injected rollback, persistent data, Unicode paths, console-only lifecycle, SQLite bytes preserved'
} finally {
    # Disposable test fixture only.
    Remove-Item -LiteralPath $root -Recurse -Force -ErrorAction Stop
}
