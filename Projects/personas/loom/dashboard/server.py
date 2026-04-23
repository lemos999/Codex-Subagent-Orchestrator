# -*- coding: utf-8 -*-
"""
PersonaBrain Multi-Persona Dashboard Server.

WebSocket으로 매 틱의 뉴런 상태를 브라우저에 전송.
MultiTickEngine을 직접 사용하여 로직 중복 제거.
"""
from __future__ import annotations
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import websockets
import numpy as np
from core.multi_tick_engine import MultiTickEngine


class DashboardServer:
    """멀티 페르소나 대시보드 서버."""

    def __init__(self):
        self.engine = MultiTickEngine()
        self.clients: set = set()
        self.running = False
        self.tick_interval = 0.5  # 0.5초마다 1틱

    def get_neuron_snapshot(self, pid: str) -> dict | None:
        """특정 페르소나의 뉴런 스냅샷."""
        brain = self.engine.brains.get(pid)
        if brain is None:
            return None
        snn = brain.snn
        n = snn.n

        voltages = snn.v.tolist()
        spikes = snn.spikes.astype(int).tolist()
        exc_count = snn.n_exc
        exc_spikes = int(snn.spikes[:exc_count].sum())
        inh_spikes = int(snn.spikes[exc_count:].sum())

        # 상위 연결 (처음 200뉴런, 각 3개)
        connections = []
        w = snn.weights
        for i in range(min(n, 200)):
            row = w[i]
            nonzero = np.nonzero(row)[0]
            if len(nonzero) > 0:
                top_k = min(3, len(nonzero))
                top_idx = nonzero[np.argsort(np.abs(row[nonzero]))[-top_k:]]
                for j in top_idx:
                    connections.append({"from": int(j), "to": i, "weight": round(float(row[j]), 4)})

        refractory = snn.refractory.tolist()

        return {
            "n_neurons": n,
            "n_exc": exc_count,
            "n_inh": snn.n_inh,
            "voltages": voltages[:200],
            "spikes": spikes[:200],
            "refractory": refractory[:200],
            "exc_spikes": exc_spikes,
            "inh_spikes": inh_spikes,
            "firing_rate": round(float(snn.spikes.sum()) / n, 4),
            "connections": connections[:500],
            "threshold": round(float(snn.threshold[0]), 4),
        }

    def tick(self) -> dict:
        """1틱 실행 + 전체 상태 반환."""
        result = self.engine.tick()

        # 뉴런 스냅샷 추가 (각 페르소나)
        for pid, pdata in result["personas"].items():
            if not pdata.get("sleeping", False):
                pdata["neurons"] = self.get_neuron_snapshot(pid)
            else:
                pdata["neurons"] = None

            # 페르소나 메타 정보
            persona = self.engine.personas[pid]
            pdata["meta"] = {
                "region": persona.region,
                "territory": persona.territory,
                "class": persona.persona_class,
            }

            # tone 정보
            inner = self.engine.inners[pid]
            pdata["tone"] = inner.tone_dict()
            pdata["oyok"] = {
                name: round(float(val), 3)
                for name, val in zip(inner.OYOK_NAMES, inner.oyok)
            }

        # 비밀 상태 (공개된 것만)
        secrets_info = {}
        for pid, sec in self.engine.secrets.items():
            name = self.engine.personas[pid].name
            knowers = [self.engine.personas[k].name for k in sec.known_by if k != pid]
            if knowers:
                secrets_info[name] = {
                    "tag": sec.content_tag,
                    "known_by": knowers,
                    "revealed_tick": sec.revealed_tick,
                }
        result["secrets"] = secrets_info

        return result

    async def broadcast(self, data: dict):
        if not self.clients:
            return
        msg = json.dumps(data, ensure_ascii=False, default=str)
        dead = set()
        for c in list(self.clients):
            try:
                await c.send(msg)
            except Exception:
                dead.add(c)
        self.clients -= dead

    async def handler(self, ws):
        self.clients.add(ws)
        try:
            async for msg in ws:
                cmd = json.loads(msg)
                if cmd.get("type") == "set_speed":
                    self.tick_interval = max(0.1, cmd.get("interval", 0.5))
                elif cmd.get("type") == "pause":
                    self.running = False
                elif cmd.get("type") == "resume":
                    self.running = True
                elif cmd.get("type") == "step":
                    state = self.tick()
                    await ws.send(json.dumps(state, ensure_ascii=False, default=str))
        finally:
            self.clients.discard(ws)

    async def tick_loop(self):
        self.running = True
        while True:
            if self.running:
                state = self.tick()
                await self.broadcast(state)
            await asyncio.sleep(self.tick_interval)

    async def start(self, host="localhost", port=8765):
        print(f"PersonaBrain Multi-Persona Dashboard: ws://{host}:{port}")
        print(f"Personas: {', '.join(p.name for p in self.engine.personas.values())}")
        print(f"Open dashboard/index.html in browser")
        async with websockets.serve(self.handler, host, port):
            await self.tick_loop()


if __name__ == "__main__":
    server = DashboardServer()
    asyncio.run(server.start())
