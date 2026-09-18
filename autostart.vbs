Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

If Not FSO.FolderExists("D:\BG\logs") Then
    FSO.CreateFolder("D:\BG\logs")
End If

' WshShell.CurrentDirectory = "D:\BG\backgrinding_production\ProcessClass"
' WshShell.Run "cmd /c ""D:\BG\env\Scripts\python.exe -u getip.py""", 1, True

WScript.Sleep 1000

' WshShell.CurrentDirectory = "D:\BG\backgrinding_production"
' WshShell.Run "cmd /c ""D:\BG\env\Scripts\pythonw.exe -u StateMachine.py >> D:\BG\logs\worker_stdout.log 2>&1""", 0, False

' WScript.Sleep 1000

' WshShell.CurrentDirectory = "D:\BG\backgrinding_production"
' WshShell.Run "cmd /c ""D:\BG\env\Scripts\pythonw.exe -u agent.py >> D:\BG\logs\agent.log 2>&1""", 0, False

Set WshShell = Nothing
Set FSO = Nothing