#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
from collections import namedtuple

import numpy as np

try:
    import dask
    import dask.array as da
    from dask.diagnostics import ProgressBar
    import Tigger
    import xarray as xr
    from xarrayms import xds_from_ms, xds_from_table, xds_to_table
except ImportError as e:
    opt_import_error = e
else:
    opt_import_error = None

from africanus.coordinates.dask import radec_to_lm
from africanus.rime.dask import phase_delay, predict_vis
from africanus.model.coherency.dask import convert
from africanus.model.spectral.dask import spectral_model
from africanus.model.shape.dask import gaussian as gaussian_shape
from africanus.model.shape.dask import shapelet as shapelet_fn
from africanus.util.requirements import requires_optional

# Testing stuff
from numpy.testing import assert_array_almost_equal
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable


SOURCE_CHUNKS = 10
Fs = np.fft.fftshift

_einsum_corr_indices = 'ijkl'

def _brightness_schema(corrs, index):
    if corrs == 4:
        return "sf" + _einsum_corr_indices[index:index + 2], index + 1
    else:
        return "sfi", index

def _phase_delay_schema(corrs, index):
    return "srf", index

def _spi_schema(corrs, index):
    return "s", index

def _gauss_shape_schema(corrs, index):
    return "srf", index

def _shapelet_schema(corrs, index):
    return "rfs", index

def _bl_jones_output_schema(corrs, index):
    if corrs == 4:
        return "->srfi" + _einsum_corr_indices[index]
    else:
        return "->srfi"

_rime_term_map = {
    'brightness': _brightness_schema,
    'phase_delay': _phase_delay_schema,
    'spi': _spi_schema,
    'gauss_shape': _gauss_shape_schema,
    'shapelet_shape': _shapelet_schema,
}



def create_parser():
    p = argparse.ArgumentParser()
    p.add_argument("ms")
    p.add_argument("-sm", "--sky-model", default="sky-model-shapelets.txt")
    p.add_argument("-rc", "--row-chunks", type=int, default=10000)
    p.add_argument("-mc", "--model-chunks", type=int, default=10000)
    p.add_argument("-iuvw", "--invert-uvw", action="store_true",
                   help="Invert UVW coordinates. Useful if we want "
                        "compare our visibilities against MeqTrees")
    return p


def parse_sky_model(filename, chunks):
    """
    Parses a Tigger sky model
    Parameters
    ----------
    filename : str
        Sky Model filename
    chunks : tuple of ints or int
        Source chunking strategy
    Returns
    -------
    radec : :class:`numpy.ndarray`
        :code:`(source, 2)` array of source coordinates
    stokes : :class:`numpy.ndarray`
        :code:`(source, 4)` array of stokes parameters
    """
    sky_model = Tigger.load(filename, verbose=False)
    

    point_radec = []
    point_stokes = []
    point_spi = []
    point_ref_freq = []

    gauss_radec = []
    gauss_stokes = []
    gauss_spi = []
    gauss_ref_freq = []
    gauss_shape = []

    shapelet_radec = []
    shapelet_stokes = []
    shapelet_spi = []
    shapelet_ref_freq = []
    shapelet_beta = []
    shapelet_coeffs = []
    max_shapelet_coeffs = 0

    print(sky_model.sources)

    for source in sky_model.sources:
        ra = source.pos.ra
        dec = source.pos.dec
        typecode = source.typecode.lower()

        I = source.flux.I
        Q = source.flux.Q
        U = source.flux.U
        V = source.flux.V

        try:
            ref_freq = source.freq0
        except AttributeError:
            ref_freq = sky_model.freq0

        try:
            spi = source.spi
        except AttributeError:
            spi = [[-0.7, 0, 0, 0]]

        if typecode == "gau":
            emaj = source.shape.ex
            emin = source.shape.ey
            pa = source.shape.pa

            gauss_radec.append([ra, dec])
            gauss_stokes.append([I, Q, U, V])
            gauss_spi.append(spi)
            gauss_ref_freq.append(ref_freq)
            gauss_shape.append([emaj, emin, pa])

        elif typecode == "pnt":
            point_radec.append([ra, dec])
            point_stokes.append([I, Q, U, V])
            point_spi.append(spi)
            point_ref_freq.append(ref_freq)
        elif typecode == "sha":
            beta_l = source.shape.sbetal
            beta_m = source.shape.sbetam
            coeffs = source.shape.shapelet_coeffs

            shapelet_radec.append([ra,dec])
            shapelet_stokes.append([I,Q,U,V])
            shapelet_spi.append(spi)
            shapelet_ref_freq.append(ref_freq)
            shapelet_beta.append([beta_l, beta_m])
            shapelet_coeffs.append(np.array(coeffs))
        else:
            raise ValueError("Unknown source morphology %s" % typecode)

    Point = namedtuple("Point", ["radec", "stokes", "spi", "ref_freq"])
    Gauss = namedtuple("Gauss", ["radec", "stokes", "spi", "ref_freq",
                                 "shape"])
    Shapelet = namedtuple("Shapelet", ["radec", "stokes", "spi", "ref_freq", "beta", "coeffs"])

    return {
        'shapelet': Shapelet(da.from_array(shapelet_radec, chunks=(chunks)),
                             da.from_array(shapelet_stokes, chunks=(chunks, -1)),
                             da.from_array(shapelet_spi, chunks=(chunks, 1, -1)),
                             da.from_array(shapelet_ref_freq, chunks=chunks),
                             da.from_array(shapelet_beta, chunks=(chunks, -1)),
                             da.from_array(shapelet_coeffs, chunks=(chunks)))
    }


def support_tables(args, tables):
    """
    Parameters
    ----------
    args : object
        Script argument objects
    tables : list of str
        List of support tables to open

    Returns
    -------
    table_map : dict of :class:`xarray.Dataset`
        {name: dataset}
    """
    return {t: [ds.compute() for ds in
                xds_from_table("::".join((args.ms, t)),
                               group_cols="__row__")]
            for t in tables}


def corr_schema(pol):
    """
    Parameters
    ----------
    pol : :class:`xarray.Dataset`

    Returns
    -------
    corr_schema : list of list
        correlation schema from the POLARIZATION table,
        `[[9, 10], [11, 12]]` for example
    """

    corrs = pol.NUM_CORR.values
    corr_types = pol.CORR_TYPE.values

    if corrs == 4:
        return [[corr_types[0], corr_types[1]],
                [corr_types[2], corr_types[3]]]  # (2, 2) shape
    elif corrs == 2:
        return [corr_types[0], corr_types[1]]    # (2, ) shape
    elif corrs == 1:
        return [corr_types[0]]                   # (1, ) shape
    else:
        raise ValueError("corrs %d not in (1, 2, 4)" % corrs)

def baseline_jones_multiply(corrs, *args):
    names = args[::2]
    arrays = args[1::2]

    input_einsum_schemas = []
    corr_index = 0

    for name, array in zip(names, arrays):
        try:
            fn = _rime_term_map[name]
        except KeyError:
            raise ValueError("Unknown RIME term '%s'" % name)
        else:
            einsum_schema, corr_index = fn(corrs, corr_index)
            input_einsum_schemas.append(einsum_schema)

            if not len(einsum_schema) == array.ndim:
                raise ValueError("%s len(%s) == %d != %s.ndim"
                                 % (name, einsum_schema,
                                    len(einsum_schema), array.shape))
            assert len(einsum_schema) == array.ndim

    output_schema = _bl_jones_output_schema(corrs, corr_index)
    schema = ",".join(input_einsum_schemas) + output_schema

    return da.einsum(schema, *arrays)

def vis_factory(args, source_type, sky_model, time_index,
                ms, field, spw, pol):
    try:
        source = sky_model[source_type]
    except KeyError:
        raise ValueError("Source type '%s' unsupported" % source_type)

    corrs = pol.NUM_CORR.values

    lm = radec_to_lm(source.radec, field.PHASE_DIR.data)
    uvw = -ms.UVW.data if args.invert_uvw else ms.UVW.data
    frequency = spw.CHAN_FREQ.data

    # (source, row, frequency)
    phase = phase_delay(lm, uvw, frequency)

    # (source, spi, corrs)
    # Apply spectral mode to stokes parameters
    stokes = spectral_model(source.stokes,
                            source.spi,
                            source.ref_freq,
                            frequency,
                            base=0)

    brightness = convert(stokes, ["I", "Q", "U", "V"],
                         corr_schema(pol))

    args = ["phase_delay", phase]

    # Add any visibility amplitude terms
    if source_type == "gauss":
        args.append("gauss_shape")
        args.append(gaussian_shape(uvw, frequency, source.shape))
    if source_type == "shapelet":
        delta_lm = np.array([1 / (10 * np.max(uvw[:, 0])), 1 / (10 * np.max(uvw[:, 1]))])
        delta_lm = da.from_array(delta_lm, chunks=delta_lm.shape)
        frequency = da.from_array(frequency, chunks=frequency.size)
        args.append("shapelet_shape")
        print(uvw.shape, frequency.shape, source.coeffs.shape, source.beta.shape, delta_lm.shape)
        print("coeffs is ", np.array(source.coeffs.compute()).shape)
        print("uvw is ", uvw)
        print("frequency is ", frequency)
        print("beta is ", source.beta)
        print("delta_lm is ", delta_lm)
        args.append(shapelet_fn(uvw, frequency, source.coeffs, source.beta, delta_lm))

    args.extend(["brightness", brightness])

    jones = baseline_jones_multiply(corrs, *args)

    return predict_vis(time_index, ms.ANTENNA1.data, ms.ANTENNA2.data,
                       None, jones, None, None, None, None)


@requires_optional("dask.array", "Tigger",
                   "xarray", "xarrayms", opt_import_error)
def predict(args):
    # Convert source data into dask arrays
    sky_model = parse_sky_model(args.sky_model, args.model_chunks)

    # Get the support tables
    tables = support_tables(args, ["FIELD", "DATA_DESCRIPTION",
                                   "SPECTRAL_WINDOW", "POLARIZATION"])

    field_ds = tables["FIELD"]
    ddid_ds = tables["DATA_DESCRIPTION"]
    spw_ds = tables["SPECTRAL_WINDOW"]
    pol_ds = tables["POLARIZATION"] 

    # List of write operations
    writes = []

    # Construct a graph for each DATA_DESC_ID
    for xds in xds_from_ms(args.ms,
                           columns=["UVW", "ANTENNA1", "ANTENNA2", "TIME"],
                           group_cols=["FIELD_ID", "DATA_DESC_ID"],
                           chunks={"row": args.row_chunks}):

        # Extract frequencies from the spectral window associated
        # with this data descriptor id
        field = field_ds[xds.attrs['FIELD_ID']]
        ddid = ddid_ds[xds.attrs['DATA_DESC_ID']]
        spw = spw_ds[ddid.SPECTRAL_WINDOW_ID.values]
        pol = pol_ds[ddid.POLARIZATION_ID.values]
        frequency = spw.CHAN_FREQ.data

        corrs = pol.NUM_CORR.values

        _, time_index = da.unique(xds.TIME.data, return_inverse=True)
        # Generate visibility expressions for each source type
        source_vis = [vis_factory(args, stype, sky_model, time_index,
                                  xds, field, spw, pol)
                      for stype in sky_model.keys()]

        # Sum visibilities together
        vis = sum(source_vis)

        # Reshape (2, 2) correlation to shape (4,)
        if corrs == 4:
            vis = vis.reshape(vis.shape[:2] + (4,))

        # Assign visibilities to MODEL_DATA array on the dataset
        model_data = xr.DataArray(vis, dims=["row", "chan", "corr"])
        xds = xds.assign(MODEL_DATA=model_data)
        # Create a write to the table
        write = xds_to_table(xds, args.ms, ['MODEL_DATA'])
        # Add to the list of writes
        writes.append(write)

    # Submit all graph computations in parallel
    with ProgressBar():
        dask.compute(writes)

if __name__ == "__main__":
    args = create_parser().parse_args()
    predict(args)