# Measuring A Terminal Window

Eyeballing a translucent window fails in three specific ways, and each of them
produced a wrong conclusion at least once before this protocol existed:

1. **The window in front is not the window you think.** A screenshot records
   whatever is stacked on top, and the foreground window can change between
   capture and analysis.
2. **You catch it mid-paint.** A window that is still animating its launch, still
   applying a settings reload, or still repainting after a resize looks like a
   finished window in a still image.
3. **The bitmap and the window disagree.** Windows Terminal restores the last
   saved window placement, so a probe can come up maximized on one run and
   windowed on the next. Capture a bitmap sized for one and painted for the
   other and you get a mostly-black image whose "body colour" is padding.
4. **The backdrop is not what you think.** A translucent window is a contract
   with whatever is behind it, and a `PrintWindow` capture cannot see that term
   at all. Two runs over two wallpapers are two different measurements.
5. **The key you set is not a key.** Settings files accept unknown keys
   silently. A key written at the wrong level - a theme key in the profile, a
   profile key at the top level - gives no error and no effect, and the capture
   then records the previous value while looking like a result.

The tools here exist to make all five visible instead of silent.

## The Three Tools

```powershell
# 1. Which windows can be captured at all
pwsh -File scripts/capture-window.ps1 -List

# 2. Capture one window, geometry forced, wait for it to stop changing
pwsh -File scripts/capture-window.ps1 -TitleMatch "probe" -Out shot.png `
     -Geometry 1200x680+80+80 -Activate -Settle

# 2b. The composite instead: the window plus the blurred backdrop you see it
#     against. Fix the backdrop first (separate process), then screen-capture.
pwsh -File scripts/white-backdrop.ps1 -Color White      # stop it when done
pwsh -File scripts/capture-window.ps1 -TitleMatch "probe" -Screen -Activate -Out over-white.png
```

```bash
# 3. Measure the capture
python scripts/analyze-capture.py shot.png
python scripts/analyze-capture.py shot.png --expect 0C0C0C   # calibration check
python scripts/analyze-capture.py shot.png --json           # for scripting
```

`capture-window.ps1` asks the window to render itself through `PrintWindow`
with `PW_RENDERFULLCONTENT`, so the result is independent of z-order and focus,
and the window need not be visible. It also reports the geometry it actually
captured, the window's DPI, and whether the window was the foreground window.

## Validity Checklist

Run this before believing any number:

- [ ] **Calibration.** Set `opacity: 100` with the material off and measure.
      The body must equal the scheme's background *exactly*. If it does not,
      nothing else is trustworthy - find out why first.
- [ ] **Geometry.** The capture size matches the geometry that was requested.
      `-Geometry` makes this checkable; without it, be suspicious of any capture.
- [ ] **Settled.** `-Settle` reports how many attempts it took. If it exhausted
      its attempts, the window never stopped changing - treat the result as
      unstable.
- [ ] **Focus.** The capture states whether the window was foreground at
      capture time. An unfocused window is a *different appearance* - unless the
      profile sets no `unfocusedAppearance`, in which case the two were measured
      identical and the flag is informational.
- [ ] **Not occluded or minimized.** `PW_RENDERFULLCONTENT` normally renders
      occluded windows fine, but a minimized window has no size to render.

## How To Read The Report

```text
body     : the dominant colour of the lower third of the window, as
           actually composited, plus its mean and its share
bands    : row ranges grouped by dominant colour, merged within a small
           tolerance - frame line, tab row, tab-row divider, body
seam     : the chrome band versus the body, PASS when within the threshold.
           This is the objective definition of "edgeless"
edge     : the outermost 1px line versus the body, reported separately
           because it is drawn by the window manager, not by the theme
content  : the box that is left after trimming edges that are uniform along
           their whole length (an unpainted 8px strip down the left, 1px
           frame lines) - those are not content
ink      : runs of rows containing enough non-body pixels to be content.
           With a seamless tab row the first run is the tab icon and title,
           so read the runs, not a single "first content row"
```

Two habits matter:

- **Use the mean, not the mode, for a diffuse material.** A dithered field
  splits its pixels across two or three adjacent values; the mode then carries
  only ~34% of them and understates what the eye sees. `mean` and `mode` close
  together with a low `share` means dither, not texture.
- **Separate the chrome seam from the frame line.** A theme can and should make
  the tab row match the body. It cannot make the window manager's 1px frame line
  match, and treating that line as a failed seam sends you optimising something
  no setting controls.

## Worked Example: Verifying a Frosted Preset

Requested: acrylic on, `opacity: 95`, `applicationTheme: dark`, seamless theme.
Captured with `-Geometry 1200x680+80+80 -Activate -Settle`:

```text
captured : shot.png  (settled after 2 attempt(s))
frame    : x=87 y=80 1186x673 (whole visible frame)
dpi      : 96  scale=1

body     : #222222  mean=rgb(33,33,33)  share=33.5%
bands    : y=0..0     1px  #2B2B2B
           y=1..39    39px  #222222
           y=40..40    1px  #1F1F1F
           y=41..671  631px  #222222
           y=672..672   1px  #000000
seam     : PASS by construction - no band above the body paints a different colour
edge     : #2B2B2B @ y=0..0 (1px)  delta=(9,9,9)
content  : x=8..1185  y=1..671  (trimmed L8 R0 T1 B1)
ink      : 1 run, y=9..40, first at y=9 with 130 px at x=44..173
```

Read it as: the material is on (33.5% share with `mean` 33 against `mode` 34 is
the dither signature), the tab row and the body are the same colour so there is
no seam, the 1px frame line is 9 units off instead of 245 (see the light-mode
case below), and after trimming the unpainted 8px strip the only ink is the tab
title - which is correct, because the probe's command produced no output.

## Case Study: A Sweep That Had To Be Thrown Away

An opacity sweep first returned "every value produces pure black", which would
have been a dramatic and completely wrong finding. The capture that gave it away
was:

```text
size     : 2560x1392      <- maximized window size
body     : #000000        share 100%
ink      : first row y=0  pixels=1202   <- the entire first row
```

The window in the bitmap was only about half the bitmap's width, with black
around it: the capture had been sized for a maximized window while the content
had been painted for a windowed one, because the placement restored between runs
differed. The "body" was the padding, and the entire padding row counted as ink.
The sweep was re-run with `-Geometry` forcing a 1200x680 window, and only then
did a coherent map emerge.

Lesson: an implausible result is usually an instrumentation artefact. Check
geometry, `share`, and where the ink rows start before believing a number.

## Case Study: Three Falsified Explanations

Each of these was a plausible mechanism that a measurement killed.

**"The material is grey because the OS is in light app mode."** Measured with
`applicationTheme` set to `light` and to `dark`, same profile, same opacity:
identical body (`#222222`) in both. Only the 1px frame line changed. The OS app
theme is not what sets the material's level.

**"The material shows the wallpaper behind it."** The same window measured at
`+80+80` and at `+1400+400`, over a mid-grey wallpaper: identical body
(`#202020` at opacity 85 in both). Position is not a variable here.

**"`window.frame` controls the frame line."** Set to `terminalBackground` and to
`#00000000`: the line measured `#2B2B2B` both times, unchanged. Measured side by
side, `applicationTheme` is what moves it - from `#FFFFFF` (245 units away from
the body, a bright halo on a light-mode OS) to `#2B2B2B` (9 units).

Note what these have in common: all three were *mechanism* claims, and all three
needed two configurations measured under otherwise identical conditions. One
measurement can never falsify a mechanism; a pair can.

## What This Cannot Show

`PrintWindow` captures the window's own composition. It shows the material's
tint, level and dither, the body colour, the seams and where text starts. It
does **not** show how strongly DWM blurs the desktop behind the window - that
happens in the compositor, outside the window's own rendering.

So: measure the material and the geometry, judge the blur with your eyes, and
report it as judged visually. Do not derive a blur claim from a captured pixel
value.

The complement is `-Screen` over a fixed backdrop (`white-backdrop.ps1`). That
capture *does* contain the blurred desktop, because it records what is on screen
rather than what the window renders - so it can measure the composite, at the
price of requiring the window unobstructed and in front. When the question is
"does this setting survive a light wallpaper", that is the instrument; when the
question is "what does this setting paint", `PrintWindow` is.

## Case Study: The Capture That Was The Backdrop

A white-backdrop sweep reported every configuration as `body #FFFFFF`,
`mean rgb(240,240,240)`, `share 71%`, `text 0`. No setting explained it: the
image was the *backdrop*, not the window. Two silent causes:

1. `SetForegroundWindow` refused to raise the probe (the measuring process was
   background, so it was not allowed to change foreground), and the `focused : NO`
   line was read as a caveat rather than as a failed run.
2. A screen capture records z-order. The probe was never in front, so it was
   never in the picture.

Both are fixed in the tooling - activation now attaches to the foreground
thread's input queue, and the backdrop is a non-activating window
(`ShowWithoutActivation`, which on `Form` is protected and therefore needs a
subclass, not a property assignment). The lesson to keep: on a `-Screen` capture,
`focused: NO` means "this is a photograph of something else", and every
configuration reporting the same near-white body is the backdrop talking.

## Troubleshooting

| Symptom | Cause and what to do |
|---|---|
| `No visible top-level window title contains '...'` | Run with `-List`. Windows Terminal windows are class `CASCADIA_HOSTING_WINDOW_CLASS`; the title changes as the running program sets it, so prefer `--suppressApplicationTitle` on a dedicated probe window |
| Several candidate windows | Tighten `-TitleMatch`; the tool names the candidates it saw |
| `PrintWindow failed` | The window refused to render - usually minimized. Restore it and retry |
| `focused : NO` even with `-Activate` | `SetForegroundWindow` is refused when the calling process is not already foreground - background scripts and agents hit this every time. `-Activate` now attaches to the foreground thread's input queue to lift the restriction. If the flag still says NO, something else holds the foreground: treat a `-Screen` capture as failed, because it may have photographed that other window |
| Body reads darker than the scheme background | Expected with a material off: `opacity` alpha-blends the scheme colour over black, so 85% of `#0C0C0C` measures `#0A0A0A` |
| Detected width is smaller than the requested geometry | `-Geometry` sets the outer window size; the visible frame can be a few pixels smaller. Use the reported frame size, not the requested one, when interpreting x coordinates |
