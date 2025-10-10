# src/server/tools.py
import requests

UCSC_BASE = "https://api.genome.ucsc.edu"

def liftover_coordinates(chrom: str, start: int, end: int, from_assembly: str, to_assembly: str):
    """
    Example function to call UCSC REST API for liftover.
    """
    url = f"{UCSC_BASE}/liftover"
    payload = {
        "from": from_assembly,
        "to": to_assembly,
        "chrom": chrom,
        "start": start,
        "end": end
    }
    # This is a placeholder — actual UCSC API may differ
    response = requests.get(url, params=payload)
    response.raise_for_status()
    return response.json()

def get_annotations(chrom: str, start: int, end: int, genome: str = "hg38", track: str = "knownGene"):
    """
    Example function to get annotations from UCSC.
    """
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