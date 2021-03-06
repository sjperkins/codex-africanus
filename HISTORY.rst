=======
History
=======

0.1.9 (YYYY-MM-DD)
------------------

* Add dask wrappers for the nifty gridder (:pr:`116`)
* Testing and requirement updates. (:pr:`124`)
* Upgraded DFT kernels to have a correlation axis and added flags
  for vis_to_im. Added predict_from_fits example. (:pr:`122`)
* Fixed segfault when using `_unique_internal` on empty ndarrays (:pr:`123`)
* Removed `apply_gains`. Use `africanus.calibration.utils.correct_vis`
  instead (:pr:`118`)
* Add streams parameter to dask `predict_vis` (:pr:`118`)
* Implement the beam in numba (:pr:`112`)
* Add residual_vis, correct_vis, phase_only_GN (:pr:`113`)

0.1.8 (2019-05-28)
------------------

* Use environment markers in setup.py (:pr:`110`)
* Add `apply_gains`, a wrapper around `predict_vis` (:pr:`108`)
* Fix testing extras_require (:pr:`107`)
* Fix WEIGHT_SPECTRUM averaging and add more averaging tests (:pr:`106`)

0.1.7 (2019-05-09)
------------------

* Even more support for automated travis deploys.

0.1.6 (2019-05-09)
------------------

* Support automated travis deploys.

0.1.5 (2019-05-09)
------------------
* Predict script enhancements (:pr:`103`) and
  dask channel chunking fix (:issue:`104`).
* Directly jit DFT functions (:pr:`100`, :pr:`101`)
* Spectral Models (:pr:`86`)
* Fix radec sign conversion in wsclean sky model (:pr:`96`)
* Full Time and Channel Averaging Implementation (:pr:`80`, :pr:`97`, :pr:`98`)
* Support integer seconds in wsclean ra and dec columns (:pr:`91`, :pr:`93`)
* Fix ratio computation in Gaussian Shape (:pr:`89`, :pr:`90`)

0.1.4 (2019-03-11)
------------------
* Support `complete` and `complete-cuda` to support non-GPU installs (:pr:`87`)
* Gaussian Shape Parameter Implementation (:pr:`82`, :pr:`83`)
* WSClean Spectral Model (:pr:`81`)
* Compare predict versus MeqTrees (:pr:`79`)
* Time and channel averaging (:pr:`75`)
* cupy implementation of `predict_vis` (:pr:`73`)
* Introduce transpose in second antenna term of predict (:pr:`72`)
* cupy implementation of `feed_rotation` (:pr:`67`)
* cupy implementation of `stokes_convert` kernel (:pr:`65`)
* Add a basic RIME example (:pr:`64`)
* requires_optional accepts ImportError's for a
  better debugging experience (:pr:`62`, :pr:`63`)
* Added `fit_component_spi` function (:pr:`61`)
* cupy implementation of the `phase_delay` kernel (:pr:`59`)
* Correct `phase_delay` argument ordering (:pr:`57`)
* Support dask for `radec_to_lmn` and `lmn_to_radec`. Also add support
  for `radec_to_lm` and `lm_to_radec` (:pr:`56`)
* Added test for dft to test if image space covariance
  is symmetric(:pr:`55`)
* Correct Parallactic Angle Computation (:pr:`49`)
* Enhance visibility predict (:pr:`50`)
* Fix Kaiser Bessel filter and taper (:pr:`48`)
* Stokes/Correlation conversion (:pr:`41`)
* Fix gridding examples (:pr:`43`)
* Add simple dask gridder example (:pr:`42`)
* Implement Kaiser Bessel filter (:pr:`38`)
* Implement W-stacking gridder/degridder (:pr:`38`)
* Use 2D filters by default (:pr:`37`)
* Fixed bug in im_to_vis. Added more tests for im_to_vis.
  Removed division by :math:`n` since it is trivial to reinstate
  after the fact. (:pr:`34`)
* Move numba implementations out of API functions. (:pr:`33`)
* Zernike Polynomial Direction Dependent Effects (:pr:`18`, :pr:`30`)
* Added division by :math:`n` to DFT.
  Fixed dask chunking issue.
  Updated test_vis_to_im_dask (:pr:`29`).
* Implement RIME visibility predict (:pr:`24`, :pr:`25`)
* Direct Fourier Transform (:pr:`19`)
* Parallactic Angle computation (:pr:`15`)
* Implement Feed Rotation term (:pr:`14`)
* Swap gridding correlation dimensions (:pr:`13`)
* Implement Direction Dependent Effect beam cubes (:pr:`12`)
* Implement Brightness Matrix Calculation (:pr:`9`)
* Implement RIME Phase Delay term (:pr:`8`)
* Support user supplied grids (:pr:`7`)
* Add dask wrappers to the gridder and degridder (:pr:`4`)
* Add weights to gridder/degridder and remove PSF function (:pr:`2`)

0.1.2 (2018-03-28)
------------------

* First release on PyPI.
