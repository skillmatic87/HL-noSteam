[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Command
)

$ErrorActionPreference = 'Stop'
$serverRoot = Join-Path (Split-Path -Parent $PSScriptRoot) 's'
$password = (Get-Content -LiteralPath (Join-Path $serverRoot 'test-rcon.secret') -Raw).Trim()
if ($password -notmatch '^[a-f0-9]{20}$') { throw 'Invalid local test credential.' }

$socket = New-Object System.Net.Sockets.UdpClient
$socket.Client.ReceiveTimeout = 1500
$socket.Connect('127.0.0.1',27025)
try {
    [byte[]]$request = @(255,255,255,255) + [System.Text.Encoding]::ASCII.GetBytes('challenge rcon') + @(0)
    [void]$socket.Send($request,$request.Length)
    $endpoint = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Any,0)
    $challengeReply = [System.Text.Encoding]::ASCII.GetString($socket.Receive([ref]$endpoint))
    if ($challengeReply -notmatch 'challenge rcon ([0-9]+)') { throw 'The test server did not issue an RCON challenge.' }
    $challenge = $Matches[1]
    $commandText = 'rcon ' + $challenge + ' ' + $password + ' ' + $Command
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
