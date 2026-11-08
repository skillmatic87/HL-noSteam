[CmdletBinding()]
param([string]$BindAddress)
$ErrorActionPreference='Stop'
$candidates=@(foreach($adapter in Get-NetIPConfiguration) {
    foreach($address in $adapter.IPv4Address) {
        if($address.IPAddress -and $address.IPAddress -notmatch '^(127\.|169\.254\.|0\.)') {
            [pscustomobject]@{Address=[string]$address.IPAddress;Gateway=[bool]$adapter.IPv4DefaultGateway}
        }
    }
})
$assigned=@($candidates | Select-Object -ExpandProperty Address)
if($BindAddress) {
    $parsed=$null
    if(-not [Net.IPAddress]::TryParse($BindAddress,[ref]$parsed) -or $parsed.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or $BindAddress -notin $assigned) {
        throw 'BindAddress must be an assigned LAN IPv4 address, excluding loopback and link-local addresses.'
    }
    return $BindAddress
}
$preferred=@($candidates | Where-Object Gateway)
if(-not $preferred.Count) { $preferred=$candidates }
$addresses=@($preferred | Select-Object -ExpandProperty Address | Sort-Object -Unique)
if($addresses.Count -ne 1) { throw 'Cannot select one LAN adapter. Configure with -BindAddress and the intended LAN IPv4 address.' }
return $addresses[0]
