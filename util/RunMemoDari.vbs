Option Explicit

' Declare and create WScript Shell object
Dim WshShell
Set WshShell = CreateObject("WScript.Shell")

' Wait for 2 minutes (120 seconds = 120000 milliseconds)
WScript.Sleep 120000

' Run the Python script using the full path to Python and the script
' Format: "PythonPath" "ScriptPath"
WshShell.Run """C:\Program Files\Python312\python.exe"" ""Extact File Path\memodari.py""", 0, False

' Clean up
Set WshShell = Nothing