<#
.SYNOPSIS
    Put an opaque full-screen backdrop behind the windows under test, so a
    translucent window can be measured over a *known* background.

.DESCRIPTION
    A measurement of a translucent window is meaningless without knowing what
    was behind it: `opacity` blends the window with the desktop, so the same
    settings look near-black over a dark wallpaper and washed-out grey over a
    bright one. To compare settings you have to fix the backdrop.

    This shows a borderless, maximized, opaque form in the requested colour and
    stays alive until stopped, so the window under test can be brought to the
    front and captured over it with:
        capture-window.ps1 -Screen -Activate

    It is deliberately NOT topmost - the window under test has to be able to
    come in front of it, which is a different requirement from the Windows
    Terminal "always on top" setting.

.PARAMETER Color
    A System.Drawing colour name ("White", "Black") or #RRGGBB. Default White,
    which is the adversarial case for a dark theme.

.PARAMETER Seconds
    Auto-close after this many seconds. 0 (the default) runs until the process
    is stopped.

.EXAMPLE
    # start it in the background, capture over it, then stop it
    pwsh -File white-backdrop.ps1 -Color White
    pwsh -File capture-window.ps1 -TitleMatch "wt-probe" -Screen -Activate -Out probe.png
#>
[CmdletBinding()]
param(
    [string]$Color = 'White',
    [int]$Seconds = 0
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# ShowWithoutActivation is protected on Form, so the backdrop needs a subclass
# rather than a property assignment (setting it from PowerShell fails outright).
# A backdrop that steals the foreground is worse than no backdrop: the window
# under test loses focus mid-measurement and, with a screen capture, the
# backdrop itself can land in the image.
if (-not ('BackdropForm' -as [type])) {
    Add-Type -ReferencedAssemblies @(
        [System.Windows.Forms.Form].Assembly.Location,
        [System.ComponentModel.Component].Assembly.Location,
        [System.Drawing.Color].Assembly.Location
    ) -TypeDefinition @'
using System.Windows.Forms;

public class BackdropForm : Form
{
    protected override bool ShowWithoutActivation { get { return true; } }
}
'@
}

$form = New-Object BackdropForm
$form.FormBorderStyle = 'None'
$form.WindowState = 'Maximized'
$form.ShowInTaskbar = $false
$form.TopMost = $false
$form.BackColor = [System.Drawing.ColorTranslator]::FromHtml($Color)

if ($Seconds -gt 0) {
    $timer = New-Object System.Windows.Forms.Timer
    $timer.Interval = $Seconds * 1000
    $timer.Add_Tick({ $form.Close() })
    $timer.Start()
}

Write-Output ("backdrop : {0} (A={1:X2} R={2:X2} G={3:X2} B={4:X2})  {5}" -f `
    $form.BackColor.Name, $form.BackColor.A, $form.BackColor.R, $form.BackColor.G, $form.BackColor.B, `
    $(if ($Seconds -gt 0) { "auto-close in ${Seconds}s" } else { 'runs until stopped' }))

[System.Windows.Forms.Application]::Run($form)
Write-Output 'backdrop : closed'
