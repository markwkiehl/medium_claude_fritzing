param([string]$Out, [string]$Keys = "", [int]$Wait = 3)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$ws = New-Object -ComObject WScript.Shell
$null = $ws.AppActivate("Fritzing")
Start-Sleep -Milliseconds 800
if ($Keys -ne "") { $ws.SendKeys($Keys); Start-Sleep -Seconds $Wait }
$b = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
(Get-Process Fritzing -ErrorAction SilentlyContinue | Select-Object -First 1).MainWindowTitle
