Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\BG"
WshShell.Run "D:\BG\.venv\Scripts\pythonw.exe D:\BG\app_gui.py", 0, False
Set WshShell = Nothing