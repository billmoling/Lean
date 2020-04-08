using QuantConnect.Algorithm.Framework.Alphas;
using QuantConnect.Algorithm.Framework.Execution;
using QuantConnect.Algorithm.Framework.Portfolio;
using QuantConnect.Algorithm.Framework.Risk;
using QuantConnect.Algorithm.Framework.Selection;
using QuantConnect.Data;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace QuantConnect.Algorithm.CSharp
{
    public class BasicXTSEStockAlgorithm:QCAlgorithm
    {
        public override void Initialize()
        {
            UniverseSettings.Resolution = Resolution.Daily;

            SetStartDate(2019, 1, 4);
            SetEndDate(2019, 12, 31);
            SetAccountCurrency("CAD");
            SetCash(10000);
            //SetWarmUp(100);

            //var iwm = AddEquity("EMA.TO", Resolution.Daily);
            var iwm = AddEquity("EMA.TO",Resolution.Daily,"XTSE");

            
            var slices = History(5);
            foreach (var s in slices)
            {
                Debug($"{s.Time} EMA: {s.Bars["EMA.TO"].Close}");
            }
            if (iwm.HasData)
            {
                Debug("EMA.TO Load Success");

            }
        }
        public override void OnData(Slice data)
        {
            // Place an order and print the average fill price
            if (!Portfolio.Invested)
            {
                MarketOrder("EMA.TO", 100);
                Debug(Portfolio["EMA.TO"].AveragePrice);
            }
        }
    }
}
