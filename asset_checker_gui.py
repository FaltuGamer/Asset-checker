import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ---------------- Core Parsing Functions ----------------
def check_file_exists(base_dir: Path, relative_path_str: str) -> bool:
    raw_path = Path(relative_path_str)
    if raw_path.is_absolute():
        return raw_path.exists()
    return (base_dir / raw_path).resolve().exists()


def parse_mtl(mtl_path: Path):
    textures = []
    keywords = {
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
                if tokens and tokens[0] in keywords and len(tokens) > 1:
                    textures.append(tokens[-1])
    except Exception:
        pass
    return textures


def inspect_obj(obj_path: Path):
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
        for tex in parse_mtl(mtl_file):
            if check_file_exists(base_dir, tex):
                found_assets.append(f"Texture: {tex}")
            else:
                missing_assets.append(
                    f"Texture: {tex} (referenced in {mtl_name})"
                )

    return {
        "type": "OBJ",
        "file": obj_path.name,
        "found": found_assets,
        "missing": missing_assets,
    }


def inspect_gltf(gltf_path: Path):
    base_dir = gltf_path.parent
    missing_assets = []
    found_assets = []

    try:
        with open(gltf_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {"error": f"Failed to parse GLTF: {e}"}

    for img in data.get("images", []):
        uri = img.get("uri")
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


# ---------------- Tkinter GUI Application ----------------
class AssetCheckerApp:

    def __init__(self, root):
        self.root = root
        self.root.title("3D Asset Dependency Checker")
        self.root.geometry("780x560")
        self.root.minsize(640, 420)

        self._build_ui()

    def _build_ui(self):
        # Top Path Selection Frame
        top_frame = ttk.Frame(self.root, padding="12")
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="Asset Folder:").pack(
            side=tk.LEFT, padx=(0, 6)
        )

        self.path_var = tk.StringVar()
        self.entry_path = ttk.Entry(
            top_frame, textvariable=self.path_var, font=("Segoe UI", 9)
        )
        self.entry_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        browse_btn = ttk.Button(
            top_frame, text="Browse...", command=self.browse_folder
        )
        browse_btn.pack(side=tk.LEFT, padx=4)

        scan_btn = ttk.Button(
            top_frame, text="Run Scan", command=self.run_scan
        )
        scan_btn.pack(side=tk.LEFT, padx=(4, 0))

        # Text Console Output Area
        output_frame = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        output_frame.pack(fill=tk.BOTH, expand=True)

        self.console = tk.Text(
            output_frame,
            wrap=tk.WORD,
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white",
            font=("Consolas", 10),
            padx=10,
            pady=10,
        )
        scrollbar = ttk.Scrollbar(
            output_frame, orient=tk.VERTICAL, command=self.console.yview
        )
        self.console.configure(yscrollcommand=scrollbar.set)

        self.console.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Style tags for colored log lines
        self.console.tag_config(
            "ok", foreground="#4ec9b0", font=("Consolas", 10, "bold")
        )
        self.console.tag_config(
            "fail", foreground="#f14c4c", font=("Consolas", 10, "bold")
        )
        self.console.tag_config("found", foreground="#9cdcfe")
        self.console.tag_config("missing", foreground="#ce9178")
        self.console.tag_config(
            "header", foreground="#569cd6", font=("Consolas", 10, "bold")
        )

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select 3D Asset Directory")
        if folder:
            self.path_var.set(folder)

    def log(self, text, tag=None):
        self.console.insert(tk.END, text + "\n", tag)
        self.console.see(tk.END)

    def run_scan(self):
        target = self.path_var.get().strip()
        if not target:
            messagebox.showwarning(
                "Missing Path", "Please select or type a folder path to scan."
            )
            return

        target_dir = Path(target)
        if not target_dir.is_dir():
            messagebox.showerror(
                "Invalid Directory", "The specified folder does not exist."
            )
            return

        self.console.delete("1.0", tk.END)
        self.log(f"Scanning directory: {target_dir.resolve()}", "header")
        self.log("-" * 65)

        assets = list(target_dir.rglob("*.obj")) + list(
            target_dir.rglob("*.gltf")
        )
        if not assets:
            self.log(
                "No .obj or .gltf files found in the selected folder.", "missing"
            )
            return

        total_missing = 0

        for asset in assets:
            report = (
                inspect_obj(asset)
                if asset.suffix.lower() == ".obj"
                else inspect_gltf(asset)
            )

            if "error" in report:
                self.log(f"[-] {asset.name}: {report['error']}", "fail")
                continue

            missing_count = len(report["missing"])
            total_missing += missing_count

            if missing_count > 0:
                self.log(f"\n[FAIL] {report['type']}: {asset.name}", "fail")
            else:
                self.log(f"\n[OK]   {report['type']}: {asset.name}", "ok")

            for item in report["found"]:
                self.log(f"    + Found:   {item}", "found")
            for item in report["missing"]:
                self.log(f"    X MISSING: {item}", "missing")

        self.log("\n" + "=" * 65)
        if total_missing == 0:
            self.log(
                "SUCCESS: All texture dependencies are intact!", "ok"
            )
        else:
            self.log(
                f"Scan Complete: {total_missing} missing texture reference(s) found.",
                "fail",
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = AssetCheckerApp(root)
    root.mainloop()