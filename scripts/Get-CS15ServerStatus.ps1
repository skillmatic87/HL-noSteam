[CmdletBinding()]
param(
    [string]$ServerAddress = '127.0.0.1',
    [ValidateRange(1,65535)][int]$Port = 27015,
    [ValidateRange(100,10000)][int]$TimeoutMilliseconds = 2000
)

$ErrorActionPreference = 'Stop'
$socket = New-Object System.Net.Sockets.UdpClient
$socket.Client.ReceiveTimeout = $TimeoutMilliseconds
try {
    $socket.Connect($ServerAddress, $Port)
    [byte[]]$request = @(255,255,255,255) + [System.Text.Encoding]::ASCII.GetBytes('details') + @(0)
    [void]$socket.Send($request, $request.Length)
    $endpoint = New-Object System.Net.IPEndPoint([System.Net.IPAddress]::Any,0)
    [byte[]]$reply = $socket.Receive([ref]$endpoint)
    if ($reply.Length -lt 5 -or $reply[4] -ne 109 -or @($reply[0..3] | Where-Object { $_ -ne 255 }).Count -ne 0) {
        throw 'The endpoint did not return a legacy GoldSrc details response.'
    }
    $offset = 5
    $strings = @()
    foreach ($field in 1..5) {
        $start = $offset
        while ($offset -lt $reply.Length -and $reply[$offset] -ne 0) { $offset++ }
        if ($offset -ge $reply.Length) { throw 'The server returned a truncated response.' }
        $strings += [System.Text.Encoding]::ASCII.GetString($reply, $start, $offset - $start)
        $offset++
    }
    if ($offset + 3 -gt $reply.Length) { throw 'The server response is missing player counts.' }
    [pscustomobject]@{
        Address = $strings[0]
        Name = $strings[1]
        Map = $strings[2]
        GameDirectory = $strings[3]
        GameDescription = $strings[4]
        Players = [int]$reply[$offset]
        MaximumPlayers = [int]$reply[$offset + 1]
        Protocol = [int]$reply[$offset + 2]
    }
} finally {
    $socket.Close()
}
