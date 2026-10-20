CREATE EXTENSION IF NOT EXISTS vector;

-- 공정 데이터: PHM 2018 원본을 run_id = '{runnum}-{Lot}' (배치 안의 웨이퍼 1장 처리, recipe 1개) 단위로 요약.
-- runnum은 여러 Lot의 배치, Lot은 여러 stage에서 재처리되므로 둘 다 단독으로는 조사 단위가 아님.
-- 센서값은 원본에서 이미 표준화됨(단위 없음)
CREATE TABLE IF NOT EXISTS runs (
  tool text, run_id text, runnum bigint, lot text, stage text, recipe text,
  start_time float8, end_time float8, n_rows int,
  PRIMARY KEY (tool, run_id));
-- step x 센서별 통계. 센서는 열이 아닌 행 (도구가 어떤 센서든 같은 쿼리)
CREATE TABLE IF NOT EXISTS run_steps (
  tool text, run_id text, recipe_step text, signal text,
  n int, mean float8, std float8, min float8, max float8, missing_rate float8,
  PRIMARY KEY (tool, run_id, recipe_step, signal),
  FOREIGN KEY (tool, run_id) REFERENCES runs);
CREATE INDEX IF NOT EXISTS runs_recipe ON runs (tool, recipe, end_time);
CREATE TABLE IF NOT EXISTS faults (id serial PRIMARY KEY, tool text, time float8, fault_name text);
CREATE INDEX IF NOT EXISTS faults_tool_time ON faults (tool, time);

-- 지식(RAG)
CREATE TABLE IF NOT EXISTS doc_chunks (
  id serial PRIMARY KEY, source text, section text, content text,
  embedding vector(1536), embed_model text);
CREATE INDEX IF NOT EXISTS doc_chunks_hnsw ON doc_chunks USING hnsw (embedding vector_cosine_ops);

-- 업무/작업
CREATE TABLE IF NOT EXISTS tasks (
  id uuid PRIMARY KEY, user_name text, user_role text, question text, tool text, run_id text,
  status text CHECK (status IN ('QUEUED','RUNNING','WAITING_APPROVAL','DONE','FAILED')),
  report jsonb, error text,
  created_at timestamptz DEFAULT now(), updated_at timestamptz DEFAULT now());
CREATE TABLE IF NOT EXISTS task_events (
  task_id uuid REFERENCES tasks, seq int, type text, payload jsonb,
  created_at timestamptz DEFAULT now(), PRIMARY KEY (task_id, seq));
CREATE TABLE IF NOT EXISTS investigations (
  id serial PRIMARY KEY, task_id uuid UNIQUE REFERENCES tasks, tool text, run_id text,
  report jsonb, approved_by text, approved_at timestamptz DEFAULT now());
