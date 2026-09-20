<#
.SYNOPSIS
    Occlusion-proof capture of a single top-level window, for measuring what a
    window really paints instead of what the screen happens to show.

.DESCRIPTION
    Taking a picture of the whole screen is the wrong instrument: whatever
    window is in front wins, the foreground window can change under you between
    capture and analysis, and a half-faded animation frame gets recorded as if
    it were the final paint. This script asks the target window to render itself
    into a bitmap via PrintWindow(), so the result is independent of z-order,
    focus, and other windows covering it.

    It also prints the geometry that matters for measurement:
      * extended frame bounds (the visible frame - not GetWindowRect, which
        includes the invisible ~7px DWM resize border on Windows 10/11)
      * client rect
      * DPI for the window (capture is at physical pixels, not virtualized)

.PARAMETER TitleMatch
    Case-insensitive substring of the window title. Required unless -List.

.PARAMETER Out
    Output PNG path. Defaults to $env:TEMP\wt-capture.png.

.PARAMETER List
    Enumerate capturable top-level windows and exit. Use this first when the
    title substring is not known.

.PARAMETER ClientOnly
    Capture only the client area instead of the whole visible frame. The default
    (whole frame) is what you want for judging tab-row / title-bar / body seams.

.PARAMETER Screen
    Capture the window's screen area instead, so the result is the real
    composite: the window plus whatever the compositor put behind it. This is
    the right instrument when the *backdrop* is part of the question. The same
    `opacity` over a dark wallpaper and over a white one produce completely
    different pictures, and the PrintWindow path cannot show that difference at
    all, because it renders only the window's own composition. Pair it with a
    fixed backdrop (white-backdrop.ps1) so runs are comparable, and bring the
    window to the front with -Activate: unlike PrintWindow this cannot see
    through other windows, so anything covering the target lands in the image.

.PARAMETER Activate
    Bring the matched window to the foreground and give it a moment to repaint
    before capturing. A measurement of an unfocused window is a measurement of
    the unfocused appearance - a different colour, and on some configurations a
    different acrylic. The script always reports whether the target really was
    in the foreground at capture time, so an accidental mismatch is visible in
    the output instead of silently poisoning the numbers.

.PARAMETER Geometry
    Force the window to a known size and position before capturing, as
    WxH+X+Y (e.g. 1200x680+80+80). Windows Terminal restores the last saved
    window placement when a new window opens, so a probe can come up maximized
    on one run and windowed on the next; a capture sized for one and painted for
    the other silently produces a mostly-black image whose "body" colour is
    padding rather than the window. Forcing geometry makes runs comparable.

.PARAMETER Settle
    Capture repeatedly until two consecutive captures are byte-identical, then
    keep that one. A terminal that is still animating its start-up, still
    applying a settings reload, or still repainting after a resize will otherwise
    be measured mid-transition. Reports how many attempts it took.

.PARAMETER CloseMatch
    Send WM_CLOSE to the matched window after capturing. Only ever closes the
    single window that matched - never the process, never sibling windows.

.EXAMPLE
    pwsh -File capture-window.ps1 -List
    pwsh -File capture-window.ps1 -TitleMatch "wt-probe" -Out "$env:TEMP\probe.png"
#>
[CmdletBinding()]
param(
    [string]$TitleMatch,
    [string]$Out = (Join-Path $env:TEMP 'wt-capture.png'),
    [string]$Geometry,
    [switch]$Settle,
    [switch]$List,
    [switch]$ClientOnly,
    [switch]$Screen,
    [switch]$Activate,
    [switch]$CloseMatch
)

$ErrorActionPreference = 'Stop'
try { Add-Type -AssemblyName System.Drawing } catch {
    try { Add-Type -AssemblyName System.Drawing.Common } catch { throw "System.Drawing unavailable: $($_.Exception.Message)" }
}

if (-not ('WinCap' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;

public class WinCap
{
    public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }

    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr lParam);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
    [DllImport("user32.dll")] public static extern uint GetDpiForWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool PostMessageW(IntPtr h, uint msg, IntPtr w, IntPtr l);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h, int x, int y, int w, int hh, bool repaint);
    [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr ctx);
    [DllImport("dwmapi.dll")] public static extern int DwmGetWindowAttribute(IntPtr h, int attr, out RECT r, int size);

    public const int DWMWA_EXTENDED_FRAME_BOUNDS = 9;
    public const uint WM_CLOSE = 0x0010;
    public const uint PW_CLIENTONLY = 1;
    public const uint PW_RENDERFULLCONTENT = 2;

    public class WinInfo
    {
        public IntPtr Hwnd;
        public string Title = "";
        public string Class = "";
        public uint Pid;
        public int X, Y, Width, Height;
        public int ClientWidth, ClientHeight;
        public uint Dpi;
    }

    public static void MakePerMonitorAware()
    {
        // -4 = DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2: coordinates and
        // PrintWindow output are physical pixels, matching what the user sees.
        try { SetProcessDpiAwarenessContext(new IntPtr(-4)); } catch { }
    }

    public static List<WinInfo> Enumerate(bool visibleOnly)
    {
        var list = new List<WinInfo>();
        EnumWindows(delegate (IntPtr h, IntPtr l)
        {
            if (visibleOnly && !IsWindowVisible(h)) return true;
            var sb = new StringBuilder(512);
            GetWindowTextW(h, sb, sb.Capacity);
            string title = sb.ToString();
            if (title.Length == 0) return true;

            var cls = new StringBuilder(256);
            GetClassNameW(h, cls, cls.Capacity);

            var wi = new WinInfo();
            wi.Hwnd = h; wi.Title = title; wi.Class = cls.ToString();
            uint pid; GetWindowThreadProcessId(h, out pid); wi.Pid = pid;

            RECT r; RECT er;
            if (DwmGetWindowAttribute(h, DWMWA_EXTENDED_FRAME_BOUNDS, out er, Marshal.SizeOf(typeof(RECT))) == 0)
                r = er;
            else
                GetWindowRect(h, out r);

            wi.X = r.Left; wi.Y = r.Top;
            wi.Width = r.Right - r.Left; wi.Height = r.Bottom - r.Top;

            RECT cr;
            if (GetClientRect(h, out cr)) { wi.ClientWidth = cr.Right; wi.ClientHeight = cr.Bottom; }
            wi.Dpi = GetDpiForWindow(h);
            list.Add(wi);
            return true;
        }, IntPtr.Zero);
        return list;
    }

    // SetForegroundWindow silently refuses when the calling process is not
    // already foreground - which is exactly the situation when a measurement is
    // driven from a background process (a script, an agent, a scheduled run).
    // Attaching to the foreground thread's input queue for the duration of the
    // call lifts that restriction. Without this you do not get an error: you
    // get a capture of whatever window was in front instead of the target.
    [DllImport("user32.dll")] public static extern IntPtr SetFocus(IntPtr h);
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
    [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();

    public static bool ForceForeground(IntPtr h)
    {
        IntPtr fg = GetForegroundWindow();
        uint fgPid;
        uint fgThread = fg != IntPtr.Zero ? GetWindowThreadProcessId(fg, out fgPid) : 0;
        uint myThread = GetCurrentThreadId();
        bool attached = false;
        if (fgThread != 0 && fgThread != myThread)
        {
            attached = AttachThreadInput(fgThread, myThread, true);
        }
        try
        {
            ShowWindow(h, 9);   // SW_RESTORE, so a maximized probe can be measured
            BringWindowToTop(h);
            SetForegroundWindow(h);
            SetFocus(h);
        }
        finally
        {
            if (attached) AttachThreadInput(fgThread, myThread, false);
        }
        return GetForegroundWindow() == h;
    }

}
'@
}

# System.Drawing is deliberately NOT referenced from the compiled helper: under
# PowerShell 7 the C# compiler needs an explicit System.Drawing.Common reference
# and fails with CS1069 otherwise. Drawing from PowerShell itself avoids the
# whole problem and works on both Windows PowerShell 5.1 and PowerShell 7.
if (-not ('System.Drawing.Bitmap' -as [type])) { throw 'System.Drawing is unavailable in this PowerShell host.' }

function Save-WindowCapture {
    param([IntPtr]$Hwnd, [int]$Width, [int]$Height, [string]$Path, [bool]$ClientOnly)
    $bmp = New-Object System.Drawing.Bitmap($Width, $Height)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $primary = if ($ClientOnly) { [WinCap]::PW_CLIENTONLY } else { [WinCap]::PW_RENDERFULLCONTENT }
    try {
        $hdc = $g.GetHdc()
        try { $ok = [WinCap]::PrintWindow($Hwnd, $hdc, [uint32]$primary) }
        finally { $g.ReleaseHdc($hdc) }
        if (-not $ok) {
            $primary = 0
            $hdc = $g.GetHdc()
            try { $ok = [WinCap]::PrintWindow($Hwnd, $hdc, [uint32]0) }
            finally { $g.ReleaseHdc($hdc) }
        }
        if (-not $ok) { throw 'PrintWindow failed for this window (it may refuse to render while occluded)' }
        $bmp.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $g.Dispose()
        $bmp.Dispose()
    }
    return $primary
}

# The complement of Save-WindowCapture: instead of asking the window to render
# itself, grab the pixels that are actually on screen over that rectangle. This
# is the only way to see the compositor's contribution - the blurred backdrop
# behind an acrylic / translucent window - which is exactly the term that
# decides how the window looks on a light versus a dark background.
function Save-ScreenCapture {
    param([int]$X, [int]$Y, [int]$Width, [int]$Height, [string]$Path)
    $bmp = New-Object System.Drawing.Bitmap($Width, $Height)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    try {
        $g.CopyFromScreen($X, $Y, 0, 0, (New-Object System.Drawing.Size($Width, $Height)))
        $bmp.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $g.Dispose()
        $bmp.Dispose()
    }
    return 'screen'
}

[WinCap]::MakePerMonitorAware()
$windows = [WinCap]::Enumerate($true)

if ($List) {
    '{0,-12} {1,-8} {2,10} {3,9} {4,-28} {5}' -f 'HWND', 'PID', 'SIZE', 'DPI', 'CLASS', 'TITLE'
    foreach ($w in ($windows | Sort-Object Pid, Title)) {
        '{0,-12} {1,-8} {2,10} {3,9} {4,-28} {5}' -f (
            ('0x{0:X}' -f [int64]$w.Hwnd), $w.Pid, "$($w.Width)x$($w.Height)", $w.Dpi, $w.Class,
            ($w.Title.Substring(0, [Math]::Min(60, $w.Title.Length)))
        )
    }
    exit 0
}

if (-not $TitleMatch) { throw 'Supply -TitleMatch <substring>, or -List to enumerate windows.' }

$matches = @($windows | Where-Object { $_.Title -like "*$TitleMatch*" })
if ($matches.Count -eq 0) { throw "No visible top-level window title contains '$TitleMatch'. Run with -List." }
if ($matches.Count -gt 1) {
    Write-Warning "Title matched $($matches.Count) windows; using the first. Tighten -TitleMatch."
    foreach ($m in $matches) { Write-Warning "  candidate: 0x$('{0:X}' -f [int64]$m.Hwnd) $($m.Title)" }
}

$win = $matches[0]

if ($Geometry) {
    if ($Geometry -notmatch '^(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$') {
        throw "-Geometry must look like WxH+X+Y, e.g. 1200x680+80+80"
    }
    $gw = [int]$Matches[1]; $gh = [int]$Matches[2]; $gx = [int]$Matches[3]; $gy = [int]$Matches[4]
    [void][WinCap]::ShowWindow($win.Hwnd, 9)   # SW_RESTORE first, so a maximized probe can be resized
    Start-Sleep -Milliseconds 250
    if (-not [WinCap]::MoveWindow($win.Hwnd, $gx, $gy, $gw, $gh, $true)) { throw 'MoveWindow failed' }
    Start-Sleep -Milliseconds 500
    # The geometry just changed, so re-read it instead of trusting pre-move numbers.
    $reread = [WinCap]::Enumerate($true) | Where-Object { $_.Hwnd -eq $win.Hwnd }
    if ($reread) { $win = $reread }
}

if ($Activate) {
    [void][WinCap]::ForceForeground($win.Hwnd)
    Start-Sleep -Milliseconds 400
}
$foreground = ([WinCap]::GetForegroundWindow() -eq $win.Hwnd)

$cw = if ($ClientOnly) { $win.ClientWidth } else { $win.Width }
$ch = if ($ClientOnly) { $win.ClientHeight } else { $win.Height }
if ($cw -le 1 -or $ch -le 1) { throw "Degenerate window size ${cw}x${ch} - is it minimized?" }
if ($Screen -and $ClientOnly) { throw '-Screen captures the visible frame; drop -ClientOnly and crop after capture instead.' }

# One closure so the settle loop and the single-shot path cannot drift apart.
$capture = {
    if ($Screen) {
        Save-ScreenCapture -X $win.X -Y $win.Y -Width $cw -Height $ch -Path $Out
    }
    else {
        Save-WindowCapture -Hwnd $win.Hwnd -Width $cw -Height $ch -Path $Out -ClientOnly ([bool]$ClientOnly)
    }
}

$dir = Split-Path -Parent $Out
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

$attempts = 1
if ($Settle) {
    $prev = "$Out.settle"
    $attempts = 0
    for ($i = 1; $i -le 8; $i++) {
        $attempts = $i
        $usedFlags = & $capture
        if ($i -ge 2 -and (Get-FileHash $Out).Hash -eq (Get-FileHash $prev).Hash) { break }
        Copy-Item $Out $prev -Force
        Start-Sleep -Milliseconds 350
    }
    Remove-Item $prev -Force -ErrorAction SilentlyContinue
}
else {
    $usedFlags = & $capture
}

Write-Output "captured : $Out  ($(if ($Settle) { "settled after $attempts attempt(s)" } else { 'single shot' }))"
Write-Output "window   : 0x$('{0:X}' -f [int64]$win.Hwnd)  pid=$($win.Pid)  class=$($win.Class)"
Write-Output "title    : $($win.Title)"
Write-Output "frame    : x=$($win.X) y=$($win.Y) ${cw}x${ch} $($(if ($ClientOnly) { '(client)' } else { '(whole visible frame)' }))"
Write-Output "dpi      : $($win.Dpi)  scale=$([Math]::Round($win.Dpi / 96.0, 2))"
Write-Output "focused  : $(if ($foreground) { 'yes - focused appearance captured' } else { 'NO - unfocused appearance; rerun with -Activate for the focused theme' })"
if ($Screen) {
    Write-Output "source   : screen - the real composite, backdrop included (anything covering the window is in this image)"
}
else {
    Write-Output "printwin : flags=$usedFlags $(if ($usedFlags -eq 2) { '(PW_RENDERFULLCONTENT)' } elseif ($usedFlags -eq 1) { '(PW_CLIENTONLY)' } else { '(0 - fallback, content may be incomplete)' })"
}

if ($CloseMatch) {
    [void][WinCap]::PostMessageW($win.Hwnd, [WinCap]::WM_CLOSE, [IntPtr]::Zero, [IntPtr]::Zero)
    Write-Output "closed   : WM_CLOSE sent to 0x$('{0:X}' -f [int64]$win.Hwnd) only"
}
