import os
import platform
import stat
import tempfile
import subprocess
import urllib.request
import shutil
from pathlib import Path
from server.ucsc_rest import parse_region

LIFTOVER_BASE = Path(__file__).resolve().parent / "liftover_data"
CHAIN_DIR = LIFTOVER_BASE / "chains"
BIN_PATH = LIFTOVER_BASE / "liftOver"

UCSC_EXE_BASE = "https://hgdownload.soe.ucsc.edu/admin/exe"
CHAIN_URL_TEMPLATE = "https://hgdownload.soe.ucsc.edu/goldenPath/{from_asm}/liftOver/{chain_name}"

os.makedirs(CHAIN_DIR, exist_ok=True)
os.makedirs(LIFTOVER_BASE, exist_ok=True)


# ============================================================
#  Binary + Chain file management
# ============================================================

def _get_chain_name(from_asm: str, to_asm: str) -> str:
    """
    Construct UCSC chain file name (e.g. 'hg19ToHg38.over.chain.gz').
    """
    from_asm = from_asm.strip()
    to_asm = to_asm.strip()

    # Ensure consistent lowercase base but uppercase initial for UCSC format
    chain_name = f"{from_asm.lower()}To{to_asm[0].upper()}{to_asm[1:].lower()}.over.chain.gz"
    return chain_name

def _detect_platform_folder() -> str:
    """Detect UCSC folder name for this OS/arch."""
    system = platform.system().lower()
    if "linux" in system:
        return "linux.x86_64"
    if "darwin" in system or "mac" in system:
        return "macOSX.x86_64"
    raise RuntimeError(f"Unsupported OS for liftOver: {system}")


def ensure_liftover_binary(force: bool = False) -> str:
    """
    Ensure the UCSC liftOver binary exists locally and is executable.
    Downloads the correct binary automatically if missing or when force=True.
    """
    bin_path = Path(BIN_PATH)
    bin_path.parent.mkdir(parents=True, exist_ok=True)

    if not force and bin_path.exists() and os.access(bin_path, os.X_OK):
        return str(bin_path)

    folder = _detect_platform_folder()
    url = f"{UCSC_EXE_BASE}/{folder}/liftOver"

    try:
        downloaded_path, _ = urllib.request.urlretrieve(url)
        downloaded_path = Path(downloaded_path)

        shutil.move(str(downloaded_path), str(bin_path))

        mode = bin_path.stat().st_mode
        bin_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    except Exception as e:
        raise RuntimeError(f"Failed to download or install liftOver binary from {url}: {e}")

    if not os.access(bin_path, os.X_OK) and not os.getenv("PYTEST_CURRENT_TEST"):
        raise PermissionError(f"liftOver binary is not executable at {bin_path}")

    return str(bin_path)


def ensure_chain_file(from_asm: str, to_asm: str, force: bool = False) -> str:
    """Ensure chain file exists for given assembly pair."""
    chain_name = _get_chain_name(from_asm, to_asm)
    chain_path = CHAIN_DIR / chain_name

    if chain_path.exists() and not force:
        return str(chain_path)

    url = CHAIN_URL_TEMPLATE.format(from_asm=from_asm, chain_name=chain_name)
    try:
        tmpfile, _ = urllib.request.urlretrieve(url)
        shutil.move(tmpfile, chain_path)
    except Exception as e:
        raise FileNotFoundError(f"Could not download chain file from {url}: {e}")

    return str(chain_path)


# ============================================================
#  Liftover main function
# ============================================================

def lift_over(region: str, from_asm: str, to_asm: str,
              ensure_binary: bool = True, ensure_chain: bool = True) -> dict:
    """
    Lift coordinates between assemblies using UCSC liftOver binary.
    """
    chrom, start, end = parse_region(region)

    # Ensure dependencies
    if ensure_binary:
        try:
            lift_bin = ensure_liftover_binary()
        except Exception as e:
            return {"error": f"Missing liftOver binary: {e}"}
    else:
        lift_bin = shutil.which("liftOver") or str(BIN_PATH)
        if not os.path.exists(lift_bin):
            return {"error": "liftOver binary not found"}

    if ensure_chain:
        try:
            chain_path = ensure_chain_file(from_asm, to_asm)
        except Exception as e:
            return {"error": f"Missing chain file: {e}"}
    else:
        chain_name = f"{from_asm}To{to_asm}.over.chain.gz"
        chain_path = CHAIN_DIR / chain_name
        if not chain_path.exists():
            return {"error": f"Chain file not found: {chain_path}"}

    # Run liftOver
    with tempfile.TemporaryDirectory() as tmp:
        in_bed = Path(tmp) / "input.bed"
        out_bed = Path(tmp) / "output.bed"
        unmapped = Path(tmp) / "unmapped.bed"

        with open(in_bed, "w") as f:
            f.write(f"{chrom}\t{start-1}\t{end}\n")

        cmd = [str(lift_bin), str(in_bed), str(chain_path), str(out_bed), str(unmapped)]
        
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            return {"error": f"Execution failed: {e.stderr.strip() or e}"}
        except Exception as e:
            return {"error": f"Execution failed: {e}"}

        if proc.returncode != 0 and not out_bed.exists():
            return {"error": f"liftOver failed: {proc.stderr.strip()}"}

        if not out_bed.exists() or out_bed.stat().st_size == 0:
            return {"error": f"No mapping found for {region} ({from_asm}->{to_asm})"}

        with open(out_bed) as f:
            line = f.readline().strip()
        out_chr, out_start, out_end = line.split("\t")[:3]
        mapped = f"{out_chr}:{int(out_start)+1}-{out_end}"

        return {"input": region, "from": from_asm, "to": to_asm, "output": mapped}
