# =====================================================================
# MangaThaiAI-Studio: Gaming PC Hardware Audit Script (Read-Only)
# Run this on your Gaming PC to inspect GPU, VRAM, Network & Environment
# =====================================================================

Write-Host "===========================================================" -ForegroundColor Green
Write-Host "  MangaThaiAI-Studio: Gaming PC Hardware Audit" -ForegroundColor Green
Write-Host "===========================================================" -ForegroundColor Green

Write-Host "`n[1/6] Operating System & Hardware Summary" -ForegroundColor Cyan
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture | Format-List
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors | Format-List
Get-CimInstance Win32_ComputerSystem | Select-Object @{Name="TotalRAM_GB";Expression={[math]::Round($_.TotalPhysicalMemory/1GB, 2)}} | Format-List

Write-Host "`n[2/6] Disk Storage (Drives)" -ForegroundColor Cyan
Get-PSDrive -PSProvider FileSystem | Select-Object Root, @{Name="UsedGB";Expression={[math]::Round(($_.Used)/1GB,2)}}, @{Name="FreeGB";Expression={[math]::Round(($_.Free)/1GB,2)}}, @{Name="TotalGB";Expression={[math]::Round(($_.Used+$_.Free)/1GB,2)}} | Format-Table

Write-Host "`n[3/6] NVIDIA GPU, Driver & VRAM" -ForegroundColor Cyan
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    nvidia-smi
} else {
    Write-Host "Warning: nvidia-smi command not found. Reading video controller information:" -ForegroundColor Yellow
    Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, @{Name="AdapterRAM_MB";Expression={[math]::Round($_.AdapterRAM/1MB,2)}} | Format-List
}

Write-Host "`n[4/6] CUDA Toolkit & Environment" -ForegroundColor Cyan
if (Get-Command nvcc -ErrorAction SilentlyContinue) {
    nvcc --version
} else {
    Write-Host "nvcc not found in PATH." -ForegroundColor Yellow
}
Get-ChildItem env:CUDA* -ErrorAction SilentlyContinue | Format-Table Name, Value

Write-Host "`n[5/6] Python, PyTorch & CUDA Detection" -ForegroundColor Cyan
if (Get-Command python -ErrorAction SilentlyContinue) {
    python --version
    python -c @"
import sys
try:
    import torch
    print(f'PyTorch Version  : {torch.__version__}')
    print(f'CUDA Available   : {torch.cuda.is_available()}')
    if torch.cuda.is_available():
        print(f'Device Count     : {torch.cuda.device_count()}')
        print(f'Device Name      : {torch.cuda.get_device_name(0)}')
        vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f'VRAM Total       : {vram:.2f} GB')
        print(f'CUDA Version     : {torch.version.cuda}')
        print(f'cuDNN Version    : {torch.backends.cudnn.version()}')
    else:
        print('CUDA is NOT available in this PyTorch installation.')
except ImportError:
    print('PyTorch is not installed in current Python environment.')
"@
} else {
    Write-Host "Python executable not found in PATH." -ForegroundColor Red
}

Write-Host "`n[6/6] LAN Network & OpenSSH Status" -ForegroundColor Cyan
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" } | Select-Object InterfaceAlias, IPAddress, PrefixLength | Format-Table
Get-Service sshd -ErrorAction SilentlyContinue | Select-Object Name, Status, StartType | Format-Table

Write-Host "===========================================================" -ForegroundColor Green
Write-Host "  Audit Completed. Please copy this output to your Laptop." -ForegroundColor Green
Write-Host "===========================================================" -ForegroundColor Green
