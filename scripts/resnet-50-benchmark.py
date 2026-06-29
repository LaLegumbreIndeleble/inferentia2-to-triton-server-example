#!/usr/bin/env python3
"""
Compiling and Benchmarking ResNet50 on Inf2 / Trn1
- Compiles ResNet50 for batch sizes 1-10 using torch_neuronx
- Benchmarks each compiled model and reports throughput + latency
"""

import os
import time
import urllib
import concurrent.futures

import numpy as np
import torch
import torch_neuronx
from PIL import Image
from torchvision import models
from torchvision.transforms import functional

# ============================================================
# Helpers
# ============================================================


def get_image(batch_size=1, image_shape=(224, 224)):
    filename = "000000039769.jpg"
    if not os.path.exists(filename):
        url = "http://images.cocodataset.org/val2017/000000039769.jpg"
        print(f"Downloading sample image...")
        urllib.request.urlretrieve(url, filename)
    image = Image.open(filename).convert("RGB")
    image = functional.resize(image, image_shape)
    image = functional.to_tensor(image)
    image = torch.unsqueeze(image, 0)
    image = torch.repeat_interleave(image, batch_size, 0)
    return (image,)


def display(metrics):
    pad = max(map(len, metrics)) + 1
    for key, value in metrics.items():
        parts = key.split("_")
        parts = list(map(str.title, parts))
        title = " ".join(parts) + ":"
        if isinstance(value, float):
            value = f"{value:0.3f}"
        print(f"{title :<{pad}} {value}")


def benchmark(filename, example, n_models=2, n_threads=2, batches_per_thread=1000):
    # Load models
    loaded_models = [torch.jit.load(filename) for _ in range(n_models)]

    # Warmup
    print("  Warming up...")
    for _ in range(8):
        for model in loaded_models:
            model(*example)

    latencies = []

    def task(model):
        for _ in range(batches_per_thread):
            start = time.time()
            model(*example)
            finish = time.time()
            latencies.append((finish - start) * 1000)

    # Run benchmark
    begin = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as pool:
        for i in range(n_threads):
            pool.submit(task, loaded_models[i % len(loaded_models)])
    end = time.time()

    # Compute metrics
    percentiles = {}
    for boundary in [50, 95, 99]:
        percentiles[f"latency_p{boundary}"] = np.percentile(latencies, boundary)

    duration = end - begin
    batch_size = next(t.shape[0] for t in example if t.shape[0] > 0)
    inferences = len(latencies) * batch_size
    throughput = inferences / duration

    metrics = {
        "filename": str(filename),
        "batch_size": batch_size,
        "batches": len(latencies),
        "inferences": inferences,
        "threads": n_threads,
        "models": n_models,
        "duration": duration,
        "throughput": throughput,
        **percentiles,
    }
    display(metrics)
    return metrics


# ============================================================
# Step 1: Compile ResNet50 for batch sizes 1-10
# ============================================================

BATCH_SIZES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

print("=" * 50)
print("Step 1: Compiling ResNet50 for each batch size")
print("=" * 50)

for batch_size in BATCH_SIZES:
    filename = f"model_batch_size_{batch_size}.pt"
    if os.path.exists(filename):
        print(f"  Batch {batch_size}: already compiled, skipping.")
        continue
    print(f"  Compiling batch size {batch_size}...")
    model = models.resnet50(pretrained=True)
    model.eval()
    example = get_image(batch_size=batch_size)
    model_neuron = torch_neuronx.trace(model, example)
    torch.jit.save(model_neuron, filename)
    print(f"  Saved → {filename}")

# ============================================================
# Step 2: Benchmark each compiled model
# ============================================================

print()
print("=" * 50)
print("Step 2: Benchmarking each batch size")
print("=" * 50)

all_metrics = []
for batch_size in BATCH_SIZES:
    print("-" * 50)
    filename = f"model_batch_size_{batch_size}.pt"
    example = get_image(batch_size=batch_size)
    metrics = benchmark(filename, example)
    all_metrics.append(metrics)
    print()

# ============================================================
# Step 3: Summary — best batch size by throughput
# ============================================================

print("=" * 50)
print("Summary")
print("=" * 50)
best = max(all_metrics, key=lambda m: m["throughput"])
print(
    f"  Best throughput:  batch_size={best['batch_size']} "
    f"→ {best['throughput']:.0f} inferences/sec "
    f"(P50={best['latency_p50']:.1f}ms, P99={best['latency_p99']:.1f}ms)"
)
