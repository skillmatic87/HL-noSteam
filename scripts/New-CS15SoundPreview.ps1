[CmdletBinding()]
param([string]$ContentDirectory)
$ErrorActionPreference='Stop'
if (-not $ContentDirectory) { $ContentDirectory=Join-Path (Split-Path -Parent $PSScriptRoot) 'content' }
$manifest=Get-Content -LiteralPath (Join-Path $ContentDirectory 'pack.json') -Raw | ConvertFrom-Json
$rows=foreach ($sound in $manifest.sounds) {
    $keyword=[Net.WebUtility]::HtmlEncode($sound.keyword)
    $path=[Net.WebUtility]::HtmlEncode(('files/cstrike/'+$sound.path))
    $seconds=([double]$sound.seconds).ToString('0.00',[Globalization.CultureInfo]::InvariantCulture)
    '<tr data-keyword="'+$keyword+'"><th scope="row"><code>'+$keyword+'</code></th><td>'+$seconds+' s</td><td><audio controls preload="none" aria-label="Listen to '+$keyword+'" src="'+$path+'"></audio></td></tr>'
}
$template=@'
<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LAN Sound Preview</title>
<style>
  :root { color-scheme:light; font:16px/1.55 system-ui,sans-serif; color:#172e39; background:#f3f5f3; }
  body { max-width:880px; margin:42px auto; padding:0 20px 40px; }
  header { border-top:5px solid #207363; padding-top:20px; }
  h1 { font-size:clamp(2rem,5vw,3rem); letter-spacing:-.045em; margin:0 0 8px; }
  p { max-width:66ch; margin:8px 0 20px; }
  label { display:block; font-weight:650; margin-bottom:6px; }
  input { width:min(100%,420px); box-sizing:border-box; font:inherit; padding:10px 12px; border:1px solid #71877e; border-radius:6px; }
  input:focus-visible { outline:3px solid #207363; outline-offset:3px; }
  table { width:100%; border-collapse:collapse; background:white; margin-top:24px; }
  th,td { text-align:left; padding:12px 14px; border-bottom:1px solid #dce3df; }
  thead { background:#173f36; color:white; }
  code { font-size:1rem; }
  audio { width:min(100%,300px); vertical-align:middle; }
  .note { color:#425c53; font-size:.92rem; margin-top:24px; }
  [hidden] { display:none; }
  @media(max-width:540px) { th,td { padding:10px 6px; } audio { width:175px; } td:nth-child(2),th:nth-child(2) { display:none; } }
</style>
<header><h1>LAN Sound Preview</h1>
<p>28 short clips selected from the supplied server collection. Play a clip below; its keyword is what players type into chat.</p></header>
<label for="filter">Find a keyword</label>
<input type="search" id="filter" placeholder="moin, afk, bier..." autocomplete="off">
<table><thead><tr><th scope="col">Chat keyword</th><th scope="col">Duration</th><th scope="col">Listen</th></tr></thead><tbody>
__ROWS__
</tbody></table>
<p class="note">This page works offline when kept beside the files folder. No audio is uploaded. Technical loading has been checked; listening on actual game clients remains a separate check.</p>
<script>
const rows = [...document.querySelectorAll('tbody tr')];
document.querySelector('#filter').addEventListener('input', event => {
  const query=event.target.value.trim().toLowerCase();
  rows.forEach(row => row.hidden=!row.dataset.keyword.includes(query));
});
document.addEventListener('play',event=>{
  if(event.target.tagName==='AUDIO') document.querySelectorAll('audio').forEach(audio=>{ if(audio!==event.target) audio.pause(); });
},true);
</script>
</html>
'@
[IO.File]::WriteAllText((Join-Path $ContentDirectory 'Listen.html'),$template.Replace('__ROWS__',($rows -join "`n")),(New-Object Text.UTF8Encoding($false)))
