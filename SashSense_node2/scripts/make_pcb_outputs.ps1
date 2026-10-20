# Verify Firefly_pcb2 and regenerate its review/manufacturing outputs from the saved native files.
# Run from SashSense_Reconstruction in PowerShell. Does not rebuild the board (see layout_pcb.py).
$ErrorActionPreference = 'Stop'
$kroot = if ($env:KICAD_ROOT) { $env:KICAD_ROOT } else { 'C:\Program Files\KiCad\10.0' }
$kc = Join-Path $kroot 'bin\kicad-cli.exe'; $kp = Join-Path $kroot 'bin\python.exe'
$pcbf = 'Firefly_pcb2.kicad_pcb'; $schf = 'Firefly_pcb2.kicad_sch'
function Run($exe, [string[]]$a) { & $exe @a; if ($LASTEXITCODE -ne 0) { throw "$exe $($a -join ' ') failed ($LASTEXITCODE)" } }

# 1. Schematic: netlist, ERC (all severities), independent schematic checks
Run $kc @('sch','export','netlist','--format','kicadxml','--output','reports\netlist.xml',$schf)
Run $kc @('sch','erc','--format','json','--severity-all','--output','reports\erc.json',$schf)
Run $kc @('sch','erc','--format','report','--severity-all','--output','reports\erc.rpt',$schf)
Run $kp @('scripts\verify_schematic.py')

# 2. Board: refill zones, native DRC with schematic parity (saved fill), independent board checks
Run $kc @('pcb','drc','--schematic-parity','--refill-zones','--save-board','--severity-all','--format','json','--units','mm','--output','reports\drc.json',$pcbf)
Run $kc @('pcb','drc','--schematic-parity','--severity-all','--format','report','--units','mm','--output','reports\drc.rpt',$pcbf)
Run $kp @('scripts\verify_pcb.py')
Run $kc @('pcb','export','stats','--output','reports\board_stats.txt',$pcbf)

# 3. Previews and plots
$pv = 'outputs\previews'; New-Item -ItemType Directory -Force $pv | Out-Null
Run $kc @('pcb','render','--side','top','--width','2400','--height','1000','--quality','high','--background','opaque','--zoom','2.3','--output',"$pv\Firefly_pcb2_3D_top.png",$pcbf)
Run $kc @('pcb','render','--side','bottom','--width','2400','--height','1000','--quality','high','--background','opaque','--zoom','2.3','--output',"$pv\Firefly_pcb2_3D_bottom.png",$pcbf)
Run $kc @('pcb','render','--width','2400','--height','1400','--quality','high','--background','opaque','--zoom','1.4','--rotate','-35,0,20','--perspective','--output',"$pv\Firefly_pcb2_3D_iso.png",$pcbf)
$o = (Get-Content 'scripts\cad_common.py' | Select-String 'OUTLINE_MM = \((.*)\)').Matches[0].Groups[1].Value -split ',\s*'
$region = @("$([double]$o[0]-1)", "$([double]$o[1]-1)", "$([double]$o[2]+1)", "$([double]$o[3]+1)", '14')
Run $kp (@('scripts\render_copper.py','F',"$pv\Firefly_pcb2_copper_top.png") + $region)
Run $kp (@('scripts\render_copper.py','B',"$pv\Firefly_pcb2_copper_bottom.png") + $region)
Run $kc @('pcb','export','pdf','--layers','F.Cu,B.Cu,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,F.Fab','--common-layers','Edge.Cuts','--mode-multipage','--include-border-title','--output','outputs\Firefly_pcb2_board_layers.pdf',$pcbf)
Run $kc @('sch','export','pdf','--output','outputs\Firefly_pcb2_schematic.pdf',$schf)
# Schematic PNG: SVG export rasterised by a local headless Edge/Chrome with a throw-away profile.
$svgdir = Join-Path $env:TEMP 'firefly_pcb2_sch_svg'; New-Item -ItemType Directory -Force $svgdir | Out-Null
Run $kc @('sch','export','svg','--output',$svgdir,$schf)
$browser = @("${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe", "$env:ProgramFiles\Google\Chrome\Application\chrome.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($browser) {
    $svg = (Get-ChildItem $svgdir -Filter *.svg | Select-Object -First 1).FullName
    $png = Join-Path (Resolve-Path 'outputs').Path 'Firefly_pcb2_schematic.png'
    & $browser --headless=new --disable-gpu --hide-scrollbars "--user-data-dir=$svgdir\profile" --force-device-scale-factor=3 --window-size=1588,1123 --default-background-color=FFFFFFFF "--screenshot=$png" ([uri]$svg).AbsoluteUri | Out-Null
    Start-Sleep -Seconds 2
} else { Write-Warning 'No Edge/Chrome found; outputs\Firefly_pcb2_schematic.png not refreshed.' }

# 4. Manufacturing review package (P2 provisional; not released for fabrication)
$m = 'outputs\manufacturing_P2_PROVISIONAL'
foreach ($d in 'gerbers','drill','assembly','netlist','3d') { New-Item -ItemType Directory -Force "$m\$d" | Out-Null }
Get-ChildItem "$m\gerbers","$m\drill" -File -ErrorAction SilentlyContinue | Remove-Item -Force
Run $kc @('pcb','export','gerbers','--layers','F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts','--subtract-soldermask','--use-drill-file-origin','--check-zones','--output',"$m\gerbers",$pcbf)
Run $kc @('pcb','export','drill','--format','excellon','--drill-origin','plot','--excellon-units','mm','--excellon-separate-th','--generate-map','--map-format','pdf','--generate-report','--report-path',"$m\drill\Firefly_pcb2_drill_report.txt",'--output',"$m\drill",$pcbf)
Run $kc @('pcb','export','pos','--side','front','--format','csv','--units','mm','--use-drill-file-origin','--exclude-dnp','--output',"$m\assembly\Firefly_pcb2_CPL_top.csv",$pcbf)
Run $kc @('sch','export','bom','--fields','Reference,Value,Manufacturer,MPN,Footprint,${QUANTITY}','--labels','Reference,Value,Manufacturer,MPN,Footprint,Qty','--group-by','Value,Manufacturer,MPN,Footprint','--output',"$m\assembly\Firefly_pcb2_BOM.csv",$schf)
Run $kc @('pcb','export','pdf','--layers','F.Fab,F.Silkscreen,Edge.Cuts','--mode-single','--include-border-title','--output',"$m\assembly\Firefly_pcb2_assembly_top.pdf",$pcbf)
Run $kc @('pcb','export','ipcd356','--output',"$m\netlist\Firefly_pcb2.ipc",$pcbf)
Run $kc @('pcb','export','step','--drill-origin','--subst-models','--force','--output',"$m\3d\Firefly_pcb2.step",$pcbf)
Run $kp @('scripts\verify_outputs.py')
Write-Host 'Firefly_pcb2 verification and outputs complete.'
