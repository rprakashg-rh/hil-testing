from typhoon.api import hil
from typhoon.api.schematic_editor import SchematicAPI
import pytest
import logging
from pathlib import Path
from typhoon.test import capture
from typhoon.test import ranges
import typhoon.test.signals as sig


logger = logging.getLogger(__name__)
model = SchematicAPI()

name = "model"
dirpath = Path(__file__).parent
model_path = str(dirpath / "digital-substation-demo.tse")

compiled_model_path = model.get_compiled_model_file(model_path)

logger = logging.getLogger(__name__)

# script directory
FILE_DIR_PATH = Path(__file__).parent

# schematic name
MODEL_NAME = "digital-substation-demo.tse"

# path to schematic folder
DIRECTORY_PATH = os.path.join(
    FILE_DIR_PATH, "..", "..", "models"
)

# path to model
MODEL_PATH = os.path.join(DIRECTORY_PATH, MODEL_NAME)

# compiled model path
COMPILED_MODEL_PATH = model.get_compiled_model_file(MODEL_PATH)

@pytest.fixture(scope="module")
def setup_function():
    model.load(MODEL_PATH)

    # Detect connected hardware
    try:
        hw_settings = model.detect_hw_settings()
        vhil_device = False
        logger.info(f"{hw_settings[0]} {hw_settings[2]} device is used")
    except Exception:
        vhil_device = True

    device, _, conf = model.get_hw_settings()
    if device not in ("HIL404", "HIL606"):
        pytest.skip(
            "Skipped because they can run only on these machines HIL404 or HIL606"
        )
    dev_core = hil.get_device_features(
        device=device, conf_id=conf, feature="Standard Processing Cores"
    )
    if dev_core < 2:
        logger.info(
            f"This test requires minimum {2} cores, current configuration has {dev_core} cores!"
        )
        pytest.skip("Device doesn't have required configuration to run the model")

    model.compile()
    hil.load_model(COMPILED_MODEL_PATH, vhil_device=vhil_device)


def start_simulation():
    model.load(filename=sch)
    model.compile()
    hil.load_model(file=cpd, vhil_device=True)
    hil.start_simulation()

def trigger_bb_fault():
    # Fault:
    fault_name = "FaultBB"
    hil.set_scada_input_value(fault_name + '.Fault select', 11)

    cap_data = capture.get_capture_results(wait_capture=True)
    #fault_time = sig.find(cap_data["Grid Fault1.enable_fb"], "above", 0.5, from_region="below", during=(0,5))
    #cb_time = sig.find(cap_data["S3_fb"], "below", 0.5, from_region="above", during=(0,5))

    #logger.info(f"Fault occured at: {fault_time}")
    #logger.info(f"Circuit breaker trip occured at: {cb_time}")
    
    #reaction_time = cb_time - fault_time
    #assert reaction_time <= Vreme_releja