
$runmode=$args[0]

#$oldfileName="BasicXTSEStockAlgorithm"
#$sourceCode="C:\Coding\QuantConnectLean\Lean\Algorithm.CSharp\$oldfileName.cs"

$oldfileName="BasicAlphaStreamTSEAlgorithm"
$sourceCode="C:\Coding\QuantConnectLean\Lean\Algorithm.Python\$oldfileName.py"


cd C:\Coding\QuantConnectLean\Lean\Launcher\bin\Debug

$DateStamp = get-date -uformat "%Y-%m-%d-%H-%M"

$newFolderName="$oldfileName-$DateStamp"



function RunDataDownload {
    C:\Coding\QuantConnectLean\Lean\Quant.XTSE.DataPrep\bin\Debug\Quant.XTSE.DataPrep.exe
}

#$fileObj = get-item $fileName
#$nameOnly = $fileObj.Name.Replace( $fileObj.Extension,'')
#$extOnly = $fileObj.extension
function CreateResultFolder {
    New-Item -Path "C:\Coding\QuantConnectLean\Result\$newFolderName" -ItemType directory 
}

function RunBackTest {
    .\QuantConnect.Lean.Launcher.exe > "$oldfileName-output.txt"
    
    Copy-Item -Path ".\$oldfileName-output.txt"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
}


function RunTearReport{

    if ($runmode -eq "Report") {
        Copy-Item -Path ".\customize-output.txt"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    }

    #for reporting generation
    Copy-Item -Path ".\$oldfileName.json"  -Destination "C:\Coding\QuantConnectLean\Lean\Report\bin\Debug\$oldfileName.json"
    Copy-Item -Path ".\$oldfileName-order-events.json"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path "$sourceCode"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"

    cd C:\Coding\QuantConnectLean\Lean\Report\bin\Debug
    .\QuantConnect.Report.exe --backtest-data-source-file "$oldfileName.json" --report-destination "$oldfileName.html"
    Copy-Item -Path ".\$oldfileName.html"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"

    Copy-Item -Path ".\monthly-returns.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\cumulative-return.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\annual-returns.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\returns-per-trade.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\drawdowns.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\asset-allocation-backtest.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\USHousingBubble(2003).png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\September11,2001Attacks.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\GlobalFinancialCrisis.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\DotComBubble.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\USDowngradeEuropeanDebtCrisis.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\FukushimaMeltdown.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\FlashCrash.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\MarketSell-Off2015.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\EuropeanDebtCrisisOct2014.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\ECBIREvent2012.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\Recovery.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
    Copy-Item -Path ".\NewNormal.png"  -Destination "C:\Coding\QuantConnectLean\Result\$newFolderName"
}

if ($runmode -eq "Full") {
    CreateResultFolder
    RunBackTest
    RunTearReport
}

if ($runmode -eq "Report") {
    CreateResultFolder
    RunTearReport
}

if ($runmode -eq "Data") {
    RunDataDownload
}





