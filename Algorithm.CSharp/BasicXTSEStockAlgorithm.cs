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
        private Equity xbb;
        private Dictionary<Symbol, MomentumPercent> mom;
        private ExponentialMovingAverage xic_50;
        private ExponentialMovingAverage xic_200;
        private Dictionary<Symbol, decimal> broughtStock;
        public override void Initialize()
        {
            






            SetStartDate(2010, 1, 4);
            SetEndDate(2019, 12, 31);
            SetAccountCurrency("CAD");
            SetCash(100000);
            List<Symbol> stock_list=PrepUniverse();


            UniverseSettings.Resolution = Resolution.Daily;

            mom = new Dictionary<Symbol, MomentumPercent>();
            broughtStock = new Dictionary<Symbol, decimal>();

            xic =AddEquity("SPY", Resolution.Daily, Market.XTSE);
            SetBenchmark(xic.Symbol);
            xbb=AddEquity("XBB.TO", Resolution.Daily, Market.XTSE);
            xic_50 = EMA(xic.Symbol, 50);
            xic_200 = EMA(xic.Symbol, 200);

            foreach (var item in stock_list)
            {
                AddEquity(item.Value, Resolution.Daily, Market.XTSE);
                mom.Add(item, MOMP(item, 126, Resolution.Daily));
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
            if (xic_50 > xic_200)
            {
                trend = true;
            }
            
            var long_stock = mom.OrderByDescending(kvp => kvp.Value).Take(5).ToList();

            foreach (var item in ActiveSecurities.Where(c => c.Value.Invested == true))
            {
                if (!long_stock.Exists(c => c.Key == item.Key))
                {
                    Liquidate(item.Key);

                    /*
                     * try to micro manage to keep the momentun run, but it is not good enough.
                     * the monthly reblance looks good enough
                    if (broughtStock[item.Key] - mom[item.Key].ToString().ToDecimal() > 5)
                    {
                        broughtStock.Remove(item.Key);
                        Liquidate(item.Key);
                    }
                    */
                    
                }
            }


            foreach (var item in long_stock)
            {
                if (!ActiveSecurities[item.Key].Invested & trend)
                {
                    //Liquidate(xbb.Symbol);
                    var quantity = CalculateOrderQuantity(item.Key, 0.15);

                    var purchase = MarketOrder(item.Key, quantity);
                    StopMarketOrder(item.Key, quantity, purchase.AverageFillPrice*0.88m);

                    
                    //broughtStock.Add(item.Key, item.Value.ToString().ToDecimal());

                }
            }
            /*
            if (!trend)
            {
                var quantity = CalculateOrderQuantity(xbb.Symbol, 0.5);
                MarketOrder(xbb.Symbol, quantity);
            }
            */
            

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
                            TRI,BIP-UN,MRU,PPL,AEM,EMA,OTEX,POW,MG,L,FFH,DOL,SJRB,AQN,SAP,H";
            //KL

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
