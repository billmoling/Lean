using QuantConnect.Algorithm.Framework.Alphas;
using QuantConnect.Algorithm.Framework.Execution;
using QuantConnect.Algorithm.Framework.Portfolio;
using QuantConnect.Algorithm.Framework.Risk;
using QuantConnect.Algorithm.Framework.Selection;
using QuantConnect.Data;
using QuantConnect.Data.UniverseSelection;
using QuantConnect.Indicators;
using QuantConnect.Securities.Equity;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace QuantConnect.Algorithm.CSharp
{
    public class BasicXTSEStockAlgorithm:QCAlgorithm
    {
        private Equity xic;
        private Momentum _xicmomentum;
        private Dictionary<Symbol, Momentum> mom;
        private ExponentialMovingAverage xic_50;
        private ExponentialMovingAverage xic_200;
        public override void Initialize()
        {
            SetStartDate(2010, 1, 4);
            SetEndDate(2019, 12, 31);
            SetAccountCurrency("CAD");
            SetCash(100000);
            List<Symbol> stock_list=PrepUniverse();

            xic=AddEquity("XIC.TO", Resolution.Daily, Market.XTSE);
            UniverseSettings.Resolution = Resolution.Daily;

            mom = new Dictionary<Symbol, Momentum>();


            _xicmomentum = MOM(xic.Symbol, 126, Resolution.Daily);
            xic_50 = EMA(xic.Symbol, 50);
            xic_200 = EMA(xic.Symbol, 200);

            foreach (var item in stock_list)
            {
                AddEquity(item.Value, Resolution.Daily, Market.XTSE);
                mom.Add(item, MOM(item, 126, Resolution.Daily));
            }

            SetWarmUp(180);
            
            Schedule.On(DateRules.MonthEnd(xic.Symbol), TimeRules.AfterMarketOpen(xic.Symbol), () =>
            {
                Rebalance();
            });

        }

        private void Rebalance()
        {

            bool trend = false;
            if (xic_50<xic_200)
            {
                trend = true;
            }
            
            
            
            
            //2. Sort the list of dictionaries by indicator in descending order
            var selected_stock = mom.OrderByDescending(kvp => kvp.Value).Take(5).ToList();
            //Insight.Price(ordered.First().Key, TimeSpan.FromDays(1), InsightDirection.Up)



            foreach (var item in ActiveSecurities.Where(c => c.Value.Invested == true))
            {
                if (!selected_stock.Exists(c => c.Key == item.Key))
                {
                    Liquidate(item.Key);
                }
            }


            foreach (var item in selected_stock)
            {
                if (!ActiveSecurities[item.Key].Invested & trend)
                {

                    var quantity = CalculateOrderQuantity(item.Key, 0.15);

                    var purchase = MarketOrder(item.Key, quantity);
                    StopMarketOrder(item.Key, quantity, purchase.AverageFillPrice*0.88m);
                }
            }
        }
        

        public override void OnData(Slice data)
        {

            if (IsWarmingUp)
                return;

        }
        

        
        public List<Symbol> PrepUniverse()
        {
            /*
            string stock_str = @"RY,TD,ENB,CNR,BNS,SHOP,TRP,BCE,ABX,ATD-B,BMO,BAM-A,CP,CM,
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
            */

            string stock_str = @"RY,TD,ENB,CNR,BNS,SHOP,TRP,BCE,ABX,ATD-B,BMO,BAM-A,CP,CM,
                            SU,MFC,WCN,T,NTR,SLF,FNV,CSU,FTS,CNQ,RCI-B,GIB-A,NA,IFC,WPM,QSR,
                            TRI,BIP-UN,MRU,PPL,AEM,EMA,OTEX,POW,MG,L,FFH,DOL,KL,SJRB,AQN,SAP,H";

            //string stock_str = @"RY,TD,ENB,CNR,BNS,SHOP,TRP,BCE,EMA";

            List<Symbol> symbols = new List<Symbol>();
            foreach (var item in stock_str.Replace("\r", "").Replace("\n", "").Split(','))
            {
                var ticker = item.Trim() + ".TO";
                symbols.Add(QuantConnect.Symbol.Create(ticker, SecurityType.Equity, Market.XTSE));
            }
            return symbols;
            
        }


    }

}
