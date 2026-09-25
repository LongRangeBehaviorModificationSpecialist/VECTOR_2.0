@echo off
rem Start VECTOR so other devices can reach it -- double-click this file.
rem
rem The same launcher as "Start VECTOR.bat", started with --lan. VECTOR
rem then listens on the network rather than on this machine alone, so a
rem tablet or a second laptop on the same network can open it: the
rem address is printed in this window when it starts.
rem
rem Traffic is unencrypted HTTP. Use this only on a network you control,
rem and use "Start VECTOR.bat" the rest of the time -- with that one, the
rem port is not on the network at all.

call "%~dp0Start VECTOR.bat" --lan %*
