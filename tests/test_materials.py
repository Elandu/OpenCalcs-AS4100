# SPDX-License-Identifier: AGPL-3.0-only
import pytest

from opencalcs_as4100.materials import run_materials


def strength(product, form, grade, thickness):
    return run_materials(
        {
            "operation": "tabulated_strength",
            "product_standard": product,
            "form": form,
            "grade": grade,
            "material_thickness_mm": thickness,
        }
    )["values"]


@pytest.mark.parametrize(
    "product,form,grade,t,fy,fu",
    [
        ("AS/NZS 1163", "hollow_sections", "C250", 40, 250, 320),
        ("AS/NZS 1594", "plate_strip_floorplate", "HA400", 80, 380, 460),
        ("AS/NZS 1594", "plate_strip", "XF500", 8, 480, 570),
        ("AS/NZS 1594", "plate_strip", "XF400", 8, 380, 460),
        ("AS/NZS 3678", "plate_floorplate", "450", 20, 450, 520),
        ("AS/NZS 3678", "plate_floorplate", "450", 20.001, 420, 500),
        ("AS/NZS 3678", "plate_floorplate", "350", 80, 340, 450),
        ("AS/NZS 3678", "plate_floorplate", "350", 80.001, 330, 450),
        ("AS/NZS 3678", "plate_floorplate", "300", 12, 310, 430),
        ("AS/NZS 3678", "plate_floorplate", "300", 12.001, 300, 430),
        ("AS/NZS 3678", "plate_floorplate", "250", 80, 240, 410),
        ("AS/NZS 3679.1", "flats_sections", "350", 11, 360, 480),
        ("AS/NZS 3679.1", "flats_sections", "350", 11.001, 340, 480),
        ("AS/NZS 3679.1", "flats_sections", "350", 40, 330, 480),
        ("AS/NZS 3679.2", "welded_i_sections", "350", 16, 350, 450),
        ("AS/NZS 3679.1", "hexagons_rounds_squares", "300", 100, 280, 440),
        ("AS 3597", "plate", "700", 5, 650, 750),
        ("AS 3597", "plate", "700", 5.001, 690, 790),
        ("AS 3597", "plate", "700", 65.001, 620, 720),
    ],
)
def test_table_2_1_product_grade_and_thickness(product, form, grade, t, fy, fu):
    assert strength(product, form, grade, t) == {
        "yield_strength_mpa": fy,
        "tensile_strength_mpa": fu,
    }


@pytest.mark.parametrize(
    "product,form,grade,t",
    [
        ("AS/NZS 3678", "plate_floorplate", "450", 50.001),
        ("AS/NZS 3678", "plate_floorplate", "350", 150.001),
        ("AS 3597", "plate", "600", 110.001),
    ],
)
def test_table_2_1_rejects_out_of_range_thickness(product, form, grade, t):
    with pytest.raises(ValueError, match="No unique Table 2.1"):
        strength(product, form, grade, t)
