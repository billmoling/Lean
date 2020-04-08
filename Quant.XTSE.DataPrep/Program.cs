using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using QuantConnect;
using QuantConnect.Data.Market;
using QuantConnect.ToolBox.YahooDownloader;

namespace Quant.XTSE.DataPrep
{
    class Program
    {
        static void Main(string[] args)
        {
            string ETF_str = @"RY,TD,ENB,CNR,BNS,SHOP,TRP,BCE,ABX,ATD-B,BMO,BAM-A,CP,CM,
                            SU,MFC,WCN,T,NTR,SLF,FNV,CSU,FTS,CNQ,RCI-B,GIB-A,NA,IFC,WPM,QSR,
                            TRI,BIP-UN,MRU,PPL,AEM,EMA,OTEX,POW,MG,L,FFH,DOL,KL,SJRB,AQN,SAP,H,BEP-UN,
                            CAR-UN,WN,K,BHC,TSGI,GWO,CCL-B,QBR-B,AP-UN,X,RBA,TECK-B,WSP,REI.UN,TIH,FM,CTC-A,CAD,
                            NPI,EMP-A,IAG,CAE,WEED,ONEX,BTO,CCO,PAAS,AC,DSG,CU,BPY-UN,STN,EFN,FSV,YRI,IMO,PKI,GIL,
                            SNC,ALA,IPL,LUN,CHP-UN,GRT-UN,CIX,BYD,ACO-X,CVE,KXS,CPX,BB,KEY,AGI,TFII,HR-UN,NG,INE,FTT,
                            SRU-UN,GEI,FCR-UN,CCA,TOU,PBH,TA,PRMW,NVU-UN,SSRM,BBU-UN,CIGI,MSI,CSH-UN,MFI,IGM,SJ,
                            BLX,CG,ENGH,BLDP,PXT,CWB,GOOS,IIP-UN,FR,RNW,PSK,KMP-UN,EDV,OR,IMG,CUF-UN,ACB,PVG,AIF,
                            CRON,ARX,SPB,NWH-UN,GC,ELD,CJT,WFT,ASR,WPK,DIR-UN,MX,LB,LNR,IVN,SSL,ATA,MIC,TXG,RCH,APHA,
                            CRR-UN,NWC,D-UN,LIF,HSE,REAL,ATZ,SMU-UN,WDO,JWEL,DOO,TCN,AX-UN,BBD.B,SMF,TCL-A,BEI-UN,HCG,
                            CAS,ECN,OGC,LSPD,NFI,MAG,SIA,RUS,CRT-UN,BAD,SVM,OSB,ARE,CGX,USD,GUD,VET,SEA,EQB,ERO,HBM,
                            CPG,ITP,WTE,EIF,MRE,CLS,CJRB,EFX,WCP,EXE,ERF,PSI,CHE.UN,MEG,CFP,VII,IFP,CHR,MTY,MTL,TOY,
                            ZZZ,AFN,AD,HEXO,FRU,FEC,BTE,SES,SCL";
            DateTime fromDate = new DateTime(2000, 1, 4);
            DateTime toDate = DateTime.Now.AddDays(-1);

            List<string> tickers=new List<string>();
            foreach (var item in ETF_str.Replace("\r", "").Replace("\n", "").Split(','))
            {
                tickers.Add(item.Trim() + ".TO");
            }

            YahooDownloaderProgram.YahooDownloader(tickers, "Daily", fromDate, toDate);
        }
    }
}
