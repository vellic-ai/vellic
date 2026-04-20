-- E2E smoke test seed data
-- Inserts two webhook deliveries with successful pipeline jobs so that
-- the deliveries list filter=done and job detail tests always find rows.

INSERT INTO webhook_deliveries (delivery_id, event_type, payload, received_at, processed_at)
VALUES
  (
    'e2e-del-aaa-0001',
    'pull_request',
    '{"action":"opened","repository":{"full_name":"vellic/smoke-repo"},"pull_request":{"number":1,"title":"E2E seed PR"}}',
    NOW() - INTERVAL '2 hours',
    NOW() - INTERVAL '110 minutes'
  ),
  (
    'e2e-del-aaa-0002',
    'pull_request',
    '{"action":"synchronize","repository":{"full_name":"vellic/smoke-repo"},"pull_request":{"number":2,"title":"E2E seed PR 2"}}',
    NOW() - INTERVAL '1 hour',
    NOW() - INTERVAL '55 minutes'
  )
ON CONFLICT DO NOTHING;

INSERT INTO pipeline_jobs (id, delivery_id, status, retry_count, created_at, updated_at)
VALUES
  (
    'f1000000-e2e0-0000-0000-000000000001'::uuid,
    'e2e-del-aaa-0001',
    'done',
    0,
    NOW() - INTERVAL '110 minutes',
    NOW() - INTERVAL '100 minutes'
  ),
  (
    'f1000000-e2e0-0000-0000-000000000002'::uuid,
    'e2e-del-aaa-0002',
    'done',
    0,
    NOW() - INTERVAL '55 minutes',
    NOW() - INTERVAL '50 minutes'
  )
ON CONFLICT DO NOTHING;
