bl_info = {
    "name": "BeamNG Auto Texture Assign",
    "author": "Probler",
    "version": (2, 4),
    "blender": (3, 0, 0),
    "location": "Properties > Material > BeamNG Auto Texture",
    "description": "Reads BeamNG .materials.json and assigns textures. Falls back to filename matching.",
    "category": "Material",
}

import bpy
import os
import re
import json
from pathlib import Path

# ─────────────────────────────────────────────
# JSON field → (Blender socket, is_normal)
# ─────────────────────────────────────────────
JSON_FIELD_MAP = {
    "baseColorMap":        ("Base Color",     False),
    "normalMap":           ("Normal",         True),
    "roughnessMap":        ("Roughness",      False),
    "metallicMap":         ("Metallic",       False),
    "ambientOcclusionMap": ("AO",             False),
    "emissiveMap":         ("Emission Color", False),
    "opacityMap":          ("Alpha",          False),
    "clearCoatMap":        ("Coat Weight",    False),
}

# DDS filename suffix → (Blender socket, is_normal)
SUFFIX_MAP = {
    "b.color":   ("Base Color",     False),
    "d.color":   ("Base Color",     False),
    "c.color":   ("Base Color",     False),
    "cc.data":   ("Base Color",     False),
    "p.color":   ("Base Color",     False),
    "da.color":  ("Base Color",     False),
    "b":         ("Base Color",     False),
    "d":         ("Base Color",     False),
    "n.normal":  ("Normal",         True),
    "nm.normal": ("Normal",         True),
    "n":         ("Normal",         True),
    "r.data":    ("Roughness",      False),
    "r":         ("Roughness",      False),
    "m.data":    ("Metallic",       False),
    "m":         ("Metallic",       False),
    "ao.data":   ("AO",             False),
    "ao":        ("AO",             False),
    "s.color":   ("Specular",       False),
    "s":         ("Specular",       False),
    "o.data":    ("Alpha",          False),
    "o":         ("Alpha",          False),
    "g.color":   ("Emission Color", False),
    "g":         ("Emission Color", False),
}

SUFFIX_KEYS_SORTED = sorted(SUFFIX_MAP.keys(), key=len, reverse=True)

LIGHT_SUFFIXES = (
    "brakelight_l", "brakelight_r", "chmsl",
    "drl", "drl_signal_l", "drl_signal_r",
    "highbeam", "lowbeam", "reverselight",
    "signal_l", "signal_r", "taillight",
)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def strip_blender_index(name):
    return re.sub(r'\.\d{3}$', '', name)


def resolve_texture_path(json_path, vehicle_folder):
    """Find actual file on disk from a JSON texture path."""
    if not json_path or json_path.startswith("@"):
        return None
    filename = os.path.basename(json_path)
    stem = Path(filename).stem
    for ext in (".dds", ".DDS", ".png", ".jpg"):
        candidate = os.path.join(vehicle_folder, stem + ext)
        if os.path.isfile(candidate):
            return candidate
    for f in Path(vehicle_folder).rglob(stem + ".*"):
        if f.suffix.lower() in (".dds", ".png", ".jpg"):
            return str(f)
    return None


def parse_materials_json(vehicle_folder):
    """
    Read all *.materials.json in vehicle_folder.
    Returns dict: mapTo_lower -> { socket_name -> (abs_path, is_normal) }
    Only includes entries that have at least one resolved texture.
    """
    material_map = {}
    for json_file in Path(vehicle_folder).rglob("*.materials.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[BeamNG Tex] Could not read {json_file}: {e}")
            continue

        for mat_key, mat_def in data.items():
            if not isinstance(mat_def, dict):
                continue
            map_to = mat_def.get("mapTo") or mat_def.get("name") or mat_key
            map_to_lower = map_to.lower()
            tex_paths = {}

            for stage in mat_def.get("Stages", []):
                if not isinstance(stage, dict):
                    continue
                for field, (socket, is_normal) in JSON_FIELD_MAP.items():
                    val = stage.get(field)
                    if val and isinstance(val, str) and not val.startswith("@"):
                        resolved = resolve_texture_path(val, vehicle_folder)
                        if resolved and socket not in tex_paths:
                            tex_paths[socket] = (resolved, is_normal)

            # Only store if we actually found textures (skip dummy/empty materials)
            if tex_paths:
                if map_to_lower not in material_map:
                    material_map[map_to_lower] = tex_paths
                else:
                    for socket, val in tex_paths.items():
                        if socket not in material_map[map_to_lower]:
                            material_map[map_to_lower][socket] = val

    return material_map


def parse_stem_filename(stem):
    """filename stem -> (mat_name_lower, suffix_key) or (None, None)"""
    stem_lower = stem.lower()
    for key in SUFFIX_KEYS_SORTED:
        if stem_lower.endswith("_" + key):
            return stem_lower[: -(len(key) + 1)], key
    return None, None


def build_filename_lookup(vehicle_folder):
    """Fallback: scan DDS files by name. Returns mat_name_lower -> {suffix -> abs_path}"""
    lookup = {}
    for f in Path(vehicle_folder).rglob("*"):
        if f.suffix.lower() not in (".dds", ".png", ".jpg"):
            continue
        mat_name, suffix_key = parse_stem_filename(f.stem)
        if mat_name is None:
            continue
        if mat_name not in lookup:
            lookup[mat_name] = {}
        if suffix_key not in lookup[mat_name]:
            lookup[mat_name][suffix_key] = str(f)
    return lookup


def filename_lookup_to_socket_map(suffix_dict):
    """Convert suffix->path dict to socket->(path, is_normal) dict."""
    result = {}
    for suffix, path in suffix_dict.items():
        entry = SUFFIX_MAP.get(suffix)
        if entry:
            socket, is_normal = entry
            if socket not in result:
                result[socket] = (path, is_normal)
    return result


def find_by_filename(mat_name_lower, filename_lookup, car_prefix):
    """Try to match via filename, including light fallback and prefix tricks."""
    candidates = [mat_name_lower]

    if car_prefix and not mat_name_lower.startswith(car_prefix):
        candidates.append(car_prefix + "_" + mat_name_lower)

    if car_prefix and mat_name_lower == car_prefix:
        candidates += [car_prefix + "_main", car_prefix + "_body"]

    for light_suffix in LIGHT_SUFFIXES:
        if mat_name_lower.endswith("_" + light_suffix):
            prefix_part = mat_name_lower[: -(len(light_suffix) + 1)]
            candidates += [
                prefix_part + "_lights",
                prefix_part + "_light",
                (car_prefix + "_lights") if car_prefix else None,
            ]
            break

    for candidate in candidates:
        if candidate and candidate in filename_lookup:
            return filename_lookup_to_socket_map(filename_lookup[candidate])

    return None


# ─────────────────────────────────────────────
# Setup material node tree
# ─────────────────────────────────────────────

def setup_material(mat, tex_paths):
    """tex_paths: { socket_name -> (abs_path, is_normal) }"""
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (700, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    x_offset = -400
    y_offset = 600

    for socket_name, (abs_path, is_normal) in tex_paths.items():
        img_node = nodes.new("ShaderNodeTexImage")
        img_node.location = (x_offset, y_offset)
        img_node.label = socket_name
        y_offset -= 300

        img = bpy.data.images.get(os.path.basename(abs_path))
        if img is None:
            try:
                img = bpy.data.images.load(abs_path)
            except Exception as e:
                print(f"[BeamNG Tex] Could not load {abs_path}: {e}")
                nodes.remove(img_node)
                continue

        img_node.image = img

        if is_normal:
            img.colorspace_settings.name = "Non-Color"
            nm_node = nodes.new("ShaderNodeNormalMap")
            nm_node.location = (x_offset + 280, y_offset + 160)
            links.new(img_node.outputs["Color"], nm_node.inputs["Color"])
            if "Normal" in bsdf.inputs:
                links.new(nm_node.outputs["Normal"], bsdf.inputs["Normal"])
        elif socket_name == "AO":
            img.colorspace_settings.name = "Non-Color"
            img_node.label = "AO (not wired - bake separately)"
        elif socket_name in ("Roughness", "Metallic", "Alpha"):
            img.colorspace_settings.name = "Non-Color"
            if socket_name in bsdf.inputs:
                links.new(img_node.outputs["Color"], bsdf.inputs[socket_name])
        else:
            if socket_name in bsdf.inputs:
                links.new(img_node.outputs["Color"], bsdf.inputs[socket_name])


# ─────────────────────────────────────────────
# Operator
# ─────────────────────────────────────────────

class BEAMNG_OT_AutoTexture(bpy.types.Operator):
    bl_idname = "beamng.auto_texture"
    bl_label = "Auto-Assign BeamNG Textures"
    bl_description = "Point at a BeamNG vehicle folder to auto-assign all textures"
    bl_options = {"REGISTER", "UNDO"}

    directory: bpy.props.StringProperty(subtype="DIR_PATH")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        vehicle_folder = self.directory.rstrip("\\/")
        if not vehicle_folder or not os.path.isdir(vehicle_folder):
            self.report({"ERROR"}, "Invalid folder path")
            return {"CANCELLED"}

        car_prefix = os.path.basename(vehicle_folder).lower()
        print(f"[BeamNG Tex] Vehicle: '{vehicle_folder}'  |  prefix: '{car_prefix}'")

        # Primary: JSON-based map
        json_map = parse_materials_json(vehicle_folder)
        print(f"[BeamNG Tex] JSON: {len(json_map)} material definitions with textures")

        # Fallback: filename-based map
        filename_lookup = build_filename_lookup(vehicle_folder)
        print(f"[BeamNG Tex] Filename scan: {len(filename_lookup)} texture sets")

        assigned_json = 0
        assigned_file = 0
        deduped       = 0
        skipped       = []
        base_tex_cache = {}

        for mat in bpy.data.materials:
            raw_name  = mat.name
            base_name = strip_blender_index(raw_name)
            base_key  = base_name.lower()

            # .001 duplicates
            if raw_name != base_name and base_key in base_tex_cache:
                setup_material(mat, base_tex_cache[base_key])
                deduped += 1
                print(f"[BeamNG Tex]  ↪  {raw_name}")
                continue

            # 1. Try JSON first
            tex_paths = json_map.get(base_key)
            source = "json"

            # 2. Fallback to filename matching
            if not tex_paths:
                tex_paths = find_by_filename(base_key, filename_lookup, car_prefix)
                source = "file"

            if tex_paths:
                setup_material(mat, tex_paths)
                base_tex_cache[base_key] = tex_paths
                if source == "json":
                    assigned_json += 1
                    print(f"[BeamNG Tex]  ✓  {raw_name}  ({len(tex_paths)} maps) [json]")
                else:
                    assigned_file += 1
                    print(f"[BeamNG Tex]  ✓  {raw_name}  ({len(tex_paths)} maps) [filename]")
            else:
                skipped.append(raw_name)
                print(f"[BeamNG Tex]  ✗  {raw_name}")

        total = assigned_json + assigned_file + deduped
        msg = (
            f"Done! {total} textured  "
            f"({assigned_json} from JSON, {assigned_file} from filename, {deduped} deduped)  "
            f"| {len(skipped)} skipped"
        )
        self.report({"INFO"}, msg)

        genuinely_missing = [s for s in skipped if not re.search(r'\.\d{3}$', s)]
        if genuinely_missing:
            print("[BeamNG Tex] Genuinely unmatched:")
            for name in genuinely_missing:
                print(f"  - {name}")

        return {"FINISHED"}


# ─────────────────────────────────────────────
# Panel
# ─────────────────────────────────────────────

class BEAMNG_PT_AutoTexturePanel(bpy.types.Panel):
    bl_label = "BeamNG Auto Texture v2.1"
    bl_idname = "BEAMNG_PT_auto_texture"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "material"

    def draw(self, context):
        layout = self.layout
        layout.label(text="Point at extracted BeamNG vehicle folder:")
        layout.operator("beamng.auto_texture", icon="TEXTURE")
        layout.separator()
        layout.label(text="Works on any car - vivace, sunburst,")
        layout.label(text="covet, D-series, and more.")


# ─────────────────────────────────────────────
# Register
# ─────────────────────────────────────────────

classes = (BEAMNG_OT_AutoTexture, BEAMNG_PT_AutoTexturePanel)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
