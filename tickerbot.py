from typing import Optional, Type

from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from maubot import Plugin, MessageEvent
from maubot.handlers import command

# not necessary, as it's imported by maubot already
#import asyncio
#import aiohttp
import json

class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("rapidapiKey")
        helper.copy("coinapiioKey")
        helper.copy("stocktrigger")
        helper.copy("cryptotrigger")

class TickerBot(Plugin):
    async def start(self) -> None:
        await super().start()
        self.config.load_and_update()

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    @command.new(name=lambda self: self.config["stocktrigger"],
            help="Look up information about a stock by its ticker symbol")
    @command.argument("ticker", pass_raw=True, required=True)
    async def handler(self, evt: MessageEvent, ticker: str) -> None:
        await evt.mark_read()

        tickerUpper = ticker.upper()
        url = f"https://apidojo-yahoo-finance-v1.p.rapidapi.com/market/v2/get-quotes?symbols={tickerUpper}"
        headers = {
            'x-rapidapi-key': self.config["rapidapiKey"],
            'x-rapidapi-host': "apidojo-yahoo-finance-v1.p.rapidapi.com"
            }
        
        try:
            response = await self.http.get(url, headers=headers)
            resp_json = await response.json()
        except Exception as e:
            await evt.respond(f"request failed: {e.message}")
            return None
        try:
            pruned_json = resp_json['quoteResponse']['result'][0]
            openDifference = f"{pruned_json['regularMarketPrice'] - pruned_json['regularMarketOpen']:.2f}"
            openPercentDiff = f"{(float(openDifference) / pruned_json['regularMarketOpen'] * 100):.2f}%"
        except Exception as e:
            await evt.respond("No results, double check that you've chosen a real ticker symbol")
            self.log.exception(e)
            return None
        
        if float(openDifference) < 0:
            color = "red"
            arrow = "\U000025BC"
        else:
            color = "green"
            arrow = "\U000025B2"

        prettyMessage = "<br />".join(
                [
                    f"<b>Current data for <a href=\"https://finance.yahoo.com/quote/{tickerUpper}\">\
                            {pruned_json['longName']}</a> ({tickerUpper}):</b>" ,
                    f"",
                    f"<b>Price:</b> <font color=\"{color}\">${str(pruned_json['regularMarketPrice'])}, \
                            {arrow}{openPercentDiff}</font> from market open @ ${str(pruned_json['regularMarketOpen'])}",
                    f"<b>52 Week High:</b> ${str(pruned_json['fiftyTwoWeekHigh'])}",
                    f"<b>52 Week Low:</b> ${str(pruned_json['fiftyTwoWeekLow'])}"
                ]
            )
        
        await evt.respond(prettyMessage, allow_html=True)




    @command.new(name=lambda self: self.config["cryptotrigger"],
            help="Look up exchange rate of a currency pair. You must supply a pair, e.g. BTC/USD or ADA/ETH, otherwise USD will be used by default.")
    @command.argument("exch_pair", pass_raw=True, required=True)
    async def handler(self, evt: MessageEvent, exch_pair: str) -> None:
        await evt.mark_read()

        exch_pair = exch_pair.upper()
        if '/' not in exch_pair:
            exch_pair = exch_pair + '/USD'

        url = f"https://rest.coinapi.io/v1/exchangerate/{exch_pair}"
        headers = {
            'X-CoinAPI-Key': self.config["coinapiioKey"],
            }
        
        try:
            response = await self.http.get(url, headers=headers)
            resp_json = await response.json()
        except Exception as e:
            await evt.respond(f"request failed: {e.message}")
            return None
        try:
            exch_rate = resp_json["rate"]
        except Exception as e:
            await evt.respond("No results, double check that you've chosen a real currency pair")
            self.log.exception(e)
            return None

        prettyMessage = "<br />".join(
                [
                    f"<b>Current exchange rate for {exch_pair}:</b> {exch_rate}" 
                ]
            )
        
        await evt.respond(prettyMessage, allow_html=True)
