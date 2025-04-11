Set WshShell = CreateObject("WScript.Shell")

' Wait for 2 minutes (120,000 milliseconds)
WScript.Sleep 120000

' Run the batch file
WshShell.Run Chr(34) & "C:\Users\gaura\OneDrive\PC-Desktop\PythonRunningApps\RandomFactsGenerator\Facts_Generator_BAT.bat" & Chr(34), 0, False

Set WshShell = Nothing
