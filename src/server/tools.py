# src/server/tools.py
import requests

UCSC_BASE = "https://api.genome.ucsc.edu"

def parse_region(region: str):
    """
    Parse UCSC-style region strings, e.g. 'chr1:1000-2000'.
    Returns (chrom, start, end).
    """
    try:
        chrom, coords = region.split(":")
        start, end = map(int, coords.replace(",", "").split("-"))
        return chrom, start, end
    except Exception:
        raise ValueError(f"Invalid region format: {region}. Use e.g. 'chr1:1000-2000'.")

def get_annotations(region: str, genome: str = "hg38", track: str = "knownGene"):
    """
    Example function to get annotations from UCSC.
    """
    chrom, start, end = parse_region(region)

    url = f"{UCSC_BASE}/getData/track"
    payload = {
        "genome": genome,
        "track": track,
        "chrom": chrom,
        "start": start,
        "end": end
    }
    response = requests.get(url, params=payload)
    response.raise_for_status()
    try:
        return response.json()
    except ValueError:
        return {"error": "No valid JSON returned", "text": response.text}