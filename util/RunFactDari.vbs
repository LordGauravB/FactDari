Option Explicit

' Declare and create WScript Shell object
Dim WshShell
Set WshShell = CreateObject("WScript.Shell")

' Set the project working directory
WshShell.CurrentDirectory = "C:\Users\gaura\OneDrive\PC-Desktop\GitHubDesktop\FactDari"

' Wait for 2 minutes after startup
WScript.Sleep 120000

' Run the Python script using the FactDari virtual environment Python
WshShell.Run """C:\Users\gaura\OneDrive\PC-Desktop\GitHubDesktop\FactDari\FactDari-venv\Scripts\python.exe"" ""C:\Users\gaura\OneDrive\PC-Desktop\GitHubDesktop\FactDari\factdari.py""", 0, False

' Clean up
Set WshShell = Nothing