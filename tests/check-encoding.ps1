$file = "C:\Users\haj\projects\Subagent-Orchestrator\subagent-runs\mixed\test-3way-final\claude-synthesis.last.txt"
$bytes = [System.IO.File]::ReadAllBytes($file)
Write-Output ("Length: " + $bytes.Length)
Write-Output ("First 100 hex: " + [BitConverter]::ToString($bytes[0..([Math]::Min(99, $bytes.Length - 1))]))

$hasBOM = ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)
Write-Output ("Has UTF-8 BOM: " + $hasBOM)

# UTF-8로 읽기 시도
$utf8Text = [System.Text.Encoding]::UTF8.GetString($bytes)
Write-Output ("UTF-8 decode: " + $utf8Text.Substring(0, [Math]::Min(200, $utf8Text.Length)))

# CP949로 읽기 시도
$cp949Text = [System.Text.Encoding]::GetEncoding(949).GetString($bytes)
Write-Output ("CP949 decode: " + $cp949Text.Substring(0, [Math]::Min(200, $cp949Text.Length)))

# stdout 원본 파일도 확인
$stdoutFile = "C:\Users\haj\projects\Subagent-Orchestrator\subagent-runs\mixed\test-3way-final\claude-synthesis.stdout"
if (Test-Path $stdoutFile) {
    $stdoutBytes = [System.IO.File]::ReadAllBytes($stdoutFile)
    Write-Output ("`nStdout file length: " + $stdoutBytes.Length)
    Write-Output ("Stdout first 100 hex: " + [BitConverter]::ToString($stdoutBytes[0..([Math]::Min(99, $stdoutBytes.Length - 1))]))
} else {
    Write-Output ("`nNo stdout file found at: $stdoutFile")
    # 디렉토리 내 모든 파일 나열
    Get-ChildItem "C:\Users\haj\projects\Subagent-Orchestrator\subagent-runs\mixed\test-3way-final\" | ForEach-Object { Write-Output $_.Name }
}
