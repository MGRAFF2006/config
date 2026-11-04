# Run elevated inside Windows after installing the matching signed IDD package.
$ErrorActionPreference = 'Stop'
$key = 'HKLM:\SOFTWARE\LookingGlass\IDD'
if (-not (Test-Path $key)) {
    New-Item -Path $key | Out-Null
}

# Match the installer's precise value permissions for the UMDF driver and helper.
# Recreating an existing key with New-Item -Force removes those explicit ACLs.
$acl = Get-Acl $key
foreach ($value in @('S-1-5-84-0-0-0-0-0', 'S-1-5-4')) {
    $sid = New-Object System.Security.Principal.SecurityIdentifier($value)
    $rule = New-Object System.Security.AccessControl.RegistryAccessRule(
        $sid,
        [System.Security.AccessControl.RegistryRights]'QueryValues,SetValue',
        [System.Security.AccessControl.AccessControlType]::Allow)
    $acl.SetAccessRule($rule)
}
Set-Acl -Path $key -AclObject $acl

foreach ($setting in @{ DefaultRefresh = 60; NoGPU = 1; ExclusiveMonitor = 1; LogStatistics = 0 }.GetEnumerator()) {
    New-ItemProperty -Path $key -Name $setting.Key -PropertyType DWord -Value $setting.Value -Force | Out-Null
}
Restart-Service LGIddHelper
