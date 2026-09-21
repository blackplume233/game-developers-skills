# Presets

Each preset below is a complete, pasteable snippet plus what it actually
measured. The numbers come from a PrintWindow capture of a forced-geometry
window (`-Geometry 1200x680+80+80 -Settle`) on Windows 11 with Windows Terminal
1.24.11911.0 and Campbell's `#0C0C0C` background, with Windows transparency
effects enabled. Treat them as a starting point and re-measure: another build,
another scheme background, or a disabled transparency effect changes them.

## The Shared Chrome Theme

Every preset uses this theme. The tab row and the active tab are painted with
the pane's own background colour, which removes the seam across the top of the
window while keeping tabs, the new-tab button and the profile dropdown fully
functional.

```jsonc
"themes": [
    {
        "name": "seamless",
        "window": {
            // Dark window chrome regardless of the OS app theme. On a
            // light-mode OS the 1px frame line otherwise measures near-white
            // (#FFFFFF against a #0C0C0C body) - a bright halo. With dark
            // chrome the same line measures #2B2B2B.
            "applicationTheme": "dark"
        },
        "tabRow": {
            "background": "terminalBackground",
            "unfocusedBackground": "terminalBackground"
        },
        "tab": {
            "background": "terminalBackground",
            "unfocusedBackground": "#00000000",
            "showCloseButton": "hover"
        }
    }
]
```

set at the top level with `"theme": "seamless"`.

Measured: no band above the body paints a different colour, so the chrome seam
check passes by construction - including with a material switched on, because
the material covers the tab row and the body alike.

`showCloseButton` also accepts `activeOnly`, which is a clearer "which tab has
focus" cue than `hover` when the tab row is seamless.

## Preset: Seamless Dark (no material)

The most black a dark scheme can get. `opacity` below 100 blends the scheme
colour over black, so the body ends up *darker* than the scheme itself.

```jsonc
"profiles": {
    "defaults": {
        "useAcrylic": false,
        "opacity": 85,
        "antialiasingMode": "grayscale",
        "padding": "0",
        "scrollbarState": "hidden"
    }
}
```

Measured body: `#0A0A0A` (= 0.85 x `#0C0C0C`, flat field, 99% single colour).

| opacity | measured body |
|---|---|
| 100 | `#0C0C0C` (the scheme background) |
| 85 | `#0A0A0A` |

Choose this when the goal is the darkest possible terminal and flatness matters.

## Preset: Frosted (acrylic)

The frosted look at full material strength. 95 keeps the pane almost opaque, so
this is the least see-through version of it; drop to 50 for glass that is
obviously semi-transparent.

```jsonc
"profiles": {
    "defaults": {
        "useAcrylic": true,
        "opacity": 95,
        "antialiasingMode": "grayscale"
    }
}
```

Measured body: `#222222`, dithered (34% of pixels on the most common colour).
Chrome seam: still passing. Frame line: `#2B2B2B`.

The full alpha map, acrylic on, `#0C0C0C` scheme:

| opacity | measured body | note |
|---|---|---|
| 100 | `#0C0C0C` | material switched off - identical to no acrylic at all |
| 98 | `#222222` | full material |
| 95 | `#222222` | full material, pane still 95% opaque |
| 90 | `#212121` | full material |
| 85 | `#202020` | full material, slightly more see-through |
| 50 | `#181818` | material weakening, body back towards the scheme |
| 25 | `#101010` | mostly scheme again |

Read that table carefully, because it is not the behaviour people expect:
switching acrylic on lifts the body onto a dark veil that barely moves between
opacity 98 and 85, and lowering opacity from there makes the composite *darker*,
not brighter. `opacity` still means what it says - the pane is drawn at that
fraction over the backdrop, so a lower value is more see-through - but the
material's own contribution moves with it, which is why the measured body does
not converge on the scheme colour as opacity falls.

Do not read that table as brightness, and this is the trap worth remembering: the
captured body keeps getting *darker* below 85 (`#181818` at 50, `#101010` at 25),
while on screen those settings look *greyer*. A PrintWindow capture contains only
the window's own composition - the compositor's blur of the desktop behind it is
missing (see `measurement.md`) - and at low opacity that missing term dominates
what you see. Over a mid-grey wallpaper the window then stops reading as a black
window with glass on it and starts reading as grey glass.

So the practical range for a near-black window with frost is **85-95**, and where
it stops working depends on the backdrop, which means the boundary is found by
eye rather than by measurement. Treat 50 and below as a different look
(bright, glass-first) rather than as "more of the same".

There is no dial that adds frost without lifting the body off what the unblurred
blend produces, and none at all that reaches the pure scheme colour while the
material is on.

Also set `opacity` explicitly: with `useAcrylic: true` and no `opacity`,
Windows Terminal defaults it to **50**, which lands in the middle of the table
above rather than at 100.

## Preset: Obsidian Black (measured, in use)

The look this file's numbers were collected against, and the one to start from
when the goal is "a black window with frost on it, on any wallpaper". Two values
carry it: the colour the glass is drawn over, and how much backdrop gets through.

```jsonc
{
    "schemes": [
        {
            // Copy the scheme your build ships - these are Campbell's own
            // colours, read out of the installed defaults.json - and change
            // only "background", so every text colour stays untouched.
            "name": "Obsidian Black",
            "background": "#000000",
            "foreground": "#CCCCCC",
            "cursorColor": "#FFFFFF",
            "black": "#0C0C0C",
            "red": "#C50F1F", "green": "#13A10E", "yellow": "#C19C00",
            "blue": "#0037DA", "purple": "#881798", "cyan": "#3A96DD",
            "white": "#CCCCCC",
            "brightBlack": "#767676", "brightRed": "#E74856",
            "brightGreen": "#16C60C", "brightYellow": "#F9F1A5",
            "brightBlue": "#3B78FF", "brightPurple": "#B4009E",
            "brightCyan": "#61D6D6", "brightWhite": "#F2F2F2"
        }
    ],
    "themes": [
        {
            "name": "seamless",
            "window": { "applicationTheme": "dark" },
            "tabRow": {
                "background": "terminalBackground",
                "unfocusedBackground": "terminalBackground"
            },
            "tab": {
                "background": "terminalBackground",
                "unfocusedBackground": "#00000000",
                "showCloseButton": "hover"
            }
        }
    ],
    "theme": "seamless",
    "profiles": {
        "defaults": {
            "colorScheme": "Obsidian Black",
            "useAcrylic": true,
            "opacity": 90,
            "antialiasingMode": "grayscale",
            "intenseTextStyle": "bold",
            "adjustIndistinguishableColors": "always",
            "padding": "0",
            "cursorShape": "filledBox",
            "scrollbarState": "hidden",
            "font": {
                "face": "Maple Mono NF CN",
                "size": 12,
                "features": { "calt": 1, "zero": 1, "cv01": 1, "cv03": 1, "cv04": 1, "ss07": 1 }
            }
        }
    }
}
```

Measured on 1.24.11911.0 - forced geometry, settled, focused, text-free pane,
`#CCCCCC` text against the measured body:

| Configuration | Own composition | Over pure white | Contrast over white |
|---|---|---|---|
| **this preset** (`#000000`, acrylic 90) | `#212121` | `#2D2D2D` rgb(46,47,46) | **8.4:1** |
| same, acrylic 85 | `#202020` | `#242425` rgb(42,43,45) | 8.8:1 |
| Campbell `#0C0C0C`, acrylic 50 | `#181818` | `#727275` rgb(84,87,90) | 4.7:1 |

The preset's two rows reproduced exactly across independent captures (spread 0).
Note the direction: *raising* opacity makes the body marginally lighter over a
bright backdrop (`#242425` at 85, `#2D2D2D` at 90), because the material's own
veil grows with it - the same reason the α table above reads the way it does.

Why these two values carry the look:

- **`background: #000000`.** The glass is drawn over the scheme colour - at
  opacity 100 the body measures exactly the scheme background, which is the
  calibration this whole file rests on - so the scheme is the floor under the
  material, and lowering the floor is the only change that helps on *every*
  backdrop at once.
- **`opacity: 90`.** High enough that the backdrop cannot take over. At 50 the
  same window over pure white measures `#727275` with text contrast down to
  4.7:1, which is no longer a black window; 85-95 all behave, and below ~80 the
  wallpaper starts deciding the look.
- The rest is crispness rather than colour: grayscale antialiasing (no colour
  fringing on top of a material), bold intense text (keeps the scheme's hue
  instead of lightening it), and `padding: 0` so the field runs to the window
  edge with no inner gutter.

## Preset: Mica (subtle tint)

Mica applies a desaturated tint derived from the desktop wallpaper beneath all
controls, with no blur.

```jsonc
"themes": [
    {
        "name": "seamless",
        "window": {
            "applicationTheme": "dark",
            "useMica": true
        },
        "tabRow": { "background": "terminalBackground" },
        "tab": { "background": "terminalBackground", "showCloseButton": "hover" }
    }
]
```

with an opaque-ish profile (`"opacity": 85`, `useAcrylic` left false).

`useMica` must live in `themes[].window` - that is where the schema defines it,
next to `applicationTheme`. Written into the profile, or into a top-level
`"window"` object, it is silently ignored: no error, no effect, and the capture
then records plain opacity while looking like a Mica result. Check that a key
exists at the path you wrote it before trusting any capture that follows from it.

Measured body: `#0F0F0F`, flat (99%). So over a dark scheme Mica is very nearly
invisible - 3 units away from the scheme's own background. It reads as a subtle
tint, not as glass. Choose it when the goal is a surface that belongs to the
desktop without ever looking blurred or bright.

## Preset: Translucent Dark (no material at all)

For the two cases the presets above do not cover: a machine that will not give
you a material, and a window that should show the **desktop itself** behind the
panes rather than a material's veil. Both material switches go off -
`useAcrylic: false` in the profile, `useMica: false` in the theme - and the tab
row has to carry its own colour, because with no backdrop left there is nothing
for a transparent tab row to fall through to.

```jsonc
"themes": [
    {
        "name": "translucent",
        "window": {
            "applicationTheme": "dark",
            // Mica off. It inserts an opaque layer behind the panes, so pane
            // transparency resolves against Mica and never reaches the desktop.
            "useMica": false
        },
        "tabRow": {
            // The scheme's own background at ~80% alpha - not terminalBackground,
            // which would be fully transparent and fall through to nothing.
            "background": "#1E1E2ECC",
            "unfocusedBackground": "#1E1E2EAA"
        },
        "tab": {
            "background": "terminalBackground",
            "unfocusedBackground": "#00000000",
            "showCloseButton": "hover"
        }
    }
],
"theme": "translucent",
"profiles": {
    "defaults": {
        "useAcrylic": false,
        "opacity": 90,
        "unfocusedAppearance": { "opacity": 82 },
        "antialiasingMode": "grayscale",
        "padding": "12, 8",
        "cursorShape": "filledBox",
        "scrollbarState": "hidden"
    }
}
```

Measured by **screen capture of the window rect** - the composite, backdrop
included, which is the `-Screen` instrument - on Windows Terminal 1.24.11911.0,
scheme `#1E1E2E`, foreground verified on every run. The implied backdrop column
is `(body - opacity x scheme) / (1 - opacity)`:

| Configuration | Body on screen | Implied backdrop |
|---|---|---|
| `opacity: 100`, acrylic off (calibration) | `#1E1E2E` | none - equals the scheme exactly |
| `opacity: 85`, acrylic off, **Mica on** | `#1F1F2C` | `#252521` - Mica, *not* the desktop |
| `opacity: 90`, acrylic off, Mica off | `#222231` | `#46464C` - the mid-grey window behind |
| `opacity: 85`, acrylic off, Mica off | `#1D1D2A` | `#171713` - the dark desktop behind |
| `opacity: 0`, Mica on | `#202020` flat | Mica's solid fallback, over a desktop that measures `#121212` with `#067AB0` patches |

Two things to take from that table:

- **With the materials off, opacity is an alpha blend against the real
  backdrop.** The implied backdrop tracks whatever is behind the window
  (`#46464C` over a grey window, `#171713` over the dark desktop) instead of
  sitting on a fixed level. That is what makes this preset see-through in the
  ordinary sense, and it is why the same opacity reads differently in the two
  rows - the setting did not change, the backdrop did.
- **Mica blocks the desktop.** With `useMica: true` the implied backdrop is a
  near-constant `#252521`, and at `opacity: 0` the pane measures a flat
  `#202020` while the same rectangle with the window minimized shows
  `#121212` / `#067AB0` / `#515151`. Pane transparency resolves against Mica,
  so a "transparent" window over Mica never shows what is actually behind it.
  If the goal is see-through, `useMica` has to be false.

### When the material is missing, not merely weak

A material can be in the schema and absent from the machine. Where DWM refuses
backdrop materials, acrylic does not degrade to "no blur" - it changes *which
level* the body sits at, in the wrong direction:

| Configuration (scheme `#1E1E2E`) | Body | Reading |
|---|---|---|
| `opacity: 85`, `useAcrylic: true` | `#1E1E2E` | exactly the scheme - fully opaque |
| `opacity: 60`, `useAcrylic: true` | `#1E1E2E` | still fully opaque; opacity does nothing |
| `opacity: 85`, `useAcrylic: false` | `#1D1D2A` | translucent, as expected |

On an affected build, **turning acrylic on makes the window more opaque, not
less.** That reads as "the acrylic setting is broken" and is easy to misdiagnose
as a bad key or a stale window; it is the same behaviour reported upstream in
`microsoft/terminal` issue 18189. Diagnose it with three captures, in order:

1. `opacity: 0` with `useMica: true`. A *flat* body while the same rectangle with
   the window minimized shows a *different, varied* desktop means the material
   is painting a solid fallback instead of sampling the wallpaper.
2. `opacity: 85` with acrylic **off** versus **on**. Translucent versus exactly
   the scheme colour is the answer; a material that is present but broken still
   reports as "on", so compare, never inspect the setting alone.
3. Rule out the controllable causes before blaming the build: transparency
   effects on (`UISettings.AdvancedEffectsEnabled`), Energy Saver off and on AC,
   not an RDP session, no virtual display adapter installed by remote-access or
   game-streaming software, GPU driver installed.

On the build these numbers come from, every one of those was ruled out
(`EnableTransparency` 1, `AdvancedEffectsEnabled` true,
`PowerManager.EnergySaverStatus` off, session `Console`, vendor graphics driver
present) and the materials still painted solid. The cause was therefore not
identified, and the diagnostic above - not a suspected cause - is what carries.

Where materials are unavailable this is the only preset that produces a
translucent window at all, because a plain alpha blend needs no material. That
is why the `#1D1D2A` / `#222231` rows exist here rather than being discarded as
a broken run.

## What The Backdrop Does

Every number above is the window's *own* composition. What you see also includes
the blurred desktop behind it, and that term is missing from a `PrintWindow`
capture - which is why the same setting looks different on different wallpapers.
Measured over a forced pure white backdrop with a screen capture (see
`measurement.md`), body of a text-free pane plus the contrast of `#CCCCCC` text
against it:

| Setting | Body over pure white | Text contrast |
|---|---|---|
| acrylic, opacity 50 | `#727275` rgb(84,87,90) | 4.7:1 |
| acrylic, opacity 85 | `#242425` rgb(42,43,45) | 8.8:1 |
| acrylic, opacity 100 (material off) | the scheme's own background | 12:1 |

So over a bright backdrop, opacity 50 is not a black window - it is a mid-grey
one, with text contrast down at the 4.5:1 threshold. Nothing in the schema
compensates per backdrop: **opacity is the only dial**, and darkening the scheme
background (`#000000` instead of Campbell's `#0C0C0C`) is the only way to lower
the floor under it. A window that has to stay black on any wallpaper wants
opacity 100 with the material off: glass is a contract with the backdrop.

## Choosing

| Goal | Preset | Captured body | Looks like |
|---|---|---|---|
| Darkest, flat, no material | Seamless Dark (acrylic off, 85) | `#0A0A0A` | flat near-black |
| Frosted, almost opaque | Frosted (acrylic, 95) | `#222222` | black window, heavy frost |
| Frosted, reads obsidian - the practical sweet spot | Frosted (acrylic, 85-90) | `#202020` / `#212121` | black window, visible frost, 10-15% see-through |
| Bright, glass-first | Frosted (acrylic, 50 and below) | `#181818` / `#101010` | own composition only - over white it measures `#727275` and reads as grey glass |
| Barely-there tint, no blur | Mica (85) | `#0F0F0F` | flat, almost no tint |
| See-through to the real desktop - or a machine that has no materials | Translucent Dark (acrylic off, Mica off, 90) | `#222231` over a mid-grey backdrop, `#1D1D2A` over a dark one | dark glass: the backdrop itself shows through, unblurred |
| The measured look this skill ships for | Obsidian Black (full preset above) | `#212121` | black window + frost; over a white wallpaper still 8.4:1 |

## Not Available

There is no blur radius, saturation, refraction or specular highlight control
in Windows Terminal 1.24 - the appearance option surface is the one enumerated
in `SKILL.md`. Apple-style liquid glass is therefore not reproducible in this
terminal; the acrylic preset above is as close as it gets. Say that rather than
searching for an option that is not in the schema.

Three caveats for all presets:

- Windows transparency effects must be on (**Settings > Personalisation >
  Colours > Transparency effects**). With them off, materials degrade to opaque
  fills and the measurements above no longer apply.
- `useAcrylicInTabRow` paints the tab row with the material *instead of* its
  theme colour, which reintroduces a band across the window even when
  `tabRow.background` is `terminalBackground`. It is a deliberate conflict
  between "frosted chrome" and "seamless chrome"; pick one.
- A material can be missing entirely rather than merely weak - see "When the
  material is missing, not merely weak" above. Every preset except Translucent
  Dark assumes the machine will actually render one, and on a machine that will
  not, `useAcrylic: true` is more opaque than leaving it false.
