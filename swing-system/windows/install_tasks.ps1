# Registers two Windows scheduled tasks for the current user.
#  - "SwingSystem Nightly": weekdays 6:30 pm (NSE data is complete by then)
#  - "SwingSystem Weekly" : Saturdays 10:00 am (self-improvement session)
# StartWhenAvailable = if the PC was off at that time, the job runs as soon as it is back on (catch-up).
$root = Split-Path -Parent $PSScriptRoot
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit (New-TimeSpan -Hours 4) -MultipleInstances IgnoreNew

$a1 = New-ScheduledTaskAction -Execute "$root\windows\run_nightly.bat" -WorkingDirectory $root
$t1 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 6:30pm
Register-ScheduledTask -TaskName "SwingSystem Nightly" -Action $a1 -Trigger $t1 -Settings $settings -Force | Out-Null

$a2 = New-ScheduledTaskAction -Execute "$root\windows\run_weekly.bat" -WorkingDirectory $root
$t2 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At 10:00am
Register-ScheduledTask -TaskName "SwingSystem Weekly" -Action $a2 -Trigger $t2 -Settings $settings -Force | Out-Null

# Telegram tip-check bot: starts when you log in, restarts itself if it ever stops.
$s3 = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
      -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
$a3 = New-ScheduledTaskAction -Execute "$root\.venv\Scripts\pythonw.exe" -Argument "scripts\run_bot.py" -WorkingDirectory $root
$t3 = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "SwingSystem Telegram Bot" -Action $a3 -Trigger $t3 -Settings $s3 -Force | Out-Null
Start-ScheduledTask -TaskName "SwingSystem Telegram Bot"
Write-Host "Scheduled tasks installed: 'SwingSystem Nightly' (weekdays 6:30 pm) 'SwingSystem Weekly' (Saturday 10 am) and 'SwingSystem Telegram Bot' (always on while you are logged in)."
