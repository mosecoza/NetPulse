# Software Requirements & Technical Specification

- **Project Name:** NetPulse Local (Device-Level Wi-Fi, Dropout & ISP Interference Diagnostic Web App)
- **Version:** 2.4 (Execution-Ready Engineering Specification)
- **Architecture:** Local Client-Server Web Application (127.0.0.1)

## 1. Executive Summary & Objective

NetPulse Local is a self-hosted, device-level network diagnostic web application engineered to isolate the root causes of intermittent connection dropouts, Wi-Fi radio degradation, ISP traffic shaping, and service-level blocking. Because web browsers sandbox raw network sockets and hardware telemetry, a least-privilege local background daemon collects deterministic telemetry and serves an authenticated web dashboard on localhost.

### Core Diagnostic Goals

1. Deterministic Fault Isolation: Separate local Wi-Fi link drops, router hangs, DNS failures, and ISP outages using N-of-M state machines, asymmetric recovery debouncing, and multi-signal confidence scoring.
2. Wi-Fi Radio Correlation: Map latency jitter and packet loss against physical wireless metrics (RSSI, link rate, channel, and BSSID roaming) with explicit degraded-mode reporting when OS permissions are restricted.
3. Throughput & Bufferbloat Measurement: Execute scheduled or on-demand bandwidth tests with concurrent loaded-latency measurement and idle-traffic deferral.
4. Safe ISP Interference Detection: Detect DNS tampering, TLS SNI resets, and protocol throttling within strict rate limits, userspace VPN isolation, target allowlists, and informed user consent.
5. Bounded Long-Term Telemetry & Full Observability: Maintain predictable disk (<= 500 MB) and memory footprints over multi-month runtimes with ULID request tracing, dual-clock safety, and deterministic numeric serialization.

## 2. System Architecture

```text
+-----------------------------------------------------------------------+

|                  Host Device (Windows / macOS / Linux)                |
|                                                                       |
|  +-----------------------+           +-----------------------------+  |
|  |   OS Network Layer    |           |       Local Storage         |  |
|  | - ICMP / TCP / ARP    |           | SQLite WAL (netpulse.db)    |  |
|  | - Wi-Fi CLI / APIs    |           | Capped at 500 MB + Rollups  |  |
|  | - Speedtest & Wireprx |           +--------------+--------------+  |
|  +-----------+-----------+                          ^                 |
|              |                                      |                 |
|              v                                      v                 |
|  +-----------------------------------------------------------------+  |
|  |               Backend Engine (Python 3.11+ / FastAPI)           |  |
|  |  - Diagnostic State Machine (N-of-M + Asymmetric Recovery)      |  |
|  |  - Startup Capability Matrix & Graceful Degraded-Mode Manager   |  |
|  |  - ULID Trace Context, Dual-Clock & Bounded WS Broadcaster      |  |
|  +------------------------------+----------------------------------+  |
|                                 |                                     |
|                 Authenticated WebSockets / REST JSON                  |
|                                 |                                     |
|                                 v                                     |
|  +-----------------------------------------------------------------+  |
|  |             Web Frontend (HTML5 / ES6 / Chart.js)               |  |
|  |  - Telemetry Charts, Degraded-Mode Badges & Fault Diagnosis     |  |
|  +-----------------------------------------------------------------+  |
+-----------------------------------------------------------------------+
```

## 3. Diagnostic Truth Model & State Machine (Module A)

To eliminate false positives from single-packet ICMP deprioritization or transient upstream jitter, fault classification operates as a finite state machine per fault category rather than evaluating isolated samples.

### 3.1 State Machine Lifecycle

Every monitored fault domain transitions through five deterministic states:

1. HEALTHY: Normal baseline operation.
2. SUSPECT: Initial threshold breach detected (>= 1 sample); telemetry is buffered while awaiting N-of-M confirmation. No alert banner is raised.
3. ACTIVE_FAULT: Failure meets both the N-of-M ratio and minimum monotonic duration threshold. A discrete record is opened in anomaly_events, and the UI raises a fault alert.
4. RECOVERING: Probe checks begin succeeding, awaiting the asymmetric clear-recovery window (10/10 consecutive healthy samples over 10s) to prevent alert flapping during unstable links.
5. RESOLVED: Recovery window satisfied; anomaly_events.end_time (RFC 3339 UTC) and duration_ms / duration_sec (monotonic delta) are finalized, and the state returns to HEALTHY.

### 3.2 Probe Cadence & Targets

- Gateway Target: Auto-detected default gateway IP (1000 ms cadence, 800 ms monotonic timeout).
- External Primary & Secondary: 1.1.1.1 and 9.9.9.9 (1000 ms cadence, 1000 ms monotonic timeout).
- External TCP Fallback (Port 443): 1.1.1.1:443 and 8.8.8.8:443 (triggered immediately on ICMP failure to rule out upstream ICMP rate-limiting).
- DNS Probe: Uncached randomized A record query (&lt;uuid&gt;.netpulse-probe.invalid) against system DNS every 5000 ms (1500 ms timeout), paired with an encrypted DoH control check (1.1.1.1).

### 3.3 Fault Rules, Debounce Windows & Confidence Tiers

Confidence is assigned as a discrete enum (LOW, MEDIUM, HIGH) based on the number of independent corroborating telemetry signals:

| Fault Code (enum) | Trigger Rule (N-of-M) | Min Duration | Clear-Recovery Window | Confidence Tier & Corroborating Signals |
| --- | --- | --- | --- | --- |
| LOCAL_WIFI_DROP | Gateway fails 4/5 samples AND (OS Wi-Fi state = DISCONNECTED OR RSSI < -85 dBm). | 5 seconds | 10/10 consecutive healthy samples (10s) | HIGH (3 signals: GATEWAY_TIMEOUT, EXT_TIMEOUT, WIFI_DISCONNECTED_OR_WEAK). |
| ROUTER_HANG | Gateway fails 4/5 samples AND OS Wi-Fi state = CONNECTED (RSSI >= -75 dBm) AND ARP neighbor probe fails. | 5 seconds | 10/10 consecutive healthy samples (10s) | HIGH (3 signals: WIFI_CONNECTED, ARP_STALE, GATEWAY_TIMEOUT). |
| ISP_OUTAGE | Gateway healthy (RTT < 15.0 ms, 0.0% loss) AND both 1.1.1.1 and 9.9.9.9 fail ICMP + TCP:443 in 4/5 samples. | 5 seconds | 10/10 consecutive healthy samples (10s) | HIGH (3 signals: GATEWAY_OK, EXT_ICMP_TIMEOUT, EXT_TCP443_TIMEOUT). |
| WIFI_CONGESTION | Gateway RTT > 100.0 ms (or Jitter > 40.0 ms) in 6/10 samples while (External_RTT - Gateway_RTT) < 30.0 ms. | 10 seconds | 10/10 samples with Gateway RTT < 40.0 ms | MEDIUM (2 signals: GATEWAY_HIGH_RTT, UPSTREAM_DELTA_FLAT). |
| ISP_CONGESTION | Gateway RTT < 15.0 ms AND External RTT > 150.0 ms (or loss > 5.0%) across both targets in 6/10 samples. | 10 seconds | 10/10 samples with External RTT < 80.0 ms | MEDIUM (2 signals: GATEWAY_OK, EXT_HIGH_RTT_OR_LOSS). |
| DNS_FAILURE | Gateway healthy AND External TCP:443 healthy, but System DNS fails 2/2 probes while DoH (1.1.1.1) succeeds. | 10 seconds | 2/2 consecutive System DNS successes (10s) | HIGH (3 signals: TRANSPORT_OK, SYS_DNS_FAIL, DOH_CONTROL_OK). |
| TRANSIENT_ANOMALY | Any threshold breach that recovers before meeting ACTIVE_FAULT duration. | < 5 seconds | Immediate | LOW (1 signal: Logged in metrics only; does not raise UI alert). |

## 4. Cross-Platform Privilege Strategy & Capability Matrix

At startup, the backend runs a Capability Self-Check and exposes the result at GET /api/system/capabilities. Missing OS tools or elevated permissions never cause unhandled exceptions; instead, subsystems enter documented degraded modes surfaced via UI badges.
Before accepting requests, log the matrix as structured JSON including UTC timestamp, app version, OS, and capability values; emit a human-readable WARNING for each degraded or unavailable feature. Do not log session tokens or network identifiers.

| Subsystem | Required / Preferred | Windows 10/11 | macOS 13+ | Linux (Desktop / systemd) | Degraded-Mode Fallback & API Flag |
| --- | --- | --- | --- | --- | --- |
| ICMP Latency | Optional (Unprivileged preferred) | icmplib via Windows IcmpSendEcho API (standard user). | icmplib via unprivileged SOCK_DGRAM (IPPROTO_ICMP). | SOCK_DGRAM if ping_group_range permits, or CAP_NET_RAW. | icmp_fallback_tcp_arp: External targets fall back to TCP:443 SYN RTT; Gateway falls back to ARP/Neighbor cache refresh + UDP unreachable probe. |
| Wi-Fi Telemetry | Optional (Graceful skip on Ethernet/blocked) | netsh wlan show interfaces (requires Location permission on Win11 24H2+). | wdutil info (privileged helper) or unprivileged system_profiler SPAirPortDataType. | nmcli -t or /proc/net/wireless + iw dev <iface> link. | wifi_metrics_unavailable: Sets wifi.available = false in API/UI, hides RSSI charts, and evaluates faults using Gateway + External probes only. |
| Raw Packet / DPI Inspection (Module E) | Optional (Requires admin/helper) | Npcap driver + Admin rights for scapy TCP RST capture. | Privileged launchd helper with /dev/bpf* read access. | CAP_NET_RAW capability on isolated probe binary. | raw_sockets_unavailable: Disables packet-level TCP RST sniffing; falls back to userspace TLS ClientHello socket error classification + DoH comparison. |
| Speedtest & VPN Diff | Optional (Bundled / userspace) | Bundled signed speedtest.exe + userspace wireproxy.exe. | Bundled signed speedtest + userspace wireproxy. | Bundled signed speedtest + userspace wireproxy. | speedtest_cli_missing / vpn_diff_unavailable: Falls back to internal chunked HTTPS throughput test against Cloudflare endpoints; disables VPN comparison toggle. |

## 5. Performance, Storage & Backpressure Policy

### 5.1 Tiered Retention & Downsampling Schedule

- In-Memory Ring Buffer (RAM): Retains 3,600 1-second raw samples (1 hour rolling window, ~1.2 MB RAM) for instant WebSocket chart hydration. 1-second samples are not written to disk, eliminating SSD/SD-card write amplification.
- Tier 1 (ping_agg_1m & wifi_agg_1m): Aggregated every 60 seconds using the fields in Section 8 and written to SQLite. Retained for 30 days.
- Tier 2 (ping_agg_daily): Rolled up once daily at 02:00 local time. Retained for 12 months (365 days).
- Discrete Events (anomaly_events, speed_tests, isp_probe_results): Retained for 12 months (365 days) independently of metric rollup pruning so ISP support evidence is never prematurely purged.
- Rollup semantics: Minute buckets use UTC sample timestamps. Gateway and primary external RTT min/average and p95 use successful measurements only; DNS average uses successful DNS measurements. Averages are arithmetic means and p95 uses the nearest-rank method (rank ceil(0.95 * count)). Minute loss_pct is failed primary external probe attempts divided by all attempted primary external probes, times 100. No observations or attempts yields null for the affected value; an observed all-failed interval has 100.0 loss and null RTT.
- Daily UTC buckets use the arithmetic mean of available minute averages and loss percentages, weighted equally per minute; ext_p95_ms is the nearest-rank p95 of available minute ext_avg_ms values, not the p95 of raw samples. total_outage_sec sums monotonic duration_sec of resolved LOCAL_WIFI_DROP, ROUTER_HANG and ISP_OUTAGE events whose start_time falls on that UTC day; overlapping faults are counted separately. Late-arriving resolved events update the relevant daily bucket while retained. Missing constituent values stay null rather than becoming zero, except total_outage_sec is zero when no qualifying events exist.
- Roaming: Preserve each BSSID's distinct per-minute aggregate; each available sample contributes to exactly one BSSID row. The RSSI chart shows the row with the greatest sample_count per minute (ties broken by lexicographically smallest BSSID), with a roam marker when the selected BSSID changes between consecutive populated minutes. Tooltips show the selected BSSID and sample count; gaps are not interpolated. The history API returns all BSSID rows, not just the selected row.

### 5.2 Database Sizing, WAL & Incremental Vacuum

- SQLite Pragmas:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA auto_vacuum = INCREMENTAL;
```

- Max Disk Quota: Hard cap of 500 MB for netpulse.db (including -wal and -shm files).
- Maintenance & Pruning Worker: Runs daily at 02:15 local time and whenever DB size exceeds 450 MB:
   1. Deletes rows older than tier retention limits.
   2. If size still exceeds 450 MB, deletes oldest ping_agg_1m and wifi_agg_1m rows in 5,000-row batches until size < 420 MB.
   3. Executes PRAGMA incremental_vacuum(500); (non-blocking, unlike full VACUUM).

### 5.3 WebSocket Backpressure & CPU Guardrails

- Bounded Per-Client Queues: Each connected WebSocket client receives an asyncio.Queue(maxsize=10).
- Drop-Oldest Policy: If a client browser tab is background-throttled and its queue reaches capacity, the broadcaster pops and discards the oldest frame (queue.get_nowait()) before enqueuing the new tick. Telemetry collectors never block on slow WebSocket consumers.
- Idle Bandwidth Guardrail: Before running a scheduled Speedtest, the daemon samples OS interface counters (psutil.net_io_counters()) for 10 seconds (measured via time.monotonic()). If active user traffic exceeds 2.00 Mbps, the scheduled test defers by 15 minutes.

### 5.4 Graceful Shutdown & Recovery

- The server lifecycle handles SIGTERM and SIGINT on supported Unix systems and the applicable Windows console or service-stop event; avoid installing competing signal handlers over the server's own lifecycle.
- On shutdown, stop scheduling and admitting new jobs and WebSocket connections; return 503 for requests that reach the application while draining. Best-effort broadcast {"type":"SERVER_SHUTDOWN","ts_utc":"&lt;RFC 3339 UTC&gt;"} to connected WebSocket clients, then close them; slow clients must not block cleanup.
- Within a total 10-second monotonic deadline, drain or cancel probes, workers, and owned child processes, terminating and reaping children as needed. For interrupted keyed jobs, atomically persist FAILED with reason DAEMON_SHUTDOWN and update their idempotency responses. Commit completed transactions, roll back incomplete transactions, close SQLite connections and flush logs; never force-commit partial work. Log cleanup failures or deadline expiry and exit nonzero if cleanup cannot finish safely.
- After an ungraceful exit, SQLite performs normal WAL recovery; before admitting jobs, reconcile persisted RUNNING idempotency records to FAILED with reason DAEMON_RESTARTED. Raw ring-buffer samples not yet rolled up may be lost and are not fabricated on restart.

## 6. Probe Safety, Legal Constraints & Consent Guardrails (Module E)

Active censorship and throttling probes generate non-standard network traffic and are governed by strict technical and legal safeguards:

1. Disabled by Default & Explicit Informed Consent:
   - Module E is disabled on fresh installs. Enabling it in the UI requires explicit confirmation of the following disclaimer stored with a UTC timestamp in settings:

   > **Diagnostic Use Only & Jurisdiction Notice:** NetPulse Local's Active ISP Interference & Throttling Probe sends DNS, TLS SNI, and throughput test traffic to external servers to diagnose connection filtering or traffic shaping. Use this feature strictly on networks you own or have explicit authorization to audit. Automated censorship or protocol probing may be logged by your ISP and may be restricted by ISP Terms of Service or local regulations in certain jurisdictions.
   - Show the notice before first enablement or an attempt to run without current consent; do not preselect acceptance. Persist the exact notice version and acceptance UTC timestamp in settings. A changed notice version invalidates prior consent and requires explicit re-acceptance; unrelated application updates do not.
   - Settings display consent state and version and provide revocation. Revocation disables future manual and scheduled runs immediately, cancels an active Module E job using the bounded cleanup procedure, and retains existing results unless separately deleted by the user. An interrupted keyed job becomes FAILED with reason CONSENT_REVOKED. Check current consent on every run request, including idempotent replays, and before each scheduled run; reject without current consent with 403 CONSENT_REQUIRED.
2. User-Owned Watchlist & Target Allowlist Enforcement:
   - Users manage their own watchlist (max 10 domains per run).
   - Input validation strictly blocks raw IP addresses, RFC1918/link-local subnets, .gov/.mil/.int TLDs, and non-HTTPS ports outside standard diagnostic test ports (80, 443, 8080, 8443).
3. Rate Limits & Concurrency Caps:
   - Global Concurrency Cap: Maximum 1 active Module E probe job at any time (max_concurrent_jobs = 1).
   - Cooldowns: Manual /api/isp-probe/run enforces a 15-minute monotonic cooldown (900.0s); scheduled background runs are capped at a minimum interval of 6 hours.
   - Packet & Data Caps: Max 3 TLS ClientHello probes and 1 TCP traceroute (max_hops=15, 1 probe/hop) per domain.
4. Userspace VPN Isolation (wireproxy):
   - Differential VPN speed tests use a userspace WireGuard SOCKS5 proxy (wireproxy) bound to an ephemeral localhost port rather than modifying the host OS routing table (wg-quick). This prevents accidental system-wide routing leaks if the app exits mid-test and caps data transfer at 25.00 MB down / 10.00 MB up (automatically skipped on metered connections).

## 7. API Contract & OpenAPI 3.1 Schemas

All REST endpoints require X-NetPulse-Token: &lt;session_token&gt; and support X-Trace-Id: tr_<26-char ULID>. All numeric fields and timestamps conform strictly to Section 11 (Observability, Traceability & Time Semantics).

### 7.1 Enumerations

- FaultCode: LOCAL_WIFI_DROP | ROUTER_HANG | ISP_OUTAGE | WIFI_CONGESTION | ISP_CONGESTION | DNS_FAILURE | TRANSIENT_ANOMALY
- ConfidenceLevel: LOW | MEDIUM | HIGH
- SystemState: HEALTHY | SUSPECT | ACTIVE_FAULT | RECOVERING
- JobStatus: RUNNING | COMPLETED | FAILED | DEFERRED
- SignalCode: GATEWAY_OK | GATEWAY_TIMEOUT | GATEWAY_HIGH_RTT | ARP_STALE | EXT_ICMP_TIMEOUT | EXT_TCP443_TIMEOUT | EXT_HIGH_RTT_OR_LOSS | UPSTREAM_DELTA_FLAT | SYS_DNS_FAIL | DOH_CONTROL_OK | TRANSPORT_OK | WIFI_CONNECTED | WIFI_DISCONNECTED_OR_WEAK
- ErrorCode: UNAUTHORIZED | FORBIDDEN_ORIGIN | CONSENT_REQUIRED | INVALID_TARGET_DOMAIN | INVALID_PAYLOAD_PRECISION | INVALID_PAYLOAD_RANGE | JOB_ALREADY_RUNNING | PROBE_COOLDOWN_ACTIVE | INTERNAL_ERROR

### 7.2 Standard Error Envelope

All 4xx/5xx responses return application/json and include trace_id conforming to Section 11.1:

```json
{
  "error": {
    "code": "JOB_ALREADY_RUNNING",
    "message": "A speedtest job is currently in progress.",
    "details": {
      "active_run_id": "run_st_01JCD89X7K2M4N6P8Q0R2S4T6V",
      "started_at": "2026-11-11T15:30:00Z"
    },
    "trace_id": "tr_01JCD8A2B4C6D8E0F2G4H6J8K0"
  }
}
```

### 7.3 Trigger Endpoints & Persistent Idempotency Contract

POST /api/speedtest/run and POST /api/isp-probe/run accept an optional Idempotency-Key header (UUIDv4).
- Persistence Scope: Keys are scoped to (endpoint_path, idempotency_key). Atomically reserve a new key and the applicable concurrency slot, persisting job_status, cached HTTP status and response in SQLite before starting the job; competing requests for the same key must not launch duplicates. A crash between reservation and launch is reconciled as an interrupted job. Set expires_epoch initially to created_epoch + 900, but never expire RUNNING records; on a terminal transition reset it to that transition's UTC epoch + 900. Retain terminal records until expiry, then permit reuse. Atomically update job_status, status_code, response_json and expires_epoch together on completion or reconciliation.
- Interrupted In-Flight Jobs on Restart: Before accepting new jobs, reconcile each RUNNING key to FAILED with reason DAEMON_RESTARTED and a cached 200 response. Replays return that reconciled response, not the original 202. A new key may start a new job.
- Behavior Matrix:
   - New Key (System Idle): Inserts record with trace_id and run_id, starts job, returns 202 Accepted.
   - Replay of Existing Key: Subject to current authorization and consent, return the currently stored status and response without starting another job. RUNNING returns the original cached 202; terminal COMPLETED, FAILED or DEFERRED returns the stored 200 response with run_id, original trace_id, status and, for failures, reason. Repeated replays are identical until the job transitions or the terminal TTL expires.
   - New Key While Another Job Is RUNNING: Returns 409 Conflict with the standard error envelope containing active_run_id and the new request's trace_id.

POST /api/isp-probe/run

- Request Body:

```json
{
  "use_vpn_diff": false,
  "domains": ["cloudflare.com", "wikipedia.org"]
}
```

- Response (202 Accepted):

```json
{
  "run_id": "run_isp_01JCD8A2B4C6D8E0F2G4H6J8K0",
  "trace_id": "tr_01JCD8A2B4C6D8E0F2G4H6J8K0",
  "status": "RUNNING",
  "target_count": 2,
  "created_at": "2026-11-11T15:32:10Z"
}
```

### 7.4 Versioned Event & Corroborating Signals JSON Contract

The evidence_json column in anomaly_events and the corresponding API object adhere to a strict versioned schema (schema_version: 1) so downstream parsers, CSV exporters, and future UI upgrades remain backward-compatible:

```json
{
  "schema_version": 1,
  "signals": [
    {
      "code": "GATEWAY_OK",
      "observed_value": 3.1,
      "threshold": 15.0,
      "unit": "ms"
    },
    {
      "code": "EXT_ICMP_TIMEOUT",
      "observed_value": 100.0,
      "threshold": 80.0,
      "unit": "loss_pct"
    },
    {
      "code": "EXT_TCP443_TIMEOUT",
      "observed_value": 100.0,
      "threshold": 80.0,
      "unit": "loss_pct"
    }
  ]
}
```

### 7.5 Cursor-Paginated Events Endpoint (GET /api/events)

- Query Parameters: limit (1..200, default 50), cursor (opaque base64 string encoding ts_epoch:id), fault_code (optional FaultCode filter).
- Response (200 OK):

```json
{
  "items": [
    {
      "id": 1042,
      "fault_code": "ISP_OUTAGE",
      "confidence": "HIGH",
      "start_time": "2026-11-11T14:22:10Z",
      "end_time": "2026-11-11T14:22:28Z",
      "duration_ms": 18040,
      "duration_sec": 18,
      "evidence": {
        "schema_version": 1,
        "signals": [
          {"code": "GATEWAY_OK", "observed_value": 3.1, "threshold": 15.0, "unit": "ms"},
          {"code": "EXT_ICMP_TIMEOUT", "observed_value": 100.0, "threshold": 80.0, "unit": "loss_pct"},
          {"code": "EXT_TCP443_TIMEOUT", "observed_value": 100.0, "threshold": 80.0, "unit": "loss_pct"}
        ]
      },
      "summary": "Gateway RTT 3.1ms; 1.1.1.1 and 9.9.9.9 unreachable for 18s."
    }
  ],
  "pagination": {
    "limit": 50,
    "next_cursor": "MTczMTMzNDkzMDoxMDQy",
    "has_more": true
  }
}
```

### 7.6 Startup Capabilities Endpoint (GET /api/system/capabilities)

```json
{
  "os": "linux",
  "app_version": "2.4.0",
  "capabilities": {
    "icmp_mode": "ICMP_UNPRIVILEGED",
    "wifi_telemetry": "AVAILABLE",
    "raw_dpi_sniffing": "DEGRADED_TLS_FALLBACK",
    "speedtest_cli": "AVAILABLE",
    "vpn_diff_proxy": "UNAVAILABLE_NO_CONFIG"
  },
  "warnings": [
    "CAP_NET_RAW not granted; Module E using userspace TLS handshake fallback."
  ]
}
```

### 7.7 WebSocket Telemetry & Progress Stream (WS /ws/telemetry?token=&lt;session_token&gt;)

```json
{
  "type": "TELEMETRY_TICK",
  "ts_utc": "2026-11-11T15:35:01Z",
  "state": "HEALTHY",
  "active_fault": null,
  "metrics": {
    "gateway_ms": 2.9,
    "ext_primary_ms": 14.1,
    "ext_secondary_ms": 16.4,
    "dns_ms": 19.0,
    "loss_10s_pct": 0.0
  },
  "wifi": {
    "available": true,
    "connected": true,
    "ssid": "HomeFiber_5G",
    "bssid": "aa:bb:cc:dd:ee:01",
    "channel": 36,
    "rssi_dbm": -54,
    "rx_rate_mbps": 866
  }
}
```

Asynchronous job updates broadcast over the same socket include the originating trace_id and run_id:

```json
{
  "type": "JOB_PROGRESS",
  "ts_utc": "2026-11-11T15:35:04Z",
  "run_id": "run_isp_01JCD8A2B4C6D8E0F2G4H6J8K0",
  "trace_id": "tr_01JCD8A2B4C6D8E0F2G4H6J8K0",
  "status": "RUNNING",
  "progress_pct": 50.0
}
```

### 7.8 Telemetry History (GET /api/telemetry)

- Query parameters: from and to are RFC 3339 UTC timestamps at whole-second precision, defining [from, to); granularity is 1s, 1m or 1d (default 1s). If both timestamps are omitted, to is the current UTC time rounded down to a second and from is 15 minutes before to. Supplying only one timestamp, from >= to, a future to, unsupported granularity, or an invalid timestamp returns 422 INVALID_PAYLOAD_RANGE in the standard error envelope.
- Source and retention: 1s reads only the 3,600-sample in-memory ring (last hour); 1m reads ping_agg_1m and wifi_agg_1m (last 30 days); 1d reads ping_agg_daily (last 365 days). Reject a range whose from precedes the requested tier's retention boundary with 422 INVALID_PAYLOAD_RANGE; pruning, restarts or missing samples can still leave gaps within retention. Raw data is never reconstructed from aggregates.
- A point's timestamp is its sample time or UTC bucket start. Return points with timestamps in [from, to), ordered by timestamp ascending; for equal timestamps preserve acquisition order. Minute and day buckets are UTC-aligned; partial edge buckets are included only when their bucket start is in range, and their values describe the entire bucket. Never combine or re-aggregate buckets. Limit each response to 1,000 points; if more exist, return 422 INVALID_PAYLOAD_RANGE and require a narrower range or coarser granularity. An empty valid range returns 200 with items: [].
- Response shape: {"from":"&lt;UTC&gt;","to":"&lt;UTC&gt;","granularity":"1s|1m|1d","items":[...]}. Every item contains ts_utc, metrics and wifi. For 1s, metrics and wifi have the same field names and nullable unavailable values as the TELEMETRY_TICK in Section 7.7. For 1m, metrics contains gw_min_ms, gw_avg_ms, gw_p95_ms, ext_avg_ms, ext_p95_ms, dns_avg_ms and loss_pct; wifi is an array of all rows for that minute, each containing bssid, ssid, channel, sample_count, rssi_min_dbm, rssi_avg_dbm and rx_avg_mbps, ordered by BSSID. A missing ping row has metrics: null; a missing Wi-Fi row has wifi: []. For 1d, metrics contains gw_avg_ms, ext_avg_ms, ext_p95_ms, loss_pct and total_outage_sec; wifi is null because there is no daily Wi-Fi tier. Missing measurements are null, not zero. All numeric values follow Section 11.3.

## 8. Database Schema (SQLite WAL)

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA auto_vacuum = INCREMENTAL;

CREATE TABLE IF NOT EXISTS ping_agg_1m (
    ts_minute INTEGER PRIMARY KEY,
    gw_min_ms REAL,
    gw_avg_ms REAL,
    gw_p95_ms REAL,
    ext_avg_ms REAL,
    ext_p95_ms REAL,
    dns_avg_ms REAL,
    loss_pct REAL
);

CREATE TABLE IF NOT EXISTS ping_agg_daily (
    ts_day INTEGER PRIMARY KEY,
    gw_avg_ms REAL,
    ext_avg_ms REAL,
    ext_p95_ms REAL,
    loss_pct REAL,
    total_outage_sec INTEGER
);

-- Composite PK (ts_minute, bssid) preserves distinct records if mesh roaming occurs mid-minute
CREATE TABLE IF NOT EXISTS wifi_agg_1m (
    ts_minute INTEGER NOT NULL,
    bssid TEXT NOT NULL,
    ssid TEXT,
    channel INTEGER,
    sample_count INTEGER NOT NULL,
    rssi_min_dbm INTEGER,
    rssi_avg_dbm INTEGER,
    rx_avg_mbps INTEGER,
    PRIMARY KEY (ts_minute, bssid)
);
CREATE INDEX idx_wifi_agg_ts ON wifi_agg_1m(ts_minute DESC);

CREATE TABLE IF NOT EXISTS speed_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    trace_id TEXT NOT NULL,
    ts_epoch INTEGER NOT NULL,
    download_mbps REAL,
    upload_mbps REAL,
    idle_ping_ms REAL,
    loaded_ping_ms REAL,
    jitter_ms REAL,
    server_name TEXT
);

CREATE TABLE IF NOT EXISTS anomaly_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_epoch INTEGER NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT,
    duration_ms INTEGER,
    duration_sec INTEGER,
    fault_code TEXT NOT NULL,
    confidence TEXT NOT NULL,
    evidence_json TEXT NOT NULL, -- Validated against schema_version: 1
    summary TEXT
);
CREATE INDEX idx_events_ts_id ON anomaly_events(ts_epoch DESC, id DESC);

CREATE TABLE IF NOT EXISTS isp_probe_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    ts_epoch INTEGER NOT NULL,
    target_domain TEXT NOT NULL,
    isp_dns_ip TEXT,
    doh_dns_ip TEXT,
    dns_status TEXT,
    tls_sni_status TEXT,
    unthrottled_mbps REAL,
    vpn_tunnel_mbps REAL,
    throttling_detected INTEGER
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    endpoint TEXT NOT NULL,
    idem_key TEXT NOT NULL,
    run_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    job_status TEXT NOT NULL CHECK (job_status IN ('RUNNING', 'COMPLETED', 'FAILED', 'DEFERRED')),
    status_code INTEGER NOT NULL,
    response_json TEXT NOT NULL,
    created_epoch INTEGER NOT NULL,
    expires_epoch INTEGER NOT NULL,
    PRIMARY KEY (endpoint, idem_key)
);
CREATE INDEX idx_idem_expires ON idempotency_keys(expires_epoch);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## 9. Packaging Security, Localhost Hardening & Update Policy (Phase 5)

### 9.1 Localhost Hardening & Anti-CSRF Controls

- Strict Loopback Bind: Uvicorn binds exclusively to 127.0.0.1 on a configurable local port (default 8080).
- Host & Origin Enforcement: Middleware rejects any request where Host is not 127.0.0.1:8080 or localhost:8080 (blocking DNS rebinding). All state-mutating POST/PUT/DELETE endpoints verify that Origin (when present) matches http://127.0.0.1:8080 and require a valid X-NetPulse-Token header.
- Per-Boot Cryptographic Token: Generated at daemon launch (secrets.token_urlsafe(32)) and saved with strict user-only permissions:
   - Linux/macOS: ~/.config/netpulse/session.token (0600)
   - Windows: %LOCALAPPDATA%\NetPulse\session.token (ACL restricted to current user SID)
- Valid Fragment Handoff URL: System tray launches the default browser to http://127.0.0&lt;session_token&gt; (e.g., http://127.0.0...). Frontend JS parses window.location.hash, stores the token in sessionStorage, and immediately clears the URL fragment via history.replaceState(null, "", "/") so the token never leaks via browser history or screenshots.

### 9.2 Least-Privilege Service Defaults

- Unprivileged Main Daemon: Installed startup services (systemd user unit, macOS LaunchAgent, or Windows Scheduled Task/Service running under LocalService or user context) run without administrative/root privileges by default.
- Isolated Privilege Elevation: Optional raw-packet features use narrow OS capabilities (CAP_NET_RAW on Linux or a dedicated, signed macOS SMJobBless helper) rather than running the web server or SQLite engine as root/SYSTEM.

### 9.3 Signed Artifacts, Channels & Rollback Watchdog

- Code Signing & Checksums:
   - Windows: Authenticode-signed .msi and binaries (signtool.exe + RFC 3161 timestamp).
   - macOS: Developer ID-signed and Apple-notarized .dmg / .app bundle.
   - Linux: GPG-signed .deb, .rpm, and AppImage packages published with SHA256SUMS.asc.
- Update Channels & Rollback Watchdog: Supports stable (default) and beta channels with offline Ed25519 manifest signing. A supervisor watchdog monitors updated binaries for 30 seconds post-restart; if 127.0.0.1:8080 fails to bind or /api/system/capabilities fails, the supervisor reverts to previous_bin and quarantines the failed release hash.

## 10. Phased Implementation Plan & Operational Acceptance Gates

Each phase requires passing automated QA verification gates before advancing to the next phase:

### Phase 1: Core Engine, State Machine & Persistence

- Scope and execution order: localhost security, ULID/clock utilities, SQLite and rollups, persistent idempotency, graceful shutdown, Module A FSM, then QA gates. Implement the job runner as a deterministic test double in Phase 1; real speedtest and ISP endpoints arrive in Phases 3 and 4.
- Pass/Fail Acceptance Gates:
   1. Fault Simulation Gate: Mock probe driver injects 2/5 ICMP timeouts (2s) → PASS if state enters SUSPECT and zero rows are written to anomaly_events. Injects 4/5 timeouts (5s) followed by 10/10 successes (10s) → PASS if exactly 1 ACTIVE_FAULT event is created with schema_version: 1 evidence and resolved after 10s.
   2. Idempotency & Restart Gate: Start a fake job with key K1, restart mid-run and replay K1 → PASS if reconciliation stores FAILED/DAEMON_RESTARTED and repeated replay returns the same 200 response without a duplicate job. Verify equivalent HTTP behavior for speedtest and ISP endpoints in Phases 3 and 4.
   3. Quota Pruning Gate: Seed netpulse.db to 460 MB with synthetic ping_agg_1m rows and trigger maintenance worker → PASS if DB prunes oldest rows and PRAGMA incremental_vacuum reduces file size below 430 MB in < 5 seconds without blocking concurrent API reads.
   4. Localhost Security Gate: Send POST /api/speedtest/run with valid token but Origin: https://evil.example or Host: evil.local:8080 → PASS if rejected with 403 Forbidden.
   5. Trace Propagation Gate: Inject request with valid X-Trace-Id and trigger async job → PASS if identical trace_id appears in request logs, error envelope (if forced error), DB job row, and job lifecycle events.
   6. Monotonic Duration Gate: Simulate wall-clock jump (+/- 5 minutes) during active probe window → PASS if cooldown, debounce, and duration behavior remains correct and no negative or incorrect durations are emitted.
   7. Shutdown & Recovery Gate: Stop with an active job, a WebSocket client and SQLite writes → PASS if shutdown completes within 10 seconds, reachable clients receive SERVER_SHUTDOWN, children are reaped, and restart reopens the database. Repeat with forced termination → PASS if WAL recovery succeeds and RUNNING keys reconcile to FAILED without duplicate jobs.

### Phase 2: Cross-Platform Capabilities & Wi-Fi Parsers

- Scope: /api/system/capabilities self-check, OS Wi-Fi scrapers (netsh, wdutil/system_profiler, nmcli/iw), composite (ts_minute, bssid) aggregation, and ARP/TCP unprivileged fallbacks.
- Pass/Fail Acceptance Gates:
   1. Degraded-Mode Startup Gate: Launch daemon inside a restricted container/sandbox lacking CAP_NET_RAW and without wireless interfaces → PASS if daemon starts cleanly (exit code 0), /api/system/capabilities reports icmp_fallback_tcp_arp and wifi_metrics_unavailable, and gateway latency uses ARP/UDP fallback without false 100% loss.
   2. Mid-Minute Roaming Gate: Feed two Wi-Fi samples within the same ts_minute with different BSSID values → PASS if two rows persist and their sample counts sum to two. Verify chart selection and roam markers in Phase 3.

### Phase 3: Speedtest, Bufferbloat & Backpressure UI

- Scope: Ookla Speedtest CLI integration, 2.00 Mbps idle-traffic deferral, concurrent loaded ping, telemetry history and CSV export, and Chart.js live dashboard with bounded WebSocket queues.
- Pass/Fail Acceptance Gates:
   1. WebSocket Backpressure Gate: Connect a simulated WebSocket client that stops reading frames (recv paused for 30 seconds) while the 1s probe loop runs → PASS if client queue caps at 10 frames (dropping oldest), collector loop jitter remains < 5.0 ms, and RSS memory growth stays < 2 MB.
   2. Idle Guardrail Gate: Generate 5.00 Mbps background download traffic and trigger a scheduled speed test → PASS if test transitions to DEFERRED without saturating user traffic.
   3. Precision Consistency Gate: Compare REST telemetry, WebSocket telemetry, and CSV export for the same sample window → PASS if units and decimal precision match policy exactly (ms 1dp, % 1dp, Mbps 2dp, RSSI/link integer).
   4. History & Export Gate: Verify defaults, all three tiers, 1,000-point limit, retention rejection, gaps, BSSID arrays, dominant-BSSID tie-breaking and roam markers, empty results and CSV headers/escaping against Sections 5.1, 7.8 and 11.5.
   5. Endpoint Restart Gate: Verify the speedtest endpoint follows the Phase 1 idempotency restart contract.

### Phase 4: Module E Safe ISP Probing

- Scope: Informed-consent workflow, domain allowlist validator, DoH vs. ISP DNS check, TLS SNI probe, monotonic rate limiter, and capped wireproxy VPN differential test.
- Pass/Fail Acceptance Gates:
   1. Consent & Allowlist Gate: Attempt POST /api/isp-probe/run before consent acceptance, or with 192.168.1.50 / agency.gov in domains → PASS if rejected with 403 CONSENT_REQUIRED and 422 INVALID_TARGET_DOMAIN.
   2. Cooldown & Concurrency Gate: Fire two concurrent POST /api/isp-probe/run requests with distinct keys, then retry immediately after completion → PASS if second concurrent call returns 409 Conflict and post-run call returns 429 PROBE_COOLDOWN_ACTIVE.
   3. Monotonic Cooldown Integrity Under Clock Step Gate: Complete a Module E probe run (15-minute cooldown active), advance the test harness wall clock forward by +2 hours, and immediately call POST /api/isp-probe/run → PASS if request is still rejected with 429 PROBE_COOLDOWN_ACTIVE.
   4. Consent Lifecycle & Restart Gate: Verify first-use notice, version-change re-acceptance, revocation during a run, retained prior results, scheduled-run blocking and real endpoint idempotency replay after restart.

### Phase 5: Signed Packaging & Update Supervisor

- Scope: System tray UI (pystray), least-privilege OS service definitions, signed release artifacts, and Ed25519-verified updater with 30s rollback watchdog.
- Pass/Fail Acceptance Gates:
   1. Corrupt Update Rollback Gate: Stage a signed test update binary engineered to crash on startup → PASS if supervisor detects health-check failure within 30 seconds, restores previous_bin, quarantines the bad version hash, and serves /api/system/capabilities cleanly.

## 11. Observability, Traceability & Time Semantics

### 11.1 Trace ID Contract

- Canonical Format: trace_id MUST match ^tr_[0-9A-HJKMNP-TV-Z]{26}$ (prefix + ULID).
Example: tr_01JCD8A2B4C6D8E0F2G4H6J8K0
- Inbound Handling:
   - If request header X-Trace-Id is present and valid, reuse it.
   - Otherwise generate a new trace_id at request admission and echo it in the X-Trace-Id response header.
- Propagation Requirements:
   - Include trace_id in all structured logs for that request/job (via contextvars.ContextVar).
   - Include trace_id in all error envelopes (4xx/5xx).
   - Include trace_id in async job progress/completion WebSocket events.
   - Persist trace_id on job records where applicable (speed_tests, isp_probe_results, idempotency_keys) for correlation.

### 11.2 Clock Source Rules

- UTC Wall Clock:
   - Use UTC wall-clock timestamps (datetime.now(timezone.utc)) for persisted/open API times: created_at, updated_at, start_time, end_time, ts_utc.
- Monotonic Clock:
   - Use monotonic time (time.monotonic()) for elapsed calculations only: probe timeouts, retry backoff, debounce windows, cooldown timers, run durations.
- Prohibited Pattern:
   - Do NOT compute elapsed duration from wall-clock subtraction.
   - Persist computed duration values from monotonic deltas (duration_ms internal; duration_sec API/DB where specified).
- Clock safety: Compare wall-clock progress with monotonic progress; log a WARNING on a backward wall-clock step greater than 5 seconds, without dropping samples or changing elapsed timers. Preserve actual UTC timestamps even if end_time precedes start_time, and warn consumers that timestamp order can differ from monotonic duration. If a monotonic reading regresses or a computed monotonic delta is negative, log CRITICAL, do not emit a negative or fabricated duration, stop accepting new work and fail safely through shutdown; do not reuse monotonic readings across process restarts.

### 11.3 Units, Precision & Rounding Policy

- Latency / jitter: milliseconds (ms), serialized as float to 1 decimal place (round(x, 1)).
- Packet loss / ratios: percent (%), serialized as float to 1 decimal place (round(x, 1)).
- Throughput: Mbps, serialized as float to 2 decimal places (round(x, 2)).
- RSSI: integer dBm (int).
- Link rate: integer Mbps (int).
- Timestamp format: RFC 3339 UTC (YYYY-MM-DDTHH:MM:SSZ).
- API Consistency:
   - REST payloads, WebSocket payloads, and CSV export MUST use the exact same unit and rounding policy.

### 11.4 Schema Enforcement

- OpenAPI Schemas: MUST declare numeric units in field descriptions, expected precision, and numeric bounds (e.g., non-negative latency 0.0..60000.0, packet loss 0.0..100.0, throughput 0.0..100000.0, RSSI -120..0).
- Validation Errors: Validation failures return the standard error envelope with code=INVALID_PAYLOAD_PRECISION or code=INVALID_PAYLOAD_RANGE alongside the request's trace_id.

### 11.5 CSV Export

- The dashboard exports the currently requested telemetry history range and granularity from Section 7.8, subject to the same retention and 1,000-point limit; it also offers export of the currently displayed events page, explicitly labeled as such. Export all BSSID rows, not only the dominant chart series.
- UTF-8 CSV uses CRLF records and RFC 4180 quoting. The first line is # NetPulse CSV schema_version=1, app_version=&lt;version&gt;, export_type=&lt;telemetry|events&gt;, followed by the column header. Null values are empty fields. Escape untrusted text that begins with =, +, -, @, tab or carriage return by prefixing an apostrophe to prevent spreadsheet formula execution; do not prefix numeric fields.
- Telemetry uses columns ts_utc, granularity, gw_min_ms, gw_avg_ms, gw_p95_ms, ext_avg_ms, ext_p95_ms, dns_avg_ms, loss_pct, total_outage_sec, gateway_ms, ext_primary_ms, ext_secondary_ms, dns_ms, loss_10s_pct, wifi_available, wifi_connected, ssid, bssid, channel, sample_count, rssi_dbm, rssi_min_dbm, rssi_avg_dbm, rx_rate_mbps, rx_avg_mbps. Emit one row per BSSID for 1m, repeating ping values; when no BSSID exists emit one row with empty Wi-Fi fields. For other granularities emit one row per point and leave inapplicable fields empty.
- Events use columns id, fault_code, confidence, start_time_utc, end_time_utc, duration_ms, duration_sec, evidence_json, summary. Encode evidence_json as a JSON string inside a CSV field. Apply Section 11.3 units and precision consistently with the corresponding REST and WebSocket values.
