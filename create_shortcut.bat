@echo off
rem =========================================================
rem create_shortcut.bat
rem - ダブルクリックで、デスクトップに 2 つのショートカットを作る
rem   - 「Chocolatier」     ：start_chocolatier.bat を起動する（アイコンは chocolatier.ico）
rem   - 「Chocolatier 終了」：stop_chocolatier.bat を起動する（アイコンは Windows の電源ボタン）
rem - bat ファイル自体にはアイコンを付けられないので、アイコン付きのショートカットを作る
rem - 同じ名前のショートカットがあれば、上書きする
rem   → リポジトリを移動したときや、パソコンを替えたときは、もう一度ダブルクリックすれば直る
rem - 文字コードは Shift_JIS（start_chocolatier.bat と同じ理由）
rem =========================================================

rem ---------------------------------------------------------
rem ① この bat があるフォルダ（chocolatier\）を、PowerShell に渡すために環境変数に入れる
rem    - %~dp0 の最後の「\」は取り除く（ショートカットの「作業フォルダー」に使うため）
rem ---------------------------------------------------------
set "CHOCO_DIR=%~dp0"
set "CHOCO_DIR=%CHOCO_DIR:~0,-1%"
rem    - 終了用のショートカットの名前も環境変数で渡す（PowerShell のコマンドに日本語を直接書くと、文字化けするため）
set "CHOCO_STOP_NAME=Chocolatier 終了"

rem ---------------------------------------------------------
rem ② 必要なファイルがそろっているか確認する
rem ---------------------------------------------------------
for %%F in (start_chocolatier.bat stop_chocolatier.bat chocolatier.ico) do (
  if not exist "%CHOCO_DIR%\%%F" (
    echo %%F が見つかりません。このファイルと同じフォルダに置いてください
    pause
    exit /b 1
  )
)

rem ---------------------------------------------------------
rem ③ PowerShell でショートカットを作る
rem    - デスクトップの場所は Windows に聞く（OneDrive のデスクトップでも正しく作れる）
rem    - 起動用は WindowStyle=7（最小化）：黒いウィンドウが一瞬出ないように
rem    - 終了用は WindowStyle=1（普通）：「止めました」の表示が見えるように
rem    - shell32.dll の 27 番：Windows に入っている電源ボタンのアイコン
rem ---------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$dir = $env:CHOCO_DIR;" ^
  "$desktop = [Environment]::GetFolderPath('Desktop');" ^
  "$shell = New-Object -ComObject WScript.Shell;" ^
  "function New-ChocoShortcut($name, $bat, $icon, $description, $window) {" ^
  "  $lnk = Join-Path $desktop ($name + '.lnk');" ^
  "  $s = $shell.CreateShortcut($lnk);" ^
  "  $s.TargetPath = Join-Path $dir $bat;" ^
  "  $s.WorkingDirectory = $dir;" ^
  "  $s.IconLocation = $icon;" ^
  "  $s.WindowStyle = $window;" ^
  "  $s.Description = $description;" ^
  "  $s.Save();" ^
  "  Write-Host ('Created: ' + $lnk)" ^
  "}" ^
  "New-ChocoShortcut 'Chocolatier' 'start_chocolatier.bat' ((Join-Path $dir 'chocolatier.ico') + ',0') 'Start Chocolatier' 7;" ^
  "New-ChocoShortcut $env:CHOCO_STOP_NAME 'stop_chocolatier.bat' ($env:SystemRoot + '\System32\shell32.dll,27') 'Stop Chocolatier' 1"

rem ---------------------------------------------------------
rem ④ 結果を表示して、キーを押すまで待つ
rem ---------------------------------------------------------
if errorlevel 1 (
  echo ショートカットを作れませんでした
) else (
  echo デスクトップに「Chocolatier」と「Chocolatier 終了」のショートカットを作りました
)
pause
