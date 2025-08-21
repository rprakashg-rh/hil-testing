# THIS CODE AND INFORMATION ARE PROVIDED "AS IS" WITHOUT WARRANTY OF ANY
# KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A
# PARTICULAR PURPOSE.

""" Basic example of a test using a very simple loopback Typhoon HIL schematic,
showing the most important concepts when writing a tests.

All the fundamental concepts shown here can be extended to more complex models. """

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
model_path = str(dirpath / "digital substation 10 bays.tse")

compiled_model_path = model.get_compiled_model_file(model_path)


def discnt_state(bay, dc, inputValue):
    if inputValue == 'On':
        hil.set_scada_input_value(bay + '.' + dc + ' close', 1)
        hil.wait_msec(100)
        hil.set_scada_input_value(bay + '.' + dc + ' close', 0)
        pass
    elif inputValue == 'Off':
        hil.set_scada_input_value(bay + '.' + dc + ' open', 1)
        hil.wait_msec(100)
        hil.set_scada_input_value(bay + '.' + dc + ' open', 0)
        pass


def dc1_off_state(bay):
    if bool(hil.read_digital_signal(name=bay + '.Digital Probe2')):
        displayValue = True
    else:
        displayValue = False
    return displayValue


def dc1_on_state(bay):
    if bool(hil.read_digital_signal(name=bay + '.Digital Probe3')):
        displayValue = True
    else:
        displayValue = False
    return displayValue


def dc2_off_state(bay):
    if bool(hil.read_digital_signal(name=bay + '.Digital Probe4')):
        displayValue = True
    else:
        displayValue = False
    return displayValue


def dc2_on_state(bay):
    if bool(hil.read_digital_signal(name=bay + '.Digital Probe5')):
        displayValue = True
    else:
        displayValue = False
    return displayValue


def circbrk_state(bay, inputValue):
    if inputValue == 'On':
        hil.set_scada_input_value(bay + '.CB' + ' close', 1)
        hil.wait_msec(100)
        hil.set_scada_input_value(bay + '.CB' + ' close', 0)
        pass
    elif inputValue == 'Off':
        hil.set_scada_input_value(bay + '.CB' + ' open', 1)
        hil.wait_msec(100)
        hil.set_scada_input_value(bay + '.CB' + ' open', 0)
        pass


def cbr_state(bay):
    if bool(hil.read_digital_signal(name=bay + '.Digital Probe1')):
        displayValue = False
    else:
        displayValue = True
    return displayValue

@pytest.fixture(scope="module")
def setup_function():
    """
    Loads schematic, sets parameters, compiles and loads model to HIL device.
    """

    model.load(model_path)

#    try:
#        model.detect_hw_settings()
#    except Exception:
#        pytest.skip("This test is not supported for VHIL mode. "
#                    "The model requires HIL connect and a HIL device that supports CAN communication.")

    model.compile(conditional_compile = True)  # Compile model
    hil.load_model(file=compiled_model_path, vhil_device=False)  # Load compiled model into the HIL
    
    hil.start_simulation()

    yield
    hil.stop_simulation()

def test_ptp_check(setup_function):
    step_signal = []
    capture.start_capture(10, signals=["PTP"], rate=1000)
    
    cap_data = capture.get_capture_results(wait_capture=True)
    
    step_signal = sig.find(cap_data["PTP"], "above", 0.5, from_region="below", during=(0,10))
    
    assert len(cap_data["PTP"]) != 0
    
def test_hil_synch_check(setup_function):
    step_signal = []
    capture.start_capture(10, signals=["Time Synch"], rate=1000)
    
    cap_data = capture.get_capture_results(wait_capture=True)
    
    step_signal = sig.find(cap_data["Time Synch"], "above", 0.5, from_region="below", during=(0,10))
    
    assert len(cap_data["Time Synch"]) != 0

def test_discnt_cb_manipulation(setup_function):
    
    capture.start_capture(10, signals=["Three-phase Meter1.IA","Three-phase Meter1.IA_RMS"],executeAt = 12, rate=10000)

    
    # set the statuses of disconectors evey second, observ DCs on web_HMI
    # set the CBs and capture all of them
    discnt_state("HV Bay 1", "DC1", "On")
    hil.wait_msec(250)
    circbrk_state("HV Bay 1", "On")
    hil.wait_msec(250)
    discnt_state("Bay 1", "DC1", "On")
    hil.wait_msec(250)
    circbrk_state("Bay 1", "On")
    hil.wait_msec(250)
    discnt_state("Bay 2", "DC1", "On")
    hil.wait_msec(250)
    circbrk_state("Bay 2", "On")
    hil.wait_msec(250)
    discnt_state("Bay 3", "DC1", "On")
    hil.wait_msec(250)
    circbrk_state("Bay 3", "On")
    hil.wait_msec(250)
    discnt_state("Bay 4", "DC1", "On")
    hil.wait_msec(250)
    circbrk_state("Bay 4", "On")
    hil.wait_msec(250)
    discnt_state("Bay 5", "DC1", "On")
    hil.wait_msec(250)
    circbrk_state("Bay 5", "On")
    hil.wait_msec(250)
    discnt_state("Bay 6", "DC1", "On")
    hil.wait_msec(250)
    circbrk_state("Bay 6", "On")
    hil.wait_msec(250)
    discnt_state("Bay 7", "DC1", "On")
    hil.wait_msec(250)
    circbrk_state("Bay 7", "On")
    hil.wait_msec(250)
    discnt_state("Bay 8", "DC1", "On")
    hil.wait_msec(250)
    circbrk_state("Bay 8", "On")
    hil.wait_msec(250)
    discnt_state("Bay 9", "DC1", "On")
    hil.wait_msec(250)
    circbrk_state("Bay 9", "On")
    hil.wait_msec(250)
    discnt_state("Bay 10", "DC1", "On")
    hil.wait_msec(250)
    circbrk_state("Bay 10", "On")
    
    #preform the fault
    #hil.set_contactor("Grid Fault1.enable",swControl = True,swState = True,executeAt= 5.5)
    
    cap_data = capture.get_capture_results(wait_capture=True)
    
    #fault_time = sig.find(cap_data["Grid Fault1.enable_fb"], "above", 0.5, from_region="below", during=(0,5))
    #cb_time = sig.find(cap_data["S3_fb"], "below", 0.5, from_region="above", during=(0,5))
    
    #logger.info(f"Fault occured at: {fault_time}")
    #logger.info(f"Circuit breaker trip occured at: {cb_time}")
    
    #reaction_time = cb_time - fault_time
    
    #assert reaction_time <= operation_time
    

def test_q3_fault(setup_function):
    
    capture.start_capture(5, signals=["Grid Fault1.enable_fb","S3_fb","Three-phase Meter1.IA","Three-phase Meter1.IA_RMS"],executeAt = 5, rate=10000)
    
    #set the CBs and capture all of them
    hil.set_scada_input_value("HV Bay 1.CB close", 1)
    hil.wait_msec(250)
    hil.set_scada_input_value("Bay 1.CB close", 1)
    hil.wait_msec(250)
    hil.set_scada_input_value("Bay 2.CB close", 1)
    hil.wait_msec(250)
    hil.set_scada_input_value("Bay 3.CB close", 1)
    hil.wait_msec(250)
    hil.set_scada_input_value("Bay 4.CB close", 1)
    hil.wait_msec(250)
    hil.set_scada_input_value("Bay 5.CB close", 1)
    hil.wait_msec(250)
    hil.set_scada_input_value("Bay 6.CB close", 1)
    hil.wait_msec(250)
    hil.set_scada_input_value("Bay 7.CB close", 1)
    hil.wait_msec(250)
    hil.set_scada_input_value("Bay 8.CB close", 1)
    hil.wait_msec(250)
    hil.set_scada_input_value("Bay 9.CB close", 1)
    hil.wait_msec(250)
    hil.set_scada_input_value("Bay 10.CB close", 1)
    hil.wait_msec(250)
    
    #preform the fault
    hil.set_contactor("Grid Fault1.enable",swControl = True,swState = True,executeAt= 5.5)
    
    cap_data = capture.get_capture_results(wait_capture=True)
    
    fault_time = sig.find(cap_data["Grid Fault1.enable_fb"], "above", 0.5, from_region="below", during=(0,5))
    cb_time = sig.find(cap_data["S3_fb"], "below", 0.5, from_region="above", during=(0,5))
    
    logger.info(f"Fault occured at: {fault_time}")
    logger.info(f"Circuit breaker trip occured at: {cb_time}")
    
    reaction_time = cb_time - fault_time
    
    assert reaction_time <= Vreme_releja
    
    
    
    
    #isolation_time = sig.find(cap_data["S3_fb"], "below", 0.5, from_region="above", during=(0,5))
    


