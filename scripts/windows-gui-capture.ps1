New-Item -ItemType Directory -Force capture | Out-Null
$log = Join-Path $PWD "capture\launch-and-capture.log"
function Note([string]$message) {
  "$(Get-Date -Format o) $message" | Tee-Object -FilePath $log -Append
}

Note "PACKAGE_COMMIT=593019d7355f8dd5dc769ae6735e05ec425e8138"
Note "CAPTURE_COMMIT=$env:GITHUB_SHA"
Note "COORDINATE_TESTS=first-five-tabs-real-clicks; last-two-native-Ctrl-PageDown; full-width-layout-NOT_TESTED"
Note "VISUAL_CONFORMITY=NOT_EVALUATED"
Note "MESA_SOURCE=https://github.com/pal1000/mesa-dist-win/releases/tag/26.2.6"
Note "MESA_VARIANT=release-mingw"
Note "MESA_LICENSE=MIT"
Note "RUNNER_NAME=$env:RUNNER_NAME"
(query user 2>&1 | Out-String) | Tee-Object -FilePath $log -Append

$outer = Get-ChildItem package-artifact -Filter "LeStudio-Windows-*.zip" -File
if ($outer.Count -ne 1 -or $outer.Name -ne "LeStudio-Windows-593019d7.zip") { Note "BLOCKED: expected commit package archive missing"; exit 2 }
Note "PACKAGE_BYTES=$($outer.Length)"
Note "PACKAGE_SHA256=$((Get-FileHash $outer.FullName -Algorithm SHA256).Hash)"
if ((Get-FileHash $outer.FullName -Algorithm SHA256).Hash -ne "D6805D40F68F8B965A41359D3096502BA47BBF4A28AA82183AB27350E7A7BDDB") { throw "Package hash mismatch" }
Expand-Archive -LiteralPath $outer.FullName -DestinationPath extracted -Force

$exe = Join-Path $PWD "extracted\bforartists.exe"
if (-not (Test-Path -LiteralPath $exe)) { Note "BLOCKED: executable missing"; exit 3 }

$uiScript = Join-Path $PWD 'extracted\5.3\scripts\startup\bl_ui\space_lestudio.py'
$originalUiHash = (Get-FileHash -LiteralPath $uiScript -Algorithm SHA256).Hash
$replacement = Join-Path $PWD 'space_lestudio_enum_fix.py'
Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/KayouCode/Bforartists/12be9d6ecdd73197b8392c54f5f0b9e9c7c084ae/scripts/startup/bl_ui/space_lestudio.py' -OutFile $replacement
$normalizedUi = [System.IO.File]::ReadAllText($replacement).Replace("`r`n","`n")
$uiHash = [Convert]::ToHexString([System.Security.Cryptography.SHA256]::HashData([System.Text.Encoding]::UTF8.GetBytes($normalizedUi)))
if ($uiHash -ne '7058DD7D07377C9D21B451FAB5EC1F0E58E5917406EEFFD3BA870C917DF4A60F') { throw 'UI enum fix hash mismatch' }
Copy-Item -LiteralPath $replacement -Destination $uiScript
@{
  executable_commit='593019d7355f8dd5dc769ae6735e05ec425e8138'
  executable_sha256=(Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
  ui_correction_commit='12be9d6ecdd73197b8392c54f5f0b9e9c7c084ae'
  correction='Python RNA enum identifier only; executable unchanged'
  original_ui_sha256=$originalUiHash
  corrected_ui_normalized_sha256=$uiHash
} | ConvertTo-Json | Set-Content -LiteralPath 'capture\package-provenance.json'
Note "UI_CORRECTION_COMMIT=12be9d6ecdd73197b8392c54f5f0b9e9c7c084ae EXE_UNCHANGED=True"

$mesaVersion = "26.2.6"
$mesaArchive = Join-Path $PWD "mesa3d-$mesaVersion-release-mingw.7z"
$mesaUrl = "https://github.com/pal1000/mesa-dist-win/releases/download/$mesaVersion/mesa3d-$mesaVersion-release-mingw.7z"
Invoke-WebRequest -Uri $mesaUrl -OutFile $mesaArchive
$mesaHash = (Get-FileHash $mesaArchive -Algorithm SHA256).Hash
Note "MESA_ARCHIVE_SHA256=$mesaHash"
if ($mesaHash -ne "DA0F71D9181B672C1918F3C342F11118C687F6059A46B16502845160733CC388") {
  Note "BLOCKED: Mesa archive hash mismatch"
  exit 4
}
& "C:\Program Files\7-Zip\7z.exe" x -y "-omesa" $mesaArchive | Out-File $log -Append
if ($LASTEXITCODE -ne 0) { Note "BLOCKED: Mesa extraction failed"; exit 5 }

$mesaRoot = Join-Path $PWD "mesa"
$archiveTree = Join-Path $PWD "capture\mesa-archive-tree.txt"
& "C:\Program Files\7-Zip\7z.exe" l -slt $mesaArchive | Set-Content -LiteralPath $archiveTree
Note "MESA_ARCHIVE_TREE=$archiveTree"

function Get-PeMachine([string]$path) {
  $stream = [System.IO.File]::Open($path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
  $reader = [System.IO.BinaryReader]::new($stream)
  try {
    $stream.Position = 0x3c
    $peOffset = $reader.ReadInt32()
    $stream.Position = $peOffset
    if ($reader.ReadUInt32() -ne 0x00004550) { return "not-pe" }
    $machine = $reader.ReadUInt16()
    switch ($machine) {
      0x8664 { return "x64" }
      0x014c { return "x86" }
      0xaa64 { return "arm64" }
      default { return ("0x{0:X4}" -f $machine) }
    }
  }
  finally {
    $reader.Dispose()
    $stream.Dispose()
  }
}

$allDlls = @(Get-ChildItem -LiteralPath $mesaRoot -Recurse -File -Filter "*.dll" | Sort-Object FullName)
$inventory = @()
foreach ($dll in $allDlls) {
  $machine = Get-PeMachine $dll.FullName
  $relative = [System.IO.Path]::GetRelativePath($mesaRoot, $dll.FullName)
  $entry = [pscustomobject]@{
    Name = $dll.Name
    RelativePath = $relative
    FullName = $dll.FullName
    Machine = $machine
    Bytes = $dll.Length
    SHA256 = (Get-FileHash $dll.FullName -Algorithm SHA256).Hash
  }
  $inventory += $entry
  Note "MESA_ARCHIVE_DLL=$relative MACHINE=$machine BYTES=$($dll.Length) SHA256=$($entry.SHA256)"
}
$inventory | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath "capture\mesa-dll-inventory.json"
Note "MESA_DLL_COUNT=$($inventory.Count)"
Note "MESA_X64_DLL_COUNT=$(@($inventory | Where-Object Machine -eq 'x64').Count)"

$openglCandidates = @($inventory | Where-Object { $_.Machine -eq "x64" -and $_.Name -ieq "opengl32.dll" })
if ($openglCandidates.Count -ne 1) {
  Note "BLOCKED: expected exactly one x64 opengl32.dll after architecture inspection, found $($openglCandidates.Count)"
  $openglCandidates | Format-List * | Out-File "capture\opengl-candidates.txt"
  exit 6
}

$vswhere = Join-Path ([Environment]::GetFolderPath("ProgramFilesX86")) "Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path -LiteralPath $vswhere)) {
  Note "BLOCKED: Visual Studio dependency inspector unavailable"
  exit 10
}
$dumpbin = @(& $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -find "VC\Tools\MSVC\**\bin\Hostx64\x64\dumpbin.exe") | Select-Object -First 1
if (-not $dumpbin -or -not (Test-Path -LiteralPath $dumpbin)) {
  Note "BLOCKED: dumpbin dependency inspector unavailable"
  exit 10
}
Note "DEPENDENCY_INSPECTOR=$dumpbin"

$x64ByName = @{}
foreach ($item in @($inventory | Where-Object Machine -eq "x64")) {
  $key = $item.Name.ToLowerInvariant()
  if (-not $x64ByName.ContainsKey($key)) { $x64ByName[$key] = @() }
  $x64ByName[$key] += $item
}

$dependencyReport = Join-Path $PWD "capture\mesa-dependencies.txt"
$selected = @{}
$queue = [System.Collections.Generic.Queue[object]]::new()
$queue.Enqueue($openglCandidates[0])
while ($queue.Count -gt 0) {
  $item = $queue.Dequeue()
  $key = $item.Name.ToLowerInvariant()
  if ($selected.ContainsKey($key)) { continue }
  $selected[$key] = $item

  "===== $($item.RelativePath) =====" | Add-Content -LiteralPath $dependencyReport
  $dependOutput = @(& $dumpbin /DEPENDENTS $item.FullName 2>&1)
  $dependOutput | Add-Content -LiteralPath $dependencyReport
  if ($LASTEXITCODE -ne 0) {
    Note "BLOCKED: dependency inspection failed for $($item.RelativePath)"
    exit 11
  }
  foreach ($line in $dependOutput) {
    if ([string]$line -match '^\s*([A-Za-z0-9_.+-]+\.dll)\s*$') {
      $dependencyName = $Matches[1].ToLowerInvariant()
      if ($x64ByName.ContainsKey($dependencyName)) {
        $matches = @($x64ByName[$dependencyName])
        if ($matches.Count -ne 1) {
          Note "BLOCKED: ambiguous x64 Mesa dependency $dependencyName count=$($matches.Count)"
          exit 12
        }
        if (-not $selected.ContainsKey($dependencyName)) { $queue.Enqueue($matches[0]) }
      }
    }
  }
}

if ($selected.ContainsKey("libglapi.dll")) {
  Note "MESA_LIBGLAPI=present-and-required"
}
else {
  Note "MESA_LIBGLAPI=absent-or-not-required"
}
if ($selected.ContainsKey("libgallium_wgl.dll")) {
  Note "MESA_GALLIUM_WGL=required"
}
else {
  Note "MESA_GALLIUM_WGL=not-imported-by-selected-opengl32"
}

foreach ($item in $selected.Values) {
  $destination = Join-Path (Split-Path $exe) $item.Name
  Copy-Item -LiteralPath $item.FullName -Destination $destination -Force
  Note "MESA_DEPLOYED=$($item.Name) SOURCE=$($item.RelativePath) SHA256=$($item.SHA256)"
}
"Mesa3D application-local deployment" | Set-Content -LiteralPath "$exe.local"
Note "MESA_APPLICATION_LOCAL_MARKER=$exe.local"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/pal1000/mesa-dist-win/26.2.6/LICENSE" -OutFile "capture\MESA_LICENSE.txt"

$env:GALLIUM_DRIVER = "llvmpipe"
$env:LIBGL_ALWAYS_SOFTWARE = "true"
$env:MESA_LOG_LEVEL = "debug"

$probe = Join-Path $PWD "gui_opengl_probe.py"
@'
import json
import os
import traceback
import bpy

output = os.path.join(os.getcwd(), "capture", "opengl-gui-probe.json")
def inspect_gui():
    result = {"mode": "graphical", "binary": bpy.app.binary_path, "build_hash": bpy.app.build_hash.decode()}
    try:
        if not bpy.data.objects.get("Cube"):
            raise RuntimeError("The native startup cube is missing")
        project = os.path.join(os.getcwd(), "capture", "Mission10D.blend")
        bpy.ops.wm.save_as_mainfile(filepath=project)
        result["project"] = project
        result["cube_count"] = sum(1 for ob in bpy.data.objects if ob.type == "MESH")
        import gpu
        result["version"] = gpu.platform.version_get()
        result["renderer"] = gpu.platform.renderer_get()
        result["vendor"] = gpu.platform.vendor_get()
    except Exception:
        result["error"] = traceback.format_exc()
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print("LESTUDIO_GUI_OPENGL", json.dumps(result, sort_keys=True), flush=True)
    return None

def record_workspace():
    try:
        window = bpy.context.window
        with open(os.path.join(os.getcwd(), "capture", "workspace-events.jsonl"), "a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "workspace": window.workspace.name if window else None,
                "scene": window.scene.name if window else None,
                "objects": len(window.scene.objects) if window else None,
            }, ensure_ascii=False) + "\n")
    except Exception:
        traceback.print_exc()
    return 0.5

bpy.app.timers.register(inspect_gui, first_interval=2.0)
bpy.app.timers.register(record_workspace, first_interval=0.5)
'@ | Set-Content -LiteralPath $probe

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
Note "SCREEN=$($screen.Width)x$($screen.Height)"
Note "INTERACTIVE=$([Environment]::UserInteractive)"

$stdout = Join-Path $PWD "capture\application-stdout.log"
$stderr = Join-Path $PWD "capture\application-stderr.log"
$process = Start-Process -FilePath $exe -ArgumentList "--factory-startup","--gpu-backend","opengl","--debug-gpu","--python",$probe -WindowStyle Maximized -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
Note "PROCESS_ID=$($process.Id)"
Start-Sleep -Seconds 25
$process.Refresh()
Note "PROCESS_EXITED=$($process.HasExited)"
Note "MAIN_WINDOW_HANDLE=$($process.MainWindowHandle)"
Note "MAIN_WINDOW_TITLE=$($process.MainWindowTitle)"
if ($process.HasExited -or $process.MainWindowHandle -eq 0) {
  Note "WARNING: no confirmed LeStudio main window; capturing desktop for diagnosis"
}
else {
  Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
[StructLayout(LayoutKind.Sequential)]
public struct LeStudioRect {
  public int Left, Top, Right, Bottom;
}
[StructLayout(LayoutKind.Sequential)]
public struct LeStudioPoint {
  public int X, Y;
  public LeStudioPoint(int x, int y) { X = x; Y = y; }
}
public static class LeStudioRunnerInput {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll", EntryPoint="GetWindowLongPtrW")] public static extern IntPtr GetWindowLongPtr(IntPtr hwnd, int index);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hwnd, System.Text.StringBuilder text, int length);
  [DllImport("user32.dll")] public static extern IntPtr WindowFromPoint(LeStudioPoint point);
  [DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint x, uint y, uint data, UIntPtr extraInfo);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out LeStudioRect rect);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hwnd, int command);
  [DllImport("user32.dll")] public static extern bool IsZoomed(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hwnd);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr hwnd, IntPtr after, int x, int y, int width, int height, uint flags);
  [DllImport("user32.dll")] public static extern IntPtr GetSystemMenu(IntPtr hwnd, bool revert);
  [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr hwnd, uint message, IntPtr wparam, IntPtr lparam);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hwnd, uint message, IntPtr wparam, IntPtr lparam);
  public static int HitTest(IntPtr hwnd, int x, int y) {
    long packed = ((long)(y & 0xffff) << 16) | (uint)(x & 0xffff);
    return (int)SendMessage(hwnd, 0x84, IntPtr.Zero, new IntPtr(packed)).ToInt64();
  }
}
'@
  $foreground = [LeStudioRunnerInput]::SetForegroundWindow($process.MainWindowHandle)
  Note "QUICK_SETUP_FOREGROUND=$foreground"
  $continueX = [int]($screen.Width * 0.50)
  $continueY = [int]($screen.Height * 0.716)
  [void][LeStudioRunnerInput]::SetCursorPos($continueX, $continueY)
  [LeStudioRunnerInput]::mouse_event(0x02, 0, 0, 0, [UIntPtr]::Zero)
  [LeStudioRunnerInput]::mouse_event(0x04, 0, 0, 0, [UIntPtr]::Zero)
  Note "QUICK_SETUP_CONTINUE_CLICK=$continueX,$continueY"
  Start-Sleep -Seconds 4
  [void][LeStudioRunnerInput]::SetForegroundWindow($process.MainWindowHandle)
  [System.Windows.Forms.SendKeys]::SendWait("{ESC}")
  Note "SPLASH_DISMISS_KEY=ESC"
  Start-Sleep -Seconds 4

  $initial = Join-Path $PWD "capture\LeStudio_M10B_initial.png"
  $initialBitmap = New-Object System.Drawing.Bitmap $screen.Width,$screen.Height
  $initialGraphics = [System.Drawing.Graphics]::FromImage($initialBitmap)
  $initialGraphics.CopyFromScreen(0,0,0,0,$initialBitmap.Size)
  $initialBitmap.Save($initial,[System.Drawing.Imaging.ImageFormat]::Png)
  $initialGraphics.Dispose()
  $initialBitmap.Dispose()
  Note "INITIAL_CAPTURE_SHA256=$((Get-FileHash $initial -Algorithm SHA256).Hash)"

  $tabFailures = 0
  $tabs = @(
    @{ Name = "Accueil"; X = 250 },
    @{ Name = "Modélisation"; X = 350 },
    @{ Name = "Sculpture"; X = 480 },
    @{ Name = "Matériaux"; X = 595 },
    @{ Name = "Rendu"; X = 690 },
    @{ Name = "Animation"; Key = "^{PGDN}" },
    @{ Name = "Scripting"; Key = "^{PGDN}" },
    @{ Name = "Modélisation"; X = 350 }
  )
  foreach ($tab in $tabs) {
    $focus = [LeStudioRunnerInput]::SetForegroundWindow($process.MainWindowHandle)
    Start-Sleep -Milliseconds 300
    $foregroundHandle = [LeStudioRunnerInput]::GetForegroundWindow()
    if ($tab.ContainsKey('Key')) {
      [System.Windows.Forms.SendKeys]::SendWait($tab.Key)
      Note "TAB_INPUT_METHOD=$($tab.Name):native-keyboard-$($tab.Key)"
    } else {
      [void][LeStudioRunnerInput]::SetCursorPos([int]$tab.X, 15)
      Start-Sleep -Milliseconds 150
      [LeStudioRunnerInput]::mouse_event(0x02, 0, 0, 0, [UIntPtr]::Zero)
      Start-Sleep -Milliseconds 150
      [LeStudioRunnerInput]::mouse_event(0x04, 0, 0, 0, [UIntPtr]::Zero)
      Note "TAB_INPUT_METHOD=$($tab.Name):real-mouse-click"
    }
    Note "TAB_INPUT=$($tab.Name) FOCUS=$focus FOREGROUND=$foregroundHandle TARGET=$($process.MainWindowHandle)"
    $eventsFile = Join-Path $PWD "capture\workspace-events.jsonl"
    $observed = $null
    $observedObjects = $null
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    do {
      Start-Sleep -Seconds 1
      if (Test-Path -LiteralPath $eventsFile) {
        $lastEvent = Get-Content -LiteralPath $eventsFile -Tail 1 | ConvertFrom-Json
        $observed = $lastEvent.workspace
        $observedObjects = $lastEvent.objects
      }
    } while ($observed -ne $tab.Name -and $timer.Elapsed.TotalSeconds -lt 30)
    $timer.Stop()
    Note "TAB_CLICK_EXPECTED=$($tab.Name) OBSERVED=$observed OBJECTS=$observedObjects X=$($tab.X) Y=15 WAIT_MS=$($timer.ElapsedMilliseconds)"
    if ($observed -ne $tab.Name) { $tabFailures++ }
  }
  Note "TAB_FAILURES=$tabFailures"
  $frameFailures = 0
  $handle = $process.MainWindowHandle
  function Get-Bounds([IntPtr]$windowHandle) {
    $bounds = [LeStudioRect]::new()
    if (-not [LeStudioRunnerInput]::GetWindowRect($windowHandle, [ref]$bounds)) {
      throw "GetWindowRect failed"
    }
    return $bounds
  }
  function Click-Point([int]$x, [int]$y) {
    [void][LeStudioRunnerInput]::SetCursorPos($x, $y)
    Start-Sleep -Milliseconds 150
    [LeStudioRunnerInput]::mouse_event(0x02, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 150
    [LeStudioRunnerInput]::mouse_event(0x04, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 500
  }
  $systemMenu = [LeStudioRunnerInput]::GetSystemMenu($handle, $false)
  Note "SYSTEM_MENU_HANDLE=$systemMenu"
  if ($systemMenu -eq [IntPtr]::Zero) { $frameFailures++ }

  $beforeDrag = Get-Bounds $handle
  [void][LeStudioRunnerInput]::SetForegroundWindow($handle)
  [void][LeStudioRunnerInput]::SetCursorPos(100, 16)
  Start-Sleep -Milliseconds 180
  [LeStudioRunnerInput]::mouse_event(0x02, 0, 0, 0, [UIntPtr]::Zero)
  Start-Sleep -Milliseconds 180
  [void][LeStudioRunnerInput]::SetCursorPos(220, 95)
  Start-Sleep -Milliseconds 450
  [LeStudioRunnerInput]::mouse_event(0x04, 0, 0, 0, [UIntPtr]::Zero)
  Start-Sleep -Seconds 1
  $afterDrag = Get-Bounds $handle
  $dragMoved = $afterDrag.Left -ne $beforeDrag.Left -or $afterDrag.Top -ne $beforeDrag.Top
  Note "DRAG_BEFORE=$($beforeDrag.Left),$($beforeDrag.Top),$($beforeDrag.Right),$($beforeDrag.Bottom) AFTER=$($afterDrag.Left),$($afterDrag.Top),$($afterDrag.Right),$($afterDrag.Bottom) MOVED=$dragMoved"
  if (-not $dragMoved) { $frameFailures++ }

  [void][LeStudioRunnerInput]::ShowWindow($handle, 9)
  [void][LeStudioRunnerInput]::SetWindowPos($handle, [IntPtr]::Zero, 60, 60, 860, 600, 0x0040)
  Start-Sleep -Milliseconds 600
  $beforeResize = Get-Bounds $handle
  $resizeX = $beforeResize.Right - 3
  $resizeY = $beforeResize.Top + 300
  [void][LeStudioRunnerInput]::SetCursorPos($resizeX, $resizeY)
  Start-Sleep -Milliseconds 180
  [LeStudioRunnerInput]::mouse_event(0x02, 0, 0, 0, [UIntPtr]::Zero)
  Start-Sleep -Milliseconds 180
  [void][LeStudioRunnerInput]::SetCursorPos(($resizeX + 45), $resizeY)
  Start-Sleep -Milliseconds 450
  [LeStudioRunnerInput]::mouse_event(0x04, 0, 0, 0, [UIntPtr]::Zero)
  Start-Sleep -Milliseconds 700
  $afterResize = Get-Bounds $handle
  $resizeGrew = ($afterResize.Right - $afterResize.Left) -gt ($beforeResize.Right - $beforeResize.Left)
  Note "RESIZE_BEFORE_WIDTH=$($beforeResize.Right - $beforeResize.Left) AFTER_WIDTH=$($afterResize.Right - $afterResize.Left) GREW=$resizeGrew"
  if (-not $resizeGrew) { $frameFailures++ }

  [void][LeStudioRunnerInput]::ShowWindow($handle, 3)
  Start-Sleep -Milliseconds 600
  $maximized = [LeStudioRunnerInput]::IsZoomed($handle)
  [void][LeStudioRunnerInput]::ShowWindow($handle, 6)
  Start-Sleep -Milliseconds 600
  $minimized = [LeStudioRunnerInput]::IsIconic($handle)
  [void][LeStudioRunnerInput]::ShowWindow($handle, 9)
  Start-Sleep -Milliseconds 600
  $restoredFromMinimized = -not [LeStudioRunnerInput]::IsIconic($handle)
  [void][LeStudioRunnerInput]::ShowWindow($handle, 9)
  Start-Sleep -Milliseconds 600
  $restoredNormal = -not [LeStudioRunnerInput]::IsZoomed($handle) -and -not [LeStudioRunnerInput]::IsIconic($handle)
  Note "SYSTEM_STATES_MAXIMIZED=$maximized MINIMIZED=$minimized RESTORED_FROM_MINIMIZED=$restoredFromMinimized RESTORED_NORMAL=$restoredNormal"
  if (-not ($maximized -and $minimized -and $restoredFromMinimized -and $restoredNormal)) { $frameFailures++ }

  [void][LeStudioRunnerInput]::SetForegroundWindow($handle)
  [System.Windows.Forms.SendKeys]::SendWait("% ")
  Start-Sleep -Milliseconds 600
  $menuPng = Join-Path $PWD "capture\LeStudio_M10D_system_menu.png"
  $menuBitmap = New-Object System.Drawing.Bitmap $screen.Width,$screen.Height
  $menuGraphics = [System.Drawing.Graphics]::FromImage($menuBitmap)
  $menuGraphics.CopyFromScreen(0,0,0,0,$menuBitmap.Size)
  $menuBitmap.Save($menuPng,[System.Drawing.Imaging.ImageFormat]::Png)
  $menuGraphics.Dispose()
  $menuBitmap.Dispose()
  Note "SYSTEM_MENU_CAPTURE_SHA256=$((Get-FileHash $menuPng -Algorithm SHA256).Hash)"
  [System.Windows.Forms.SendKeys]::SendWait("{ESC}")

  [void][LeStudioRunnerInput]::ShowWindow($handle, 3)
  Start-Sleep -Milliseconds 600
  $maxBounds = Get-Bounds $handle
  $hitY = [Math]::Max(15, $maxBounds.Top + 16)
  $hitCodes = @{}
  $buttonXs = @{}
  for ($hitX = $maxBounds.Right - 170; $hitX -lt $maxBounds.Right - 4; $hitX += 3) {
    $code = [LeStudioRunnerInput]::HitTest($handle, $hitX, $hitY)
    if (-not $hitCodes.ContainsKey($code)) { $hitCodes[$code] = $hitX }
    $child = [LeStudioRunnerInput]::WindowFromPoint([LeStudioPoint]::new($hitX, $hitY))
    if ($child -ne [IntPtr]::Zero -and $child -ne $handle) {
      $id = [LeStudioRunnerInput]::GetDlgCtrlID($child)
      if ($id -in @(0x7A01, 0x7A02, 0x7A03)) {
        if (-not $buttonXs.ContainsKey($id)) { $buttonXs[$id] = @() }
        $buttonXs[$id] += $hitX
      }
    }
  }
  Note "CAPTION_HITTESTS=$((@($hitCodes.GetEnumerator() | ForEach-Object { "$($_.Key):$($_.Value)" }) -join ','))"
  Note "WIN32_CHILD_BUTTONS=$((@($buttonXs.GetEnumerator() | ForEach-Object { "$($_.Key):$($_.Value.Count)" }) -join ','))"
  $buttonCenters = @{}
  foreach ($id in @(0x7A01, 0x7A02, 0x7A03)) {
    if ($buttonXs.ContainsKey($id)) {
      $buttonCenters[$id] = $buttonXs[$id][[int][Math]::Floor($buttonXs[$id].Count / 2)]
    }
  }
  if ($buttonCenters.Count -ne 3) {
    $frameFailures++
    Note "CAPTION_BUTTONS=NOT_ALL_VISIBLE"
  }
  else {
    Note "CAPTION_BUTTONS=THREE_WIN32_CONTROLS"
    $style = [LeStudioRunnerInput]::GetWindowLongPtr($handle, -16).ToInt64()
    $clipChildren = ($style -band 0x02000000) -ne 0
    Note ("CAPTION_STYLE=0x{0:X8} CLIPCHILDREN={1}" -f $style,$clipChildren)
    if (-not $clipChildren) { $frameFailures++ }
    Click-Point $buttonCenters[0x7A02] $hitY
    $maxButtonRestored = -not [LeStudioRunnerInput]::IsZoomed($handle)
    Note "MAX_BUTTON_REAL_CLICK_RESTORED=$maxButtonRestored"
    if (-not $maxButtonRestored) { $frameFailures++ }
    $restoredBounds = Get-Bounds $handle
    $maxOffset = $maxBounds.Right - $buttonCenters[0x7A02]
    Click-Point ($restoredBounds.Right - $maxOffset) ($restoredBounds.Top + 16)
    $maxButtonMaximized = [LeStudioRunnerInput]::IsZoomed($handle)
    Note "MAX_BUTTON_REAL_CLICK_MAXIMIZED=$maxButtonMaximized"
    if (-not $maxButtonMaximized) { $frameFailures++ }
    Click-Point $buttonCenters[0x7A01] $hitY
    $minButtonMinimized = [LeStudioRunnerInput]::IsIconic($handle)
    Note "MIN_BUTTON_REAL_CLICK_MINIMIZED=$minButtonMinimized"
    if (-not $minButtonMinimized) { $frameFailures++ }
    [void][LeStudioRunnerInput]::ShowWindow($handle, 3)
    Start-Sleep -Milliseconds 500
  }
  Note "SNAP_LAYOUTS=NOT_TESTED_ON_WINDOWS_SERVER_2022"
  Note "FRAME_FAILURES=$frameFailures"
  [void][LeStudioRunnerInput]::SetCursorPos(500, 500)
  Start-Sleep -Seconds 2
}

$bitmap = New-Object System.Drawing.Bitmap $screen.Width,$screen.Height
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen(0,0,0,0,$bitmap.Size)
$png = Join-Path $PWD "capture\LeStudio_Mesa_LLVMpipe_native.png"
$bitmap.Save($png,[System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()

$check = [System.Drawing.Bitmap]::FromFile($png)
$colors = New-Object 'System.Collections.Generic.HashSet[int]'
$sum = 0L
for ($y=0; $y -lt $screen.Height; $y+=16) {
  for ($x=0; $x -lt $screen.Width; $x+=16) {
    $c=$check.GetPixel($x,$y)
    [void]$colors.Add($c.ToArgb())
    $sum += $c.R + $c.G + $c.B
  }
}
$check.Dispose()
Note "SAMPLED_DISTINCT_COLORS=$($colors.Count)"
Note "SAMPLED_RGB_SUM=$sum"
if ($colors.Count -lt 16 -or $sum -lt 10000) {
  Note "BLOCKED: black, empty, or uniform capture"
  Remove-Item -LiteralPath $png -Force
  Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
  exit 9
}
Note "CAPTURE_SHA256=$((Get-FileHash $png -Algorithm SHA256).Hash)"
$rightActions = @(
  @{ Name = "Bell"; X = $screen.Width - 241 },
  @{ Name = "Help"; X = $screen.Width - 201 },
  @{ Name = "User"; X = $screen.Width - 161 }
)
foreach ($action in $rightActions) {
  [void][LeStudioRunnerInput]::SetForegroundWindow($handle)
  $target = [LeStudioRunnerInput]::WindowFromPoint([LeStudioPoint]::new([int]$action.X, 15))
  $targetId = [LeStudioRunnerInput]::GetDlgCtrlID($target)
  Note "RIGHT_ACTION_TARGET_$($action.Name)=$target ID=$targetId MAIN=$handle"
  if ($target -ne $handle) { $frameFailures++; Note "PARTIAL: right action covered by child control" }
  Click-Point ([int]$action.X) 15
  $actionForeground = [LeStudioRunnerInput]::GetForegroundWindow()
  $titleBuffer = [System.Text.StringBuilder]::new(256)
  [void][LeStudioRunnerInput]::GetWindowText($actionForeground,$titleBuffer,256)
  $actionPng = Join-Path $PWD ("capture\LeStudio_10H_right_" + $action.Name + ".png")
  $actionBitmap = New-Object System.Drawing.Bitmap $screen.Width,$screen.Height
  $actionGraphics = [System.Drawing.Graphics]::FromImage($actionBitmap)
  $actionGraphics.CopyFromScreen(0,0,0,0,$actionBitmap.Size)
  $actionBitmap.Save($actionPng,[System.Drawing.Imaging.ImageFormat]::Png)
  $actionGraphics.Dispose()
  $actionBitmap.Dispose()
  Note "RIGHT_ACTION_CLICK_$($action.Name)=$($action.X),15 FOREGROUND=$actionForeground TITLE=$titleBuffer PNG_SHA256=$((Get-FileHash $actionPng -Algorithm SHA256).Hash)"
  if ([LeStudioRunnerInput]::IsIconic($handle)) {
    $frameFailures++
    Note "PARTIAL: right action minimized main window"
    [void][LeStudioRunnerInput]::ShowWindow($handle, 3)
  }
  if ($actionForeground -ne $handle -and $actionForeground -ne [IntPtr]::Zero) {
    [void][LeStudioRunnerInput]::PostMessage($actionForeground, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
  }
  else {
    [System.Windows.Forms.SendKeys]::SendWait("{ESC}")
  }
  Start-Sleep -Milliseconds 500
}

if (Test-Path -LiteralPath "capture\opengl-gui-probe.json") {
  $guiProbe = Get-Content -LiteralPath "capture\opengl-gui-probe.json" -Raw
  Note "GUI_OPENGL_PROBE=$guiProbe"
  $guiData = $guiProbe | ConvertFrom-Json
  if (-not $guiData.build_hash.StartsWith("593019d7355f")) { $frameFailures++; Note "BLOCKED: graphical executable commit mismatch" }
}
else {
  Note "GUI_OPENGL_PROBE=NOT_AVAILABLE"
}
if (Test-Path -LiteralPath $stderr) {
  Get-Content -LiteralPath $stderr -Tail 80 | Out-File -FilePath $log -Append
}
if (Test-Path -LiteralPath $stdout) {
  Get-Content -LiteralPath $stdout -Tail 80 | Out-File -FilePath $log -Append
}
if ($process.HasExited -or $process.MainWindowHandle -eq 0) {
  Note "BLOCKED: no confirmed real LeStudio application window"
}
else {
  Note "CAPTURE_CANDIDATE=$png"
}
$topCheck = [System.Drawing.Bitmap]::FromFile($png)
$topPixel = $topCheck.GetPixel(500, 10)
$closeGlyphBright = 0
for ($py = 8; $py -le 25; $py++) {
  for ($px = $screen.Width - 43; $px -le $screen.Width - 5; $px++) {
    $pixel = $topCheck.GetPixel($px, $py)
    if ($pixel.R -ge 150 -and $pixel.G -ge 150 -and $pixel.B -ge 150) {
      $closeGlyphBright++
    }
  }
}
$topCheck.Dispose()
Note "CLOSE_GLYPH_BRIGHT_PIXELS=$closeGlyphBright"
if ($closeGlyphBright -lt 8) {
  $frameFailures++
  Note "PARTIAL: clickable close control has no visible glyph"
}
Note "TOPBAR_PIXEL_500_10=$($topPixel.R),$($topPixel.G),$($topPixel.B)"
$neutralWhite = ($topPixel.R -ge 200 -and $topPixel.G -ge 200 -and $topPixel.B -ge 200 -and
  ([Math]::Max($topPixel.R, [Math]::Max($topPixel.G, $topPixel.B)) -
   [Math]::Min($topPixel.R, [Math]::Min($topPixel.G, $topPixel.B))) -le 25)
$blueTint = ($topPixel.B -ge 100 -and $topPixel.B -gt $topPixel.R * 1.4 -and
  $topPixel.B -gt $topPixel.G * 1.15)
Note "TOPBAR_NEUTRAL_WHITE=$neutralWhite BLUE_TINT=$blueTint"
if ($neutralWhite -or $blueTint) {
  $frameFailures++
  Note "BLOCKED: native white or blue frame still covers LeStudio header"
}

$project = Join-Path $PWD "capture\Mission10D.blend"
if (-not (Test-Path -LiteralPath $project)) {
  $frameFailures++
  Note "BLOCKED: native project save missing"
}
else {
  Note "PROJECT_SAVED_SHA256=$((Get-FileHash $project -Algorithm SHA256).Hash)"
}

$process.Refresh()
if (-not $process.HasExited -and $process.MainWindowHandle -ne 0) {
  [void][LeStudioRunnerInput]::SetForegroundWindow($process.MainWindowHandle)
  [System.Windows.Forms.SendKeys]::SendWait("^s")
  Start-Sleep -Seconds 2
  if ($buttonCenters -and $buttonCenters.ContainsKey(0x7A03)) {
    Click-Point $buttonCenters[0x7A03] $hitY
    Note "CLOSE_BUTTON_REAL_CLICK=$($buttonCenters[0x7A03]),$hitY"
  }
  else {
    [void][LeStudioRunnerInput]::PostMessage($process.MainWindowHandle, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
    Note "CLOSE_FALLBACK=WM_CLOSE"
    $frameFailures++
  }
  Start-Sleep -Seconds 3
  $process.Refresh()
  Note "CLOSE_EXITED=$($process.HasExited)"
  if (-not $process.HasExited) {
    $frameFailures++
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
  }
}
else {
  $frameFailures++
  Note "BLOCKED: application exited before close test"
}

if (Test-Path -LiteralPath $project) {
  $reloadProbe = Join-Path $PWD "reload_probe.py"
  @'
import bpy
import json
import os

def verify_reload():
    result = {
        "filepath": bpy.data.filepath,
        "cube_count": sum(1 for ob in bpy.data.objects if ob.name == "Cube" and ob.type == "MESH"),
        "scene": bpy.context.scene.name if bpy.context.scene else None,
    }
    with open(os.path.join(os.getcwd(), "capture", "reload-probe.json"), "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print("LESTUDIO_RELOAD", json.dumps(result, sort_keys=True), flush=True)
    return None

bpy.app.timers.register(verify_reload, first_interval=4.0)
'@ | Set-Content -LiteralPath $reloadProbe
  $reloadStdout = Join-Path $PWD "capture\reload-stdout.log"
  $reloadStderr = Join-Path $PWD "capture\reload-stderr.log"
  $reloaded = Start-Process -FilePath $exe -ArgumentList "--factory-startup","--gpu-backend","opengl",$project,"--python",$reloadProbe -WindowStyle Maximized -RedirectStandardOutput $reloadStdout -RedirectStandardError $reloadStderr -PassThru
  Start-Sleep -Seconds 20
  $reloaded.Refresh()
  Note "RELOAD_WINDOW_HANDLE=$($reloaded.MainWindowHandle) EXITED=$($reloaded.HasExited)"
  $reloadDataPath = Join-Path $PWD "capture\reload-probe.json"
  if (Test-Path -LiteralPath $reloadDataPath) {
    $reloadData = Get-Content -LiteralPath $reloadDataPath -Raw | ConvertFrom-Json
    Note "RELOAD_FILEPATH=$($reloadData.filepath) CUBE_COUNT=$($reloadData.cube_count) SCENE=$($reloadData.scene)"
    if ($reloadData.cube_count -ne 1 -or $reloadData.filepath -ne $project) { $frameFailures++ }
  }
  else {
    Note "BLOCKED: reload probe missing"
    $frameFailures++
  }
  if (-not $reloaded.HasExited -and $reloaded.MainWindowHandle -ne 0) {
    [void][LeStudioRunnerInput]::SetForegroundWindow($reloaded.MainWindowHandle)
    [void][LeStudioRunnerInput]::SetCursorPos([int]($screen.Width * 0.50), [int]($screen.Height * 0.716))
    [LeStudioRunnerInput]::mouse_event(0x02, 0, 0, 0, [UIntPtr]::Zero)
    [LeStudioRunnerInput]::mouse_event(0x04, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Seconds 2
    [System.Windows.Forms.SendKeys]::SendWait("{ESC}")
    Start-Sleep -Seconds 2
    $reloadPng = Join-Path $PWD "capture\LeStudio_M10D_reloaded.png"
    $reloadBitmap = New-Object System.Drawing.Bitmap $screen.Width,$screen.Height
    $reloadGraphics = [System.Drawing.Graphics]::FromImage($reloadBitmap)
    $reloadGraphics.CopyFromScreen(0,0,0,0,$reloadBitmap.Size)
    $reloadBitmap.Save($reloadPng,[System.Drawing.Imaging.ImageFormat]::Png)
    $reloadGraphics.Dispose()
    $reloadBitmap.Dispose()
    Note "RELOAD_CAPTURE_SHA256=$((Get-FileHash $reloadPng -Algorithm SHA256).Hash)"
    [void][LeStudioRunnerInput]::PostMessage($reloaded.MainWindowHandle, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)
  }
  else { $frameFailures++ }
  Start-Sleep -Seconds 2
  $reloaded.Refresh()
  if (-not $reloaded.HasExited) {
    Stop-Process -Id $reloaded.Id -Force -ErrorAction SilentlyContinue
  }
}
Note "FINAL_FRAME_FAILURES=$frameFailures"
if ($tabFailures -gt 0) { Note "BLOCKED: one or more workspace tab clicks failed"; exit 13 }
if ($frameFailures -gt 0) { Note "PARTIAL: one or more frame or reload checks failed"; exit 14 }
