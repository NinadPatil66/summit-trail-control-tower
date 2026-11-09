
M5 to Summit Trail mapping

Source: Kaggle M5 Forecasting - Accuracy (sales_train_evaluation.csv, calendar.csv, sell_prices.csv).

Stores to DCs (units summed)

M5 storesSummit Trail DC
CA_1, CA_2ONT (Ontario, CA)
CA_3, CA_4RNO (Reno, NV)
TX_1, TX_2DAL (Dallas, TX)
TX_3ATL (Atlanta, GA)
WI_1, WI_2CMH (Columbus, OH)
WI_3ABE (Allentown, PA)

Items to SKUs

Keep the top 2,500 items by total units over d_1212 to d_1941. Sparse items add forecasting noise, not signal.

Categories

HOBBIES -> Outdoor gear, HOUSEHOLD -> Home goods, FOODS -> Trail consumables (rename only).

Dates

Use the last 730 days (d_1212 to d_1941). Shift every date forward 3,640 days (520 weeks) so weekdays stay aligned. History runs May 2024 to May 2026.

Dropped

M5 event and SNAP columns. Their dates don't match 2024 to 2026 after the shift; we build our own holiday and promo seed.

