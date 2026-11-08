[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Command,
    [string]$ServerDirectory,
    [System.Net.IPAddress]$ServerAddress = '127.0.0.1',
    [ValidateRange(1,65535)][int]$Port = 27025
)

$ErrorActionPreference = 'Stop'
$serverRoot = if ($ServerDirectory) { (Resolve-Path -LiteralPath $ServerDirectory).Path } else { Join-Path (Split-Path -Parent $PSScriptRoot) 's' }
if ($ServerDirectory) {
    $localConfig = Get-Content -LiteralPath (Join-Path $serverRoot 'cstrike\server.cfg') -Raw
    $credentials=[regex]::Matches($localConfig,'(?m)^[ \t]*rcon_password[ \t]+"([^"\r\n]+)"[ \t]*(?://[^\r\n]*)?\r?$')
    if ($credentials.Count -ne 1) { throw 'Expected one quoted local RCON password in server.cfg.' }
    $password = $credentials[0].Groups[1].Value
    $localConfig = $null
} else {
    $password = (Get-Content -LiteralPath (Join-Path $serverRoot 'test-rcon.secret') -Raw).Trim()
}
if ([string]::IsNullOrWhiteSpace($password) -or $password -match '[^\x20-\x7e]|"') { throw 'Invalid local control credential: use nonempty ASCII text without quotes or control characters.' }

$socket = New-Object System.Net.Sockets.UdpClient
$socket.Client.ReceiveTimeout = 1500
$localAddresses=@('127.0.0.1')+@(Get-NetIPAddress -AddressFamily IPv4 | Select-Object -ExpandProperty IPAddress)
if($ServerAddress.ToString() -notin $localAddresses) { throw 'This operator helper only sends control commands to this PC.' }
$socket.Connect($ServerAddress.ToString(),$Port)
try {
    [byte[]]$request = @(255,255,255,255) + [System.Text.Encoding]::ASCII.GetBytes('challenge rcon') + @(0)
    [void]$socket.Send($request,$request.Length)
    $endpoint = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Any,0)
    $challengeReply = [System.Text.Encoding]::ASCII.GetString($socket.Receive([ref]$endpoint))
    if ($challengeReply -notmatch 'challenge rcon ([0-9]+)') { throw 'The test server did not issue an RCON challenge.' }
    $challenge = $Matches[1]
    $commandText = 'rcon ' + $challenge + ' "' + $password + '" ' + $Command
    [byte[]]$request = @(255,255,255,255) + [System.Text.Encoding]::ASCII.GetBytes($commandText) + @(0)
    [void]$socket.Send($request,$request.Length)
    for ($packet = 0; $packet -lt 20; $packet++) {
        try { $response = $socket.Receive([ref]$endpoint) } catch [System.Net.Sockets.SocketException] {
            if ($_.Exception.SocketErrorCode -eq [System.Net.Sockets.SocketError]::TimedOut) { break }
            throw
        }
        $offset = if ($response.Length -gt 4 -and $response[4] -eq 108) { 5 } else { 4 }
        if ($response.Length -gt $offset) {
            $responseText = [System.Text.Encoding]::ASCII.GetString($response,$offset,$response.Length - $offset).Trim([char]0)
            if ($responseText -match 'Bad rcon_password|Bad challenge') {
                throw 'The test server rejected the RCON credentials or challenge.'
            }
            $responseText
        }
    }
} finally {
    $socket.Close()
    $password = $null
}
