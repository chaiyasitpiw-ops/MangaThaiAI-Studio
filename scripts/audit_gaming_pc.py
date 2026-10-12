#!/usr/bin/env python3
"""
MangaThaiAI-Studio: Gaming PC Hardware Audit (Python Version)
Checks OS, CPU, RAM, Disk, GPU/VRAM, CUDA, PyTorch, and Network.
"""

import os
import platform
import shutil
import subprocess
import sys


def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_os():
    print_header("1. OS & Platform")
    print(f"OS Platform : {platform.system()} {platform.release()} ({platform.version()})")
    print(f"Architecture: {platform.machine()} / {platform.architecture()[0]}")
    print(f"Processor   : {platform.processor()}")


def check_memory_and_disk():
    print_header("2. Memory & Disk Space")
    try:
        import psutil
        vm = psutil.virtual_memory()
        print(f"RAM Total   : {vm.total / (1024**3):.2f} GB")
        print(f"RAM Avail   : {vm.available / (1024**3):.2f} GB")
        print("\nDisks:")
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                print(f"  {part.device} [{part.fstype}] Total: {usage.total / (1024**3):.2f} GB | Free: {usage.free / (1024**3):.2f} GB")
            except PermissionError:
                continue
    except ImportError:
        print("Note: psutil is not installed. To see RAM/disk details, run 'pip install psutil' or use the PowerShell script.")


def check_gpu():
    print_header("3. NVIDIA GPU & Drivers")
    smi = shutil.which("nvidia-smi")
    if smi:
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,name,driver_version,memory.total,memory.free", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                check=True,
            )
            print("Detected GPU(s):")
            for line in res.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                print(f"  GPU #{parts[0]}: {parts[1]} | Driver: {parts[2]} | Total VRAM: {parts[3]} | Free: {parts[4]}")
        except Exception as e:
            print(f"Error querying nvidia-smi: {e}")
    else:
        print("nvidia-smi executable not found in PATH.")


def check_pytorch():
    print_header("4. Python & PyTorch / CUDA")
    print(f"Python Executable : {sys.executable}")
    print(f"Python Version    : {sys.version.split()[0]}")
    try:
        import torch
        print(f"PyTorch Version   : {torch.__version__}")
        print(f"CUDA Available    : {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"Device Count      : {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(i)
                print(f"  Device {i}       : {props.name}")
                print(f"  Total VRAM      : {props.total_memory / (1024**3):.2f} GB")
                print(f"  Compute Cap     : {props.major}.{props.minor}")
            print(f"Torch CUDA Version: {torch.version.cuda}")
        else:
            print("CUDA is NOT enabled in current PyTorch build.")
    except ImportError:
        print("PyTorch is not installed in current Python environment.")


if __name__ == "__main__":
    check_os()
    check_memory_and_disk()
    check_gpu()
    check_pytorch()
    print_header("Audit Finished")
