$url = "https://the.earth.li/~sgtatham/putty/latest/w64/plink.exe"
$output = "d:\Projects\CGCPT-Server\plink.exe"
Write-Output "Downloading plink.exe..."
Invoke-WebRequest -Uri $url -OutFile $output -UseBasicParsing
Write-Output "Download complete. File size: $((Get-Item $output).Length) bytes"
