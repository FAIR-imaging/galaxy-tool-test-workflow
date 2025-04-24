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

tiff_intensity_dir_path = tiff_dir_path / 'intensity'
tiff_intensity_dir_path.mkdir(parents=True, exist_ok=True)
for filepath in glob.glob(str(tiff_intensity_dir_path / '*.tiff')):
    os.remove(filepath)

tiff_binary_dir_path = tiff_dir_path / 'binary'
tiff_binary_dir_path.mkdir(parents=True, exist_ok=True)
for filepath in glob.glob(str(tiff_binary_dir_path / '*.tiff')):
    os.remove(filepath)


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


def create_sample_image(data, axes, shape, target):
    assert len(axes) == len(shape)
    assert len(frozenset(axes) ) == len(axes)
    axes_hint = '_'.join(
        (f'{axis.lower()}{n}' for axis, n in zip(axes, shape))
    )
    match target:
        case 'intensity':
            target_dir_path = tiff_intensity_dir_path
        case 'binary':
            target_dir_path = tiff_binary_dir_path
            assert len(np.unique(data)) == 2
    filepath = target_dir_path / f'{str(data.dtype)}_{axes_hint}.tiff'
    tifffile.imwrite(
        str(filepath),
        data,
        metadata=dict(
            axes=axes,
        ),
    )


def create_sample_images(axes, shape, target, dtypes='all'):
    data = create_sample_data(shape)

    if dtypes == 'all':
        dtypes = (np.float16, np.float32, np.uint8, np.uint16)

    if target == 'binary':
        data = (data > data.mean())

    if np.float16 in dtypes:
        create_sample_image(
            data.astype(np.float16), axes, shape, target,
        )
    if np.float32 in dtypes:
        create_sample_image(
            data.astype(np.float32), axes, shape, target,
        )
    if np.uint8 in dtypes:
        create_sample_image(
            (data * 0xFF).round().astype(np.uint8), axes, shape, target,
        )
    if np.uint16 in dtypes:
        create_sample_image(
            (data * 0xFFFF).round().astype(np.uint16), axes, shape, target,
        )


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

        # Generate the shape of the image
        shape = []
        for axis_idx, axis in enumerate(axes):
            match axis:
                case 'C':
                    shape.append(3)
                case 'S':
                    shape.append(5)
                case _:
                    shape.append(10 + axis_idx)

        # Generate set of images with a subset of axes,
        # as well as by adding the "missing" axes as singletons
        for complete_axes in (
            '',
            frozenset(axes_universe) - {'C'},
            frozenset(axes_universe) - {'S'},
        ):
            _axes = str(axes)  # copy
            _shape = list(shape)  # copy
            for axis in complete_axes:
                if axis not in axes:
                    _axes += axis
                    _shape += [1]

            # Assumption: C axis is alias for S axis
            if frozenset('CS') <= frozenset(_axes):
                continue

            for target in ('intensity', 'binary'):

                # We do not need to test the variety of datatypes jointly with
                #  1) singleton axes (test those only with uint8 below)
                #  2) support for the Q axis (it's enough to test with uint8)
                if complete_axes == '' and 'Q' not in _axes:
                    create_sample_images(_axes, _shape, target)

                create_sample_images(
                    _axes[::-1],
                    _shape[::-1],
                    target,
                    dtypes=[np.uint8],
                )


for target in ('intensity', 'binary'):
    match target:
        case 'intensity':
            target_dir_path = tiff_intensity_dir_path
        case 'binary':
            target_dir_path = tiff_binary_dir_path

    # In addition, create a test file with multiple images (of equal format)
    join_images(
        target_dir_path / 'multiseries1.tiff',
        src_filepaths=[
            target_dir_path / 'uint8_y10_x11.tiff',
            target_dir_path / 'uint8_y10_x11.tiff',
        ],
    )

    # In addition, create a test file with multiple images (different formats)
    join_images(
        target_dir_path / 'multiseries2.tiff',
        src_filepaths=[
            target_dir_path / 'uint8_y10_x11.tiff',
            target_dir_path / 'float32_y10_x11_z12.tiff',
        ],
    )

    # Create ZIP file to be used in Galaxy
    with zipfile.ZipFile(
        data_dir_path / f'tiff-{target}-images.zip', 'w',
    ) as zip_file:
        for file in glob.glob(str(target_dir_path / '*.tiff')):
            zip_file.write(file)