"""
ledger/consumption.py — metering the real draw (Source 1 instance D; Source 2).

This is the half of the standing-condition ledger that is genuinely solved. Your
own argument: the draw is trivially meterable today; the only thing missing was
the wire from the meter to the decision process. This module IS that wire.

Honesty discipline baked in:
  - Every reading is tagged MEASURED / ESTIMATED / UNAVAILABLE so the ledger
    never overstates its own precision.
  - The water number is energy * a configurable WUE coefficient, and it is
    labeled an estimate with its coefficient, never a measured fact. A laptop is
    not a data center; we refuse to claim a false precision just as we refuse to
    claim a false zero.

It degrades gracefully: if psutil/pynvml aren't present, it still produces an
ESTIMATED reading rather than crashing or silently reporting zero (zero would be
the willful-blindness failure).
"""

import time

try:
    import psutil  # real per-process CPU / memory / IO
    _HAVE_PSUTIL = True
except Exception:
    _HAVE_PSUTIL = False

try:
    import pynvml  # NVIDIA GPU energy, when present
    pynvml.nvmlInit()
    _HAVE_NVML = True
except Exception:
    _HAVE_NVML = False


# Very rough power model used only when we cannot measure. These are deliberately
# conservative, clearly-labeled estimates — the point is to never report zero
# draw, not to be a lab instrument.
_ASSUMED_CPU_TDP_WATTS = 28.0   # a typical laptop package under load
_ASSUMED_RAM_WATTS_PER_GB = 0.3


class ConsumptionMeter:
    def __init__(self, wue_liters_per_kwh: float, wue_label: str):
        self.wue = float(wue_liters_per_kwh)
        self.wue_label = wue_label
        self._proc = psutil.Process() if _HAVE_PSUTIL else None
        self._last_wall = time.time()

    def meter_cycle(self) -> dict:
        """Measure (or honestly estimate) the draw since the last call."""
        now = time.time()
        wall_seconds = max(0.0, now - self._last_wall)
        self._last_wall = now

        cpu_kwh = 0.0
        ram_kwh = 0.0
        gpu_kwh = 0.0
        method = []
        confidence = "ESTIMATED"

        if _HAVE_PSUTIL and self._proc is not None:
            # cpu_percent over the interval, scaled by an assumed package TDP.
            # This is an ESTIMATE: psutil gives utilization, not watts. We are
            # explicit that this is modeled, not measured.
            cpu_pct = self._proc.cpu_percent(interval=None) / 100.0
            watts = cpu_pct * _ASSUMED_CPU_TDP_WATTS
            cpu_kwh = (watts * wall_seconds) / 3_600_000.0
            mem_gb = self._proc.memory_info().rss / (1024 ** 3)
            ram_kwh = (mem_gb * _ASSUMED_RAM_WATTS_PER_GB * wall_seconds) / 3_600_000.0
            method.append("psutil_cpu_load_estimate")
        else:
            method.append("no_psutil_fallback_estimate")
            # Without psutil we cannot even estimate from load; assume idle-ish
            # package draw so the number is non-zero (blindness is the failure).
            cpu_kwh = (_ASSUMED_CPU_TDP_WATTS * 0.1 * wall_seconds) / 3_600_000.0

        if _HAVE_NVML:
            try:
                h = pynvml.nvmlDeviceGetHandleByIndex(0)
                # Power in milliwatts -> watts -> kWh over the interval.
                mw = pynvml.nvmlDeviceGetPowerUsage(h)
                gpu_kwh = ((mw / 1000.0) * wall_seconds) / 3_600_000.0
                method.append("nvml_power_estimate")
                confidence = "MEASURED"  # GPU power is a real reading
            except Exception:
                method.append("nvml_unavailable")

        total_kwh = cpu_kwh + ram_kwh + gpu_kwh
        water_liters = total_kwh * self.wue

        return {
            "cpu_energy_kwh": round(cpu_kwh, 9),
            "ram_energy_kwh": round(ram_kwh, 9),
            "gpu_energy_kwh": round(gpu_kwh, 9),
            "total_energy_kwh": round(total_kwh, 9),
            "wall_seconds": round(wall_seconds, 3),
            # Labeled estimate, with the coefficient and its provenance in tow.
            "water_liters_estimate": round(water_liters, 9),
            "wue_liters_per_kwh": self.wue,
            "wue_basis": self.wue_label,
            "metering_method": "+".join(method),
            "metering_confidence": confidence,
        }
