# Unsupported Artist classes: subclasses of AxesImage, QuadMesh (upstream could
# have a `format_coord`-like method); PolyCollection (picking is not well
# defined).

from collections import ChainMap, namedtuple
import copy
import functools
import inspect
from inspect import Signature
import re

import numpy as np


def _artist_in_container(container):
    return next(filter(None, container.get_children()))


class AttrArray(np.ndarray):
    """An array subclass that can store additional attributes.
    """

    def __new__(cls, array):
        return np.asarray(array).view(cls)


def with_attrs(array, **kwargs):
    array = AttrArray(array)
    for k, v in kwargs.items():
        setattr(array, k, v)
    return array


Selection = namedtuple("Selection", "artist target dist annotation extras")
# Override equality to identity: Selections should be considered immutable
# (with mutable fields though) and we don't want to trigger casts of array
# equality checks to booleans.  We don't need to override comparisons because
# artists are already non-comparable.
Selection.__eq__ = lambda self, other: self is other
Selection.__ne__ = lambda self, other: self is not other
try:
    Selection.artist.__doc__ = (
        "The selected artist.")
    Selection.target.__doc__ = (
        "The point picked within the artist, in data coordinates.")
    Selection.dist.__doc__ = (
        "The distance from the click to the target, in pixels.")
    Selection.annotation.__doc__ = (
        "The instantiated `matplotlib.text.Annotation`.")
    Selection.extras.__doc__ = (
        "An additional list of artists (e.g., highlighters) that will be "
        "cleared at the same time as the annotation.")
except AttributeError:  # Read-only in Py3.4.
    pass


class Index:
    def __init__(self, i, x, y):
        self.int = i
        self.x = x
        self.y = y

    def floor(self):
        return self.int

    def ceil(self):
        return self.int if max(self.x, self.y) <= 0 else self.int + 1

    def __format__(self, fmt):
        return "{0.int}.(x={0.x:{1}}, y={0.y:{1}})".format(self, fmt)

    def __str__(self):
        return format(self, "")

    @classmethod
    def pre_index(cls, n_pts, index):
        del n_pts
        i, frac = divmod(index, 1)
        i, odd = divmod(i, 2)
        x, y = (0, frac) if not odd else (frac, 1)
        return cls(i, x, y)

    @classmethod
    def post_index(cls, n_pts, index):
        del n_pts
        i, frac = divmod(index, 1)
        i, odd = divmod(i, 2)
        x, y = (frac, 0) if not odd else (1, frac)
        return cls(i, x, y)

    @classmethod
    def mid_index(cls, n_pts, index):
        i, frac = divmod(index, 1)
        if i == 0:
            frac = .5 + frac / 2
        elif i == 2 * n_pts - 2:  # One less line than points.
            frac = frac / 2
        quot, odd = divmod(i, 2)
        if not odd:
            if frac < .5:
                i = quot - 1
                x, y = frac + .5, 1
            else:
                i = quot
                x, y = frac - .5, 0
        else:
            i = quot
            x, y = .5, frac
        return cls(i, x, y)


def _compute_projection_pick(artist, path, xy):
    """Project *xy* on *path* to obtain a `Selection` for *artist*.

    *path* is first transformed to screen coordinates using the artist
    transform, and the target of the returned `Selection` is transformed
    back to data coordinates using the artist *axes* inverse transform.  The
    `Selection` `index` is returned as a float.  This function returns ``None``
    for degenerate inputs.

    The caller is responsible for converting the index to the proper class if
    needed.
    """
    transform = artist.get_transform().frozen()
    tpath = (path.cleaned(transform) if transform.is_affine
             # `cleaned` only handles affine transforms.
             else transform.transform_path(path).cleaned())
    # `cleaned` should return a path where the first element is `MOVETO`, the
    # following are `LINETO` or `CLOSEPOLY`, and the last one is `STOP`, i.e.
    #     codes = path.codes
    #     assert (codes[0], codes[-1]) == (path.MOVETO, path.STOP)
    #     assert np.in1d(codes[1:-1], [path.LINETO, path.CLOSEPOLY]).all()
    vertices = tpath.vertices[:-1]
    codes = tpath.codes[:-1]
    vertices[codes == tpath.CLOSEPOLY] = vertices[0]
    # Unit vectors for each segment.
    us = vertices[1:] - vertices[:-1]
    ls = np.hypot(*us.T)
    with np.errstate(invalid="ignore"):
        # Results in 0/0 for repeated consecutive points.
        us /= ls[:, None]
    # Vectors from each vertex to the event (overwritten below).
    vs = xy - vertices[:-1]
    # Clipped dot products -- `einsum` cannot be done in place, `clip` can.
    # `clip` can trigger invalid comparisons if there are nan points.
    with np.errstate(invalid="ignore"):
        dot = np.clip(np.einsum("ij,ij->i", vs, us), 0, ls, out=vs[:, 0])
    # Projections.
    projs = vertices[:-1] + dot[:, None] * us
    ds = np.hypot(*(xy - projs).T, out=vs[:, 1])
    try:
        argmin = np.nanargmin(ds)
        dmin = ds[argmin]
    except (ValueError, IndexError):  # See above re: exceptions caught.
        return
    else:
        target = AttrArray(artist.axes.transData.inverted().transform_point(projs[argmin]))
        target.index = (
                (argmin + dot[argmin] / ls[argmin])
                / (getattr(path, '_interpolation_steps') / getattr(tpath, '_interpolation_steps')))
        return Selection(artist, target, dmin, None, None)


def compute_pick(artist, event):
    # No need to call `line.contains` as we're going to redo the work anyways
    # (also see matplotlib/matplotlib#6645, though that's fixed in mpl2.1).

    # Always work in screen coordinates, as this is how we need to compute
    # distances.  Note that the artist transform may be different from the axes
    # transform (e.g., for axvline).
    xy = np.array([event.x, event.y])
    data_xy = artist.get_xydata()
    sels = []
    ds = np.hypot(*(xy - artist.get_transform().transform(data_xy)).T)
    try:
        argmin = np.nanargmin(ds)
        dmin = ds[argmin]
    except (ValueError, IndexError):
        # numpy 1.7.0's `nanargmin([nan])` returns nan, so
        # `ds[argmin]` raises IndexError.  In later versions of numpy,
        # `nanargmin([nan])` raises ValueError (the release notes for 1.8.0
        # are incorrect on this topic).
        pass
    else:
        # More precise than transforming back.
        target = with_attrs(artist.get_xydata()[argmin], index=argmin)
        sels.append(Selection(artist, target, dmin, None, None))
    if not sels:
        return None
    sel = min(sels, key=lambda _sel: _sel.dist)
    return sel if sel.dist < artist.get_pickradius() else None


def _call_with_selection(func):
    """Decorator that passes a `Selection` built from the non-kwonly args.
    """
    wrapped_kwonly_params = [
        param for param in inspect.signature(func).parameters.values()
        if param.kind == param.KEYWORD_ONLY]
    sel_sig = inspect.signature(Selection)
    default_sel_sig = sel_sig.replace(
        parameters=[param.replace(default=None) if param.default is param.empty
                    else param
                    for param in sel_sig.parameters.values()])

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        extra_kw = {param.name: kwargs.pop(param.name)
                    for param in wrapped_kwonly_params if param.name in kwargs}
        ba = default_sel_sig.bind(*args, **kwargs)
        # apply_defaults
        ba.arguments = ChainMap(
            ba.arguments,
            {
                name: param.default
                for name, param in default_sel_sig.parameters.items()
                if param.default is not param.empty
            })
        sel = Selection(*ba.args, **ba.kwargs)
        return func(sel, **extra_kw)

    wrapper.__signature__ = Signature(
        list(sel_sig.parameters.values()) + wrapped_kwonly_params)
    return wrapper


def _format_coord_unspaced(ax, xy):
    # Un-space-pad, remove empty coordinates from the output of
    # `format_{x,y}data`, and rejoin with newlines.
    return "\n".join(
        line for line, empty in zip(
            re.split(",? +", ax.format_coord(*xy)),
            ["x=", "y=", "z="]
        )
        if line != empty).rstrip()


@_call_with_selection
def get_ann_text(sel):
    artist = sel.artist
    label = artist.get_label() or "_"
    text = _format_coord_unspaced(artist.axes, sel.target)
    if not label.startswith('_'):
        text = "{}\n{}".format(label, text)
    return text


def _move_within_points(sel, xys, *, key):
    # Avoid infinite loop in case everything became nan at some point.
    for _ in range(len(xys)):
        if key == "left":
            new_idx = int(np.ceil(sel.target.index) - 1) % len(xys)
        elif key == "right":
            new_idx = int(np.floor(sel.target.index) + 1) % len(xys)
        else:
            return sel
        target = with_attrs(xys[new_idx], index=new_idx)
        sel = getattr(sel, '_replace')(target=target, dist=0)
        if np.isfinite(target).all():
            return sel


@_call_with_selection
def move(sel, *, key):
    return _move_within_points(sel, sel.artist.get_xydata(), key=key)


def _set_valid_props(artist, kwargs):
    """Set valid properties for the artist, dropping the others.
    """
    artist.set(**{k: kwargs[k] for k in kwargs if hasattr(artist, "set_" + k)})
    return artist


@_call_with_selection
def make_highlight(sel, *, highlight_kwargs):
    hl = copy.copy(sel.artist)
    _set_valid_props(hl, highlight_kwargs)
    return hl
