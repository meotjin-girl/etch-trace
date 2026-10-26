# TRACE Agent Physics E2E deterministic tool output

This is the actual structured output of the freshly built Agent's `simulate_mock_fab_etch`
tool over the live Sensor MCP and Physics MCP services. A final LLM-authored prose response was
not captured because the running development container's configured OpenAI API key returned 401.

- Status: `SIMULATED`
- Validation: `NOT_VALIDATED`
- Run ID: `ETCH-01:CH-A:1101`
- Equipment / chamber: `ETCH-01 / CH-A`
- Lot: `SIMLOT-20261026-1A134022`
- Wafer: `SIMLOT-20261026-1A134022-W01`
- Recipe / step: `RCP-OX-ETCH-EDU-01 / MAIN_ETCH`
- Sensor snapshot: `sha256:4376396f68ecd6fdf60583b70ae8940c8ce94f370dbfb207a15376fcab48c4ad`
- Input range: `0.0~120.0 s`, 25 GOOD samples, adjacent `offset_sec` intervals of 5 s
- Initial depth: `0.0 nm`
- Base etch rate: `100.0 nm/min`
- ARDE coefficient: `0.10`, user input, uncalibrated educational assumption

## Equations returned by Physics MCP

```text
delta_x = (x - x_reference) / abs(x_reference)
relative_rate = clamp(1 + sum(beta_x * delta_x), 0.1, 2.0)
R_ARDE = base_rate * relative_rate / (1 + k_ARDE * aspect_ratio)
D[n+1] = D[n] + R_ARDE[n] * delta_t / 60
aspect_ratio = depth / opening_width
```

The integration implementation uses the left interval rate and the difference between adjacent `offset_sec` values. The last sample at 120 s reports the rate/profile state but does not add an interval after 120 s.

## Uncalibrated sensitivity coefficients

| Variable | Coefficient | Unit | Source |
|---|---:|---|---|
| Source RF | 0.35 | per relative change | TRACE educational assumption v1 |
| Bias RF | 0.25 | per relative change | TRACE educational assumption v1 |
| Pressure | -0.15 | per relative change | TRACE educational assumption v1 |
| SF6 | 0.30 | per relative change | TRACE educational assumption v1 |
| O2 | -0.10 | per relative change | TRACE educational assumption v1 |
| ESC temperature | 0.05 | per relative change | TRACE educational assumption v1 |

## Final comparison

| Width | Final depth | Final AR | Final ARDE rate |
|---:|---:|---:|---:|
| 200 nm | 191.1707515233 nm | 0.9558537576 | 91.2282597353 nm/min |
| 40 nm | 166.6663945364 nm | 4.1666598634 | 70.5518083909 nm/min |

`40 nm - 200 nm` final depth difference is `-24.5043569869 nm`. The same Run, sensor snapshot, time range, process points, base rate, coefficient set, and ARDE coefficient were used; only feature width changed.

The 2D output is a fixed-width rectangular removed-region diagram. It does not predict bowing, taper, or sidewall angle. These outputs are not measured etch rates, validated profiles, equipment-fault evidence, OCAP dispositions, recipe-change authority, or Lot Release evidence.
