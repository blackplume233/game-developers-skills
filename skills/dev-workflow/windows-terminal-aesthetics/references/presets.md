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

Measured body: `#0F0F0F`, flat (99%). So over a dark scheme Mica is very nearly
invisible - 3 units away from the scheme's own background. It reads as a subtle
tint, not as glass. Choose it when the goal is a surface that belongs to the
desktop without ever looking blurred or bright.

## Choosing

| Goal | Preset | Captured body | Looks like |
|---|---|---|---|
| Darkest, flat, no material | Seamless Dark (acrylic off, 85) | `#0A0A0A` | flat near-black |
| Frosted, almost opaque | Frosted (acrylic, 95) | `#222222` | black window, heavy frost |
| Frosted, reads obsidian - the practical sweet spot | Frosted (acrylic, 85-90) | `#202020` / `#212121` | black window, visible frost, 10-15% see-through |
| Bright, glass-first | Frosted (acrylic, 50 and below) | `#181818` / `#101010` | grey glass: the desktop blur dominates |
| Barely-there tint, no blur | Mica (85) | `#0F0F0F` | flat, almost no tint |

## Not Available

There is no blur radius, saturation, refraction or specular highlight control
in Windows Terminal 1.24 - the appearance option surface is the one enumerated
in `SKILL.md`. Apple-style liquid glass is therefore not reproducible in this
terminal; the acrylic preset above is as close as it gets. Say that rather than
searching for an option that is not in the schema.

Two caveats for all presets:

- Windows transparency effects must be on (**Settings > Personalisation >
  Colours > Transparency effects**). With them off, materials degrade to opaque
  fills and the measurements above no longer apply.
- `useAcrylicInTabRow` paints the tab row with the material *instead of* its
  theme colour, which reintroduces a band across the window even when
  `tabRow.background` is `terminalBackground`. It is a deliberate conflict
  between "frosted chrome" and "seamless chrome"; pick one.
