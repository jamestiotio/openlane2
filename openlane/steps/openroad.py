import os
import re
import json
from typing import List, Optional

from .step import TclStep, get_script_dir
from .state import State, DesignFormat, Output

EXAMPLE_INPUT = """
li1 X 0.23 0.46
li1 Y 0.17 0.34
met1 X 0.17 0.34
met1 Y 0.17 0.34
met2 X 0.23 0.46
met2 Y 0.23 0.46
met3 X 0.34 0.68
met3 Y 0.34 0.68
met4 X 0.46 0.92
met4 Y 0.46 0.92
met5 X 1.70 3.40
met5 Y 1.70 3.40
"""


def old_to_new_tracks(old_tracks: str) -> str:
    """
    >>> old_to_new_tracks(EXAMPLE_INPUT)
    'make_tracks li1 -x_offset 0.23 -x_pitch 0.46 -y_offset 0.17 -y_pitch 0.34\\nmake_tracks met1 -x_offset 0.17 -x_pitch 0.34 -y_offset 0.17 -y_pitch 0.34\\nmake_tracks met2 -x_offset 0.23 -x_pitch 0.46 -y_offset 0.23 -y_pitch 0.46\\nmake_tracks met3 -x_offset 0.34 -x_pitch 0.68 -y_offset 0.34 -y_pitch 0.68\\nmake_tracks met4 -x_offset 0.46 -x_pitch 0.92 -y_offset 0.46 -y_pitch 0.92\\nmake_tracks met5 -x_offset 1.70 -x_pitch 3.40 -y_offset 1.70 -y_pitch 3.40\\n'
    """
    layers = {}

    for line in old_tracks.splitlines():
        if line.strip() == "":
            continue
        layer, cardinal, offset, pitch = line.split()
        layers[layer] = layers.get(layer) or {}
        layers[layer][cardinal] = (offset, pitch)

    final_str = ""
    for layer, data in layers.items():
        x_offset, x_pitch = data["X"]
        y_offset, y_pitch = data["Y"]
        final_str += f"make_tracks {layer} -x_offset {x_offset} -x_pitch {x_pitch} -y_offset {y_offset} -y_pitch {y_pitch}\n"

    return final_str


inf_rx = re.compile(r"\b(-?)inf\b")


class OpenROADStep(TclStep):
    def get_command(self, step_dir: str) -> List[str]:
        metrics_path = os.path.join(step_dir, "metrics.json")
        return ["openroad", "-exit", "-metrics", metrics_path]

    @classmethod
    def get_script_path(Self) -> List[str]:
        raise Exception("Abstract class")

    def run(
        self,
        state_in: State,
        step_dir: str,
        env: Optional[dict] = None,
        **kwargs,
    ) -> State:
        state_out = super().run(state_in, step_dir, env, **kwargs)
        metrics_path = os.path.join(step_dir, "metrics.json")
        if os.path.exists(metrics_path):
            metrics_str = open(metrics_path).read()
            metrics_str = inf_rx.sub(lambda m: f"{m[1] or ''}\"Infinity\"", metrics_str)
            new_metrics = json.loads(metrics_str)
            state_out.metrics.update(new_metrics)
            with open(metrics_path, "w") as f:
                f.write(json.dumps(state_out.metrics, indent=2))
        return state_out


class NetlistSTA(OpenROADStep):
    inputs = [DesignFormat.NETLIST]
    outputs = []

    @classmethod
    def get_script_path(Self) -> List[str]:
        return os.path.join(get_script_dir(), "openroad", "sta.tcl")

    def run(self, state_in: State, step_dir: str, **kwargs) -> State:
        env = os.environ.copy()
        env["RUN_STANDALONE"] = "1"
        env["STA_PRE_CTS"] = "1"
        env["STA_REPORT_POWER"] = "1"
        return super().run(state_in, step_dir, env=env, **kwargs)


class Floorplan(OpenROADStep):
    inputs = [DesignFormat.NETLIST]
    outputs = [Output(DesignFormat.ODB), Output(DesignFormat.DEF)]

    @classmethod
    def get_script_path(Self) -> List[str]:
        return os.path.join(get_script_dir(), "openroad", "floorplan.tcl")

    def run(self, state_in: State, step_dir: str, **kwargs) -> State:
        tracks_info_str = open(self.config["TRACKS_INFO_FILE"]).read()
        tracks_commands = old_to_new_tracks(tracks_info_str)
        new_tracks_info = os.path.join(step_dir, "config.tracks")
        with open(new_tracks_info, "w") as f:
            f.write(tracks_commands)

        env = os.environ.copy()
        env["TRACKS_INFO_FILE_PROCESSED"] = new_tracks_info
        return super().run(state_in, step_dir, env=env, **kwargs)
