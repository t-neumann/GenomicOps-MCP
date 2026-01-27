# src/server/tools.py
import requests
from typing import List, Dict, Any
import logging
import time, os, json

logger = logging.getLogger(__name__)

CACHE_FILE = os.path.join(os.path.dirname(__file__), "ucsc_genomes_cache.json")
CACHE_TTL = 24 * 3600  # 24 hours

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

def list_ucsc_tracks(genome: str = "hg38", timeout: int = 10) -> Dict[str, Any]:
    """
    List all available UCSC genome browser tracks for a given assembly.

    Example:
        list_ucsc_tracks("hg38")

    Returns:
        dict: Simplified UCSC track metadata, or {"error": "..."} if something fails.
    """
    url = f"{UCSC_BASE}/list/tracks?genome={genome}"

    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        # The main track data is nested under the genome key, e.g. data["hs1"]
        if genome not in data:
            return {"error": f"No track data found for {genome}"}

        tracks = data[genome]

        # Flatten the response into a list of top-level tracks (filter out composite containers)
        simplified_tracks = []
        for track_name, track_info in tracks.items():
            if isinstance(track_info, dict) and "type" in track_info:
                simplified_tracks.append({
                    "track_id": track_name,
                    "shortLabel": track_info.get("shortLabel"),
                    "longLabel": track_info.get("longLabel"),
                    "type": track_info.get("type"),
                    "group": track_info.get("group"),
                    "bigDataUrl": track_info.get("bigDataUrl"),
                    "html": track_info.get("html"),
                })

        return {
            "genome": genome,
            "track_count": len(simplified_tracks),
            "tracks": simplified_tracks,
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Failed to fetch tracks for {genome}: {e}"}
    except ValueError:
        return {"error": f"Invalid JSON returned for {genome} tracks"}
    
# ---------------------------------------------------------------------
# UCSC genome listing utilities
# ---------------------------------------------------------------------

def fetch_ucsc_genomes(timeout: int = 10, use_cache: bool = True) -> list[dict[str, Any]]:
    """
    Fetch /list/ucscGenomes and return a normalized list of genome dicts with optional local JSON caching.
    Cache automatically refreshes every 24h (configurable via CACHE_TTL).
    Handles both list and dict-of-dicts shapes.
    """

    if use_cache and os.path.exists(CACHE_FILE):
        mtime = os.path.getmtime(CACHE_FILE)
        age = time.time() - mtime
        if age < CACHE_TTL:
            try:
                with open(CACHE_FILE, "r") as f:
                    data = json.load(f)
                    if data:
                        return data
            except Exception:
                # corrupted cache, ignore and refetch
                pass

    url = f"{UCSC_BASE}/list/ucscGenomes"
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    genomes = extract_ucsc_genomes(data)

    if use_cache:
        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump(genomes, f, indent=2)
        except Exception as e:
            print(f"Warning: could not write cache: {e}")

    return genomes


def extract_ucsc_genomes(data: dict) -> list[dict[str, Any]]:
    """
    Extract UCSC genomes grouped by species.

    Returns a list of dicts like:
    [
      {
        "speciesKey": "Ailuropoda melanoleuca",
        "scientificName": "Ailuropoda melanoleuca",
        "commonName": "Panda",
        "count": 1,
        "assemblies": [
          {"genome": "ailMel1", "assemblyName": "Dec. 2009 (BGI-Shenzhen 1.0/ailMel1)"}
        ]
      },
      ...
    ]
    """
    genomes = data.get("ucscGenomes", {})
    species_map: dict[str, dict[str, Any]] = {}

    for genome_id, info in genomes.items():

        sci = info.get("scientificName")
        common = info.get("organism") or info.get("genome")

        if not sci:
            continue

        if sci not in species_map:
            species_map[sci] = {
                "speciesKey": sci,
                "scientificName": sci,
                "commonName": common,
                "assemblies": [],
            }

        species_map[sci]["assemblies"].append({
            "genome": genome_id,
            "assemblyName": info.get("description") or genome_id,
        })

    for s in species_map.values():
        s["count"] = len(s["assemblies"])

    return sorted(species_map.values(), key=lambda x: x["scientificName"])

def get_species(genomes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Aggregate unique species from UCSC genome data.
    Returns a list of species with available assemblies.
    """
    species_list = []

    for s in genomes:
        species_list.append({
            "speciesKey": s.get("speciesKey"),
            "scientificName": s.get("scientificName"),
            "commonName": s.get("commonName"),
            "count": s.get("count"),
            "assemblies": [
                {
                    "genome": a.get("genome"),
                    "assemblyName": a.get("assemblyName")
                } for a in s.get("assemblies", [])
            ]
        })

    return species_list


def get_assemblies(species_name: str, genomes: list[dict[str, Any]], exact: bool = False) -> dict[str, Any]:
    """
    Return all assemblies for a given species, matched by:
      - scientific name
      - common name
      - (optional) partial match if exact=False

    Returns a dict containing:
      - matched_species: canonical scientific name
      - assemblies: list of assemblies
    """
    species_name_lower = species_name.lower()

    # First pass — exact match
    for entry in genomes:
        sci = entry.get("scientificName", "").lower()
        common = entry.get("commonName", "").lower()

        if species_name_lower in (sci, common):
            return {
                "matched_species": entry["scientificName"],
                "assemblies": entry["assemblies"],
            }

    # Optional fuzzy match
    if not exact:
        for entry in genomes:
            sci = entry.get("scientificName", "").lower()
            common = entry.get("commonName", "").lower()

            if species_name_lower in sci or species_name_lower in common:
                return {
                    "matched_species": entry["scientificName"],
                    "assemblies": entry["assemblies"],
                }

    # Nothing found
    return {"error": f"No assemblies found for species matching '{species_name}'"}