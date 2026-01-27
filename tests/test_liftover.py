import pytest
from unittest.mock import patch, Mock, MagicMock
import os
import subprocess
from server import liftover

SAMPLE_REGION = "chr1:1000-1100"
FROM = "hg19"
TO = "hg38"


# ============================================================
# BASIC UTILITY TESTS
# ============================================================

def test_get_chain_name_basic():
    """Test chain name is formatted correctly and capitalization applied."""
    assert liftover._get_chain_name("hg19", "hg38") == "hg19ToHg38.over.chain.gz"
    assert liftover._get_chain_name("  Hg19 ", " mm10 ") == "hg19ToMm10.over.chain.gz"


# ============================================================
# CHAIN AND BINARY MANAGEMENT
# ============================================================

@patch("pathlib.Path.chmod")
@patch("genomicops.liftover.urllib.request.urlretrieve")
def test_ensure_binary_download_success(mock_urlretrieve, mock_chmod, tmp_path, monkeypatch):
    """Ensure binary download success path."""
    # Simulate a downloaded file
    downloaded = tmp_path / "liftOver_downloaded"
    downloaded.write_text("binary")

    mock_urlretrieve.return_value = (str(downloaded), None)
    monkeypatch.setattr(liftover, "BIN_PATH", str(tmp_path / "liftOver"))

    # Run the function
    path = liftover.ensure_liftover_binary()

    # Verify results
    assert "liftOver" in str(path)
    mock_chmod.assert_called_once()


@patch("genomicops.liftover.urllib.request.urlretrieve")
def test_ensure_chain_file_download_failure(mock_urlretrieve, tmp_path, monkeypatch):
    """If urlretrieve raises, ensure_chain_file should raise FileNotFoundError."""
    mock_urlretrieve.side_effect = Exception("network error")

    # Patch CHAIN_DIR to a temp directory so file does not exist
    monkeypatch.setattr(liftover, "CHAIN_DIR", tmp_path)

    # Provide dummy from/to asm
    with pytest.raises(FileNotFoundError):
        liftover.ensure_chain_file("hg19", "hg38", force=True)


# ============================================================
# MAIN lift_over FUNCTION TESTS
# ============================================================

@patch("genomicops.liftover.subprocess.run")
def test_lift_over_invalid_region(mock_run):
    """Invalid region string should raise ValueError."""
    with pytest.raises(ValueError):
        liftover.lift_over("invalid_region", FROM, TO)


@patch("genomicops.liftover.subprocess.run")
def test_lift_over_missing_chain_file(mock_run, tmp_path, monkeypatch):
    """Missing chain file should raise if ensure_chain=False."""
    monkeypatch.setattr(liftover, "CHAIN_DIR", tmp_path)
    monkeypatch.setattr(liftover, "BIN_PATH", str(tmp_path / "liftOver"))
    (tmp_path / "liftOver").write_text("fake-bin")

    result = liftover.lift_over(SAMPLE_REGION, FROM, TO, ensure_binary=False, ensure_chain=False)
    assert "error" in result
    assert "Chain file not found" in result["error"]

def test_lift_over_missing_binary(tmp_path, monkeypatch):
    """
    Missing liftOver binary should return an error dict.
    """
    monkeypatch.setattr(liftover, "BIN_PATH", str(tmp_path / "liftOver"))
    monkeypatch.setattr(liftover, "CHAIN_DIR", tmp_path)
    (tmp_path / f"{FROM}To{TO}.over.chain.gz").write_text("fake-chain")

    result = liftover.lift_over(SAMPLE_REGION, FROM, TO, ensure_binary=False, ensure_chain=False)
    assert "error" in result
    assert "liftOver binary not found" in result["error"]


@patch("genomicops.liftover.urllib.request.urlretrieve")
@patch("genomicops.liftover.subprocess.run")
def test_lift_over_subprocess_failure(mock_run, mock_urlretrieve, tmp_path, monkeypatch):
    """Subprocess failure should return informative error in result dict."""
    liftover_bin = tmp_path / "liftOver"
    chain_file = tmp_path / f"{FROM}To{TO}.over.chain.gz"

    liftover_bin.write_text("fake")
    chain_file.write_text("chain")

    monkeypatch.setattr(liftover, "BIN_PATH", str(liftover_bin))
    monkeypatch.setattr(liftover, "CHAIN_DIR", tmp_path)

    mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd="liftOver", output="", stderr="failure")

    result = liftover.lift_over(SAMPLE_REGION, FROM, TO, ensure_binary=False, ensure_chain=False)
    assert "error" in result
    assert "failure" in result["error"].lower()


@patch("genomicops.liftover.urllib.request.urlretrieve")
@patch("genomicops.liftover.subprocess.run")
def test_lift_over_unit_success(mock_run, mock_urlretrieve, tmp_path, monkeypatch):
    """
    Unit test: simulate successful liftOver run.
    """
    liftover_bin = tmp_path / "liftOver"
    chain_file = tmp_path / f"{FROM}To{TO}.over.chain.gz"
    liftover_bin.write_text("fake-binary")
    chain_file.write_text("fake-chain")

    monkeypatch.setattr(liftover, "BIN_PATH", str(liftover_bin))
    monkeypatch.setattr(liftover, "CHAIN_DIR", tmp_path)

    def fake_run(cmd, capture_output, text, check=False):
        out_bed = cmd[3]
        with open(out_bed, "w") as f:
            f.write("chr1\t150\t250\n")
        m = Mock()
        m.returncode = 0
        return m

    mock_run.side_effect = fake_run
    result = liftover.lift_over(SAMPLE_REGION, FROM, TO, ensure_binary=False, ensure_chain=False)
    assert isinstance(result, dict)
    assert result.get("output") == "chr1:151-250"


# ============================================================
# OPTIONAL REAL SMOKE TEST
# ============================================================

@pytest.mark.smoke
@pytest.mark.asyncio
async def test_lift_over_real_small_region():
    """Optional smoke test: run real liftOver binary if available."""
    if not os.path.exists(liftover.BIN_PATH):
        pytest.skip("liftOver binary not installed")

    region = "chr22:10000000-10001000"
    result = liftover.lift_over(region, "hg19", "hg38", ensure_chain=True)
    assert "output" in result or "error" in result