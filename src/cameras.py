"""List the webcams Windows knows about, in the same order OpenCV's DirectShow indices use."""
import comtypes
from pygrabber.dshow_graph import FilterGraph


def list_cameras():
    """[(index, name), ...]. Empty if enumeration fails. Safe to call from any thread."""
    comtypes.CoInitialize()
    try:
        return list(enumerate(FilterGraph().get_input_devices()))
    except Exception:
        return []
    finally:
        comtypes.CoUninitialize()
