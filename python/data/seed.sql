-- 默认演示账号：admin / admin123
INSERT INTO users (id, tenant_id, username, email, hashed_password, role, is_active, created_at, updated_at)
VALUES (
  'admin-001',
  'tenant-001',
  'admin',
  'admin@example.com',
  '$2b$12$iWheK/VZWEx6/oANU18fq.736.a1KfJljSbOoR2EEjIZFuaDYCNvK',
  'admin',
  true,
  CURRENT_TIMESTAMP,
  CURRENT_TIMESTAMP
)
ON CONFLICT (username) DO NOTHING;
