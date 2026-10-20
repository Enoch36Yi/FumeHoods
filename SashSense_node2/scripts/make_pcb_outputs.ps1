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

# 3. Previews
$pv = 'outputs\previews'; New-Item -ItemType Directory -Force $pv | Out-Null
Run $kc @('pcb','render','--side','top','--width','2400','--height','2400','--quality','high','--background','opaque','--output',"$pv\Firefly_pcb2_3D_top_full.png",$pcbf)
Run $kc @('pcb','render','--side','bottom','--width','2400','--height','2400','--quality','high','--background','opaque','--output',"$pv\Firefly_pcb2_3D_bottom_full.png",$pcbf)
# camera pan calibrated to centre the populated region (x 27-190 mm, y 27-82 mm)
Run $kc @('pcb','render','--side','top','--width','2400','--height','900','--quality','high','--background','opaque','--zoom','6.5','--pan','4.35,-5.75,0','--output',"$pv\Firefly_pcb2_3D_top_populated.png",$pcbf)
Run $kc @('pcb','render','--side','bottom','--width','2400','--height','900','--quality','high','--background','opaque','--zoom','6.5','--pan','-4.3,-5.75,0','--output',"$pv\Firefly_pcb2_3D_bottom_populated.png",$pcbf)
Run $kc @('pcb','render','--width','2400','--height','1400','--quality','high','--background','opaque','--zoom','6','--pan','6.4,-3.2,0','--rotate','-35,0,20','--perspective','--output',"$pv\Firefly_pcb2_3D_iso_populated.png",$pcbf)
Run $kp @('scripts\render_copper.py','F',"$pv\Firefly_pcb2_copper_top.png")
Run $kp @('scripts\render_copper.py','B',"$pv\Firefly_pcb2_copper_bottom.png")
Run $kc @('pcb','export','pdf','--layers','F.Cu,B.Cu,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,F.Fab','--common-layers','Edge.Cuts','--mode-multipage','--include-border-title','--output','outputs\Firefly_pcb2_board_layers.pdf',$pcbf)

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
