# Static assets

VECTOR shows unit branding from this directory when the files are here:

| File               | Used for                                               |
|--------------------|--------------------------------------------------------|
| `novadc_icac.png`  | The logo on the login, Home and Reports pages          |
| `novadc_icac.ico`  | The icon in the top bar, and the browser tab icon      |
| `favicon.ico`      | Optional: the browser tab icon, in place of the above  |

They are not distributed with the source. Drop them in here after
cloning. VECTOR runs without them: a page with no logo file shows just
its title, so a missing logo never gets in the way of documenting a
scene.

A logo appears on the next page load. The browser tab icon is picked up
when VECTOR is restarted.

## VECTOR's own icon

`icons/` holds the icon the desktop shortcut uses
(`tools/make_shortcut.py`): a white "V" on the app's blue.

| File                   | Used for                                          |
|------------------------|---------------------------------------------------|
| `icons/vector.svg`     | The drawing, for Windows and Linux                |
| `icons/vector-mac.svg` | The same mark on Apple's icon grid                |
| `icons/vector.ico`     | Windows: 16 to 256 px                             |
| `icons/vector.icns`    | macOS: 16 to 1024 px, Retina sizes included       |
| `icons/vector-256.png` | Linux                                             |
| `icons/vector-512.png` | Anywhere a large picture of the icon is needed    |

These are distributed with VECTOR, unlike the unit branding above.
