# Smart Search fault-injected acceptance

- Run: `acceptance-final`
- Source commits: `620149f8665ebd11f4cb404bac480b26e673f9da, 7a58705a2e63dfa7c1fbd21f139efa1715597eef, 812dd3ba6a373febd8331cf734c11949af527eb1`
- Suite verdict: **PASS**
- Doctor probes: `1` / `1`

## Cases

- A1: **PASS** at `7a58705a2e63dfa7c1fbd21f139efa1715597eef`; injected evidence `gateway-events.jsonl:1, gateway-events.jsonl:2`; verified sources `10`.
- A2: **PASS** at `7a58705a2e63dfa7c1fbd21f139efa1715597eef`; injected evidence `gateway-events.jsonl:1`; verified sources `14`.
- A3: **PASS** at `812dd3ba6a373febd8331cf734c11949af527eb1`; injected evidence `gateway-events.jsonl:1, gateway-events.jsonl:2, gateway-events.jsonl:3`; verified sources `14`.
- A4: **PASS** at `620149f8665ebd11f4cb404bac480b26e673f9da`; injected evidence `gateway-events.jsonl:1`; verified sources `7`.
- A5: **PASS** at `620149f8665ebd11f4cb404bac480b26e673f9da`; injected evidence `gateway-events.jsonl:1, gateway-events.jsonl:2, gateway-events.jsonl:3, gateway-events.jsonl:4`; verified sources `4`.

## Superseded attempts

- A1: valid FAIL retained as sanitized correction evidence; superseded by final `7a58705a2e63dfa7c1fbd21f139efa1715597eef` PASS.
- A4: valid FAIL retained as sanitized correction evidence; superseded by final `620149f8665ebd11f4cb404bac480b26e673f9da` PASS.
- A5: valid FAIL retained as sanitized correction evidence; superseded by final `620149f8665ebd11f4cb404bac480b26e673f9da` PASS.
