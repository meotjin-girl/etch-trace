"""SECS/GEM mock etch tool: one process per tool, one run loop per chamber."""

import datetime
import logging
import os
import random
import threading
import time

import secsgem.common
import secsgem.gem
import secsgem.hsms
import secsgem.secs
from secsgem.secs.variables import F8, U1, U4, String

import sensors

log = logging.getLogger("equipment")
KST = datetime.timezone(datetime.timedelta(hours=9))


def svid_type(name: str):
    if name in ("run_no", "sample_offset_s"):
        return U4
    if name == "plasma_detected":
        return U1
    return String if name in sensors.CONTEXT or name == "sensor_data_quality" else F8


class Tool(secsgem.gem.GemEquipmentHandler):
    def __init__(self, settings: secsgem.common.Settings, tool_id: str):
        super().__init__(settings)
        self._mdln, self._softrev = "ETCH-MOCK", "1.0.0"
        self.tool_id = tool_id
        self.values: dict[int, object] = {}
        self._run_no = 1100
        self._lock = threading.Lock()

        for chamber, band in sensors.CHAMBER_BAND.items():
            for name, offset in sensors.SVID_OFFSET.items():
                vtype = svid_type(name)
                unit = sensors.SENSORS.get(name, (None,) * 5)[4] or ""
                self.status_variables[band + offset] = secsgem.gem.StatusVariable(
                    band + offset, f"{chamber}.{name}", unit, vtype
                )
                self.values[band + offset] = "" if vtype is String else 0
            for i, (name, (*_, ocap)) in enumerate(sensors.ALARMS.items()):
                alid = band + sensors.ALID_OFFSET + i
                alarm = secsgem.gem.Alarm(
                    alid, f"{chamber}.{name}", f"{chamber} {name} {ocap}",
                    secsgem.secs.data_items.ALCD.PARAMETER_CONTROL_ERROR, 0, 0,
                )
                # ponytail: alarms report from start; a host S5F3 can still disable them
                alarm.enabled = True
                self.alarms[alid] = alarm
            for ceid, name in ((sensors.CEID_RUN_START, "RUN_START"), (sensors.CEID_RUN_END, "RUN_END")):
                self.collection_events[band + ceid] = secsgem.gem.CollectionEvent(band + ceid, f"{chamber}.{name}", [])

    def on_sv_value_request(self, svid, status_variable):
        return status_variable.value_type(self.values[status_variable.svid])

    def next_run_no(self) -> int:
        with self._lock:
            self._run_no += 1
            return self._run_no

    def sync_alarms(self, band: int, active: set[str]) -> None:
        for i, name in enumerate(sensors.ALARMS):
            alarm = self.alarms[band + sensors.ALID_OFFSET + i]
            if (name in active) != alarm.set:
                try:
                    (self.set_alarm if name in active else self.clear_alarm)(alarm.alid)
                except Exception:  # host gone mid-send: keep local state so the AlarmsSet SV stays right
                    log.exception("alarm %s send failed", alarm.name)
                    alarm.set = name in active

    def run_chamber(self, chamber: str, rng: random.Random, fault_rate: float, noise: float) -> None:
        band = sensors.CHAMBER_BAND[chamber]
        faults = sensors.FAULTS[(self.tool_id, chamber)]
        tool_no = self.tool_id[-1]
        deadline = time.monotonic()
        while True:
            now = datetime.datetime.now(KST)
            lot_id = f"SIMLOT-{now:%Y%m%d}-{tool_no}{chamber[-1]}{now:%H%M%S}"
            scenario = rng.choice(faults) if rng.random() < fault_rate else "NORMAL"
            # the scenario is the hidden ground-truth label: logged here, never exposed over SECS
            log.info("%s/%s run lot=%s scenario=%s", self.tool_id, chamber, lot_id, scenario)
            context = {
                "lot_id": lot_id,
                "wafer_id": f"{lot_id}-W01",
                "recipe_id": sensors.RECIPE_ID,
                "recipe_step": "MAIN_ETCH",
                "process_state": "PROCESSING",
                "run_no": self.next_run_no(),
            }
            for sample in sensors.run_samples(scenario, rng, noise):
                for name, value in (context | sample).items():
                    self.values[band + sensors.SVID_OFFSET[name]] = value
                if sample["sample_offset_s"] == 0:
                    self.trigger_collection_events([band + sensors.CEID_RUN_START])
                self.sync_alarms(band, sensors.active_alarms(sample))
                deadline += sensors.SAMPLE_S
                time.sleep(max(0.0, deadline - time.monotonic()))
            self.trigger_collection_events([band + sensors.CEID_RUN_END])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("secsgem").setLevel(logging.WARNING)
    logging.getLogger("communication").setLevel(logging.WARNING)
    settings = secsgem.hsms.HsmsSettings(
        address="0.0.0.0",
        port=int(os.getenv("HSMS_PORT", "5000")),
        connect_mode=secsgem.hsms.HsmsConnectMode.PASSIVE,
        device_type=secsgem.common.DeviceType.EQUIPMENT,
    )
    tool = Tool(settings, os.environ["TOOL_ID"])
    tool.enable()
    fault_rate = float(os.getenv("FAULT_RATE", "0.1"))
    noise = float(os.getenv("NOISE_SCALE", "1.0"))
    for chamber in sensors.CHAMBER_BAND:
        args = (chamber, random.Random(), fault_rate, noise)
        threading.Thread(target=tool.run_chamber, args=args, daemon=True, name=chamber).start()
    threading.Event().wait()


if __name__ == "__main__":
    main()
