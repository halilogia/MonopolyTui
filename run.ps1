# MonopolyTui başlatıcı: Windows Terminal'de 125x38 yeni pencere açar (yoksa mevcut konsolda çalışır).
$dir = $PSScriptRoot
Set-Location $dir
if (Get-Command wt -ErrorAction SilentlyContinue) {
    Start-Process wt -ArgumentList @('-w', 'new', '--size', '125,38', '-d', "$dir.", 'python', 'main.py')
} else {
    python main.py
}
