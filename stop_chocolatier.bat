@echo off
rem =========================================================
rem stop_chocolatier.bat
rem - ダブルクリックで、Chocolatier の画面（Edge の専用ウィンドウ）を閉じて、Backend と Frontend を止める
rem - start_chocolatier.bat で起動したウィンドウは、サーバーが止まると自動で閉じる
rem - 文字コードは Shift_JIS（start_chocolatier.bat と同じ理由）
rem =========================================================

echo Chocolatier を止めています...

rem ---------------------------------------------------------
rem ① PowerShell に渡す値を、環境変数に入れる
rem    - PowerShell のコマンドに日本語や記号を直接書かないため
rem    - CHOCO_DIR：このフォルダ（最後の「\」は取り除く）
rem    - CHOCO_EDGE_PROFILE：start_chocolatier.bat が使う、Edge の専用プロフィール
rem ---------------------------------------------------------
set "CHOCO_DIR=%~dp0"
set "CHOCO_DIR=%CHOCO_DIR:~0,-1%"
set "CHOCO_EDGE_PROFILE=%LOCALAPPDATA%\Chocolatier\EdgeProfile"

rem ---------------------------------------------------------
rem ② PowerShell で、画面とサーバーをまとめて止める
rem    - 時間がかからないように、PowerShell の起動もプログラムの一覧の取得も 1 回だけにする
rem    - ポートを調べるのは netstat を使う（Get-NetTCPConnection は 1 回 2 秒以上かかるため）
rem      Get-ListenPids：8000 番・3000 番を待ち受けているプログラムの番号（netstat の最後の列）
rem    - 各行は cmd がスペースでつないで 1 行にするので、命令の終わりには必ず「;」を付ける
rem    (1) 動いているプログラムの一覧から、止める対象を探す
rem        - 画面：専用プロフィールの Edge（いつものブラウザは閉じない）
rem        - サーバー：「サーバーを起動したコマンド」だけ（ほかのプロジェクトや、VS Code の補完などは止めない）
rem            起動バッチ：start_chocolatier.bat を含む
rem            Django   ：このフォルダの backend と runserver を含む（起動したウィンドウごと止める）
rem            React    ：このフォルダの frontend と、npm start か react-scripts を含む
rem        - $PID（この PowerShell 自身）は除く。探す条件の文字が自分のコマンドにも入っているため
rem    (2) 画面を強制的に閉じる
rem        - 普通に閉じても、Edge はウィンドウだけ消えて裏で動き続けるため、最初から強制的に止める
rem        - 「ページを復元しますか？」は、start_chocolatier.bat の --hide-crash-restore-bubble で出ないようにしている
rem    (3) サーバーを止める。taskkill /T：子プログラムもまとめて / /F：強制的に
rem    (4) 念のため、8000 番と 3000 番を待ち受けているプログラムも止める（ターミナルで手動で起動した場合など）
rem    (5) 8000 番・3000 番がまだ使われていたら、止めきれなかったとして 1 を返す
rem ---------------------------------------------------------
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$dir = $env:CHOCO_DIR.ToLower(); $edgeProfile = $env:CHOCO_EDGE_PROFILE.ToLower();" ^
  "$backend = Join-Path $dir 'backend'; $frontend = Join-Path $dir 'frontend';" ^
  "function Get-ListenPids { netstat -ano | Select-String ':(8000|3000)\s.*LISTENING' | ForEach-Object { ($_.Line -split '\s+')[-1] } | Sort-Object -Unique };" ^
  "$all = Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine };" ^
  "$edge = @($all | Where-Object { $_.Name -eq 'msedge.exe' -and $_.CommandLine.ToLower().Contains($edgeProfile) });" ^
  "$servers = @($all | Where-Object {" ^
  "  $cmd = $_.CommandLine.ToLower();" ^
  "  $cmd.Contains('start_chocolatier.bat') -or" ^
  "  ($cmd.Contains($backend) -and $cmd.Contains('runserver')) -or" ^
  "  ($cmd.Contains($frontend) -and ($cmd.Contains('npm start') -or $cmd.Contains('react-scripts')))" ^
  "});" ^
  "if ($edge) { Write-Host '  - window'; $edge | ForEach-Object { taskkill /T /F /PID $_.ProcessId 2>&1 | Out-Null } };" ^
  "foreach ($p in $servers) { Write-Host ('  - ' + $p.Name + ' (PID ' + $p.ProcessId + ')'); taskkill /T /F /PID $p.ProcessId 2>&1 | Out-Null };" ^
  "Get-ListenPids | ForEach-Object { taskkill /T /F /PID $_ 2>&1 | Out-Null };" ^
    "Start-Sleep -Milliseconds 500;" ^
  "if (Get-ListenPids) { exit 1 } else { exit 0 }"

rem ---------------------------------------------------------
rem ③ 結果を表示する
rem    - 止められたら、2 秒後に閉じる
rem    - 止めきれなかったら、キーを押すまで閉じない（メッセージを読めるように）
rem ---------------------------------------------------------
echo.
if errorlevel 1 (
  echo 止めきれませんでした。タスクバーの「Chocolatier Backend」「npm start」のウィンドウを閉じてください
  pause
) else (
  echo Chocolatier を止めました
  ping -n 3 127.0.0.1 >nul
)
