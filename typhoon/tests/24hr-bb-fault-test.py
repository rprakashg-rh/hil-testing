from typhoon.api import hil
from typhoon.api.schematic_editor import SchematicAPI

import logging
from pathlib import Path


logger = logging.getLogger(__name__)
model = SchematicAPI()

name = "model"
dirpath = Path(__file__).parent
sch = str(dirpath / "model.tse")
cpd = model.get_compiled_model_file(sch)


def start_simulation():
    model.load(filename=sch)
    model.compile()
    hil.load_model(file=cpd, vhil_device=True)
    hil.start_simulation()

def trigger_bb_fault():
    # Capture data:
    # Define Capture/Scope widget
    cs = panel.get_widget_by_id("563a009cfeb511edbb091c1bb5b93d80")

    # dip params
    dip_depth = 0.5
    dip_width = 0.5


    # switch to capture mode
    state = "Capture"
    panel.set_property_value(cs,
                            prop_name="state",
                            prop_value=state)
                            
    # select preset
    preset = "Diff prot"
    panel.set_property_value(cs, api_const.PROP_CS_ACTIVE_CAPTURE_PRESET, preset)

    # set capture time interval
    panel.set_property_value(cs, api_const.PROP_CS_CAPTURE_TIME_INTERVAL, dip_width)


    # force data acquisition
    panel.execute_action(cs, api_const.ACT_CS_FORCE_TRIGGER)

    hil.wait_msec(250)

    # Fault:
    fault_name = "FaultBB"
    hil.set_scada_input_value(fault_name + '.Fault select', 11)