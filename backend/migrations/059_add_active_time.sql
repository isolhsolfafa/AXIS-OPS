-- Migration 059: Sprint 86 — active_time_minutes 컬럼 추가 (순수 작업시간) + 백필
--
-- Sprint: FEAT-ACTIVE-TIME-PURE-WORK-20260606 (Codex 5라운드 GO)
-- 도입 시점: 2026-06-06
--
-- active_time = 순수 작업시간 = Σ_w FLOOR(GREATEST(0, len(session∩영업창)
--                  − len((manual_pause ∪ 휴게) ∩ session ∩ 영업창)))
--   · 영업창 = attendance[MIN(in),MAX(out)] 우선 / fallback 평일[08:00,20:00]·주말[08:00,17:00] KST
--   · 휴게 = 일별 [10:00-10:20, 11:20-12:20, 15:00-15:20, 17:00-18:00] (admin 표준 시간표)
--   · 저장 active = LEAST(active_raw, duration_minutes) — 불변식 active ≤ man-hour
--
-- ⚠️ 058 은 v2.22.0(man-hour duration 백필) 예약 → 059 사용 (충돌 회피).
-- ⚠️ 본 백필은 active_time_minutes 만 채움 — duration_minutes 불간섭(man-hour 불변).
--
-- 호환성:
--   - additive only (NULLABLE, DEFAULT NULL) — 기존 row forward-only
--   - man-hour(duration_minutes)·close·audit 전부 불변
--   - 백필은 현재 admin_settings(근무/휴게 시간표) 균일 기준 (운영상 고정, 변경 이력 없음)
--     → 향후 시간표 변경 시 전체 재백필 필요 (BACKLOG REBACKFILL-ACTIVE-TIME-ON-SETTINGS-CHANGE)

BEGIN;

-- 1. active_time_minutes 컬럼 추가 (NULLABLE, additive)
ALTER TABLE app_task_details
ADD COLUMN IF NOT EXISTS active_time_minutes INTEGER DEFAULT NULL;

-- 2. 백필 — 완료 task 전수 (compute_task_work 와 동일 SQL, close_at = completed_at).
--    duration_minutes 불간섭. active = LEAST(active_raw, 기존 duration_minutes) (CT 표시 일관).
--    set-based 단일 UPDATE (행 lock 짧음, 읽기 산출이라 운영 무중단).
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
    tstzrange((d + time '10:00') AT TIME ZONE 'Asia/Seoul', (d + time '10:20') AT TIME ZONE 'Asia/Seoul','[)'),
    tstzrange((d + time '11:20') AT TIME ZONE 'Asia/Seoul', (d + time '12:20') AT TIME ZONE 'Asia/Seoul','[)'),
    tstzrange((d + time '15:00') AT TIME ZONE 'Asia/Seoul', (d + time '15:20') AT TIME ZONE 'Asia/Seoul','[)'),
    tstzrange((d + time '17:00') AT TIME ZONE 'Asia/Seoul', (d + time '18:00') AT TIME ZONE 'Asia/Seoul','[)')
  ]) AS br
  FROM days
),
breaks_union AS (SELECT tid, worker_id, range_agg(br) AS mr FROM breaks_day GROUP BY tid, worker_id),
per_worker AS (
  SELECT su.tid, su.worker_id,
    COALESCE((SELECT SUM(EXTRACT(EPOCH FROM (upper(r)-lower(r)))/60)
              FROM unnest(su.mr * COALESCE(bh.mr, '{}'::tstzmultirange)) r),0) AS sess_bh_min,
    COALESCE((SELECT SUM(EXTRACT(EPOCH FROM (upper(r)-lower(r)))/60)
              FROM unnest( (COALESCE(pu.mr,'{}'::tstzmultirange) + COALESCE(bk.mr,'{}'::tstzmultirange))
                           * su.mr * COALESCE(bh.mr,'{}'::tstzmultirange) ) r),0) AS inactive_min
  FROM sess_union su
  LEFT JOIN pause_union pu USING(tid, worker_id)
  LEFT JOIN bh_union bh USING(tid, worker_id)
  LEFT JOIN breaks_union bk USING(tid, worker_id)
),
active_per_task AS (
  SELECT tid, COALESCE(SUM(FLOOR(GREATEST(0, sess_bh_min - inactive_min))),0)::int AS active_raw
  FROM per_worker GROUP BY tid
)
UPDATE app_task_details td
SET active_time_minutes = LEAST(apt.active_raw, COALESCE(td.duration_minutes, apt.active_raw))
FROM active_per_task apt
WHERE td.id = apt.tid
  AND td.active_time_minutes IS NULL;  -- 멱등 (이미 채워진 행 skip)

COMMIT;
