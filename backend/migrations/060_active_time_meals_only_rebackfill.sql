-- Migration 060: active_time 식사시간만 제외 정정 + 전체 재백필
--
-- Sprint: FEAT-ACTIVE-TIME-PURE-WORK 후속 정정 (사용자 catch 2026-06-07)
-- 배경: v2.28.0(migration 059)은 4개 휴게(오전 10:00-10:20 / 점심 11:20-12:20 /
--       오후 15:00-15:20 / 저녁 17:00-18:00)를 모두 제외했으나,
--       **오전/오후 20분 휴게는 작업시간으로 인정** = 식사(점심·저녁)만 제외해야 함.
--       → breaks = [11:20-12:20, 17:00-18:00] 만. active_time 전체 재계산(값 상승).
--
-- ⚠️ 059 와 달리 active_time_minutes IS NULL 가드 없음 — 기존 값 전체 OVERWRITE (재백필).
-- ⚠️ duration_minutes(man-hour) 불간섭. active = LEAST(active_raw, 기존 duration_minutes).
-- compute_task_work 코드도 동일 정정(식사만) — 본 migration 후 신규 완료부터 정합.

BEGIN;

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
  -- 식사시간만 (점심 11:20-12:20 / 저녁 17:00-18:00). 오전/오후 20분 휴게 = 작업시간 인정.
  SELECT tid, worker_id, unnest(ARRAY[
    tstzrange((d + time '11:20') AT TIME ZONE 'Asia/Seoul', (d + time '12:20') AT TIME ZONE 'Asia/Seoul','[)'),
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
WHERE td.id = apt.tid;  -- 전체 재계산 (IS NULL 가드 없음 — 식사만 제외로 값 상승 OVERWRITE)

COMMIT;
