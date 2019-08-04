import copy
from collections import Counter
from contextlib import suppress
from functools import partial

import numpy as np
from matplotlib.cbook import CallbackRegistry

from . import _pick_info

_default_bindings = dict(
    select=1,
    deselect=3,
    left="shift+left",
    right="shift+right",
    up="shift+up",
    down="shift+down",
    toggle_enabled="e",
    toggle_visible="v",
)
_default_annotation_kwargs = dict(
    textcoords="offset points",
    bbox=dict(
        boxstyle="round,pad=.5",
        fc="yellow",
        alpha=.5,
        ec="k",
    ),
    arrowprops=dict(
        arrowstyle="->",
        connectionstyle="arc3",
        shrinkB=0,
        ec="k",
    ),
)
_default_annotation_positions = [
    dict(position=(-15, 15), ha="right", va="bottom"),
    dict(position=(15, 15), ha="left", va="bottom"),
    dict(position=(15, -15), ha="left", va="top"),
    dict(position=(-15, -15), ha="right", va="top"),
]


class _MarkedStr(str):
    """A string subclass solely for marking purposes.
    """


def _get_rounded_intersection_area(bbox_1, bbox_2):
    """Compute the intersection area between two bboxes, rounded to 8 digits.
    """
    # The rounding allows sorting areas without floating point issues.
    bbox = bbox_1.intersection(bbox_1, bbox_2)
    return (round(bbox.width * bbox.height / 1e-8) * 1e-8
            if bbox else 0)


def _is_alive(artist):
    """Check whether an artist is still present on an axes.
    """
    return bool(artist and artist.axes)


def _reassigned_axes_event(event, ax):
    """Reassign *event* to *ax*.
    """
    event = copy.copy(event)
    event.xdata, event.ydata = (
        ax.transData.inverted().transform_point((event.x, event.y)))
    return event


class Cursor:
    """A cursor for selecting Matplotlib artists.

    Attributes
    ----------
    bindings : dict
        See the *bindings* keyword argument to the constructor.
    annotation_kwargs : dict
        See the *annotation_kwargs* keyword argument to the constructor.
    annotation_positions : dict
        See the *annotation_positions* keyword argument to the constructor.
    """

    def __init__(self,
                 artists,
                 *,
                 multiple=False,
                 bindings=None,
                 annotation_kwargs=None,
                 annotation_positions=None):
        """Construct a cursor.

        Parameters
        ----------

        artists : List[Artist]
            A list of artists that can be selected by this cursor.

        multiple : bool, optional
            Whether multiple artists can be "on" at the same time (defaults to
            False).

        bindings : dict, optional
            A mapping of button and keybindings to actions.  Valid entries are:

            ================ ==================================================
            'select'         mouse button to select an artist
                             (default: 1)
            'deselect'       mouse button to deselect an artist
                             (default: 3)
            'left'           move to the previous point in the selected path,
                             or to the left in the selected image
                             (default: shift+left)
            'right'          move to the next point in the selected path, or to
                             the right in the selected image
                             (default: shift+right)
            'up'             move up in the selected image
                             (default: shift+up)
            'down'           move down in the selected image
                             (default: shift+down)
            'toggle_enabled' toggle whether the cursor is active
                             (default: e)
            'toggle_visible' toggle default cursor visibility and apply it to
                             all cursors (default: v)
            ================ ==================================================

            Missing entries will be set to the defaults.  In order to not
            assign any binding to an action, set it to ``None``.

        annotation_kwargs : dict, optional
            Keyword argments passed to the `annotate
            <matplotlib.axes.Axes.annotate>` call.

        annotation_positions : List[dict], optional
            List of positions tried by the annotation positioning algorithm.
        """

        self._artists = artists

        self._multiple = multiple

        self._visible = True
        self._enabled = True
        self._selections = []
        self._last_auto_position = None
        self._last_active_selection = -1
        self._callbacks = CallbackRegistry()

        connect_pairs = [
            ('key_press_event', self._on_key_press),
            ('button_press_event', self._mouse_click_handler),
            ('pick_event', self._pick_event_handler)
        ]
        self._disconnectors = [
            partial(canvas.mpl_disconnect, canvas.mpl_connect(*pair))
            for pair in connect_pairs
            for canvas in {artist.figure.canvas for artist in self._artists}
        ]

        if bindings is not None:
            unknown_bindings = set(bindings) - set(_default_bindings)
            if unknown_bindings:
                raise ValueError("Unknown binding(s): {}".format(", ".join(sorted(unknown_bindings))))
            duplicate_bindings = [k for k, v in Counter(list(bindings.values())).items() if v > 1]
            if duplicate_bindings:
                raise ValueError("Duplicate binding(s): {}".format(", ".join(sorted(map(str, duplicate_bindings)))))
            self.bindings = copy.deepcopy(_default_bindings)
            for key, value in bindings.items():
                self.bindings[key] = value
        else:
            self.bindings = _default_bindings

        self.annotation_kwargs = copy.deepcopy(_default_annotation_kwargs)
        if annotation_kwargs is not None:
            for key, value in annotation_kwargs.items():
                self.annotation_kwargs[key] = value
        self.annotation_positions = copy.deepcopy(_default_annotation_positions)
        if annotation_positions is not None:
            for key, value in annotation_positions.items():
                self.annotation_positions[key] = value

    @property
    def artists(self):
        """The tuple of selectable artists.
        """
        # Work around matplotlib/matplotlib#6982: `cla()` does not clear
        # `.axes`.
        return tuple(self._artists)

    @property
    def enabled(self):
        """Whether clicks are registered for picking and unpicking events.
        """
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value

    @property
    def selections(self):
        """The tuple of current `Selection`\\s.
        """
        for sel in self._selections:
            if sel.annotation.axes is None:
                raise RuntimeError("Annotation unexpectedly removed; "
                                   "use 'cursor.remove_selection' instead")
        return tuple(self._selections)

    @property
    def visible(self):
        """Whether selections are visible by default.

        Setting this property also updates the visibility status of current
        selections.
        """
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = value
        for sel in self.selections:
            sel.annotation.set_visible(value)
            sel.annotation.figure.canvas.draw_idle()

    def add_selection(self, pi):
        """Create an annotation for a `Selection` and register it.

        Returns a new `Selection`, that has been registered by the `Cursor`,
        with the added annotation set in the :attr:`annotation` field.

        Emits the ``"add"`` event with the new `Selection` as argument.  When
        the event is emitted, the position of the annotation is temporarily
        set to ``(nan, nan)``; if this position is not explicitly set by a
        callback, then a suitable position will be automatically computed.

        Likewise, if the text alignment is not explicitly set but the position
        is, then a suitable alignment will be automatically computed.
        """
        # pi: "pick_info", i.e. an incomplete selection.
        # Pre-fetch the figure and axes, as callbacks may actually unset them.
        figure = pi.artist.figure
        axes = pi.artist.axes
        if axes.get_renderer_cache() is None:
            figure.canvas.draw()  # Needed by draw_artist below anyways.
        renderer = pi.artist.axes.get_renderer_cache()
        ann = pi.artist.axes.annotate(
            _pick_info.get_ann_text(*pi),
            xy=pi.target,
            xytext=(np.nan, np.nan),
            ha=_MarkedStr("center"), va=_MarkedStr("center"),
            visible=self.visible,
            **self.annotation_kwargs)
        ann.draggable(state=True, use_blit=not self._multiple)
        sel = getattr(pi, '_replace')(annotation=ann)
        self._selections.append(sel)
        self._callbacks.process("add", sel)

        # Check that `ann.axes` is still set, as callbacks may have removed the
        # annotation.
        if ann.axes and ann.xyann == (np.nan, np.nan):
            fig_bbox = figure.get_window_extent()
            ax_bbox = axes.get_window_extent()
            overlaps = []
            for idx, annotation_position in enumerate(self.annotation_positions):
                ann.set(**annotation_position)
                # Work around matplotlib/matplotlib#7614: position update is missing.
                ann.update_positions(renderer)
                bbox = ann.get_window_extent(renderer)
                overlaps.append(
                    (_get_rounded_intersection_area(fig_bbox, bbox),
                     _get_rounded_intersection_area(ax_bbox, bbox),
                     # Avoid needlessly jumping around by breaking ties using
                     # the last used position as default.
                     idx == self._last_auto_position))
            auto_position = max(range(len(overlaps)), key=getattr(overlaps, '__getitem__'))
            ann.set(**self.annotation_positions[auto_position])
            self._last_auto_position = auto_position
        else:
            if isinstance(ann.get_ha(), _MarkedStr):
                ann.set_ha({-1: "right", 0: "center", 1: "left"}[np.sign(np.nan_to_num(ann.xyann[0]))])
            if isinstance(ann.get_va(), _MarkedStr):
                ann.set_va({-1: "top", 0: "center", 1: "bottom"}[np.sign(np.nan_to_num(ann.xyann[1]))])

        if len(self.selections) > 1 and not self._multiple or not figure.canvas.supports_blit:
            # Either:
            #  - there may be more things to draw, or
            #  - annotation removal will make a full redraw necessary, or
            #  - blitting is not (yet) supported.
            figure.canvas.draw_idle()
        elif ann.axes:
            # Fast path, only needed if the annotation has not been immediately removed.
            figure.draw_artist(ann)
            # Explicit argument needed on MacOSX backend.
            figure.canvas.blit(figure.bbox)
        # Removal comes after addition so that the fast blitting path works.
        if not self._multiple:
            for sel in self.selections[:-1]:
                self.remove_selection(sel)
        self._last_active_selection = -1
        return sel

    def connect(self, event, func=None):
        """Connect a callback to a `Cursor` event; return the callback id.

        Two classes of event can be emitted, both with a `Selection` as single
        argument:

            - ``"add"`` when a `Selection` is added, and
            - ``"remove"`` when a `Selection` is removed.

        The callback registry relies on Matplotlib's implementation; in
        particular, only weak references are kept for bound methods.

        This method is can also be used as a decorator::

            @cursor.connect("add")
            def on_add(sel):
                ...

        Examples of callbacks::

            # Change the annotation text and alignment:
            lambda sel: sel.annotation.set(
                text=sel.artist.get_label(),  # or use e.g. sel.target.index
                ha="center", va="bottom")

            # Make label non-draggable:
            lambda sel: sel.draggable(False)
        """
        if event not in ["add", "remove"]:
            raise ValueError("Invalid cursor event: {}".format(event))
        if func is None:
            return partial(self.connect, event)
        return self._callbacks.connect(event, func)

    def disconnect(self, cid):
        """Disconnect a previously connected callback id.
        """
        self._callbacks.disconnect(cid)

    def remove(self):
        """Remove a cursor.

        Remove all `Selection`\\s, disconnect all callbacks, and allow the
        cursor to be garbage collected.
        """
        for disconnectors in self._disconnectors:
            disconnectors()
        for sel in self.selections:
            self.remove_selection(sel)

    def _mouse_click_handler(self, event):
        if event.name == "button_press_event" and self._enabled:
            if event.button == self.bindings["select"]:
                self._on_select_button_press(event)
            if event.button == self.bindings["deselect"]:
                self._on_deselect_button_press(event)

    def _pick_event_handler(self, event):
        if event.name == "pick_event" and self._enabled:
            for index, sel in enumerate(self._selections[::-1]):
                if np.allclose(event.artist.xy, sel.target):
                    self._last_active_selection = len(self._selections) - index - 1
                    break

    def _filter_mouse_event(self, event):
        # Accept the event iff we are enabled, and either
        #   - no other widget is active, and this is not the second click of a
        #     double click (to prevent double selection), or
        #   - another widget is active, and this is a double click (to bypass
        #     the widget lock).
        return self.enabled and event.canvas.widgetlock.locked() == event.dblclick

    def _on_select_button_press(self, event):
        if not self._filter_mouse_event(event):
            return
        # Work around lack of support for twinned axes.
        per_axes_event = {ax: _reassigned_axes_event(event, ax)
                          for ax in {artist.axes for artist in self._artists}}
        pis = []
        for artist in self._artists:
            if (artist.axes is None  # Removed or figure-level artist.
                    or event.canvas is not artist.figure.canvas
                    or not artist.axes.contains(event)[0]):  # Cropped by axes.
                continue
            pi = _pick_info.compute_pick(artist, per_axes_event[artist.axes])
            if pi:
                pis.append(pi)
        if not pis:
            return
        self.add_selection(min(pis, key=lambda _pi: _pi.dist))

    def _on_deselect_button_press(self, event):
        if not self._filter_mouse_event(event):
            return
        for sel in self.selections[::-1]:
            ann = sel.annotation
            if event.canvas is not ann.figure.canvas:
                continue
            contained, _ = ann.contains(event)
            if contained:
                self.remove_selection(sel)
                return

    def _on_key_press(self, event):
        if event.key == self.bindings["toggle_enabled"]:
            self.enabled = not self.enabled
        elif event.key == self.bindings["toggle_visible"]:
            self.visible = not self.visible
        try:
            sel = self.selections[self._last_active_selection]
        except IndexError:
            return
        for key in ["left", "right", "up", "down"]:
            if event.key == self.bindings[key]:
                self.remove_selection(sel)
                self.add_selection(_pick_info.move(*sel, key=key))
                break

    def remove_selection(self, sel):
        """Remove a `Selection`.
        """
        self._selections.remove(sel)
        # <artist>.figure will be unset so we save them first.
        figures = {artist.figure for artist in [sel.annotation]}
        # ValueError is raised if the artist has already been removed.
        with suppress(ValueError):
            sel.annotation.remove()
        self._callbacks.process("remove", sel)
        for figure in figures:
            figure.canvas.draw_idle()
