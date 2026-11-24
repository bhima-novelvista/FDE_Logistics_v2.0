<#
=====================================================================
 update_env.ps1 - adds the settings of newer project versions to your
 EXISTING .env on WINDOWS. Works in Windows PowerShell 5.1 and in
 PowerShell 7. (On a Mac or Linux use update_env.sh instead.)

 Run from the project folder:
   powershell -NoProfile -ExecutionPolicy Bypass -File .\legacy_system\update_env.ps1

 - Never changes or removes a setting that already has a value.
 - Adds only what is missing; fills a setting only if it is empty.
 - Asks for new passwords without showing them; creates random secrets
   itself. Never prints a password or secret.
 - Keeps the file format of create_env.ps1 (UTF-8 without BOM, Unix line
   endings) and the file's access rights.
 - Safe to run again: the second time it says "nothing to add".

 Allowed password characters: letters, digits and  _ @ % + = . -
=====================================================================
#>
$ErrorActionPreference = 'Stop'

$RootDir = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $RootDir '.env'

if (-not (Test-Path -LiteralPath $EnvFile)) {
    Write-Host "ERROR: $EnvFile not found."
    Write-Host "       Create it first (Step 1, D1):  powershell -NoProfile -ExecutionPolicy Bypass -File .\legacy_system\create_env.ps1"
    exit 1
}

# ---------------------------------------------------------------------
# The settings each version needs. One line per setting:
#   KEY|kind|text
#   kind = value    -> written as  KEY=text
#          password -> you are asked for it (text = what it is for)
#          secret   -> a random value is created (text = what it is for)
# A line starting with # is a section heading, written once.
# (Keep this list the same as in update_env.sh.)
# ---------------------------------------------------------------------
$Settings = @(
    '# ---- v2.0 Step 3: data integration layer (rule service database login) ----',
    'FDE_VIEWS_DB|value|fde_views',
    'FDE_AUDIT_DB|value|fde_audit',
    'RULE_SVC_USER|value|rule_svc',
    'RULE_SVC_PASSWORD|password|the rule service database login (rule_svc)',
    '# ---- v2.0 Step 4: rule service API (port, login keys, API users) ----',
    'RULE_API_PORT|value|8101',
    'JWT_SECRET|secret|the key that signs login tokens',
    'JWT_EXPIRE_MINUTES|value|30',
    'RULE_API_KEY|secret|the API key for machine clients',
    'API_USER_DISPATCHER_PASSWORD|password|the API user dispatcher',
    'API_USER_SUPERVISOR_PASSWORD|password|the API user supervisor',
    'API_USER_ADMIN_PASSWORD|password|the API user admin'
)

function ConvertTo-PlainText([System.Security.SecureString]$Secure) {
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function Read-NewPassword([string]$Purpose) {
    while ($true) {
        $first  = ConvertTo-PlainText (Read-Host -AsSecureString "New password for $Purpose (hidden)")
        $second = ConvertTo-PlainText (Read-Host -AsSecureString "Type it again")
        if ($first -cne $second) {
            Write-Host "  x The two entries are different. Please try again."
            continue
        }
        if ($first.Length -lt 8) {
            Write-Host "  x Use at least 8 characters. Please try again."
            continue
        }
        if ($first -cnotmatch '^[A-Za-z0-9_@%+=.-]+$') {
            Write-Host "  x Use only letters, digits and  _ @ % + = . -  Please try again."
            continue
        }
        return $first
    }
}

function New-Secret {
    # 64 random hexadecimal characters.
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return -join ($bytes | ForEach-Object { $_.ToString('x2') })
}

# ReadAllLines accepts both Unix and Windows line endings.
$lines = New-Object System.Collections.Generic.List[string]
foreach ($l in [System.IO.File]::ReadAllLines($EnvFile)) { $lines.Add($l) }

$changed = 0
$heading = ''
Write-Host "Updating $EnvFile"
Write-Host ''

foreach ($spec in $Settings) {
    if ($spec.StartsWith('#')) { $heading = $spec; continue }
    $parts = $spec -split '\|', 3
    $key = $parts[0]; $kind = $parts[1]; $text = $parts[2]

    $index = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].StartsWith("$key=", [System.StringComparison]::Ordinal)) { $index = $i; break }
    }
    if ($index -ge 0 -and $lines[$index].Length -gt ($key.Length + 1)) {
        Write-Host "  kept    $key (already set)"
        continue
    }

    switch ($kind) {
        'value'    { $val = $text }
        'password' { Write-Host ''; $val = Read-NewPassword $text }
        'secret'   { $val = New-Secret }
        default    { throw "Unknown kind '$kind' for $key" }
    }

    if ($index -ge 0) {
        # the setting exists but is empty: fill in that one line
        $lines[$index] = "$key=$val"
        Write-Host "  filled  $key (was empty)"
    }
    else {
        if ($heading -ne '' -and -not $lines.Contains($heading)) {
            $lines.Add('')
            $lines.Add($heading)
        }
        $lines.Add("$key=$val")
        Write-Host "  added   $key"
    }
    $changed++
}
Remove-Variable val -ErrorAction SilentlyContinue

Write-Host ''
if ($changed -eq 0) {
    Write-Host 'OK: nothing to add - .env already has every setting.'
}
else {
    # Writing into the existing file keeps its access rights (set by create_env.ps1).
    $content = ($lines -join "`n") + "`n"
    [System.IO.File]::WriteAllText($EnvFile, $content, (New-Object System.Text.UTF8Encoding($false)))
    Remove-Variable content -ErrorAction SilentlyContinue
    Write-Host "OK: $changed setting(s) added to .env (passwords and secrets not shown)."
}
Write-Host 'Settings in the file:'
Get-Content -LiteralPath $EnvFile |
    Where-Object { $_ -cmatch '^[A-Z_]+=' } |
    ForEach-Object { $_ -creplace '^([A-Z_]*(PASSWORD|SECRET|API_KEY))=.+$', '$1=******** (set)' }
