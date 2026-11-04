$ErrorActionPreference='Stop'
$helper=Join-Path $PSScriptRoot 'Get-CS15LANAddress.ps1'
function Get-NetIPConfiguration { $adapters }
$adapters=@(
    [pscustomobject]@{IPv4Address=@([pscustomobject]@{IPAddress='169.254.123.3'});IPv4DefaultGateway=$null},
    [pscustomobject]@{IPv4Address=@([pscustomobject]@{IPAddress='192.168.178.41'});IPv4DefaultGateway=[pscustomobject]@{NextHop='192.168.178.1'}}
)
if((& $helper) -cne '192.168.178.41') { throw 'Incorrect adapter selected beside a TAP link-local address.' }
if((& $helper -BindAddress '192.168.178.41') -cne '192.168.178.41') { throw 'Assigned explicit address was rejected.' }
foreach($address in @('169.254.123.3','127.0.0.1','192.168.178.99','bad-address')) {
    $rejected=$false
    try { $null=& $helper -BindAddress $address } catch { $rejected=$true }
    if(-not $rejected) { throw ('Unsafe or unassigned bind address accepted: '+$address) }
}
$adapters[1].IPv4DefaultGateway=$null
if((& $helper) -cne '192.168.178.41') { throw 'An isolated LAN without a gateway should work.' }
$adapters+= [pscustomobject]@{IPv4Address=@([pscustomobject]@{IPAddress='10.1.2.3'});IPv4DefaultGateway=$null}
$rejected=$false
try { $null=& $helper } catch { $rejected=$true }
if(-not $rejected) { throw 'Ambiguous adapters must require an explicit choice.' }
'PASS: TAP exclusion, gateway selection, isolated LAN, explicit address validation and ambiguous adapters.'
