from qgis.utils import qgsfunction
import random

CHARLOOP = {}


@qgsfunction(args="auto", group="Custom")
def charloop_reset(v, feature, parent):
    global CHARLOOP
    CHARLOOP = {}
    return v


def _line_direction_we(feature):
    """
    Determine if the line direction is from West to East.
    """
    try:
        nodes = feature.geometry().asPolyline()
        x1 = nodes[0].x()
        x2 = nodes[-1].x()
        return x1 < x2
    except Exception:
        nodes = feature.geometry().asMultiPolyline()
        x1 = nodes[0][0].x()
        x2 = nodes[-1][-1].x()
        return x1 < x2


@qgsfunction(args="auto", group="Custom")
def line_direction_we(feature, parent):
    """<h1>line_direction_we function</h1>
        Determine if the line direction is from West to East.<br>
        <h2>Exemples : </h2>
            <pre>case
        when line_direction_we()
        then ($geometry)
        else reverse($geometry)
    end</pre>
    """
    return _line_direction_we(feature)


def _charloop(lib, layerid, start_index, feature):
    """
    Loop through a list of characters for a given layer and feature.
    This function maintains a state for each layer to ensure that characters are cycled in a consistent manner based on the feature ID.
    :param lib: List of characters to loop through.
    :param layerid: Unique identifier for the layer.
    """
    global CHARLOOP

    if not (layerid in CHARLOOP):
        CHARLOOP[layerid] = {"last_id": -1, "begin": {}, "index": {}}

    if not feature.id() in CHARLOOP[layerid]["begin"]:
        CHARLOOP[layerid]["begin"][feature.id()] = start_index
        CHARLOOP[layerid]["index"][feature.id()] = start_index

    if CHARLOOP[layerid]["last_id"] != feature.id():
        CHARLOOP[layerid]["index"][feature.id()] = CHARLOOP[layerid]["begin"][
            feature.id()
        ]
    else:
        CHARLOOP[layerid]["index"][feature.id()] = (
            CHARLOOP[layerid]["index"][feature.id()] + 1
        ) % len(lib)

    CHARLOOP[layerid]["last_id"] = feature.id()

    return lib[CHARLOOP[layerid]["index"][feature.id()]]


@qgsfunction(args="auto", group="Custom")
def charloop_random(lib, layerid, feature, parent):
    """
    Loop through a list of characters for a given layer and feature.
    This function maintains a state for each layer to ensure that characters are cycled in a consistent manner based on the feature ID.
    :param lib: List of characters to loop through.
    :param layerid: Unique identifier for the layer.
    """
    return _charloop(lib, layerid, random.randint(0, len(lib) - 1), feature)


@qgsfunction(args="auto", group="Custom")
def charloop(lib, layerid, feature, parent):
    """<h1>charloop function</h1>
        Loop through a list of characters for a given layer and feature.<br>
        <h2>Exemples : </h2>
        <p>Use it in char expression</p>
            <pre>charloop('ABCDE', @layerid)
    </pre>
    """
    return _charloop(lib, layerid, 0, feature)


@qgsfunction(args="auto", group="Custom")
def animated_charloop(
    lib,
    layerid,
    frame_number,
    total_frame_count,
    feature,
    parent,
):
    """
    Loop through a list of characters for a given layer and feature, with animation based on frame number.
    """
    pos = int((frame_number / int(total_frame_count)) * len(lib))

    if _line_direction_we(feature):
        # west-est direction : rotate right
        newlib = lib[-pos:] + lib[:-pos]
    else:
        # est-west direction : rotate left
        newlib = lib[pos:] + lib[:pos]

    return _charloop(newlib, layerid, 0, feature)


@qgsfunction(args="auto", group="Custom")
def animated_charloop_random(
    lib,
    layerid,
    frame_number,
    total_frame_count,
    feature,
    parent,
):
    """
    Loop through a list of characters for a given layer and feature, with animation based on frame number.
    """
    pos = int((frame_number / int(total_frame_count)) * len(lib))

    if _line_direction_we(feature):
        # west-est direction : rotate right
        newlib = lib[-pos:] + lib[:-pos]
    else:
        # est-west direction : rotate left
        newlib = lib[pos:] + lib[:pos]

    return _charloop(newlib, layerid, random.randint(0, len(lib) - 1), feature)


@qgsfunction(args="auto", group="Custom")
def charloop_shift(
    lib,
    gap,
    frame_number,
    total_frame_count,
    feature,
    parent,
):
    """
    Loop through a list of characters for a given layer and feature, with animation based on frame number.
    """
    pos = (frame_number / int(total_frame_count)) * len(lib)
    shift = pos - int(pos)

    if _line_direction_we(feature):
        return shift * gap
    else:
        return gap - shift * gap
