---
name: windows-terminal-aesthetics
version: 1.0.1
description: >-
  Tune the look of Windows Terminal and prove the result with pixel
  measurements instead of eyeballing: acrylic and Mica backdrops, opacity,
  removing the tab-row seam for an edgeless window, keeping text crisp over a
  translucent backdrop, and validating settings.json against the schema of the
  version actually installed. Triggers on: "Windows Terminal theme",
  "terminal too grey", "make the terminal transparent", "frosted glass",
  "acrylic", "Mica", "opacity", "edgeless terminal", "seamless tab row",
  "terminal text looks blurry", "settings.json ignored", "窗口美化",
  "终端美化", "终端磨砂", "液态玻璃", "亚克力", "终端透明度", "无边框终端",
  "标签栏接缝", "终端字体发虚", "设置不生效".
license: MIT
allowed-tools: Shell, Read, Glob, Grep
---

# Windows Terminal Aesthetics

## Role

You tune how Windows Terminal *looks* and you prove each claim with a
measurement. Terminal appearance is unusually easy to get wrong by reasoning:
three layers composite into one pixel value, most knobs interact, and a setting
whose key name the installed version does not know is ignored in silence. So the
loop is always:

```text
back up -> edit -> validate against the installed version's schema
        -> capture the window -> measure -> accept or roll back
```

Never report "this should look blacker / more frosted". Either a capture says so
or the answer is that it could not be measured and why.

## Trigger Conditions

- Making a terminal darker, lighter, translucent, frosted, or edgeless
- The window's background is not the colour the scheme specifies
- Text over a translucent backdrop looks washed out, fringed or blurry
- A setting was added to `settings.json` and appears to do nothing
- Comparing theme or backdrop variants and wanting a defensible answer
- Upgrading Windows Terminal and needing to know which keys still exist

## The Composition Model

A pixel in the terminal body is decided bottom-up by four layers. Knowing the
order is what makes the documented observations predictable instead of
surprising:

1. **Window backdrop material** - DWM acrylic (blur + tint + noise) or Mica
   (tint only, no blur), chosen by the profile's `useAcrylic` or the theme's
   `window.useMica`. This is the only layer that can blur what is behind.
2. **The scheme background**, drawn at `opacity` over that material. With
   acrylic off there is nothing to blur, so opacity is a plain alpha blend of
   the scheme colour over black - which is why a body can measure *darker* than
   the scheme's own background.
3. **The tab row and tabs**, painted from the theme's `tabRow`/`tab` colours
   unless those are set to the special value `terminalBackground`.
4. **Window-manager chrome** - a 1px frame line and the corner radius. Not
   reachable from the colour settings; see the pitfalls below.

Consequences worth stating up front, because they trip people up:

- `opacity` is not a blend factor against the desktop; it is the alpha of the
  scheme background over whatever backdrop exists.
- Enabling a material does more than "add blur": it changes the *level* the
  body sits at, and material is a switch rather than a slider.
- A tab row whose colour equals the body colour is what makes a window read as
  edgeless. Deleting the tab row is not required, and costs tab switching, the
  new-tab button and the profile dropdown - do not trade function for looks.

## The Option Surface

Before touching anything, enumerate what the installed version actually offers.
The full appearance/material surface in Windows Terminal 1.24 (schema
v1.24.11911.0) is small, and several settings people expect do not exist:

| Where | Key | Effect |
|---|---|---|
| profile | `useAcrylic` | acrylic material on/off - the only real blur |
| profile | `opacity` | 0-100, alpha of the scheme background |
| profile | `acrylicOpacity` | **deprecated** in 1.24, replaced by `opacity` |
| profile | `antialiasingMode` | `grayscale` avoids ClearType fringing over translucency |
| profile | `font.features` | OpenType feature tags, any four printable ASCII chars |
| theme `window` | `useMica` | Mica backdrop under all controls, including panes |
| theme `window` | `applicationTheme` | `light` / `dark` / `system` for the window chrome |
| theme `window` | `frame`, `unfocusedFrame` | frame colour; measured to have no effect on the focused frame line |
| theme `tabRow` | `background`, `unfocusedBackground` | accepts `terminalBackground` |
| theme `tab` | `background`, `unfocusedBackground`, `showCloseButton`, `iconStyle` | `showCloseButton`: `always`/`hover`/`never`/`activeOnly` |
| global | `compatibility.enableUnfocusedAcrylic` | default `true`; unfocused windows may keep acrylic |
| global | `experimental.useBackgroundImageForWindow` | background image spans the whole window |

There is no blur radius, no saturation, no refraction and no frost-strength
knob. That is an enumerated fact about the schema, not an opinion, and it is why
macOS-style liquid glass is not reproducible here - say so plainly instead of
hunting for a hidden option.

## Workflow

### 1. Back up and locate the live file

```powershell
$set = "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json"
Copy-Item $set "$env:TEMP\settings.backup.jsonc"
```

The live file lives under the package **family name**, not a versioned folder:

```powershell
(Get-AppxPackage Microsoft.WindowsTerminal).PackageFamilyName   # Microsoft.WindowsTerminal_8wekyb3d8bbwe
```

Copy files, do not "fix" them in place, and keep the copy until the change has
been measured.

### 2. Validate before measuring

```bash
python scripts/validate-settings.py              # auto-detects file and version
python scripts/validate-settings.py --version 1.24.11911.0
```

This parses JSONC (comments and trailing commas are legal in this file, so a
plain JSON parser is the wrong tool) and checks every key and value against the
schema for the installed version, quoting line numbers on syntax errors and
listing keys the version does not know. Run it after **every** edit: a
mistyped key produces no error anywhere else, the setting just never applies.

### 3. Edit, preferring the theme over the profile

Chrome belongs in a named theme so it can be switched with one line
(`"theme": "name"`). Body appearance belongs in the profile, because
`useAcrylic` and `opacity` are profile settings and cannot be selected by theme
name - if a user needs to switch between opaque and frosted bodies, the honest
options are a duplicate profile or editing one line.

Set an explicit `opacity` whenever `useAcrylic` is true: if opacity is omitted
while acrylic is on, Windows Terminal defaults it to **50**, not 100.

Profile appearance changes apply to windows that are already open - verified by
flipping `useAcrylic` with a window on screen and re-measuring the same window
(`#202020` -> `#0A0A0A` -> `#202020`). So a settings edit that "did nothing" is a
validation or key-name problem (step 2), not a stale-window problem. Do not send
users off to restart the terminal for this.

### 4. Measure

```powershell
pwsh -File scripts/capture-window.ps1 -List
pwsh -File scripts/capture-window.ps1 -TitleMatch "<title substring>" -Out shot.png `
     -Geometry 1200x680+80+80 -Activate -Settle
python scripts/analyze-capture.py shot.png
python scripts/analyze-capture.py shot.png --expect 0C0C0C    # calibration
```

`-Geometry` forces a known size and position, `-Settle` re-captures until two
captures are byte-identical, and `-Activate` brings the window forward. Without
them you measure a resized, animating, or unfocused window and cannot tell. The
capture also prints whether the target really was focused - a measurement of an
unfocused window is a measurement of a different appearance.

Calibrate before trusting anything: set opacity 100 and check that the measured
body equals the scheme's own background exactly. If it does not, stop and find
out why before drawing conclusions from any other number.

### 5. Accept or roll back, and record why

Keep the measured table in a comment next to the settings it justifies, with the
version and conditions. Do not keep a number whose provenance is gone - the next
person (or the next Windows Terminal release) has no way to tell whether it was
measured or guessed.

## Measured Pitfalls

Each of these cost a wrong conclusion before it was measured:

- **A "grey floor" is not the system app theme.** The material's tone was
  attributed to `AppsUseLightTheme = 1` until `applicationTheme: light` and
  `dark` were measured side by side and produced an *identical* body (see
  `references/measurement.md`). Do not explain a backdrop from the OS theme
  without measuring both.
- **Screen position is not the answer either.** The same window at two screen
  positions over a mid-grey wallpaper measured an identical body, so the
  material is not simply tracking the local wallpaper region.
- **`window.frame` does not control the focused frame line.** Setting it to
  `terminalBackground` and to `#00000000` both left the 1px line unchanged. On
  a light-mode OS that line measures near-white; `applicationTheme: dark` is
  what turns it dark. Do not promise a no-border window from colour settings.
- **Acrylic is dithered.** ~34% of pixels sit on the single most common colour
  versus ~99% for a flat fill. A capture that reports a low "share" with a mean
  close to the mode is dithered, not textured - and a naive per-pixel threshold
  will call that noise "content".
- **Screenshotting the screen is the wrong instrument.** A screen capture can
  record a stale or occluded window and a half-finished animation. Capture the
  window itself.
- **Windows Terminal restores the last window placement.** A probe can appear
  maximized on one run and windowed the next; a bitmap sized for one and painted
  for the other yields a mostly-black image whose "body" is padding. Force
  geometry.
- **Captures contain unpainted edges.** An 8px black strip on the left and 1px
  frame lines are not content; `analyze-capture.py` trims any edge that is
  uniform along its whole length before looking for text.

## What Cannot Be Measured This Way

A `PrintWindow` capture shows the window's *own* composition. It reveals the
material's tint, level and dither, the body colour, seams and text positions -
but **not** how strongly DWM blurs the desktop behind the window. Judge the blur
itself visually, and say that the blur was verified by eye rather than by
measurement. Do not infer blur strength from a captured pixel value.

## Reporting

State, for each claim: the value, the conditions it was measured under
(Windows Terminal version, scheme background, opacity, other settings), and
whether it reproduced. Distinguish measured facts from mechanism guesses, and
say when the available instrumentation cannot answer the question at all.

## Completion Status

- `DONE`: settings validated for the installed version, the change captured and
  measured, the number recorded next to the setting, rollback documented
- `PARTIAL`: change applied and measured, but the mechanism is unexplained
- `BLOCKED`: cannot capture (no window, or `PrintWindow` refuses) or cannot
  determine the installed version's schema - say which, and what was tried

## Related Files

- `references/presets.md` - ready-made appearance presets with measured results
- `references/measurement.md` - the measurement protocol and worked examples
- `scripts/capture-window.ps1` - occlusion-proof window capture
- `scripts/analyze-capture.py` - body colour, bands, seams, content box, text rows
- `scripts/validate-settings.py` - settings.json vs the installed version's schema
