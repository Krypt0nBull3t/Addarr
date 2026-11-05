# Filename: install.ps1
# Author: Christian Blank (https://github.com/cyneric)
# Created Date: 2024-11-08
# Description: PowerShell installer script for Addarr, a Media Management Telegram Bot.
# License: MIT

# Installer script for Windows
$ErrorActionPreference = "Stop"

# Colors for output
$colors = @{
    Red = [System.ConsoleColor]::Red
    Green = [System.ConsoleColor]::Green
    Yellow = [System.ConsoleColor]::Yellow
    Blue = [System.ConsoleColor]::Blue
}

Write-Host @"

╔═══════════════════════════════════════╗
║           Addarr Installer            ║
║     Media Management Telegram Bot     ║
╚═══════════════════════════════════════╝
"@ -ForegroundColor $colors.Blue

# Check for required commands
function Test-Command {
    param($Command)
    
    if (!(Get-Command $Command -ErrorAction SilentlyContinue)) {
        Write-Host "Error: $Command is required but not installed." -ForegroundColor $colors.Red
        Write-Host "Please install $Command and try again."
        exit 1
    }
}

# Check requirements
Test-Command "python"
Test-Command "git"

# Create installation directory
$INSTALL_DIR = "$env:LOCALAPPDATA\Addarr"
Write-Host "`nInstalling Addarr to: $INSTALL_DIR" -ForegroundColor $colors.Yellow

if (Test-Path $INSTALL_DIR) {
    Write-Host "Installation directory already exists. Backing up..." -ForegroundColor $colors.Yellow
    $backupDir = "$INSTALL_DIR.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Move-Item $INSTALL_DIR $backupDir
}

# Clone repository
Write-Host "`nCloning repository..." -ForegroundColor $colors.Blue
try {
    git clone https://github.com/Krypt0nBull3t/Addarr.git $INSTALL_DIR
} catch {
    Write-Host "Failed to clone repository" -ForegroundColor $colors.Red
    exit 1
}

# Create virtual environment
Write-Host "`nCreating virtual environment..." -ForegroundColor $colors.Blue
Set-Location $INSTALL_DIR
python -m venv venv

# Activate virtual environment and install dependencies
Write-Host "`nInstalling dependencies..." -ForegroundColor $colors.Blue
& "$INSTALL_DIR\venv\Scripts\activate.ps1"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install dependencies" -ForegroundColor $colors.Red
    exit 1
}

# Create launcher script
$LAUNCHER = "$env:LOCALAPPDATA\Microsoft\WindowsApps\addarr.cmd"
@"
@echo off
call "$INSTALL_DIR\venv\Scripts\activate.bat"
python "$INSTALL_DIR\run.py" %*
"@ | Out-File -FilePath $LAUNCHER -Encoding ASCII

# Add installation directory to PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$env:LOCALAPPDATA\Microsoft\WindowsApps*") {
    [Environment]::SetEnvironmentVariable(
        "Path",
        "$userPath;$env:LOCALAPPDATA\Microsoft\WindowsApps",
        "User"
    )
}

# Warn about an older Addarr service (earlier versions of this script installed one)
$olderService = Get-Service -Name Addarr -ErrorAction SilentlyContinue
if ($olderService) {
    Write-Host "`nAn older Addarr Windows service exists. It runs with SYSTEM rights and will not start after this install." -ForegroundColor $colors.Yellow
    Write-Host "Remove it from an Administrator PowerShell:" -ForegroundColor $colors.Yellow
    Write-Host "sc.exe stop Addarr"
    Write-Host "sc.exe delete Addarr"
}

# Ask about starting Addarr at logon
$taskInstalled = $false
Write-Host "`nWould you like Addarr to start automatically when you log on? [y/N]" -ForegroundColor $colors.Yellow
$autoStart = Read-Host
if ($autoStart -eq 'y' -or $autoStart -eq 'Y') {
    # Setup writes config.yaml, and the bot cannot start without it
    Write-Host "`nRunning setup..." -ForegroundColor $colors.Blue
    & "$INSTALL_DIR\venv\Scripts\python.exe" "$INSTALL_DIR\run.py" --setup

    if (-not (Test-Path "$INSTALL_DIR\config.yaml")) {
        Write-Host "`nSetup did not create config.yaml, so the logon task is not installed." -ForegroundColor $colors.Red
        Write-Host "Run 'addarr --setup', then run this installer again."
    } else {
        # The task runs as the installing user without elevation
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
        $python = "$INSTALL_DIR\venv\Scripts\python.exe"
        $action = New-ScheduledTaskAction -Execute $python -Argument "`"$INSTALL_DIR\run.py`"" -WorkingDirectory $INSTALL_DIR
        $trigger = New-ScheduledTaskTrigger -AtLogOn -User $identity
        $principal = New-ScheduledTaskPrincipal -UserId $identity -LogonType Interactive -RunLevel Limited
        $settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

        # Replace the task of an earlier install
        Unregister-ScheduledTask -TaskName Addarr -Confirm:$false -ErrorAction SilentlyContinue
        Register-ScheduledTask -TaskName Addarr -Description "Telegram bot for media management through Radarr, Sonarr, and Lidarr" -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
        $taskInstalled = $true
        Write-Host "✓ Addarr will start when $identity logs on" -ForegroundColor $colors.Green

        # Ask about starting now
        Write-Host "`nWould you like to start Addarr now? [y/N]" -ForegroundColor $colors.Yellow
        $startNow = Read-Host
        if ($startNow -eq 'y' -or $startNow -eq 'Y') {
            Start-ScheduledTask -TaskName Addarr
            Write-Host "✓ Addarr started" -ForegroundColor $colors.Green
        }
        Write-Host "`nYou can manage the task with:" -ForegroundColor $colors.Blue
        Write-Host "Start-ScheduledTask -TaskName Addarr"
        Write-Host "Stop-ScheduledTask -TaskName Addarr"
        Write-Host "Get-ScheduledTask -TaskName Addarr"
    }
}

Write-Host "`nInstallation complete!" -ForegroundColor $colors.Green
if ($taskInstalled) {
    Write-Host "`nSetup is done. Addarr starts automatically when you log on." -ForegroundColor $colors.Yellow
} else {
    Write-Host "`nTo get started:" -ForegroundColor $colors.Yellow
    Write-Host "1. Run initial setup:" -NoNewline
    Write-Host " addarr (on first run, setup wizard will start automatically)" -ForegroundColor $colors.Blue
    Write-Host "2. Start the bot:" -NoNewline
    Write-Host " addarr" -ForegroundColor $colors.Blue
}
Write-Host "`nFor more information, visit: " -NoNewline
Write-Host "https://github.com/Krypt0nBull3t/Addarr/wiki" -ForegroundColor $colors.Blue

# Refresh environment variables in current session
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")