# ShelfLife AI — Business Guide

*For sales teams, store managers, and business stakeholders*

---

## What is ShelfLife AI?

ShelfLife AI is a smart assistant for grocery stores that helps you **sell more food and waste less**.

Every day, fresh products sit on shelves too long, expire, and get thrown away — costing your store real money. At the same time, popular items run out, and customers leave without buying. ShelfLife AI fixes both problems by learning your store's unique sales patterns and telling you exactly **what to order, when to discount, and what to donate** — before products expire.

---

## The Problem We Solve

| The Pain | The Cost |
|---|---|
| Food expires on shelves before selling | US grocery stores lose **$18B+ annually** to waste |
| Popular items go out of stock | Lost sales, unhappy customers who shop elsewhere |
| Managers order based on gut feel | Leads to both over-ordering (waste) and under-ordering (stockouts) |
| No early warning system | By the time you notice waste, the money is already lost |
| Each store is different | What sells in one location doesn't match another |

---

## What ShelfLife AI Does — In Plain Language

### 1. Predicts What Will Sell Tomorrow

The AI studies your store's history — what sold on which day, during which season, during promotions, before holidays — and tells you **how many units of each product your store will sell tomorrow**.

**Why this matters:** If you know bananas will sell 40 units tomorrow (not 20, not 80), you order exactly 40. No waste, no empty shelf.

### 2. Spots Products About to Be Wasted

The AI gives every product a **waste risk score** — a percentage that says "there's a 75% chance this yogurt will expire before it sells." Products with high scores show up as alerts.

**Why this matters:** You see the problem 2–3 days before expiry, when you can still do something about it — markdown, bundle, or donate.

### 3. Tells You Exactly What to Do

Based on predictions and risk scores, ShelfLife AI generates specific actions:

| Action | Example |
|---|---|
| **Markdown** | "Reduce Organic Whole Milk by 30% — saves $47 in waste" |
| **Reorder** | "Order 25 units of Sourdough Bread — will run out in 2 days" |
| **Donate** | "Donate 12 units of Greek Yogurt to food bank before Friday expiry" |
| **Adjust Order** | "Reduce next Bakery order by 15% — consistently over-ordering" |
| **Redistribute** | "Transfer 20 units of Lettuce to Downtown store — selling faster there" |

### 4. Compares All Your Stores

See every store side by side: which one wastes the most, which one earns the most, which one needs attention this week.

---

## How Accurate Is It?

| Metric | What It Means | Our Score |
|---|---|---|
| **MAPE** | Average prediction error | **7.7%** (excellent — industry standard is 15–30%) |
| **Waste Risk AUC** | How well we identify products that will be wasted | **98%** (near perfect) |
| **vs Simple Rules** | Compared to "order what you sold last week" | **5× more accurate** |

For a product that sells 10 units per day, the AI is typically off by less than 1 unit. A simple spreadsheet formula would be off by 3–4 units.

---

## "Why Can't We Just Use a Spreadsheet?"

Great question. Here's the honest answer:

A spreadsheet can tell you: *"Last week, this product sold an average of 15 units per day."*

The AI can tell you: *"Tomorrow is Saturday before a holiday weekend. This product usually sells 23 units on Saturdays, but we have a promotion running, inventory is low, and the weather forecast shows rain. Predicted: 19 units, with 90% confidence it will be between 16 and 22."*

The difference is **35 factors analyzed simultaneously**, including:
- Day of week patterns (Mondays ≠ Fridays)
- Monthly seasonality (December ≠ March)
- Holiday effects (sales spike before Thanksgiving, drop after)
- Promotion impact (a 20% discount can double sales overnight)
- Inventory feedback (when stock is low, sales naturally drop)
- Price sensitivity (each product responds differently to price changes)
- Cross-product patterns (if chicken is on sale, salad sales go up too)

No human and no spreadsheet can weigh all 35 factors at once for 50 products across 3 stores every single day. The AI does it in 20 seconds.

---

## "Can We Predict Next Month?"

**Short answer:** Not yet, but it's on the roadmap.

**Why:** The current AI is trained to predict 1–7 days ahead using recent patterns. Monthly forecasts need a different model architecture (seasonal decomposition + trend projection). We're building this as a Phase 2 feature.

**What you can do today:**
- Look at the last 30 days of actual vs predicted to understand your store's trajectory
- Use the weekly waste trend to see if things are improving or getting worse
- Compare store performance month-over-month using the scorecards

---

## "How Much Money Does This Save?"

Based on industry benchmarks and our model accuracy:

| Store Size | Annual Waste (Without AI) | Expected Reduction | Annual Savings |
|---|---|---|---|
| Small (200 products) | ~$120,000 | 15–20% | **$18,000–24,000** |
| Medium (500 products) | ~$350,000 | 20–25% | **$70,000–87,500** |
| Large (1000+ products) | ~$800,000 | 20–25% | **$160,000–200,000** |

Additional revenue from fewer stockouts: **+5–10%** better product availability.

---

## Daily Workflow for a Store Manager

### Morning (5 minutes)
1. **Command Center** — Check the 4 KPI cards. Is waste going up or down?
2. **Inventory Health** — Look at "Critical (≤2 days)" number. If it's not zero, act now.
3. **Recommendations** — Follow the top 3 recommended actions.

### Weekly (20 minutes)
1. **Waste Analytics** — Which categories got worse? Which improved?
2. **Product Catalog** — Are your top wasted products the same as last week?
3. **Demand Forecast** — Is the AI still accurate? (MAPE below 15%?)

### Monthly
1. **Store Scorecards** — Compare stores. Which one needs focus next month?
2. **Model Performance** — Any drift alerts? Are predictions still reliable?
3. Review waste trend — is the line going down over the month?

---

## Quick Answers for Common Questions

**"Is this replacing my job?"**
No. The AI handles the math. You handle the decisions, the relationships, the shelf management, and the judgment calls. The AI just makes sure you have the right information at the right time.

**"What if the AI is wrong?"**
It will be wrong sometimes — that's normal. It's right 92% of the time (MAPE 7.7%). Even when it's off, it's usually off by a small amount. The confidence band on the Demand Forecast shows you the range — if it's wide, the AI is less sure.

**"Do I need to feed it data?"**
No. The system collects data automatically from your sales and inventory systems. All you need to do is open the dashboard and act on what it tells you.

**"How often does it learn?"**
The AI is retrained periodically with the latest data. It automatically detects when its predictions start drifting and triggers a retraining cycle. You don't need to do anything.

---

*ShelfLife AI — Less waste. More sales. Better decisions.*
