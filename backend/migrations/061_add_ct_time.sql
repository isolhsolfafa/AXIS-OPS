-- Migration 061: S-2 (FEAT-CT-TRUE-UNION) — ct_time_minutes 컬럼 추가 (진짜 CT, across-worker UNION) + 백필
--
-- Sprint: FEAT-CT-TRUE-UNION (VIEW OPS_API_REQUESTS #82 ⓑ, Codex 3라운드 GO M=0)
-- 도입 시점: 2026-06-08
--
-- CT (union) = FLOOR(length( UNION_worker worker_active_mr ))
--   worker_active_mr = (session_union ∩ BH) − (manual_pause ∪ 식사휴게)   ← 작업자별 정제 multirange (060 동일)
--   M/H (active)     = Σ_worker FLOOR(length(worker_active_mr))            ← 기존 active_time_minutes
--   CT  (union)      = 전 작업자 worker_active_mr 의 across-worker UNION 길이 ← 신규 ct_time_minutes
--   저장값            = LEAST(FLOOR(union_exact), active_time_minutes)       ← A-1 가드 (불변식 CT ≤ M/H)
--
-- ⚠️ 순서: 작업자별 clip(BH·pause·break) 먼저 → 정제 multirange 를 across-worker UNION (raw 세션 union 먼저 ❌).
-- ⚠️ 060 과 동일 CTE 재사용 — 식사휴게만([11:20-12:20, 17:00-18:00]) 제외 (오전/오후 20분 휴게 = 작업시간 인정).
--    059/060 active_time_minutes 산식과 100% 정합 (작업자별 정제 multirange 까지 동일). 최종 집계만 SUM→UNION 차이.
-- ⚠️ 058 = v2.22.0 예약 / 059 = active 컬럼 / 060 = 식사정정 재백필 → 061 사용 (충돌 회피).
--
-- A-2 preflight: ct_raw > active_time_minutes 케이스 = late checkout 유입으로 현재 재계산 CT > 과거 active 스냅샷 →
--   LEAST 가드가 active 로 보수적 clipping. 의도된 동작(불변식 CT ≤ M/H 보장). 아래 RAISE NOTICE 로 가시화.
--
-- 호환성:
--   - additive only (NULLABLE, DEFAULT NULL) — 기존 row forward-only
--   - active_time_minutes·duration_minutes(man-hour)·close·audit 전부 불변
--   - active NULL(TANK_DOCKING 등 one-action) → ct NULL 자연 유지 (LEAST(ct, NULL) → ct, 단 WHERE 가드로 멱등)
--   - 백필은 현재 admin_settings(근무/휴게 시간표) 균일 기준 (운영상 고정, 변경 이력 없음)

BEGIN;

-- 1. ct_time_minutes 컬럼 추가 (NULLABLE, additive)
ALTER TABLE app_task_details
ADD COLUMN IF NOT EXISTS ct_time_minutes INTEGER DEFAULT NULL;

-- A-2 preflight — ct_raw > active_time_minutes 건수/샘플 가시화 (백필 전 관측, LEAST 보수 clipping 대상)
DO $preflight$
DECLARE
  _cnt int;
BEGIN
  WITH starts AS (
    SELECT td.id AS tid, td.completed_at AS close_at, ws.worker_id, ws.started_at,
           LEAD(ws.started_at) OVER (PARTITION BY td.id, ws.worker_id ORDER BY ws.started_at) AS next_start,
           (SELECT MIN(wc.completed_at) FROM work_completion_log wc
              WHERE wc.task_id = td.id AND wc.worker_id = ws.worker_id
                AND wc.completed_at >= ws.started_at) AS comp,
           (SELECT MAX(pa.check_time) FROM hr.partner_attendance pa
              WHERE pa.worker_id = ws.worker_id AND pa.check_type = 'out'
                AND DATE(pa.check_time AT TIME ZONE 'Asia/Seoul')
                    = DATE(ws.started_at AT TIME ZONE 'Asia/Seoul')) AS checkout
    FROM app_task_details td
    JOIN work_start_log ws ON ws.task_id = td.id
    WHERE td.completed_at IS NOT NULL
      AND ws.started_at < td.completed_at
      AND td.active_time_minutes IS NOT NULL
  ),
  sessions AS (
    SELECT tid, close_at, worker_id,
           tstzrange(started_at,
             GREATEST(started_at, LEAST(
               COALESCE(comp, 'infinity'::timestamptz),
               COALESCE(checkout, 'infinity'::timestamptz),
               CASE WHEN checkout IS NULL
                    THEN (date_trunc('day', started_at AT TIME ZONE 'Asia/Seoul') + interval '17 hours') AT TIME ZONE 'Asia/Seoul'
                    ELSE 'infinity'::timestamptz END,
               COALESCE(next_start, 'infinity'::timestamptz),
               close_at
             )), '[)') AS sess
    FROM starts
  ),
  sess_union AS (SELECT tid, close_at, worker_id, range_agg(sess) AS mr FROM sessions GROUP BY tid, close_at, worker_id),
  pauses AS (
    SELECT su.tid, wpl.worker_id, tstzrange(wpl.paused_at, COALESCE(wpl.resumed_at, su.close_at), '[)') AS pr
    FROM sess_union su
    JOIN work_pause_log wpl ON wpl.task_detail_id = su.tid AND wpl.worker_id = su.worker_id
    WHERE wpl.pause_type = 'manual' AND wpl.paused_at < su.close_at
      AND COALESCE(wpl.resumed_at, su.close_at) > wpl.paused_at
  ),
  pause_union AS (SELECT tid, worker_id, range_agg(pr) AS mr FROM pauses GROUP BY tid, worker_id),
  days AS (
    SELECT su.tid, su.worker_id,
           generate_series(date_trunc('day', lower(su.mr) AT TIME ZONE 'Asia/Seoul'),
                           date_trunc('day', upper(su.mr) AT TIME ZONE 'Asia/Seoul'),
                           interval '1 day')::date AS d
    FROM sess_union su
  ),
  att_day AS (
    SELECT dd.tid, dd.worker_id, dd.d,
      MIN(pa.check_time) FILTER (WHERE pa.check_type='in')  AS cin,
      MAX(pa.check_time) FILTER (WHERE pa.check_type='out') AS cout
    FROM days dd
    LEFT JOIN hr.partner_attendance pa
      ON pa.worker_id = dd.worker_id AND DATE(pa.check_time AT TIME ZONE 'Asia/Seoul') = dd.d
    GROUP BY dd.tid, dd.worker_id, dd.d
  ),
  bh_day AS (
    SELECT tid, worker_id,
      CASE
        WHEN cin IS NOT NULL AND cout IS NOT NULL AND cin < cout THEN tstzrange(cin, cout, '[)')
        WHEN extract(dow from d) IN (0,6)
          THEN tstzrange((d + time '08:00') AT TIME ZONE 'Asia/Seoul', (d + time '17:00') AT TIME ZONE 'Asia/Seoul', '[)')
        ELSE tstzrange((d + time '08:00') AT TIME ZONE 'Asia/Seoul', (d + time '20:00') AT TIME ZONE 'Asia/Seoul', '[)')
      END AS bhr
    FROM att_day
  ),
  bh_union AS (SELECT tid, worker_id, range_agg(bhr) AS mr FROM bh_day GROUP BY tid, worker_id),
  breaks_day AS (
    -- 식사시간만 (점심 11:20-12:20 / 저녁 17:00-18:00). 오전/오후 20분 휴게 = 작업시간 인정 (060 동일).
    SELECT tid, worker_id, unnest(ARRAY[
      tstzrange((d + time '11:20') AT TIME ZONE 'Asia/Seoul', (d + time '12:20') AT TIME ZONE 'Asia/Seoul','[)'),
      tstzrange((d + time '17:00') AT TIME ZONE 'Asia/Seoul', (d + time '18:00') AT TIME ZONE 'Asia/Seoul','[)')
    ]) AS br
    FROM days
  ),
  breaks_union AS (SELECT tid, worker_id, range_agg(br) AS mr FROM breaks_day GROUP BY tid, worker_id),
  -- 작업자별 정제 multirange = (sess ∩ BH) − (pause ∪ break)
  cleaned AS (
    SELECT su.tid, su.worker_id,
      ( (su.mr * COALESCE(bh.mr, '{}'::tstzmultirange))
        - (COALESCE(pu.mr,'{}'::tstzmultirange) + COALESCE(bk.mr,'{}'::tstzmultirange)) ) AS amr
    FROM sess_union su
    LEFT JOIN pause_union pu USING(tid, worker_id)
    LEFT JOIN bh_union bh USING(tid, worker_id)
    LEFT JOIN breaks_union bk USING(tid, worker_id)
  ),
  ranges AS (SELECT tid, r FROM cleaned, unnest(amr) r),
  ct_union AS (
    SELECT tid,
      COALESCE((SELECT SUM(EXTRACT(EPOCH FROM (upper(g)-lower(g)))/60)
                FROM unnest(range_agg(r)) g),0)::numeric AS ct_raw_min
    FROM ranges GROUP BY tid
  )
  SELECT COUNT(*) INTO _cnt
  FROM ct_union cu
  JOIN app_task_details td ON td.id = cu.tid
  WHERE FLOOR(cu.ct_raw_min) > td.active_time_minutes;

  RAISE NOTICE '[061 preflight] ct_raw > active_time_minutes (LEAST 보수 clipping 대상): % rows', _cnt;
END
$preflight$;

-- 2. 백필 — 완료 task 전수. 작업자별 정제 multirange(cleaned) → across-worker range_agg union 길이.
--    059/060 과 동일 CTE (식사휴게만). active_time_minutes IS NULL → ct NULL 자연 (조인 조건).
--    저장 ct = LEAST(ct_raw, active_time_minutes) (A-1 불변식 CT ≤ M/H).
WITH starts AS (
  SELECT td.id AS tid, td.completed_at AS close_at, ws.worker_id, ws.started_at,
         LEAD(ws.started_at) OVER (PARTITION BY td.id, ws.worker_id ORDER BY ws.started_at) AS next_start,
         (SELECT MIN(wc.completed_at) FROM work_completion_log wc
            WHERE wc.task_id = td.id AND wc.worker_id = ws.worker_id
              AND wc.completed_at >= ws.started_at) AS comp,
         (SELECT MAX(pa.check_time) FROM hr.partner_attendance pa
            WHERE pa.worker_id = ws.worker_id AND pa.check_type = 'out'
              AND DATE(pa.check_time AT TIME ZONE 'Asia/Seoul')
                  = DATE(ws.started_at AT TIME ZONE 'Asia/Seoul')) AS checkout
  FROM app_task_details td
  JOIN work_start_log ws ON ws.task_id = td.id
  WHERE td.completed_at IS NOT NULL
    AND ws.started_at < td.completed_at
),
sessions AS (
  SELECT tid, close_at, worker_id,
         tstzrange(started_at,
           GREATEST(started_at, LEAST(
             COALESCE(comp, 'infinity'::timestamptz),
             COALESCE(checkout, 'infinity'::timestamptz),
             CASE WHEN checkout IS NULL
                  THEN (date_trunc('day', started_at AT TIME ZONE 'Asia/Seoul') + interval '17 hours') AT TIME ZONE 'Asia/Seoul'
                  ELSE 'infinity'::timestamptz END,
             COALESCE(next_start, 'infinity'::timestamptz),
             close_at
           )), '[)') AS sess
  FROM starts
),
sess_union AS (SELECT tid, close_at, worker_id, range_agg(sess) AS mr FROM sessions GROUP BY tid, close_at, worker_id),
pauses AS (
  SELECT su.tid, wpl.worker_id, tstzrange(wpl.paused_at, COALESCE(wpl.resumed_at, su.close_at), '[)') AS pr
  FROM sess_union su
  JOIN work_pause_log wpl ON wpl.task_detail_id = su.tid AND wpl.worker_id = su.worker_id
  WHERE wpl.pause_type = 'manual' AND wpl.paused_at < su.close_at
    AND COALESCE(wpl.resumed_at, su.close_at) > wpl.paused_at
),
pause_union AS (SELECT tid, worker_id, range_agg(pr) AS mr FROM pauses GROUP BY tid, worker_id),
days AS (
  SELECT su.tid, su.worker_id,
         generate_series(date_trunc('day', lower(su.mr) AT TIME ZONE 'Asia/Seoul'),
                         date_trunc('day', upper(su.mr) AT TIME ZONE 'Asia/Seoul'),
                         interval '1 day')::date AS d
  FROM sess_union su
),
att_day AS (
  SELECT dd.tid, dd.worker_id, dd.d,
    MIN(pa.check_time) FILTER (WHERE pa.check_type='in')  AS cin,
    MAX(pa.check_time) FILTER (WHERE pa.check_type='out') AS cout
  FROM days dd
  LEFT JOIN hr.partner_attendance pa
    ON pa.worker_id = dd.worker_id AND DATE(pa.check_time AT TIME ZONE 'Asia/Seoul') = dd.d
  GROUP BY dd.tid, dd.worker_id, dd.d
),
bh_day AS (
  SELECT tid, worker_id,
    CASE
      WHEN cin IS NOT NULL AND cout IS NOT NULL AND cin < cout THEN tstzrange(cin, cout, '[)')
      WHEN extract(dow from d) IN (0,6)
        THEN tstzrange((d + time '08:00') AT TIME ZONE 'Asia/Seoul', (d + time '17:00') AT TIME ZONE 'Asia/Seoul', '[)')
      ELSE tstzrange((d + time '08:00') AT TIME ZONE 'Asia/Seoul', (d + time '20:00') AT TIME ZONE 'Asia/Seoul', '[)')
    END AS bhr
  FROM att_day
),
bh_union AS (SELECT tid, worker_id, range_agg(bhr) AS mr FROM bh_day GROUP BY tid, worker_id),
breaks_day AS (
  SELECT tid, worker_id, unnest(ARRAY[
    tstzrange((d + time '11:20') AT TIME ZONE 'Asia/Seoul', (d + time '12:20') AT TIME ZONE 'Asia/Seoul','[)'),
    tstzrange((d + time '17:00') AT TIME ZONE 'Asia/Seoul', (d + time '18:00') AT TIME ZONE 'Asia/Seoul','[)')
  ]) AS br
  FROM days
),
breaks_union AS (SELECT tid, worker_id, range_agg(br) AS mr FROM breaks_day GROUP BY tid, worker_id),
cleaned AS (
  SELECT su.tid, su.worker_id,
    ( (su.mr * COALESCE(bh.mr, '{}'::tstzmultirange))
      - (COALESCE(pu.mr,'{}'::tstzmultirange) + COALESCE(bk.mr,'{}'::tstzmultirange)) ) AS amr
  FROM sess_union su
  LEFT JOIN pause_union pu USING(tid, worker_id)
  LEFT JOIN bh_union bh USING(tid, worker_id)
  LEFT JOIN breaks_union bk USING(tid, worker_id)
),
ranges AS (SELECT tid, r FROM cleaned, unnest(amr) r),
ct_per_task AS (
  SELECT tid,
    COALESCE((SELECT SUM(EXTRACT(EPOCH FROM (upper(g)-lower(g)))/60)
              FROM unnest(range_agg(r)) g),0)::numeric AS ct_raw_min
  FROM ranges GROUP BY tid
)
-- M-2: eligible(active NOT NULL & ct NULL) 전수 LEFT JOIN.
--   ct_per_task 는 amr 빈집합(active=0 미추적 task)이면 tid 누락 → INNER 매칭 시 active=0 행 ct NULL 잔류.
--   LEFT JOIN + COALESCE(ct_raw, 0) → active=0 → ct = LEAST(0, 0) = 0 (compute_task_work live 산식과 정합).
--   active NULL(TANK_DOCKING 등) → elig 제외 → ct NULL 유지. 멱등(ct IS NULL).
UPDATE app_task_details td
SET ct_time_minutes = LEAST(COALESCE(FLOOR(cpt.ct_raw_min)::int, 0), td.active_time_minutes)
FROM (SELECT id FROM app_task_details
      WHERE active_time_minutes IS NOT NULL AND ct_time_minutes IS NULL) elig
LEFT JOIN ct_per_task cpt ON cpt.tid = elig.id
WHERE td.id = elig.id;

COMMIT;
