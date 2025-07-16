from qgis.utils import qgsfunction
import random

CHARLOOP = {}

@qgsfunction(args="auto", group="Custom")
def charloop_reset(feature, parent):
    CHARLOOP = {}

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
    """
    Determine if the line direction is from West to East.
    """
    return _line_direction_we(feature)


def _charloop(lib, layerid, feature):
    """
    Loop through a list of characters for a given layer and feature.
    This function maintains a state for each layer to ensure that characters are cycled in a consistent manner based on the feature ID.
    :param lib: List of characters to loop through.
    :param layerid: Unique identifier for the layer.
    """
    global CHARLOOP

    if not (layerid in CHARLOOP):
        CHARLOOP[layerid] = {"last_id": -1, "index": -1}

    # Check if the feature ID has changed since the last call
    # if the last feature ID is not the same as the current one, reset the index
    if CHARLOOP[layerid]["last_id"] != feature.id():
        CHARLOOP[layerid]["index"] = -1

    CHARLOOP[layerid]["last_id"] = feature.id()
    CHARLOOP[layerid]["index"] = (CHARLOOP[layerid]["index"] + 1) % len(lib)

    # if feature["fid"] == 14956:
    #    print(lib)

    return lib[CHARLOOP[layerid]["index"]]


@qgsfunction(args="auto", group="Custom")
def charloop_randomize(lib, layerid, feature, parent):
    """
    Loop through a list of characters for a given layer and feature.
    This function maintains a state for each layer to ensure that characters are cycled in a consistent manner based on the feature ID.
    :param lib: List of characters to loop through.
    :param layerid: Unique identifier for the layer.
    """
    global CHARLOOP

    if not (layerid in CHARLOOP):
        CHARLOOP[layerid] = {"last_id": -1, "begin":{}, "index":{}}

    if not feature.id() in CHARLOOP[layerid]["begin"]:
        CHARLOOP[layerid]["begin"][feature.id()] = random.randint(0, len(lib)-1)
        CHARLOOP[layerid]["index"][feature.id()] = CHARLOOP[layerid]["begin"][feature.id()]

    if CHARLOOP[layerid]["last_id"] != feature.id():
        CHARLOOP[layerid]["index"][feature.id()] = CHARLOOP[layerid]["begin"][feature.id()]
    else:
        CHARLOOP[layerid]["index"][feature.id()] = (CHARLOOP[layerid]["index"][feature.id()] + 1) % len(lib)

    CHARLOOP[layerid]["last_id"] = feature.id()

    if feature.id() == 1:
        print(lib[CHARLOOP[layerid]["index"][feature.id()]])
        
    return lib[CHARLOOP[layerid]["index"][feature.id()]]

@qgsfunction(args="auto", group="Custom")
def charloop(lib, layerid, feature, parent):
    """
    Loop through a list of characters for a given layer and feature.
    This function maintains a state for each layer to ensure that characters are cycled in a consistent manner based on the feature ID.
    :param lib: List of characters to loop through.
    :param layerid: Unique identifier for the layer.
    """
    return _charloop(lib, layerid, feature)


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
    pos = int((frame_number / total_frame_count) * len(lib))

    if _line_direction_we(feature):
        # west-est direction : rotate right
        newlib = lib[-pos:] + lib[:-pos]
    else:
        # est-west direction : rotate left
        newlib = lib[pos:] + lib[:pos]

    return _charloop(newlib, layerid, feature)


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
    pos = (frame_number / total_frame_count) * len(lib)
    shift = pos - int(pos)

    if _line_direction_we(feature):
        return shift * gap
    else:
        return gap - shift * gap
