import sys
import platform

print(sys.abiflags)
print(sys.byteorder)
print(sys.platform)

print(platform.architecture())
print(platform.platform())
print(platform.python_implementation())
print(platform.uname())
