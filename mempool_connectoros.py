#!/usr/bin/env python3
"""
MEMBRA ConnectorOS — PendingProofOS read-only endpoint sampler.

Purpose:
- List public / permissioned pending-state endpoint records.
- Probe REST endpoints.
- Subscribe to read-only WebSocket streams.
- Normalize observations into MEMBRA proof-ledger events.

Safety boundary:
- Read-only only.
- No private keys.
- No transaction submission.
- No bundle submission.
- No trading automation.

Install:
    pip install requests websockets

Examples:
    python mempool_connectoros.py --list
    python mempool_connectoros.py --probe-rest
    python mempool_connectoros.py --ws mempool_space_btc --seconds 20
    python mempool_connectoros.py --ws publicnode_eth --seconds 20
    python mempool_connectoros.py --ws solana_public_logs --seconds 20
    python mempool_connectoros.py --ws xrpl_transactions --seconds 20
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional
from urllib import request

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

try:
    import websockets
except Exception:  # pragma: no cover
    websockets = None


def now_ms() -> int:
    return int(time.time() * 1000)


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def payload_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def expand_env_placeholders(value: str) -> str:
    out = value
    for key, val in os.environ.items():
        out = out.replace("{ENV:" + key + "}", val)
    return out


def print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str), flush=True)


PROVENANCE_SCORE = {
    "self_hosted_full_node": 0.95,
    "self_hosted_validator_or_archival_node": 0.98,
    "dedicated_paid_rpc_or_grpc": 0.85,
    "paid_or_keyed_provider": 0.75,
    "public_free_rpc": 0.45,
    "public_provider": 0.45,
    "manual_pasted_sample": 0.20,
}

SETTLEMENT_SCORE = {
    "pending_seen": 0.35,
    "included_in_block": 0.75,
    "confirmed_depth_safe": 0.95,
    "dropped_or_replaced": 0.05,
}


def proof_confidence(provider_type: str, settlement_status: str = "pending_seen") -> float:
    return round(PROVENANCE_SCORE.get(provider_type, 0.30) * SETTLEMENT_SCORE.get(settlement_status, 0.20), 4)


def observation_id(obs: Dict[str, Any]) -> str:
    stable = {
        "source": obs.get("source"),
        "chain": obs.get("chain"),
        "network": obs.get("network"),
        "stream_type": obs.get("stream_type"),
        "endpoint": obs.get("endpoint"),
        "payload_hash": obs.get("payload_hash"),
    }
    return payload_hash(stable)[:24]


def normalize_observation(source: str, cfg: Dict[str, Any], stream_type: str, endpoint: str, payload: Any) -> Dict[str, Any]:
    obs = {
        "schema": "membra.pending_observation.v1",
        "source": source,
        "chain": cfg.get("chain", "unknown"),
        "network": cfg.get("network", "unknown"),
        "provider_provenance": cfg.get("provenance", "unknown"),
        "stream_type": stream_type,
        "endpoint": endpoint,
        "first_seen_at": now_iso(),
        "first_seen_ms": now_ms(),
        "payload_hash": payload_hash(payload),
        "payload": payload,
        "settlement_status": "pending_seen",
        "pending_seen": True,
        "included_in_block": False,
        "confirmation_depth": 0,
        "proof_confidence": proof_confidence(cfg.get("provenance", "unknown"), "pending_seen"),
        "note": "Pending observation proves this provider/node saw data; it does not prove settlement.",
    }
    obs["observation_id"] = observation_id(obs)
    return obs


ENDPOINTS: Dict[str, Dict[str, Any]] = {
    "mempool_space_btc": {
        "chain": "bitcoin",
        "network": "mainnet",
        "kind": "rest_and_websocket",
        "provenance": "public_provider",
        "rest_urls": [
            "https://mempool.space/api/mempool",
            "https://mempool.space/api/mempool/txids",
            "https://mempool.space/api/mempool/recent",
            "https://mempool.space/api/v1/fees/recommended",
            "https://mempool.space/api/v1/fees/mempool-blocks",
        ],
        "websocket": "wss://mempool.space/api/v1/ws",
        "ws_payload": {"action": "want", "data": ["blocks", "mempool-blocks", "stats"]},
    },
    "blockstream_btc": {
        "chain": "bitcoin",
        "network": "mainnet",
        "kind": "rest",
        "provenance": "public_provider",
        "rest_urls": [
            "https://blockstream.info/api/mempool",
            "https://blockstream.info/api/mempool/txids",
            "https://blockstream.info/api/mempool/recent",
            "https://blockstream.info/api/fee-estimates",
        ],
    },
    "publicnode_eth": {
        "chain": "ethereum",
        "network": "mainnet",
        "kind": "websocket_jsonrpc",
        "provenance": "public_free_rpc",
        "websocket": "wss://ethereum-rpc.publicnode.com",
        "ws_payload": {"jsonrpc": "2.0", "id": 1, "method": "eth_subscribe", "params": ["newPendingTransactions"]},
    },
    "publicnode_base": {
        "chain": "base",
        "network": "mainnet",
        "kind": "websocket_jsonrpc",
        "provenance": "public_free_rpc",
        "websocket": "wss://base-rpc.publicnode.com",
        "ws_payload": {"jsonrpc": "2.0", "id": 1, "method": "eth_subscribe", "params": ["newPendingTransactions"]},
    },
    "polygon_drpc_public": {
        "chain": "polygon",
        "network": "mainnet",
        "kind": "websocket_jsonrpc",
        "provenance": "public_free_rpc",
        "websocket": "wss://polygon.drpc.org",
        "ws_payload": {"jsonrpc": "2.0", "id": 1, "method": "eth_subscribe", "params": ["newPendingTransactions"]},
    },
    "alchemy_eth": {
        "chain": "ethereum",
        "network": "mainnet",
        "kind": "websocket_jsonrpc",
        "provenance": "paid_or_keyed_provider",
        "requires_env": ["ALCHEMY_API_KEY"],
        "websocket": "wss://eth-mainnet.g.alchemy.com/v2/{ENV:ALCHEMY_API_KEY}",
        "ws_payload": {"jsonrpc": "2.0", "id": 1, "method": "eth_subscribe", "params": ["newPendingTransactions"]},
        "ws_payload_full_body": {"jsonrpc": "2.0", "id": 2, "method": "eth_subscribe", "params": ["alchemy_pendingTransactions", {"hashesOnly": False}]},
    },
    "infura_eth": {
        "chain": "ethereum",
        "network": "mainnet",
        "kind": "websocket_jsonrpc",
        "provenance": "paid_or_keyed_provider",
        "requires_env": ["INFURA_API_KEY"],
        "websocket": "wss://mainnet.infura.io/ws/v3/{ENV:INFURA_API_KEY}",
        "ws_payload": {"jsonrpc": "2.0", "id": 1, "method": "eth_subscribe", "params": ["newPendingTransactions"]},
    },
    "solana_public_logs": {
        "chain": "solana",
        "network": "mainnet-beta",
        "kind": "websocket_jsonrpc",
        "provenance": "public_free_rpc",
        "websocket": "wss://api.mainnet-beta.solana.com",
        "ws_payload": {"jsonrpc": "2.0", "id": 1, "method": "logsSubscribe", "params": ["all", {"commitment": "processed"}]},
    },
    "helius_solana_logs": {
        "chain": "solana",
        "network": "mainnet-beta",
        "kind": "websocket_jsonrpc",
        "provenance": "paid_or_keyed_provider",
        "requires_env": ["HELIUS_API_KEY"],
        "websocket": "wss://mainnet.helius-rpc.com/?api-key={ENV:HELIUS_API_KEY}",
        "ws_payload": {"jsonrpc": "2.0", "id": 1, "method": "logsSubscribe", "params": ["all", {"commitment": "processed"}]},
    },
    "xrpl_transactions": {
        "chain": "xrpl",
        "network": "mainnet",
        "kind": "websocket_json",
        "provenance": "public_free_rpc",
        "websocket": "wss://xrplcluster.com",
        "alternate_websockets": ["wss://s1.ripple.com", "wss://s2.ripple.com"],
        "ws_payload": {"id": "membra-xrpl-transactions", "command": "subscribe", "streams": ["transactions"]},
    },
    "toncenter_pending": {
        "chain": "ton",
        "network": "mainnet",
        "kind": "rest",
        "provenance": "public_provider",
        "rest_urls": ["https://toncenter.com/api/v3/pendingTransactions"],
    },
    "bitcoin_core_local": {
        "chain": "bitcoin",
        "network": "local_node",
        "kind": "json_rpc_http",
        "provenance": "self_hosted_full_node",
        "rpc_url": "http://127.0.0.1:8332",
        "rpc_methods": [
            {"method": "getrawmempool", "params": [True]},
            {"method": "getmempoolinfo", "params": []},
        ],
    },
    "geth_local": {
        "chain": "ethereum",
        "network": "local_node",
        "kind": "websocket_and_http_jsonrpc",
        "provenance": "self_hosted_full_node",
        "websocket": "ws://127.0.0.1:8546",
        "http": "http://127.0.0.1:8545",
        "ws_payload": {"jsonrpc": "2.0", "id": 1, "method": "eth_subscribe", "params": ["newPendingTransactions"]},
        "http_payloads": [
            {"jsonrpc": "2.0", "id": 1, "method": "txpool_status", "params": []},
            {"jsonrpc": "2.0", "id": 2, "method": "txpool_content", "params": []},
        ],
    },
}


def list_endpoints() -> None:
    print_json([
        {
            "name": name,
            "chain": cfg.get("chain"),
            "network": cfg.get("network"),
            "kind": cfg.get("kind"),
            "provenance": cfg.get("provenance"),
            "requires_env": cfg.get("requires_env", []),
            "websocket": cfg.get("websocket"),
            "rest_urls": cfg.get("rest_urls"),
            "http": cfg.get("http") or cfg.get("rpc_url"),
        }
        for name, cfg in ENDPOINTS.items()
    ])


def http_get_json(url: str, timeout: int = 15) -> Any:
    if requests is not None:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "MEMBRA-ConnectorOS/0.2"})
        r.raise_for_status()
        try:
            return r.json()
        except Exception:
            return r.text[:2000]
    req = request.Request(url, headers={"User-Agent": "MEMBRA-ConnectorOS/0.2"})
    with request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body)
        except Exception:
            return body[:2000]


def probe_rest(limit_per_source: int = 3) -> None:
    observations: List[Any] = []
    for name, cfg in ENDPOINTS.items():
        for url in (cfg.get("rest_urls") or [])[:limit_per_source]:
            url = expand_env_placeholders(url)
            try:
                data = http_get_json(url)
                observations.append(normalize_observation(name, cfg, "rest_probe", url, data))
            except Exception as exc:
                observations.append({"source": name, "endpoint": url, "error": str(exc)})
    print_json(observations)


async def ws_subscribe(name: str, seconds: int = 30, full_body: bool = False) -> None:
    if websockets is None:
        raise SystemExit("Missing dependency: pip install websockets")
    cfg = ENDPOINTS.get(name)
    if not cfg:
        raise SystemExit(f"Unknown endpoint: {name}")
    missing = [x for x in cfg.get("requires_env", []) if not os.getenv(x)]
    if missing:
        raise SystemExit(f"Missing required environment variables for {name}: {missing}")
    ws_url = expand_env_placeholders(cfg.get("websocket", ""))
    payload = cfg.get("ws_payload_full_body") if full_body and cfg.get("ws_payload_full_body") else cfg.get("ws_payload")
    if not ws_url or not payload:
        raise SystemExit(f"Endpoint {name} is missing websocket or payload")
    print_json({"event": "connecting", "name": name, "websocket": ws_url, "payload": payload, "seconds": seconds})
    start = time.time()
    async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20, max_size=20_000_000) as ws:
        await ws.send(json.dumps(payload))
        while time.time() - start < seconds:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=max(1, seconds))
            except asyncio.TimeoutError:
                break
            try:
                payload_obj = json.loads(msg)
            except Exception:
                payload_obj = msg
            print_json(normalize_observation(name, cfg, "websocket_subscription", ws_url, payload_obj))
            print("---", flush=True)


def export_registry() -> None:
    print_json({
        "schema": "membra.connectoros.pending_registry.v1",
        "generated_at": now_iso(),
        "provenance_scoring": PROVENANCE_SCORE,
        "settlement_status_weights": SETTLEMENT_SCORE,
        "chain_semantics": {
            "bitcoin": "mempool observation then mined then confirmed",
            "ethereum_evm": "provider or local pending pool then block inclusion",
            "solana": "processed stream observation; no single global public mempool",
            "ton": "pending transaction/message then finality",
            "xrpl": "transaction stream then validated ledger",
        },
        "endpoints": ENDPOINTS,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description="MEMBRA ConnectorOS read-only pending-state endpoint sampler")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--names", action="store_true")
    parser.add_argument("--registry", action="store_true")
    parser.add_argument("--probe-rest", action="store_true")
    parser.add_argument("--limit-per-source", type=int, default=3)
    parser.add_argument("--ws", default="")
    parser.add_argument("--full-body", action="store_true")
    parser.add_argument("--seconds", type=int, default=30)
    args = parser.parse_args()

    if args.list:
        list_endpoints(); return
    if args.names:
        print("\n".join(ENDPOINTS.keys())); return
    if args.registry:
        export_registry(); return
    if args.probe_rest:
        probe_rest(args.limit_per_source); return
    if args.ws:
        asyncio.run(ws_subscribe(args.ws, args.seconds, args.full_body)); return
    parser.print_help()


if __name__ == "__main__":
    main()
