


#property strict

#define SIDE_BUY  0
#define SIDE_SELL 1

input int TradeSide = SIDE_BUY;
input int n_1 = 100;
input int n_2 = 50;
input int n_3 = 200;
input int MagicNumber = 123456;
input bool AvoidRepeatedTradeRanges = false;
input bool EnableDynamicN1 = false;

#define FIXED_LOT 0.01
string EA_COMMENT_BUY  = "PriceCycleBuy";
string EA_COMMENT_SELL = "PriceCycleSell";


double g_rangeLow[];
double g_rangeHigh[];
int    g_rangeCount = 0;
int    g_historyCount = -1;


bool     g_hasLastClose = false;
double   g_lastClosePrice = 0.0;
datetime g_lastCloseTime = 0;


int OnInit()
{
   if(n_1 <= 0 || n_2 <= 0 || n_3 <= 0)
   {
      Print("n_1, n_2 and n_3 must be greater than zero.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   if(TradeSide != SIDE_BUY && TradeSide != SIDE_SELL)
   {
      Print("TradeSide must be 0 for BUY or 1 for SELL.");
      return(INIT_PARAMETERS_INCORRECT);
   }

   RebuildClosedTradeCache();
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   ArrayResize(g_rangeLow, 0);
   ArrayResize(g_rangeHigh, 0);
   g_rangeCount = 0;
   
}


void OnTick()
{
   RefreshRates();

   
   if(OrdersHistoryTotal() != g_historyCount)
      RebuildClosedTradeCache();

   int ticket = FindOpenTrade();
   if(ticket > 0)
   {
      ManageOpenTrade(ticket);
      return;
   }

   if(!g_hasLastClose)
   {
      OpenSelectedTrade();
      return;
   }

   
   if(TradeSide == SIDE_BUY)
   {
      double currentPrice = Bid;
      if(currentPrice >= g_lastClosePrice + n_2 * Point ||
         currentPrice <= g_lastClosePrice - n_3 * Point)
      {
         OpenSelectedTrade();
         return;
      }
   }
   if(TradeSide == SIDE_SELL)
   {
      double currentPrice = Ask;
      if(currentPrice <= g_lastClosePrice - n_2 * Point ||
         currentPrice >= g_lastClosePrice + n_3 * Point)
      {
         OpenSelectedTrade();
         return;
      }
   }
}


void ManageOpenTrade(int ticket)
{
   if(!OrderSelect(ticket, SELECT_BY_TICKET, MODE_TRADES))
      return;
   if(OrderCloseTime() != 0)
      return;

   RefreshRates();
   double openPrice = OrderOpenPrice();

   if(OrderType() == OP_BUY)
   {
      bool mustClose;
      if(!EnableDynamicN1)
      {
         
         double distance = MathAbs(Bid - openPrice) / Point;
         mustClose = (distance >= n_1);
      }
      else
      {
         
         double highestBid = GetAndUpdateHighestBid(ticket, openPrice, Bid);
         double upperExit = openPrice + n_1 * Point;
         double lowerExit = highestBid - n_1 * Point;
         mustClose = (Bid >= upperExit || Bid <= lowerExit);
      }

      if(mustClose)
      {
         int closeTicket = OrderTicket();
         double lots = OrderLots();
         double requestedClose = Bid;
         bool closed = OrderClose(closeTicket, lots, requestedClose, 30, clrNONE);
         if(!closed)
         {
            int errorCode = GetLastError();
            Print("BUY OrderClose failed. Ticket=", closeTicket,
                  " Error=", errorCode);
            ResetLastError();
         }
         else
         {
            RecordSuccessfulClose(closeTicket, openPrice, requestedClose);
            GlobalVariableDel(HighKey(closeTicket));
         }
      }
      return;
   }

   if(OrderType() == OP_SELL)
   {
      
      double distance = MathAbs(Ask - openPrice) / Point;
      if(distance >= n_1)
      {
         int closeTicket = OrderTicket();
         double lots = OrderLots();
         double requestedClose = Ask;
         bool closed = OrderClose(closeTicket, lots, requestedClose, 30, clrNONE);
         if(!closed)
         {
            int errorCode = GetLastError();
            Print("SELL OrderClose failed. Ticket=", closeTicket,
                  " Error=", errorCode);
            ResetLastError();
         }
         else
            RecordSuccessfulClose(closeTicket, openPrice, requestedClose);
      }
      return;
   }
}


void OpenSelectedTrade()
{
   RefreshRates();
   double price;
   int type;
   string comment;

   if(TradeSide == SIDE_BUY)
   {
      type = OP_BUY;
      price = Ask;
      comment = EA_COMMENT_BUY;
   }
   else
   {
      type = OP_SELL;
      price = Bid;
      comment = EA_COMMENT_SELL;
   }
   price = NormalizeDouble(price, Digits);

   
   if(AvoidRepeatedTradeRanges && IsInsideTradedRange(price))
      return;

   int ticket = OrderSend(Symbol(), type, FIXED_LOT, price, 30, 0, 0,
                          comment, MagicNumber, 0, clrNONE);
   if(ticket < 0)
   {
      int errorCode = GetLastError();
      Print("OrderSend failed. Error=", errorCode);
      ResetLastError();
   }
   else if(type == OP_BUY && EnableDynamicN1)
   {
      
      if(OrderSelect(ticket, SELECT_BY_TICKET, MODE_TRADES))
         SaveHighestBid(ticket, OrderOpenPrice());
   }
}


int FindOpenTrade()
{
   string requiredComment = (TradeSide == SIDE_BUY)
                            ? EA_COMMENT_BUY : EA_COMMENT_SELL;
   for(int i = OrdersTotal() - 1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_TRADES)) continue;
      if(OrderSymbol() != Symbol()) continue;
      if(OrderMagicNumber() != MagicNumber) continue;
      if(OrderComment() != requiredComment) continue;
      if(TradeSide == SIDE_BUY && OrderType() == OP_BUY)
         return(OrderTicket());
      if(TradeSide == SIDE_SELL && OrderType() == OP_SELL)
         return(OrderTicket());
   }
   return(-1);
}




void RebuildClosedTradeCache()
{
   int total = OrdersHistoryTotal();
   g_historyCount = total;
   g_hasLastClose = false;
   g_lastClosePrice = 0.0;
   g_lastCloseTime = 0;
   g_rangeCount = 0;
   ArrayResize(g_rangeLow, 0);
   ArrayResize(g_rangeHigh, 0);

   double lows[];
   double highs[];
   int count = 0;
   if(AvoidRepeatedTradeRanges)
   {
      ArrayResize(lows, total);
      ArrayResize(highs, total);
   }

   string requiredComment = (TradeSide == SIDE_BUY)
                            ? EA_COMMENT_BUY : EA_COMMENT_SELL;
   int requiredType = (TradeSide == SIDE_BUY) ? OP_BUY : OP_SELL;

   
   for(int i = total - 1; i >= 0; i--)
   {
      if(!OrderSelect(i, SELECT_BY_POS, MODE_HISTORY)) continue;
      if(OrderSymbol() != Symbol()) continue;
      if(OrderMagicNumber() != MagicNumber) continue;
      if(OrderComment() != requiredComment) continue;
      if(OrderType() != requiredType) continue;
      if(OrderCloseTime() == 0) continue;

      if(!g_hasLastClose || OrderCloseTime() > g_lastCloseTime)
      {
         g_hasLastClose = true;
         g_lastCloseTime = OrderCloseTime();
         g_lastClosePrice = OrderClosePrice();
      }

      if(AvoidRepeatedTradeRanges)
      {
         lows[count]  = MathMin(OrderOpenPrice(), OrderClosePrice());
         highs[count] = MathMax(OrderOpenPrice(), OrderClosePrice());
         count++;
      }
   }

   if(AvoidRepeatedTradeRanges && count > 0)
   {
      SortIntervals(lows, highs, 0, count - 1);
      ArrayResize(g_rangeLow, count);
      ArrayResize(g_rangeHigh, count);
      for(int j = 0; j < count; j++)
      {
         if(g_rangeCount > 0 && lows[j] <= g_rangeHigh[g_rangeCount-1] + Point)
         {
            if(highs[j] > g_rangeHigh[g_rangeCount-1])
               g_rangeHigh[g_rangeCount-1] = highs[j];
         }
         else
         {
            g_rangeLow[g_rangeCount] = lows[j];
            g_rangeHigh[g_rangeCount] = highs[j];
            g_rangeCount++;
         }
      }
      ArrayResize(g_rangeLow, g_rangeCount);
      ArrayResize(g_rangeHigh, g_rangeCount);
   }
}


void SortIntervals(double &lows[], double &highs[], int left, int right)
{
   int i = left, j = right;
   double pivot = lows[(left + right) / 2];
   while(i <= j)
   {
      while(lows[i] < pivot) i++;
      while(lows[j] > pivot) j--;
      if(i <= j)
      {
         double tmp = lows[i]; lows[i] = lows[j]; lows[j] = tmp;
         tmp = highs[i]; highs[i] = highs[j]; highs[j] = tmp;
         i++; j--;
      }
   }
   if(left < j) SortIntervals(lows, highs, left, j);
   if(i < right) SortIntervals(lows, highs, i, right);
}


bool IsInsideTradedRange(double price)
{
   int left = 0, right = g_rangeCount - 1;
   while(left <= right)
   {
      int mid = left + (right - left) / 2;
      if(price < g_rangeLow[mid]) right = mid - 1;
      else if(price > g_rangeHigh[mid]) left = mid + 1;
      else return(true);
   }
   return(false);
}


void InsertClosedInterval(double firstPrice, double secondPrice)
{
   if(!AvoidRepeatedTradeRanges) return;
   double low = MathMin(firstPrice, secondPrice);
   double high = MathMax(firstPrice, secondPrice);
   int start = 0;
   while(start < g_rangeCount && g_rangeHigh[start] + Point < low)
      start++;
   int finish = start;
   while(finish < g_rangeCount && g_rangeLow[finish] <= high + Point)
   {
      low = MathMin(low, g_rangeLow[finish]);
      high = MathMax(high, g_rangeHigh[finish]);
      finish++;
   }
   int removed = finish - start;
   int newCount = g_rangeCount - removed + 1;
   
   if(newCount > g_rangeCount)
   {
      if(ArrayResize(g_rangeLow, newCount) < 0 ||
         ArrayResize(g_rangeHigh, newCount) < 0)
      {
         Print("Insufficient memory for closed-price interval cache.");
         RebuildClosedTradeCache();
         return;
      }
   }
   if(newCount > g_rangeCount)
   {
      for(int j = g_rangeCount - 1; j >= finish; j--)
      {
         int dest = j - removed + 1;
         g_rangeLow[dest] = g_rangeLow[j];
         g_rangeHigh[dest] = g_rangeHigh[j];
      }
   }
   else
   {
      for(int j = finish; j < g_rangeCount; j++)
      {
         int dest = j - removed + 1;
         g_rangeLow[dest] = g_rangeLow[j];
         g_rangeHigh[dest] = g_rangeHigh[j];
      }
   }
   g_rangeLow[start] = low;
   g_rangeHigh[start] = high;
   g_rangeCount = newCount;
   if(newCount < ArraySize(g_rangeLow))
   {
      ArrayResize(g_rangeLow, newCount);
      ArrayResize(g_rangeHigh, newCount);
   }
}

void RecordSuccessfulClose(int ticket, double openPrice, double requestedClose)
{
   
   double actualClose = requestedClose;
   datetime actualCloseTime = TimeCurrent();
   if(OrderSelect(ticket, SELECT_BY_TICKET, MODE_HISTORY) && OrderCloseTime() > 0)
   {
      actualClose = OrderClosePrice();
      actualCloseTime = OrderCloseTime();
   }
   InsertClosedInterval(openPrice, actualClose);
   if(!g_hasLastClose || actualCloseTime >= g_lastCloseTime)
   {
      g_hasLastClose = true;
      g_lastClosePrice = actualClose;
      g_lastCloseTime = actualCloseTime;
   }
}



string HighKey(int ticket)
{
   return("PDC_H_" + IntegerToString(AccountNumber()) + "_" +
          IntegerToString(ticket));
}

void SaveHighestBid(int ticket, double highest)
{
   if(GlobalVariableSet(HighKey(ticket), highest) == 0)
      Print("Unable to save BUY high-water mark, ticket=", ticket,
            ", error=", GetLastError());
}

double GetAndUpdateHighestBid(int ticket, double openPrice, double currentBid)
{
   string key = HighKey(ticket);
   double highest = openPrice;
   double saved;
   if(GlobalVariableGet(key, saved))
      highest = MathMax(highest, saved);
   
   double newHigh = MathMax(highest, currentBid);
   if(newHigh > highest || !GlobalVariableCheck(key))
      SaveHighestBid(ticket, newHigh);
   return(newHigh);
}

