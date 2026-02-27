# FMV Exam Walkthrough - Portfolio Analysis and CAPM

Alright Freddie. This one's different. No calendar, no tasks. This is your CAPM exam revision episode. Question three from the practice final - portfolio analysis and the Capital Asset Pricing Model. Twenty-five marks. The big one.

We're going to walk through the whole thing, but first, let's make sure the theory is locked in. Because if you understand the theory, the maths is just plugging in numbers.

Here's the setup. You've got twenty thousand dollars sitting in a single stock called Stock X. It earns seven percent expected return with a standard deviation of twenty-six percent. The risk-free rate is four percent. The market portfolio earns ten percent with a standard deviation of eighteen percent. And CAPM holds.

Now. Before we touch any numbers, let's talk about what this question is really testing. It's testing one idea. The difference between total risk and systematic risk. Total risk is the standard deviation - all the ups and downs a stock experiences. Systematic risk is beta - only the portion of those ups and downs that come from the market moving. The whole point of CAPM is that investors only get compensated for systematic risk. Because idiosyncratic risk, the firm-specific stuff, can be diversified away. If you can eliminate it for free, the market won't pay you for bearing it.

That's the free lunch Belo keeps talking about. Diversification eliminates risk without reducing return. So the market prices only what you can't escape.

OK. Part A. Sharpe ratio of Stock X.

The Sharpe ratio is excess return divided by total risk. Excess return means how much more than the risk-free rate you're earning. So that's seven minus four, which is three percent. Divide by the standard deviation of twenty-six percent. Three over twenty-six gives you zero point one one five.

That's not great. For every unit of risk you're taking, you're getting about eleven and a half basis points of excess return. Compare that to the US stock market, which historically delivers a Sharpe ratio around zero point four. Stock X is well below that. You're carrying a lot of risk for not much reward.

Part B. Maximum Sharpe ratio you can achieve.

This comes straight from two-fund separation. Session nine. The tangent portfolio is the market portfolio, and it has the highest Sharpe ratio of any portfolio. Nobody can beat it. So the maximum Sharpe ratio is the market's Sharpe ratio. Ten minus four over eighteen. Six over eighteen. Zero point three three three.

Why is this the maximum? Because the market portfolio sits at the point where a line from the risk-free rate is tangent to the efficient frontier. Any other portfolio gives you a shallower line, a worse trade-off between risk and return. The market is the steepest line you can draw.

Part C. Build an efficient portfolio P with the same seven percent return as Stock X, but the lowest possible risk.

This is two-fund separation in action. Every efficient portfolio is just a mix of two things: the risk-free asset and the market portfolio. That's it. So if you want seven percent return, you find the right mix.

Set up the equation. Seven percent equals w times four percent, plus one minus w times ten percent. Where w is the weight in the risk-free asset. Solve it. Seven equals four w plus ten minus ten w. Seven minus ten equals minus six w. w equals zero point five.

So fifty percent in the risk-free asset, fifty percent in the market portfolio. If you've got twenty thousand dollars, put ten thousand in Treasury bills and ten thousand in an index fund.

Now the risk. When you combine a risk-free asset with a risky portfolio, the formula simplifies beautifully. The risk-free asset has zero volatility and zero correlation with everything. So portfolio risk is just the weight in the risky asset times its standard deviation. Zero point five times eighteen percent equals nine percent.

Nine percent. Compare that to Stock X's twenty-six percent. Same expected return - seven percent in both cases. But portfolio P has less than a third of the risk. That's the power of diversification. Stock X is carrying a massive amount of idiosyncratic risk that you're not being paid for.

And the Sharpe ratio of P? Three percent over nine percent. Zero point three three three. Same as the market. Because P lies on the Capital Market Line. Any portfolio on the CML shares the market's Sharpe ratio.

Part D. The Capital Market Line.

The CML equation is expected return equals four percent plus zero point three three three times sigma. It's a straight line from the risk-free rate through the market portfolio. The slope is the market's Sharpe ratio.

Where do our three assets sit? The market is on the CML by definition - it's the tangent portfolio. Portfolio P is on the CML because we built it from the risk-free asset and the market. Stock X is below the CML. Way below. At its volatility of twenty-six percent, the CML predicts a return of about twelve point seven percent. Stock X only delivers seven. It's sitting south of the line because it carries uncompensated idiosyncratic risk.

Part E. The Security Market Line.

This is where it gets interesting. The SML equation is expected return equals four percent plus beta times six percent. Where six percent is the market risk premium.

Here's the crucial distinction. The CML plots return against sigma - total risk. Only efficient portfolios lie on it. The SML plots return against beta - systematic risk. Under CAPM, every asset lies on it. Every single one.

So where do our assets sit? Market - on the SML, beta equals one, return equals ten percent. Portfolio P - on the SML, correctly priced. Stock X - also on the SML.

Wait. Stock X was below the CML but it's on the SML? Yes. That's the whole point. Stock X has too much total risk for its return - that's why it's below the CML. But its expected return is exactly right for its level of systematic risk - that's why it's on the SML. The market doesn't punish you for having high total risk. It prices you based on your beta. Stock X's problem isn't that it's mispriced. It's that holding it alone is inefficient.

Part F. Beta of Stock X.

Since CAPM holds and Stock X is on the SML, we can extract beta directly. Seven percent equals four percent plus beta times six percent. So beta equals three over six. Zero point five.

Stock X has half the market's systematic risk. When the market moves one percent, Stock X is expected to move half a percent. Think of it like consumer staples - companies people buy from regardless of the economic cycle. Low co-movement with the market.

Part G. Correlation between Stock X and the market.

Beta equals correlation times sigma X divided by sigma M. We know beta is zero point five, sigma X is twenty-six percent, sigma M is eighteen percent. Rearrange. Correlation equals zero point five times eighteen over twenty-six. That's zero point three four six.

Only about thirty-five percent correlation with the market. This confirms what we've been saying - most of Stock X's volatility is idiosyncratic. It's bouncing around a lot, but most of that bouncing has nothing to do with the market. It's firm-specific noise. And noise that can be diversified away earns no compensation.

Part H. Two-fund separation with two clients. This is the most practical question on the paper.

A financial advisor uses two-fund separation for two clients. Client A has two hundred thousand. The advisor tells them to put one hundred thousand in the risk-free asset, and the remaining one hundred thousand across three stocks: forty thousand in X, fifty thousand in Y, ten thousand in Z.

Client B has a million dollars and wants more risk. She puts two hundred thousand in the risk-free asset.

The question: how should Client B allocate to X, Y, and Z?

Here's the key insight. Two-fund separation says every investor holds the same risky portfolio. They only differ in how much they put in it versus the risk-free asset. Conservative investors hold more risk-free. Aggressive investors hold more of the risky portfolio. But the risky portfolio itself - the tangent portfolio - is identical for everyone.

So step one. Extract the tangent portfolio from Client A's allocation. Client A's total risky investment is forty plus fifty plus ten, which is one hundred thousand. The weights within the risky portfolio: X is forty percent, Y is fifty percent, Z is ten percent.

Step two. Client B has a million dollars, puts two hundred thousand risk-free. That leaves eight hundred thousand for the risky portfolio.

Step three. Apply the same weights. X gets forty percent of eight hundred thousand, which is three hundred and twenty thousand. Y gets fifty percent, which is four hundred thousand. Z gets ten percent, which is eighty thousand.

Check: two hundred plus three hundred and twenty plus four hundred plus eighty equals one million. Done.

The beauty of this is that the advisor didn't need to re-optimise anything for Client B. The tangent portfolio weights are the same. Risk preferences only change the split between the risk-free asset and the tangent portfolio. That's two-fund separation. That's the punchline of session nine.

Alright. Let's close this out with the big picture.

This entire question tests one through-line. Diversification is free, so the market only prices what you can't diversify away. Stock X has lots of total risk but modest systematic risk. If you hold it alone, you're taking uncompensated risk. If you combine the risk-free asset and the market portfolio to get the same seven percent return, you cut your risk from twenty-six percent down to nine percent.

CML versus SML - know when to use which. CML is for portfolio construction. It tells you whether a portfolio is efficient. SML is for asset pricing. It tells you whether an asset's return is fair given its beta. Stock X fails the CML test but passes the SML test. It's not mispriced. It's just inefficient to hold alone.

Two-fund separation - everyone holds the same tangent portfolio. The only thing that changes across investors is how much they lever up or save in the risk-free asset. That's the elegance. One optimal risky portfolio for everyone.

Remember the formulas. Sharpe ratio: excess return over sigma. CML: R f plus Sharpe ratio of market times sigma. SML: R f plus beta times market risk premium. Beta: correlation times sigma i over sigma M. And two-fund separation: find the tangent portfolio weights, then scale.

You've got this. Have a good run.
