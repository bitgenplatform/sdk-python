"""The package as an integrator gets it: `consumer.py` is type-checked in strict mode against the installed wheel (the
`# type: ignore[...]` lines are expected errors — an unused one means the typing regressed), `smoke.py` runs the wheel
against the test server. Both run in the `package` job of the CI, in a blank environment where only the wheel is
installed."""
