$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$work = 'C:\VMSetup'
New-Item -ItemType Directory -Force -Path $work | Out-Null
Start-Transcript -Path "$work\setup.log" -Append

function Set-SetupState([string]$stage, [string]$state = 'running', [string]$message = '') {
    @{ stage = $stage; state = $state; message = $message; time = (Get-Date).ToString('o') } |
        ConvertTo-Json | Set-Content "$work\status.json"
    Write-Host "$state - $stage - $message"
}

function Get-CheckedDownload([string]$uri, [string]$path, [string]$sha256) {
    Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $path
    if ((Get-FileHash -Algorithm SHA256 $path).Hash -ne $sha256) {
        throw "SHA-256 mismatch: $path"
    }
}

function Assert-Signature([string]$path) {
    if ((Get-AuthenticodeSignature $path).Status -ne 'Valid') {
        throw "Invalid Authenticode signature: $path"
    }
}

try {
    Set-SetupState 'guest-agent'
    Assert-Signature 'C:\OEM\qemu-ga-x86_64.msi'
    $agent = Start-Process msiexec.exe -ArgumentList '/i C:\OEM\qemu-ga-x86_64.msi /qn /norestart /l*v C:\VMSetup\guest-agent.log' -Wait -PassThru
    if ($agent.ExitCode -notin @(0, 3010)) { throw "Guest-agent install failed: $($agent.ExitCode)" }
    Start-Service QEMU-GA

    # Restore normal protections changed by the upstream unattended image.
    Set-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' -Name EnableLUA -Value 1
    $updates = 'HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings'
    foreach ($name in @('FlightSettingsMaxPauseDays', 'PauseFeatureUpdatesStartTime', 'PauseFeatureUpdatesEndTime', 'PauseQualityUpdatesStartTime', 'PauseQualityUpdatesEndTime', 'PauseUpdatesStartTime', 'PauseUpdatesExpiryTime')) {
        if (Get-ItemProperty -Path $updates -Name $name -ErrorAction SilentlyContinue) {
            Remove-ItemProperty -Path $updates -Name $name
        }
    }
    Set-SmbClientConfiguration -EnableInsecureGuestLogons $false -RequireSecuritySignature $true -Confirm:$false

    Set-SetupState 'office-download'
    Get-CheckedDownload 'https://download.microsoft.com/download/6c1eeb25-cf8b-41d9-8d0d-cc1dbc032140/officedeploymenttool_20430-20146.exe' "$work\odt.exe" 'af1594121ab610cd8abc3dd6ff0a504e0cbc6ce54372e5c3813926352d1179c6'
    Assert-Signature "$work\odt.exe"
    $extract = Start-Process "$work\odt.exe" -ArgumentList "/quiet /extract:$work\ODT" -Wait -PassThru
    if ($extract.ExitCode -ne 0) { throw "Office deployment tool extraction failed: $($extract.ExitCode)" }
    Assert-Signature "$work\ODT\setup.exe"

    Set-SetupState 'office-install'
    $office = Start-Process "$work\ODT\setup.exe" -ArgumentList '/configure C:\OEM\office.xml' -Wait -PassThru
    if ($office.ExitCode -notin @(0, 3010)) { throw "Office installation failed: $($office.ExitCode)" }

    Set-SetupState 'activation-download'
    Get-CheckedDownload 'https://raw.githubusercontent.com/massgravel/Microsoft-Activation-Scripts/6401d2f36975dc07bcb6d22ea823a8498a75ec01/MAS/All-In-One-Version-KL/MAS_AIO.cmd' "$work\MAS.cmd" '850f979665fb93999acae93f4790c1ff8ed2041532060b7966a121c2d29a0bfa'
    Set-SetupState 'windows-activation'
    $windows = Start-Process cmd.exe -ArgumentList '/d /c C:\VMSetup\MAS.cmd /HWID /HWID-NoEditionChange' -Wait -PassThru
    if ($windows.ExitCode -ne 0) { throw "Windows activation failed: $($windows.ExitCode)" }
    Set-SetupState 'office-activation'
    $activation = Start-Process cmd.exe -ArgumentList '/d /c C:\VMSetup\MAS.cmd /Z-Office /Z-SCID' -Wait -PassThru
    if ($activation.ExitCode -ne 0) { throw "Office activation failed: $($activation.ExitCode)" }

    Set-SetupState 'verification'
    $licenses = @(Get-CimInstance SoftwareLicensingProduct | Where-Object { $_.PartialProductKey -and $_.LicenseStatus -eq 1 })
    if (-not ($licenses | Where-Object ApplicationID -eq '55c92734-d682-4d71-983e-d6ec3f16059f')) { throw 'Windows does not report a licensed status.' }
    if (-not ($licenses | Where-Object ApplicationID -eq '0ff1ce15-a989-479d-af46-f275c6370663')) { throw 'Office does not report a licensed status.' }
    $licenses | Select-Object Name, Description, LicenseStatus | ConvertTo-Json | Set-Content "$work\licenses.json"
    if (-not (Test-Path 'C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE')) { throw 'Word executable is missing.' }
    Set-SetupState 'ready' 'complete'
} catch {
    Set-SetupState 'failed' 'failed' $_.Exception.Message
    throw
} finally {
    Stop-Transcript
}
