-- Sprint 17: 출퇴근 분류 체계 추가 (work_site + product_line)
-- VARCHAR + CHECK constraint 방식 (ENUM 아님 — 확장성)
-- 기존 데이터는 DEFAULT 값 자동 적용 (GST + SCR)

ALTER TABLE hr.partner_attendance
  ADD COLUMN work_site VARCHAR(10) NOT NULL DEFAULT 'GST',
  ADD COLUMN product_line VARCHAR(10) NOT NULL DEFAULT 'SCR';

ALTER TABLE hr.partner_attendance
  ADD CONSTRAINT chk_work_site CHECK (work_site IN ('GST', 'HQ')),
  ADD CONSTRAINT chk_product_line CHECK (product_line IN ('SCR', 'CHI'));

CREATE INDEX IF NOT EXISTS idx_partner_att_site_line
  ON hr.partner_attendance(work_site, product_line);
