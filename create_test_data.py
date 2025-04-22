#!/usr/bin/env python

import glob
import itertools
import os
import pathlib
import zipfile

import numpy as np
import scipy.ndimage as ndi
import tifffile

data_dir_path = pathlib.Path('data')
tiff_dir_path = data_dir_path / 'images/tiff'
tiff_dir_path.mkdir(parents=True, exist_ok=True)
[os.remove(filepath) for filepath in glob.glob(str(tiff_dir_path / '*.tiff'))]


def create_sample_data(shape, sigma='auto'):
    """
    Create a sample 3D numpy array with the given shape.
    """
    if isinstance(sigma, str) and sigma == 'auto':
        sigma = min(shape) / 2
    np.random.seed(0)
    data = np.random.rand(*shape)
    data = ndi.gaussian_filter(data, sigma=sigma)
    return data


def create_sample_image(data, axes, shape):
    assert len(axes) == len(shape)
    assert len(frozenset(axes) ) == len(axes)
    axes_hint = '_'.join(
        (f'{axis.lower()}{n}' for axis, n in zip(axes, shape))
    )
    filepath = tiff_dir_path / f'{str(data.dtype)}_{axes_hint}.tiff'
    tifffile.imwrite(
        str(filepath),
        data,
        metadata=dict(
            axes=axes,
        ),
    )


def create_sample_images(axes, shape):
    data = create_sample_data(shape)
    create_sample_image(data.astype(np.float16), axes, shape)
    create_sample_image(data.astype(np.float32), axes, shape)
    create_sample_image((data * 0xFF).round().astype(np.uint8), axes, shape)
    create_sample_image((data * 0xFFFF).round().astype(np.uint16), axes, shape)


def join_images(output_filepath, src_filepaths):
    with tifffile.TiffWriter(output_filepath) as tif_out:
        for tif_in in [
            tifffile.TiffFile(filepath) for filepath in src_filepaths
        ]:
            for series in tif_in.series:
                tif_out.write(
                    series.asarray(),
                    metadata=dict(axes=series.axes),
                )


# Assumption: Image axes are a subset of the axes defined below
axes_universe = 'YXZTQCS'

for r in range(2, len(axes_universe) + 1):
    for axes in itertools.combinations(axes_universe, r):
        axes = ''.join(axes)

        # Assumption: Images always have Y and X axes
        if not frozenset('YX') <= frozenset(axes):
            continue

        shape = [5 + i for i in range(len(axes))]
        for complete_axes in (False, True):
            _axes = str(axes)  # copy
            _shape = list(shape)  # copy
            if complete_axes:
                for axis in axes_universe:
                    if axis not in axes:
                        _axes += axis
                        _shape += [1]

            # Assumption: C axis is alias for S axis
            if frozenset('CS') <= frozenset(_axes):
                continue

            create_sample_images(_axes, _shape)
            create_sample_images(_axes[::-1], _shape[::-1])

# In addition, create a test file with multiple images (of equal format)
join_images(
    tiff_dir_path / 'multiseries1.tiff',
    src_filepaths=[
        tiff_dir_path / 'uint8_y5_x6.tiff',
        tiff_dir_path / 'uint8_y5_x6.tiff',
    ],
)


# In addition, create a test file with multiple images (of different format)
join_images(
    tiff_dir_path / 'multiseries2.tiff',
    src_filepaths=[
        tiff_dir_path / 'uint8_y5_x6.tiff',
        tiff_dir_path / 'float32_s7_x6_y5.tiff',
    ],
)

# Create ZIP file to be used in Galaxy
with zipfile.ZipFile(data_dir_path / 'images.zip', 'w') as zipfile:
    for file in glob.glob(str(tiff_dir_path / '*.tiff')):
        zipfile.write(file)