import pytest

from rtk.data_io.loaders import SAMPLE_DIR


@pytest.mark.parametrize(
    "name",
    ["pz_field_volumetric.csv", "pz_field_waterdrive.csv"],
)
def test_sample_files_ship_in_package(name):
    assert (SAMPLE_DIR / name).is_file()
