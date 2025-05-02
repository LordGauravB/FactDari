Set WshShell = CreateObject("WScript.Shell")

' Wait for 2 minutes (120,000 milliseconds)
WScript.Sleep 120000

' Get the script's folder path
Set fso = CreateObject("Scripting.FileSystemObject")
scriptFolder = fso.GetParentFolderName(WScript.ScriptFullName)

' Run the batch file from the util folder
WshShell.Run Chr(34) & scriptFolder & "\Facts_Generator_BAT.bat" & Chr(34), 0, False

Set WshShell = Nothing
Set fso = Nothing