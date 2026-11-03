# Query performance evidence

Measured EXPLAIN ANALYZE/BUFFERS plans are stored in reports/query_plans.json. These are local prototype timings, not production SLAs.

| query       |   execution_ms | plan             |
|:------------|---------------:|:-----------------|
| monthly     |         65.989 | Aggregate        |
| daily_queue |          1.16  | Bitmap Heap Scan |

Indexes cover order_id, purchase_date and primary_seller_id; item/bridge indexes cover order_id and seller_id. The daily lookup can use the purchase-date index. Aggregate scans may correctly choose sequential scans. Inspect plans against workload before adding more indexes.

Last measured stages: {'models': 17.613, 'optimization': 17.309}
