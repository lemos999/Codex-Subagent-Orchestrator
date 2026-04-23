# -*- coding: utf-8 -*-
"""Capture one tick from the dashboard server and inspect data shape."""
import asyncio, json, sys
sys.path.insert(0, '.')

async def main():
    import websockets
    async with websockets.connect('ws://localhost:8765') as ws:
        for i in range(3):
            msg = await ws.recv()
            d = json.loads(msg)
            print(f"\n=== Tick {d.get('tick')} ===")
            for pid, p in d.get('personas', {}).items():
                neurons = p.get('neurons')
                has_neurons = neurons is not None
                n_voltages = len(neurons.get('voltages', [])) if has_neurons else 0
                n_spikes = sum(neurons.get('spikes', [])) if has_neurons else 0
                n_conns = len(neurons.get('connections', [])) if has_neurons else 0
                print(f"  {p.get('name','?'):12s} sleeping={p.get('sleeping')} "
                      f"neurons={'YES' if has_neurons else 'NO'} "
                      f"voltages={n_voltages} spikes={n_spikes} conns={n_conns}")
            print(f"  interactions: {len(d.get('interactions', []))}")
            print(f"  relationships: {list(d.get('relationships', {}).keys())}")

asyncio.run(main())
