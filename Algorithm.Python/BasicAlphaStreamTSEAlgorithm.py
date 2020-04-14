# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean Algorithmic Trading Engine v2.0. Copyright 2014 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from clr import AddReference
AddReference("System")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Common")
AddReference("QuantConnect.Algorithm.Framework")


import numpy as np

from System import *
from QuantConnect import *
from QuantConnect.Orders import *
from QuantConnect.Algorithm import *
from QuantConnect.Algorithm.Framework import *
from QuantConnect.Algorithm.Framework.Alphas import *
from QuantConnect.Algorithm.Framework.Execution import *
from QuantConnect.Algorithm.Framework.Portfolio import *
from QuantConnect.Algorithm.Framework.Risk import *
from QuantConnect.Algorithm.Framework.Selection import *

from itertools import groupby
from datetime import datetime, timedelta
from pytz import utc
UTCMIN = datetime.min.replace(tzinfo=utc)


import pandas as pd
from scipy.optimize import minimize


class MomentumAlphaCreationModel(AlphaModel):


    def __init__(self, resolution = Resolution.Daily):
        
        self.insightExpiry = Time.Multiply(Extensions.ToTimeSpan(resolution), 0.25) # insight duration
        self.insightDirection = InsightDirection.Up # insight direction
        self.long = [] # list to store securities to consider
        self.short=[]
        self.mom = []
        self.insights = [] # list to store the new insights to be created
        
    def Update(self, algorithm, data):

        ordered = sorted(self.mom, key=lambda kv: kv["indicator"].Current.Value, reverse=True)
        self.long=ordered[:5]
        
        #return Insight.Group([Insight.Price(ordered[0]['symbol'], timedelta(1), InsightDirection.Up), Insight.Price(ordered[1]['symbol'], timedelta(1), InsightDirection.Flat) ])
        #self.insights.append(Insight.Price(symbol, timedelta(1), InsightDirection.Flat))
        self.investedSecurity=list(filter(lambda x: x.Value.Invested == True, algorithm.ActiveSecurities))
        
        for item in self.investedSecurity:
            if not any(x for x in self.long if x['symbol'].Value==item.Key.Value):
                self.insights.append(Insight.Price(item.Key, self.insightExpiry, InsightDirection.Flat))



        # loop through securities and generate insights
        for security in self.long:
            # check if there's new data for the security or we're already invested
            # if there's no new data but we're invested, we keep updating the insight since we don't really need to place orders
            if not algorithm.Portfolio[security['symbol']].Invested:
                self.insights.append(Insight.Price(security['symbol'], self.insightExpiry, self.insightDirection))
            #else:
                #algorithm.Log('(Alpha) excluding this security due to missing data: ' + str(security['symbol'].Value))
        
                
        #for symbol in self.short:
            #if algorithm.Portfolio[symbol].Invested:
                #self.insights.append(Insight.Price(symbol, self.insightExpiry, InsightDirection.Flat))

        return self.insights
        
    def OnSecuritiesChanged(self, algorithm, changes):
        
        '''
        Description:
            Event fired each time the we add/remove securities from the data feed
        Args:
            algorithm: The algorithm instance that experienced the change in securities
            changes: The security additions and removals from the algorithm
        '''
        
        # add new securities
        for security in changes.AddedSecurities:
            symbol = security.Symbol
            self.mom.append({"symbol":symbol, "indicator":algorithm.MOM(symbol, 126, Resolution.Daily)})

        # remove securities
        #for security in changes.RemovedSecurities:
            #symbol = security.Symbol
            #self.short.append(symbol)
                


class CustomOptimizationPortfolioConstructionModel(PortfolioConstructionModel):
    
    '''
    Description:
        Allocate optimal weights to each security in order to optimize the portfolio objective function provided
    Details:
        - The target percent holdings of each security is 1/N where N is the number of securities with active Up/Down insights
        - For InsightDirection.Up, long targets are returned
        - For InsightDirection.Down, short targets are returned
        - For InsightDirection.Flat, closing position targets are returned
    '''

    def __init__(self, objectiveFunction = 'std', rebalancingParam = False):
        
        '''
        Description:
            Initialize a new instance of CustomOptimizationPortfolioConstructionModel
        Args:
            objectiveFunction: The function to optimize. If set to 'equal', it will just perform equal weighting
            rebalancingParam: Integer indicating the number of days for rebalancing (default set to False, no rebalance)
                - Independent of this parameter, the portfolio will be rebalanced when a security is added/removed/changed direction
        '''
        
        if objectiveFunction != 'equal':
            # minWeight set to 0 to ensure long only weights
            self.optimizer = CustomPortfolioOptimizer(minWeight = 0, maxWeight = 1, objFunction = objectiveFunction) # initialize the optimizer
        
        self.optWeights = None
        self.objectiveFunction = objectiveFunction
        self.insightCollection = InsightCollection()
        self.removedSymbols = []
        self.nextExpiryTime = UTCMIN
        self.rebalancingTime = UTCMIN
        
        # if the rebalancing parameter is not False but a positive integer
        # convert rebalancingParam to timedelta and create rebalancingFunc
        if rebalancingParam > 0:
            self.rebalancing = True
            rebalancingParam = timedelta(days = rebalancingParam)
            self.rebalancingFunc = lambda dt: dt + rebalancingParam
        else:
            self.rebalancing = rebalancingParam

    def CreateTargets(self, algorithm, insights):

        '''
        Description:
            Create portfolio targets from the specified insights
        Args:
            algorithm: The algorithm instance
            insights: The insights to create portfolio targets from
        Returns:
            An enumerable of portfolio targets to be sent to the execution model
        '''

        targets = []
        
        # check if we have new insights coming from the alpha model or if some existing insights have expired
        # or if we have removed symbols from the universe
        if (len(insights) == 0 and algorithm.UtcTime <= self.nextExpiryTime and self.removedSymbols is None):
            return targets
        
        # here we get the new insights and add them to our insight collection
        for insight in insights:
            self.insightCollection.Add(insight)
            
        # create flatten target for each security that was removed from the universe
        if self.removedSymbols is not None:
            universeDeselectionTargets = [ PortfolioTarget(symbol, 0) for symbol in self.removedSymbols ]
            targets.extend(universeDeselectionTargets)
            self.removedSymbols = None

        # get insight that haven't expired of each symbol that is still in the universe
        activeInsights = self.insightCollection.GetActiveInsights(algorithm.UtcTime)

        # get the last generated active insight for each symbol
        lastActiveInsights = []
        for symbol, g in groupby(activeInsights, lambda x: x.Symbol):
            lastActiveInsights.append(sorted(g, key = lambda x: x.GeneratedTimeUtc)[-1])

        # check if we actually want to create new targets for the securities (check function ShouldCreateTargets for details)
        if self.ShouldCreateTargets(algorithm, self.optWeights, lastActiveInsights):
            # symbols with active insights
            lastActiveSymbols = [x.Symbol for x in lastActiveInsights]
            
            # get historical data for all symbols for the last 253 trading days (to get 252 returns)
            history = algorithm.History(lastActiveSymbols, 253, Resolution.Daily)
            
            # empty dictionary for calculations
            calculations = {}
            
            # iterate over all symbols and perform calculations
            for symbol in lastActiveSymbols:
                if (str(symbol) not in history.index or history.loc[str(symbol)].get('close') is None
                or history.loc[str(symbol)].get('close').isna().any()):
                    algorithm.Log('(Portfolio) no historical data for: ' + str(symbol.Value))
                    continue
                else:
                    # add symbol to calculations
                    calculations[symbol] = SymbolData(symbol)
                    try:
                        # get series of log-returns
                        calculations[symbol].CalculateLogReturnSeries(history)
                    except Exception:
                        algorithm.Log('(Portfolio) removing from calculations due to CalculateLogReturnSeries failing: ' + str(symbol.Value))
                        calculations.pop(symbol)
                        continue
            
            # determine target percent for the given insights (check function DetermineTargetPercent for details)
            self.optWeights = self.DetermineTargetPercent(calculations, lastActiveInsights)
            
            if not self.optWeights.isnull().values.any():
                algorithm.Log('(Portfolio) optimal weights: ' + str(self.optWeights))
                
                errorSymbols = {}
                for symbol in lastActiveSymbols:
                    if str(symbol) in self.optWeights:
                        # avoid very small numbers and make them 0
                        if self.optWeights[str(symbol)] <= 1e-10:
                            self.optWeights[str(symbol)] = 0
                        algorithm.Plot('Optimal Allocation', symbol.Value, float(self.optWeights[str(symbol)]))
                        target = PortfolioTarget.Percent(algorithm, symbol, self.optWeights[str(symbol)])
                        if not target is None:
                            targets.append(target)
                        else:
                            errorSymbols[symbol] = symbol

            # update rebalancing time
            if self.rebalancing:
                self.rebalancingTime = self.rebalancingFunc(algorithm.UtcTime)

        # get expired insights and create flatten targets for each symbol
        expiredInsights = self.insightCollection.RemoveExpiredInsights(algorithm.UtcTime)

        expiredTargets = []
        for symbol, f in groupby(expiredInsights, lambda x: x.Symbol):
            if not self.insightCollection.HasActiveInsights(symbol, algorithm.UtcTime) and not symbol in errorSymbols:
                expiredTargets.append(PortfolioTarget(symbol, 0))
                continue

        targets.extend(expiredTargets)
        
        # here we update the next expiry date in the insight collection
        self.nextExpiryTime = self.insightCollection.GetNextExpiryTime()
        if self.nextExpiryTime is None:
            self.nextExpiryTime = UTCMIN

        return targets
        
    def ShouldCreateTargets(self, algorithm, optWeights, lastActiveInsights):
        
        '''
        Description:
            Determine whether we should rebalance the portfolio to keep equal weighting when:
                - It is time to rebalance regardless
                - We want to include some new security in the portfolio
                - We want to modify the direction of some existing security
        Args:
            optWeights: Series containing the current optimal weight for each security
            lastActiveInsights: The last active insights to check
        '''
        
        # it is time to rebalance
        if self.rebalancing and algorithm.UtcTime >= self.rebalancingTime:
            return True
        
        for insight in lastActiveInsights:
            # if there is an insight for a new security that's not invested and it has no existing optimal weight, then rebalance
            if (not algorithm.Portfolio[insight.Symbol].Invested
            and insight.Direction != InsightDirection.Flat
            and str(insight.Symbol) not in optWeights):
                return True
            # if there is an insight to close a long position, then rebalance
            elif algorithm.Portfolio[insight.Symbol].IsLong and insight.Direction != InsightDirection.Up:
                return True
            # if there is an insight to close a short position, then rebalance
            elif algorithm.Portfolio[insight.Symbol].IsShort and insight.Direction != InsightDirection.Down:
                return True
            else:
                continue
            
        return False
        
    def DetermineTargetPercent(self, calculations, lastActiveInsights):
        
        '''
        Description:
            Determine the target percent for each symbol provided
        Args:
            calculations: Dictionary with calculations for symbols
            lastActiveInsights: Dictionary with calculations for symbols
        '''
        
        if self.objectiveFunction == 'equal':
            # give equal weighting to each security
            count = sum(x.Direction != InsightDirection.Flat for x in lastActiveInsights)
            percent = 0 if count == 0 else 1.0 / count
        
            result = {}
            for insight in lastActiveInsights:
                result[str(insight.Symbol)] = insight.Direction * percent
            
            weights = pd.Series(result)
            
            return weights
        
        else:        
            # create a dictionary keyed by the symbols in calculations with a pandas.Series as value to create a dataframe of log-returns
            logReturnsDict = { str(symbol): symbolData.logReturnSeries for symbol, symbolData in calculations.items() }
            logReturnsDf = pd.DataFrame(logReturnsDict)
            
            # portfolio optimizer finds the optimal weights for the given data
            weights = self.optimizer.Optimize(historicalLogReturns = logReturnsDf)
            weights = pd.Series(weights, index = logReturnsDf.columns)
            
            return weights
        
    def OnSecuritiesChanged(self, algorithm, changes):
        
        '''
        Description:
            Event fired each time the we add/remove securities from the data feed
        Args:
            algorithm: The algorithm instance that experienced the change in securities
            changes: The security additions and removals from the algorithm
        '''

        # get removed symbol and invalidate them in the insight collection
        self.removedSymbols = [x.Symbol for x in changes.RemovedSecurities]
        self.insightCollection.Clear(self.removedSymbols)
        
class SymbolData:
    
    ''' Contain data specific to a symbol required by this model '''
    
    def __init__(self, symbol):
        
        self.Symbol = symbol
        self.logReturnSeries = None
    
    def CalculateLogReturnSeries(self, history):
        
        ''' Calculate the log-returns series for each security '''
        
        self.logReturnSeries = np.log(1 + history.loc[str(self.Symbol)]['close'].pct_change(periods = 1).dropna()) # 1-day log-returns
        
### class containing the CustomPortfolioOptimizer -----------------------------------------------------------------------------------------

class CustomPortfolioOptimizer:
    
    '''
    Description:
        Implementation of a custom optimizer that calculates the weights for each asset to optimize a given objective function
    Details:
        Optimization can be:
            - Maximize Portfolio Return
            - Minimize Portfolio Standard Deviation
            - Maximize Portfolio Sharpe Ratio
        Constraints:
            - Weights must be between some given boundaries
            - Weights must sum to 1
    '''
    
    def __init__(self, 
                 minWeight = -1,
                 maxWeight = 1,
                 objFunction = 'std'):
                     
        '''
        Description:
            Initialize the CustomPortfolioOptimizer
        Args:
            minWeight(float): The lower bound on portfolio weights
            maxWeight(float): The upper bound on portfolio weights
            objFunction: The objective function to optimize (return, std, sharpe)
        '''
        
        self.minWeight = minWeight
        self.maxWeight = maxWeight
        self.objFunction = objFunction

    def Optimize(self, historicalLogReturns, covariance = None):
        
        '''
        Description:
            Perform portfolio optimization using a provided matrix of historical returns and covariance (optional)
        Args:
            historicalLogReturns: Matrix of historical log-returns where each column represents a security and each row log-returns for the given date/time (size: K x N)
            covariance: Multi-dimensional array of double with the portfolio covariance of returns (size: K x K)
        Returns:
            Array of double with the portfolio weights (size: K x 1)
        '''
        
        # if no covariance is provided, calculate it using the historicalLogReturns
        if covariance is None:
            covariance = historicalLogReturns.cov()

        size = historicalLogReturns.columns.size # K x 1
        x0 = np.array(size * [1. / size])
        
        # apply equality constraints
        constraints = ({'type': 'eq', 'fun': lambda weights: self.GetBudgetConstraint(weights)})

        opt = minimize(lambda weights: self.ObjectiveFunction(weights, historicalLogReturns, covariance),   # Objective function
                        x0,                                                                                 # Initial guess
                        bounds = self.GetBoundaryConditions(size),                                          # Bounds for variables
                        constraints = constraints,                                                          # Constraints definition
                        method = 'SLSQP')                                                                   # Optimization method: Sequential Least Squares Programming
                        
        return opt['x']

    def ObjectiveFunction(self, weights, historicalLogReturns, covariance):
        
        '''
        Description:
            Compute the objective function
        Args:
            weights: Portfolio weights
            historicalLogReturns: Matrix of historical log-returns
            covariance: Covariance matrix of historical log-returns
        '''
        
        # calculate the annual return of portfolio
        annualizedPortfolioReturns = np.sum(historicalLogReturns.mean() * 252 * weights)

        # calculate the annual standard deviation of portfolio
        annualizedPortfolioStd = np.sqrt( np.dot(weights.T, np.dot(covariance * 252, weights)) )
        
        if annualizedPortfolioStd == 0:
            raise ValueError(f'CustomPortfolioOptimizer.ObjectiveFunction: annualizedPortfolioStd cannot be zero. Weights: {weights}')
        
        # calculate annual sharpe ratio of portfolio
        annualizedPortfolioSharpeRatio = (annualizedPortfolioReturns / annualizedPortfolioStd)
            
        if self.objFunction == 'sharpe':
            return -annualizedPortfolioSharpeRatio # convert to negative to be minimized
        elif self.objFunction == 'return':
            return -annualizedPortfolioReturns # convert to negative to be minimized
        elif self.objFunction == 'std':
            return annualizedPortfolioStd
        else:
            raise ValueError(f'CustomPortfolioOptimizer.ObjectiveFunction: objFunction input has to be one of sharpe, return or std')

    def GetBoundaryConditions(self, size):
        
        ''' Create the boundary condition for the portfolio weights '''
        
        return tuple((self.minWeight, self.maxWeight) for x in range(size))

    def GetBudgetConstraint(self, weights):
        
        ''' Define a budget constraint: the sum of the weights equal to 1 '''
        
        return np.sum(weights) - 1


class ImmediateExecutionWithLogsModel(ExecutionModel):
    
    '''
    Description:
        Custom implementation of IExecutionModel that immediately submits market orders to achieve the desired portfolio targets
    Details:
        This custom implementation includes logs with information about number of shares traded, prices, profit and profit percent
        for both long and short positions.
    '''

    def __init__(self):
        
        ''' Initializes a new instance of the ImmediateExecutionModel class '''
        
        self.targetsCollection = PortfolioTargetCollection()

    def Execute(self, algorithm, targets):
        
        '''
        Description:
            Immediately submits orders for the specified portfolio targets
        Args:
            algorithm: The algorithm instance
            targets: The portfolio targets to be ordered
        '''
        
        self.targetsCollection.AddRange(targets)
        
        if self.targetsCollection.Count > 0:
            for target in self.targetsCollection.OrderByMarginImpact(algorithm):
                # calculate remaining quantity to be ordered
                quantity = OrderSizing.GetUnorderedQuantity(algorithm, target)
                
                # check if quantity is actually different than zero
                if quantity != 0:
                    # get the current holdings quantity, average price and cost
                    beforeHoldingsQuantity = algorithm.ActiveSecurities[target.Symbol].Holdings.Quantity
                    beforeHoldingsAvgPrice = algorithm.ActiveSecurities[target.Symbol].Holdings.AveragePrice
                    beforeHoldingsCost = algorithm.ActiveSecurities[target.Symbol].Holdings.HoldingsCost
                    
                    # place market order
                    algorithm.MarketOrder(target.Symbol, quantity)
                    
                    # get the new holdings quantity, average price and cost
                    newHoldingsQuantity = beforeHoldingsQuantity + quantity
                    newHoldingsAvgPrice = algorithm.ActiveSecurities[target.Symbol].Holdings.AveragePrice
                    newHoldingsCost = algorithm.ActiveSecurities[target.Symbol].Holdings.HoldingsCost
                    
                    # this is just for market on open orders because the avg price and cost won't update until order gets filled
                    # so to avoid getting previous values we just make them zero
                    if newHoldingsAvgPrice == beforeHoldingsAvgPrice and newHoldingsCost == beforeHoldingsCost:
                        newHoldingsAvgPrice = 0
                        newHoldingsCost = 0
                    
                    # calculate the profit percent and dollar profit when closing positions
                    lastPrice = algorithm.ActiveSecurities[target.Symbol].Price
                    if beforeHoldingsAvgPrice != 0 and lastPrice != 0:
                        # profit/loss percent for the trade
                        tradeProfitPercent = (((lastPrice / beforeHoldingsAvgPrice) - 1) * np.sign(beforeHoldingsQuantity)) * 100
                        # dollar profit/loss for the trade
                        tradeDollarProfit = (lastPrice - beforeHoldingsAvgPrice) * beforeHoldingsQuantity
                    else:
                        tradeProfitPercent = 0
                        tradeDollarProfit = 0
                        
                    ### if we are not invested already the options are: ----------------------------------------------------------
                        # new holdings > 0 => going long
                        # new holdings < 0 => going short
                    if beforeHoldingsQuantity == 0:
                        if newHoldingsQuantity > 0:
                            algorithm.Log(str(target.Symbol.Value) + ': going long!'
                            + ' current total holdings: ' + str(round(quantity, 0))
                            + '; current average price: ' + str(round(newHoldingsAvgPrice, 4))
                            + '; current total holdings cost: ' + str(round(newHoldingsCost, 2)))
                        else:
                            algorithm.Log(str(target.Symbol.Value) + ': going short!'
                            + ' current total holdings: ' + str(round(quantity, 0))
                            + '; average price: ' + str(round(newHoldingsAvgPrice, 4))
                            + '; current total holdings cost: ' + str(round(newHoldingsCost, 2)))
                    ### -----------------------------------------------------------------------------------------------------------
                    
                    ### if we are already long the security the options are: ------------------------------------------------------
                        # new quantity > 0 => adding to long position
                        # new quantity < 0 and new holdings < before holdings => partially selling long position
                        # new quantity < 0 and new holdings = 0 => closing entire long position
                        # new quantity < 0 and new holdings < 0 => closing entire long position and going short
                    elif beforeHoldingsQuantity > 0:
                        if quantity > 0:
                            algorithm.Log(str(target.Symbol.Value) + ': adding to current long position!'
                            + ' additional shares: ' + str(round(quantity, 0))
                            + '; current total holdings: ' + str(round(newHoldingsQuantity, 0))
                            + '; current average price: ' + str(round(newHoldingsAvgPrice, 4))
                            + '; current total holdings cost: ' + str(round(newHoldingsCost, 2)))
                        
                        elif newHoldingsQuantity > 0 and newHoldingsQuantity < beforeHoldingsQuantity:  
                            algorithm.Log(str(target.Symbol.Value) + ': selling part of current long position!'
                            + ' selling shares: ' + str(round(-quantity, 0))
                            + '; current total holdings: ' + str(round(newHoldingsQuantity, 0))
                            + '; buying average price was: ' + str(round(beforeHoldingsAvgPrice, 4))
                            + '; approx. selling average price is: ' + str(round(lastPrice, 4))
                            + '; profit percent: ' + str(round(tradeProfitPercent, 4))
                            + '; dollar profit: ' + str(round(tradeDollarProfit, 2)))
                            
                        elif newHoldingsQuantity == 0:
                            algorithm.Log(str(target.Symbol.Value) + ': closing down entire current long position!'
                            + ' selling shares: ' + str(round(-quantity, 0))
                            + '; current total holdings: ' + str(round(newHoldingsQuantity, 0))
                            + '; buying average price was: ' + str(round(beforeHoldingsAvgPrice, 4))
                            + '; approx. selling average price is: ' + str(round(lastPrice, 4))
                            + '; profit percent: ' + str(round(tradeProfitPercent, 4))
                            + '; dollar profit: ' + str(round(tradeDollarProfit, 2)))
                            
                        elif newHoldingsQuantity < 0:
                            algorithm.Log(str(target.Symbol.Value) + ': closing down entire current long position and going short!'
                            + ' selling shares to close long: ' + str(round(beforeHoldingsQuantity, 0))
                            + '; profit percent on long position: ' + str(round(tradeProfitPercent, 4))
                            + '; dollar profit on long position: ' + str(round(tradeDollarProfit, 2))
                            + '; selling shares to go short: ' + str(round(-newHoldingsQuantity, 0))
                            + '; current total holdings: ' + str(round(newHoldingsQuantity, 0))
                            + '; current average price: ' + str(round(newHoldingsAvgPrice, 4))
                            + '; current total holdings cost: ' + str(round(newHoldingsCost, 2)))
                    ### --------------------------------------------------------------------------------------------------------------
                    
                    ### if we are already short the security the options are: --------------------------------------------------------
                        # new quantity < 0 => adding to short position
                        # new quantity > 0 and new holdings > before holdings => partially buying back short position
                        # new quantity > 0 and new holdings = 0 => closing entire short position
                        # new quantity > 0 and new holdings > 0 => closing entire short position and going long
                    elif beforeHoldingsQuantity < 0:
                        if quantity < 0:
                            algorithm.Log(str(target.Symbol.Value) + ': adding to current short position!'
                            + ' additional shares: ' + str(round(quantity, 0))
                            + '; current total holdings: ' + str(round(newHoldingsQuantity, 0))
                            + '; current average price: ' + str(round(newHoldingsAvgPrice, 4))
                            + '; current total holdings cost: ' + str(round(newHoldingsCost, 2)))
                        
                        elif newHoldingsQuantity < 0 and newHoldingsQuantity > beforeHoldingsQuantity: 
                            algorithm.Log(str(target.Symbol.Value) + ': buying back part of current short position!'
                            + ' buying back shares: ' + str(round(quantity, 0))
                            + '; current total holdings: ' + str(round(newHoldingsQuantity, 0))
                            + '; shorting average price was: ' + str(round(beforeHoldingsAvgPrice, 4))
                            + '; approx. buying back average price is: ' + str(round(lastPrice, 4))
                            + '; profit percent: ' + str(round(tradeProfitPercent, 4))
                            + '; dollar profit: ' + str(round(tradeDollarProfit, 2)))
                            
                        elif newHoldingsQuantity == 0:
                            algorithm.Log(str(target.Symbol.Value) + ': closing down entire current short position!'
                            + ' buying back shares: ' + str(round(quantity, 0))
                            + '; current total holdings: ' + str(round(newHoldingsQuantity, 0))
                            + '; shorting average price was: ' + str(round(beforeHoldingsAvgPrice, 4))
                            + '; approx. buying back average price is: ' + str(round(lastPrice, 4))
                            + '; profit percent: ' + str(round(tradeProfitPercent, 4))
                            + '; dollar profit: ' + str(round(tradeDollarProfit, 2)))
                            
                        elif newHoldingsQuantity > 0:
                            algorithm.Log(str(target.Symbol.Value) + ': closing down entire current short position and going long!'
                            + ' buying back shares to close short: ' + str(round(-beforeHoldingsQuantity, 0))
                            + '; profit percent on short position: ' + str(round(tradeProfitPercent, 4))
                            + '; dollar profit on short position: ' + str(round(tradeDollarProfit, 2))
                            + '; buying shares to go long: ' + str(round(newHoldingsQuantity, 0))
                            + '; current total holdings: ' + str(round(newHoldingsQuantity, 0))
                            + '; current average price: ' + str(round(newHoldingsAvgPrice, 4))
                            + '; current total holdings cost: ' + str(round(newHoldingsCost, 2)))
                    ### ---------------------------------------------------------------------------------------------------------------
                        
            self.targetsCollection.ClearFulfilled(algorithm)






### <summary>
### Basic template algorithm simply initializes the date range and cash. This is a skeleton
### framework you can use for designing an algorithm.
### </summary>
### <meta name="tag" content="using data" />
### <meta name="tag" content="using quantconnect" />
### <meta name="tag" content="trading and orders" />
class BasicAlphaStreamTSEAlgorithm(QCAlgorithm):
    '''Basic template algorithm simply initializes the date range and cash'''

    def Initialize(self):
        '''Initialise the data and resolution required, as well as the cash and start-end dates for your algorithm. All algorithms must initialized.'''

        ### user-defined inputs --------------------------------------------------------------

        self.SetStartDate(2019, 1, 1)   # set start date
        self.SetEndDate(2020, 4, 3)     # set end date
        self.SetAccountCurrency("CAD")
        self.SetCash(100000)            # set strategy cash
        
        
        
        # objective function for portfolio optimizer
        # options are: equal (Equal Weighting), return (Maximize Portfolio Return), std (Minimize Portfolio Standard Deviation),
        # and sharpe (Maximize Portfolio Sharpe Ratio)
        objectiveFunction = 'return'
        
        # rebalancing period (to enable rebalancing enter an integer for number of calendar days, e.g. 1, 7, 30, 365)
        rebalancingParam = 30
            
        ### -----------------------------------------------------------------------------------
        
        # set the brokerage model for slippage and fees
        #self.SetSecurityInitializer(self.CustomSecurityInitializer)
        #self.SetBrokerageModel(AlphaStreamsBrokerageModel())
        
        # set requested data resolution and disable fill forward data
        self.UniverseSettings.Resolution = Resolution.Daily
        self.UniverseSettings.FillForward = False
        self.averages = { }
        # initialize plot for optimal allocation
        #allocationPlot = Chart('Optimal Allocation')

        allocationPlot = Chart('Optimal Allocation')
        # add tickers to the list
        tickers = ['RY','TD','ENB','CNR','BNS','SHOP','TRP','BCE','ABX','ATD-B','BMO','BAM-A','CP','CM',
                    'SU','MFC','WCN','T','NTR','SLF','FNV','CSU','FTS','CNQ','RCI-B','GIB-A','NA','IFC','WPM','QSR',
                    'TRI','BIP-UN','MRU','PPL','AEM','EMA','OTEX','POW','MG','L','FFH','DOL','SJRB','AQN','SAP','H']
        
        
        
        #str='RY,TD,ENB,CNR,BNS,SHOP,TRP,BCE,ABX,ATD-B,BMO,BAM-A,CP,CM,SU,MFC,WCN,T,NTR,SLF,FNV,CSU,FTS,CNQ,RCI-B,GIB-A,NA,IFC,WPM,QSR,\
        #                    TRI,BIP-UN,MRU,PPL,AEM,EMA,OTEX,POW,MG,L,FFH,DOL,KL,SJRB,AQN,SAP,H,BEP-UN,\
        #                    CAR-UN,WN,K,BHC,TSGI,GWO,CCL-B,QBR-B,AP-UN,X,RBA,TECK-B,WSP,REI-UN,TIH,FM,CTC-A,CAD,\
        #                    NPI,EMP-A,IAG,CAE,WEED,ONEX,BTO,CCO,PAAS,AC,DSG,CU,BPY-UN,STN,EFN,FSV,YRI,IMO,PKI,GIL,\
        #                    SNC,ALA,IPL,LUN,CHP-UN,GRT-UN,CIX,BYD,ACO-X,CVE,KXS,CPX,BB,KEY,AGI,TFII,HR-UN,NG,INE,FTT,\
        #                    SRU-UN,GEI,FCR-UN,CCA,TOU,PBH,TA,PRMW,NVU-UN,SSRM,BBU-UN,CIGI,MSI,CSH-UN,MFI,IGM,SJ,\
        #                    BLX,CG,ENGH,BLDP,PXT,CWB,GOOS,IIP-UN,FR,RNW,PSK,KMP-UN,EDV,OR,IMG,CUF-UN,ACB,PVG,AIF,\
        #                    CRON,ARX,SPB,NWH-UN,GC,ELD,CJT,WFT,ASR,WPK,DIR-UN,MX,LB,LNR,IVN,SSL,ATA,MIC,TXG,RCH,APHA,\
        #                    CRR-UN,NWC,D-UN,LIF,HSE,REAL,ATZ,SMU-UN,WDO,JWEL,DOO,TCN,AX-UN,BBD.B,SMF,TCL-A,BEI-UN,HCG,\
        #                    CAS,ECN,OGC,LSPD,NFI,MAG,SIA,RUS,CRT-UN,BAD,SVM,OSB,ARE,CGX,USD,GUD,VET,SEA,EQB,ERO,HBM,\
        #                    CPG,ITP,WTE,EIF,MRE,CLS,CJRB,EFX,WCP,EXE,ERF,PSI,CHE.UN,MEG,CFP,VII,IFP,CHR,MTY,MTL,TOY,\
        #                    ZZZ,AFN,AD,HEXO,FRU,FEC,BTE,SES,SCL'

        #tickers= str.split(',')
        

        symbols = []
        # loop through the tickers list and create symbols for the universe
        for i in range(len(tickers)):
            symbols.append(Symbol.Create(tickers[i].strip()+'.TO', SecurityType.Equity, Market.XTSE))
            #allocationPlot.AddSeries(Series(tickers[i], SeriesType.Line, ''))
        #symbols.append(Symbol.Create('SPY', SecurityType.Equity, Market.XTSE))    
        self.AddChart(allocationPlot)
        
        # select modules
        self.SetUniverseSelection(ManualUniverseSelectionModel(symbols))
        

        self.SetAlpha(MomentumAlphaCreationModel())
        self.SetPortfolioConstruction(CustomOptimizationPortfolioConstructionModel(objectiveFunction = objectiveFunction, rebalancingParam = rebalancingParam))
        
        
        self.SetExecution(ImmediateExecutionModel())
        #self.SetExecution(ImmediateExecutionWithLogsModel())
        self.SetRiskManagement(NullRiskManagementModel())