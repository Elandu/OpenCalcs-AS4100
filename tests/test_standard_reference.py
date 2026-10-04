from opencalcs_as4100.standards import STANDARD


def test_reference_reports_reviewed_amendment_with_bounded_application():
    descriptor = STANDARD.descriptor()
    assert descriptor["edition"] == "2020"
    assert "Amendment No. 1 (2021) reviewed" in descriptor["amendments"]
    assert "only the covered corrected provisions are applied" in descriptor["amendments"]
