import argparse
import json
import os
from pathlib import Path


def check_file_exists(base_dir: Path, relative_path_str: str) -> bool:
    """Checks if a file exists relative to base_dir or as an absolute path."""
    raw_path = Path(relative_path_str)
    if raw_path.is_absolute():
        return raw_path.exists()
    return (base_dir / raw_path).resolve().exists()


def parse_mtl(mtl_path: Path):
    """Extracts texture map paths from an MTL file."""
    textures = []
    texture_keywords = {
        "map_Kd",
        "map_Ks",
        "map_Ka",
        "map_Bump",
        "bump",
        "map_d",
        "map_Ns",
    }

    try:
        with open(mtl_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                tokens = line.strip().split()
                if not tokens:
                    continue
                # Format: map_Kd path/to/texture.png
                if tokens[0] in texture_keywords and len(tokens) > 1:
                    textures.append(tokens[-1])
    except Exception as e:
        print(f"  [!] Could not read MTL {mtl_path.name}: {e}")

    return textures


def inspect_obj(obj_path: Path):
    """Finds linked MTL files, parses them, and verifies texture presence."""
    base_dir = obj_path.parent
    linked_mtls = []
    missing_assets = []
    found_assets = []

    try:
        with open(obj_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                tokens = line.strip().split()
                if tokens and tokens[0] == "mtllib":
                    linked_mtls.extend(tokens[1:])
    except Exception as e:
        return {"error": f"Failed to read OBJ: {e}"}

    for mtl_name in linked_mtls:
        mtl_file = base_dir / mtl_name
        if not mtl_file.exists():
            missing_assets.append(f"Material Lib (MTL): {mtl_name}")
            continue

        found_assets.append(f"Material Lib (MTL): {mtl_name}")
        textures = parse_mtl(mtl_file)
        for tex in textures:
            if check_file_exists(base_dir, tex):
                found_assets.append(f"Texture: {tex}")
            else:
                missing_assets.append(f"Texture: {tex} (referenced in {mtl_name})")

    return {
        "type": "OBJ",
        "file": obj_path.name,
        "found": found_assets,
        "missing": missing_assets,
    }


def inspect_gltf(gltf_path: Path):
    """Parses GLTF JSON structure to verify linked image URIs."""
    base_dir = gltf_path.parent
    missing_assets = []
    found_assets = []

    try:
        with open(gltf_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"error": f"Failed to parse GLTF JSON: {e}"}

    images = data.get("images", [])
    for img in images:
        uri = img.get("uri")
        # Ignore embedded base64 data URIs
        if uri and not uri.startswith("data:"):
            if check_file_exists(base_dir, uri):
                found_assets.append(f"Texture: {uri}")
            else:
                missing_assets.append(f"Texture: {uri}")

    return {
        "type": "GLTF",
        "file": gltf_path.name,
        "found": found_assets,
        "missing": missing_assets,
    }


def scan_directory(target_dir: str):
    path = Path(target_dir)
    if not path.is_dir():
        print(f"Error: '{target_dir}' is not a valid directory.")
        return

    # Find supported 3D formats
    asset_files = list(path.rglob("*.obj")) + list(path.rglob("*.gltf"))

    if not asset_files:
        print(f"No .obj or .gltf files found in: {target_dir}")
        return

    print(f"\nScanning {len(asset_files)} asset(s) in: {path.resolve()}\n" + "=" * 60)

    total_missing = 0

    for asset in asset_files:
        if asset.suffix.lower() == ".obj":
            report = inspect_obj(asset)
        elif asset.suffix.lower() == ".gltf":
            report = inspect_gltf(asset)
        else:
            continue

        if "error" in report:
            print(f"[-] {asset.name}: {report['error']}")
            continue

        missing_count = len(report["missing"])
        total_missing += missing_count

        status = "[FAIL]" if missing_count > 0 else "[OK]"
        print(f"\n{status} {report['type']}: {asset.name}")

        if report["found"]:
            for item in report["found"]:
                print(f"    + Found:   {item}")

        if report["missing"]:
            for item in report["missing"]:
                print(f"    X MISSING: {item}")

    print("\n" + "=" * 60)
    if total_missing == 0:
        print("All texture and material references are intact!")
    else:
        print(f"Scan complete. Found {total_missing} missing asset reference(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify texture and material dependencies for .obj and .gltf assets."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Path to folder containing 3D models (defaults to current folder)",
    )
    args = parser.parse_args()
    scan_directory(args.directory)