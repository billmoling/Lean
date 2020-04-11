using QuantConnect.Data;
using QuantConnect.Indicators;
using QuantConnect.Securities.Equity;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace QuantConnect.Algorithm.CSharp
{
    public class CanadaSingleSockMomentumAlgo : QCAlgorithm
    {
        private Equity stock;
        private Momentum mom;
        public override void Initialize()
        {
            SetStartDate(2010, 1, 4);
            SetEndDate(2019, 12, 31);
            SetAccountCurrency("CAD");
            SetCash(100000);

            UniverseSettings.Resolution = Resolution.Daily;

            stock = AddEquity("EMA.TO", Resolution.Daily, Market.XTSE);

            mom = MOM(stock.Symbol, 126, Resolution.Daily);
            SetWarmUp(180);

            Schedule.On(DateRules.MonthEnd(stock.Symbol), TimeRules.AfterMarketOpen(stock.Symbol), () =>
            {
                Rebalance();
            });

        }

        private void Rebalance()
        {
            if (mom > 0)
            {
                var quantity = CalculateOrderQuantity(stock.Symbol, 0.8);

                var purchase = MarketOrder(stock.Symbol, quantity);
                StopMarketOrder(stock.Symbol, quantity, purchase.AverageFillPrice * 0.88m);
            }
            else
            {
                Liquidate(stock.Symbol);
            }
        }

        public override void OnData(Slice data)
        {

            if (IsWarmingUp)
                return;

            


        }
    }
}
