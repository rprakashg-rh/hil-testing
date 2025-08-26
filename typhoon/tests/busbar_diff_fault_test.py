#!/usr/bin/env python3
"""
Busbar Differential Protection – Internal vs External Fault Test
Typhoon HIL automated test template (Python)

What this gives you
-------------------
- Start/stop simulation flow
- Arms your IED (or logic) and timestamps pickup/trip
- Injects an INTERNAL busbar fault (3φ bolted by default) and checks trip & time
- Injects an EXTERNAL fault (on a feeder) and checks for NO-TRIP / stability
- Captures waveforms (optional) and saves a CSV
- Emits a simple pass/fail summary

How to use
----------
1) Fill in the TODOs in the CONFIG section to match your model signal names:
   - model_path / compiled_model_path
   - digital inputs/outputs used to arm/trip
   - analog measurement signals for currents/voltages (used for pickup detection)
   - fault control handles (Digital In or component path/parameter) for internal & external faults
2) Run with a Python interpreter on a Typhoon HIL machine where Control Center is installed.
3) If you use a relay via GPI/O, set gpio_* names accordingly OR map to your model logic.

Notes:
------
- This is a template. You might need to adapt API calls to
  your exact Control Center version (hil.* API).
- For models that use the built-in "Fault" component, expose enable pins/parameters,
  and set them via set_parameter or digital input as shown.
"""
import time
import csv
import os
from datetime import datetime

# ===== Typhoon HIL API =====
try:
    # Newer API location
    from typhoon.api.hil import hil
    from typhoon.api.tlc import tlc
except Exception:
    # Older API fallback (adjust if needed)
    from typhoonhild import hil  # type: ignore

# =========================
# ======= CONFIG =========
# =========================
CONFIG = {
    # --- Model paths ---
    "model_path": r"CHANGE_ME/my_busbar_model.tse",            # TODO
    "compiled_model_path": r"CHANGE_ME/my_busbar_model.tse",   # or .tse/.rpc depending on your flow

    # --- Simulation setup ---
    "simulation_duration_s": 2.0,
    "prefault_time_s": 0.20,       # wait before fault
    "fault_duration_s": 0.20,      # how long to leave fault applied (internal)
    "postfault_time_s": 0.20,      # time after clearing for assertions
    "rated_frequency_hz": 60.0,

    # --- Protection expectations ---
    "expect_pickup_in_s": 0.010,   # pickup by differential within 10 ms (example)
    "expect_trip_in_s": 0.040,     # trip within 40 ms (example)
    "stability_window_s": 0.250,   # for external fault: must NOT trip for this long

    # --- I/O mappings (adapt to your model or GPI/O wiring) ---
    # Use either model signals or physical DI/DO names exposed via HIL configuration.
    "arm_input_name": "DI_ARM",        # TODO: digital input (to arm relay/logic) or model signal
    "trip_output_name": "DO_TRIP",     # TODO: digital output that goes high when relay trips
    "pickup_output_name": "DO_PICKUP", # optional: differential element pickup indication

    # --- Measured signals (optional, for extra checks/records) ---
    "meas_currents": ["Ia_bus", "Ib_bus", "Ic_bus"],  # TODO: model analog signal names
    "meas_voltages": ["Va_bus", "Vb_bus", "Vc_bus"],  # TODO

    # --- Fault control (choose one style and comment the other) ---
    # Option A) Digital inputs that enable faults inside the model
    "internal_fault_di": "DI_FAULT_INTERNAL",  # TODO
    "external_fault_di": "DI_FAULT_EXTERNAL",  # TODO

    # Option B) Direct parameter writes to built-in Fault components
    # "internal_fault_component": r"Grid/BusbarFault",      # example path in model tree
    # "external_fault_component": r"Feeder3/FeederFault",
    # "fault_param_enable": "enabled",                      # parameter name to toggle
    # "fault_param_r_f": "Rfault",                          # ohmic fault parameter (if needed)
    # "fault_param_x_f": "Xfault",
    # "fault_impedance": (0.001, 0.0),                      # R, X for bolted fault
    # --- Capture ---
    "capture_csv": True,
    "capture_dir": "test_artifacts",
}


# =========================
# ===== Utilities =========
# =========================
def ensure_capture_dir():
    os.makedirs(CONFIG["capture_dir"], exist_ok=True)


def now_str():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def sleep_s(sec):
    # Small helper that can be intercepted if you want to sync to grid periods later
    time.sleep(sec)


def set_di(name, value: int):
    """Set digital input or model boolean signal."""
    try:
        hil.set_digital_input_value(name, value)
    except Exception:
        # Fallback if your model exposes this as a top-level parameter/signal
        hil.set_signal_value(name, float(value))


def get_do(name) -> int:
    """Read digital output or model boolean signal."""
    try:
        return int(hil.get_digital_output_value(name))
    except Exception:
        return int(hil.get_signal_value(name) > 0.5)


def get_signal(name) -> float:
    """Read analog value."""
    return float(hil.get_signal_value(name))


def set_fault_di(di_name: str, on: bool):
    set_di(di_name, 1 if on else 0)


def set_fault_component(path: str, enable: bool):
    # Example for parameter-based control; adjust param names in CONFIG if using this mode.
    hil.set_parameter_value(path, CONFIG.get("fault_param_enable", "enabled"), 1 if enable else 0)
    if enable and ("fault_param_r_f" in CONFIG or "fault_param_x_f" in CONFIG):
        r = CONFIG.get("fault_impedance", (0.001, 0.0))[0]
        x = CONFIG.get("fault_impedance", (0.001, 0.0))[1]
        if "fault_param_r_f" in CONFIG:
            hil.set_parameter_value(path, CONFIG["fault_param_r_f"], r)
        if "fault_param_x_f" in CONFIG:
            hil.set_parameter_value(path, CONFIG["fault_param_x_f"], x)


def capture_row(writer, t0, label):
    row = {
        "t_since_start_s": time.perf_counter() - t0,
        "label": label,
    }
    for sig in CONFIG["meas_currents"] + CONFIG["meas_voltages"]:
        try:
            row[sig] = get_signal(sig)
        except Exception:
            row[sig] = float("nan")
    writer.writerow(row)


# =========================
# ===== Main Tests ========
# =========================
class BusbarDiffTester:
    def __init__(self):
        self.results = []
        self.t_trip_internal = None
        self.t_pickup_internal = None

    def load_and_start(self):
        print("Loading and starting simulation...")
        model_path = CONFIG["compiled_model_path"] or CONFIG["model_path"]
        if model_path.lower().endswith(".tse"):
            hil.load_model(model_path)
            hil.compile_model()  # compile on the fly
        else:
            hil.load_model(model_path)
        hil.start_simulation()
        print("Simulation started.")

    def stop_and_unload(self):
        print("Stopping simulation...")
        try:
            hil.stop_simulation()
        finally:
            try:
                hil.release_hardware()
            except Exception:
                pass
        print("Simulation stopped.")

    def arm_protection(self):
        print("Arming protection...")
        set_di(CONFIG["arm_input_name"], 1)
        sleep_s(0.05)

    def wait_for_pickup_or_trip(self, t0, pickup_name=None, trip_name=None, timeout=0.5):
        t_start = time.perf_counter()
        t_pickup = None
        t_trip = None
        while (time.perf_counter() - t_start) < timeout:
            if pickup_name:
                if get_do(pickup_name):
                    t_pickup = time.perf_counter()
            if trip_name and get_do(trip_name):
                t_trip = time.perf_counter()
                break
            time.sleep(0.001)  # 1 ms poll
        return t_pickup, t_trip

    def apply_internal_fault(self, on: bool):
        if "internal_fault_di" in CONFIG and CONFIG["internal_fault_di"]:
            set_fault_di(CONFIG["internal_fault_di"], on)
        elif "internal_fault_component" in CONFIG:
            set_fault_component(CONFIG["internal_fault_component"], on)
        else:
            raise RuntimeError("No internal fault control configured.")

    def apply_external_fault(self, on: bool):
        if "external_fault_di" in CONFIG and CONFIG["external_fault_di"]:
            set_fault_di(CONFIG["external_fault_di"], on)
        elif "external_fault_component" in CONFIG:
            set_fault_component(CONFIG["external_fault_component"], on)
        else:
            raise RuntimeError("No external fault control configured.")

    def run_internal_fault_test(self):
        print("\n=== INTERNAL BUSBAR FAULT TEST ===")
        ensure_capture_dir()
        csv_path = os.path.join(CONFIG["capture_dir"], f"internal_fault_{now_str()}.csv")
        pickup_name = CONFIG.get("pickup_output_name")
        trip_name = CONFIG.get("trip_output_name")

        with open(csv_path, "w", newline="") as f:
            fieldnames = ["t_since_start_s", "label"] + CONFIG["meas_currents"] + CONFIG["meas_voltages"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            t0 = time.perf_counter()
            capture_row(writer, t0, "start")

            # Prefault
            sleep_s(CONFIG["prefault_time_s"])
            capture_row(writer, t0, "prefault")

            # Apply internal 3φ fault
            print("Applying internal fault...")
            self.apply_internal_fault(True)
            t_fault = time.perf_counter()

            # Observe pickup/trip
            t_pickup, t_trip = self.wait_for_pickup_or_trip(
                t_fault,
                pickup_name=pickup_name,
                trip_name=trip_name,
                timeout=max(CONFIG["expect_trip_in_s"] * 2.0, 0.5),
            )

            if t_pickup:
                self.t_pickup_internal = t_pickup - t_fault
            if t_trip:
                self.t_trip_internal = t_trip - t_fault

            capture_row(writer, t0, "fault_applied")
            sleep_s(CONFIG["fault_duration_s"])

            # Clear fault
            print("Clearing internal fault...")
            self.apply_internal_fault(False)
            capture_row(writer, t0, "fault_cleared")

            sleep_s(CONFIG["postfault_time_s"])

        # Assertions
        passed = True
        messages = []

        if self.t_pickup_internal is None:
            passed = False
            messages.append("Pickup not detected.")
        else:
            if self.t_pickup_internal > CONFIG["expect_pickup_in_s"]:
                passed = False
                messages.append(f"Pickup too slow: {self.t_pickup_internal*1000:.1f} ms > {CONFIG['expect_pickup_in_s']*1000:.1f} ms")
            else:
                messages.append(f"Pickup OK: {self.t_pickup_internal*1000:.1f} ms")

        if self.t_trip_internal is None:
            passed = False
            messages.append("Trip not detected.")
        else:
            if self.t_trip_internal > CONFIG["expect_trip_in_s"]:
                passed = False
                messages.append(f"Trip too slow: {self.t_trip_internal*1000:.1f} ms > {CONFIG['expect_trip_in_s']*1000:.1f} ms")
            else:
                messages.append(f"Trip OK: {self.t_trip_internal*1000:.1f} ms")

        self.results.append({
            "test": "Internal busbar fault",
            "passed": passed,
            "details": "; ".join(messages),
            "pickup_ms": None if self.t_pickup_internal is None else self.t_pickup_internal * 1000.0,
            "trip_ms": None if self.t_trip_internal is None else self.t_trip_internal * 1000.0,
            "csv": csv_path if CONFIG["capture_csv"] else None,
        })
        print("\n".join(messages))
        print(f"CSV: {csv_path}")

    def run_external_fault_test(self):
        print("\n=== EXTERNAL FAULT (STABILITY) TEST ===")
        ensure_capture_dir()
        csv_path = os.path.join(CONFIG["capture_dir"], f"external_fault_{now_str()}.csv")
        trip_name = CONFIG.get("trip_output_name")

        with open(csv_path, "w", newline="") as f:
            fieldnames = ["t_since_start_s", "label"] + CONFIG["meas_currents"] + CONFIG["meas_voltages"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            t0 = time.perf_counter()
            capture_row(writer, t0, "start")

            # Prefault
            sleep_s(CONFIG["prefault_time_s"])
            capture_row(writer, t0, "prefault")

            print("Applying external fault...")
            self.apply_external_fault(True)
            t_fault = time.perf_counter()

            tripped = False
            t_start = time.perf_counter()
            while (time.perf_counter() - t_start) < CONFIG["stability_window_s"]:
                if trip_name and get_do(trip_name):
                    tripped = True
                    break
                time.sleep(0.001)

            capture_row(writer, t0, "external_fault_window_done")

            print("Clearing external fault...")
            self.apply_external_fault(False)
            capture_row(writer, t0, "fault_cleared")

            sleep_s(CONFIG["postfault_time_s"])

        passed = not tripped
        details = "Stable (no trip) during external fault window." if passed else "FAILED: Relay tripped for external fault."
        self.results.append({
            "test": "External fault stability",
            "passed": passed,
            "details": details,
            "csv": csv_path if CONFIG["capture_csv"] else None,
        })
        print(details)
        print(f"CSV: {csv_path}")

    def summary(self):
        print("\n================= SUMMARY =================")
        any_fail = False
        for r in self.results:
            status = "PASS" if r["passed"] else "FAIL"
            if not r["passed"]:
                any_fail = True
            line = f"{status} - {r['test']}: {r['details']}"
            if r.get("pickup_ms") is not None:
                line += f" | pickup={r['pickup_ms']:.1f} ms"
            if r.get("trip_ms") is not None:
                line += f" | trip={r['trip_ms']:.1f} ms"
            print(line)
            if r.get("csv"):
                print(f"  data: {r['csv']}")
        print("==========================================")
        return 0 if not any_fail else 1


def main():
    tester = BusbarDiffTester()
    try:
        tester.load_and_start()
        tester.arm_protection()
        tester.run_internal_fault_test()
        tester.run_external_fault_test()
    finally:
        tester.stop_and_unload()
    exit_code = tester.summary()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
