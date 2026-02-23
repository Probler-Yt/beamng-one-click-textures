<div align="center">

```
██████╗ ███████╗ █████╗ ███╗   ███╗███╗   ██╗ ██████╗ 
██╔══██╗██╔════╝██╔══██╗████╗ ████║████╗  ██║██╔════╝ 
██████╔╝█████╗  ███████║██╔████╔██║██╔██╗ ██║██║  ███╗
██╔══██╗██╔══╝  ██╔══██║██║╚██╔╝██║██║╚██╗██║██║   ██║
██████╔╝███████╗██║  ██║██║ ╚═╝ ██║██║ ╚████║╚██████╔╝
╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═══╝ ╚═════╝ 
         AUTO TEXTURE ASSIGN BLENDER ADDON
```

### **Stop clicking. Start rendering.**
*A Blender addon that reads BeamNG.drive vehicle files and auto-assigns every texture in one click.*

---

![Blender](https://img.shields.io/badge/Blender-4.0%2B-orange?style=for-the-badge&logo=blender&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![BeamNG](https://img.shields.io/badge/BeamNG.drive-Compatible-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)
![Version](https://img.shields.io/badge/Version-2.1-red?style=for-the-badge)

</div>

---

## 🔥 What Is This?

You've imported a BeamNG car into Blender. It looks like a grey ghost. You've got **60+ materials** staring at you with zero textures assigned. The DDS files are right there. The materials.json is right there. But you'd still have to manually drag-drop every single texture into every single material slot, set the colour spaces, plug them into the right Principled BSDF inputs...

**Yeah. No.**

This addon reads BeamNG's own `.materials.json` definitions and DDS texture files, then wires everything up automatically — base colour, normals, roughness, metallic, emission, opacity — all in one click.

---

## ✨ Features

- 🧠 **Smart JSON-first matching** — reads BeamNG's own `.materials.json` for pixel-perfect texture assignments
- 🔍 **Filename fallback** — catches light materials and anything the JSON doesn't cover
- 💡 **Handles dummy light materials** — brake lights, DRLs, signals, highbeams all fall back to the correct shared light texture set automatically  
- ♻️ **Deduplicates Blender's `.001` clones** — no more re-assigning the same material 3 times
- 🎯 **Correct colour spaces automatically** — roughness/metallic/normal maps are set to Non-Color, no manual fixing
- 🔌 **Full PBR node setup** — every texture lands in the right Principled BSDF socket with Normal Map nodes inserted where needed
- 🚗 **Works on any BeamNG car** — Vivace, Sunburst, Covet, D-Series, ETK, Bolide, you name it

---

## 📸 Before / After

| Before | After |
|--------|-------|
| 60+ grey materials, everything unassigned | Full PBR materials, ready to render |
| Manual drag-drop nightmare | One button click |
| 2 hours of your life gone | 10 seconds |
| ![Before](assets/Before.gif) | ![After](assets/After.gif) |


> *"Some people are brave and insane enough to do all that manually. This addon is for the rest of us."*

---

## ⚡ Quick Start

### 1. Extract your vehicle folder

Grab the car's `.zip` from your BeamNG content folder:
```
C:\Program Files (x86)\Steam\steamapps\common\BeamNG.drive\content\vehicles\
```
Extract it somewhere accessible. You need the full folder with the `.dae`, `.dds`, and `.materials.json` files all in one place.

> **Note:** BeamNG ships everything as zips. Just right-click → Extract All into a folder on your Desktop.

---

### 2. Install the addon

1. Download `beamng_texture_assign.py`
2. Open Blender → **Edit** → **Preferences** → **Add-ons**
3. Click **Install** and select the `.py` file
4. Search `BeamNG` and tick the checkbox to enable it

> ⚠️ **Blender 5.0+ users:** The Collada (`.dae`) importer was removed. Install an older Blender (4.x) **alongside** your current version just for importing — your main version still works fine for everything else. <https://download.blender.org/release/Blender4.5/>

---

### 3. Import your car

In **Blender 3.x** → **File** → **Import** → **Collada (.dae)**  
Navigate to your extracted vehicle folder and import the `.dae` file.

---

### 4. Run the addon

1. Select any object in the scene
2. Open the **Properties panel** (right sidebar) → **Material Properties** (sphere icon)
3. Scroll down to the **"BeamNG Auto Texture v2.1"** panel
4. Click **Auto-Assign BeamNG Textures**
5. Navigate to your extracted vehicle folder → **Accept**

That's it. Watch the console light up with ✓ marks.

---

## 📊 What Gets Matched

| Socket | Source |
|--------|--------|
| Base Color | `_b.color` / `_d.color` / JSON `baseColorMap` |
| Normal | `_n.normal` / `_nm.normal` / JSON `normalMap` |
| Roughness | `_r.data` / JSON `roughnessMap` |
| Metallic | `_m.data` / JSON `metallicMap` |
| Emission | `_g.color` / JSON `emissiveMap` |
| Alpha/Opacity | `_o.data` / JSON `opacityMap` |
| Ambient Occlusion | `_ao.data` - *loaded but not wired (bake separately)* |

---

## ⚠️ Known Limitations

| Material | Why it can't be fixed |
|----------|----------------------|
| `vivace_gauges_screen` | BeamNG renders gauges as a **live Chromium webpage** - not a texture |
| `vivace_gps_screen` | Same as above |
| `mirror_CE / CX / F` | Shared BeamNG asset - lives in another car's folder |
| `generic_race_decals` | Shared asset - not in the vehicle folder |
| `branded_sunstrip` | Shared asset |
| `glass_invisible` | Intentionally invisible material - no texture exists |

These are BeamNG engine limitations, not addon bugs. Everything that *can* be textured *will* be textured.

---

## 🗂️ Tested Vehicles

| Vehicle | Result |
|---------|--------|
| Civetta Vivace | ✅ 60/75 materials textured |
| *(More coming - test it and let me know!)* | |

---

## 🔧 How It Works

The addon uses a two-pass strategy:

**Pass 1 - JSON matching**  
Reads every `*.materials.json` file in the vehicle folder. BeamNG stores exact texture paths in these files using a `mapTo` field that matches directly to Blender's material names after import. This is the most accurate method.

**Pass 2 - Filename fallback**  
For materials that use BeamNG's glowMap system (lights, indicators etc), the JSON contains empty stages with no texture paths. The addon falls back to scanning DDS filenames and matching them by the consistent BeamNG naming convention (`vivace_taillight` → `vivace_lights_*.dds`).

**Deduplication**  
Blender creates `.001` / `.002` clones of materials during import. The addon detects these, looks up what was assigned to the base material, and copies it rather than doing the lookup twice.

---

## 🤝 Contributing

PRs welcome! Especially interested in:
- Testing on more BeamNG vehicles and reporting results
- Support for the BeamNG `common` shared assets folder
- Blender 5.x compatibility improvements

---

## 📜 License

MIT -- do whatever you want with it, just don't claim you wrote it from scratch.

---

<div align="center">

**Made out of spite for doing this manually.**  
*If this saved you 2 hours, consider dropping a ⭐*

</div>
