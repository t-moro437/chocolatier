@echo off
rem ---------------------------------------------------------
rem 準備：このウィンドウを最小化する
rem    - bat は自分のウィンドウを最小化できないので、「最小化で自分自身をもう一度起動して、今のウィンドウは閉じる」
rem    - 2 回目の起動には目印の min を付けて、また起動し直さないようにする
rem ---------------------------------------------------------
if not "%~1"=="min" (
  start "Chocolatier" /min "%~f0" min
  exit /b
)

rem =========================================================
rem start_chocolatier.bat
rem - ダブルクリックで、Chocolatier の Backend と Frontend を起動して、スナップの画面を Edge の専用ウィンドウで開く
rem - サーバーはそれぞれ別のウィンドウで、最小化して動く
rem - 止めるときは stop_chocolatier.bat をダブルクリックする（サーバーが止まると、ウィンドウも自動で閉じる）
rem - %~dp0 は、この bat ファイルがあるフォルダ（chocolatier\）
rem - 文字コードは Shift_JIS（cmd は bat ファイルを Shift_JIS で読むため。UTF-8 だと日本語が化けて誤動作する）
rem =========================================================

rem ---------------------------------------------------------
rem ① Backend（Django）を起動する
rem    - すでに 8000 番ポートが使われていたら、起動済みとみなして飛ばす
rem      （2 回ダブルクリックしても、サーバーが二重に起動しないように）
rem    - venv を有効にしてから runserver する
rem    - cmd /c：サーバーが止まったら、ウィンドウも閉じる
rem      （エラーで止まったときも閉じるので、エラーを見たいときはターミナルで手動で起動する）
rem ---------------------------------------------------------
netstat -ano | findstr /r /c:":8000 .*LISTENING" >nul
if errorlevel 1 (
  echo Backend を起動します（http://localhost:8000）
  start "Chocolatier Backend" /min cmd /c "cd /d "%~dp0backend" && call venv\Scripts\activate.bat && python manage.py runserver"
) else (
  echo Backend はすでに起動しています
)

rem ---------------------------------------------------------
rem ② Frontend（React）を起動する
rem    - 3000 番ポートで同じように確認する
rem    - BROWSER=none：npm start が自分でブラウザを開かないようにする
rem      （③ でスナップの画面を開くので、タブが 2 つ開かないように）
rem ---------------------------------------------------------
netstat -ano | findstr /r /c:":3000 .*LISTENING" >nul
if errorlevel 1 (
  echo Frontend を起動します（http://localhost:3000）
  start "Chocolatier Frontend" /min cmd /c "cd /d "%~dp0frontend" && set BROWSER=none&& npm start"
) else (
  echo Frontend はすでに起動しています
)

rem ---------------------------------------------------------
rem ③ Frontend の準備ができるまで待ってから、スナップの画面を開く
rem    - 1 秒ごとに 3000 番ポートを確認する。最大 300 秒（5 分）待つ
rem      （npm start は開発用のサーバーで、起動に 2 分ほどかかることがある）
rem    - ping -n 2 は「約 1 秒待つ」ための書き方（timeout はウィンドウの状態によって動かないことがあるため）
rem    - ログインしていなければ、画面がサインインに移動する
rem ---------------------------------------------------------
echo 画面の準備ができるまで待っています（2 分ほどかかることがあります）...
set /a waited=0
:wait_frontend
netstat -ano | findstr /r /c:":3000 .*LISTENING" >nul
if not errorlevel 1 goto open_browser
if %waited% geq 300 goto timeout_frontend
ping -n 2 127.0.0.1 >nul
set /a waited+=1
goto wait_frontend

:open_browser
echo スナップの画面を開きます
rem Edge の場所（64 ビット版の Windows では Program Files (x86) に入っている）
rem - ( ) を含むパスなので、if のカッコの外で、引用符で囲んで代入する
set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE%" set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
rem - --app：アドレスバーやタブのない、アプリのような専用ウィンドウで開く
rem - --user-data-dir：Chocolatier 専用のプロフィールを使う
rem   → いつものブラウザとは別のプログラムになるので、stop_chocolatier.bat でこのウィンドウだけを閉じられる
rem   → ログイン情報（Cookie）も別になるので、最初の 1 回だけ、このウィンドウでログインし直す
rem - --hide-crash-restore-bubble：stop_chocolatier.bat で強制的に閉じても、次に開いたとき「ページを復元しますか？」を出さない
rem - Edge が見つからなければ、いつものブラウザで開く
if exist "%EDGE%" (
  start "" "%EDGE%" --app=http://localhost:3000/snaps --user-data-dir="%LOCALAPPDATA%\Chocolatier\EdgeProfile" --no-first-run --no-default-browser-check --hide-crash-restore-bubble
) else (
  start "" http://localhost:3000/snaps
)
ping -n 3 127.0.0.1 >nul
rem このウィンドウは最小化で起動し直したもの（cmd /K）なので、exit /b ではなく exit で閉じる
exit

rem ---------------------------------------------------------
rem ④ 時間切れ
rem    - このウィンドウは最小化されていて気づけないので、ポップアップで知らせる
rem ---------------------------------------------------------
:timeout_frontend
powershell -NoProfile -Command "Add-Type -AssemblyName PresentationFramework; [System.Windows.MessageBox]::Show('5 分待っても画面の準備ができませんでした。タスクバーの「Chocolatier Frontend」のウィンドウを確認してください', 'Chocolatier') | Out-Null"
exit
