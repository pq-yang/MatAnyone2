import numpy as np

from matanyone2.webapp.services.masking import merge_masks


def test_merge_masks_collapses_multiple_targets_into_single_uint8_mask():
    mask_a = np.array([[1, 0], [0, 0]], dtype=np.uint8)
    mask_b = np.array([[0, 0], [1, 0]], dtype=np.uint8)

    merged = merge_masks([mask_a, mask_b])

    assert merged.dtype == np.uint8
    assert merged.tolist() == [[255, 0], [255, 0]]
