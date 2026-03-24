# stdout.log 원본 확인
$stdoutLog = "C:\Users\haj\projects\Subagent-Orchestrator\subagent-runs\mixed\test-3way-final\claude-synthesis.stdout.log"
$bytes = [System.IO.File]::ReadAllBytes($stdoutLog)
Write-Output ("stdout.log length: " + $bytes.Length)
Write-Output ("First 100 hex: " + [BitConverter]::ToString($bytes[0..([Math]::Min(99, $bytes.Length - 1))]))

$hasBOM = ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)
Write-Output ("Has UTF-8 BOM: " + $hasBOM)

$utf8Text = [System.Text.Encoding]::UTF8.GetString($bytes)
Write-Output ("UTF-8 (first 300): " + $utf8Text.Substring(0, [Math]::Min(300, $utf8Text.Length)))

Write-Output ""
Write-Output "--- 0x3F (?) count in last.txt ---"
$lastBytes = [System.IO.File]::ReadAllBytes("C:\Users\haj\projects\Subagent-Orchestrator\subagent-runs\mixed\test-3way-final\claude-synthesis.last.txt")
$qCount = ($lastBytes | Where-Object { $_ -eq 0x3F }).Count
Write-Output ("0x3F count: $qCount out of $($lastBytes.Length) bytes")

Write-Output ""
Write-Output "--- 0x3F (?) count in stdout.log ---"
$qCount2 = ($bytes | Where-Object { $_ -eq 0x3F }).Count
Write-Output ("0x3F count: $qCount2 out of $($bytes.Length) bytes")

# gemini 파일도 확인
Write-Output ""
Write-Output "--- gemini-mechanics.last.txt ---"
$gemBytes = [System.IO.File]::ReadAllBytes("C:\Users\haj\projects\Subagent-Orchestrator\subagent-runs\mixed\test-3way-final\gemini-mechanics.last.txt")
Write-Output ("Length: " + $gemBytes.Length)
$gemUtf8 = [System.Text.Encoding]::UTF8.GetString($gemBytes)
Write-Output ("UTF-8: " + $gemUtf8.Substring(0, [Math]::Min(200, $gemUtf8.Length)))
