/*
 * QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
 * Lean Algorithmic Trading Engine v2.0. Copyright 2014 QuantConnect Corporation.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
*/

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Linq;
using QuantConnect.Data.Market;
using QuantConnect.Data.UniverseSelection;
using QuantConnect.Indicators;

namespace QuantConnect.Algorithm.CSharp
{
    /// <summary>
    /// In this algorithm we demonstrate how to perform some technical analysis as
    /// part of your coarse fundamental universe selection
    /// </summary>
    /// <meta name="tag" content="using data" />
    /// <meta name="tag" content="indicators" />
    /// <meta name="tag" content="universes" />
    /// <meta name="tag" content="coarse universes" />
    public class EmaTogetherUniverseSelectionAlgorithm : QCAlgorithm
    {

        private readonly ConcurrentDictionary<Symbol, SelectionData> averages = new ConcurrentDictionary<Symbol, SelectionData>();

        public override void Initialize()
        {
            SetStartDate(2020, 9, 1);
            SetEndDate(2020, 11, 23);
            SetCash(100000);
            AddUniverse(CoarseSelectionFilter);
            UniverseSettings.Resolution = Resolution.Daily;
        }

        public IEnumerable<Symbol> CoarseSelectionFilter(IEnumerable<CoarseFundamental> universe)
        {
            decimal tolerence = 1.01m;
            var selected = new List<Symbol>();
            universe = universe
                .Where(x => x.Price > 10)
                .OrderByDescending(x => x.DollarVolume).Take(100);

            foreach (var coarse in universe)
            {
                var symbol = coarse.Symbol;

                if (!averages.ContainsKey(symbol))
                {
                    //1. Call history to get an array of 200 days of history data
                    var history = History(symbol, 50, Resolution.Daily);

                    //2. Adjust SelectionData to pass in the history result
                    averages[symbol] = new SelectionData(history);
                }

                averages[symbol].Update(Time, coarse.AdjustedPrice);

                if (averages[symbol].IsReady() && averages[symbol].FiveMA > averages[symbol].TenMA && 
                    averages[symbol].TenMA > averages[symbol].TwentyMA  && averages[symbol].TwentyMA > averages[symbol].ThirtyMA )
                {
                    decimal gap = averages[symbol].FiveMA / averages[symbol].ThirtyMA;
                    if (gap<tolerence)
                    {
                        selected.Add(coarse.Symbol);
                    }
                    //Log("averages[symbol].FiveMA / averages[symbol].ThirtyMA: " + averages[symbol].FiveMA / averages[symbol].ThirtyMA);
                    
                }
            }

            return selected.Take(10);
        }
        public override void OnSecuritiesChanged(SecurityChanges changes)
        {
            foreach (var security in changes.RemovedSecurities)
            {
                if (security.Invested)
                {
                    Liquidate(security.Symbol);
                }
            }

            foreach (var security in changes.AddedSecurities)
            {
                SetHoldings(security.Symbol, 0.10m);
            }
        }


    }


    public partial class SelectionData
    {
        public readonly ExponentialMovingAverage FiveMA;
        public readonly ExponentialMovingAverage TenMA;
        public readonly ExponentialMovingAverage TwentyMA;
        public readonly ExponentialMovingAverage ThirtyMA;
        public bool IsReady() { return TenMA.IsReady && TwentyMA.IsReady && ThirtyMA.IsReady && FiveMA.IsReady; }

        //3. Update the constructor to accept an IEnumerable<TradeBar> history parameter
        public SelectionData(IEnumerable<TradeBar> history)
        {
            FiveMA = new ExponentialMovingAverage(5);
            TenMA = new ExponentialMovingAverage(10);
            TwentyMA = new ExponentialMovingAverage(20);
            ThirtyMA = new ExponentialMovingAverage(30);

            //4. Loop over history data and pass the bar.EndTime and bar.Close values to Update()
            foreach (var bar in history)
            {
                Update(bar.EndTime, bar.Close);
            }
        }

        public bool Update(DateTime time, decimal value)
        {
            FiveMA.Update(time, value);
            TenMA.Update(time, value);
            TwentyMA.Update(time, value);
            ThirtyMA.Update(time, value);
            
            return IsReady();
        }
    }



}